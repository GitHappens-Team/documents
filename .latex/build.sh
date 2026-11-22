#!/usr/bin/env bash
# Uso: .latex/build.sh <cartella-documento>   (contiene main.tex)
# Builds a copy of the document with the glossary terms marked (as in CI),
# the resulting pdf is copied to <cartella-documento>/main.pdf.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
doc="$(cd "$1" && pwd)"
export TEXINPUTS=".:$root/.latex//:"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -R "$doc/." "$tmp"
glossary="$root/RTB/documenti_interni/glossario"
# the glossary itself is built from the copy
[ "$doc" = "$glossary" ] && glossary="$tmp"
python3 "$root/.github/scripts/glossary.py" "$glossary" "$tmp"

cd "$tmp"
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
cp main.pdf "$doc/main.pdf"
