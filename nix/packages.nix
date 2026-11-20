{
  pkgs,
  sources,
  cameraBase,
}:
let
  kernel = pkgs.callPackage ./kernel.nix {
    source = sources.kernel-source;
    kernelPatches = [ ];
  };
  hardware = import ./hardware.nix { inherit pkgs sources; };
  keymint = import ./keymint.nix { inherit pkgs sources; };
  mkInitramfs =
    kernel:
    import ./initramfs.nix {
      inherit pkgs sources kernel;
      inherit (hardware) firmware;
      inherit (keymint) keymint;
    };
  initramfs = mkInitramfs kernel;
  dtb = import ./dtb.nix {
    inherit pkgs;
    source = sources.kernel-source;
  };
  mkImages =
    kernel:
    import ./images.nix {
      inherit
        pkgs
        sources
        kernel
        dtb
        ;
      inherit (mkInitramfs kernel) initramfs;
    };
  defaultImages = (mkImages kernel { }).packages;
  packages =
    hardware
    // keymint
    // initramfs
    // defaultImages
    // {
      inherit kernel dtb;
      libcamera-0_7 = import ./libcamera.nix {
        base = cameraBase;
        source = sources."libcamera/0.7";
      };
      libcamera-0_8 = import ./libcamera.nix {
        base = cameraBase;
        source = sources."libcamera/0.8";
      };
      flasher = pkgs.writeShellApplication {
        name = "zhiyu-install";
        text = ''
          exec ${pkgs.python3}/bin/python3 ${./flash.py} "$@"
        '';
      };
      default = defaultImages.zhiyu-images;
    };
in
{
  inherit packages mkInitramfs mkImages;
}
