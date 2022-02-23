let
  pkgs = import (builtins.fetchTarball {
    name = "nixpkgs-unstable-2021-02-15";
    url = "https://github.com/nixos/nixpkgs/archive/1882c6b7368fd284ad01b0a5b5601ef136321292.tar.gz";
    sha256 = "0zg7ak2mcmwzi2kg29g4v9fvbvs0viykjsg2pwaphm1fi13s7s0i";
  }) {};
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    (python310.withPackages (ps: with ps; [
    ]))
  ];
}
