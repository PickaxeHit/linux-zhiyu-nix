{
  pkgs,
  sources,
  kernel,
  firmware,
  keymint,
}:
let
  inherit (pkgs) stdenv;
  static = [
    stdenv.cc.libc
    stdenv.cc.libc.static
  ];
  staticTool =
    name: source: script: vars: inputs:
    stdenv.mkDerivation {
      pname = "zhiyu-${name}";
      inherit (source) version src;
      nativeBuildInputs = [ pkgs.file ] ++ inputs;
      buildInputs = static;
      buildCommand = ''
        mkdir -p src/initramfs-src "$out/bin"
        cp ${script} src/initramfs-src/build.sh
        export CROSS_COMPILE="" JOBS="$NIX_BUILD_CORES"
        ${vars}
        bash src/initramfs-src/build.sh
      '';
    };
  busybox =
    staticTool "busybox" sources.busybox ../initramfs-src/build-busybox.sh
      ''
        export BB_SRC=${sources.busybox.src} BB_OUT="$out/bin/busybox"
      ''
      [
        pkgs.flex
        pkgs.bison
      ];
  fsck-f2fs =
    staticTool "fsck-f2fs" sources.f2fs-tools ../initramfs-src/build-fsck.sh
      ''
        export F2FS_SRC=${sources.f2fs-tools.src} F2FS_OUT="$out/bin/fsck.f2fs"
      ''
      [
        pkgs.autoconf
        pkgs.automake
        pkgs.libtool
        pkgs.pkg-config
      ];
  static-helpers = stdenv.mkDerivation {
    name = "zhiyu-static-helpers";
    buildInputs = static;
    buildCommand = ''
      mkdir -p "$out/bin"
      $CC -static -Os -Wall -Wextra -Werror ${../initramfs-src/src/btaddr.c} -o "$out/bin/btaddr"
      $CC -static -Os -Wall -Wextra -Werror ${../initramfs-src/src/charger.c} -o "$out/bin/charger"
      $CC -static -Os -Wall -Wextra -Werror ${./boot-select.c} -o "$out/bin/zhiyu-boot-select"
    '';
  };
  tree = pkgs.lib.fileset.toSource {
    root = ../initramfs-src;
    fileset = pkgs.lib.fileset.unions [
      ../initramfs-src/build.sh
      ../initramfs-src/fs
      ../initramfs-src/busybox-applets.txt
      ../initramfs-src/modules.tsv
      ../initramfs-src/order-modules.py
    ];
  };
  initramfs =
    pkgs.runCommand "zhiyu-initramfs-${kernel.modDirVersion}"
      {
        nativeBuildInputs = with pkgs; [
          cpio
          kmod
          file
          python3
          gzip
          binutils
        ];
        disallowedReferences = [
          busybox
          fsck-f2fs
          static-helpers
          keymint
          firmware
          kernel
          kernel.modules
        ];
      }
      ''
        mkdir -p "$out" source/initramfs-src
        cp -R ${tree}/. source/initramfs-src/
        export KS=${kernel} VER=${kernel.modDirVersion}
        export MODULES_DIR=${kernel.modules}/lib/modules/$VER/kernel SYSTEM_MAP=${kernel}/System.map
        export BB_OUT=${busybox}/bin/busybox FSCK_OUT=${fsck-f2fs}/bin/fsck.f2fs
        export STATIC_HELPERS=${static-helpers} KEYMINT_TOOLS=${keymint}
        export FW_SRC=${firmware} FW_TREE=${firmware}/lib/firmware
        PREBUILT=1 STAGE_PARENT="$PWD" OUT="$PWD/stage" bash source/initramfs-src/build.sh

        python3 ${./verify-initramfs.py} stage "$VER"
        find stage -exec touch -h -d @1 {} +
        (cd stage && find . -print0 | LC_ALL=C sort -z |
          cpio --null -o --format=newc --owner=0:0 --reproducible --quiet |
          gzip -n -9) > "$out/initramfs.cpio.gz"
      '';
in
{
  inherit
    busybox
    fsck-f2fs
    static-helpers
    initramfs
    ;
}
