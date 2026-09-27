# Changelog

## v0.9.9

- New default `pa_method: auto`: the first PA measurement fits every run with decay, and with fast when decay does not fit, keeps the method with more good runs and saves it (`SAVE_CONFIG` keeps it). Tested on recorded data: a slow hotend picks decay, a hotend whose pressure drops in 15 to 20 ms picks fast. A `pa_method` line in your config is left alone
- `OZNLAB_PA_SCALE` also stores the method it was measured with, so a scale and its method always match
- "no reliable measurement" now lists the reasons in the same line, for example `(noisy fall x3, no pressure signal x2)`, without VERBOSE=1
- The fast fit lets Klipper's other timers run while it computes
- `OZNLAB_HELP`: words in [ ] are optional, type them without the brackets
- Guide: nozzle homing config in one block, "home first (G28)" in the fix table, redo the PA steps after a nozzle or hotend change

## v0.9.8

- `pa_method: decay` is now the default: pressure advance is measured from the pressure fall after the extruder stops. On both test printers it was repeatable within about 6 %, needs no primed melt zone and ignores gear slack at the start. The old method stays available as `pa_method: rise`
- If you tuned `pa_scale` with v0.9.7 or older: measure once with `OZNLAB_CALIBRATE_PA` and run `OZNLAB_PA_SCALE PATTERN_PA=<your pattern value>` again (or add `pa_method: rise` to keep the old behaviour)
- A rejected PA run says why (creeping rise, rise that overshoots, noisy rise or fall)
- New `pa_method: fast`: uses only the fast part of the pressure fall. For large nozzles (0.6 mm and up) and runny filaments, where the melt pressure drops in 10 to 30 ms and a slow tail follows. Tested on recorded data from a 0.6 mm nozzle (PETG at 3 mm/s, PLA at 6 mm/s, data_rate 100)
- PA runs whose drop is faster than the sensor's data_rate, or whose pressure step is too small, now say so

## v0.9.7

- New option `pa_method: decay` (and `METHOD=decay` on `OZNLAB_CALIBRATE_PA`): measures the PA time constant from the pressure fall after the extruder stops, for extruders whose start is jerky. Default stays `rise`. Redo the PA pattern test after switching
- A rejected PA run now says whether the rise creeps or overshoots and falls back
- `OZNLAB_CHECK` / setup step 1: when the sensor reports conversion errors, only the [FAIL] line tells you to run `LDC_CALIBRATE_DRIVE_CURRENT` (the same advice is no longer repeated as a [WARN])
- Guide: new intro, JP1 explained, wiring diagram on every hardware step, which coil side faces the heatsink, `OZNLAB_SETUP` without STEP= in the setup steps, `[stepper_z]` example for position_min, RX toolhead on Printables

## v0.9.6

- At start the console says when a newer version is on GitHub (one `git ls-remote` in the background, `update_check: 0` turns it off)
- `OZNLAB_CHECK` shows whether the installed version is the latest

## v0.9.5

- `OZNLAB_SETUP` remembers the last step across the restart that `SAVE_CONFIG` does, and says where it continues (`RESET=1` starts over)
- A setup step that cannot run yet (not homed, nozzle cold, sensor errors) is repeated by the next `OZNLAB_SETUP` instead of skipped
- The heat messages name the minimum nozzle temperature (the extruder's `min_extrude_temp` for the tap and PA steps, 140 C for Z homing)

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
