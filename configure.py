#!/usr/bin/env python3
# OznLab Sensor - writes the [oznlab_sensor hotend] section into printer.cfg
#   python3 configure.py                  asks which board the coil is wired to
#   BOARD=ebb python3 configure.py        no questions (ebb | gen2 | i2c bus name)
#   MCU=EBBCan python3 configure.py       the [mcu ...] section the coil is wired to
#   CONFIG_PATH=~/printer_data/config     where printer.cfg lives
# It also makes sure [stepper_z] position_min is -1 (the tap goes a little below zero).
# Every file it changes is backed up first (printer-<date>.cfg next to it).
import glob, os, re, sys, time

CONFIG = os.path.expanduser(os.environ.get('CONFIG_PATH', '~/printer_data/config'))
HOST_MCU = ('host', 'rpi', 'pi', 'cm4', 'cb1', 'linux', 'mkspi')
BOARDS = [
    ('ebb',  "BTT EBB36 / EBB42 v1.1, v1.2", 'i2c3_PB3_PB4'),
    ('gen2', "BTT EBB36 / EBB42 GEN2",       'i2c3_PA7_PA6'),
]
SECTION = """
# ---------------------------------------------------------------------
# OznLab Sensor (written by configure.py; the guide explains every line)
# Keep this section here in printer.cfg, not in an included file:
# SAVE_CONFIG writes the values the module measures into it.
# ---------------------------------------------------------------------
[oznlab_sensor hotend]
i2c_mcu: %(mcu)s
i2c_bus: %(bus)s
i2c_address: 43               # JP1 on 2B = 43 (default), on 2A = 42
tap_adjust_z: 0.04            # first layer too squished? babystep, then OZNLAB_TAP_ADJUST
clog_gcode: PAUSE
runout_gcode: PAUSE
"""

def say(msg):
    print(msg)


def ask(prompt, choices):
    """numbered question on the terminal; returns the chosen key"""
    if not sys.stdin.isatty():
        return None
    say(prompt)
    for i, (key, label) in enumerate(choices, 1):
        say("  %d) %s" % (i, label))
    while True:
        try:
            a = input("> ").strip()
        except EOFError:
            return None
        if a.isdigit() and 1 <= int(a) <= len(choices):
            return choices[int(a) - 1][0]
        for key, label in choices:
            if a.lower() == key.lower():
                return key
        say("type a number from the list")


def cfg_files(main):
    """printer.cfg and everything it includes, recursively"""
    seen = []
    def walk(path):
        if path in seen or not os.path.isfile(path):
            return
        seen.append(path)
        base = os.path.dirname(path)
        for line in open(path, errors='replace'):
            m = re.match(r'\s*\[include\s+(.+?)\s*\]', line)
            if m:
                for f in sorted(glob.glob(os.path.join(base, m.group(1)))):
                    walk(f)
    walk(main)
    return seen


def sections(path):
    """[(name, first line index)] of the sections in a file, comments ignored"""
    out = []
    for i, line in enumerate(open(path, errors='replace')):
        m = re.match(r'\s*\[([^\]#;]+)\]', line)
        if m and not line.lstrip().startswith(('#', ';')):
            out.append((m.group(1).strip(), i))
    return out


def backup(path):
    stamp = time.strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(os.path.dirname(path), "%s-%s.cfg" % (os.path.splitext(os.path.basename(path))[0], stamp))
    open(dst, 'w').write(open(path, errors='replace').read())
    return dst


def fix_position_min(files):
    """[stepper_z] position_min: -1 (comment the old line, or add one)"""
    for path in files:
        secs = sections(path)
        for k, (name, start) in enumerate(secs):
            if name != 'stepper_z':
                continue
            lines = open(path, errors='replace').read().split('\n')
            end = secs[k + 1][1] if k + 1 < len(secs) else len(lines)
            for i in range(start + 1, end):
                m = re.match(r'\s*position_min\s*[:=]\s*(-?[\d.]+)', lines[i])
                if m:
                    if float(m.group(1)) <= -0.5:
                        return "position_min %s is fine" % m.group(1)
                    lines[i] = "position_min: -1               # OznLab: the tap goes below zero (was %s)" % m.group(1)
                    break
            else:
                lines.insert(start + 1, "position_min: -1               # OznLab: the tap goes below zero")
            backup(path)
            open(path, 'w').write('\n'.join(lines))
            return "position_min set to -1 in %s" % os.path.basename(path)
    return "no [stepper_z] found - check position_min yourself (delta printers: minimum_z_position)"


def main():
    main_cfg = os.path.join(CONFIG, 'printer.cfg')
    if not os.path.isfile(main_cfg):
        say("No printer.cfg in %s. Run again with CONFIG_PATH=/path/to/config" % CONFIG)
        return 1
    files = cfg_files(main_cfg)
    all_secs = [(n, os.path.basename(p)) for p in files for n, _ in sections(p)]
    if any(n.startswith('oznlab_sensor') for n, _ in all_secs):
        say("[oznlab_sensor ...] is already in your config, nothing written.")
        say(fix_position_min(files))
        return 0

    # which MCU is the coil wired to: the toolhead board when there is one
    mcus = [n.split(None, 1)[1] for n, _ in all_secs if n.startswith('mcu ')]
    mcus = [m for m in mcus if m.lower() not in HOST_MCU]
    mcu = os.environ.get('MCU')
    if not mcu:
        if len(mcus) == 1:
            mcu = mcus[0]
        elif len(mcus) > 1:
            mcu = ask("Which board is the coil wired to?", [(m, "[mcu %s]" % m) for m in mcus] + [('mcu', "the main board [mcu]")])
        else:
            mcu = ask("No toolhead board found in the config. Where is the coil wired?",
                      [('mcu', "the main board [mcu]"), ('other', "a board I will name (as in its [mcu ...] section)")])
            if mcu == 'other':
                mcu = input("[mcu name]: ").strip()
            elif mcu is None:
                mcu = 'mcu'
                say("No toolhead board in the config: i2c_mcu: mcu (the main board). Edit it if the coil is elsewhere.")
        if mcu is None:
            say("Several boards found (%s). Run again with MCU=<name> BOARD=<ebb|gen2|bus> ./install.sh" % ", ".join(mcus))
            return 1

    # the I2C bus depends on the board
    board = os.environ.get('BOARD')
    if not board:
        board = ask("Which board is it? (decides the I2C bus name)",
                    [(k, label) for k, label, _ in BOARDS] + [('other', "another board (type the bus name next)")])
        if board is None:
            say("Run again with BOARD=ebb, BOARD=gen2 or BOARD=<i2c bus name> (guide step 2.5), e.g.\n"
                "  BOARD=ebb ./install.sh")
            return 1
        if board == 'other':
            board = input("i2c_bus name from the guide (e.g. i2c1_PB8_PB9): ").strip()
    bus = dict((k, b) for k, _, b in BOARDS).get(board.lower(), board)
    if not re.match(r'^i2c\w+$', bus):
        say("'%s' does not look like an I2C bus name - see guide step 2.5" % bus)
        return 1

    bak = backup(main_cfg)
    text = open(main_cfg, errors='replace').read()
    head, sep, tail = text.partition('#*# <---------------------- SAVE_CONFIG')
    block = SECTION % dict(mcu=mcu, bus=bus)
    text = head.rstrip('\n') + '\n' + block + ('\n' + sep + tail if sep else '\n')
    open(main_cfg, 'w').write(text)
    say("Added [oznlab_sensor hotend] to printer.cfg (i2c_mcu: %s, i2c_bus: %s). Backup: %s"
        % (mcu, bus, os.path.basename(bak)))
    say(fix_position_min(cfg_files(main_cfg)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
