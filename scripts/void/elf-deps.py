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
for path in stage.rglob("*"):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open("rb") as f:
        hdr = f.read(20)
    if hdr[:6] != b"\x7fELF\x02\x01" or int.from_bytes(hdr[18:20], "little") != 183:
        continue
    dynamic = run("readelf", "-d", str(path))
    needed.update(re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", dynamic))
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
    sys.exit("Unresolved Void runtime SONAMEs: " + " ".join(sorted(unresolved)))
print(" ".join(sorted(set(providers.values()))))
print(" ".join(sorted(public)))
print(" ".join(sorted(needed)))
