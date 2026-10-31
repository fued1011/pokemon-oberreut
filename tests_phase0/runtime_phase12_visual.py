#!/usr/bin/env python3
"""Capture *unaltered* mGBA frames at fixed local RTC hours (night/day).

Usage: MGBA_PYTHON=...; "$MGBA_PYTHON" tests_phase0/runtime_phase12_visual.py 1
       "$MGBA_PYTHON" tests_phase0/runtime_phase12_visual.py 12
An isolated cartridge save is created for each invocation; the ROM is unchanged.
"""
import datetime
import json
import sys
import tempfile
from pathlib import Path

from mgba._pylib import lib
from mgba.gba import GBA

from runtime_mgba import ROOT, frames, location, open_game, press


def capture(hour):
    if hour not in (1, 12):
        raise ValueError('Only the stable night (1) and day (12) checkpoints are supported')
    with tempfile.TemporaryDirectory(prefix='phase12-visual-') as folder:
        gba, framebuffer = open_game(Path(folder) / 'isolated.sav')
        # This is the emulator's RTC, not a ROM patch, image filter, or save edit.
        gba._core.rtc.override = lib.RTC_FIXED
        # mGBA's RTC_FIXED value is milliseconds, not Unix seconds.
        gba._core.rtc.value = int(datetime.datetime(2026, 10, 31, hour).astimezone().timestamp() * 1000)
        gba.reset()
        frames(gba, 400)
        press(gba, 'START', 90)
        for _ in range(250):
            press(gba, 'A')
            if location(gba) == [0, 57, 30, 28]:
                break
        else:
            raise AssertionError('New Game did not reach the map')
        frames(gba, 900)
        gba.set_keys(GBA.KEY_UP)
        frames(gba, 350)
        gba.set_keys()
        frames(gba, 30)
        assert location(gba) == [0, 57, 30, 17], location(gba)
        label = 'night' if hour == 1 else 'day'
        picture = ROOT / f'logs/phase12c-building-{label}.png'
        framebuffer.to_pil().convert('RGB').save(picture)
        print(json.dumps({'hour_local': hour, 'rtc_fixed': True,
                          'location': location(gba), 'framebuffer': str(picture)}))
        if hour == 12:
            # Walk around the western end of the old mask for a view of rows
            # 10-11. The frontal view at (30,17) crops these rows off-screen.
            gba.set_keys(GBA.KEY_LEFT)
            frames(gba, 175)
            gba.set_keys()
            frames(gba, 20)
            assert location(gba) == [0, 57, 19, 17], location(gba)
            gba.set_keys(GBA.KEY_UP)
            frames(gba, 48)
            gba.set_keys()
            frames(gba, 20)
            assert location(gba) == [0, 57, 19, 14], location(gba)
            roof = ROOT / 'logs/phase12c-roof-day.png'
            framebuffer.to_pil().convert('RGB').save(roof)
            print(json.dumps({'roof_location': location(gba),
                              'framebuffer': str(roof)}))


if __name__ == '__main__':
    capture(int(sys.argv[1]))
