#!/usr/bin/env python3
"""Capture the two approved Phase 1.4 daytime views using real controls."""
import datetime
import json
import tempfile
from pathlib import Path

from mgba._pylib import lib
from runtime_mgba import ROOT, frames, location, open_game, press
from runtime_slice_visual import route
from mgba.gba import GBA


def main():
    with tempfile.TemporaryDirectory(prefix="oberreut-phase14-") as folder:
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

        for name, goal in (("plaza", (30, 24)), ("stop", (44, 24))):
            for point, key in route(tuple(location(gba)[2:]), goal):
                gba.set_keys(getattr(GBA, "KEY_" + key))
                for _ in range(80):
                    gba.run_frame()
                    if tuple(location(gba)[2:]) == point:
                        break
                else:
                    raise AssertionError((name, point, location(gba)))
                gba.set_keys()
                frames(gba, 20)
            frames(gba, 60)
            output = ROOT / f"logs/phase14-{name}-day.png"
            framebuffer.to_pil().convert("RGB").save(output)
            print(json.dumps({"camera": name, "location": location(gba), "framebuffer": str(output)}), flush=True)


if __name__ == "__main__":
    main()
