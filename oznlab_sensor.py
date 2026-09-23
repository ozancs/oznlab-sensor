# OznLab Sensor: an LDC1612 eddy coil on the toolhead, watching hotend micro-deflection.
# Tap Z offset, per-print pressure advance and clog / runout monitoring.
#
# Install:  git clone https://github.com/ozancs/oznlab-sensor.git && ./oznlab-sensor/install.sh
# Guide:    https://ozancs.github.io/oznlab-sensor/
# Config:
#   [oznlab_sensor hotend]
#   i2c_mcu: EBBCan
#   i2c_bus: i2c3_PB3_PB4
#   i2c_address: 43          # JP1 on 2B = 43, on 2A = 42 (with a BTT Eddy on the bus use 2B)
#   reg_drive_current: 29
#   data_rate: 200           # LDC samples/s; lower = finer resolution (400 -> 23 Hz steps, 200 -> 12, 100 -> 6)
#   #verbose: 0              # 1 = per-step numbers on the console (always in klippy.log); VERBOSE=1 per command
#   #tap_sigma: 6.0          # arm threshold, x slew noise
#   #amp_sigma: 5.0          # minimum event amplitude, x force noise
#   #clog_mult: 8.0          # clog level = this x minimum amplitude
#   #tap_adjust_z: 0.04      # added to the measured contact Z (your squish preference)
#   #tap_target_z: -0.3      # hard lower limit of the tap descent (never below this)
#   #tap_samples: 5          # measurements per OZNLAB_TAP (plus 1 priming tap)
#   #tap_speed: 2.0  #tap_start_z: 2.0   # descent speed (mm/s, clamped to max_z_velocity) and start height
#   #tap_mesh_compensate: 1  # subtract the bed_mesh correction at the tap point (avoids double counting)
#   tap_z is written by OZNLAB_TAP; SAVE_CONFIG stores it and it is re-applied at every startup
#   pa_speed: 3.0            # mm/s filament for the PA test extrusion
#   pa_duration: 1.5         # s
#   #pa_scale: 0.175         # PA = rise tau * pa_scale  (per filament: OZNLAB_PA_SCALE PATTERN_PA=... TYPE=...)
#   #pa_prime: 12.0          # mm extruded before measuring (refills the melt zone emptied by ooze)
#   #pa_tau_max: 0.4         # fits above this (creeping rise) are rejected
#   #flow_exp: 0.6           # pressure ~ speed^flow_exp (fitted automatically when SPEEDS has 2+ values)
#   #clog_ratio: 2.0  #runout_ratio: 0.25  #confirm_windows: 3  #confirm_time: 10  #monitor_min_z: 0.5
#   #baseline_max_drift: 3   # Hz/s safety creep of the baseline while extruding (drift itself is learned from idle moments)
#   #clog_gcode: PAUSE       #runout_gcode: PAUSE   #monitor_min_speed: 0.5
#   #crash_um: 80  #crash_step: 150  #crash_sigma: 10  #crash_settle: 0.25  #crash_min_z: 0.6  #crash_gcode:
#   #report_sensors:        # temperatures in OZNLAB_REPORT (default: all temperature_sensor / heater_generic)
#        (crash_um x the sensitivity of the last tap = the Hz threshold; crash_step is only a floor)
#   mesh_min / mesh_max / mesh_count are written by OZNLAB_MESH_SETUP (nozzle coordinates)
#   #z_homing: 1             # home Z by touching the bed with the nozzle (needs trigger_analog in the toolhead firmware)
#   #z_homing_probe: 1       # ... and be Klipper's [probe]: endstop_pin: probe:z_virtual_endstop in [stepper_z]
#                            # (leave 0 on a printer that already has a probe, e.g. a BTT Eddy)
#   #home_trigger_frac: 0.5  #home_noise_sigma: 6  #home_lowpass: 12  #home_assume_sens: 1.5
#   #mesh_samples: 2  #mesh_speed: 150  #mesh_travel_z: 2  #mesh_min_temp: 180  #mesh_profile:
#   setup_step is written by OZNLAB_SETUP (so SAVE_CONFIG's restart does not lose your place)
#   thermal_um_c / thermal_ref_t are written by OZNLAB_THERMAL_CAL - informational only, nothing
#   applies them yet (tap at printing temperature and you do not need them)
#
# Commands:
#   OZNLAB_STATUS [DURATION=1]                 f0 / noise / rate / errors
#   OZNLAB_STREAM DURATION=10 FILE=... | OFF=1   raw time,frequency to CSV
#   OZNLAB_WATCH  [DURATION=120] [TRIG=Hz/s] [CLOG=Hz]   live events on the console
#   OZNLAB_WATCH  OFF=1
#   OZNLAB_TAP [SAMPLES=5] [DISCARD=1] [SPEED=2] [START=2.0] [TARGET=-0.3] [ADJUST=0] [APPLY=1] [SAVE=1]
#        nozzle-on-bed tap at the current XY: descends from START to the hard limit TARGET,
#        finds the contact point from the frequency kink, sets SET_GCODE_OFFSET Z=contact+ADJUST
#   OZNLAB_CALIBRATE_PA [SPEEDS=3] [DURATION=1.5] [SAMPLES=1] [DISCARD=1] [PRIME=12] [RETRIES=2] [SCALE=] [APPLY=1] [FILE=]
#        extrusion step in the air, fits the pressure rise tau, SET_PRESSURE_ADVANCE tau*pa_scale (not saved)
#   OZNLAB_PA_SCALE PATTERN_PA=<value> [TYPE=]  one-time per filament: pa_scale from a slicer PA pattern test
#   OZNLAB_MONITOR | OFF=1 | STATUS=1 | LOG=file.csv   clog / runout watch (reference = last CALIBRATE_PA)
#   OZNLAB_MAX_FLOW [START=1] [STEP=1] [MAX=] [DURATION=1.2] [PRIME=10]   real volumetric limit (mm3/s)
#   OZNLAB_RETRACT_TEST [SPEED=5] [MIN=.2] [MAX=1.4] [STEP=.2] [RSPEED=35]   retraction length for the slicer
#   OZNLAB_TEMP_SCAN [MIN=] [MAX=] [STEP=5] [SPEED=3] [SETTLE=20]          pressure vs nozzle temperature
#   OZNLAB_CRASH | OFF=1 | STATUS=1 | TEST=1 [UM=80] [HZ=] [GCODE=]   EXPERIMENTAL toolhead-collision watch
#   OZNLAB_THERMAL_CAL [MIN=180] [MAX=250] [STEP=20] [SETTLE=90] [SAMPLES=3] [SPEED=] [START=] [TARGET=] [SAVE=1]
#        nozzle drift per degree C: the tap repeated at several hotend temperatures (unload filament first)
#   OZNLAB_CHECK                             health report (chip, f0, noise, errors, config sanity)
#   OZNLAB_HELP                              every command with its usage
#   OZNLAB_MESH_SETUP                        pick the bed mesh area with the nozzle (Mainsail/Fluidd popup)
#   OZNLAB_MESH [ADAPTIVE=1] [MARGIN=5] [COUNT=] [SAMPLES=2] [PROFILE=] [TEMP=] [KEEP_HOT=1]
#        bed mesh with the nozzle as the probe; Klipper's [bed_mesh] applies it
#        every tap is written to oznlab_mesh_taps.csv in the config folder
#   OZNLAB_MESH_COMPARE [A=default] [B=oznlab]   shape difference of two mesh profiles
#   OZNLAB_HOME_TEST                         tap homing dry run (needs z_homing: 1): trigger vs contact
#   OZNLAB_SETUP [STEP=1..8] [RESET=1]       guided first-time setup, one step per call
#   OZNLAB_MENU [PAGE=]                      Mainsail / Fluidd popup with every tool, in four pages
#   OZNLAB_REPORT                            summary of the current or last print
#   OZNLAB_FILAMENT TYPE=                    which filament this print uses (per-filament pa_scale)
#   OZNLAB_PRINT_START [FILAMENT=] [PA_X= PA_Y=] [TAP_X= TAP_Y=] [SETTLE=15] [PA=1] [TAP=1] [MONITOR=0] [CRASH=0]
#   OZNLAB_PRINT_END                         stops the clog / runout and crash watch
#   OZNLAB_TEST TYPE=flow|retract|temp       the three filament tests from one command
#
# PRINT_START:  ... heat ... OZNLAB_PRINT_START FILAMENT=... PA_X= PA_Y= ... prime line ... OZNLAB_MONITOR
# PRINT_END / CANCEL:  OZNLAB_PRINT_END   (the watches also stop by themselves when the print ends)
#
# Detector used by OZNLAB_WATCH:
#   slew  = step-matched filter, (mean of newest HALF samples - mean of previous HALF) / dt
#   fc    = f - baseline;  baseline tracks with tau=1.2 s while idle, creeps (20 s) in an event
#   arm on |slew| > TRIG; falls below 40% of its own peak within 0.3 s -> TAP, otherwise PRESS.
#
# Copyright (C) 2026  Ozan Sahin  <ozancsahin@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging, math, os, re
from . import ldc1612

# Release version. Bump it together with a git tag (v0.9.0 ...): Moonraker's update manager
# (channel: stable) offers an update only for a new tag, and this string shows which one runs.
VERSION = "0.9.5"

IDLE, EDGE, PRESS = 0, 1, 2

class Detector:
    TAP_WINDOW = 0.30; TAP_DROP = 0.40; PRESS_KEEP = 0.50
    REL_EDGE = 0.7; REFRAC = 0.15; STALL_T = 2.0; WEAK_T = 0.30
    PRESS_MAX = 30.0; CAL_T = 3.0; PRINT_DT = 0.25

    def __init__(self, respond, tap_sigma, amp_sigma, clog_mult, trig=None, clog=None):
        self.respond = respond
        self.tap_sigma, self.amp_sigma, self.clog_mult = tap_sigma, amp_sigma, clog_mult
        self.trig_override, self.clog_override = trig, clog
        self.reset()

    def reset(self):
        self.dt = None; self.half = 4; self.buf = []
        self.med = []; self.base = None; self.fc = 0.; self.slew = 0.
        self.cal_t0 = None; self.cal_s2s = 0.; self.cal_s2f = 0.; self.cal_n = 0; self.cal_done = False
        self.sd_slew = 1.; self.sd_fc = 1.; self.TRIG = 1e9; self.FC_MIN = 1e9; self.CLOG = 1e9
        self.st = IDLE; self.t_ev = 0.; self.t_end = -1.; self.ev_peak = 0.; self.ev_slew0 = 0.
        self.ev_slewmax = 0.; self.ev_rev = False; self.t_rel = None; self.t_print = 0.
        self.t_stall = None; self.t_weak = None; self.clog_on = False; self.t_clog = None
        self.fring = []; self.n_ev = 0; self.n_clog = 0; self.last_t = None
        self.q = None; self.last_x = None            # LDC quantisation step estimate

    # ---- filters ----
    def _step(self, t, f):
        if self.last_t is not None and self.dt is None:
            d = t - self.last_t
            if d > 1e-5:                                          # clock-sync revisions can go backwards
                self.dt = d
                self.half = max(3, int(round(0.015 / self.dt)))   # ~15 ms per half window
        self.last_t = t
        self.med.append(f); self.med = self.med[-3:]
        x = sorted(self.med)[len(self.med)//2]
        if self.last_x is not None:
            d = abs(x - self.last_x)
            if d > 0.5 and (self.q is None or d < self.q): self.q = d
        self.last_x = x
        self.buf.append(x); self.buf = self.buf[-2*self.half:]
        if len(self.buf) == 2*self.half and self.dt:
            h = self.half
            self.slew = (sum(self.buf[h:])/h - sum(self.buf[:h])/h) / (h*self.dt)
        if self.base is None: self.base = x
        tau = 20.0 if self.st != IDLE else 1.2
        a = 1.0 - math.exp(-(self.dt or 0.0025)/tau)
        self.base += a*(x - self.base)
        self.fc = x - self.base
        return x

    def _end(self, t, x):
        self.st = IDLE; self.clog_on = False; self.t_clog = None; self.t_end = t
        self.base = x; self.fc = 0.; self.buf = []; self.fring = []

    # ---- calibration on the first CAL_T seconds ----
    def _calibrate(self, t):
        if self.cal_t0 is None: self.cal_t0 = t; return False
        if t - self.cal_t0 > 1.0:                       # skip first second (settling)
            self.cal_s2s += self.slew*self.slew; self.cal_s2f += self.fc*self.fc; self.cal_n += 1
        if t - self.cal_t0 < self.CAL_T: return False
        n = max(1, self.cal_n)
        self.sd_slew = max(50., math.sqrt(self.cal_s2s/n))
        self.sd_fc = max(5., math.sqrt(self.cal_s2f/n))
        self.cal_done = True
        self._thresholds()
        self.respond("oznlab watch: noise slew %.0f Hz/s, force %.1f Hz, quant ~%.0f Hz | ARM %.0f Hz/s | min amp %.0f Hz | CLOG %.0f Hz"
                     % (self.sd_slew, self.sd_fc, self.q or 0., self.TRIG, self.FC_MIN, self.CLOG))
        return True

    def _thresholds(self):
        # sigma-based, but never below what the LDC's own quantisation can fake:
        # a 1-step blip must not arm, a 3-step blip must not count as an event
        q = (self.q or 0.) * 1.2
        hw = self.half * (self.dt or 0.0025)
        self.TRIG = self.trig_override or max(self.sd_slew*self.tap_sigma, 1.6*q/hw)
        self.FC_MIN = max(self.sd_fc*self.amp_sigma, 3.5*q)
        self.CLOG = self.clog_override or self.FC_MIN*self.clog_mult

    # ---- one sample ----
    def feed(self, t, f):
        x = self._step(t, f)
        if not self.cal_done:
            self._calibrate(t); return
        a = abs(self.fc)
        if self.st == IDLE:
            self._thresholds()
            if t - self.t_end > self.REFRAC and abs(self.slew) > self.TRIG:
                self.st = EDGE; self.t_ev = t; self.ev_peak = a; self.ev_slew0 = self.slew
                self.ev_slewmax = abs(self.slew); self.ev_rev = False
            return
        if a > self.ev_peak: self.ev_peak = a
        if self.st == EDGE:
            if abs(self.slew) > self.ev_slewmax: self.ev_slewmax = abs(self.slew)
            if self.slew*self.ev_slew0 < 0 and abs(self.slew) > self.TRIG*0.5: self.ev_rev = True
            dropped = self.ev_rev and a < self.ev_peak*self.TAP_DROP
            timeout = t - self.t_ev > self.TAP_WINDOW
            if dropped or (timeout and a < self.ev_peak*self.PRESS_KEEP):
                if self.ev_peak >= self.FC_MIN:
                    self.n_ev += 1
                    self.respond("TAP #%d  peak %.0f Hz  slew %.0f Hz/s  %.0f ms"
                                 % (self.n_ev, self.ev_peak, self.ev_slewmax, (t-self.t_ev)*1000))
                self._end(t, x)
            elif timeout:
                if self.ev_peak < self.FC_MIN*2.0: self._end(t, x); return
                self.st = PRESS; self.t_rel = None; self.t_print = 0.; self.t_clog = None
                self.t_stall = None; self.t_weak = None; self.fring = []
            return
        # ---- PRESS ----
        ring_n = max(8, int(0.1 / (self.dt or 0.0025)))
        self.fring.append(self.fc); self.fring = self.fring[-ring_n:]
        if self.slew*self.ev_slew0 < 0 and abs(self.slew) > self.TRIG*self.REL_EDGE and a < self.ev_peak*0.7:
            self.n_ev += 1
            self.respond("PRESS released  peak %.0f Hz (%.0f%% of clog)  held %.0f ms"
                         % (self.ev_peak, self.ev_peak/self.CLOG*100., (t-self.t_ev)*1000))
            self._end(t, x); return
        if a < self.FC_MIN:
            if self.t_weak is None: self.t_weak = t
            elif t - self.t_weak > self.WEAK_T: self._end(t, x); return
        else: self.t_weak = None
        if len(self.fring) >= ring_n:
            m = sum(self.fring)/len(self.fring)
            sd = math.sqrt(max(0., sum((v-m)**2 for v in self.fring)/len(self.fring)))
            if sd < self.sd_fc*3.0:
                if self.t_stall is None: self.t_stall = t
                elif t - self.t_stall > self.STALL_T:
                    self.respond("    flat level - re-zeroed"); self._end(t, x); return
            else: self.t_stall = None
        if not self.clog_on:
            if a >= self.CLOG:
                if self.t_clog is None: self.t_clog = t
                elif t - self.t_clog > 0.4:
                    self.clog_on = True; self.n_clog += 1
                    self.respond(">>> CLOG DETECTED  %.0f Hz (%.1fx)" % (a, a/self.CLOG))
            else: self.t_clog = None
        elif a < self.CLOG*0.5:
            self.clog_on = False; self.t_clog = None; self.respond("    clog cleared")
        if t - self.t_print > self.PRINT_DT:
            self.t_print = t
            pct = int(a/self.CLOG*100.); nb = min(20, pct*20//100)
            self.respond("    force [%s] %3d%%  %.0f Hz%s"
                         % ('#'*nb + '.'*(20-nb), pct, a, "   << CLOG" if self.clog_on else ""))
        if t - self.t_ev > self.PRESS_MAX: self._end(t, x)


class OznLabSensor:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.name = config.get_name().split()[-1]
        mcu_name = config.get('i2c_mcu', 'mcu')
        if mcu_name != 'mcu' and not config.has_section('mcu ' + mcu_name):
            have = ['mcu'] + [c.get_name().split(None, 1)[1] for c in config.get_prefix_sections('mcu ')]
            raise config.error("oznlab: i2c_mcu: %s - there is no [mcu %s] in your config. "
                               "Use the name of your toolhead board's [mcu ...] section: %s"
                               % (mcu_name, mcu_name, ", ".join(have)))
        # default address 43 (JP1 on 2B, as in the guide), not the LDC1612's own 42: that one is
        # the BTT Eddy's, and the guide always solders 2B
        _addr = ldc1612.LDC1612_ADDR
        ldc1612.LDC1612_ADDR = 0x2b
        try:
            self.sensor = ldc1612.LDC1612(config, None)
        finally:
            ldc1612.LDC1612_ADDR = _addr
        self.i2c_addr = config.getint('i2c_address', 43)
        # a BTT Eddy (or another LDC1612) on the same wires at the same address: both would answer
        for oc in config.get_prefix_sections('probe_eddy_current') + config.get_prefix_sections('ldc1612'):
            if (oc.get('i2c_mcu', 'mcu') == mcu_name and oc.get('i2c_bus', None) == config.get('i2c_bus', None)
                    and oc.getint('i2c_address', 42, note_valid=False) == self.i2c_addr):
                raise config.error("oznlab: [%s] uses the same i2c_bus and address %d as [%s]. Solder JP1 on "
                                   "the OznLab board to 2B and set i2c_address: 43"
                                   % (oc.get_name(), self.i2c_addr, config.get_name()))
        # LDC conversion time = 1/data_rate: 400/s -> ~23 Hz steps, 200/s -> ~12 Hz, 100/s -> ~6 Hz
        self.sensor.data_rate = config.getint('data_rate', 200, minval=50, maxval=400)
        # upstream sized ffreader's clock-sync smoothing for its own default rate; resize it for ours
        try:
            from . import bulk_sensor
            smooth = self.sensor.data_rate * ldc1612.BATCH_UPDATES * 2
            self.sensor.ffreader.clock_sync = bulk_sensor.ClockSyncRegression(
                self.sensor.i2c.get_mcu(), smooth)
        except Exception:
            logging.exception("oznlab: could not resize the clock-sync window")
        self.tap_sigma = config.getfloat('tap_sigma', 6.0, above=1.)
        self.amp_sigma = config.getfloat('amp_sigma', 5.0, above=1.)
        self.clog_mult = config.getfloat('clog_mult', 8.0, above=1.)
        self.tap_adjust_z = config.getfloat('tap_adjust_z', 0.04, minval=-1., maxval=1.)
        self.tap_target_z = config.getfloat('tap_target_z', -0.3, minval=-0.6, maxval=0.0)
        self.tap_speed = config.getfloat('tap_speed', 2.0, above=0.2, maxval=10.)
        self.tap_start_z = config.getfloat('tap_start_z', 2.0, above=0.5, maxval=10.)
        self.tap_samples = config.getint('tap_samples', 5, minval=1, maxval=10)
        # A tap measures the raw kinematic contact height, but bed_mesh later ADDS its own
        # correction at the same XY. Without this, both are applied and the nozzle ends up
        # that much too high over the whole first layer.
        self.tap_mesh_comp = config.getboolean('tap_mesh_compensate', True)
        self.cfg_name = config.get_name()
        # console: one short line per result; per-step numbers go to klippy.log, and to the
        # console too with verbose: 1 in the config or VERBOSE=1 on any command
        self.verbose = config.getboolean('verbose', False)
        # nozzle-tap bed mesh - the area is written by OZNLAB_MESH_SETUP (nozzle coordinates)
        self.mesh_min = config.getfloatlist('mesh_min', None, count=2)
        self.mesh_max = config.getfloatlist('mesh_max', None, count=2)
        self.mesh_count = config.getintlist('mesh_count', (5, 5), count=2)
        if min(self.mesh_count) < 3:
            raise config.error("oznlab: mesh_count needs at least 3 points per axis")
        if self.mesh_min is not None and self.mesh_max is not None and \
                (self.mesh_min[0] >= self.mesh_max[0] or self.mesh_min[1] >= self.mesh_max[1]):
            raise config.error("oznlab: mesh_min must be below mesh_max on both axes "
                               "(run OZNLAB_MESH_SETUP again)")
        self.mesh_samples = config.getint('mesh_samples', 2, minval=1, maxval=5)   # kept taps per point
        self.mesh_speed = config.getfloat('mesh_speed', 150., above=10.)          # mm/s between points
        self.mesh_travel_z = config.getfloat('mesh_travel_z', 2., above=0.5, maxval=20.)
        # below this the plastic on the tip is rubbery and compresses under every tap (measured:
        # 150 C drifted 0.16 mm over 10 taps, 250 C stayed within 0.015 mm)
        self.mesh_min_temp = config.getfloat('mesh_min_temp', 180., minval=0.)
        self.mesh_profile = config.get('mesh_profile', '').strip()
        self._ms = None                                        # mesh setup wizard state
        # tap homing (nozzle touches the bed, no probe needed). Needs a Klipper with
        # trigger_analog (2026) on the host and the toolhead board - the same the eddy probe homing uses.
        self.z_homing = config.getboolean('z_homing', False)
        self.z_homing_probe = config.getboolean('z_homing_probe', False)     # opt in: the nozzle replaces the Z endstop
        self.home_trigger_frac = config.getfloat('home_trigger_frac', 0.5, above=0.1, maxval=0.7)
        self.home_noise_sigma = config.getfloat('home_noise_sigma', 6., above=2.)
        self.home_lowpass = config.getfloat('home_lowpass', 12., above=2.)   # Hz
        self.home_assume_sens = config.getfloat('home_assume_sens', 1.5, above=0.1)  # Hz/um before any tap
        self.homing = None
        if self.z_homing:
            self.homing = OznLabHoming(self, config)
        self.saved_tap_z = config.getfloat('tap_z', None)      # written by OZNLAB_TAP + SAVE_CONFIG
        # pressure advance calibration (never saved - applied live per print)
        self.pa_speed = config.getfloat('pa_speed', 3.0, above=0.5, maxval=20.)     # mm/s filament
        self.pa_duration = config.getfloat('pa_duration', 1.5, minval=0.8, maxval=5.)
        self.pa_scale = config.getfloat('pa_scale', 0.175, above=0.005, maxval=3.)      # PA = tau_rise * pa_scale
        self._pa_scale_set = config.get('pa_scale', None) is not None   # tuned by the user or still the default
        # per filament: pa_scale_asa, pa_scale_petg ... (written by OZNLAB_PA_SCALE while that filament
        # is loaded). The filament comes from the slicer: PRINT_START -> OZNLAB_FILAMENT TYPE=...
        self.pa_scales = {}
        for opt in config.get_prefix_options('pa_scale_'):
            key = self._fil_key(opt[len('pa_scale_'):])
            if key:
                self.pa_scales[key] = config.getfloat(opt, above=0.005, maxval=3.)
        self.filament = None               # lower-case key of the filament of this print, or None
        self.filament_name = None          # the same filament as the slicer wrote it, for messages
        self._ps_hint = False
        # print report: collected from OZNLAB_FILAMENT (start of PRINT_START) to the end of the print
        self.report_sensors = [x.strip() for x in config.get('report_sensors', '').split(',') if x.strip()]
        self._job = None; self._last_job = None; self._job_timer = None
        self.last_tap_z = None; self.last_pa = None
        self.pa_prime = config.getfloat('pa_prime', 12.0, minval=0., maxval=50.)    # mm extruded first: refill the melt zone after ooze
        self.pa_tau_max = config.getfloat('pa_tau_max', 0.4, above=0.05)           # fits above this are rejected (melt zone not primed)
        self.pa_cal = None                                     # last calibration result (for clog reference)
        # print monitor (clog / runout) - reference comes from the last OZNLAB_CALIBRATE_PA
        self.flow_exp = config.getfloat('flow_exp', 0.6, above=0.1, maxval=1.5)     # P ~ v^flow_exp
        self.clog_ratio = config.getfloat('clog_ratio', 2.0, above=1.1)
        self.runout_ratio = config.getfloat('runout_ratio', 0.25, above=0., below=1.)
        self.mon_min_speed = config.getfloat('monitor_min_speed', 0.5, above=0.05)  # mm/s filament
        self.mon_min_z = config.getfloat('monitor_min_z', 0.5, minval=0.)          # no decisions on the first layer(s)
        self.confirm_windows = config.getint('confirm_windows', 3, minval=1)       # consecutive windows that must agree
        self.confirm_time = config.getfloat('confirm_time', 10.0, above=1.)        # s per window
        # Safety creep of the baseline while extruding (Hz/s). Thermal drift itself is learned
        # from idle moments and extrapolated; this only bounds the error during long stretches
        # without any idle moment. Keep it small - it is exactly what a slow clog hides behind.
        self.base_drift = config.getfloat('baseline_max_drift', 3., above=0.)       # Hz/s
        self.clog_gcode = config.get('clog_gcode', 'PAUSE')
        self.runout_gcode = config.get('runout_gcode', 'PAUSE')
        # crash detection (EXPERIMENTAL) - a mechanical hit is a step the melt pressure cannot make
        # threshold = crash_um x the Hz/um measured by the last tap (re-measured every print by
        # OZNLAB_TAP in PRINT_START, so it follows the hotend temperature); crash_step is a floor
        self.crash_um = config.getfloat('crash_um', 80., above=10.)         # um of nozzle push in 15 ms
        self.crash_step = config.getfloat('crash_step', 150., above=30.)    # Hz floor when no tap has run yet
        self.crash_sigma = config.getfloat('crash_sigma', 10., above=3.)    # ... and never below this x noise
        self.crash_min_z = config.getfloat('crash_min_z', 0.6, minval=0.)
        self.crash_settle = config.getfloat('crash_settle', 0.25, above=0.05)   # s of steady flow before arming
        self.crash_gcode = config.get('crash_gcode', '')                    # empty = report only
        # thermal calibration (written by OZNLAB_THERMAL_CAL)
        self.thermal_um_c = config.getfloat('thermal_um_c', None)           # nozzle drop per degree C
        self.thermal_ref_t = config.getfloat('thermal_ref_t', None)
        self._mon = None
        self._cap = None
        self._watch = None
        self._tap = None; self._tap_on = False
        self._quiet_pt = 0.        # print time before which the crash watch never judges
        self._tap_T = None          # nozzle temperature when last_sens was measured
        self._crash = None
        self.last_stats = None
        self.last_sens = None; self.last_sens_t = 0.
        # setup progress survives the restart SAVE_CONFIG does (stored with the autosave values)
        self._setup_step = config.getint('setup_step', 0, minval=0, maxval=8)
        self._setup_saved = self._setup_step
        self._setup_resume = 0 < self._setup_step < 8
        self._help = {}
        for cmd, func, desc in (('OZNLAB_STATUS', self.cmd_STATUS, self.cmd_STATUS_help),
                                ('OZNLAB_STREAM', self.cmd_STREAM, self.cmd_STREAM_help),
                                ('OZNLAB_WATCH', self.cmd_WATCH, self.cmd_WATCH_help),
                                ('OZNLAB_TAP', self.cmd_TAP, self.cmd_TAP_help),
                                ('OZNLAB_CALIBRATE_PA', self.cmd_CALIBRATE_PA, self.cmd_CALIBRATE_PA_help),
                                ('OZNLAB_PA_SCALE', self.cmd_PA_SCALE, self.cmd_PA_SCALE_help),
                                ('OZNLAB_FILAMENT', self.cmd_FILAMENT, self.cmd_FILAMENT_help),
                                ('OZNLAB_MONITOR', self.cmd_MONITOR, self.cmd_MONITOR_help),
                                ('OZNLAB_MAX_FLOW', self.cmd_MAX_FLOW, self.cmd_MAX_FLOW_help),
                                ('OZNLAB_RETRACT_TEST', self.cmd_RETRACT_TEST, self.cmd_RETRACT_TEST_help),
                                ('OZNLAB_TEMP_SCAN', self.cmd_TEMP_SCAN, self.cmd_TEMP_SCAN_help),
                                ('OZNLAB_CRASH', self.cmd_CRASH, self.cmd_CRASH_help),
                                ('OZNLAB_THERMAL_CAL', self.cmd_THERMAL_CAL, self.cmd_THERMAL_CAL_help),
                                ('OZNLAB_CHECK', self.cmd_CHECK, self.cmd_CHECK_help),
                                ('OZNLAB_SETUP', self.cmd_SETUP, self.cmd_SETUP_help),
                                ('OZNLAB_MESH_SETUP', self.cmd_MESH_SETUP, self.cmd_MESH_SETUP_help),
                                ('OZNLAB_MESH', self.cmd_MESH, self.cmd_MESH_help),
                                ('OZNLAB_MESH_COMPARE', self.cmd_MESH_COMPARE, self.cmd_MESH_COMPARE_help),
                                ('OZNLAB_HELP', self.cmd_HELP, self.cmd_HELP_help),
                                ('OZNLAB_HOME_TEST', self.cmd_HOME_TEST, self.cmd_HOME_TEST_help),
                                ('OZNLAB_REPORT', self.cmd_REPORT, self.cmd_REPORT_help),
                                ('OZNLAB_MENU', self.cmd_MENU, self.cmd_MENU_help),
                                ('OZNLAB_PRINT_START', self.cmd_PRINT_START, self.cmd_PRINT_START_help),
                                ('OZNLAB_PRINT_END', self.cmd_PRINT_END, self.cmd_PRINT_END_help),
                                ('OZNLAB_TEST', self.cmd_TEST, self.cmd_TEST_help)):
            self._help[cmd] = desc
            self.gcode.register_mux_command(cmd, 'SENSOR', self.name, func, desc=desc)
            try:
                self.gcode.register_mux_command(cmd, 'SENSOR', None, func, desc=desc)
            except Exception:
                pass
        self.printer.register_event_handler('klippy:connect', self._on_connect)
        self.printer.register_event_handler('klippy:ready', self._on_ready)

    def _on_connect(self):
        try:
            mid = self.sensor.read_reg(0x7E); did = self.sensor.read_reg(0x7F)
            logging.info("oznlab %s v%s: LDC1612 id %04x/%04x", self.name, VERSION, mid, did)
            if mid != 0x5449 or did != 0x3055:
                logging.error("oznlab %s: unexpected LDC1612 id - check address/JP1", self.name)
        except Exception:
            logging.exception("oznlab %s: LDC1612 not responding", self.name)

    def _on_ready(self):
        if self.saved_tap_z is None: return
        try:
            self.gcode.run_script("SET_GCODE_OFFSET Z=%.4f MOVE=0" % self.saved_tap_z)
            self.gcode.respond_info("OznLab: saved z offset %.3f applied" % self.saved_tap_z)
        except Exception:
            logging.exception("oznlab: could not apply the saved tap z offset")

    # ================= capture (STATUS / STREAM) =================
    def _on_batch(self, msg, mine=None):
        cap = self._cap
        if cap is None or (mine is not None and cap is not mine): return False   # an older capture's client
        for t, f, z in msg.get('data', ()):
            if f <= 0.: cap['bad'] += 1; continue
            cap['n'] += 1; cap['s'] += f; cap['s2'] += f*f
            if cap['last'] is not None: cap['sd'] += abs(f-cap['last']); cap['nd'] += 1
            cap['last'] = f
            if cap['t0'] is None: cap['t0'] = t
            cap['t1'] = t
            if cap['fh'] is not None:
                try:
                    cap['fh'].write("%.4f,%.2f\n" % (t, f))
                except Exception:                  # full disk etc. - an exception here kills klippy
                    logging.exception("oznlab stream: write failed, stopping the file")
                    try: cap['fh'].close()
                    except Exception: pass
                    cap['fh'] = None; cap['fname'] = None
        e = msg.get('errors', 0); o = msg.get('overflows', 0)
        if cap['e0'] is None: cap['e0'] = e; cap['o0'] = o
        cap['errors'] = e - cap['e0']; cap['overflows'] = o - cap['o0']
        if self.reactor.monotonic() >= cap['until']:
            self._finish(quiet=cap.get('quiet', False)); return False
        return True

    def _start(self, seconds, fname=None, quiet=False):
        if self._cap is not None:
            raise self.gcode.error("oznlab: a capture is already running - wait for it or OZNLAB_STREAM OFF=1")
        fh = None
        if fname:
            fname = self._csv_path(fname)
            try:
                fh = open(fname, 'w'); fh.write("time,frequency\n")
            except OSError as e:
                raise self.gcode.error("oznlab: cannot write %s (%s)" % (fname, e))
        until = self.reactor.monotonic() + seconds
        self._cap = dict(until=until, n=0, s=0., s2=0., sd=0., nd=0,
                         last=None, t0=None, t1=None, bad=0, errors=0, overflows=0,
                         e0=None, o0=None, fh=fh, fname=fname, quiet=quiet)
        try:
            self._client('capture', lambda msg, mine=self._cap: self._on_batch(msg, mine), self._cap_abort)
        except Exception:
            self._cap = None
            if fh is not None: fh.close()
            raise
        # watchdog: if the sensor stops delivering batches the callback never runs again and
        # every other command would stay blocked on "capture already running"
        cap = self._cap
        def _watchdog(eventtime, cap=cap):
            if self._cap is cap:
                try: self._finish(quiet=cap.get('quiet', False))
                except Exception: logging.exception("oznlab: capture watchdog")
            return self.reactor.NEVER
        self.reactor.register_timer(_watchdog, until + 2.0)

    def _cap_abort(self):
        cap = self._cap; self._cap = None
        if cap is not None and cap.get('fh') is not None:
            cap['fh'].close()

    def _finish(self, quiet=False):
        cap = self._cap; self._cap = None
        if cap is None: return None
        if cap['fh'] is not None:
            try: cap['fh'].close()
            except Exception: logging.exception("oznlab: could not close the capture file")
        n = cap['n']
        if n < 2:
            self.last_stats = None
            self.gcode.respond_info("OznLab: no data from the sensor - check the wiring, i2c_address and JP1 "
                                    "(bad %d, errors %d)" % (cap['bad'], cap['errors'])); return None
        mean = cap['s']/n; std = math.sqrt(max(0., cap['s2']/n - mean*mean))
        white = (cap['sd']/cap['nd'])/1.128 if cap['nd'] else 0.
        dur = (cap['t1']-cap['t0']) if cap['t0'] is not None else 0.
        rate = (n-1)/dur if dur > 0 else 0.
        probs = cap['bad'] + cap['errors'] + cap['overflows']
        msg = ("OznLab: %.4f MHz, noise %.1f Hz, %.0f samples/s, %s"
               % (mean/1e6, white, rate, "no errors" if not probs else
                  "%d bad / %d errors / %d overflows" % (cap['bad'], cap['errors'], cap['overflows'])))
        logging.info("oznlab %s: f0=%.4f MHz noise=%.2f Hz rms (%.2f ppm) drift-incl std=%.2f Hz "
                     "rate=%.0f/s samples=%d bad=%d errors=%d overflows=%d"
                     % (self.name, mean/1e6, white, white/mean*1e6, std, rate, n,
                        cap['bad'], cap['errors'], cap['overflows']))
        self.last_stats = dict(f0=mean, noise=white, std=std, rate=rate, n=n,
                               bad=cap['bad'], errors=cap['errors'], overflows=cap['overflows'])
        if cap['fname']: msg += "\n  written: %s" % cap['fname']
        if not quiet: self.gcode.respond_info(msg)
        return self.last_stats

    cmd_STATUS_help = "Frequency and noise of the OznLab Sensor: OZNLAB_STATUS [DURATION=1]"
    def cmd_STATUS(self, gcmd):
        secs = self._gf(gcmd, 'DURATION', 1.0, minval=0.2, maxval=30.)
        self._start(secs)
        self.reactor.pause(self.reactor.monotonic() + secs + 0.7)
        if self._cap is not None: self._finish()

    cmd_STREAM_help = "Stream raw OznLab Sensor samples to a CSV: OZNLAB_STREAM DURATION=10 FILE=... | OFF=1"
    def cmd_STREAM(self, gcmd):
        if gcmd.get_int('OFF', 0):
            if self._cap is None: gcmd.respond_info("oznlab: no capture running"); return
            self._finish(); return
        secs = self._gf(gcmd, 'DURATION', 10., minval=0.5, maxval=600.)
        fname = gcmd.get('FILE', '/tmp/oznlab_%s.csv' % self.name)
        self._start(secs, fname)
        gcmd.respond_info("oznlab %s: streaming %.0f s -> %s" % (self.name, secs, fname))

    # ================= WATCH (live detector) =================
    def _on_watch(self, msg, mine=None):
        w = self._watch
        if w is None or (mine is not None and w is not mine): return False
        det = w['det']
        for t, f, z in msg.get('data', ()):
            if f > 0.: det.feed(t, f)
        if self.reactor.monotonic() >= w['until']:
            self._watch = None
            self.gcode.respond_info("oznlab watch: done  (%d events, %d clogs)" % (det.n_ev, det.n_clog))
            return False
        return True

    def _free(self, gcmd, what, mon=False):
        """Make the sensor free for a measurement. A WATCH is only a live view: stop it (it also
        never ends by itself when the sensor delivers nothing). STREAM / MONITOR are deliberate,
        so say how to stop them."""
        if self._watch is not None:
            done = self.reactor.monotonic() >= self._watch['until']
            self._watch = None
            if not done:
                gcmd.respond_info("oznlab watch: stopped for %s" % what)
        if self._cap is not None:
            raise gcmd.error("oznlab %s: a STREAM capture is running - wait for it or OZNLAB_STREAM OFF=1" % what)
        if self._tap is not None:
            raise gcmd.error("oznlab %s: another OznLab measurement is still running" % what)
        if mon and self._mon is not None:
            raise gcmd.error("oznlab %s: the clog/runout watch is on - OZNLAB_MONITOR OFF=1 first" % what)

    cmd_WATCH_help = "Live tap/press/clog events on the console: OZNLAB_WATCH [DURATION=120] [TRIG=Hz/s] [CLOG=Hz] | OFF=1"
    def cmd_WATCH(self, gcmd):
        if gcmd.get_int('OFF', 0):
            if self._watch is not None:
                # clear it here: if the sensor stopped delivering, the callback never runs
                # again and a stuck watch would block TAP / PA until a restart
                self._watch = None; gcmd.respond_info("oznlab watch: stopped")
            return
        if self._watch is not None and self.reactor.monotonic() >= self._watch['until']:
            self._watch = None             # ran out without data from the sensor
        if self._watch is not None: raise gcmd.error("oznlab: watch already running (OFF=1 to stop)")
        secs = self._gf(gcmd, 'DURATION', 120., minval=5., maxval=3600.)
        trig = self._gf(gcmd, 'TRIG', None, above=0.)
        clog = self._gf(gcmd, 'CLOG', None, above=0.)
        det = Detector(self.gcode.respond_info, self.tap_sigma, self.amp_sigma, self.clog_mult, trig, clog)
        self._watch = dict(det=det, until=self.reactor.monotonic()+secs)
        try:
            self._client('watch', lambda msg, mine=self._watch: self._on_watch(msg, mine),
                         lambda: setattr(self, '_watch', None))
        except Exception as e:
            self._watch = None
            raise gcmd.error("oznlab watch: sensor did not start (%s)" % (e,))
        gcmd.respond_info("oznlab watch: %.0f s - hold still 3 s for calibration, then tap" % secs)


    # ================= TAP (nozzle on bed, bounded descent) =================
    def _tap_client(self, rec):
        """per-run capture closure: drops out as soon as self._tap is no longer THIS record,
        so a new descent can never inherit the previous run's still-subscribed client"""
        def cb(msg):
            if self._tap is not rec: return False
            for t, f, z in msg.get('data', ()):
                if f > 0.: rec.append((t, f))
            return True
        return cb

    def _z_of_t(self, t, t0, z0, z1, v, a):
        """trapezoid profile z(t) for a move z0 -> z1 starting at print time t0"""
        d = z0 - z1
        if d <= 0.: return z0
        t_acc = v / a; d_acc = 0.5 * a * t_acc * t_acc
        if 2. * d_acc > d:                       # triangle
            t_acc = math.sqrt(d / a); d_acc = d / 2.; v = a * t_acc
        d_cruise = d - 2. * d_acc; t_cruise = d_cruise / v
        dt = t - t0
        if dt <= 0.: return z0
        if dt < t_acc: return z0 - 0.5 * a * dt * dt
        dt -= t_acc
        if dt < t_cruise: return z0 - d_acc - v * dt
        dt -= t_cruise
        if dt < t_acc: return z0 - d_acc - d_cruise - (v * dt - 0.5 * a * dt * dt)
        return z1

    def _move_time(self, z0, z1, v, a):
        d = z0 - z1
        if d <= 0.: return 0.
        t_acc = v / a; d_acc = 0.5 * a * t_acc * t_acc
        if 2. * d_acc > d: return 2. * math.sqrt(d / a)
        return 2. * t_acc + (d - 2. * d_acc) / v

    def _quant(self):
        """LDC output step in Hz at the configured data rate (400 -> 23, 200 -> 12, 100 -> 6):
        a faster conversion counts fewer reference clocks, so the step grows with the rate"""
        try:
            return max(1., 0.0588 * float(self.sensor.data_rate))
        except Exception:
            return 12.

    def _find_kink(self, ts, fs):
        """flat-then-ramp fit; returns (t_contact, slope Hz/s, step_amp) or None.
        O(n): every candidate split uses running sums, so a 400 Hz tap does not stall klippy."""
        n = len(ts)
        if n < 20: return None
        # shift the time origin for numerical sanity (print times are ~1e4 s)
        tz = ts[0]
        # prefix sums over f, f^2, t, t^2, t*f
        Sf = [0.]; Sff = [0.]; St = [0.]; Stt = [0.]; Stf = [0.]
        for t, f in zip(ts, fs):
            x = t - tz
            Sf.append(Sf[-1] + f); Sff.append(Sff[-1] + f * f)
            St.append(St[-1] + x); Stt.append(Stt[-1] + x * x); Stf.append(Stf[-1] + x * f)
        best = None
        for k in range(8, n - 8):
            # left: constant fit on [0, k)
            m = Sf[k] / k
            sse_l = Sff[k] - k * m * m
            # right: linear fit on [k, n)
            nr = n - k
            sf = Sf[n] - Sf[k]; sff = Sff[n] - Sff[k]
            st = St[n] - St[k]; stt = Stt[n] - Stt[k]; stf = Stf[n] - Stf[k]
            mt = st / nr; mf = sf / nr
            sxx = stt - nr * mt * mt
            if sxx <= 1e-12: continue
            sxy = stf - nr * mt * mf
            b = sxy / sxx
            sse_r = (sff - nr * mf * mf) - b * sxy
            tot = sse_l + sse_r
            if best is None or tot < best[0]: best = (tot, k, m, mf - b * mt, b)
        if best is None: return None
        tot, k, m, a0, b = best
        a0 -= b * tz                                # back to absolute time
        if abs(b) < 1e-9: return None
        t_c = (m - a0) / b                       # where the ramp crosses the flat level
        t_c = min(max(t_c, ts[max(0, k - 3)]), ts[min(n - 1, k + 3)])
        amp = abs(fs[-1] - m)
        return t_c, b, amp

    def _vb(self, gcmd=None):
        if gcmd is None:
            return self.verbose
        try:
            return bool(gcmd.get_int('VERBOSE', 1 if self.verbose else 0))
        except Exception:
            return self.verbose

    def _detail(self, gcmd, msg):
        """per-step numbers: always in klippy.log, on the console only when verbose"""
        logging.info(msg)
        if self._vb(gcmd):
            (gcmd.respond_info if gcmd is not None else self.gcode.respond_info)(msg)

    def _sync_gcode_pos(self):
        """toolhead.manual_move bypasses gcode_move; without this the next relative Z move and
        the monitor's gcode_position Z are wrong until an absolute move happens"""
        try:
            self.printer.lookup_object('gcode_move').reset_last_position()
        except Exception:
            logging.exception("oznlab: could not resync gcode_move")

    def _still_printing(self, script):
        """a PAUSE queued by the clog / crash watch runs only when the gcode queue is free:
        by then the print may have ended. PAUSE after the end would park a finished print."""
        if not script.strip().upper().startswith('PAUSE'):
            return True
        try:
            state = self.printer.lookup_object('print_stats').get_status(
                self.reactor.monotonic())['state']
        except Exception:
            return True                            # no print_stats: cannot tell, keep the old behaviour
        return state == 'printing'

    def _csv_path(self, fname):
        """user-given output file: only .csv, so a typo can never overwrite printer.cfg"""
        path = os.path.expanduser(fname.strip())
        if not path.lower().endswith('.csv'):
            raise self.gcode.error("oznlab: the output file must end in .csv (got %s)" % (fname,))
        return path

    def _gf(self, gcmd, name, default=None, **kw):
        """gcmd.get_float that also refuses nan / inf: Klipper's own range checks let nan through
        (every comparison with nan is False), and a nan Z offset or tap target moves the nozzle
        to nowhere"""
        v = gcmd.get_float(name, default, **kw)
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise gcmd.error("oznlab: %s must be a number" % (name,))
        return v

    def _client(self, name, cb, on_fail=None):
        """Sensor client that can never take Klipper down: an exception inside a bulk-sensor
        callback runs in a reactor timer and would shut the printer down mid-print. Here it
        stops only this feature, logs the traceback and says so on the console."""
        def guarded(msg):
            try:
                return cb(msg)
            except Exception:
                logging.exception("oznlab %s: internal error in the sensor callback", name)
                if on_fail is not None:
                    try:
                        on_fail()
                    except Exception:
                        logging.exception("oznlab %s: cleanup after the error failed", name)
                try:
                    self.gcode.respond_info("OznLab %s stopped after an internal error (details in "
                                            "klippy.log). The print goes on." % name)
                except Exception:
                    pass
                return False
        self.sensor.add_client(guarded)

    def _release_tap(self, toolhead=None, extra=0.6):
        """end of a tap / PA burst / test: stop the capture and keep the crash watch quiet
        until everything queued so far has run, plus a margin for the hotend to settle"""
        self._tap_on = False; self._tap = None
        try:
            th = toolhead or self.printer.lookup_object('toolhead')
            self._quiet_pt = max(self._quiet_pt, th.get_last_move_time() + extra)
        except Exception:
            logging.exception("oznlab: could not read the move queue end")

    def _noz_temp(self):
        try:
            h = self.printer.lookup_object('toolhead').get_extruder().get_heater()
            return float(h.get_status(self.reactor.monotonic())['temperature'])
        except Exception:
            return None

    def _trapq(self, name):
        # motion_report renamed trapqs -> dtrapqs in Oct 2025; support both
        mr = self.printer.lookup_object('motion_report', None)
        tqs = getattr(mr, 'dtrapqs', None)
        if tqs is None:
            tqs = getattr(mr, 'trapqs', None) or {}
        return tqs.get(name)

    def _other_probe(self):
        """a probe that is not this module's own nozzle probe (z_homing_probe: 1 registers
        itself as 'probe', which must not count as 'the printer already has a probe')"""
        p = self.printer.lookup_object('probe', None)
        return p is not None and p is not self.homing

    def _mesh_z_here(self, toolhead):
        """bed_mesh correction at the current XY, or 0 when no mesh is active."""
        if not self.tap_mesh_comp:
            return 0.
        # default=None: a printer without [bed_mesh] is normal, not an error
        bm = self.printer.lookup_object('bed_mesh', None)
        if bm is None or getattr(bm, 'z_mesh', None) is None:
            return 0.
        try:
            x, y = toolhead.get_position()[:2]
            return float(bm.z_mesh.calc_z(x, y))
        except Exception:
            logging.exception("oznlab tap: could not read the bed mesh")
            return 0.

    def _tap_once(self, toolhead, z_start, z_target, speed, accel, lift_speed=10.,
                  settle=0.3, pre=0.4, post=0.35):
        """One bounded descent. Returns (contact_z, Hz/um, ramp amplitude, pre-contact baseline Hz).
        Raises on a bad measurement; the caller is responsible for lifting on an error."""
        # the kinematics clamp Z moves to max_z_velocity; the timing model must use the same
        # speed or the contact Z is off by (speed error x descent time)
        try:
            speed = min(speed, getattr(toolhead.get_kinematics(), 'max_z_velocity', speed))
        except Exception:
            pass
        self._end_crash_test("a tap")
        toolhead.manual_move([None, None, z_start], lift_speed)
        toolhead.wait_moves(); toolhead.dwell(settle)
        # arm capture, then descend to the hard limit
        rec = []; self._tap = rec; self._tap_on = True
        self._client('tap', self._tap_client(rec))
        self.reactor.pause(self.reactor.monotonic() + pre)     # pre-contact baseline
        toolhead.manual_move([None, None, z_target], speed)
        # print time at the END of the queued move is exact even after an idle gap
        t0 = toolhead.get_last_move_time() - self._move_time(z_start, z_target, speed, accel)
        toolhead.wait_moves(); toolhead.dwell(min(0.15, post))
        self.reactor.pause(self.reactor.monotonic() + post)    # let the last batch arrive
        # lift first, THEN release: the crash watch must not judge the nozzle springing back
        # off the bed (manual_move does not update the gcode Z the watch reads either)
        toolhead.manual_move([None, None, z_start], lift_speed)
        self._release_tap(toolhead)
        toolhead.wait_moves()
        # keep pre-contact baseline + the descent, drop the plateau after the move ends
        # Fit the frequency against the commanded nozzle DEPTH, not against time: the ramp is a
        # straight line in depth all the way through the deceleration, while in time it bends
        # there (the time fit read the contact up to 17 um high on a slow Z axis or fast taps)
        t_end = t0 + self._move_time(z_start, z_target, speed, accel) - 0.01
        win = [(t, f) for (t, f) in rec if t >= t0 - 0.3 and t <= t_end]
        xs = [z_start - self._z_of_t(t, t0, z_start, z_target, speed, accel) for t, f in win]
        fs = [f for t, f in win]
        pre = [f for (t, f) in rec if t0 - 0.35 <= t <= t0 - 0.05]
        if len(xs) < 20:
            raise self.gcode.error("oznlab tap: not enough samples (%d) - sensor?" % len(xs))
        res = self._find_kink(xs, fs)
        if res is None:
            raise self.gcode.error("oznlab tap: no contact signature found")
        x_c, slope, amp = res
        if amp < max(4. * self._quant(), 60.):
            raise self.gcode.error("oznlab tap: contact amplitude too small (%.0f Hz) - "
                                   "did the nozzle reach the bed?" % amp)
        z_c = z_start - x_c
        n_ramp = sum(1 for x in xs if x > x_c)
        if n_ramp < 10:
            # too few samples on the ramp for a straight-line fit: the contact comes out high
            raise self.gcode.error("oznlab tap: only %d samples after the contact - the descent is too fast "
                                   "for the data rate. Lower SPEED (default 2)" % n_ramp)
        hz_per_um = abs(slope) / 1000.            # Hz/mm -> Hz/um
        # remembered for the crash watch and tap homing: the sensitivity climbs with the
        # hotend temperature (2 Hz/um cold, 10+ Hz/um at printing temperature)
        self.last_sens = hz_per_um; self.last_sens_t = self.reactor.monotonic()
        self._tap_T = self._noz_temp()
        f_pre = sum(pre) / len(pre) if pre else 0.
        return z_c, hz_per_um, amp, f_pre

    cmd_TAP_help = ("Nozzle-on-bed tap using the OznLab Sensor: OZNLAB_TAP [SAMPLES=5] [DISCARD=1] "
                    "[SPEED=2] [START=2] [TARGET=-0.3] [ADJUST=] [APPLY=1] [SAVE=1]")
    def cmd_TAP(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        if 'z' not in toolhead.get_status(self.reactor.monotonic())['homed_axes']:
            raise gcmd.error("oznlab tap: home first (G28)")
        self._free(gcmd, "tap")
        samples = gcmd.get_int('SAMPLES', self.tap_samples, minval=1, maxval=10)
        speed = self._gf(gcmd, 'SPEED', self.tap_speed, above=0.2, maxval=10.)
        z_start = self._gf(gcmd, 'START', self.tap_start_z, above=0.5, maxval=10.)
        z_target = self._gf(gcmd, 'TARGET', self.tap_target_z, minval=-0.6, maxval=0.0)
        adjust = self._gf(gcmd, 'ADJUST', self.tap_adjust_z, minval=-1., maxval=1.)
        apply = gcmd.get_int('APPLY', 1)
        discard = gcmd.get_int('DISCARD', 1, minval=0, maxval=3)   # priming taps, not counted
        save = gcmd.get_int('SAVE', 1)                              # SAVE=0: apply only, no SAVE_CONFIG entry
        # max_z_accel lives on the kinematics object, not on the toolhead
        try:
            kin = toolhead.get_kinematics()
            accel = min(toolhead.max_accel, getattr(kin, 'max_z_accel', toolhead.max_accel))
            z_min = kin.rails[2].get_range()[0]
        except Exception:
            accel = 100.; z_min = None
        accel = accel or 100.
        if z_min is not None and z_target < z_min:
            raise gcmd.error("oznlab tap: TARGET=%.2f is below [stepper_z] position_min=%.2f - "
                             "set position_min to about -1 or raise TARGET" % (z_target, z_min))
        lift_speed = 10.
        results = []; sens = []
        try:
            for i in range(samples + discard):
                z_c, hz_per_um, amp, f_pre = self._tap_once(toolhead, z_start, z_target,
                                                            speed, accel, lift_speed)
                if i < discard:
                    self._detail(gcmd, "oznlab tap: priming tap (not used) z=%.4f" % z_c)
                    continue
                results.append(z_c); sens.append(hz_per_um)
                self._detail(gcmd, "oznlab tap %d/%d: z=%.4f  ramp %.0f Hz over %.2f mm, %.1f Hz/um"
                             % (i + 1 - discard, samples, z_c, amp, z_c - z_target, hz_per_um))
        except self.gcode.error as e:
            self._job_note('tap', "failed: %s" % (e,))
            raise
        finally:
            # never leave the sensor client subscribed or the nozzle pressed against the bed
            self._release_tap()
            try:
                toolhead.manual_move([None, None, z_start], lift_speed); toolhead.wait_moves()
            except Exception:
                logging.exception("oznlab tap: could not lift after an error")
            self._sync_gcode_pos()
        results.sort()
        med = results[len(results) // 2]
        mean = sum(results) / len(results)
        sd = math.sqrt(sum((r - mean) ** 2 for r in results) / len(results))
        self._detail(gcmd, "oznlab tap: median z=%.4f mean %.4f stddev %.4f range %.4f sensitivity %.1f Hz/um"
                     % (med, mean, sd, results[-1] - results[0], sum(sens) / len(sens)))
        spread = "%d taps within %.3f mm" % (len(results), results[-1] - results[0]) \
            if len(results) > 1 else "1 tap, not cross-checked"
        if len(results) >= 2 and sd > 0.025:
            gcmd.respond_info("OznLab tap: the taps disagree (%.3f mm) - z offset NOT changed. "
                              "Clean the nozzle and try again." % (results[-1] - results[0]))
            self._job_note('tap', "taps disagreed (%.3f mm), offset not changed" % (results[-1] - results[0]))
            return
        if not apply:
            gcmd.respond_info("OznLab tap: contact at z=%.3f (%s)" % (med, spread))
        if apply:
            mesh_z = self._mesh_z_here(toolhead)
            z_off = med + adjust - mesh_z
            self._detail(gcmd, "oznlab tap: offset %.4f = contact %.4f + adjust %.3f - mesh here %.4f"
                         % (z_off, med, adjust, mesh_z))
            self.gcode.run_script_from_command("SET_GCODE_OFFSET Z=%.4f MOVE=0" % z_off)
            if save:
                configfile = self.printer.lookup_object('configfile')
                configfile.set(self.cfg_name, 'tap_z', "%.4f" % z_off)
            gcmd.respond_info("OznLab tap: z offset %.3f set (%s)%s"
                              % (z_off, spread, " - SAVE_CONFIG to keep it" if save else ""))
            self.last_tap_z = z_off
            self._job_note('tap', "%.3f mm (%s)" % (z_off, spread))

    # ================= PRESSURE ADVANCE (extrude step -> pressure rise time constant) =================
    # Linear melt model: tau * dP/dt = v_in - v_out, v_out ~ P.  Klipper's PA feeds E + PA*v, which
    # cancels the lag exactly when PA == tau.  We measure tau directly as the rise time constant
    # of the sensor signal (proportional to melt pressure / nozzle force) after a step in extruder
    # speed, with PA temporarily set to 0 so the extruder does not pre-shape the step.
    @staticmethod
    def _fit_tau(pts):
        """pts: (t, x) with x the remaining fraction (1 -> 0). log-linear LSQ -> tau [s]"""
        pts = [(t, math.log(x)) for t, x in pts if 0. < x < 1.]
        n = len(pts)
        if n < 6: return None
        sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
        sxx = sum(p[0] * p[0] for p in pts); sxy = sum(p[0] * p[1] for p in pts)
        den = n * sxx - sx * sx
        if den <= 0.: return None
        slope = (n * sxy - sx * sy) / den
        if slope >= 0.: return None
        return -1. / slope

    @staticmethod
    def _fit_rise(pts):
        """pts: (dt, y) from the speed step. Model y = A*(1-exp(-(dt-td)/tau)) + B*(dt-td):
        fast pressure rise (tau) on top of a slow linear creep (B). Grid over tau/td, LSQ for A/B."""
        best = None
        for k in range(40):
            tau = 0.02 * (30. ** (k / 39.))            # 0.02 .. 0.6 s
            for j in range(21):
                td = 0.01 * j                            # 0 .. 0.2 s dead time
                s11 = s12 = s22 = s1y = s2y = syy = 0.; n = 0
                for dt, y in pts:
                    u = dt - td
                    if u < 0.: e1 = 0.; e2 = 0.
                    else: e1 = 1. - math.exp(-u / tau); e2 = u
                    s11 += e1 * e1; s12 += e1 * e2; s22 += e2 * e2
                    s1y += e1 * y; s2y += e2 * y; syy += y * y; n += 1
                den = s11 * s22 - s12 * s12
                if den <= 1e-12: continue
                A = (s1y * s22 - s2y * s12) / den; B = (s2y * s11 - s1y * s12) / den
                sse = syy - A * s1y - B * s2y
                if best is None or sse < best[0]: best = (sse, tau, td, A, B, n)
        if best is None: return None
        sse, tau, td, A, B, n = best
        return tau, td, A, B, math.sqrt(max(sse, 0.) / max(n, 1))

    def _pa_analyze(self, rec, t0, t1):
        """rec: (t, f) samples; t0/t1: print time of extruder speed step up / down"""
        base = [f for t, f in rec if t0 - 0.45 <= t <= t0 - 0.05]
        plat = [f for t, f in rec if t1 - 0.30 <= t <= t1 - 0.02]
        if len(base) < 10 or len(plat) < 10:
            raise self.gcode.error("oznlab pa: not enough samples (base %d, plateau %d)" % (len(base), len(plat)))
        fb = sum(base) / len(base); P = sum(plat) / len(plat) - fb
        if abs(P) < 300.:
            raise self.gcode.error("oznlab pa: no pressure signal (%.0f Hz) - filament loaded? hotend hot?" % P)
        fit = self._fit_rise([(t - t0, f - fb) for t, f in rec if t0 - 0.02 <= t <= t1 - 0.02])
        if fit is None: return P, None, None, None, None, None
        tau_r, td, A, B, rms = fit
        decay = [(t - t1, (f - fb) / P) for t, f in rec if t1 <= t <= t1 + 2.5]
        tau_d = self._fit_tau([(dt, x) for dt, x in decay if 0.3 <= x <= 0.9])
        return P, tau_r, td, tau_d, (A, B, rms), fb

    def _pa_client(self, rec):
        """per-run capture callback: stays subscribed only while rec is the active record"""
        def cb(msg):
            if self._tap is not rec: return False
            for t, f, z in msg.get('data', ()):
                if f > 0.: rec.append((t, f))
            return True
        return cb

    cmd_CALIBRATE_PA_help = ("Measure melt pressure rise time and set pressure advance (not saved): "
                             "OZNLAB_CALIBRATE_PA [SPEEDS=3] [DURATION=1.5] [SAMPLES=1] [DISCARD=1] "
                             "[PRIME=12] [RETRIES=2] [SCALE=] [APPLY=1] [FILE=]  (SCALE defaults to this filament's pa_scale)")
    def cmd_CALIBRATE_PA(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        self._free(gcmd, "pa")
        try:
            speeds = [float(s) for s in gcmd.get('SPEEDS', "%.2f" % self.pa_speed).split(',')]
        except ValueError:
            raise gcmd.error("oznlab pa: SPEEDS must be comma separated mm/s, e.g. SPEEDS=3,6")
        secs = self._gf(gcmd, 'DURATION', self.pa_duration, minval=0.8, maxval=5.)
        samples = gcmd.get_int('SAMPLES', 1, minval=1, maxval=5)
        discard = gcmd.get_int('DISCARD', 1, minval=0, maxval=2)   # priming runs (filament slack), not counted
        prime = self._gf(gcmd, 'PRIME', self.pa_prime, minval=0., maxval=50.)
        scale_auto, scale_src, scale_known = self._pa_scale_for()
        scale = self._gf(gcmd, 'SCALE', scale_auto, above=0.005, maxval=3.)
        if gcmd.get('SCALE', None) is None and not scale_known:
            j = self._job
            if not (j is not None and j.get('warned') == self.filament):   # FILAMENT said it already
                gcmd.respond_info(self._scale_warning())
        apply = gcmd.get_int('APPLY', 1)
        retries = gcmd.get_int('RETRIES', 2, minval=0, maxval=4)
        fname = gcmd.get('FILE', None)                 # optional raw dump: run,speed,time,frequency
        extruder = toolhead.get_extruder()
        now = self.reactor.monotonic()
        st = extruder.get_status(now)
        if not st.get('can_extrude', True):
            raise gcmd.error("oznlab pa: the nozzle is below min_extrude_temp - heat it to printing temperature first")
        pa_old = st.get('pressure_advance', 0.)
        v_max = getattr(extruder, 'max_e_velocity', 1e9)
        accel = getattr(extruder, 'max_e_accel', 1500.) or 1500.
        speeds = [min(v, v_max) for v in speeds if v > 0.]
        if not speeds: raise gcmd.error("oznlab pa: no valid speeds")
        results = []; fh = None
        if fname:      # opened first: a bad path must not leave PA at 0 and M83 active
            try:
                fh = open(self._csv_path(fname), 'w'); fh.write("run,speed,t0,t1,time,frequency\n")
            except OSError as e:
                raise gcmd.error("oznlab pa: cannot write %s (%s)" % (fname, e))
        run = 0; n_fail = 0
        try:
          # inside the try: if any of these three lines fails the finally still restores PA / state
          self._end_crash_test("OZNLAB_CALIBRATE_PA")
          self.gcode.run_script_from_command("SAVE_GCODE_STATE NAME=oznlab_pa\nM83\nM220 S100\nM221 S100\nSET_PRESSURE_ADVANCE ADVANCE=0")
          for attempt in range(retries + 1):
            # The melt zone empties while the hotend sits hot (ooze). Measuring on an empty melt
            # zone gives a creeping rise and a tau 2-3x too high, so every attempt refills it first
            # and a failed attempt refills harder before trying again.
            p_now = prime * (1.5 ** attempt)
            if p_now > 0.:
                self.gcode.run_script_from_command("G1 E%.3f F300" % p_now)
                toolhead.wait_moves(); toolhead.dwell(1.0); toolhead.wait_moves()
            for v in speeds:
                for i in range(samples + discard):
                      run += 1
                      toolhead.wait_moves(); toolhead.dwell(0.6); toolhead.wait_moves()   # pressure bleed-off
                      self.reactor.pause(self.reactor.monotonic() + 0.3)  # previous client drops out
                      rec = []; self._tap = rec
                      self._client('pa', self._pa_client(rec))
                      self.reactor.pause(self.reactor.monotonic() + 0.6)  # baseline
                      self.gcode.run_script_from_command("G1 E%.3f F%.0f" % (v * secs, v * 60.))
                      t1 = toolhead.get_last_move_time()                  # exact print time of the stop
                      t0 = t1 - (secs + v / accel)                        # trapezoid: secs at v plus accel ramp
                      toolhead.wait_moves(); toolhead.dwell(2.2)          # decay window
                      toolhead.wait_moves()
                      self.reactor.pause(self.reactor.monotonic() + 0.35)
                      self._release_tap()
                      if fh is not None:
                          for t, f in rec: fh.write("%d,%.2f,%.4f,%.4f,%.4f,%.2f\n" % (run, v, t0, t1, t, f))
                      try:
                          P, tau_r, td, tau_d, fit, fb = self._pa_analyze(rec, t0, t1)
                          if tau_r is None:
                              raise gcmd.error("could not fit the pressure rise")
                      except self.gcode.error as e:
                          # an empty melt zone on the very first run shows up here as "no pressure
                          # signal"; that is exactly what the next attempt's bigger prime is for
                          n_fail += 1
                          self._detail(gcmd, "oznlab pa %.1f mm/s: %s (ignored)" % (v, e))
                          continue
                      A, B, rms = fit
                      tag = "(priming, ignored)" if i < discard else ""
                      # creep is Hz/s, so compare it over the actual measurement window
                      bad = (tau_r > self.pa_tau_max or abs(B) * secs > 0.20 * abs(A)
                             or rms > 0.06 * abs(A) + 40.)
                      if bad and i >= discard: tag = "(UNRELIABLE - creeping rise, melt zone not primed? ignored)"
                      if i >= discard and not bad: results.append((v, A, tau_r, tau_d, fb))
                      self._detail(gcmd, "oznlab pa %.1f mm/s: step %.0f Hz  rise tau %.4f s  delay %.3f s  "
                                   "creep %.0f Hz/s  fit rms %.0f Hz  decay tau %s %s"
                                   % (v, A, tau_r, td, B, rms, "%.3f s" % tau_d if tau_d is not None else "n/a", tag))
            if results: break
            if attempt < retries:
                gcmd.respond_info("OznLab PA: melt zone not settled yet, priming more and retrying (%d/%d)"
                                  % (attempt + 2, retries + 1))
        finally:
            self._release_tap()
            if fh is not None: fh.close()
            try:
                self.gcode.run_script_from_command("SET_PRESSURE_ADVANCE ADVANCE=%.5f\n"
                                                   "RESTORE_GCODE_STATE NAME=oznlab_pa" % pa_old)
            except Exception:
                logging.exception("oznlab pa: could not restore pressure advance / gcode state")
        if not results:
            # drop the old reference: monitoring against a calibration taken in a different
            # thermal state is worse than not monitoring at all (it fires false runouts)
            self.pa_cal = None
            self._job_note('pa', "no reliable measurement, PA stayed %.4f" % pa_old)
            if self._mon is not None:
                self._mon_stop("the PA reference was dropped")
            gcmd.respond_info("OznLab PA: no reliable measurement - pressure advance stays at %.4f, "
                              "clog/runout watch has no reference for this print" % pa_old)
            return
        taus = sorted(r[2] for r in results)
        tau = taus[len(taus) // 2]
        pa_new = tau * scale
        # reference for the print monitor: pressure amplitude at the calibration speed, P ~ v^n
        v_ref = min(r[0] for r in results)          # only the runs that survived the reliability check
        amps = [abs(r[1]) for r in results if r[0] == v_ref]
        p_ref = sum(amps) / len(amps)
        sign = -1. if sum(r[1] for r in results) < 0. else 1.
        n_exp = self.flow_exp
        v_hi = max(r[0] for r in results)
        if v_hi > v_ref:
            lo = [abs(r[1]) for r in results if r[0] == v_ref]; hi = [abs(r[1]) for r in results if r[0] == v_hi]
            lo_m = sum(lo) / len(lo); hi_m = sum(hi) / len(hi)
            if lo_m > 1. and hi_m > 1.:
                n_exp = min(1.5, max(0.1, math.log(hi_m / lo_m) / math.log(v_hi / v_ref)))
        taus_d = sorted(r[3] for r in results if r[3] is not None)
        tau_d = taus_d[len(taus_d) // 2] if taus_d else 0.5
        self.pa_cal = dict(results=results, tau=tau, pa=pa_new, v_ref=v_ref, p_ref=p_ref, sign=sign,
                           n=n_exp, tau_d=tau_d, fb=results[-1][4], t=self.reactor.monotonic())
        if self._mon is not None: self._mon_reload()
        self._detail(gcmd, "oznlab pa: tau %.4f s x scale %.3f -> %.4f (was %.4f)" % (tau, scale, pa_new, pa_old))
        if apply:
            self.gcode.run_script_from_command("SET_PRESSURE_ADVANCE ADVANCE=%.5f" % pa_new)
            gcmd.respond_info("OznLab PA: pressure advance %.4f set (was %.4f)" % (pa_new, pa_old))
            self.last_pa = pa_new
            self._job_note('pa', "%.4f (tau %.3f s x pa_scale %.3f%s)"
                           % (pa_new, tau, scale, (" for %s" % self._fil_disp()) if scale_known and self.filament
                              else "" if scale_known else ", default"))
        else:
            gcmd.respond_info("OznLab PA: measured %.4f (tau %.3f s) - not applied" % (pa_new, tau))

    # ---- filament of the current print and its pa_scale ----
    @staticmethod
    def _fil_key(name):
        name = (name or '').strip().lower().replace('+', ' plus ')
        return re.sub(r'[^a-z0-9]+', '_', name).strip('_')

    def _pa_scale_for(self, key=None):
        """(scale, where it came from, known) for a filament key (default: this print's)"""
        key = self.filament if key is None else key
        if key and key in self.pa_scales:
            return self.pa_scales[key], "pa_scale_%s" % key, True
        if key:
            return self.pa_scale, "pa_scale (default)", False
        # filament unknown: the default is all there is. Only 'known' when nothing per filament exists.
        return self.pa_scale, "pa_scale", not self.pa_scales

    def _fil_disp(self):
        return self.filament_name or (self.filament or '').upper()

    def _scale_warning(self):
        if self.filament:
            return ("OznLab PA: no pa_scale for %s yet - using the default %.3f, pressure advance may be "
                    "off and the print may suffer. Print a PA pattern with this filament, then "
                    "OZNLAB_PA_SCALE PATTERN_PA=<best value>." % (self._fil_disp(), self.pa_scale))
        return ("OznLab PA: filament unknown - using the default pa_scale %.3f. Pass the filament from the "
                "slicer (PRINT_START FILAMENT=...) so each filament uses its own scale." % self.pa_scale)

    cmd_FILAMENT_help = "Tell the sensor which filament this print uses (PRINT_START calls it): OZNLAB_FILAMENT TYPE=ASA"
    def cmd_FILAMENT(self, gcmd):
        raw = gcmd.get('TYPE', '').strip().strip('"').strip("'")
        self.filament = self._fil_key(raw) or None
        self.filament_name = raw.upper() if self.filament else None
        if self._job is not None and self._job.get('auto'):
            self._job['filament'] = self._fil_disp(); self._job['auto'] = False   # same print, now named
        else:
            self._job_start()  # PRINT_START calls this first: a new print begins
        scale, src, known = self._pa_scale_for()
        if self.filament is None:
            msg = "OznLab filament: unknown (no TYPE)"
            if self.pa_scales:
                msg += " - " + self._scale_warning().replace("OznLab PA: ", "")
        elif known:
            msg = "OznLab filament: %s - pa_scale %.3f" % (self._fil_disp(), scale)
        else:
            msg = "OznLab filament: %s - %s" % (self._fil_disp(),
                                                   self._scale_warning().replace("OznLab PA: ", ""))
        if self._job is not None and not known:
            self._job['warned'] = self.filament
        gcmd.respond_info(msg)

    cmd_PA_SCALE_help = ("One-time setup per filament: OZNLAB_PA_SCALE PATTERN_PA=<best PA from a pattern test> "
                         "[TYPE=ASA] -> stores pa_scale_<filament>")
    def cmd_PA_SCALE(self, gcmd):
        if self.pa_cal is None:
            raise gcmd.error("oznlab: run OZNLAB_CALIBRATE_PA first (same filament/temperature as the pattern test)")
        pattern = self._gf(gcmd, 'PATTERN_PA', above=0.)
        key = self._fil_key(gcmd.get('TYPE', '')) or self.filament
        scale = round(pattern / self.pa_cal['tau'], 4)      # checked as it will be saved
        if not 0.005 < scale <= 3.0:                # must stay inside the range the config accepts at boot
            raise gcmd.error("oznlab: computed pa_scale %.4f is out of range (tau %.4f s) - "
                             "re-run OZNLAB_CALIBRATE_PA and check PATTERN_PA" % (scale, self.pa_cal['tau']))
        configfile = self.printer.lookup_object('configfile')
        if key:
            opt = 'pa_scale_%s' % key
            self.pa_scales[key] = scale
            where = "for %s" % key.upper()
        else:
            opt = 'pa_scale'
            self.pa_scale = scale; self._pa_scale_set = True
            where = "default (filament unknown; add TYPE=ASA etc. to store it per filament)"
        configfile.set(self.cfg_name, opt, "%.4f" % scale)
        gcmd.respond_info("OznLab: %s %.4f (= %.4f / tau %.4f), %s - SAVE_CONFIG to keep it"
                          % (opt, scale, pattern, self.pa_cal['tau'], where))

    # ================= PRINT MONITOR (clog / runout) =================
    # Expected pressure from the commanded extruder speed: P_exp = P_ref * (v / v_ref)^n, lagged with the
    # measured rise / decay time constants.  The sensor baseline (thermal drift) is tracked slowly while
    # extruding and re-zeroed quickly when the extruder has been idle.  Ratio = P_meas / P_exp:
    # Printing adds layer back-pressure on top of the free-air reference, so the normal printing level k
    # is learned during the first 20 s of extrusion (then tracked slowly) and decisions use ratio / k:
    #   > clog_ratio   in confirm_windows consecutive windows -> CLOG    -> clog_gcode
    #   < runout_ratio in confirm_windows consecutive windows -> RUNOUT  -> runout_gcode
    # Nothing is judged on the first layer (monitor_min_z): nozzle/bed contact forces look like pressure.
    def _mon_reload(self):
        m = self._mon; c = self.pa_cal
        m.update(p_ref=c['p_ref'], v_ref=c['v_ref'], n=c['n'], sign=c['sign'],
                 tau_r=max(0.03, c['tau']), tau_d=max(0.1, c['tau_d']))

    def _mon_fire(self, kind, script, ratio):
        m = self._mon
        m['fired'] = kind; m['n_' + kind] += 1
        what = ("CLOG: nozzle pressure %.1fx the normal level" % ratio if kind == 'clog' else
                "RUNOUT: nozzle pressure only %.0f%% of normal - out of filament or slipping" % (100. * ratio))
        self.gcode.respond_info("OznLab %s%s" % (what, " -> %s" % script if script else ""))
        self._job_event("%s %s" % (kind.upper(), ("%.1fx" % ratio) if kind == 'clog' else ("%.0f%%" % (100. * ratio))))
        if not script: return
        try:
            paused = self.printer.lookup_object('pause_resume').get_status(
                self.reactor.monotonic()).get('is_paused', False)
        except Exception:
            paused = False
        if paused and script.strip().upper().startswith('PAUSE'):
            logging.info("oznlab: already paused, %s action skipped", kind); return
        def _run(eventtime, script=script, kind=kind):
            try:
                if not self._still_printing(script):
                    logging.info("oznlab: %s action skipped, the print is no longer running", kind); return
                self.gcode.run_script(script)
            except Exception as e:                 # an exception here would shut klippy down
                logging.exception("oznlab: %s action failed", kind)
                self.gcode.respond_info("OznLab: the %s action '%s' failed (%s) - the print goes on. "
                                        "PAUSE needs [pause_resume] in printer.cfg." % (kind, script, e))
        self.reactor.register_callback(_run)

    def _mon_cb(self, msg, mine=None):
        m = self._mon
        if m is None or (mine is not None and m is not mine): return False
        m['rx'] = self.reactor.monotonic(); m['blind'] = False
        toolhead = self.printer.lookup_object('toolhead')
        extruder = toolhead.get_extruder()
        try:
            m['z'] = self.printer.lookup_object('gcode_move').get_status(self.reactor.monotonic())['gcode_position'][2]
        except Exception:
            m['z'] = 0.                            # unknown Z -> behave like the first layer (no decisions)
        if self._tap is not None:
            # TAP / CALIBRATE_PA / the slicer tests are running: nozzle contact or a deliberate
            # pressure step, neither is print pressure. Drop the window and resync afterwards.
            m['win'] = dict(t0=-1e9, t=0., hi=0., lo=0.); m['t_last'] = None
            return True
        for t, f, z in msg.get('data', ()):
            if f <= 0.: continue
            try:
                e = extruder.find_past_position(t)
            except Exception:
                e = None
            if m['t_last'] is None or e is None or m['e_last'] is None:
                m['t_last'] = t; m['e_last'] = e
                if m['base'] is None: m['base'] = f
                continue
            dt = t - m['t_last']
            if dt <= 0.: continue
            v = (e - m['e_last']) / dt
            m['t_last'] = t; m['e_last'] = e
            v_prev = m['v']                        # compare against the EMA BEFORE it moves
            m['v'] += (v - m['v']) * min(1., dt / 0.1)
            vp = max(m['v'], 0.)
            p_ss = m['p_ref'] * (vp / m['v_ref']) ** m['n'] if vp > 0.02 else 0.
            tau = m['tau_r'] if p_ss > m['p_exp'] else m['tau_d']
            m['p_exp'] += (p_ss - m['p_exp']) * min(1., dt / tau)
            if abs(m['v']) > 0.2: m['t_move'] = t
            # ---- baseline: the frequency the sensor would read with NO melt pressure ----
            # Two things move the raw frequency slowly: the coil's own thermal drift (~12 Hz/s
            # measured on a warming machine, present whether or not filament flows) and the melt
            # pressure level itself (halves over 10 min as the melt thins - present only while
            # extruding). They cannot be told apart by rate, only by correlation with flow. So
            # the baseline is observed at the END of every retract/travel gap, from measured
            # frequencies alone: after a gap of g seconds the pressure has decayed to
            # rem = exp(-g/tau_d) of its flowing value, so f_end = base + rem*(f_flow - base)
            # and base = (f_end - rem*f_flow) / (1 - rem). No model pressure, no k, nothing
            # circular. Between gaps the learned drift rate is extrapolated; the pressure
            # level is left entirely to k. (A baseline that crept during extrusion absorbed a
            # x2.5 clog in simulation.)
            resid = m['sign'] * (f - m['base']) - m['p_exp']
            if m['t_seed'] is None: m['t_seed'] = t
            flowing = v > 0.2                      # commanded velocity: exact, no EMA lag
            if flowing and not m['flowing']:
                # gap just ended: one clean observation of the baseline
                g = t - m['t_stop'] if m['t_stop'] is not None else 0.
                if g >= 0.35 and m['f_flow'] is not None and m['f_end']:
                    rem = math.exp(-g / max(m['tau_d'], 0.05))
                    f_end = sorted(m['f_end'])[len(m['f_end']) // 2]
                    if rem < 0.7:
                        b_obs = (f_end - rem * m['f_flow']) / (1. - rem)
                        wgt = min(1., 1. - rem)             # longer gap -> more decayed -> more trust
                        if m['t_obs'] is not None:
                            gap = t - m['t_obs']
                            if 1.0 < gap < 120.:
                                rate = (b_obs - m['b_obs']) / gap
                                m['drift'] += (rate - m['drift']) * min(1., gap / 60.)
                        m['base'] += (b_obs - m['base']) * wgt
                        m['t_obs'] = t; m['b_obs'] = b_obs
                m['f_end'] = []
            elif not flowing and m['flowing']:
                m['t_stop'] = t; m['f_end'] = []
            m['flowing'] = flowing
            if not flowing:
                m['f_end'].append(f); m['f_end'] = m['f_end'][-5:]     # last samples of the gap
            elif abs(v - v_prev) < 0.25 * max(m['v'], 0.1) and t - m['t_move'] < 0.1:
                # steadily flowing: remember the flowing frequency for the next gap's estimate
                m['f_flow'] = f if m['f_flow'] is None else m['f_flow'] + (f - m['f_flow']) * min(1., dt / 1.0)
            if t - m['t_seed'] < 30. and m['t_obs'] is None:
                # SEEDING (until the first usable gap): the monitor usually starts mid-extrusion,
                # so the first sample lands in the middle of the pressure signal. Converge onto
                # p = p_exp fast; no decision is made in this phase anyway.
                m['base'] += m['sign'] * resid * min(1., dt / 1.5)
            elif flowing:
                # extrapolate the drift, plus a tiny safety creep towards the k-adjusted
                # expectation so an error cannot grow without bound during a long stretch with
                # no gap at all (vase mode). Frozen while an anomaly is building.
                m['base'] += m['drift'] * dt
                if not self._mon_pending(m):
                    resid_k = m['sign'] * (f - m['base']) - m['k'] * m['p_exp']
                    lim = self.base_drift * dt
                    m['base'] += m['sign'] * max(-lim, min(lim, resid_k * dt / 60.))
            else:
                m['base'] += m['drift'] * dt
            p = m['sign'] * (f - m['base'])
            m['p'] = p; m['t'] = t
            if m['t_start'] is None: m['t_start'] = t
            if m['z'] < self.mon_min_z:
                m['ratio'] = None; continue          # first layer: nozzle/bed contact forces dominate the signal
            # judge only in quasi-steady extrusion: speed settled and the modelled lag mostly over
            steady = (abs(v - v_prev) < 0.25 * max(m['v'], 0.1)
                      and abs(p_ss - m['p_exp']) < 0.15 * max(p_ss, 1.))
            active = (steady and m['v'] > self.mon_min_speed and m['p_exp'] > 0.15 * m['p_ref']
                      and (t - m['t_start']) > 2.0)
            if m['fh'] is not None:
                m['nlog'] += 1
                if m['nlog'] % 10 == 0:
                    try:
                        m['fh'].write("%.3f,%.2f,%.3f,%.1f,%.1f,%.1f,%.1f,%.3f,%.3f,%s,%d\n"
                                      % (t, m['z'], m['v'], f, m['base'], p, m['p_exp'],
                                         p / m['p_exp'] if m['p_exp'] > 1. else 0., m['k'],
                                         "%.3f" % m['ratio'] if m['ratio'] is not None else "",
                                         1 if active else 0))
                    except Exception:
                        logging.exception("oznlab monitor: log write failed")
                        m['fh'] = None
            if not active:
                m['ratio'] = None; continue          # travels / retracts / transients are not judged
            r = p / m['p_exp']
            # Printing adds back-pressure on top of the free-air reference. Learn the print's normal level k
            # (fast for the first 20 s of extrusion, then slowly, bounded); decisions use r/k.
            m['t_act'] += dt
            if not self._mon_pending(m):           # frozen while an anomaly is building up
                tau_k = 5. if m['t_act'] < 20. else 60.
                m['k'] += (r - m['k']) * min(1., dt / tau_k)
                # The floor was 0.4 and it bound for 300 s on a real print: as the machine warms
                # the melt thins and the pressure at a fixed flow halves in 10 minutes, so k has
                # to be free to go well below the free-air reference.
                m['k'] = min(4.0, max(0.15, m['k']))
            if m['t_act'] < 10.: m['ratio'] = r; continue        # still learning
            r = r / m['k']; m['ratio'] = r
            # a step away from 1 starts the k hold (see _mon_pending); back inside the band it ends
            if abs(r - 1.) > 0.4:
                if m['t_dev'] is None: m['t_dev'] = t
            else:
                m['t_dev'] = None
            # A reference from a different thermal state (or a calibration that silently went
            # wrong) reads low from the very first window and looks exactly like a runout.
            # A real fault starts from a healthy signal, so nothing is judged until the ratio
            # has actually been healthy for a while.
            r_raw = p / m['p_exp']
            if 0.6 < r < 1.6 and 0.1 < r_raw < 8.:
                m['ok_t'] += dt
            elif m['ok_t'] < 20. and m['t_act'] > 60. and not m['warned']:
                m['warned'] = True; m['n_warn'] += 1
                self.gcode.respond_info("OznLab monitor: pressure never matched the start-of-print "
                                        "measurement, clog/runout watch stays passive this print")
                logging.info("oznlab monitor: never matched the reference (ratio %.2f, raw %.2f)" % (r, r_raw))
            if m['ok_t'] < 20.:
                continue
            # Persistence: the anomaly must dominate several consecutive windows (default 3 x 10 s) of
            # extrusion time before anything fires. A single spike or one contact event never does.
            w = m['win']
            w['t'] += dt
            if r > self.clog_ratio: w['hi'] += dt
            if -0.3 < r < self.runout_ratio: w['lo'] += dt      # strongly negative = nozzle contact, not runout
            if t - w['t0'] >= self.confirm_time:
                if w['t'] >= max(1.0, 0.3 * self.confirm_time):
                    hi_dom = w['hi'] > 0.5 * w['t']; lo_dom = w['lo'] > 0.5 * w['t']
                    m['n_hi'] = m['n_hi'] + 1 if hi_dom else 0
                    m['n_lo'] = m['n_lo'] + 1 if lo_dom else 0
                    if m['n_hi'] or m['n_lo']:      # klippy.log only - the console stays quiet until a decision
                        logging.info("oznlab monitor: window hi %d lo %d  ratio %.2f  v %.1f mm/s  z %.2f",
                                     m['n_hi'], m['n_lo'], r, m['v'], m['z'])
                    if m['n_hi'] >= self.confirm_windows and m['fired'] != 'clog':
                        self._mon_fire('clog', self.clog_gcode, r); m['n_hi'] = 0
                    if m['n_lo'] >= self.confirm_windows and m['fired'] != 'runout':
                        self._mon_fire('runout', self.runout_gcode, r); m['n_lo'] = 0
                    # a fired state is only released by a window that was actually clean,
                    # otherwise the same fault re-fires every confirm_windows x confirm_time
                    if not hi_dom and not lo_dom: m['fired'] = None
                m['win'] = dict(t0=t, t=0., hi=0., lo=0.)
        # stop automatically once a print job has ended
        try:
            state = self.printer.lookup_object('print_stats').get_status(self.reactor.monotonic())['state']
        except Exception:
            state = 'printing'
        if state == 'printing': m['seen_print'] = True
        elif m['seen_print'] and state != 'paused':
            self._mon_stop("print %s" % state); return False
        return True

    @staticmethod
    def _mon_pending(m):
        """True while the level learner k and the baseline creep must hold still: an anomaly
        window is being counted, the current window is trending that way, or the ratio has
        recently stepped away from 1 (a fault develops in seconds, the legitimate level drift
        takes minutes - k must not chase the fast one). The hold is released after 60 s if no
        window confirmed anything, so a genuine slow change is still absorbed eventually."""
        if m['n_hi'] or m['n_lo']: return True
        w = m['win']
        if w['t'] > 2.0 and (w['hi'] > 0.3 * w['t'] or w['lo'] > 0.3 * w['t']): return True
        return m['t_dev'] is not None and (m['t'] - m['t_dev']) < 60.

    def _mon_stop(self, why):
        m = self._mon; self._mon = None
        if m is None: return
        if m.get('fh') is not None:
            try: m['fh'].close()
            except Exception: logging.exception("oznlab monitor: could not close the log")
        ev = m['n_clog'] + m['n_runout']
        self._job_note('monitor', "%d clog, %d runout" % (m['n_clog'], m['n_runout']) if ev else "no events")
        self.gcode.respond_info("OznLab monitor: off%s" % (
            "" if not ev else " - %d clog, %d runout" % (m['n_clog'], m['n_runout'])))
        logging.info("oznlab monitor: off (%s) - %d clog, %d runout, %d warnings"
                     % (why, m['n_clog'], m['n_runout'], m['n_warn']))

    cmd_MONITOR_help = ("Clog / runout watch during a print: "
                        "OZNLAB_MONITOR | OFF=1 | STATUS=1 | LOG=~/printer_data/config/mon.csv")
    def cmd_MONITOR(self, gcmd):
        if gcmd.get_int('OFF', 0):
            self._mon_stop("stopped"); return
        if gcmd.get_int('STATUS', 0):
            m = self._mon
            if m is None: gcmd.respond_info("OznLab monitor: off"); return
            if m['ok_t'] < 20.:
                state = "learning (%.0f s of extrusion so far)" % m['t_act']
            else:
                state = "watching, pressure %s of normal" % (
                    "%.0f%%" % (100. * m['ratio']) if m['ratio'] is not None else "-")
            gcmd.respond_info("OznLab monitor: %s" % state)
            self._detail(gcmd, "oznlab monitor: v=%.2f mm/s  P=%.0f  P_exp=%.0f  k=%.2f  learned %.0fs  z=%.2f  "
                         "windows hi %d lo %d  clog %d runout %d"
                         % (m['v'], m['p'], m['p_exp'], m['k'], m['t_act'], m['z'], m['n_hi'], m['n_lo'],
                            m['n_clog'], m['n_runout']))
            return
        if self.pa_cal is None:
            gcmd.respond_info("OznLab monitor: not started - it needs OZNLAB_CALIBRATE_PA earlier in the print")
            return
        if self._mon is not None:
            gcmd.respond_info("OznLab monitor: already on"); return
        log = gcmd.get('LOG', None)
        fh = None
        if log:
            try:
                fh = open(self._csv_path(log), 'w')
                fh.write("t,z,v,f,base,p,p_exp,r_raw,k,ratio,active\n")
            except (IOError, OSError) as e:
                raise gcmd.error("oznlab monitor: cannot write %s (%s)" % (log, e))
        self._mon = dict(fh=fh, nlog=0, ok_t=0., warned=False, t_seed=None, t_dev=None,
                         flowing=False, t_stop=None, f_end=[], f_flow=None, t_obs=None, b_obs=None, drift=0.,
                         t_last=None, e_last=None, base=None, v=0., p=0., p_exp=0., ratio=None,
                         t_move=-1e9, win=dict(t0=-1e9, t=0., hi=0., lo=0.), n_hi=0, n_lo=0, fired=None, t=0., k=1., t_act=0., z=0.,
                         t_start=None, n_clog=0, n_runout=0, n_warn=0, seen_print=False)
        self._mon_reload()
        try:
            self._client('clog/runout watch', lambda msg, mine=self._mon: self._mon_cb(msg, mine),
                         lambda: self._mon_stop("internal error"))
        except Exception as e:
            self._mon = None
            if fh is not None: fh.close()
            raise gcmd.error("oznlab monitor: sensor did not start (%s)" % (e,))
        if fh is not None:
            gcmd.respond_info("oznlab monitor: logging every 10th sample to %s" % log)
        m = self._mon
        gcmd.respond_info("OznLab monitor: on - clog and runout watch for this print")
        self._detail(gcmd, "oznlab monitor: ref %.0f Hz @ %.1f mm/s, n=%.2f; clog >%.1fx, runout <%.2fx, "
                     "%d x %.0f s windows must agree, no decisions below z=%.2f"
                     % (m['p_ref'], m['v_ref'], m['n'], self.clog_ratio, self.runout_ratio,
                        self.confirm_windows, self.confirm_time, self.mon_min_z))

    # ================= SLICER TESTS (max flow / retraction / temperature) =================
    # All three extrude in the air: put the nozzle where ooze does no harm before starting.
    # They only measure and report a number - nothing is applied or saved.
    def _extrude_burst(self, v, secs, settle=0.8):
        """extrude v mm/s of filament for secs; returns (baseline, plateau, ripple) in Hz"""
        toolhead = self.printer.lookup_object('toolhead')
        extruder = toolhead.get_extruder()
        accel = getattr(extruder, 'max_e_accel', 1500.) or 1500.
        toolhead.wait_moves(); toolhead.dwell(settle); toolhead.wait_moves()
        self.reactor.pause(self.reactor.monotonic() + 0.3)
        rec = []; self._tap = rec
        self._client('pa', self._pa_client(rec))
        self.reactor.pause(self.reactor.monotonic() + 0.5)          # baseline window
        self.gcode.run_script_from_command("G1 E%.4f F%.0f" % (v * secs, v * 60.))
        t1 = toolhead.get_last_move_time()
        t0 = t1 - (secs + v / accel)
        toolhead.wait_moves()
        self.reactor.pause(self.reactor.monotonic() + 0.35)
        self._release_tap()
        base = [f for t, f in rec if t0 - 0.45 <= t <= t0 - 0.05]
        plat = [f for t, f in rec if t1 - 0.40 <= t <= t1 - 0.02]
        if len(base) < 5 or len(plat) < 5:
            raise self.gcode.error("oznlab: not enough samples (base %d, plateau %d)" % (len(base), len(plat)))
        fb = sum(base) / len(base); pl = sum(plat) / len(plat)
        # ripple = scatter around the local trend. The melt keeps creeping upward during the
        # plateau and that creep grows with flow, so a plain rms would look like rising noise.
        pt = [t for t, f in rec if t1 - 0.40 <= t <= t1 - 0.02]
        mt = sum(pt) / len(pt)
        sxx = sum((x - mt) ** 2 for x in pt)
        b = (sum((x - mt) * (y - pl) for x, y in zip(pt, plat)) / sxx) if sxx > 0. else 0.
        ripple = math.sqrt(sum((y - (pl + b * (x - mt))) ** 2 for x, y in zip(pt, plat)) / len(plat))
        return fb, abs(pl - fb), ripple

    def _lift_clear(self, gcmd, want=50.):
        """Raise the nozzle before extruding in the air. Whether the bed drops or the gantry
        rises is the kinematics' problem - Z always means nozzle-to-bed distance."""
        toolhead = self.printer.lookup_object('toolhead')
        if 'z' not in toolhead.get_status(self.reactor.monotonic())['homed_axes']:
            gcmd.respond_info("oznlab: Z is not homed, not lifting - make sure the nozzle is "
                              "already clear of the bed")
            return
        try:
            z_max = toolhead.get_kinematics().rails[2].get_range()[1]
        except Exception:
            z_max = None
        target = min(want, z_max - 5.) if z_max else want
        z = toolhead.get_position()[2]
        if z >= target - 0.01:
            return
        toolhead.manual_move([None, None, target], 10.)
        toolhead.wait_moves()
        self._sync_gcode_pos()
        self._detail(gcmd, "oznlab: nozzle raised to z=%.0f so the ooze does not reach the bed" % target)

    def _test_prologue(self, gcmd):
        self._end_crash_test("a slicer test")
        self._free(gcmd, "test")
        toolhead = self.printer.lookup_object('toolhead')
        st = toolhead.get_extruder().get_status(self.reactor.monotonic())
        if not st.get('can_extrude', True):
            raise gcmd.error("oznlab: hotend is below min_extrude_temp - heat it up first")
        return toolhead

    def _test_begin(self, gcmd):
        """the state-changing half: call as the FIRST statement inside the try whose finally is
        _test_epilogue, and only after every parameter has been parsed - otherwise a bad
        parameter leaves M83 and an orphaned SAVE_GCODE_STATE behind"""
        self.gcode.run_script_from_command("SAVE_GCODE_STATE NAME=oznlab_test\nM83\nM220 S100\nM221 S100")
        self._lift_clear(gcmd)

    def _test_epilogue(self):
        self._release_tap()
        try:
            self.gcode.run_script_from_command("RESTORE_GCODE_STATE NAME=oznlab_test")
        except Exception:
            logging.exception("oznlab: could not restore the gcode state")

    def _fil_area(self):
        try:
            d = self._cfg_settings('extruder').get('filament_diameter', 1.75)
        except Exception:
            d = 1.75
        return math.pi * d * d / 4.

    cmd_MAX_FLOW_help = ("Find the real volumetric limit by extruding faster and faster in the air: "
                         "OZNLAB_MAX_FLOW [START=1] [STEP=1] [MAX=] [DURATION=1.2] [PRIME=10]")
    def cmd_MAX_FLOW(self, gcmd):
        toolhead = self._test_prologue(gcmd)
        extruder = toolhead.get_extruder()
        v0 = self._gf(gcmd, 'START', 1.0, above=0.2, maxval=40.)
        dv = self._gf(gcmd, 'STEP', 1.0, above=0.1, maxval=10.)
        v_lim = self._gf(gcmd, 'MAX', min(20., getattr(extruder, 'max_e_velocity', 20.)), above=1., maxval=60.)
        secs = self._gf(gcmd, 'DURATION', 1.2, minval=0.6, maxval=4.)
        prime = self._gf(gcmd, 'PRIME', 10.0, minval=0., maxval=50.)
        # Klipper caps extrude-only moves at max_e_velocity (silently) and refuses them above
        # max_extrude_only_distance - either would break the timing or abort the test
        v_lim = min(v_lim, getattr(extruder, 'max_e_velocity', v_lim) or v_lim)
        if v0 > v_lim:
            raise gcmd.error("oznlab: START (%.1f) is above the highest speed (%.1f mm/s)" % (v0, v_lim))
        e_max = getattr(extruder, 'max_e_dist', None)
        if e_max and v_lim * secs > e_max:
            raise gcmd.error("oznlab: %.1f mm/s x %.1f s = %.0f mm is over max_extrude_only_distance "
                             "(%.0f mm) - lower MAX or DURATION" % (v_lim, secs, v_lim * secs, e_max))
        if e_max and prime > e_max:
            prime = e_max
        area = self._fil_area()
        gcmd.respond_info("OznLab Sensor max flow: stepping %.1f -> %.1f mm/s in %.1f mm/s steps "
                          "(about %.0f mm of filament). Nozzle must be in the air."
                          % (v0, v_lim, dv, prime + (v0 + v_lim) / 2. * secs * ((v_lim - v0) / dv + 1)))
        pts = []; limit = None; why = ""; bad = 0
        try:
            self._test_begin(gcmd)
            if prime > 0.:
                self.gcode.run_script_from_command("G1 E%.2f F300" % prime)
                toolhead.wait_moves(); toolhead.dwell(1.0)
            v = v0
            while v <= v_lim + 1e-9:
                fb, P, ripple = self._extrude_burst(v, secs)
                pts.append((v, P, ripple))
                gcmd.respond_info("  %.1f mm/s (%.1f mm3/s): pressure %.0f Hz, ripple %.0f Hz"
                                  % (v, v * area, P, ripple))
                if len(pts) >= 3:
                    # fit log P = log a + n log v on every point EXCEPT the newest one (the
                    # newest is what is being judged; including it made the third point
                    # unfailable and froze the exponent for the rest of the run)
                    good = [(math.log(pv), math.log(pp)) for pv, pp, _ in pts[:-1 - bad] if pv > 0 and pp > 0]
                    n = 0.6; la = math.log(max(pts[0][1], 1.)) - n * math.log(pts[0][0])
                    if len(good) >= 2:
                        mx = sum(x for x, y in good) / len(good); my = sum(y for x, y in good) / len(good)
                        sxx = sum((x - mx) ** 2 for x, y in good)
                        if sxx > 1e-9:
                            n = sum((x - mx) * (y - my) for x, y in good) / sxx
                            n = min(1.5, max(0.2, n)); la = my - n * mx
                    exp_p = math.exp(la + n * math.log(v))
                    # ripple is judged as a fraction of the pressure: absolute ripple grows with
                    # flow even when everything is healthy, the ratio does not
                    r0 = max(pts[0][2] / max(pts[0][1], 1.), 0.004)
                    rr = ripple / max(P, 1.)
                    if P < 0.80 * exp_p:
                        bad += 1
                        why = ("pressure stopped following the flow curve (%.0f Hz measured vs %.0f expected)"
                               % (P, exp_p))
                    elif rr > 4. * r0:
                        bad += 1
                        why = ("pressure got ragged (ripple %.1f%% of the pressure vs %.1f%% at the start) - "
                               "the extruder is slipping" % (100. * rr, 100. * r0))
                    else:
                        bad = 0
                    if bad >= 2:                      # one odd step never ends the test
                        limit = pts[-1 - bad][0] if len(pts) > bad else pts[0][0]
                        break
                v += dv
        finally:
            self._test_epilogue()
        if limit is None:
            limit = pts[-1][0] if pts else 0.
            why = "no limit found up to %.1f mm/s - raise MAX to push further" % v_lim
        gcmd.respond_info("OznLab Sensor max flow: last good %.1f mm/s = %.1f mm3/s (%s)\n"
                          "  Put about %.1f mm3/s in the slicer (10%% margin)."
                          % (limit, limit * area, why, 0.9 * limit * area))

    def _retract_probe(self, toolhead, v, secs, L, rspeed, delay=0.15):
        """Extrude at v mm/s for secs, then immediately retract L mm (queued back to back,
        so no pressure is lost in between). Returns the signed pressure at the end of the
        extrusion and the signed pressure `delay` seconds later, both relative to baseline."""
        extruder = toolhead.get_extruder()
        accel = getattr(extruder, 'max_e_accel', 1500.) or 1500.
        toolhead.wait_moves(); toolhead.dwell(1.0); toolhead.wait_moves()
        self.reactor.pause(self.reactor.monotonic() + 0.3)
        rec = []; self._tap = rec
        self._client('pa', self._pa_client(rec))
        self.reactor.pause(self.reactor.monotonic() + 0.5)              # baseline window
        self.gcode.run_script_from_command("G1 E%.4f F%.0f" % (v * secs, v * 60.))
        t1 = toolhead.get_last_move_time()
        t0 = t1 - (secs + v / accel)
        if L > 0.:
            self.gcode.run_script_from_command("G1 E-%.4f F%.0f" % (L, rspeed * 60.))
        toolhead.wait_moves()
        self.reactor.pause(self.reactor.monotonic() + delay + 0.45)
        self._release_tap()
        base = [f for t, f in rec if t0 - 0.45 <= t <= t0 - 0.05]
        plat = [f for t, f in rec if t1 - 0.30 <= t <= t1 - 0.01]
        aft = [f for t, f in rec if t1 + delay <= t <= t1 + delay + 0.12]
        if len(base) < 5 or len(plat) < 5 or len(aft) < 3:
            raise self.gcode.error("oznlab: not enough samples (base %d, peak %d, after %d)"
                                   % (len(base), len(plat), len(aft)))
        fb = sum(base) / len(base)
        return sum(plat) / len(plat) - fb, sum(aft) / len(aft) - fb

    cmd_RETRACT_TEST_help = ("Find the retraction length that actually drops the melt pressure: "
                             "OZNLAB_RETRACT_TEST [SPEED=5] [MIN=0.2] [MAX=1.4] [STEP=0.2] [RSPEED=35]")
    def cmd_RETRACT_TEST(self, gcmd):
        toolhead = self._test_prologue(gcmd)
        v = self._gf(gcmd, 'SPEED', 5.0, above=0.5, maxval=15.)
        l0 = self._gf(gcmd, 'MIN', 0.2, above=0.05, maxval=3.)
        l1 = self._gf(gcmd, 'MAX', 1.4, above=0.1, maxval=6.)
        dl = self._gf(gcmd, 'STEP', 0.2, above=0.05, maxval=1.)
        rspeed = self._gf(gcmd, 'RSPEED', 35., above=5., maxval=120.)
        secs = 1.2
        gcmd.respond_info("OznLab Sensor retraction test: pressure is built at %.1f mm/s, then %.1f..%.1f mm is "
                          "retracted at %.0f mm/s and what is left is measured.\n"
                          "  Nozzle must be in the air. About %.0f s."
                          % (v, l0, l1, rspeed, ((l1 - l0) / dl + 2) * 4.5))
        rows = []
        try:
            self._test_begin(gcmd)
            self.gcode.run_script_from_command("G1 E8 F300")
            toolhead.wait_moves(); toolhead.dwell(1.0)
            # reference pass without any retraction: how much the pressure falls on its own
            pk0, af0 = self._retract_probe(toolhead, v, secs, 0., rspeed)
            if abs(pk0) < 200.:
                raise gcmd.error("oznlab: no pressure signal (%.0f Hz) - is filament loaded and hot?" % abs(pk0))
            decay0 = af0 / pk0
            if decay0 < 0.05:
                raise gcmd.error("oznlab: the pressure already collapses on its own - lower SPEED or "
                                 "use a stiffer filament for this test")
            L = l0
            while L <= l1 + 1e-9:
                pk, af = self._retract_probe(toolhead, v, secs, L, rspeed)
                pct = 100. * (af / pk) / decay0 if pk else 0.
                rows.append((L, pct))
                gcmd.respond_info(("  %.2f mm -> %.0f%% of the pressure left" % (L, pct)) if pct >= 0. else
                                  ("  %.2f mm -> melt pulled back (%.0f%%)" % (L, pct)))
                self.gcode.run_script_from_command("G1 E%.4f F%.0f" % (L, rspeed * 60.))   # give it back
                toolhead.wait_moves()
                L += dl
        finally:
            self._test_epilogue()
        good = [L for L, pct in rows if abs(pct) <= 10.]
        over = [L for L, pct in rows if pct < -15.]
        msg = "OznLab Sensor retraction test: "
        if good:
            msg += "use about %.2f mm at %.0f mm/s." % (good[0], rspeed)
        else:
            msg += "nothing in the tested range brought the pressure below 10%% - raise MAX."
        if over:
            msg += "\n  %.2f mm and above pull the melt back too far (gaps at the start of a line)." % over[0]
        gcmd.respond_info(msg)

    cmd_TEMP_SCAN_help = ("Pressure vs nozzle temperature at a fixed flow: "
                          "OZNLAB_TEMP_SCAN [MIN=] [MAX=] [STEP=5] [SPEED=3] [SETTLE=20]")
    def cmd_TEMP_SCAN(self, gcmd):
        toolhead = self._test_prologue(gcmd)
        heater = toolhead.get_extruder().get_heater()
        t_now = heater.get_status(self.reactor.monotonic())['target'] or 0.
        t0 = self._gf(gcmd, 'MIN', max(170., t_now - 20.), minval=150., maxval=350.)
        t1 = self._gf(gcmd, 'MAX', t_now + 15., minval=150., maxval=350.)
        dt = self._gf(gcmd, 'STEP', 5., above=1., maxval=20.)
        v = self._gf(gcmd, 'SPEED', 3.0, above=0.5, maxval=15.)
        settle = self._gf(gcmd, 'SETTLE', 20., minval=5., maxval=120.)
        if t1 <= t0: raise gcmd.error("oznlab: MAX must be above MIN")
        gcmd.respond_info("OznLab Sensor temperature scan: %.0f -> %.0f C in %.0f C steps at %.1f mm/s.\n"
                          "  Takes about %.0f minutes, nozzle must be in the air."
                          % (t0, t1, dt, v, ((t1 - t0) / dt + 1) * (settle + 6.) / 60.))
        rows = []
        try:
            self._test_begin(gcmd)
            T = t0
            while T <= t1 + 1e-9:
                self.gcode.run_script_from_command("M109 S%.0f" % T)
                toolhead.dwell(settle); toolhead.wait_moves()
                fb, P, _ = self._extrude_burst(v, 1.2)
                rows.append((T, P))
                gcmd.respond_info("  %.0f C: pressure %.0f Hz" % (T, P))
                T += dt
        finally:
            self._test_epilogue()
            try:   # t_now may be 0 (heater was off but still hot) - then 0 IS the right restore
                self.gcode.run_script_from_command("M104 S%.0f" % t_now)
            except Exception:
                logging.exception("oznlab: could not restore the nozzle temperature")
        if len(rows) < 3:
            gcmd.respond_info("OznLab Sensor temperature scan: not enough points"); return
        # the knee: where the pressure stops dropping much with temperature
        slopes = [((rows[i+1][1] - rows[i][1]) / (rows[i+1][0] - rows[i][0]), rows[i+1][0]) for i in range(len(rows)-1)]
        i_steep = min(range(len(slopes)), key=lambda i: slopes[i][0])
        steep = slopes[i_steep][0]
        # the knee is where the curve flattens AFTER its steepest part; a shallow or noisy first
        # interval must not be mistaken for it
        knee = next((T for sl, T in slopes[i_steep:] if sl > 0.35 * steep), rows[-1][0])
        gcmd.respond_info("OznLab Sensor temperature scan: pressure %.0f Hz at %.0f C -> %.0f Hz at %.0f C.\n"
                          "  Above about %.0f C more heat buys little - %.0f C is a sensible setting.\n"
                          "  (lower = stronger layer bonding is lost, higher = stringing; this only shows the flow side)"
                          % (rows[0][1], rows[0][0], rows[-1][1], rows[-1][0], knee, knee))


    # ================= CRASH DETECTION (EXPERIMENTAL, NOT TESTED ON HARDWARE) =================
    # Melt pressure is a first-order system: it cannot change faster than its own time constant
    # (tau ~ 0.15 s here), so over a 15 ms window it can move at most a few tens of Hz once the
    # extruder speed has settled. A toolhead that hits something deflects the heatsink in one or
    # two samples. That bandwidth gap is the whole discriminator: a large step while the flow is
    # steady is mechanical, never hydraulic.
    #   - armed only while printing, above crash_min_z, and after crash_settle of constant flow
    #     (during accelerations, retractions and the first 0.25 s of a travel the melt transient
    #      is still running, so nothing is judged - same philosophy as the clog monitor)
    #   - two consecutive same-sign steps above the threshold are required; one sample never fires
    #   - threshold = crash_step, raised automatically if the sensor noise is larger than expected
    #   - default action is a console message only; set crash_gcode: PAUSE once you trust it
    def _crash_um(self, hz):
        """Hz step -> um of nozzle push, with the sensitivity of the last tap"""
        sens = self.last_sens or 3.
        return hz / sens

    def _crash_fire(self, step, thr, z):
        c = self._crash
        c['n'] += 1
        self.gcode.respond_info("OznLab: possible CRASH at z=%.1f - toolhead pushed ~%.0f um (limit %.0f um)%s"
                                % (z, self._crash_um(step), self._crash_um(thr),
                                   " -> %s" % c['gcode'] if c['gcode'] else " (experimental, no action set)"))
        logging.info("oznlab crash: %.0f Hz step, limit %.0f Hz, z=%.2f" % (step, thr, z))
        self._job_event("possible crash at z=%.1f (~%.0f um)" % (z, self._crash_um(step)))
        script = c['gcode']
        if not script: return
        def _run(eventtime, script=script):
            try:
                if not self._still_printing(script):
                    logging.info("oznlab: crash action skipped, the print is no longer running"); return
                self.gcode.run_script(script)
            except Exception as e:                 # an exception here would shut klippy down
                logging.exception("oznlab: crash action failed")
                self.gcode.respond_info("OznLab: the crash action '%s' failed (%s)" % (script, e))
        self.reactor.register_callback(_run)

    def _crash_cb(self, msg, mine=None):
        c = self._crash
        if c is None or (mine is not None and c is not mine): return False
        now = self.reactor.monotonic()
        try:
            c['z'] = self.printer.lookup_object('gcode_move').get_status(now)['gcode_position'][2]
        except Exception:
            c['z'] = 0.
        extruder = self.printer.lookup_object('toolhead').get_extruder()
        try:
            state = self.printer.lookup_object('print_stats').get_status(now)['state']
        except Exception:
            state = 'printing'
        dtq = None
        if c['test']:
            # real axis motion only (motion_report keeps the executed moves): a fan command
            # or a dwell advances the print time but moves nothing and must not end the test
            try:
                dtq = self._trapq('toolhead')
            except Exception:
                dtq = None
        for t, f, z in msg.get('data', ()):
            if f <= 0.: continue
            buf = c['buf']; buf.append(f)
            if len(buf) > 2 * c['w']: del buf[0]
            try:
                e = extruder.find_past_position(t)
            except Exception:
                e = None
            if e is not None and c['e_last'] is not None and c['t_last'] is not None:
                dt = t - c['t_last']
                if dt > 0.:
                    v = (e - c['e_last']) / dt
                    v_prev = c['v']
                    c['v'] += (v - c['v']) * min(1., dt / 0.12)
                    if abs(v - v_prev) > max(0.3, 0.25 * abs(c['v'])):
                        c['t_vchg'] = t            # flow is changing: the melt transient is running
            dtn = (t - c['t_last']) if c['t_last'] is not None else 0.01
            if e is not None: c['e_last'] = e
            c['t_last'] = t
            w = c['w']
            if len(buf) < 2 * w: continue
            # step-matched filter: two means of w samples, ~15 ms apart whatever the data rate
            st = (sum(buf[-w:]) - sum(buf[-2 * w:-w])) / float(w)
            if c['um'] and self.last_sens:
                c['step'] = max(c['floor'], c['um'] * self.last_sens)
            thr = max(c['step'], self.crash_sigma * max(c['noise'], 1.))
            # quiet-level tracker, ~2.5 s time constant at any data rate. A bump and its ringing
            # must not raise the threshold: measured by hand-knocking, feeding the tails in
            # drifted the limit from 75 to 140 um within a minute. So nothing is learned during
            # an event (anything over 30% of the limit) and for 0.5 s after it.
            if abs(st) > 0.3 * thr:
                c['hold'] = t + 0.5
            elif t > c.get('hold', 0.):
                c['noise'] += (abs(st) - c['noise']) * min(1., max(dtn, 0.) / 2.5)
            c['thr'] = thr
            if c['test']:
                # the hand test only makes sense with the printer standing still: a G28, a jog
                # or any other move shakes the hotend and would be reported as knocks
                if dtq is not None and t > c['t0']:
                    try:
                        pos, vel = dtq.get_trapq_position(t)
                    except Exception:
                        vel = None
                    if vel is not None and abs(vel) > 0.5:     # mm/s, not float dust
                        self._crash_stop("printer moved", note="stopped because the printer moved")
                        return False
                self._crash_test_step(c, st, thr, w)
                continue
            # self._tap is not None while TAP / CALIBRATE_PA / the slicer tests are running:
            # those deliberately push the nozzle or the melt around, so never judge during them
            # only while actually printing (not paused: brush / filament change macros), and
            # never inside the quiet window a tap / PA burst / test leaves behind
            c['armed'] = (state not in ('paused', 'complete', 'cancelled', 'error') and c['z'] >= self.crash_min_z and t > c['dead']
                          and self._tap is None and t > self._quiet_pt
                          and (t - c['t_vchg']) > self.crash_settle)
            if not c['armed']:
                c['run'] = 0; c['peak'] = 0.; continue
            # The step filter sees a real step at full height only at one position and at
            # (w-1)/w of it on either side, so "twice above thr" would need a 2x step at
            # w=2. Count consecutive same-sign positions above half the threshold and
            # require the peak to clear the full threshold.
            if abs(st) > 0.5 * thr and (c['run'] == 0 or st * c['sign'] > 0.):
                c['run'] += 1; c['sign'] = st; c['peak'] = max(c['peak'], abs(st))
            else:
                c['run'] = 0; c['peak'] = 0.
            if c['run'] >= 2 and c['peak'] > thr:
                c['dead'] = t + 3.0; c['run'] = 0
                self._crash_fire(c['peak'], thr, c['z'])
                c['peak'] = 0.
        if c['test']:
            if now > c['until']:
                self._crash_stop("test finished"); return False
            return True
        if state == 'printing': c['seen_print'] = True
        elif c['seen_print'] and state != 'paused':
            self._crash_stop("print %s" % state); return False
        return True

    def _crash_test_step(self, c, st, thr, w):
        """TEST=1: every knock on the hotend is reported with its strength, and whether the
        print-time rule (two consecutive steps over half the limit, peak over the limit) would
        have fired. Nothing is ever executed."""
        lvl = 0.3 * thr
        if abs(st) > lvl:
            if not c['ev']:
                c.update(ev=True, ev_peak=0., ev_run=0, ev_maxrun=0, ev_sign=st, ev_quiet=0)
            if abs(st) > 0.5 * thr and st * c['ev_sign'] > 0.:
                c['ev_run'] += 1
            else:
                c['ev_run'] = 0
            c['ev_sign'] = st
            c['ev_maxrun'] = max(c['ev_maxrun'], c['ev_run'])
            c['ev_peak'] = max(c['ev_peak'], abs(st)); c['ev_quiet'] = 0
        elif c['ev']:
            c['ev_quiet'] += 1
            if c['ev_quiet'] >= 3 * w:                 # quiet again: the knock is over, report it
                c['ev'] = False; c['n'] += 1
                pk = c['ev_peak']; ratio = pk / thr
                fires = c['ev_maxrun'] >= 2 and pk > thr
                word = ("hard" if ratio >= 1. else "medium" if ratio >= 0.5 else "light")
                if fires:
                    verdict = "WOULD TRIGGER"
                elif ratio >= 1.:
                    # peak over the limit but it lasted a single sample window: a real collision
                    # keeps pushing, a flick or an electrical spike does not - by design
                    verdict = "would not trigger (too short, over in one sample)"
                else:
                    verdict = "would not trigger"
                self.gcode.respond_info("OznLab crash test #%d: %s knock, ~%.0f um push (limit %.0f um) -> %s"
                                        % (c['n'], word, self._crash_um(pk), self._crash_um(thr), verdict))
                logging.info("oznlab crash test: peak %.0f Hz, limit %.0f Hz, run %d"
                             % (pk, thr, c['ev_maxrun']))

    def _queued_end(self):
        """print time at the end of everything queued so far (does not flush anything)"""
        try:
            return float(self.printer.lookup_object('toolhead').get_status(
                self.reactor.monotonic())['print_time'])
        except Exception:
            return 0.

    def _end_crash_test(self, what):
        """a hand-knock test cannot run next to anything that moves the nozzle or the melt:
        it would report the tap / extrusion as knocks. Stop it and say why."""
        c = self._crash
        if c is not None and c['test']:
            self._crash_stop("%s started" % what, note="stopped because %s started" % what)

    def _crash_stop(self, why, note=None):
        c = self._crash; self._crash = None
        if c is None: return
        if c['test']:
            self.gcode.respond_info("OznLab crash test: %s, %d knock(s) seen"
                                    % (note or "finished", c['n']))
        else:
            self._job_note('crash', "%d possible crash(es)" % c['n'] if c['n'] else "no events")
            self.gcode.respond_info("OznLab crash watch: off%s" % (
                " - %d possible crash(es) this print" % c['n'] if c['n'] else ""))
        logging.info("oznlab crash watch: off (%s) - %d event(s)" % (why, c['n']))

    cmd_CRASH_help = ("EXPERIMENTAL toolhead collision watch: OZNLAB_CRASH | OFF=1 | STATUS=1 | "
                      "TEST=1 [DURATION=60] [UM=80] [HZ=] [STEP=] [GCODE=PAUSE]  (limit = UM x last tap sensitivity; HZ= fixes it, STEP= is the Hz floor)")
    def cmd_CRASH(self, gcmd):
        if gcmd.get_int('OFF', 0):
            if self._crash is None: gcmd.respond_info("OznLab crash watch: already off"); return
            self._crash_stop("stopped"); return
        if gcmd.get_int('STATUS', 0):
            c = self._crash
            if c is None: gcmd.respond_info("OznLab crash watch: off"); return
            gcmd.respond_info("OznLab crash watch: on, %s, limit ~%.0f um, %d event(s)"
                              % ("test mode" if c['test'] else "armed" if c['armed'] else "waiting (not printing / "
                                 "flow changing)", self._crash_um(c['thr']), c['n']))
            self._detail(gcmd, "oznlab crash: threshold %.0f Hz (%s), noise %.0f Hz, z=%.2f"
                         % (c['thr'], ("%.0f um at %.1f Hz/um" % (c['um'], self.last_sens))
                            if (c['um'] and self.last_sens) else "fixed", c['noise'], c['z']))
            return
        if self._crash is not None:
            if self._crash['test']:
                if not gcmd.get_int('TEST', 1):         # TEST=0 while a test runs: stop it
                    self._crash_stop("TEST=0", note="stopped"); return
                gcmd.respond_info("OznLab crash test: already running (OZNLAB_CRASH OFF=1 stops it)"); return
            gcmd.respond_info("OznLab crash watch: already on (OFF=1 first)"); return
        um = self._gf(gcmd, 'UM', self.crash_um, above=10., maxval=2000.)
        floor = self._gf(gcmd, 'STEP', self.crash_step, above=30.)
        step_fixed = self._gf(gcmd, 'HZ', None, above=30.)             # HZ= pins the threshold in Hz
        script = gcmd.get('GCODE', self.crash_gcode)
        test = gcmd.get_int('TEST', 0)
        duration = self._gf(gcmd, 'DURATION', 60., minval=5., maxval=600.)
        if test:
            script = ''                                         # a test never runs anything
        if step_fixed is not None:
            step, um = step_fixed, 0.
        elif self.last_sens:
            step = max(floor, um * self.last_sens)
        else:
            step = max(floor, um * 3.)          # no tap yet: assume 3 Hz/um until one runs
        w = max(2, int(round(0.015 * self.sensor.data_rate)))      # half-window ~15 ms
        self._crash = dict(buf=[], w=w, e_last=None, t_last=None, v=0., t_vchg=-1e9, dead=0.,
                           run=0, sign=0., peak=0., noise=0., thr=step, step=step, um=um, floor=floor,
                           armed=False, z=0., n=0, seen_print=False, gcode=script,
                           test=bool(test), until=self.reactor.monotonic() + duration, ev=False,
                           t0=self.printer.lookup_object('toolhead').get_last_move_time())
        if not test:
            # everything PRINT_START queued before this line (prime line, the lift off it, the
            # travel to the print) is not judged, plus 2 s: the nozzle leaving the prime line
            # pulls on the melt and read as a 64 um push on the reference printer
            self._crash['dead'] = self._crash['t0'] + 2.0
        try:
            self._client('crash watch', lambda msg, mine=self._crash: self._crash_cb(msg, mine),
                         lambda: self._crash_stop("internal error", note="stopped after an internal error"))
        except Exception as e:
            self._crash = None
            raise gcmd.error("oznlab crash watch: sensor did not start (%s)" % (e,))
        how = ("%.0f um x %.1f Hz/um from the last tap" % (um, self.last_sens) if (um and self.last_sens)
               else "%.0f um x an assumed 3 Hz/um" % um if um else "fixed HZ=")
        if test:
            gcmd.respond_info("OznLab crash test: %.0f s - knock the hotend sideways, each knock is reported "
                              "with its strength. Limit ~%.0f um%s."
                              % (duration, self._crash_um(step),
                                 "" if self.last_sens else " (no tap yet this session - run OZNLAB_TAP first "
                                 "for a real number)"))
        else:
            gcmd.respond_info("OznLab crash watch: on (experimental) - limit ~%.0f um, %s"
                              % (self._crash_um(step), "action: %s" % script if script else "message only"))
        self._detail(gcmd, "oznlab crash: step > %.0f Hz (%s) in %.0f ms, twice in a row, only above z=%.2f "
                     "and after %.2f s of steady flow; follows every new tap"
                     % (step, how, 2000. * w / self.sensor.data_rate, self.crash_min_z, self.crash_settle))

    # ================= THERMAL CALIBRATION (nozzle drift vs hotend temperature) =================
    # The same tap as OZNLAB_TAP, repeated at several hotend temperatures. The heat block and the
    # heatsink grow as they get hotter, so the nozzle tip sits a few tens of microns lower at 260 C
    # than at 180 C. This measures that slope once; after that a tap taken at one temperature can be
    # corrected for a print running at another.
    cmd_THERMAL_CAL_help = ("Nozzle drift per degree C, by tapping at several temperatures: "
                            "OZNLAB_THERMAL_CAL [MIN=180] [MAX=250] [STEP=20] [SETTLE=90] [SAMPLES=3] [SPEED=] [START=] [TARGET=] [SAVE=1]")
    def cmd_THERMAL_CAL(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        if 'z' not in toolhead.get_status(self.reactor.monotonic())['homed_axes']:
            raise gcmd.error("oznlab thermal: home first (G28)")
        self._free(gcmd, "thermal")
        heater = toolhead.get_extruder().get_heater()
        t_now = heater.get_status(self.reactor.monotonic())['target'] or 0.
        t0 = self._gf(gcmd, 'MIN', 180., minval=60., maxval=350.)
        t1 = self._gf(gcmd, 'MAX', 250., minval=60., maxval=350.)
        dT = self._gf(gcmd, 'STEP', 20., above=5., maxval=60.)
        settle = self._gf(gcmd, 'SETTLE', 90., minval=20., maxval=600.)
        samples = gcmd.get_int('SAMPLES', 3, minval=2, maxval=10)
        speed = self._gf(gcmd, 'SPEED', self.tap_speed, above=0.2, maxval=10.)
        z_start = self._gf(gcmd, 'START', self.tap_start_z, above=0.5, maxval=10.)
        z_target = self._gf(gcmd, 'TARGET', self.tap_target_z, minval=-0.6, maxval=0.0)
        save = gcmd.get_int('SAVE', 1)
        if t1 <= t0: raise gcmd.error("oznlab thermal: MAX must be above MIN")
        try:
            kin = toolhead.get_kinematics()
            accel = min(toolhead.max_accel, getattr(kin, 'max_z_accel', toolhead.max_accel)) or 100.
        except Exception:
            accel = 100.
        n_steps = int((t1 - t0) / dT) + 1
        gcmd.respond_info("OznLab Sensor thermal calibration: %d taps from %.0f to %.0f C, about %.0f minutes.\n"
                          "  UNLOAD THE FILAMENT FIRST - ooze on the bed ruins every tap.\n"
                          "  The nozzle taps at the current XY, so park it over a clean spot."
                          % (n_steps, t0, t1, n_steps * (settle + samples * 6. + 10.) / 60.))
        rows = []
        try:
            T = t0
            while T <= t1 + 1e-9:
                self.gcode.run_script_from_command("M109 S%.0f" % T)
                toolhead.dwell(settle); toolhead.wait_moves()
                zs = []; fs = []
                for i in range(samples + 1):                  # the first tap only primes
                    z_c, hz_um, amp, f_pre = self._tap_once(toolhead, z_start, z_target, speed, accel)
                    if i == 0: continue
                    zs.append(z_c); fs.append(f_pre)
                zs.sort()
                z_med = zs[len(zs) // 2]
                sd = math.sqrt(sum((x - sum(zs) / len(zs)) ** 2 for x in zs) / len(zs))
                rows.append((T, z_med, sum(fs) / len(fs), sd))
                gcmd.respond_info("  %.0f C: contact z=%.4f (stddev %.4f)  baseline %.0f Hz"
                                  % (T, z_med, sd, sum(fs) / len(fs)))
                T += dT
        finally:
            self._release_tap()
            try:
                toolhead.manual_move([None, None, z_start], 10.); toolhead.wait_moves()
            except Exception:
                logging.exception("oznlab thermal: could not lift")
            self._sync_gcode_pos()
            try:
                self.gcode.run_script_from_command("M104 S%.0f" % t_now)
            except Exception:
                logging.exception("oznlab thermal: could not restore the nozzle temperature")
        if len(rows) < 2:
            gcmd.respond_info("oznlab thermal: not enough points"); return
        n = len(rows)
        mt = sum(r[0] for r in rows) / n
        mz = sum(r[1] for r in rows) / n
        mf = sum(r[2] for r in rows) / n
        sxx = sum((r[0] - mt) ** 2 for r in rows)
        if sxx <= 0.:
            gcmd.respond_info("oznlab thermal: temperatures did not vary"); return
        um_c = 1000. * sum((r[0] - mt) * (r[1] - mz) for r in rows) / sxx
        hz_c = sum((r[0] - mt) * (r[2] - mf) for r in rows) / sxx
        way = "down" if um_c > 0 else "up"
        gcmd.respond_info("OznLab Sensor thermal calibration: the nozzle moves %s %.2f um per degree C "
                          "(%.0f um over %.0f..%.0f C).\n"
                          "  Sensor baseline drifts %.1f Hz/C - that part is the coil itself and is "
                          "already removed by the tap.\n"
                          "  Tapping at one temperature and printing at another: add "
                          "(T_print - T_tap) x %.4f mm to the Z offset."
                          % (way, abs(um_c), abs(um_c) * (rows[-1][0] - rows[0][0]),
                             rows[0][0], rows[-1][0], hz_c, um_c / 1000.))
        if save:
            configfile = self.printer.lookup_object('configfile')
            configfile.set(self.cfg_name, 'thermal_um_c', "%.3f" % um_c)
            configfile.set(self.cfg_name, 'thermal_ref_t', "%.0f" % rows[-1][0])
            gcmd.respond_info("The SAVE_CONFIG command will update the printer config file\n"
                              "with the above and restart the printer.")

    # ================= SETUP WIZARD =================
    # OZNLAB_CHECK  - one-shot health report, no motion
    # OZNLAB_SETUP  - guided first-time setup, one step per call (~10 min total)
    def _cfg_settings(self, name):
        """options Klipper has read for a section (defaults included); keys are lower-cased"""
        try:
            return self.printer.lookup_object('configfile').get_status(
                self.reactor.monotonic())['settings'].get(name.lower(), {})
        except Exception:
            return {}

    def _cfg_raw(self, name):
        """options actually written in printer.cfg (autosave block included), no defaults"""
        try:
            return self.printer.lookup_object('configfile').get_status(
                self.reactor.monotonic())['config'].get(name, {})
        except Exception:
            return {}

    def _check(self, gcmd):
        """returns (ok, [lines]) - pure diagnosis, no motion"""
        L = []; ok = True
        # 1 - chip answers
        try:
            mid = self.sensor.read_reg(0x7E); did = self.sensor.read_reg(0x7F)
        except Exception as e:
            return False, ["  [FAIL] sensor does not answer on I2C (%s)" % (e,),
                           "         check 5V/GND, SCL/SDA, that JP1 is soldered, and that it matches "
                           "i2c_address: %d (JP1 2B = 43, 2A = 42)" % self.i2c_addr]
        if (mid, did) != (0x5449, 0x3055):
            ok = False; L.append("  [FAIL] wrong chip id %04x/%04x - wrong address or a different device" % (mid, did))
        else:
            L.append("  [ OK ] LDC1612 answers (id %04x/%04x)" % (mid, did))
        # 2 - a short capture (quiet: the wizard prints its own summary)
        if self._cap is not None:
            return False, L + ["  [WARN] a capture is already running - stop it first (OZNLAB_WATCH OFF=1)"]
        self.last_stats = None
        self._start(1.0, quiet=True)
        self.reactor.pause(self.reactor.monotonic() + 1.7)
        st = self._finish(quiet=True) if self._cap is not None else self.last_stats
        if not st:
            return False, L + ["  [FAIL] no samples arrived - sensor found but not measuring"]
        L.append("  [ OK ] f0 = %.4f MHz, noise %.1f Hz rms, %.0f samples/s" % (st['f0']/1e6, st['noise'], st['rate']))
        if not 1.0e6 < st['f0'] < 6.0e6:
            ok = False; L.append("  [WARN] f0 outside the usual 2-4 MHz - coil cable, C4a value, or no coil connected")
        if st['errors']:
            ok = False
            L.append("  [FAIL] %d conversion errors - run: LDC_CALIBRATE_DRIVE_CURRENT CHIP=%s   then SAVE_CONFIG"
                     % (st['errors'], self.name))
        if st['noise'] > 60.:
            L.append("  [WARN] noise %.0f Hz is high (expect ~10) - check that the coil and its wires cannot move" % st['noise'])
        exp = self.sensor.data_rate
        if st['rate'] < 0.7 * exp:
            L.append("  [WARN] sample rate %.0f/s is below the configured %d - I2C is the bottleneck, try i2c_speed: 400000" % (st['rate'], exp))
        # 3 - config sanity
        if self._cfg_raw(self.cfg_name).get('reg_drive_current') is None:
            L.append("  [WARN] reg_drive_current not set yet - run LDC_CALIBRATE_DRIVE_CURRENT CHIP=%s + SAVE_CONFIG" % self.name)
        zmin = None
        try:
            zmin = self.printer.lookup_object('toolhead').get_kinematics().rails[2].get_range()[0]
        except Exception:
            pass
        if zmin is not None and zmin > self.tap_target_z:
            ok = False
            L.append("  [FAIL] [stepper_z] position_min = %.2f, but the tap needs to reach %.2f - set position_min: -1"
                     % (zmin, self.tap_target_z))
        acts = [g for g in (self.clog_gcode, self.runout_gcode, self.crash_gcode)
                if g and g.strip().upper().startswith('PAUSE')]
        if acts and self.printer.lookup_object('pause_resume', None) is None:
            L.append("  [WARN] clog/runout/crash actions call PAUSE, but printer.cfg has no [pause_resume] - "
                     "add [pause_resume] or the print will not stop")
        if not self._pa_scale_set and not self.pa_scales:
            L.append("  [WARN] pa_scale not tuned yet (default 0.175 from the reference hotend) - "
                     "pressure advance is a guess until step 5")
        if self.pa_scales:
            L.append("  [ OK ] pa_scale per filament: %s (default %.3f)"
                     % (", ".join("%s %.3f" % (k.upper(), v) for k, v in sorted(self.pa_scales.items())),
                        self.pa_scale))
        # 4 - is it wired into PRINT_START?
        ps = (self._cfg_settings('gcode_macro print_start').get('gcode') or '').upper()
        if ps:
            # PRINT_START usually calls the sensor through helper macros (a purge/brush sequence,
            # for example), so look one level down as well before complaining
            try:
                names = [nm.split(None, 1)[-1] for nm, obj
                         in self.printer.lookup_objects('gcode_macro')]
            except Exception:
                names = []
            def body(nm):
                # configfile keeps its settings under the lower-cased section name
                sec = self._cfg_settings('gcode_macro %s' % nm.lower()) or \
                    self._cfg_settings('gcode_macro %s' % nm)
                return (sec.get('gcode') or '').upper()
            seen = set(['PRINT_START'])
            for _ in range(2):                     # two levels deep, over a stable snapshot
                snap = ps; extra = ""
                for nm in names:
                    up = nm.upper()
                    if up in seen or len(up) < 4: continue
                    if re.search(r'(^|[^A-Z0-9_])%s([^A-Z0-9_]|$)' % re.escape(up), snap):
                        seen.add(up); extra += "\n" + body(nm)
                if not extra: break
                ps += extra
            have = set(c for c in ('OZNLAB_CALIBRATE_PA', 'OZNLAB_TAP', 'OZNLAB_MONITOR') if c in ps)
            for line in ps.split('\n'):
                if 'OZNLAB_PRINT_START' in line and not line.strip().startswith('#'):
                    if 'PA=0' not in line: have.add('OZNLAB_CALIBRATE_PA')
                    if 'TAP=0' not in line: have.add('OZNLAB_TAP')
                    if 'MONITOR=1' in line: have.add('OZNLAB_MONITOR')
            miss = [c for c in ('OZNLAB_CALIBRATE_PA', 'OZNLAB_TAP', 'OZNLAB_MONITOR') if c not in have]
            if miss: L.append("  [WARN] PRINT_START does not call: %s" % ", ".join(miss))
            else: L.append("  [ OK ] PRINT_START calls CALIBRATE_PA, TAP and MONITOR")
        return ok, L

    cmd_CHECK_help = "OznLab Sensor health report (no motion): chip, frequency, noise, errors, config sanity"
    def cmd_CHECK(self, gcmd):
        ok, lines = self._check(gcmd)
        gcmd.respond_info("OznLab Sensor v%s check [%s]\n%s" % (VERSION, "PASS" if ok else "PROBLEM", "\n".join(lines)))

    cmd_SETUP_help = "Guided first-time setup, one step per call: OZNLAB_SETUP [STEP=1..8] [RESET=1]"
    def cmd_SETUP(self, gcmd):
        R = gcmd.respond_info
        if gcmd.get_int('RESET', 0): self._setup_step = 0
        resume = (self._setup_resume and gcmd.get('STEP', None) is None
                  and not gcmd.get_int('RESET', 0))
        self._setup_resume = False
        step = gcmd.get_int('STEP', self._setup_step % 8 + 1, minval=1, maxval=8)
        self._setup_step = step
        self._setup_keep(step)
        if resume:
            R("Continuing the setup at step %d (OZNLAB_SETUP RESET=1 starts over, STEP=n jumps)" % step)
        th = self.printer.lookup_object('toolhead')
        ext = self.printer.lookup_object('toolhead').get_extruder()
        hot = ext.get_status(self.reactor.monotonic()).get('can_extrude', False)
        try: tmin = float(ext.get_heater().min_extrude_temp)
        except Exception: tmin = 170.
        nxt = "\n  -> when done, run OZNLAB_SETUP for the next step"
        if step == 1:
            ok, lines = self._check(gcmd)
            if not ok: self._setup_keep(0)
            R("STEP 1/8  WIRING AND SENSOR\n%s\n%s" % ("\n".join(lines),
              ("  Everything answers." + nxt) if ok else
              "  Fix the [FAIL] lines above, then run OZNLAB_SETUP STEP=1 again."))
        elif step == 2:
            if not self.last_stats:            # after the restart SAVE_CONFIG did: measure now
                self._check(gcmd)
            if not self.last_stats:
                self._setup_keep(0)
                R("STEP 2/8  DRIVE CURRENT\n  No data from the sensor - run OZNLAB_SETUP STEP=1 first."); return
            st = self.last_stats or {}
            if st.get('errors'):
                self._setup_keep(1)
                R("STEP 2/8  DRIVE CURRENT\n  The sensor reported errors. Run:\n"
                  "    LDC_CALIBRATE_DRIVE_CURRENT CHIP=%s\n    SAVE_CONFIG\n"
                  "  (the printer restarts) then run OZNLAB_SETUP STEP=2" % self.name)
            else:
                R("STEP 2/8  DRIVE CURRENT\n  [ OK ] no conversion errors, drive current is fine.%s" % nxt)
        elif step == 3:
            secs = 25.
            R("STEP 3/8  DOES THE COIL FEEL THE HOTEND?\n"
              "  Watching for %.0f s. Push the nozzle UP with a finger (or press it on the bed) 3 times.\n"
              "  Each push should print a TAP line below. No lines = the coil is too far from the\n"
              "  heatsink, or it is looking at plastic instead of aluminium.%s" % (secs, nxt))
            self.cmd_WATCH(self.gcode.create_gcode_command(
                "OZNLAB_WATCH", "OZNLAB_WATCH", {'DURATION': secs, 'SENSOR': self.name}))
        elif step == 4:
            if 'z' not in th.get_status(self.reactor.monotonic())['homed_axes']:
                self._setup_keep(3)
                R("STEP 4/8  TAP TEST\n  Home first (G28), move over the middle of the bed, then run OZNLAB_SETUP STEP=4"); return
            if not hot:
                self._setup_keep(3)
                R("STEP 4/8  TAP TEST\n  Heat the nozzle first: at least %.0f C, your printing temperature is best\n"
                  "  (the hotend grows ~60 um from cold to hot, so tap at the temperature you print at),\n"
                  "  then run OZNLAB_SETUP STEP=4" % tmin); return
            R("STEP 4/8  TAP TEST AND Z OFFSET")
            self.cmd_TAP(self.gcode.create_gcode_command(
                "OZNLAB_TAP", "OZNLAB_TAP", {'SENSOR': self.name}))
            R("  If the z offset was set, run SAVE_CONFIG to keep it.\n"
              "  If the taps disagreed, clean the nozzle and run OZNLAB_SETUP STEP=4 again.\n"
              "  First layer too squished later? raise tap_adjust_z.%s" % nxt)
        elif step == 5:
            if not hot:
                self._setup_keep(4)
                R("STEP 5/8  PRESSURE ADVANCE\n  Load filament and heat the nozzle to its printing temperature\n"
                  "  (at least %.0f C, e.g. PLA 210 C, PETG 240 C, ASA 250 C),\n"
                  "  move the nozzle over the purge bucket or a waste area (the Z lift is automatic),\n"
                  "  then run OZNLAB_SETUP STEP=5" % tmin); return
            R("STEP 5/8  PRESSURE ADVANCE (measures the melt pressure rise, applies nothing)")
            self._lift_clear(gcmd)
            self.cmd_CALIBRATE_PA(self.gcode.create_gcode_command(
                "OZNLAB_CALIBRATE_PA", "OZNLAB_CALIBRATE_PA", {'APPLY': 0, 'SENSOR': self.name}))
            tau = (self.pa_cal or {}).get('tau')
            R("  Now print your slicer's PA pattern test (same filament and temperature),\n"
              "  read the PA of the cleanest line, and run:\n"
              "    OZNLAB_PA_SCALE PATTERN_PA=<that value> TYPE=<filament, e.g. PLA>\n    SAVE_CONFIG\n"
              "  (one scale per filament type; repeat for each filament you print)\n"
              "  %s%s" % (("measured tau = %.3f s, so pa_scale = PATTERN_PA / %.3f" % (tau, tau)) if tau else
                          "no reliable tau yet - check the message above", nxt))
        elif step == 6:
            self._setup_homing(gcmd, hot, nxt)
        elif step == 7:
            has_probe = self._other_probe()
            if has_probe:
                R("STEP 7/8  BED MESH\n"
                  "  This printer already has a probe, keep using it for the mesh (it is faster).\n"
                  "  The nozzle-tap mesh is still there for a check: OZNLAB_MESH_SETUP, then\n"
                  "  OZNLAB_MESH and OZNLAB_MESH_COMPARE show where the probe and the nozzle disagree.%s" % nxt)
            else:
                R("STEP 7/8  BED MESH (no probe on this printer - the nozzle is the probe)\n"
                  "  1. OZNLAB_MESH_SETUP   - a popup walks the nozzle to the four corners of the\n"
                  "     usable bed, then SAVE_CONFIG (adds [bed_mesh] if you have none)\n"
                  "  2. Nozzle at printing temperature and brushed, bed at printing temperature:\n"
                  "     OZNLAB_MESH          - 5x5 takes about 3 min, then SAVE_CONFIG\n"
                  "  3. In PRINT_START, before OZNLAB_TAP:  BED_MESH_PROFILE LOAD=default\n"
                  "     (Klipper does not load a profile by itself), or OZNLAB_MESH ADAPTIVE=1 for a\n"
                  "     fresh mesh under every print.\n"
                  "  (Z homing with the nozzle is step 6: OZNLAB_SETUP STEP=6)%s" % nxt)
        else:
            R("STEP 8/8  WIRE IT INTO PRINT_START\n"
              "  In PRINT_START, after the nozzle is at printing temperature:\n"
              "    OZNLAB_PRINT_START FILAMENT=\"{params.FILAMENT|default('')}\" PA_X=<purge x> PA_Y=<purge y>\n"
              "    ... prime line ...\n"
              "    OZNLAB_MONITOR             ; last line of PRINT_START\n"
              "  (OZNLAB_PRINT_START = FILAMENT, PA over the purge area, 15 s settle, tap over the bed centre)\n"
              "  In PRINT_END and CANCEL_PRINT:\n"
              "    OZNLAB_PRINT_END\n"
              "  Done. OZNLAB_CHECK re-runs the health report any time.")

    def _setup_keep(self, step):
        # the last step done; kept by the next SAVE_CONFIG, so the restart it does resumes here
        self._setup_step = step
        if step != self._setup_saved:
            self.printer.lookup_object('configfile').set(self.cfg_name, 'setup_step', str(step))
            self._setup_saved = step

    def _setup_homing(self, gcmd, hot, nxt):
        """SETUP step 6, optional: home Z with the nozzle.
        a) z_homing off              -> the one line to add
        b) z_homing on, other homing -> dry run; if good, the exact lines that switch Z homing over
        c) the nozzle homes Z        -> measure the contact after homing and store the Z offset"""
        R = gcmd.respond_info
        head = "STEP 6/8  Z HOMING WITH THE NOZZLE (optional)"
        th = self.printer.lookup_object('toolhead')
        if self.homing is None:
            R("%s\n"
              "  Skip this step if you are happy with your Z endstop or probe.\n"
              "  To try it, add this to [%s], restart Klipper, then run OZNLAB_SETUP STEP=6 again:\n"
              "    z_homing: 1\n"
              "  (needs trigger_analog in the toolhead board's Klipper firmware; if Klipper then\n"
              "  refuses to start, remove the line again)%s" % (head, self.cfg_name, nxt)); return
        if not self._homed():
            self._setup_keep(5)
            R("%s\n  Home first (G28), move the nozzle over the middle of the bed, then run "
              "OZNLAB_SETUP STEP=6" % head); return
        if (self._noz_temp() or 0.) < 140.:      # the tap needs soft plastic and a settled hotend
            self._setup_keep(5)
            R("%s\n  Heat the nozzle first (at least 140 C, 150 C is fine, tip clean), then run "
              "OZNLAB_SETUP STEP=6" % head); return
        ep = (self._cfg_settings('stepper_z').get('endstop_pin') or '')
        nozzle_homes = (self.z_homing_probe and self.printer.lookup_object('probe', None) is self.homing
                        and 'z_virtual_endstop' in str(ep))
        if not nozzle_homes:
            # b) dry run against the current Z homing
            R("%s\n  Test run: the nozzle comes down on the trigger, then fine taps. Nothing is changed." % head)
            self.homing.dry_run(gcmd)
            l = self.homing.last or {}
            over = abs(l.get('trigger', 0.) - l.get('contact', 0.))
            if over >= 0.3:
                R("  The trigger stopped %.2f mm past the bed - too late to rely on. Check that the\n"
                  "  coil is fixed, heat the nozzle to printing temperature and run STEP=6 again." % over); return
            pos = th.get_position()
            other = self._other_probe()
            lines = ["  The trigger works (%.2f mm past the bed). To home Z with the nozzle:" % over,
                     "  1. In [%s] add:" % self.cfg_name,
                     "       z_homing_probe: 1",
                     "  2. In [stepper_z] set:",
                     "       endstop_pin: probe:z_virtual_endstop",
                     "       homing_speed: 3",
                     "       homing_retract_dist: 0",
                     "       position_min: -1"]
            zs = self._cfg_raw('stepper_z')
            drop = [o for o in ('position_endstop', 'homing_positive_dir') if o in zs]
            if drop:
                lines += ["     and delete these lines from [stepper_z] (Klipper refuses to start with them):"]
                lines += ["       %s: %s" % (o, zs[o]) for o in drop]
            if self.printer.lookup_object('homing_override', None) is not None:
                lines += ["  3. Your [homing_override] must home Z with the nozzle over the bed",
                          "     (for example at X%.0f Y%.0f, where you are now)." % (pos[0], pos[1])]
            else:
                lines += ["  3. If you have no [safe_z_home], add one so Z homes over the bed:",
                          "       [safe_z_home]",
                          "       home_xy_position: %.0f, %.0f" % (pos[0], pos[1]),
                          "       z_hop: 5"]
            if other:
                lines += ["  4. Klipper allows one probe: disable your current probe's section, and delete its",
                          "     #*# lines at the bottom of printer.cfg too (keep a backup of the file).",
                          "     Your mesh and z_tilt then use the nozzle (OZNLAB_MESH)."]
            lines += ["  Restart Klipper, G28, heat the nozzle and run OZNLAB_SETUP STEP=6 again:",
                      "  it then measures and stores the Z offset."]
            R("\n".join(lines)); return
        # c) the nozzle is the Z endstop: homing already put Z 0 on the contact. Measure the
        # contact here and store the offset (contact + tap_adjust_z) for prints without a tap.
        R("%s\n  The nozzle homes Z. Measuring the contact after homing and storing the Z offset." % head)
        self.cmd_TAP(self.gcode.create_gcode_command(
            "OZNLAB_TAP", "OZNLAB_TAP", {'SENSOR': self.name}))
        R("  If the z offset was set: SAVE_CONFIG to keep it. It is applied at every start, so a\n"
          "  print is right even without OZNLAB_TAP in PRINT_START (keeping it there is still best).%s" % nxt)

    # ================= PRINT REPORT =================
    # One summary per print: what the sensor measured and saw. Starts at OZNLAB_FILAMENT (first line
    # of PRINT_START), ends when print_stats leaves printing / paused, or at OZNLAB_REPORT.
    def _job_start(self):
        if self._job is not None:
            self._job_finish(quiet=True)
        self._job = dict(t0=self.reactor.monotonic(), filament=self._fil_disp(), notes={}, events=[],
                         peaks={}, seen_print=False, done=False)
        if self._job_timer is None:
            self._job_timer = self.reactor.register_timer(self._job_tick, self.reactor.NOW)
        else:
            self.reactor.update_timer(self._job_timer, self.reactor.NOW)

    def _job_auto(self):
        # PRINT_START without OZNLAB_FILAMENT: the first OznLab step of a running print opens the report
        if self._job is None:
            try:
                state = self.printer.lookup_object('print_stats').get_status(
                    self.reactor.monotonic())['state']
            except Exception:
                state = None
            if state in ('printing', 'paused'):
                self._job_start()
                self._job['auto'] = True
        return self._job

    def _job_note(self, key, text):
        if self._job_auto() is not None:
            self._job['notes'][key] = text

    def _job_event(self, text):
        if self._job_auto() is not None and len(self._job['events']) < 50:
            mins = (self.reactor.monotonic() - self._job['t0']) / 60.
            self._job['events'].append("%.0f min: %s" % (mins, text))

    def _report_objects(self):
        if self.report_sensors:
            names = self.report_sensors
        else:
            names = [n for n, o in self.printer.lookup_objects()
                     if n.startswith('temperature_sensor ') or n.startswith('heater_generic ')]
        out = []
        for n in names:
            o = self.printer.lookup_object(n, None)
            if o is None and ' ' not in n:
                o = (self.printer.lookup_object('temperature_sensor ' + n, None)
                     or self.printer.lookup_object('heater_generic ' + n, None))
            if o is not None and hasattr(o, 'get_status'):
                out.append((n.split(' ', 1)[-1], o))
        return out

    def _job_tick(self, eventtime):
        try:
            return self._job_tick_inner(eventtime)
        except Exception:                          # a timer exception would shut Klipper down
            logging.exception("oznlab report: tick failed")
            self._job = None
            return self.reactor.NEVER

    def _job_tick_inner(self, eventtime):
        j = self._job
        if j is None:
            return self.reactor.NEVER
        try:
            for label, o in self._report_objects():
                t = o.get_status(eventtime).get('temperature')
                if t is not None and t > j['peaks'].get(label, -1e9):
                    j['peaks'][label] = t
        except Exception:
            logging.exception("oznlab report: could not read a temperature")
        try:
            state = self.printer.lookup_object('print_stats').get_status(eventtime)['state']
        except Exception:
            state = None
        m = self._mon
        if m is not None and state == 'printing':
            # a cable or I2C problem stops the samples without any error: say the watch is blind
            rx = m.setdefault('rx', eventtime)
            if eventtime - rx > 10. and not m.get('blind'):
                m['blind'] = True
                self.gcode.respond_info("OznLab: no data from the sensor for %.0f s - the clog/runout "
                                        "watch cannot see anything. Check the sensor wiring." % (eventtime - rx))
                self._job_event("sensor silent, clog/runout watch blind")
        if state in ('printing', 'paused'):
            j['seen_print'] = True
        elif j['seen_print'] or eventtime - j['t0'] > 24 * 3600.:
            j['end_state'] = state
            self._job_finish()
            return self.reactor.NEVER
        return eventtime + 5.

    def _job_finish(self, quiet=False):
        j = self._job
        if j is None:
            return
        self._job = None
        j['t1'] = self.reactor.monotonic()
        # watches still running (they stop on the same state change, maybe a moment later)
        m = self._mon
        if m is not None and 'monitor' not in j['notes']:
            ev = m['n_clog'] + m['n_runout']
            j['notes']['monitor'] = "%d clog, %d runout" % (m['n_clog'], m['n_runout']) if ev else "no events"
        c = self._crash
        if c is not None and not c['test'] and 'crash' not in j['notes']:
            j['notes']['crash'] = "%d possible crash(es)" % c['n'] if c['n'] else "no events"
        self._last_job = j
        if not quiet:
            self.gcode.respond_info(self._report_text(j))

    def _report_text(self, j):
        mins = ((j.get('t1') or self.reactor.monotonic()) - j['t0']) / 60.
        head = "OznLab print report - %.0f min%s%s" % (
            mins, (", %s" % j['filament'].upper()) if j.get('filament') else "",
            (" (%s)" % j['end_state']) if j.get('end_state') and j['end_state'] != 'complete' else "")
        n = j['notes']
        rows = [("Z offset", n.get('tap', "not measured")),
                ("PA", n.get('pa', "not measured")),
                ("Clog/runout", n.get('monitor', "watch not running")),
                ("Crash watch", n.get('crash', "not running"))]
        lines = [head] + ["  %-12s %s" % r for r in rows]
        if j['peaks']:
            lines.append("  %-12s %s" % ("Peak temps", ", ".join(
                "%s %.0f C" % (k, v) for k, v in sorted(j['peaks'].items(), key=lambda kv: -kv[1]))))
        if j['events']:
            lines.append("  Events:")
            lines += ["    " + e for e in j['events']]
        return "\n".join(lines)

    cmd_REPORT_help = "Summary of the current or last print: OZNLAB_REPORT"
    def cmd_REPORT(self, gcmd):
        if self._job is not None:
            # PRINT_END calls this for printers that stream G-code (print_stats stays standby there)
            try:
                state = self.printer.lookup_object('print_stats').get_status(self.reactor.monotonic())['state']
            except Exception:
                state = None
            if state in ('printing', 'paused'):
                gcmd.respond_info(self._report_text(self._job) + "\n  (print still running)")
                return
            self._job_finish()
            return
        if self._last_job is None:
            gcmd.respond_info("OznLab: no print recorded yet since the last restart")
            return
        gcmd.respond_info(self._report_text(self._last_job))

    # ================= MENU (Mainsail / Fluidd popup) =================
    MENU = (
        # key, button label, command, color, needs
        ('check', "Health check", "OZNLAB_CHECK", 'primary', None),
        ('push', "Push test (25 s)", "OZNLAB_WATCH DURATION=25", 'secondary', None),
        ('setup', "Guided setup", "OZNLAB_SETUP", 'secondary', None),
        ('tap', "Tap: Z offset", "OZNLAB_TAP SAVE=0", 'primary', 'homed'),
        ('pa', "Measure PA", "OZNLAB_CALIBRATE_PA", 'primary', 'hot'),
        ('crashtest', "Crash test (60 s)", "OZNLAB_CRASH TEST=1", 'secondary', None),
        ('maxflow', "Max flow", "OZNLAB_MAX_FLOW", 'info', 'hot'),
        ('retract', "Retraction", "OZNLAB_RETRACT_TEST", 'info', 'hot'),
        ('temp', "Temperature", "OZNLAB_TEMP_SCAN", 'info', 'hot'),
        ('meshsetup', "Mesh area", "OZNLAB_MESH_SETUP", 'secondary', None),
        ('mesh', "Nozzle mesh", "OZNLAB_MESH", 'secondary', 'homed'),
        ('hometest', "Home test", "OZNLAB_HOME_TEST", 'secondary', 'homing'),
        ('report', "Last print", "OZNLAB_REPORT", 'secondary', None),
        ('help', "All commands", "OZNLAB_HELP", 'secondary', None),
    )
    # two levels: the start page shows the groups, each group page its tools
    MENU_PAGES = (
        # key, button label, color, rows of MENU keys, note on the page
        ('setup', "Setup and health", 'primary', (('check', 'push', 'setup'),), None),
        ('zpa', "Z offset and PA", 'primary', (('tap', 'pa'), ('crashtest',)),
         "Tap needs a homed printer; PA needs a hot nozzle over the purge area."),
        ('tests', "Filament tests", 'info', (('maxflow', 'retract', 'temp'),),
         "These extrude in the air: park over the purge area first."),
        ('mesh', "Bed mesh and homing", 'secondary', (('meshsetup', 'mesh'), ('hometest',)), None),
    )

    cmd_MENU_help = "Popup with the OznLab Sensor tools (Mainsail / Fluidd): OZNLAB_MENU [PAGE=] [CLOSE=1]"
    def cmd_MENU(self, gcmd):
        c = "OZNLAB_MENU"
        items = dict((k, (label, cmd, color, need)) for k, label, cmd, color, need in self.MENU)
        pages = dict((k, (label, color, rows, note)) for k, label, color, rows, note in self.MENU_PAGES)
        if gcmd.get_int('CLOSE', 0):
            self._prompt_close(); return
        run = gcmd.get('RUN', '').strip().lower()
        if run:
            if run not in items:
                raise gcmd.error("oznlab menu: unknown item %s" % run)
            # close first: the command may open its own popup (mesh setup) or run for minutes
            self._prompt_close()
            self.gcode.run_script_from_command(items[run][1])
            return
        page = gcmd.get('PAGE', '').strip().lower()
        if page and page not in pages:
            raise gcmd.error("oznlab menu: unknown page %s" % page)
        scale, src, known = self._pa_scale_for()
        texts = ["OznLab Sensor v%s" % VERSION,
                 "Filament: %s, pa_scale %.3f%s" % (self._fil_disp() if self.filament else "unknown",
                                                     scale, "" if known else " (default)"),
                 "Last tap: %s   Last PA: %s" % ("%.3f mm" % self.last_tap_z if self.last_tap_z is not None else "-",
                                                "%.4f" % self.last_pa if self.last_pa is not None else "-")]
        close = ("Close", "%s CLOSE=1" % c, 'secondary')
        if not page:
            rows = [[(label, "%s PAGE=%s" % (c, k.upper()), color)]
                    for k, label, color, r, note in self.MENU_PAGES]
            rows.append([(items['report'][0], "%s RUN=REPORT" % c, 'secondary'),
                         (items['help'][0], "%s RUN=HELP" % c, 'secondary')])
            self._prompt("OznLab Sensor", texts, rows, [close])
            return
        label, color, prow, note = pages[page]
        rows = []
        for row in prow:
            btns = []
            for k in row:
                blabel, cmd, bcolor, need = items[k]
                if need == 'homing' and self.homing is None:
                    continue
                btns.append((blabel, "%s RUN=%s" % (c, k.upper()), bcolor))
            if btns:
                rows.append(btns)
        if note:
            texts.append(note)
        self._prompt("OznLab Sensor: %s" % label, texts, rows,
                     [("Back", c, 'secondary'), close])

    cmd_PRINT_START_help = ("Everything OznLab needs at print start, in one line: OZNLAB_PRINT_START "
                            "[FILAMENT=] [PA_X= PA_Y=] [TAP_X= TAP_Y=] [SETTLE=15] [PA=1] [TAP=1] [MONITOR=0] [CRASH=0]")
    def cmd_PRINT_START(self, gcmd):
        """FILAMENT, pressure advance over the purge area, settle, tap over the bed. The clog watch
        is started here only with MONITOR=1: it normally goes after the prime line."""
        run = self.gcode.run_script_from_command
        def sub(name, fn, params):
            fn(self.gcode.create_gcode_command(name, name, params))
        if gcmd.get('FILAMENT', None) is not None:
            sub('OZNLAB_FILAMENT', self.cmd_FILAMENT, {'TYPE': gcmd.get('FILAMENT')})
        if not self._homed():
            raise gcmd.error("oznlab print start: home first (G28)")
        do_pa = gcmd.get_int('PA', 1); do_tap = gcmd.get_int('TAP', 1)
        settle = self._gf(gcmd, 'SETTLE', 15., minval=0., maxval=120.)
        th = self.printer.lookup_object('toolhead')
        gm = self.printer.lookup_object('gcode_move')
        was_abs = gm.get_status(self.reactor.monotonic()).get('absolute_coordinates', True)
        try:
            kin = th.get_kinematics()
            (x0, x1), (y0, y1), (z0, z1) = [kin.rails[i].get_range() for i in range(3)]
        except Exception:
            x0 = y0 = 0.; x1 = y1 = 200.; z1 = 200.
        run("G90")
        if do_pa:
            lift = min(20., z1 - 5.)
            if th.get_position()[2] < lift:
                run("G1 Z%.1f F600" % lift)
            px = self._gf(gcmd, 'PA_X', None); py = self._gf(gcmd, 'PA_Y', None)
            if px is not None or py is not None:
                run("G1 %s%s F9000" % ("X%.1f " % px if px is not None else "",
                                        "Y%.1f" % py if py is not None else ""))
            sub('OZNLAB_CALIBRATE_PA', self.cmd_CALIBRATE_PA, {})
            run("SAVE_GCODE_STATE NAME=oznlab_ps\nM83\nG1 E-4 F1800\nRESTORE_GCODE_STATE NAME=oznlab_ps")
            if settle > 0.:
                run("G4 P%.0f" % (settle * 1000.))   # let the hotend finish expanding before the tap
        if do_tap:
            tx = self._gf(gcmd, 'TAP_X', (x0 + x1) / 2.); ty = self._gf(gcmd, 'TAP_Y', (y0 + y1) / 2.)
            run("G1 Z5 F600")
            run("G1 X%.1f Y%.1f F6000" % (tx, ty))
            sub('OZNLAB_TAP', self.cmd_TAP, {'SAVE': '0'})
        if gcmd.get_int('MONITOR', 0):
            sub('OZNLAB_MONITOR', self.cmd_MONITOR, {})
        if gcmd.get_int('CRASH', 0):
            sub('OZNLAB_CRASH', self.cmd_CRASH, {})
        if not was_abs:
            run("G91")
        if not gcmd.get_int('MONITOR', 0) and not self._ps_hint:
            self._ps_hint = True                   # once per restart, not on every print
            gcmd.respond_info("OznLab print start done. Put OZNLAB_MONITOR after your prime line "
                              "(or add MONITOR=1 here).")

    cmd_PRINT_END_help = "Stops the clog / runout and crash watch (PRINT_END and CANCEL_PRINT): OZNLAB_PRINT_END"
    def cmd_PRINT_END(self, gcmd):
        if self._mon is not None:
            self._mon_stop("print end")
        if self._crash is not None:
            self._crash_stop("print end")

    TESTS = {'flow': 'MAX_FLOW', 'retract': 'RETRACT_TEST', 'temp': 'TEMP_SCAN'}
    cmd_TEST_help = ("Filament tests in the air, one entry point: OZNLAB_TEST TYPE=flow|retract|temp "
                     "[the test's own parameters]")
    def cmd_TEST(self, gcmd):
        kind = gcmd.get('TYPE', '').strip().lower()
        if kind not in self.TESTS:
            raise gcmd.error("oznlab test: TYPE must be one of flow, retract, temp")
        name = self.TESTS[kind]
        params = dict((k, v) for k, v in gcmd.get_command_parameters().items() if k.upper() != 'TYPE')
        fn = getattr(self, 'cmd_' + name)
        fn(self.gcode.create_gcode_command('OZNLAB_' + name, 'OZNLAB_' + name, params))

    cmd_HOME_TEST_help = ("Tap homing dry run: descend on the MCU trigger, then the fine tap; reports "
                          "trigger z vs contact z. Needs z_homing: 1 and a homed Z. OZNLAB_HOME_TEST [SPEED=3]")
    def cmd_HOME_TEST(self, gcmd):
        if self.homing is None:
            raise gcmd.error("oznlab: set z_homing: 1 in [%s] (and update the toolhead firmware) first"
                             % self.cfg_name)
        if not self._homed():
            raise gcmd.error("oznlab home test: home first (G28) - the test compares against the "
                             "current Z, it does not home")
        speed = self._gf(gcmd, 'SPEED', None, above=0.5, maxval=25.)
        self.homing.dry_run(gcmd, speed)

    # ================= HELP =================
    HELP_GROUPS = (
        ("Setup and health", ('OZNLAB_MENU', 'OZNLAB_SETUP', 'OZNLAB_CHECK', 'OZNLAB_STATUS', 'OZNLAB_REPORT', 'OZNLAB_HELP')),
        ("Every print (PRINT_START / PRINT_END)", ('OZNLAB_PRINT_START', 'OZNLAB_PRINT_END', 'OZNLAB_FILAMENT')),
        ("Z: tap and bed mesh", ('OZNLAB_TAP', 'OZNLAB_MESH_SETUP', 'OZNLAB_MESH', 'OZNLAB_MESH_COMPARE',
                                 'OZNLAB_HOME_TEST', 'OZNLAB_THERMAL_CAL')),
        ("Extrusion", ('OZNLAB_CALIBRATE_PA', 'OZNLAB_PA_SCALE', 'OZNLAB_TEST', 'OZNLAB_MAX_FLOW',
                       'OZNLAB_RETRACT_TEST', 'OZNLAB_TEMP_SCAN')),
        ("During the print", ('OZNLAB_MONITOR', 'OZNLAB_CRASH')),
        ("Debug", ('OZNLAB_WATCH', 'OZNLAB_STREAM')),
    )
    cmd_HELP_help = "List every OznLab Sensor command with its usage"
    def cmd_HELP(self, gcmd):
        out = ["OznLab Sensor v%s commands" % VERSION]
        listed = set()
        for title, cmds in self.HELP_GROUPS:
            have = [c for c in cmds if c in self._help]
            if not have: continue
            out.append("")
            out.append("== %s ==" % title)
            for c in have:
                out.append("%s\n    %s" % (c, self._help[c])); listed.add(c)
        rest = [c for c in sorted(self._help) if c not in listed]
        if rest:
            out.append(""); out.append("== Other ==")
            for c in rest:
                out.append("%s\n    %s" % (c, self._help[c]))
        gcmd.respond_info("\n".join(out))

    # ================= BED MESH (nozzle tap) =================
    # The nozzle itself is the probe, so the mesh has no XY offset and needs no [probe].
    # Klipper's own bed_mesh still applies it (interpolation, fade, profiles); we only measure.
    def _prompt(self, title, texts, rows, footer):
        """Mainsail / Fluidd macro prompt. rows: list of button rows, each [(label, gcode, color)]"""
        R = self.gcode.respond_raw
        R("// action:prompt_begin %s" % title)
        for t in texts:
            R("// action:prompt_text %s" % t)
        for row in rows:
            if len(row) > 1: R("// action:prompt_button_group_start")
            for label, cmd, color in row:
                R("// action:prompt_button %s|%s|%s" % (label, cmd, color))
            if len(row) > 1: R("// action:prompt_button_group_end")
        for label, cmd, color in footer:
            R("// action:prompt_footer_button %s|%s|%s" % (label, cmd, color))
        R("// action:prompt_show")

    def _prompt_close(self):
        self.gcode.respond_raw("// action:prompt_end")

    def _xy_limits(self):
        st = self.printer.lookup_object('toolhead').get_status(self.reactor.monotonic())
        lo = st['axis_minimum']; hi = st['axis_maximum']
        return (float(lo[0]), float(lo[1])), (float(hi[0]), float(hi[1]))

    def _homed(self, axes='xyz'):
        h = self.printer.lookup_object('toolhead').get_status(self.reactor.monotonic())['homed_axes']
        return all(a in h for a in axes)

    MS_CORNERS = (("1/4", "X min, Y min", "front left on most printers", 0, 0),
                  ("2/4", "X max, Y min", "front right on most printers", 1, 0),
                  ("3/4", "X max, Y max", "back right on most printers", 1, 1),
                  ("4/4", "X min, Y max", "back left on most printers", 0, 1))

    def _ms_move(self, x=None, y=None, z=None):
        th = self.printer.lookup_object('toolhead')
        lo, hi = self._xy_limits()
        pos = th.get_position()
        if z is not None:
            th.manual_move([None, None, z], 10.)
        if x is not None or y is not None:
            x = pos[0] if x is None else min(max(x, lo[0]), hi[0])
            y = pos[1] if y is None else min(max(y, lo[1]), hi[1])
            th.manual_move([x, y, None], self.mesh_speed)
        th.wait_moves()
        self._sync_gcode_pos()

    def _ms_show(self):
        ms = self._ms
        th = self.printer.lookup_object('toolhead')
        x, y, z = th.get_position()[:3]
        n, axes, hint, _, _ = self.MS_CORNERS[ms['i']]
        st = ms['step']
        texts = ["Corner %s: %s (%s)." % (n, axes, hint),
                 "Jog the nozzle to the edge of the usable bed area, clear of clips and the brush.",
                 "Nozzle now: X %.1f  Y %.1f  Z %.1f" % (x, y, z)]
        c = "OZNLAB_MESH_SETUP"
        steps = [("%g mm" % v, "%s STEP=%g" % (c, v), "primary" if abs(v - st) < 1e-6 else "secondary")
                 for v in (1, 10, 50)]
        rows = [steps,
                [("Y+ %g" % st, "%s JOG=Y DIST=%g" % (c, st), "info")],
                [("X- %g" % st, "%s JOG=X DIST=%g" % (c, -st), "info"),
                 ("X+ %g" % st, "%s JOG=X DIST=%g" % (c, st), "info")],
                [("Y- %g" % st, "%s JOG=Y DIST=%g" % (c, -st), "info")],
                [("Lower to 2 mm (look at the gap)", "%s LOWER=1" % c, "secondary"),
                 ("Raise", "%s RAISE=1" % c, "secondary")]]
        footer = [("Cancel", "%s CANCEL=1" % c, "error"),
                  ("Save corner %s" % n, "%s NEXT=1" % c, "primary")]
        self._prompt("OznLab bed mesh area", texts, rows, footer)

    def _ms_goto_corner(self):
        ms = self._ms
        lo, hi = ms['lo'], ms['hi']
        _, _, _, cx, cy = self.MS_CORNERS[ms['i']]
        m = 15.
        x = lo[0] + m if cx == 0 else hi[0] - m
        y = lo[1] + m if cy == 0 else hi[1] - m
        # start the next corner from what the user already picked on the shared edge
        if ms['pts']:
            px, py = ms['pts'][-1]
            if cx == self.MS_CORNERS[ms['i'] - 1][3]: x = px
            if cy == self.MS_CORNERS[ms['i'] - 1][4]: y = py
        th = self.printer.lookup_object('toolhead')
        self._ms_move(z=max(th.get_position()[2], 5.))
        self._ms_move(x=x, y=y)

    def _ms_area(self):
        p = self._ms['pts']
        return (max(p[0][0], p[3][0]), max(p[0][1], p[1][1]),
                min(p[1][0], p[2][0]), min(p[2][1], p[3][1]))

    cmd_MESH_SETUP_help = ("Pick the bed mesh area with the nozzle (Mainsail/Fluidd popup): "
                           "OZNLAB_MESH_SETUP [RESET=1]")
    def cmd_MESH_SETUP(self, gcmd):
        c = "OZNLAB_MESH_SETUP"
        if gcmd.get_int('CLOSE', 0):
            self._prompt_close(); return
        if gcmd.get_int('SAVECFG', 0):
            # close the popup BEFORE the restart: Mainsail rebuilds open prompts from the
            # console history, so a prompt still open at restart comes back afterwards
            self._prompt_close()
            self.gcode.run_script_from_command("SAVE_CONFIG"); return
        if gcmd.get_int('CANCEL', 0):
            self._ms = None; self._prompt_close()
            try: self._ms_move(z=max(self.printer.lookup_object('toolhead').get_position()[2], 5.))
            except Exception: pass
            gcmd.respond_info("OznLab mesh setup: cancelled, nothing saved"); return
        if gcmd.get_int('SAVE', 0):
            # saving only writes the config: no homing needed (the motors may have timed out)
            return self._ms_save(gcmd)
        if gcmd.get_int('HOME', 0):
            self._prompt_close()
            self.gcode.run_script_from_command("G28")
        if not self._homed():
            self._prompt("OznLab bed mesh area",
                         ["The printer has to be homed before the nozzle can be moved to the corners."],
                         [[("Home all (G28)", "%s HOME=1" % c, "primary")]],
                         [("Cancel", "%s CANCEL=1" % c, "error")])
            return
        self._free(gcmd, "mesh setup", mon=True)
        if self._ms is None or gcmd.get_int('RESET', 0):
            lo, hi = self._xy_limits()
            self._ms = {'i': 0, 'step': 10., 'pts': [], 'lo': lo, 'hi': hi}
            self._ms_goto_corner(); self._ms_show(); return
        ms = self._ms
        if gcmd.get_int('HOME', 0) and ms['i'] < 4:
            # re-homed half way (idle timeout): keep the corners already picked
            self._ms_goto_corner(); self._ms_show(); return
        if ms['i'] >= 4:
            return self._ms_summary()
        step = self._gf(gcmd, 'STEP', None, above=0., maxval=200.)
        if step is not None:
            ms['step'] = step
        jog = gcmd.get('JOG', '').upper()
        if jog in ('X', 'Y'):
            d = self._gf(gcmd, 'DIST', ms['step'], minval=-200., maxval=200.)
            pos = self.printer.lookup_object('toolhead').get_position()
            if jog == 'X': self._ms_move(x=pos[0] + d)
            else: self._ms_move(y=pos[1] + d)
        if gcmd.get_int('LOWER', 0):
            self._ms_move(z=2.)
        if gcmd.get_int('RAISE', 0):
            self._ms_move(z=5.)
        if gcmd.get_int('NEXT', 0):
            pos = self.printer.lookup_object('toolhead').get_position()
            ms['pts'].append((round(pos[0], 1), round(pos[1], 1)))
            self._detail(gcmd, "oznlab mesh setup: corner %s = X %.1f Y %.1f"
                              % (self.MS_CORNERS[ms['i']][0], pos[0], pos[1]))
            ms['i'] += 1
            if ms['i'] >= 4:
                self._ms_move(z=max(self.printer.lookup_object('toolhead').get_position()[2], 5.))
                return self._ms_summary()
            self._ms_goto_corner()
        self._ms_show()

    def _ms_summary(self):
        c = "OZNLAB_MESH_SETUP"
        x0, y0, x1, y1 = self._ms_area()
        if x1 - x0 < 30. or y1 - y0 < 30.:
            self._prompt("OznLab bed mesh area",
                         ["The four corners leave only %.0f x %.0f mm - that cannot be right." % (x1 - x0, y1 - y0),
                          "Check that corner 1 is X min/Y min and the others go round in order."],
                         [], [("Cancel", "%s CANCEL=1" % c, "error"), ("Start again", "%s RESET=1" % c, "primary")])
            return
        texts = ["Mesh area: X %.1f .. %.1f, Y %.1f .. %.1f  (%.0f x %.0f mm)." % (x0, x1, y0, y1, x1 - x0, y1 - y0),
                 "Pick the grid. Each point takes about 7 s: 3x3 ~ 1 min, 5x5 ~ 3 min, 7x7 ~ 6 min, 9x9 ~ 10 min.",
                 "With ADAPTIVE=1 only the part under the print is measured, so a large grid is fine."]
        rows = [[("%dx%d" % (n, n), "%s SAVE=1 COUNT=%d" % (c, n), "primary" if n == 5 else "secondary")
                 for n in (3, 5, 7, 9)]]
        self._prompt("OznLab bed mesh area", texts, rows,
                     [("Cancel", "%s CANCEL=1" % c, "error"), ("Start again", "%s RESET=1" % c, "secondary")])

    def _ms_save(self, gcmd):
        if self._ms is None or len(self._ms['pts']) < 4:
            raise gcmd.error("oznlab mesh setup: pick the four corners first (OZNLAB_MESH_SETUP)")
        n = gcmd.get_int('COUNT', 5, minval=3, maxval=15)
        x0, y0, x1, y1 = self._ms_area()
        if x1 - x0 < 30. or y1 - y0 < 30.:
            raise gcmd.error("oznlab mesh setup: the four corners leave only %.0f x %.0f mm - "
                             "not saved. Corner 1 must be X min / Y min, then go round in order."
                             % (x1 - x0, y1 - y0))
        cfg = self.printer.lookup_object('configfile')
        cfg.set(self.cfg_name, 'mesh_min', "%.1f, %.1f" % (x0, y0))
        cfg.set(self.cfg_name, 'mesh_max', "%.1f, %.1f" % (x1, y1))
        cfg.set(self.cfg_name, 'mesh_count', "%d, %d" % (n, n))
        self.mesh_min = (x0, y0); self.mesh_max = (x1, y1); self.mesh_count = (n, n)
        self._ms = None
        lines = ["Saved: X %.1f .. %.1f, Y %.1f .. %.1f, %dx%d points." % (x0, x1, y0, y1, n, n)]
        if self.printer.lookup_object('bed_mesh', None) is None:
            # without a [bed_mesh] section Klipper cannot apply any mesh; add a minimal one
            cfg.set('bed_mesh', 'mesh_min', "%.1f, %.1f" % (x0, y0))
            cfg.set('bed_mesh', 'mesh_max', "%.1f, %.1f" % (x1, y1))
            cfg.set('bed_mesh', 'probe_count', "%d, %d" % (n, n))
            if n > 6:
                cfg.set('bed_mesh', 'algorithm', 'bicubic')
            lines.append("Your config had no [bed_mesh] section, so one was added to the SAVE_CONFIG block "
                         "(move it into printer.cfg later if you want fade_start etc. next to it).")
            lines.append("SAVE_CONFIG restarts Klipper; after that run OZNLAB_MESH.")
        else:
            lines.append("Active now. SAVE_CONFIG keeps it after a restart. Run OZNLAB_MESH to measure.")
        gcmd.respond_info("OznLab mesh setup: " + lines[0])
        self._prompt("OznLab bed mesh area", lines, [],
                     [("Close", "OZNLAB_MESH_SETUP CLOSE=1", "secondary"),
                      ("SAVE_CONFIG", "OZNLAB_MESH_SETUP SAVECFG=1", "primary")])

    def _tap_point(self, toolhead, samples, pred, speed, accel):
        """Contact z at the current XY for the mesh.
        Tap 1 is a squash tap and is never used: after the XY move it read up to 0.06 mm off in
        BOTH directions (ooze would only read high), so it doubles as the settle tap. It waits
        0.3 s for the toolhead to stop ringing first. Then `samples` kept taps (default 2) that
        must agree within 0.015 mm; up to two more are added if they do not.
        Descents start just above the expected contact (neighbours) - most of the speed-up.
        Returns (z, spread of the kept taps, all taps incl. the squash tap)."""
        full = (self.tap_start_z, self.tap_target_z)
        def one(start, target, settle, pre):
            z = self._tap_once(toolhead, start, target, speed, accel,
                               settle=settle, pre=pre, post=0.2)[0]
            if z > start - 0.03:
                raise self.printer.command_error("contact at the very start of the descent")
            return z
        def full_tap(settle, pre):
            # a full descent gets three attempts, each a little slower to settle: a single
            # missed batch or a noisy trace must not throw away minutes of taps
            last = None
            for attempt in range(3):
                try:
                    return one(full[0], full[1], settle + 0.2 * attempt, pre + 0.1 * attempt)
                except self.printer.command_error as e:
                    last = e
                    logging.info("oznlab mesh: full tap attempt %d failed: %s", attempt + 1, e)
            raise last
        def tap(ref, margin, settle=0.1, pre=0.25):
            if ref is None:
                return full_tap(settle, pre)
            start = min(self.tap_start_z, ref + margin)
            target = max(self.tap_target_z, ref - 0.3)
            try:
                return one(start, target, settle, pre)
            except self.printer.command_error as e:
                logging.info("oznlab mesh: short tap failed (%s), full descent", e)
                return full_tap(settle, pre)
        taps = [tap(pred, 0.6, settle=0.3, pre=0.3)]
        kept = []
        while True:
            ref = kept[-1] if kept else taps[0]
            z = tap(ref, 0.3 if kept else 0.4); kept.append(z); taps.append(z)
            n = len(kept)
            if n < samples:
                continue
            kk = sorted(kept)
            med = kk[n // 2] if n % 2 else 0.5 * (kk[n // 2 - 1] + kk[n // 2])
            if samples == 1:
                ok = abs(kept[0] - taps[0]) <= 0.03
            else:
                # the tightest pair among the kept taps decides
                best = min(kk[k + 1] - kk[k] for k in range(n - 1))
                ok = best <= 0.015
                if ok and n > 2:
                    k = min(range(n - 1), key=lambda k: kk[k + 1] - kk[k])
                    med = 0.5 * (kk[k] + kk[k + 1])
            if ok or n >= samples + 2:
                return med, kk[-1] - kk[0], taps

    cmd_MESH_help = ("Bed mesh with the nozzle as the probe: OZNLAB_MESH [ADAPTIVE=1] [MARGIN=5] "
                     "[COUNT=5] [SAMPLES=2] [PROFILE=] [TEMP=] [KEEP_HOT=1]")
    def cmd_MESH(self, gcmd):
        th = self.printer.lookup_object('toolhead')
        if not self._homed():
            raise gcmd.error("oznlab mesh: home X, Y and Z first")
        self._end_crash_test("OZNLAB_MESH")
        self._free(gcmd, "mesh", mon=True)
        bm = self.printer.lookup_object('bed_mesh', None)
        if bm is None:
            raise gcmd.error("oznlab mesh: there is no [bed_mesh] section - run OZNLAB_MESH_SETUP, "
                             "then SAVE_CONFIG")
        if self.mesh_min is None or self.mesh_max is None:
            raise gcmd.error("oznlab mesh: no mesh area yet - run OZNLAB_MESH_SETUP first")
        # every parameter is parsed before anything heats or moves
        temp = self._gf(gcmd, 'TEMP', None, minval=0., maxval=300.)
        samples = gcmd.get_int('SAMPLES', self.mesh_samples, minval=1, maxval=5)
        keep_hot = gcmd.get_int('KEEP_HOT', 0)
        cnt = gcmd.get_int('COUNT', None, minval=3, maxval=15)
        adaptive = gcmd.get_int('ADAPTIVE', 0)
        margin = self._gf(gcmd, 'MARGIN', 5., minval=0.)
        profile_arg = gcmd.get('PROFILE', None)
        now = self.reactor.monotonic()
        heater = th.get_extruder().get_heater()
        hs = heater.get_status(now)
        t_noz = temp if temp is not None else (hs.get('target') or hs.get('temperature', 0.))
        if t_noz < self.mesh_min_temp:
            gcmd.respond_info("OznLab mesh: nozzle is only %.0f C - soft plastic on the tip makes the points "
                              "drift. Best at printing temperature with a brushed nozzle." % t_noz)
        try:
            bed = self.printer.lookup_object('heater_bed', None)
            bs = bed.get_status(now) if bed is not None else None
        except Exception:
            bs = None
        if bs is not None and (bs.get('target') or 0.) < 40.:
            gcmd.respond_info("OznLab mesh: the bed is cold - a hot bed has a different shape, "
                              "heat it to printing temperature for a mesh you print with")
        if temp is not None:
            self.gcode.run_script_from_command("M109 S%.0f" % temp)
        nx, ny = (cnt, cnt) if cnt else self.mesh_count
        ax0, ay0 = self.mesh_min; ax1, ay1 = self.mesh_max
        x0, y0, x1, y1 = ax0, ay0, ax1, ay1
        adaptive_hit = False
        if adaptive:
            eo = self.printer.lookup_object('exclude_object', None)
            objs = eo.get_status(now).get('objects', []) if eo is not None else []
            pts = [p for o in objs for p in (o.get('polygon') or [])]
            if pts:
                adaptive_hit = True
                x0 = max(ax0, min(p[0] for p in pts) - margin); x1 = min(ax1, max(p[0] for p in pts) + margin)
                y0 = max(ay0, min(p[1] for p in pts) - margin); y1 = min(ay1, max(p[1] for p in pts) + margin)
                # keep at least 20 mm per axis so the mesh is well defined
                for lo_, hi_, a0, a1, k in ((x0, x1, ax0, ax1, 'x'), (y0, y1, ay0, ay1, 'y')):
                    if hi_ - lo_ < 20.:
                        mid = (lo_ + hi_) / 2.
                        lo_ = max(a0, mid - 10.); hi_ = min(a1, lo_ + 20.); lo_ = max(a0, hi_ - 20.)
                        if k == 'x': x0, x1 = lo_, hi_
                        else: y0, y1 = lo_, hi_
                nx = max(3, min(nx, int(math.ceil(nx * (x1 - x0) / (ax1 - ax0)))))
                ny = max(3, min(ny, int(math.ceil(ny * (y1 - y0) / (ay1 - ay0)))))
            else:
                gcmd.respond_info("OznLab mesh: no object outlines from the slicer, measuring the whole area")
        bmc = getattr(bm, 'bmc', None)
        mc = dict(getattr(bmc, 'mesh_config', {}) or {})
        pps = (mc.get('mesh_x_pps', 2), mc.get('mesh_y_pps', 2))
        algo = mc.get('algo', 'lagrange')
        if max(pps) == 0:
            algo = 'direct'
        else:
            if max(nx, ny) > 6:
                algo = 'bicubic'
                nx, ny = max(nx, 4), max(ny, 4)          # bicubic needs 4+ on both axes
            elif algo == 'bicubic' and min(nx, ny) < 4:
                algo = 'lagrange'
        # an adaptive mesh covers only this print: it is applied but never stored, so it cannot
        # replace the full-bed profile (upstream bed_mesh does the same)
        if profile_arg:
            profile = profile_arg
        elif adaptive_hit:
            profile = None
        else:
            profile = (self.mesh_profile or
                       ('oznlab' if self._other_probe() else 'default'))
        xs = [x0 + (x1 - x0) * i / (nx - 1) for i in range(nx)]
        ys = [y0 + (y1 - y0) * j / (ny - 1) for j in range(ny)]
        try:
            kin = th.get_kinematics()
            accel = min(th.max_accel, getattr(kin, 'max_z_accel', th.max_accel))
            z_min = kin.rails[2].get_range()[0]
        except Exception:
            accel = 100.; z_min = None
        accel = accel or 100.
        z_target = self.tap_target_z
        if z_min is not None and z_target < z_min:
            raise gcmd.error("oznlab mesh: tap_target_z %.2f is below [stepper_z] position_min %.2f"
                             % (z_target, z_min))
        z_start = self.tap_start_z; travel_z = self.mesh_travel_z
        speed = self.tap_speed
        est = nx * ny * (3.0 + 2.1 * samples)                 # measured: 5x5, 2 taps = 175 s
        gcmd.respond_info("OznLab mesh: %dx%d points, about %s" % (
            nx, ny, "%.0f s" % est if est < 90 else "%.0f min" % (est / 60.)))
        self._detail(gcmd, "oznlab mesh: X %.1f..%.1f  Y %.1f..%.1f, 1 squash tap + %d kept tap(s) each, %s"
                     % (x0, x1, y0, y1, samples,
                        "profile '%s'" % profile if profile else "adaptive (not stored)"))
        bm.set_mesh(None)                                   # a failed run must not leave the old mesh active
        t_begin = self.reactor.monotonic()
        matrix = []; worst = 0.; wide = []
        log = None
        try:
            cfg_dir = os.path.dirname(self.printer.get_start_args()['config_file'])
            log_name = os.path.join(cfg_dir, 'oznlab_mesh_taps.csv')
            log = open(log_name, 'w')
            log.write("row,col,x,y,tap,z,median,t_noz,predicted\n")
        except Exception:
            logging.exception("oznlab mesh: could not open the tap log"); log = None
        try:
            # the toolhead may be parked high over the bucket / brush: travel to the first
            # point at the current height when that is higher, never descend on the spot
            z_now = th.get_position()[2]
            first_z = max(z_now, travel_z)
            got = {}
            for j, y in enumerate(ys):
                row = [0.] * nx
                order = range(nx) if j % 2 == 0 else range(nx - 1, -1, -1)
                for i in order:
                    if got:
                        travel = max(travel_z, max(got.values()) + 1.0)
                    else:
                        travel = first_z
                    th.manual_move([None, None, travel], 10.)
                    th.manual_move([xs[i], y, None], self.mesh_speed)
                    # expected contact from measured neighbours (same row, row before)
                    nb = [got[k] for k in ((i - 1, j), (i + 1, j), (i, j - 1)) if k in got]
                    pred = (max(nb) if nb else None)
                    try:
                        z, spread, taps = self._tap_point(th, samples, pred, speed, accel)
                    except self.printer.command_error as e:
                        raise gcmd.error("oznlab mesh: point X %.1f Y %.1f failed three times (%s) - "
                                         "is the bed there? tap_target_z reachable?" % (xs[i], y, e))
                    row[i] = z; got[(i, j)] = z; worst = max(worst, spread)
                    if len(taps) > samples + 1:
                        wide.append("X%.0f Y%.0f: %s" % (xs[i], y, " ".join("%.3f" % v for v in taps)))
                    if log is not None:
                        try:
                            tn = th.get_extruder().get_heater().get_status(self.reactor.monotonic())['temperature']
                            for k, v in enumerate(taps):
                                log.write("%d,%d,%.1f,%.1f,%d,%.4f,%.4f,%.1f,%s\n" % (
                                    j, i, xs[i], y, k + 1, v, z, tn, "" if pred is None else "%.4f" % pred))
                        except Exception:
                            pass
                if j + 1 < ny:
                    gcmd.respond_info("OznLab mesh: %d%%" % (100 * (j + 1) // ny))
                self._detail(gcmd, "oznlab mesh: row %d/%d  %s" % (j + 1, ny, "  ".join("%.3f" % v for v in row)))
                matrix.append(row)
        finally:
            self._release_tap()
            if log is not None:
                try: log.close()
                except Exception: pass
            try:
                th.manual_move([None, None, max(th.get_position()[2], travel_z)], 10.); th.wait_moves()
            except Exception:
                logging.exception("oznlab mesh: could not lift after an error")
            self._sync_gcode_pos()
            # run from the console: switch the heaters off afterwards (also after an error).
            # Inside a print (PRINT_START) they must stay on. KEEP_HOT=1 / ADAPTIVE=1 keep them.
            # ADAPTIVE=1 only makes sense inside a print: never touch the heaters then, even
            # when print_stats cannot tell (G-code streamed from OctoPrint stays 'standby')
            if not keep_hot and not adaptive:
                try:
                    state = self.printer.lookup_object('print_stats').get_status(
                        self.reactor.monotonic())['state']
                except Exception:
                    state = 'standby'
                if state not in ('printing', 'paused'):
                    try:
                        self.gcode.run_script_from_command("TURN_OFF_HEATERS")
                        gcmd.respond_info("OznLab mesh: heaters off (KEEP_HOT=1 keeps them on)")
                    except Exception:
                        logging.exception("oznlab mesh: could not switch the heaters off")
        if wide:
            self._detail(gcmd, "oznlab mesh: points that needed extra taps (first = squash tap, "
                         "not used):\n  " + "\n  ".join(wide))
        from . import bed_mesh as bm_mod
        import collections
        params = collections.OrderedDict()
        params['min_x'] = xs[0]; params['max_x'] = xs[-1]
        params['min_y'] = ys[0]; params['max_y'] = ys[-1]
        params['x_count'] = nx; params['y_count'] = ny
        params['mesh_x_pps'] = pps[0]; params['mesh_y_pps'] = pps[1]
        params['algo'] = algo; params['tension'] = mc.get('tension', 0.2)
        try:
            zm = bm_mod.ZMesh(params, profile)
        except TypeError:                                   # older Klipper: ZMesh(params)
            zm = bm_mod.ZMesh(params)
        try:
            zm.build_mesh(matrix)
        except Exception as e:
            raise gcmd.error("oznlab mesh: bed_mesh rejected the points (%s)" % (e,))
        # Reference: contact heights are absolute (0.0..0.5 mm here). bed_mesh's fade would
        # carry that whole offset into the upper layers when fade_target is set, and a short
        # fade range rejects the mesh outright. Use [bed_mesh] zero_reference_position when it
        # is set and inside the area, otherwise centre the mesh on its own average - exactly
        # what a probe mesh looks like. OZNLAB_TAP subtracts the mesh value at its XY, so the
        # first layer is unaffected by this choice.
        # with mesh_pps 0 bed_mesh uses 'direct' and mesh_matrix IS probed_matrix (one list):
        # any offset applied to both would land twice. Give mesh_matrix its own copy.
        if getattr(zm, 'mesh_matrix', None) is not None and zm.mesh_matrix is zm.probed_matrix:
            zm.mesh_matrix = [list(r) for r in zm.probed_matrix]
        ref_note = ""
        zref = None
        try:
            zref = bm.bmc.probe_mgr.get_zero_ref_pos()
        except Exception:
            zref = None
        if zref is not None and xs[0] <= zref[0] <= xs[-1] and ys[0] <= zref[1] <= ys[-1] \
                and hasattr(zm, 'set_zero_reference'):
            zm.set_zero_reference(zref[0], zref[1])
            ref_note = "zero at (%.0f, %.0f)" % (zref[0], zref[1])
        else:
            avg = sum(v for r in matrix for v in r) / float(nx * ny)
            for r in (zm.probed_matrix, zm.mesh_matrix):
                for line in r:
                    for k in range(len(line)):
                        line[k] -= avg
            ref_note = "centred (average %.3f removed)" % avg
        bm.set_mesh(zm)
        if profile:
            try:
                bm.save_profile(profile)
            except Exception:
                logging.exception("oznlab mesh: could not store profile %s", profile)
        flat = [v for r in zm.get_probed_matrix() for v in r]
        dur = self.reactor.monotonic() - t_begin
        gcmd.respond_info("OznLab mesh: done in %s, bed range %.2f mm%s. %s" % (
            "%.0f s" % dur if dur < 90 else "%d min %02d s" % (dur // 60, dur % 60),
            max(flat) - min(flat),
            ", %d point(s) needed extra taps" % len(wide) if wide else "",
            ("Active as '%s' - SAVE_CONFIG to keep it." % profile) if profile else
            "Active for this print only."))
        self._detail(gcmd, "oznlab mesh: min %.3f max %.3f, worst tap spread %.3f mm, %s. Klipper does not "
                     "load profiles by itself: BED_MESH_PROFILE LOAD=%s in PRINT_START, then OZNLAB_TAP."
                     % (min(flat), max(flat), worst, ref_note, profile or "..."))

    def _profile_mesh(self, bm, name):
        from . import bed_mesh as bm_mod
        prof = bm.pmgr.get_profiles().get(name)
        if prof is None:
            return None
        try:
            zm = bm_mod.ZMesh(prof['mesh_params'], name)
        except TypeError:
            zm = bm_mod.ZMesh(prof['mesh_params'])
        zm.build_mesh(prof['points'])
        return zm

    cmd_MESH_COMPARE_help = ("Compare two bed mesh profiles point by point: "
                             "OZNLAB_MESH_COMPARE [A=default] [B=oznlab]")
    def cmd_MESH_COMPARE(self, gcmd):
        bm = self.printer.lookup_object('bed_mesh', None)
        if bm is None:
            raise gcmd.error("oznlab compare: no [bed_mesh] section - there is no mesh to compare yet")
        na = gcmd.get('A', 'default'); nb = gcmd.get('B', 'oznlab')
        names = sorted(bm.pmgr.get_profiles().keys())
        ma = self._profile_mesh(bm, na); mb = self._profile_mesh(bm, nb)
        if ma is None or mb is None:
            hint = ""
            if not self._other_probe():
                hint = (" - this printer has no probe, so the nozzle mesh is the only mesh and there is "
                        "nothing to compare it with")
            elif mb is None:
                hint = " - run OZNLAB_MESH first (it saves the nozzle mesh as 'oznlab' when a probe exists)"
            raise gcmd.error("oznlab compare: profile '%s' not found (have: %s)%s"
                             % (na if ma is None else nb, ", ".join(names) or "none", hint))
        pa = ma.get_mesh_params(); pb = mb.get_mesh_params()
        x0 = max(pa['min_x'], pb['min_x']); x1 = min(pa['max_x'], pb['max_x'])
        y0 = max(pa['min_y'], pb['min_y']); y1 = min(pa['max_y'], pb['max_y'])
        if x1 - x0 < 10. or y1 - y0 < 10.:
            raise gcmd.error("oznlab compare: the two meshes barely overlap")
        # compare on B's measured points that lie inside A's area (no extrapolation)
        nx, ny = pb['x_count'], pb['y_count']
        bx = [pb['min_x'] + (pb['max_x'] - pb['min_x']) * i / (nx - 1) for i in range(nx)]
        by = [pb['min_y'] + (pb['max_y'] - pb['min_y']) * j / (ny - 1) for j in range(ny)]
        xs = [x for x in bx if x0 - 0.01 <= x <= x1 + 0.01]
        ys = [y for y in by if y0 - 0.01 <= y <= y1 + 0.01]
        if len(xs) < 2 or len(ys) < 2:
            xs = [x0 + (x1 - x0) * i / 4. for i in range(5)]
            ys = [y0 + (y1 - y0) * j / 4. for j in range(5)]
        d = [[mb.calc_z(x, y) - ma.calc_z(x, y) for x in xs] for y in ys]
        flat = [v for r in d for v in r]
        n = len(flat); off = sum(flat) / n
        # best-fit plane: a tilt difference (z_tilt in between) is not a shape difference
        sx = sy = sxx = syy = sxy = sz = sxz = syz = 0.
        for jy, y in enumerate(ys):
            for ix, x in enumerate(xs):
                v = d[jy][ix]
                sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y
                sz += v; sxz += x * v; syz += y * v
        M = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, float(n)]]
        rhs = [sxz, syz, sz]
        def det3(m):
            return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                    - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                    + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
        D = det3(M)
        coef = []
        for k in range(3):
            mk = [row[:] for row in M]
            for r in range(3): mk[r][k] = rhs[r]
            coef.append(det3(mk) / D if abs(D) > 1e-12 else 0.)
        res = [[d[jy][ix] - (coef[0] * x + coef[1] * y + coef[2]) for ix, x in enumerate(xs)]
               for jy, y in enumerate(ys)]
        rflat = [v for r in res for v in r]
        rms = math.sqrt(sum(v * v for v in rflat) / n)
        out = ["oznlab compare: %s minus %s at %d points (X %.0f..%.0f, Y %.0f..%.0f)"
               % (nb, na, n, xs[0], xs[-1], ys[0], ys[-1]),
               "  constant offset %+.3f mm (different zero points, ignore)" % off,
               "  tilt difference %+.3f mm/100mm in X, %+.3f mm/100mm in Y" % (coef[0] * 100., coef[1] * 100.),
               "  SHAPE difference after removing both: rms %.3f mm, worst %+.3f mm"
               % (rms, max(rflat, key=abs)),
               "  per point, front row first (mm):"]
        for jy, y in enumerate(ys):
            out.append("   Y%4.0f  %s" % (y, "  ".join("%+.3f" % v for v in res[jy])))
        verdict = ("they agree" if rms <= 0.015 else
                   "close, worth a second look" if rms <= 0.03 else "they do NOT agree")
        worst_i = max(range(n), key=lambda k: abs(rflat[k]))
        wx = xs[worst_i % len(xs)]; wy = ys[worst_i // len(xs)]
        gcmd.respond_info("OznLab compare: %s vs %s - %s (shape differs by %.3f mm on average, "
                          "most at X%.0f Y%.0f: %+.3f)" % (nb, na, verdict, rms, wx, wy, rflat[worst_i]))
        self._detail(gcmd, "\n".join(out))


# ================= TAP HOMING (nozzle on bed, MCU-side trigger) =================
# The descent is stopped by Klipper's trigger_analog on the toolhead MCU: the LDC1612 samples go
# through a first-order low-pass and a derivative, and |d f / d sample| above a threshold fires the
# trsync that stops the Z steppers - the same mechanism the BTT Eddy tap uses, with no host latency.
# Before contact the coil sees nothing but thermal drift (a few Hz/s), on contact the frequency
# ramps at sensitivity x speed (1.5..10 Hz/um x 3 mm/s = 5..30 kHz/s), so the derivative is a clean
# discriminator and is immune to the drift a level trigger would trip on during a long descent.
# The trigger only has to be within a few tenths of a millimetre: after it the nozzle lifts 1 mm and
# the normal kink-fit tap (the one OZNLAB_TAP uses) measures the contact to ~10 um. That contact is
# what Klipper's homing gets as the probe result, so Z=0 is the bed at tap precision.
class _SosDesign:
    """the minimal 'filter design' trigger_analog.MCU_SosFilter needs, without scipy:
    one first-order low-pass section, one derivative section"""
    def __init__(self, sps, cutoff_hz):
        a = 1. - math.exp(-2. * math.pi * cutoff_hz / float(sps))
        self.a = a
        self.sections = [[a, 0., 0., 1., -(1. - a), 0.],     # y = a x + (1-a) y[n-1]
                         [1., -1., 0., 1., 0., 0.]]           # y = x - x[n-1]
    def get_filter_sections(self):
        return self.sections
    def get_initial_state(self):
        return [[0., 0.] for _ in self.sections]
    def get_size(self):
        return len(self.sections)

MAX_VALID_RAW_VALUE = 0x03ffffff

class OznLabHoming:
    def __init__(self, oz, config):
        self.oz = oz
        self.printer = oz.printer
        try:
            from . import trigger_analog, probe, manual_probe
        except ImportError:
            trigger_analog = None
        OLD = ("oznlab z_homing needs a Klipper from late May 2026 or newer (%s missing). Update Klipper, "
               "flash the toolhead board with it, or set z_homing: 0")
        if trigger_analog is None:
            raise config.error(OLD % "trigger_analog")
        self.trigger_analog = trigger_analog; self.probe = probe; self.manual_probe = manual_probe
        missing = [n for n in ('MCU_trigger_analog', 'MCU_SosFilter') if not hasattr(trigger_analog, n)]
        missing += [n for n in ('SampleAveragingHelper', 'ProbeParameterHelper', 'ProbeCommandHelper',
                                'LookupZSteppers', 'lookup_minimum_z', 'HomingViaProbeHelper')
                    if not hasattr(probe, n)]
        if not missing:
            try:
                import inspect
                if 'position_endstop' not in inspect.signature(probe.HomingViaProbeHelper.__init__).parameters:
                    missing.append('HomingViaProbeHelper(position_endstop)')
            except (TypeError, ValueError):
                pass
        if missing:
            raise config.error(OLD % ", ".join(missing))
        self.printer.register_event_handler('klippy:mcu_identify', self._check_firmware)
        self.ta = trigger_analog.MCU_trigger_analog(oz.sensor)
        cmdq = self.ta.get_dispatch().get_command_queue()
        self.sos = trigger_analog.MCU_SosFilter(oz.sensor.get_mcu(), cmdq, 2)
        self.ta.setup_sos_filter(self.sos)
        probe.LookupZSteppers(config, self.ta.get_dispatch().add_stepper)
        self.z_min = probe.lookup_minimum_z(config)
        self.param_helper = probe.ProbeParameterHelper(config)
        self.session = probe.SampleAveragingHelper(config, self.param_helper, self._start_session)
        self.last = None
        self._in_session = False
        if oz.z_homing_probe:
            other = [sec for sec in ('probe', 'bltouch', 'smart_effector', 'load_cell_probe', 'dockable_probe',
                                     'beacon', 'cartographer', 'scanner') if config.has_section(sec)]
            other += config.get_prefix_sections('probe_eddy_current')
            if other or self.printer.lookup_object('probe', None) is not None:
                raise config.error("oznlab z_homing_probe: there is already a [probe] - set "
                                   "z_homing_probe: 0 (tap homing can still be tested with OZNLAB_HOME_TEST)")
            # nozzle = probe: no XY offset, contact = Z 0 (squish comes from tap_adjust_z via OZNLAB_TAP)
            self.cmd_helper = probe.ProbeCommandHelper(config, self, None, can_set_z_offset=False)
            probe.HomingViaProbeHelper(config, 0.)
            self.printer.add_object('probe', self)

    def _check_firmware(self):
        # host updated, toolhead board not: say so instead of a bare "MCU Protocol error"
        mcu = self.oz.sensor.get_mcu()
        if not mcu.check_valid_response("trigger_analog_query_state oid=%c"):
            raise self.printer.config_error(
                "oznlab z_homing: the Klipper firmware on '%s' is too old (no trigger_analog). Flash the "
                "toolhead board with the same Klipper version as the host, or set z_homing: 0" % mcu.get_name())

    # --- Klipper probe interface (only used when z_homing_probe is on)
    def get_probe_params(self, gcmd=None):
        return self.param_helper.get_probe_params(gcmd)
    def get_offsets(self, gcmd=None):
        return (0., 0., 0.)
    def get_status(self, eventtime):
        st = {'name': self.oz.cfg_name, 'last_query': False, 'last_z_result': 0.}
        if getattr(self, 'cmd_helper', None) is not None:
            st = self.cmd_helper.get_status(eventtime)
        if self.last:
            st = dict(st); st.update(last_trigger_z=self.last['trigger'], last_contact_z=self.last['contact'])
        return st
    def start_probe_session(self, gcmd):
        return self.session.start_probe_session(gcmd)

    # --- hardware session
    def _start_session(self, gcmd):
        self._in_session = True
        self.results = []
        return self
    def end_probe_session(self):
        self._in_session = False
        self.results = []
    def pull_probed_results(self):
        r = self.results; self.results = []
        return r

    def _prep_trigger(self, speed):
        """set the MCU filter and threshold for this descent speed; raises when the expected
        contact slope is too close to the noise floor (the trigger could miss and the nozzle
        would plough on to position_min)"""
        oz = self.oz; sensor = oz.sensor
        sps = float(sensor.get_samples_per_second())
        # The sensitivity rises with the hotend temperature (about 2 Hz/um cold, 10+ hot). A value
        # measured hot must not be used cold: the threshold would sit above the real contact
        # slope and the trigger would never fire. Trust the last tap only if the nozzle is not
        # noticeably cooler now than it was then; otherwise take the smaller, safe value.
        sens = oz.last_sens
        t_now = oz._noz_temp()
        if not sens:
            sens = oz.home_assume_sens
        elif oz._tap_T is None or t_now is None or t_now < oz._tap_T - 10.:
            sens = min(sens, oz.home_assume_sens)
        slope = sens * speed * 1000. / sps                   # Hz per sample once in contact
        design = _SosDesign(sps, oz.home_lowpass)
        noise = (oz.last_stats or {}).get('noise') or 4.     # Hz rms per raw sample
        # first-order LP then a difference: sigma_d = a * sigma * sqrt(2 / (2 - a))
        noise_d = noise * design.a * math.sqrt(2. / (2. - design.a))
        floor = oz.home_noise_sigma * noise_d
        thr = max(oz.home_trigger_frac * slope, floor)
        if thr > 0.75 * slope:
            raise self.printer.command_error(
                "oznlab homing: expected contact slope %.1f Hz/sample (%.1f Hz/um x %.1f mm/s at %.0f sps) "
                "is too close to the noise floor %.1f Hz/sample - the trigger could miss. Heat the hotend "
                "(sensitivity rises with temperature), lower data_rate, or raise the homing speed."
                % (slope, sens, speed, sps, floor))
        self.sos.set_filter_design(design)
        self.sos.set_offset_scale(0, 1000. * sensor.convert_raw_to_frequency(1), auto_offset=True)
        self.ta.set_raw_range(0, MAX_VALID_RAW_VALUE)
        self.ta.set_trigger('abs_ge', int(thr * 1000. + 0.5))     # filter runs in milli-Hz
        return slope, thr, sens

    def _descend_and_tap(self, gcmd, speed, check_movement, floor=None):
        oz = self.oz
        oz._end_crash_test("Z homing")
        th = self.printer.lookup_object('toolhead')
        # the kinematics cap Z at max_z_velocity; the expected slope must use the real speed
        try:
            speed = min(speed, getattr(th.get_kinematics(), 'max_z_velocity', speed) or speed)
        except Exception:
            pass
        slope, thr, sens = self._prep_trigger(speed)
        pos = th.get_position()
        pos[2] = self.z_min if floor is None else max(self.z_min, floor)
        phoming = self.printer.lookup_object('homing')
        # the LDC1612 is only sampled while a host client is subscribed; without one the MCU
        # trigger would see no data (its monitor then aborts the move, but do not rely on that)
        live = {'on': True}
        oz.sensor.add_client(lambda msg: live['on'])
        oz.reactor.pause(oz.reactor.monotonic() + 0.3)
        try:
            trig = phoming.probing_move(self.ta, pos, speed, check_movement=check_movement)
        finally:
            live['on'] = False
        # coarse contact is trig[2]; now the fine tap from 1 mm above it.
        # During G28 the toolhead runs in homing's temporary frame (Z ~ 1.5 x the axis length),
        # where every ordinary move is "out of range". Shift the frame so the trigger point is
        # Z 0 for the fine taps (this also makes z_min a floor 1 mm below the trigger), and
        # shift back afterwards. Outside homing the shift is invisible.
        th.wait_moves()
        p = th.get_position(); delta = p[2]
        p[2] = 0.; th.set_position(p)
        z_now = 0.
        try:
            kin = th.get_kinematics()
            accel = min(th.max_accel, getattr(kin, 'max_z_accel', th.max_accel)) or 100.
        except Exception:
            accel = 100.
        z_start = z_now + 1.0
        # z_now is already past contact (the trigger stops 0.05-0.09 mm late at 3 mm/s), so
        # 0.25 below it is about as deep as an ordinary tap (tap_target_z -0.3 below contact)
        z_target = max(self.z_min, z_now - 0.25)
        # fine taps. Measured on the reference printer: right after the MCU press the first fine
        # tap reads ~0.02 mm LOW and the following ones creep back up (0.064 -> 0.083 -> 0.089),
        # the hotend mount relaxing after being pushed. So: wait, one relax tap that is not used,
        # then kept taps until two in a row agree within 0.01 mm (max 4), mean of that pair.
        zs = []
        try:
            # lift off the bed first, then let the hotend mount relax in the air
            th.manual_move([None, None, z_start], 10.); th.wait_moves()
            oz.reactor.pause(oz.reactor.monotonic() + 0.8)
            for k in range(5):
                if zs:
                    z_start = zs[-1] + 0.4
                    z_target = max(self.z_min, zs[-1] - 0.3)
                z_k, hz_um, amp, f_pre = oz._tap_once(th, z_start, z_target, oz.tap_speed, accel,
                                                      settle=0.3 if k == 0 else 0.15,
                                                      pre=0.3 if k == 0 else 0.25, post=0.25)
                zs.append(z_k)
                if len(zs) >= 3 and abs(zs[-1] - zs[-2]) <= 0.01:
                    break
        finally:
            try:
                th.wait_moves()
                p = th.get_position(); p[2] += delta; th.set_position(p)
            finally:
                oz._sync_gcode_pos()
        zs = [z + delta for z in zs]
        kept = zs[1:]
        if len(kept) >= 2 and abs(kept[-1] - kept[-2]) <= 0.01:
            z_c = 0.5 * (kept[-1] + kept[-2])
        else:
            zz = sorted(kept); z_c = zz[len(zz) // 2]
        self.last_fine = zs
        self.last = dict(trigger=trig[2], contact=z_c, sens=hz_um, sens_assumed=sens,
                         slope=slope, thr=thr, speed=speed)
        return trig, z_c

    def run_probe(self, gcmd):
        params = self.param_helper.get_probe_params(gcmd)
        speed = params['probe_speed']
        phoming = self.printer.lookup_object('homing')
        check_movement = not phoming.check_probe_first_home(gcmd)
        trig, z_c = self._descend_and_tap(gcmd, speed, check_movement)
        self.results.append(self.manual_probe.ProbeResult(trig[0], trig[1], z_c, trig[0], trig[1], trig[2]))

    def dry_run(self, gcmd, speed=None):
        """OZNLAB_HOME_TEST: same descent on an already homed Z, nothing is changed"""
        oz = self.oz
        th = self.printer.lookup_object('toolhead')
        if speed is None:
            speed = min(3., self.param_helper.get_probe_params(None)['probe_speed'])
        # Z is homed here, so the bed is known to be near 0: never descend below -0.5 even if the
        # trigger misses (position_min may be -10)
        z0 = max(th.get_position()[2], 3.)
        th.manual_move([None, None, z0], 10.); th.wait_moves()
        trig, z_c = self._descend_and_tap(gcmd, speed, True, floor=-0.5)
        l = self.last
        over = abs(trig[2] - z_c)
        gcmd.respond_info("OznLab home test: %s - stopped %.2f mm past the bed, contact at z=%.3f"
                          % ("OK" if over < 0.3 else "stopped late", over, z_c))
        oz._detail(gcmd, "oznlab home test: %.1f mm/s from z=%.2f; MCU trigger z=%.4f (threshold %.1f "
                     "Hz/sample, expected slope %.1f, sensitivity assumed %.1f Hz/um); fine taps %s "
                     "(first not used) -> %.4f, %.1f Hz/um measured"
                     % (speed, z0, trig[2], l['thr'], l['slope'], l['sens_assumed'],
                        " ".join("%.4f" % v for v in getattr(self, 'last_fine', [])), z_c, l['sens']))


def load_config_prefix(config):
    return OznLabSensor(config)

def load_config(config):          # a plain [oznlab_sensor] section works too
    return OznLabSensor(config)
