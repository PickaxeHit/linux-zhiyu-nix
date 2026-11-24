#!/bin/bash
# Emit an XBPS binary package from the common stage without xbps-src.
set -euo pipefail
stage=$(realpath "${1:?stage}")
out=$(realpath -m "${2:?output}")
name=${PKG_NAME:?}
version=$(printf '%s' "${PKG_VERSION:?}" | tr '-+' '.p')
revision=${PKG_REVISION:-1}
[[ $revision =~ ^[1-9][0-9]*$ ]] || { echo 'XBPS revision must be a positive integer' >&2; exit 1; }
[[ $(xbps-uhelper arch) == aarch64 ]] || exit 1
mkdir -p "$out"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -a "$stage/." "$work/"
# Boot images are not automatically flashed on Void. Use the supplied updater explicitly.
if [[ $name == hexagonrpc ]]; then
    install -m755 scripts/void/hexagonrpc.INSTALL "$work/INSTALL"
fi
meta=$(python3 scripts/void/elf-deps.py "$work" && printf "END\n")
mapfile -t fields <<< "$meta"
args=(-A aarch64 -n "${name}-${version}_${revision}"
      -s "${PKG_DESC:-$name}" -l "${PKG_LICENSE:?}" -m 'Zhiyu CI <ci@localhost>'
      -H 'https://github.com/PickaxeHit/linux-zhiyu'
      --source-revisions "$(git rev-parse HEAD)")
dependencies="${PKG_XBPS_DEPENDS:-} ${fields[0]:-}"
[[ -z ${dependencies// /} ]] || args+=(-D "$dependencies")
[[ -z ${PKG_XBPS_PROVIDES:-} ]] || args+=(-P "$PKG_XBPS_PROVIDES")
[[ -z ${PKG_XBPS_REPLACES:-} ]] || args+=(-R "$PKG_XBPS_REPLACES")
[[ -z ${fields[1]:-} ]] || args+=(--shlib-provides "${fields[1]}")
[[ -z ${fields[2]:-} ]] || args+=(--shlib-requires "${fields[2]}")
(cd "$out" && xbps-create "${args[@]}" "$work")
