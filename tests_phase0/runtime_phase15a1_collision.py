#!/usr/bin/env python3
"""Use real controls to verify one tree trunk and the north facade."""
import datetime
import json
import tempfile
from pathlib import Path

from mgba._pylib import lib
from mgba.gba import GBA
from runtime_mgba import ROOT, frames, location, open_game, press
from runtime_slice_visual import route


def walk(gba, goal):
    for point, key in route(tuple(location(gba)[2:]), goal):
        gba.set_keys(getattr(GBA, "KEY_" + key))
        for _ in range(80):
            gba.run_frame()
            if tuple(location(gba)[2:]) == point:
                break
        else:
            raise AssertionError((point, location(gba)))
        gba.set_keys()
        frames(gba, 10)


def blocked(gba, key):
    before = location(gba)
    gba.set_keys(getattr(GBA, "KEY_" + key))
    frames(gba, 30)
    gba.set_keys()
    frames(gba, 10)
    assert location(gba) == before, (key, before, location(gba))


def main():
    with tempfile.TemporaryDirectory(prefix="oberreut-phase15a1-") as folder:
        gba, _ = open_game(Path(folder) / "isolated.sav")
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
        walk(gba, (28, 21))
        blocked(gba, "UP")  # tree trunk at 28,20
        walk(gba, (30, 17))
        blocked(gba, "UP")  # facade at 30,16
        print(json.dumps({"tree_test": [28, 20], "facade_test": [30, 16],
                          "final_location": location(gba), "result": "blocked"}), flush=True)


if __name__ == "__main__":
    main()
