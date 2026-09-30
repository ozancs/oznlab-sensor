# OznLab Sensor

Klipper module for the OznLab Sensor: an LDC1612 eddy coil that watches the hotend.
It measures the nozzle touching the bed and the melt pressure, and turns that into
a Z offset, pressure advance and a clog / runout watch on every print.

Step by step guide: https://ozancs.github.io/oznlab-sensor/

## Hardware

- Board files (Gerber, BOM, CPL for JLCPCB): https://ozancsahin.gumroad.com/l/oznlabsensor
- The coil PCB is made for the RX toolhead: https://www.printables.com/model/1779906-rx-toolhead-v5-using-bambu-h2sa1-gear-h2d-hotend
  The version with the sensor mount will be published there.
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

It asks which board the coil is wired to, writes the `[oznlab_sensor hotend]` section
into `printer.cfg` and restarts Klipper (`BOARD=ebb ./install.sh` skips the question).
`config/oznlab_sensor.cfg` lists every option. Then run `OZNLAB_SETUP` (or `OZNLAB_MENU`)
in the console, one step per call.

In PRINT_START, in place of the line that heats the nozzle:

```
OZNLAB_PRINT_START EXTRUDER={extruder}
```

(tap at 150 C with a clean tip, heat, filament type from the gcode file, PA in the air;
a nozzle wipe macro goes on the line as `BRUSH=`, a purge bucket into the config as
`pa_x` / `pa_y` / `pa_z`, see guide 5.1)

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
