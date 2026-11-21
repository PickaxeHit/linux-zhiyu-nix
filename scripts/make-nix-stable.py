#!/usr/bin/env python3
"""Export the buildable Nix source tree and its dependency revisions from a commit."""
import argparse
from pathlib import Path
import json
import re
import subprocess
import tarfile
from tempfile import TemporaryFile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "LICENSE.md", "licenses", "flake.nix", "flake.lock", "nix",
    "deps/deps.json", "deps/nix-sources.json", "avb-test-key.pem",
    "configs/modprobe.d/99-zhiyu-no-trace.conf", "dts/lenovo-zhiyu.dts",
    "initramfs-src/build.sh", "initramfs-src/build-busybox.sh",
    "initramfs-src/build-fsck.sh", "initramfs-src/busybox-applets.txt",
    "initramfs-src/fs", "initramfs-src/modules.tsv",
    "initramfs-src/order-modules.py", "initramfs-src/src", "initramfs-src/tplg",
    "keymint/build.sh", "keymint/stage-initramfs.sh", "keymint/idlc.Cargo.lock",
    "keymint/rpmb_proxy.c", "keymint/time_main.c", "keymint/unlock_metadata.c",
    "sensors/Makefile", "sensors/sensord.c", "scripts/alsa-ucm2",
    "scripts/60-persistent-v4l.rules", "scripts/90-dma-heap.rules",
    "scripts/90-fastrpc.rules", "scripts/91-flash-led.rules", "scripts/verify-images.sh",
    "mkbootimg", "mkvendorbootimg", "mkinitbootimg", "mkvbmetaimg",
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def metadata(repo, commit, lock, deps, flake):
    rows = [("BSP", "主仓", f"https://github.com/{repo}", "", commit, "")]
    for name in sorted(lock.keys() | deps.keys()):
        entry = lock[name] if name in lock else deps[name]
        ref = entry.get("rev") or entry["sha256"]
        label = entry.get("version") or deps.get(name, {}).get("tag", "")
        scope = "Nix 源码锁" if name in lock else "传统构建"
        rows.append((name, scope, entry["url"], label, ref, entry.get("hash", "")))
    for name, node in sorted(flake["nodes"].items()):
        if entry := node.get("locked"):
            url = entry.get("url")
            if entry["type"] == "github":
                url = f"https://github.com/{entry['owner']}/{entry['repo']}"
            rows.append((f"flake/{name}", "Flake 锁", url or entry["type"], node.get("original", {}).get("ref", ""),
                         entry.get("rev", ""), entry.get("narHash", "")))
    lines = [
        "# 源码版本表",
        "",
        "由 CI 根据主仓提交、源码锁和 Flake 锁生成。Rust crate 版本及校验和见",
        "[`keymint/idlc.Cargo.lock`](keymint/idlc.Cargo.lock)。",
        "",
        "| 组件 | 锁定来源 | 上游 | 版本标签 | 完整 Git 提交或归档 SHA-256 | Nix 源码哈希 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend("| " + " | ".join(str(v).replace("|", r"\|") for v in row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new directory for the exported source")
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--repository", default="PickaxeHit/linux-zhiyu-next")
    args = parser.parse_args()
    commit = git("rev-parse", "--verify", f"{args.revision}^{{commit}}").strip()
    lock = json.loads(git("show", f"{commit}:deps/nix-sources.json"))
    deps = json.loads(git("show", f"{commit}:deps/deps.json"))
    flake = json.loads(git("show", f"{commit}:flake.lock"))
    version = re.match(r"[0-9]+\.[0-9]+", lock["kernel-source"]["version"])
    if not version:
        parser.error("kernel source lock has an invalid version")
    readme = git("show", f"{commit}:README.md")
    guide = readme.split("### Nix / NixOS\n", 1)[1].split("#### 更新源码锁\n", 1)[0]
    guide = guide.replace("github:PickaxeHit/linux-zhiyu-next/nix-stable", f"github:{args.repository}/nix-stable")
    guide = guide.replace("上文的 Android 底包和 fastboot 流程",
                          f"[主仓的 Android 底包和 fastboot 流程](https://github.com/{args.repository}#食用方法)")
    with TemporaryFile() as archive:
        subprocess.run(["git", "archive", commit, "--", *FILES,
                        f"configs/linux-{version[0]}-zhiyu.config"], cwd=ROOT, stdout=archive, check=True)
        archive.seek(0)
        args.destination.mkdir(parents=True)
        with tarfile.open(fileobj=archive) as stream:
            stream.extractall(args.destination, filter="data")
    (args.destination / "README.md").write_text(
        "# Zhiyu Nix BSP\n\n"
        f"由 [主仓提交 `{commit[:12]}`](https://github.com/{args.repository}/commit/{commit}) 自动生成。"
        "依赖明细见 [源码版本表](SOURCE-COMMITS.md)。\n"
        + guide, encoding="utf-8",
    )
    (args.destination / "SOURCE-COMMITS.md").write_text(
        metadata(args.repository, commit, lock, deps, flake), encoding="utf-8",
    )


if __name__ == "__main__":
    main()
