# Minimal example for an ext4 root on the first microSD partition.
# Import the BSP module alongside this file in your own NixOS configuration.
{
  zhiyu.enable = true;
  networking.hostName = "zhiyu";
  boot.kernelParams = [ "zhiyu.root=sd" ];
  fileSystems."/" = {
    device = "/dev/mmcblk0p1";
    fsType = "ext4";
  };
  system.stateVersion = "26.05";
}
