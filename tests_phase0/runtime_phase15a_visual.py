#!/usr/bin/env python3
"""Capture the Phase 1.5a north facade at the fixed comparison camera."""
import datetime
import json
import tempfile
from pathlib import Path

from mgba._pylib import lib
from mgba.gba import GBA
from runtime_mgba import ROOT, frames, location, open_game, press
from runtime_slice_visual import route


def main():
    with tempfile.TemporaryDirectory(prefix="oberreut-phase15a-") as folder:
        gba, framebuffer = open_game(Path(folder) / "isolated.sav")
        gba._core.rtc.override = lib.RTC_FIXED
        gba._core.rtc.value = int(datetime.datetime(2026, 10, 31, 12).astimezone().timestamp() * 1000)
        gba.reset()
        frames(gba, 400)
        press(gba, "START", 90)
        for _ in range(250):
            press(gba, "A")
            if location(gba) == [0, 57, 30, 28]:
                break
        else:
            raise AssertionError("New Game did not reach Oberreut")
        frames(gba, 900)
        goal = (30, 17)
        for point, key in route(tuple(location(gba)[2:]), goal):
            gba.set_keys(getattr(GBA, "KEY_" + key))
            for _ in range(80):
                gba.run_frame()
                if tuple(location(gba)[2:]) == point:
                    break
            else:
                raise AssertionError((point, location(gba)))
            gba.set_keys()
            frames(gba, 20)
        frames(gba, 60)
        output = ROOT / "logs/phase15a-facade-after.png"
        framebuffer.to_pil().convert("RGB").save(output)
        print(json.dumps({"camera": "facade", "location": location(gba),
                          "rtc": "2026-10-31T12:00:00+01:00",
                          "framebuffer": str(output)}), flush=True)


if __name__ == "__main__":
    main()
