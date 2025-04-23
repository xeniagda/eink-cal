{
  description = "A bare minimum flake";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";

    esp-idf = {
      url = "github:mirrexagon/nixpkgs-esp-dev";
      inputs.flake-utils.follows = "flake-utils";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, esp-idf, flake-utils }:
    flake-utils.lib.eachDefaultSystem (sys:
      let pkgs = import nixpkgs { system = sys; };
          python = pkgs.python313.withPackages (ps: [ ps.ipython ps.numpy ps.pillow ps.requests ps.tqdm ps.caldav ps.toml ]);
      in rec {
        devShells.esp = esp-idf.outputs.devShells.${sys}.esp-idf-full;
        devShells.py = pkgs.mkShell {
          packages = [ python pkgs.usbutils ];
        };
        devShells.default = pkgs.mkShell {
          inputsFrom = [ devShells.esp devShells.py ];
        };

        packages.cal-render = pkgs.stdenv.mkDerivation (self: {
          name = "cal-render";
          src = ./cal_render ;

          buildPhase = ''
            mkdir -p $out/bin
            cp -r $src/* $out/bin/
            cat > $out/bin/cal-render <<'EOF'
            #!/bin/sh
            ${python}/bin/python "$(dirname "$0")"/main.py "$@"
            EOF
            chmod a+x $out/bin/cal-render
          '';
        });
      }
    );
}
