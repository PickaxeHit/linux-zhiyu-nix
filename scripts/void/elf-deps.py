#!/usr/bin/env python3
"""Emit three lines: runtime package patterns, public SONAMEs, external SONAMEs."""
import os
import re
import subprocess
import sys
from pathlib import Path

def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()

stage = Path(sys.argv[1])
provided, public, needed = set(), set(), set()
required_by = {}
# Firmware and kernel modules are not loaded by the Linux userspace dynamic
# linker. Qualcomm's ARM64 TrustZone firmware can have its own DT_NEEDED
# entries (e.g. libcmnlib.so); never turn those into XBPS dependencies.
non_userspace = (
    Path("usr/lib/firmware"), Path("lib/firmware"),
    Path("usr/lib/modules"), Path("lib/modules"),
    Path("usr/lib/linux-zhiyu/images"),
)
for path in stage.rglob("*"):
    if path.is_symlink() or not path.is_file():
        continue
    relative = path.relative_to(stage)
    if any(relative.is_relative_to(prefix) for prefix in non_userspace):
        continue
    with path.open("rb") as f:
        hdr = f.read(20)
    if hdr[:6] != b"\x7fELF\x02\x01" or int.from_bytes(hdr[18:20], "little") != 183:
        continue
    dynamic = run("readelf", "-d", str(path))
    for soname in re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", dynamic):
        needed.add(soname)
        required_by.setdefault(soname, set()).add(str(relative))
    sonames = set(re.findall(r"\(SONAME\).*?\[([^\]]+)\]", dynamic))
    provided.update(sonames)
    if path.parent == stage / "usr/lib":
        public.update(sonames)

needed -= provided
providers = {}
# QRTR is built from pinned source alongside sensh, not installed in the build container.
if os.environ.get("PKG_XBPS_QRTR") == "1" and "libqrtr.so.1" in needed:
    providers["libqrtr.so.1"] = "zhiyu-qrtr>=1.2"
unresolved = needed - providers.keys()
if unresolved:
    for line in run("xbps-query", "-l").splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] != "ii":
            continue
        pkgver = fields[1]
        try:
            libs = set(run("xbps-query", "-p", "shlib-provides", pkgver).split())
        except subprocess.CalledProcessError:
            continue
        found = unresolved & libs
        if found:
            pkg = run("xbps-uhelper", "getpkgname", pkgver)
            ver = pkgver[len(pkg) + 1:]
            for soname in found:
                providers[soname] = f"{pkg}>={ver}"
            unresolved -= found
        if not unresolved:
            break
if unresolved:
    for soname in sorted(unresolved):
        print(f"Unresolved {soname}: {', '.join(sorted(required_by[soname]))}", file=sys.stderr)
    sys.exit("Unresolved Void runtime SONAMEs: " + " ".join(sorted(unresolved)))
print(" ".join(sorted(set(providers.values()))))
print(" ".join(sorted(public)))
print(" ".join(sorted(needed)))
