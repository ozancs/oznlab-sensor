#!/bin/bash
# OznLab Sensor installer
#  - links oznlab_sensor.py into Klipper (so updates of this folder reach Klipper)
#  - hides the link from Klipper's own git status
#  - adds the Moonraker update manager entry (Update button in Mainsail / Fluidd)
#  - writes the [oznlab_sensor hotend] section into printer.cfg (asks which board the coil is on)
# Run it again at any time; it only changes what is missing.
#   BOARD=ebb ./install.sh        no questions: ebb | gen2 | <i2c bus name>
#   MCU=EBBCan ./install.sh       the [mcu ...] the coil is wired to, when there are several
set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KLIPPER="${KLIPPER_PATH:-$HOME/klipper}"
CONFIG="${CONFIG_PATH:-$HOME/printer_data/config}"
MOONRAKER_CONF="$CONFIG/moonraker.conf"

if [ ! -d "$KLIPPER/klippy/extras" ]; then
    echo "Klipper not found in $KLIPPER. Run again with KLIPPER_PATH=/path/to/klipper ./install.sh"
    [ "$(id -u)" = "0" ] && echo "(started with sudo? run it as your normal user: ./install.sh)"
    exit 1
fi

echo "Linking oznlab_sensor.py into $KLIPPER/klippy/extras"
ln -sf "$REPO/oznlab_sensor.py" "$KLIPPER/klippy/extras/oznlab_sensor.py"

EXCLUDE="$KLIPPER/.git/info/exclude"
if [ -f "$EXCLUDE" ] && ! grep -qx "klippy/extras/oznlab_sensor.py" "$EXCLUDE"; then
    echo "klippy/extras/oznlab_sensor.py" >> "$EXCLUDE"
fi

ORIGIN="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
if [ -z "$ORIGIN" ]; then
    echo "Not a git clone: skipping the update manager entry."
elif [ ! -f "$MOONRAKER_CONF" ]; then
    echo "No moonraker.conf in $CONFIG: skipping the update manager entry."
    for d in "$HOME"/printer_*_data/config; do
        [ -f "$d/moonraker.conf" ] && echo "  Found $d - run again with: CONFIG_PATH=$d ./install.sh"
    done
elif grep -q "^\[update_manager oznlab_sensor\]" "$MOONRAKER_CONF"; then
    echo "Update manager entry already there."
else
    echo "Adding the update manager entry to moonraker.conf"
    cat >> "$MOONRAKER_CONF" <<CONF

[update_manager oznlab_sensor]
type: git_repo
channel: stable
path: $REPO
origin: $ORIGIN
primary_branch: main
managed_services: klipper
CONF
    sudo systemctl restart moonraker || echo "Could not restart Moonraker - restart it from Mainsail / Fluidd"
fi

echo "Config"
if CONFIG_PATH="$CONFIG" python3 "$REPO/configure.py"; then
    CFG_OK=1
else
    CFG_OK=0
fi

echo "Restarting Klipper"
sudo systemctl restart klipper || echo "Could not restart the klipper service - use RESTART in the console"
if [ "$CFG_OK" = 1 ]; then
    echo "Done. Next: OZNLAB_SETUP in the console, one step per call."
else
    echo "Done, but the config section is not written yet (see above). Then: OZNLAB_SETUP in the console."
fi
