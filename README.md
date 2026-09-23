# OznLab Sensor

Klipper module for the OznLab Sensor: an LDC1612 eddy coil that watches the hotend.
It measures the nozzle touching the bed and the melt pressure, and turns that into
a Z offset, pressure advance and a clog / runout watch on every print.

Step by step guide: https://ozancs.github.io/oznlab-sensor/

## Hardware

- Board files (Gerber, BOM, CPL for JLCPCB): https://ozancsahin.gumroad.com/l/oznlabsensor
- The coil PCB is made for the RX toolhead. The version with the sensor mount will be published on
  the designer's MakerWorld page: https://makerworld.com/en/@raidycv
- Questions, other toolheads: https://discord.com/invite/MSKvKRJp8X

## Requirements

- Klipper v0.13.0 or newer, Mainsail or Fluidd, SSH access.
- Z homing with the nozzle (optional, `z_homing: 1`) needs a Klipper from late May 2026
  or newer, on the Pi and flashed to the toolhead board.

## Install

```
cd ~
git clone https://github.com/ozancs/oznlab-sensor.git
cd oznlab-sensor
./install.sh
```

Run it as your normal user, not with `sudo`. Several printers on one Pi:
`CONFIG_PATH=~/printer_1_data/config ./install.sh`.

Then add the `[oznlab_sensor hotend]` section to `printer.cfg`. `config/oznlab_sensor.cfg`
has every option and is safe to copy next to `printer.cfg` and `[include]`. Restart
Klipper and run `OZNLAB_SETUP` (or `OZNLAB_MENU`) in the console.

In PRINT_START, after heating and before the prime line:

```
OZNLAB_PRINT_START FILAMENT="{params.FILAMENT|default('')}" PA_X=<purge x> PA_Y=<purge y>
```

and `OZNLAB_MONITOR` after the prime line, `OZNLAB_PRINT_END` in PRINT_END and CANCEL_PRINT.

## Updates

`install.sh` adds this to `moonraker.conf`, so Mainsail and Fluidd show an
Update button when a new version is released:

```
[update_manager oznlab_sensor]
type: git_repo
channel: stable
path: ~/oznlab-sensor
origin: https://github.com/ozancs/oznlab-sensor.git
primary_branch: main
managed_services: klipper
```

## License

GNU GPLv3, see `LICENSE`.
