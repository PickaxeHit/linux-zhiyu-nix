{
  lib,
  linuxManualConfig,
  python3,
  source,
  features ? { },
  kernelPatches ? [ ],
  randstructSeed ? "",
}:
let
  inherit (source) src version;
  configfile = ../configs + "/linux-${lib.versions.majorMinor version}-zhiyu.config";
  localVersion = builtins.head (
    lib.filter (line: line != null) (
      map (builtins.match ''CONFIG_LOCALVERSION="(.*)"'') (
        lib.splitString "\n" (builtins.readFile configfile)
      )
    )
  );
in
(linuxManualConfig {
  inherit
    src
    version
    configfile
    features
    kernelPatches
    ;
  # Keep the fixed default seed unless randstruct is actually enabled.
  randstructSeed =
    if lib.hasInfix "\nCONFIG_RANDSTRUCT_NONE=y\n" (builtins.readFile configfile) then
      ""
    else
      randstructSeed;
  modDirVersion = version + builtins.head localVersion;
  buildDTBs = false;
  extraMeta.platforms = [ "aarch64-linux" ];
}).overrideAttrs
  (old: {
    pname = "linux-zhiyu";
    makeFlags = old.makeFlags ++ [ "LOCALVERSION=" ];
    configurePhase = builtins.replaceStrings [ " oldconfig" ] [ " olddefconfig" ] old.configurePhase;
    nativeBuildInputs = old.nativeBuildInputs ++ [ python3 ];
    postConfigure = (old.postConfigure or "") + ''
      python3 ${./check-kconfig.py} ${configfile} "$buildRoot/.config"
    '';
  })
