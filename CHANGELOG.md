# Changelog

## v0.9.17

- After a tap, a home test or a mesh the nozzle parks 3 mm above the bed (it stayed 0.4 mm above)
- A tap run that is rejected (taps disagree: ooze, dirt, a cold tip) no longer changes the sensitivity the trigger relies on, so the next trigger descent is not refused
- `OZNLAB_Z_TILT` descends to `position_min` at every point, an unlevelled bed can be a millimetre low at a corner, and says so when it finds no bed
- Trigger descents outside homing go at 3 mm/s, the speed the lag was measured at
- Mesh time estimates from the measured run: 5x5 in 77 s, 9x9 about 4 min

## v0.9.16

- Less push on the toolhead, with the MCU trigger the nozzle homing already uses (needs `z_homing: 1`). `OZNLAB_TAP`: the first descent stops on the trigger a few hundredths past the contact instead of pushing 0.3 mm and more into the bed; the soft taps follow. `OZNLAB_MESH`: one trigger descent per point, no fit, a second descent only when the point is far from what its neighbours predict; about twice as fast (5x5 in 77 s on our printer, was 3 min) and the push is that of the trigger: 0.05 mm at 2 mm/s. Without the trigger the previous taps are used; `TRIGGER=0` forces them
- New `OZNLAB_Z_TILT`: bed / gantry level with nozzle taps at the points of your `[z_tilt]` or `[quad_gantry_level]` section, Klipper's own adjustment and retries. Menu: Bed level. Guide 6.8
- `OZNLAB_MESH_COMPARE` reports the numbers without a verdict
- Menu: every page is one status line, then for each action one line that says what happens and its button. Z offset page shows how far the last tap pushed the nozzle. Bed mesh page says how long the grid takes. Bed level page added

## v0.9.15

- Heaters go off by themselves after a tap or a test outside a print: 2 minutes after the last OznLab step, when no print is running and nothing else is moving the printer. Another OznLab step in the meantime, or a print starting, keeps them on. Before, a quick tap test could leave the nozzle hot for hours
- Z homing setup (step 6): the lines to change in printer.cfg now come in a popup, in plain words, one step at a time, instead of on the console (console lines start with `//`, and pasted from there they became comments)
- Menu, bed mesh page: 3x3 / 5x5 / 7x7 / 9x9 buttons change the number of points and keep the area, no need to pick the corners again

## v0.9.14

- `OZNLAB_CHECK` and setup step 2 only say the drive current "was measured at start" when it was; otherwise they say how to set it
- README: the purge bucket goes into the config (`pa_x` / `pa_y`), not onto the PRINT_START line
- Config template: three options were listed twice
- Menu, bed mesh page: "Compare meshes" lists every saved mesh, you pick the first and then the second (before, it compared two fixed names)
- `release.sh` is executable in the repo

## v0.9.13

- A purge bucket for the PA test is set in the config: `pa_x`, `pa_y` in `[oznlab_sensor hotend]`. The PRINT_START line stays `OZNLAB_PRINT_START` with nothing after it
- Taps push less. A tap run at the spot of the previous one starts soft too (only the very first tap after a start goes the full depth). `SOFT=` on `OZNLAB_TAP` (mm, default 0.1) tries how far past the bed the soft taps go; smaller is gentler, the descent slows down to keep the samples the fit needs. A soft tap that finds no contact in its window is repeated at full depth
- `OZNLAB_MENU` rebuilt: one page each for Z offset, pressure advance, bed mesh, Z homing, and setup, health and tests. Every page says in plain words what each button does before the button. The PA page shows the saved filament scales and lets you pick the loaded filament. "Start bed mesh" says it starts right away; "Choose mesh area" says what it opens. All the tests (push, crash, home test, filament tests, thermal) are on one page. "All commands" opens command pages by group instead of printing everything on the console
- Guide 5.1 rewritten: two lines into the macro, everything optional goes into the config, one example macro. Troubleshooting: `Unknown command: "PA_X=260"` and the Cura filament case

## v0.9.12

- The soft taps of v0.9.11 failed with "only 9 samples after the contact" on a printer with 100 samples/s: at a low data rate the ramp fit cannot get its samples within 0.1 mm at 2 mm/s. The taps after the first now descend slower instead of deeper (0.7 mm/s at 100 samples/s, 1.4 at 200, 2 at 400), so they stay about 0.15 mm past the contact at any data rate; the record's lost end and the deceleration are counted in. A short tap that still fails is repeated at full depth instead of failing the command
- `OZNLAB_MESH` about twice as fast: the throw-away tap per point is gone (the first, soft tap counts; a pair that disagrees still gets a third), the slow part of a descent starts 0.15 mm above the expected contact instead of 0.3 to 0.6, shorter waits around each tap, and the travel between points is 1 mm up (`mesh_travel_z`, was 2) or 0.5 mm above the highest contact so far. In the simulator a 5x5 went from about 3 min to 1.5 on a Z axis with 45 mm/s2
- Guide 6.5: the time per point

## v0.9.11

- Softer taps: only the first descent of a tap goes the full 0.3 mm past the bed to find the contact. The others go just past it (about 0.1 mm at 2 mm/s and 200 samples/s: the 12 samples the fit needs, `DEPTH=` on `OZNLAB_TAP` overrides). Same for the fine taps after nozzle homing and for the mesh. The contact fit uses only that first stretch, so the numbers do not change, the push on the toolhead and the bed does. Suggested by Raidy
- Guide 5.1: a whole PRINT_START as an example, with the purge bucket lines

## v0.9.10

Setup with fewer things to type, after watching a second printer go through it.

- `install.sh` writes the `[oznlab_sensor hotend]` section into printer.cfg (finds the toolhead `[mcu ...]`, asks which board for the I2C bus, backs the file up first) and sets `[stepper_z] position_min: -1`. `BOARD=ebb|gen2|<bus>` and `MCU=` skip the questions
- The drive current is measured by the module at the first start and applied; `SAVE_CONFIG` keeps it. Setup step 2 only checks
- Setup step 4 (tap) and step 6 (Z homing test) home, heat and move over the bed centre by themselves. `TEMP=`, `X=`, `Y=` override
- `OZNLAB_CALIBRATE_PA FILAMENT=PLA TEMP=215` and `OZNLAB_SETUP STEP=5 FILAMENT=PLA TEMP=215`: one line instead of three
- `OZNLAB_PA_SCALE` measures tau right then (same filament, `TEMP=` heats first) instead of using an earlier measurement, so a Klipper restart between the pattern print and this command no longer matters
- `OZNLAB_PRINT_START` needs no parameters: the filament type comes from the gcode file (Orca, Prusa, Super, Bambu write `filament_type`), the PA measurement defaults to the air over the bed's front left corner. `FILAMENT=` and `PA_X= PA_Y=` still override
- New `OZNLAB_TAP_ADJUST`: babystep during the print, run it, `SAVE_CONFIG`: the babystep is folded into `tap_adjust_z`
- New `[stepper_z] endstop_pin: oznlab:z_virtual_endstop`: Z homes on the nozzle while another probe (BTT Eddy, Beacon ...) stays Klipper's probe for the mesh. Route B in guide 6.6, simulated only so far
- Clear config errors instead of Klipper's: `probe:z_virtual_endstop` with nothing being a probe; `z_homing_probe: 1` next to another probe (`probe_eddy_ng` and others are recognised now); `position_min` too high for nozzle homing
- Values this module saves next to a copy in an included file: `OZNLAB_PA_SCALE` and `OZNLAB_TAP_ADJUST` say so instead of a failing `SAVE_CONFIG`; `OZNLAB_CHECK` warns when the section is in an include
- `OZNLAB_THERMAL_CAL` waits 40 s per temperature instead of 90
- Clog / runout and crash watch: the filament speed is taken over 50 ms instead of one sample. One sample moves the filament only a few microsteps, so the speed jittered by 30 to 100 % on ungeared extruders or at 400 samples/s and the "steady flow" test that gates every decision rarely passed. The baseline observed at the end of a travel is frozen while an anomaly builds and may move by a bounded amount per gap, so a slower decay (a clog) is not learned as baseline
- Fixes: `OZNLAB_PA_SCALE` with a prime or duration over `max_extrude_only_distance` says so instead of aborting; a fine tap that raises during nozzle homing no longer blocks every later measurement; a failed setup step is repeated by the next `OZNLAB_SETUP` instead of skipped; `OZNLAB_PRINT_END` closes the print report on hosts that stream G-code; `OZNLAB_MESH` inside PRINT_START on such hosts no longer turns the heaters off; `OZNLAB_MESH_COMPARE` with a broken profile reports instead of shutting Klipper down; a crash test that saw no samples ends when asked again
- New `release.sh` for us: refuses to tag anything but the pushed main HEAD (v0.9.8's tag pointed at an older commit)
- Guide: install, setup steps 4.2 to 4.6, 5.1, 5.3 and 6.6 rewritten for the above

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
