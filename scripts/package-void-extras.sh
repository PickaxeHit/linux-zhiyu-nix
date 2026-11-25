#!/bin/bash
# Build pinned dependencies that Void does not provide and the Qualcomm VA backend.
set -euo pipefail
cd "$(dirname "$0")/.."
build="$PWD/$BUILD_ROOT"
stage="$PWD/$STAGE_ROOT"
mkdir -p "$build" "$stage"
for n in zhiyu-qrtr sensh hexagonrpc qcom-va-driver qbootctl; do rm -rf "$build/$n" "$stage/$n"; done
qmic=$(python3 scripts/deps.py path qmic)
make -C "$qmic" -j"${JOBS:-1}"
install -Dm755 "$qmic/qmic" "$build/tools/qmic"
export PATH="$build/tools:$PATH"

qrtr=$(python3 scripts/deps.py path qrtr)
meson setup "$build/zhiyu-qrtr" "$qrtr" --buildtype=release --prefix=/usr --libdir=lib
meson compile -C "$build/zhiyu-qrtr" -j"${JOBS:-1}"
DESTDIR="$stage/zhiyu-qrtr" meson install -C "$build/zhiyu-qrtr" --no-rebuild
for license in "$qrtr"/LICENSE* "$qrtr"/COPYING*; do
    [[ -f "$license" ]] || continue
    install -Dm644 "$license" "$stage/zhiyu-qrtr/usr/share/licenses/zhiyu-qrtr/${license##*/}"
done
PKG_NAME=zhiyu-qrtr PKG_VERSION=1.2 PKG_LICENSE=BSD-3-Clause \
    PKG_DESC='Qualcomm QRTR IPC library and utilities' \
    scripts/emit-package.sh "$stage/zhiyu-qrtr" "$PACKAGE_OUT"

sensh=$(python3 scripts/deps.py path sensh)
qrtr_usr="$stage/zhiyu-qrtr/usr"
# Use the staged QRTR headers and libraries, with no runtime path to CI checkout.
PKG_CONFIG_PATH="$qrtr_usr/lib/pkgconfig" \
    CFLAGS="-I$qrtr_usr/include" LDFLAGS="-L$qrtr_usr/lib" \
    meson setup "$build/sensh" "$sensh" --buildtype=release --prefix=/usr --libdir=lib
meson compile -C "$build/sensh" -j"${JOBS:-1}"
DESTDIR="$stage/sensh" meson install -C "$build/sensh" --no-rebuild
install -Dm644 "$sensh/COPYING" "$stage/sensh/usr/share/licenses/sensh/COPYING"
PKG_NAME=sensh PKG_VERSION=2.1.1 PKG_LICENSE=GPL-3.0-or-later \
    PKG_DESC='Qualcomm Sensor Core diagnostic shell' PKG_XBPS_QRTR=1 \
    scripts/emit-package.sh "$stage/sensh" "$PACKAGE_OUT"

hex=$(python3 scripts/deps.py path hexagonrpc)
meson setup "$build/hexagonrpc" "$hex" --buildtype=release --prefix=/usr --libdir=lib
meson compile -C "$build/hexagonrpc" -j"${JOBS:-1}"
DESTDIR="$stage/hexagonrpc" meson install -C "$build/hexagonrpc" --no-rebuild
rm -rf "$stage/hexagonrpc/usr/lib/systemd"
for service in hexagonrpcd-adsp-rootpd hexagonrpcd-adsp-sensorspd; do
    install -Dm755 scripts/void/"$service.run" "$stage/hexagonrpc/etc/sv/$service/run"
done
install -Dm644 "$hex/COPYING" "$stage/hexagonrpc/usr/share/licenses/hexagonrpc/COPYING"
install -m644 licenses/LGPL-3.0.txt "$stage/hexagonrpc/usr/share/licenses/hexagonrpc/"
PKG_NAME=hexagonrpc PKG_VERSION=0.5.0 PKG_LICENSE='GPL-3.0-or-later AND LGPL-3.0-or-later' \
    PKG_DESC='Qualcomm Hexagon FastRPC daemon and libraries' \
    PKG_XBPS_DEPENDS='shadow>=0 runit>=0 kmod>=0 coreutils>=0' \
    scripts/emit-package.sh "$stage/hexagonrpc" "$PACKAGE_OUT"

va=$(python3 scripts/deps.py path qcom-va-driver)
meson setup "$build/qcom-va-driver" "$va" --buildtype=release --prefix=/usr --libdir=lib \
    -Dgpu_copy=enabled -Dcdsp_vpp=disabled -Dvulkan_vpp=disabled
meson compile -C "$build/qcom-va-driver" -j"${JOBS:-1}"
DESTDIR="$stage/qcom-va-driver" meson install -C "$build/qcom-va-driver" --no-rebuild
# Upstream names the backend v4l2 and supplies the msm alias. Retain the
# qcom alias used by existing Zhiyu desktop configurations as well.
dri="$stage/qcom-va-driver/usr/lib/dri"
test -f "$dri/v4l2_drv_video.so"
test -f "$dri/msm_drv_video.so"
if [[ ! -e "$dri/qcom_drv_video.so" && ! -L "$dri/qcom_drv_video.so" ]]; then
    ln -s v4l2_drv_video.so "$dri/qcom_drv_video.so"
fi
test -f "$dri/qcom_drv_video.so"
for license in "$va"/LICENSE* "$va"/COPYING*; do
    [[ -f "$license" ]] || continue
    install -Dm644 "$license" "$stage/qcom-va-driver/usr/share/licenses/qcom-va-driver/${license##*/}"
done
PKG_NAME=qcom-va-driver PKG_VERSION=1.1.1 PKG_LICENSE=MIT \
    PKG_DESC='Qualcomm Iris V4L2 VA-API driver' \
    scripts/emit-package.sh "$stage/qcom-va-driver" "$PACKAGE_OUT"


# Keep qbootctl in the signed BSP repo instead of rebuilding in each rootfs.
# The source revision is the same one used by the existing rootfs builder.
qboot=$(python3 scripts/deps.py path qbootctl)
meson setup "$build/qbootctl" "$qboot" --buildtype=release --prefix=/usr --libdir=lib
meson compile -C "$build/qbootctl" -j"${JOBS:-1}"
DESTDIR="$stage/qbootctl" meson install -C "$build/qbootctl" --no-rebuild
install -Dm644 "$qboot/LICENSE" "$stage/qbootctl/usr/share/licenses/qbootctl/LICENSE"
test -x "$stage/qbootctl/usr/bin/qbootctl"
PKG_NAME=qbootctl PKG_VERSION=0.0.20250324 PKG_LICENSE=GPL-3.0-or-later \
    PKG_DESC='Qualcomm boot slot controller' \
    scripts/emit-package.sh "$stage/qbootctl" "$PACKAGE_OUT"
