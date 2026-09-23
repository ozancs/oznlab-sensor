# Changelog

## v0.9.4

First public release.

- `OZNLAB_PRINT_START` / `OZNLAB_PRINT_END`: the print start and end steps in one line each
- `OZNLAB_TEST TYPE=flow|retract|temp`: the three filament tests from one command
- `OZNLAB_MENU` has four pages: setup, Z and PA, filament tests, bed mesh
- Tap: the contact is fitted against the nozzle depth, accurate at every tap speed and Z acceleration; taps too fast for the data rate are refused
- Defaults follow the guide: `i2c_address: 43`, `tap_adjust_z: 0.04`

- `install.sh` links the module into Klipper and adds the Moonraker update entry
- Clear config errors for the usual mistakes: wrong `i2c_mcu` name, an Eddy on the same bus and address, `z_homing` on a Klipper or toolhead firmware that is too old
- `config/oznlab_sensor.cfg` is safe to `[include]` as it is
- `pa_scale` defaults to 0.175
- Print report opens by itself when PRINT_START has no `OZNLAB_FILAMENT` line
- `OZNLAB_CHECK` warns when clog / runout actions call PAUSE without `[pause_resume]`
- Works with Klipper v0.13.0 (older motion report name)
- An internal error in a sensor callback stops only that feature, never Klipper
- Warns when the clog / runout watch gets no data from the sensor
- A clog / crash PAUSE queued after the print ended is skipped
- Numbers are checked for nan / inf; tap ADJUST limited to -1..1 mm
- Output files (FILE=, LOG=) must end in .csv
- Help texts match the real parameters; clearer error messages
