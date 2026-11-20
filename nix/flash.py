"""Install a generation's verified Android images to the running Zhiyu slot."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import sys

# Write vbmeta last so we only commit its descriptors after the payloads.
PARTITIONS = {"boot": 96 << 20, "vendor_boot": 96 << 20, "init_boot": 8 << 20, "vbmeta": 64 << 10}
STORE_SYSTEM = re.compile(r"/nix/store/[0-9a-z]{32}-nixos-system-[^/]+")
ID_PAIR = re.compile(r"[0-9a-f]{64} [0-9a-f]{64}\n")
BLKGETSIZE64 = 0x80081272
BLKFLSBUF = 0x1261
CHUNK = 1 << 20


def require(condition, error):
    if not condition:
        raise ValueError(error)


def slot(proc):
    cmdline = (proc / "cmdline").read_text().split()
    supplied = [token.split("=", 1)[-1] for token in cmdline
                if token.split("=", 1)[0] == "androidboot.slot_suffix"]
    bootconfig = proc / "bootconfig"
    config_slots = []
    if bootconfig.exists():
        for line in bootconfig.read_text().splitlines():
            if re.match(r"^\s*androidboot\.slot_suffix(?:\s|=|$)", line):
                match = re.fullmatch(r'\s*androidboot\.slot_suffix\s*=\s*"(_[ab])"\s*', line)
                require(match, "Malformed slot in bootconfig")
                config_slots.append(match[1])
    values = supplied + config_slots
    require(len(supplied) <= 1 and len(config_slots) <= 1 and values
            and len(set(values)) == 1 and values[0] in ("_a", "_b"),
            "Missing, duplicate, or conflicting A/B slot")
    return values[0]


def manifest(path, pattern):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        require(len(fields) == 2, f"Malformed {path.name}")
        value, name = fields
        require(re.fullmatch(pattern, value) and name not in result, f"Malformed {path.name} entry")
        result[name] = value
    require(set(result) == {part + ".img" for part in PARTITIONS}, f"Invalid {path.name} partition set")
    return result


def blocks(file, size):
    file.seek(0)
    while size:
        block = file.read(min(size, CHUNK))
        require(block, f"Short read from {file.name}")
        size -= len(block)
        yield block


def checksum(file, size):
    digest = hashlib.sha256()
    for block in blocks(file, size):
        digest.update(block)
    return digest.hexdigest()


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_profile(profiles, name, system):
    temp = profiles / f".{name}.{os.getpid()}"
    temp.unlink(missing_ok=True)
    temp.symlink_to(system)
    os.replace(temp, profiles / name)
    sync_dir(profiles)


def flash(args):
    simulate = args.simulate is not None
    base = args.simulate.resolve() if simulate else Path("/")
    proc = base / "proc"
    compatible = (proc / "device-tree/lenovo,mainline-compatible").read_bytes().split(b"\0")
    require(b"lenovo,zhiyu" in compatible, "Device is not a Lenovo TB378FC")
    active = slot(proc)
    require(args.expect_slot is None or active == "_" + args.expect_slot, "Active slot differs from requested slot")

    system = args.system.resolve(strict=True)
    require(simulate or STORE_SYSTEM.fullmatch(str(system)), "Expected a NixOS toplevel in /nix/store")
    images = system / "etc/zhiyu/boot-images"
    ids = (system / "etc/zhiyu/boot-id").read_text()
    require(ID_PAIR.fullmatch(ids) and ids == (images / "BOOT-IDS").read_text(), "Generation and bundle IDs differ")
    require(os.access(system / "init", os.X_OK), "Generation init is not executable")
    hashes = manifest(images / "SHA256SUMS", r"[0-9a-f]{64}")
    sizes = manifest(images / "SIZES", r"[1-9][0-9]*")
    profiles = base / "nix/var/nix/profiles"

    with ExitStack() as stack:
        flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
        lock = os.open(base / "run/lock/zhiyu-install.lock", flags, 0o600)
        stack.callback(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        prepared = []
        dev_ids = set()
        for part, expected_size in PARTITIONS.items():
            name = part + ".img"
            require(int(sizes[name]) == expected_size, f"Unexpected image size for {part}")
            source = stack.enter_context((images / name).open("rb"))
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_size == expected_size, f"Invalid {name}")
            digest = hashes[name]
            require(checksum(source, expected_size) == digest, f"Image hash mismatch for {name}")

            label = part + active
            if simulate:
                target = base / "partitions" / label
                require(target.parent.resolve() == target.parent, "Simulation partition directory cannot be a symlink")
            else:
                target = (Path("/dev/disk/by-partlabel") / label).resolve(strict=True)
                require(target.parent == Path("/dev"), f"Unexpected path to {label}: {target}")
            flags = os.O_RDONLY if args.dry_run else os.O_RDWR
            # Verify the opened inode and then use this descriptor for all I/O.
            fd = os.open(target, flags | os.O_CLOEXEC | os.O_NOFOLLOW)
            device = stack.enter_context(os.fdopen(fd, "rb" if args.dry_run else "r+b", buffering=0))
            info = os.fstat(fd)
            if simulate:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Simulation requires private regular files")
                identity, size = (info.st_dev, info.st_ino), info.st_size
            else:
                require(stat.S_ISBLK(info.st_mode), f"{label} is not a block device")
                identity = info.st_rdev
                sysfs = (Path("/sys/dev/block") / f"{os.major(identity)}:{os.minor(identity)}").resolve(strict=True)
                require("1d84000.ufs" in sysfs.parts, f"{label} is not on the onboard UFS controller")
                attributes = (sysfs / "uevent").read_text().splitlines()
                require("DEVTYPE=partition" in attributes and f"PARTNAME={label}" in attributes, f"Wrong GPT label for {label}")
                require(not any((sysfs / "holders").iterdir()), f"{label} has active block device holders")
                size = struct.unpack("Q", fcntl.ioctl(fd, BLKGETSIZE64, bytes(8)))[0]
            require(identity not in dev_ids and size == expected_size, f"Unexpected partition size or alias for {label}")
            dev_ids.add(identity)
            changed = checksum(device, expected_size) != digest
            prepared.append((label, source, device, expected_size, digest, changed))

        if not args.dry_run:
            # Retain the system closure even if the update is interrupted.
            save_profile(profiles, "zhiyu-pending", system)
        for label, source, device, size, digest, changed in prepared:
            if not changed:
                print(f"{label}: unchanged")
                continue
            if args.dry_run:
                print(f"{label}: would write {size} bytes")
                continue
            print(f"{label}: writing {size} bytes", flush=True)
            device.seek(0)
            for block in blocks(source, size):
                remaining = memoryview(block)
                while remaining:
                    count = device.write(remaining)
                    require(count, f"Short write to {label}")
                    remaining = remaining[count:]
            os.fsync(device.fileno())
            if not simulate:
                fcntl.ioctl(device.fileno(), BLKFLSBUF)
            require(checksum(device, size) == digest, f"Read-back verification failed for {label}")

        if not args.dry_run:
            save_profile(profiles, "zhiyu-boot", system)
            (profiles / "zhiyu-pending").unlink()
            sync_dir(profiles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expect-slot", choices=("a", "b"))
    parser.add_argument("--simulate", type=Path, help="Use private regular files under a test fixture")
    args = parser.parse_args()
    if args.simulate is None and os.geteuid() != 0:
        parser.error("root is required on a real device")
    try:
        flash(args)
    except (OSError, ValueError) as error:
        sys.exit(f"zhiyu-install: {error}. Any interrupted write requires verification before reboot.")


if __name__ == "__main__":
    main()
