#!/bin/sh
# Copies the firmware to the board (CIRCUITPY). settings.toml on the board stays as it is.
# Also removes the files of the first version (led_sequences/, boot.py, ...).
#
#     tools/deploy.sh                      # board mounted at /Volumes/CIRCUITPY
#     tools/deploy.sh /media/me/CIRCUITPY
set -e
BOARD="${1:-/Volumes/CIRCUITPY}"
cd "$(dirname "$0")/.."
[ -f "$BOARD/boot_out.txt" ] || { echo "No CircuitPython board at $BOARD"; exit 1; }

# first version: boot.py wrote to the NVM on every start and would wipe the settings
rm -rf "$BOARD/boot.py" "$BOARD/led_sequences" "$BOARD/code_backup.py" "$BOARD/get_device_ip.sh" "$BOARD/__pycache__"

for dir in app scenes web; do
    rm -rf "$BOARD/$dir"
    mkdir "$BOARD/$dir"
    find "$dir" -maxdepth 1 -type f ! -name '.*' ! -name '*.md' -exec cp -X {} "$BOARD/$dir/" \;
done
mkdir -p "$BOARD/lib"
rm -rf "$BOARD/lib/adafruit_httpserver"
cp -RX lib/adafruit_httpserver "$BOARD/lib/"
cp -X code.py "$BOARD/code.py"  # last, so the board restarts with everything in place
sync
echo "Copied to $BOARD"
