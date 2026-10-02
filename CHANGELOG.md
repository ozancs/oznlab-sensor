# Changelog

## v0.10.5

- PA measurements check the sensor's sample timing before they start and on every burst. Right after a G28, the first 400/s stream once delivered samples a second apart with gaps for 20 s; `OZNLAB_PA_AUTO` read that as a 74 % pressure dip and stopped. Now the stream is restarted until the time stamps are sound, a burst or loop with broken timing is not used, and a first train that looks unsettled is run once more. Single wild samples (a chip status word read as a frequency) are dropped

## v0.10.4

- New, experimental: `OZNLAB_PA_AUTO [TEMP=] [FILAMENT=] [APPLY=1] [FILE=]` finds the pressure advance from the melt pressure alone, no pattern test and no pa_scale. The extruder pulses slow and fast in the air; for each candidate K the charge Klipper's PA would add is put in with plain extrude-only moves. The rule, taken from the loadcell method that matched printed pattern tests: raise K until the pressure dips below its new level after a speed drop, the last K without that dip is the answer. About 2 minutes, 70-100 mm of filament. `FILE=` writes the raw samples. Not in PRINT_START yet
- `uninstall.sh`: removes the link in Klipper and the update manager entry, says what to delete from printer.cfg. Guide and README have an Uninstall section

## v0.10.3

- The PA bursts run at 400 samples/s again, everything else stays at 100. A fast hotend's pressure fall is 20-30 ms: 2-3 samples at 100/s, which the 3-sample rule of v0.10.0 rejected or read wrong, so `OZNLAB_PA_SCALE` ended with "the readings did not settle" on such a hotend. At 400/s the same fall is 8-12 samples. The rate switches only while nothing else is streaming (clog/runout monitor, crash watch), and goes back to 100 when the bursts are done. The "noisy fall" test of a burst uses the noise of that burst's own baseline, measured at the rate it ran at
- The sensor stream stays up for the whole PA calibration instead of restarting for every burst. Klipper builds the sample clock from scratch at every start, and a few ms of timing error on a 30 ms fall is a wrong tau
- The fast fit allows a dead time between the extruder stop and the start of the fall (the filament relaxes first); pinned at the stop it read that delay as a shorter tau, 15 % off with 8 ms of delay in the test. A fine pass after the grid brings the step quantisation from 9 % under 2 %
- The decay fit weights its points: the end of the fall is far noisier in the log fit than its start and steered the slope on printers with a small pressure step
- `OZNLAB_PA_SCALE` and setup step 5 home first when the printer is not homed (the nozzle was not lifted before, and extruded where it stood), and step 5 asks for two readings that agree like `OZNLAB_PA_SCALE` does instead of taking one
- When an attempt gives no usable reading, the retry line says why ("the fall is too short to measure x6") instead of "melt zone not settled" for every reason; the reasons are grouped without their per-burst numbers
- The "no pa_scale for this filament yet" warning is not shown by the two commands that are making that scale

## v0.10.2

- The "no pressure signal" limit of the PA measurement and the filament tests follows the sensor noise (25 x the noise, at least 40 Hz) instead of a fixed 300 Hz. That number was sized for the reference printer's 9 Hz/um; a coil that gives 1 Hz/um sees a 9 x smaller pressure step with 2 Hz of noise, and every PA run was rejected on such a printer. The crash watch floor follows the noise the same way (`crash_step` is only needed to override it)

## v0.10.1

- `pa_x` / `pa_y` outside the bed (a value copied from an example) are pulled to the nearest edge with a note, instead of the print failing with "Move out of range"; the example values are 245, 245 so they fit a 250 mm bed as they are
- PA measurements go on until two readings in a row agree within 15 % (up to three bursts more than asked), and the settled pair is the result. The plastic that sat in the hotend while it heated flows differently, and only the hotend knows how much of it there is; before, one burst on that plastic could be the result. The prime before the first burst is 20 mm (was 12). `OZNLAB_PA_SCALE` refuses to store a scale from readings that did not settle
- Pressure advance is set without the two `pressure_advance:` lines Klipper prints, and the "no pa_scale for this filament yet" warning comes once per filament, not from every command

## v0.10.0

Less to know, less to type. The module measures what it needs and keeps it.

- `OZNLAB_PRINT_START EXTRUDER=<printing temperature>` is the whole start routine now, in place of the macro's M109: nozzle to 150 C (a clean contact, no ooze), `BRUSH=<macro>` if you have a wipe, tap over the bed centre, heat to the printing temperature, filament, PA. Without `EXTRUDER=` it works as before (hot: PA, settle, tap). A tap done since the last G28, an `OZNLAB_TAP` of your own in the macro, is not repeated
- `OZNLAB_PA_SCALE` measures three times and refuses when they disagree by more than 35 %; a fall shorter than 3 samples (25 ms) is no longer accepted as a time constant by any method. Seen on a user's printer: one 20 ms reading where the real tau was 60 ms set the scale three times too large, and every print then got three times the PA of the pattern test
- `pa_z` (default 10): the nozzle height during the PA test of `OZNLAB_PRINT_START`, next to `pa_x` / `pa_y` (a purge bucket beside the bed may want less than the 20 mm it used to lift to). `PA_Z=` on the command overrides it
- The installer's section says in its header that it must stay in printer.cfg, not in an included file

- One sensitivity model. Every tap measures the coil's Hz/um at the nozzle temperature of that moment; the values are kept per 20 C and written to the config (`sens_table`, kept by SAVE_CONFIG). The trigger, the crash watch and the tap checks all take their number from there, at any temperature, with a safe lower value between the measured ones. Before the first tap at a temperature, a mesh or a Z tilt does one plain tap at the bed centre to learn it. `home_assume_sens`, `home_trigger_frac`, `home_noise_sigma`, `home_lowpass` are gone
- `OZNLAB_THERMAL_CAL` is gone (nothing used its result); `thermal_um_c` / `thermal_ref_t` are ignored
- `data_rate` is gone: the LDC runs at 100 samples/s, the rate everything was tested at
- Commands that touch the bed (`OZNLAB_TAP`, `OZNLAB_MESH`, `OZNLAB_Z_TILT`, `OZNLAB_HOME_TEST`) home and heat the nozzle (150 C, or your current target when it is hot already) by themselves instead of asking for it. `TEMP=` sets another temperature, `TEMP=0` skips the heating. The heaters go off afterwards as before. `mesh_min_temp` is ignored
- Old options still load and do nothing; the start-up lists the lines that can go
- The config template, the installer's section and the guide show the handful of lines a user decides: i2c, `tap_adjust_z`, `pa_x` / `pa_y`, the watch actions, `z_homing`. Every tuning option keeps working, documented in the source next to where it is used
- `OZNLAB_HELP` lists the everyday commands; the rarely needed ones are one line, `ALL=1` shows them
- `OZNLAB_CHECK` shows the sensitivity table
- A duplicate, unreachable tests page in the menu code is gone

## v0.9.21

- The trigger works with a cold nozzle too. Its filter now looks at the change over 1, 2 or 4 samples instead of always 1: a longer span gives the small contact slope of a cold nozzle about three times more room above the noise, for a trigger that fires one or two samples later. The shortest span with a safe margin is taken, so with a hot nozzle nothing changes
- When even that is not enough the descent goes at 5 mm/s instead of 3 (the slope per sample grows with the speed). Only then, the push is a little larger
- A mesh or a Z tilt keeps the same speed and filter for all its points, so every point has the same small lag

## v0.9.20

- `data_rate` default 100 (was 200), in the module, the config template and the installer. Everything is tested at 100, and the sensor resolution is finer there
- With `z_homing: 1` and `data_rate` above 200 a warning at start says to set 100: at 400 samples/s the contact slope per sample is lost in the noise with a cold nozzle and homing fails

## v0.9.19

- The trigger threshold floor now follows the sensor noise measured in the moment before each descent (steppers on, bed hot, the toolhead just moved), not only the noise seen at startup; a retry raises it further. The refusal messages print the numbers: threshold, expected contact slope, noise at rest
- Fixed: a trigger point where the fine taps found no bed raised an internal error ("Internal error on command G28", printer shutdown) instead of continuing the descent

## v0.9.18

- Nozzle homing on a printer that homes and retracts fast: the trigger could fire in the first samples of the descent, while the hotend was still shaking from the move before ("Probe triggered prior to movement", or a Z 0 in the air followed by "contact amplitude too small"). Every trigger descent now waits for the previous move to finish and settles first; a trigger that fires before the nozzle has moved is retried after a pause; a trigger point where the fine taps find no bed is left behind and the descent continues on the trigger
- When a print ends (`OZNLAB_PRINT_END`) and the Z offset was babystepped during it, a popup offers to keep the babystep for the next taps, with or without `SAVE_CONFIG`
- Setup step 3 (finger push test) refuses to start with the nozzle above 50 C and says so in the guide, the menu and the console

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
