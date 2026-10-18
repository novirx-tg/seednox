{
  description = "Seednox - Secure Encrypted Cold-Storage Telegram Bot & Desktop Vault (Reproducible Build)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "seednox";
          version = "1.0.3";
          src = self;

          nativeBuildInputs = [
            python
            pkgs.gdb
          ];

          buildPhase = ''
            export SOURCE_DATE_EPOCH=1700000000
            export PYTHONHASHSEED=0
            export LC_ALL=C.UTF-8
            export LANG=C.UTF-8
            export TZ=UTC

            ${python}/bin/python scripts/reproducible_pack.py \
              --src . \
              --out dist/seednox-1.0.3-reproducible.tar.gz \
              --epoch 1700000000

            ${python}/bin/python scripts/reproducible_pack.py \
              --src . \
              --out dist/seednox-1.0.3-reproducible.zip \
              --epoch 1700000000
          '';

          installPhase = ''
            mkdir -p $out/dist
            cp dist/seednox-1.0.3-reproducible.* $out/dist/
            cd $out/dist && sha256sum * > SHA256SUMS
          '';
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pkgs.gdb
          ];

          shellHook = ''
            echo "Seednox 1.0.3 Reproducible Nix Environment Active"
            export SOURCE_DATE_EPOCH=1700000000
            export PYTHONHASHSEED=0
          '';
        };
      }
    );
}
