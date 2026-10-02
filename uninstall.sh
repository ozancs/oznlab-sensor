#!/bin/bash
# OznLab Sensor uninstaller: the reverse of install.sh.
#  - removes the link in Klipper's extras folder and its entry in Klipper's git exclude list
#  - removes the [update_manager oznlab_sensor] block from moonraker.conf
#  - restarts Moonraker and Klipper
# It does not touch printer.cfg: delete the [oznlab_sensor hotend] section (and the lines the module
# saved under SAVE_CONFIG) by hand, and take the OZNLAB_ lines out of your PRINT_START / PRINT_END.
# This folder stays; delete it afterwards with: rm -rf ~/oznlab-sensor
set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KLIPPER="${KLIPPER_PATH:-$HOME/klipper}"
CONFIG="${CONFIG_PATH:-$HOME/printer_data/config}"
MOONRAKER_CONF="$CONFIG/moonraker.conf"

LINK="$KLIPPER/klippy/extras/oznlab_sensor.py"
if [ -L "$LINK" ] || [ -f "$LINK" ]; then
    echo "Removing $LINK"
    rm -f "$LINK"
else
    echo "No oznlab_sensor.py in $KLIPPER/klippy/extras"
fi

EXCLUDE="$KLIPPER/.git/info/exclude"
if [ -f "$EXCLUDE" ] && grep -qx "klippy/extras/oznlab_sensor.py" "$EXCLUDE"; then
    sed -i '\#^klippy/extras/oznlab_sensor.py$#d' "$EXCLUDE"
fi

if [ -f "$MOONRAKER_CONF" ] && grep -q "^\[update_manager oznlab_sensor\]" "$MOONRAKER_CONF"; then
    echo "Removing the update manager entry from moonraker.conf"
    cp "$MOONRAKER_CONF" "$MOONRAKER_CONF.oznlab-backup"
    # the block runs from its header to the next [section] or the end of the file
    awk 'BEGIN{skip=0} /^\[update_manager oznlab_sensor\]/{skip=1; next} /^\[/{skip=0} !skip' "$MOONRAKER_CONF" > "$MOONRAKER_CONF.tmp"
    mv "$MOONRAKER_CONF.tmp" "$MOONRAKER_CONF"
    sudo systemctl restart moonraker || echo "Could not restart Moonraker - restart it from Mainsail / Fluidd"
fi

if grep -q "^\[oznlab_sensor" "$CONFIG/printer.cfg" 2>/dev/null; then
    echo
    echo "printer.cfg still has the [oznlab_sensor ...] section. Klipper will not start until it is gone:"
    echo "  delete that section, the oznlab lines under SAVE_CONFIG at the end of the file,"
    echo "  and the OZNLAB_ lines in PRINT_START / PRINT_END, then: sudo systemctl restart klipper"
    echo "(not restarting Klipper now)"
else
    echo "Restarting Klipper"
    sudo systemctl restart klipper || echo "Could not restart the klipper service - use RESTART in the console"
    echo "Done. This folder can go: rm -rf $REPO"
fi
