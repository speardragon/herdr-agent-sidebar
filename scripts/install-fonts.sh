#!/bin/sh
# Copy the bundled agent icon fonts into the per-user font directory.
set -eu

src="$(cd "$(dirname "$0")/.." && pwd)/fonts"

case "$(uname -s)" in
  Darwin) dest="$HOME/Library/Fonts" ;;
  Linux) dest="${XDG_DATA_HOME:-$HOME/.local/share}/fonts" ;;
  *) echo "Unsupported platform; install fonts from $src manually." >&2; exit 0 ;;
esac

mkdir -p "$dest"
for font in "$src"/*.ttf; do
  name="$(basename "$font")"
  if cmp -s "$font" "$dest/$name"; then
    continue
  fi
  cp "$font" "$dest/$name"
  echo "installed $dest/$name"
done

if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f "$dest" >/dev/null 2>&1 || true
fi
