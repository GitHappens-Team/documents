#!/usr/bin/env bash
# Uso: .latex/build.sh <cartella-documento>   (contiene main.tex)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
doc="$(cd "$1" && pwd)"
export TEXINPUTS="$root/.latex//:"
cd "$doc"
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
