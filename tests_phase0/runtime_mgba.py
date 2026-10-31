#!/usr/bin/env python3
"""Optional real-ROM mGBA acceptance: new game, movement, flash save, Continue.

Run with a Python environment containing the official mGBA CFFI bindings and
libmgba (see PHASE0-REPORT.md). Uses only an isolated temporary .sav, never
modifies a user's emulator save. The Python unit tests do not require mGBA.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from mgba import core, image, log, vfs
from mgba.gba import GBA

log.silence()
ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "pokeemerald.gba"
match = re.search(r"^\s*(0x[0-9a-fA-F]+)\s+gSaveBlock1Ptr$",
                  (ROOT / "pokeemerald.map").read_text(), re.MULTILINE)
if not match:
    raise RuntimeError("Build ROM and pokeemerald.map before the mGBA test")
SAVE_PTR = int(match.group(1), 16)


def open_game(save):
    (ROOT / "logs").mkdir(exist_ok=True)
    gba = core.load_path(str(ROM))
    if gba is None:
        raise RuntimeError(f"Cannot load {ROM}")
    save.touch(exist_ok=True)
    # mGBA 0.10.x vfs.open_path('w+') combines incompatible access flags.
    if not gba.load_save(vfs.open_path(str(save), "r+")):
        raise RuntimeError("Cannot attach isolated cartridge flash")
    framebuffer = image.Image(*gba.desired_video_dimensions())
    gba.set_video_buffer(framebuffer)
    gba.reset()
    return gba, framebuffer


def frames(gba, count):
    for _ in range(count):
        gba.run_frame()


def press(gba, button, wait=45):
    gba.set_keys(getattr(GBA, "KEY_" + button))
    frames(gba, 2)
    gba.set_keys()
    frames(gba, wait)


def location(gba):
    mem = gba.memory
    ptr = mem.u16[SAVE_PTR] | (mem.u16[SAVE_PTR + 2] << 16)
    if not 0x02000000 <= ptr < 0x02040000:
        return None
    return [mem.u8[ptr + 4], mem.u8[ptr + 5], mem.u16[ptr], mem.u16[ptr + 2]]


def create_save(save):
        gba, framebuffer = open_game(save)
        frames(gba, 400)
        press(gba, "START", 90)
        for _ in range(250):
            press(gba, "A")
            if location(gba) == [0, 57, 30, 28]:
                break
        else:
            raise AssertionError("New Game never reached Oberreut spawn")
        frames(gba, 900)  # wait for intro fade and input unlock
        assert location(gba) == [0, 57, 30, 28]
        framebuffer.to_pil().convert('RGB').save(ROOT/'logs/phase12-west-spawn.png')
        gba.set_keys(GBA.KEY_RIGHT)
        frames(gba, 35)
        gba.set_keys()
        frames(gba, 20)
        assert location(gba) == [0, 57, 32, 28], location(gba)
        framebuffer.to_pil().convert('RGB').save(ROOT/'logs/phase12-west-after-right.png')
        press(gba, "START", 60)
        press(gba, "DOWN", 12)
        press(gba, "DOWN", 12)
        press(gba, "A", 90)  # select SAVE
        press(gba, "A", 80)  # show YES/NO
        press(gba, "A", 80)  # choose YES; flash write begins
        frames(gba, 272)  # flash write; avoid later mGBA 0.10.5 callback crash
        assert save.stat().st_size >= 131072, save.stat().st_size
        print(json.dumps({"new_game": [0, 57, 30, 28], "after_right": [0, 57, 32, 28],
                          "save_bytes": save.stat().st_size}),flush=True)


def check_reload(save):
        # Fresh emulator process reloads cartridge flash, not a savestate.
        reloaded, framebuffer2 = open_game(save)
        frames(reloaded, 650)
        assert location(reloaded) == [0, 57, 32, 28], location(reloaded)
        # Graphics changed in Phase 1.2; no fixed framebuffer colour sentinel.
        # Prove CONTINUE with persisted map coordinates and live movement instead.
        for _ in range(15):
            press(reloaded, "A", 55)
        frames(reloaded, 250)
        assert location(reloaded) == [0, 57, 32, 28], location(reloaded)
        reloaded.set_keys(GBA.KEY_LEFT)
        frames(reloaded, 35)
        reloaded.set_keys()
        frames(reloaded, 60)
        assert location(reloaded)[2] < 32, location(reloaded)
        # From (30,28), the source raster's first blocked cell to the north
        # lies at (30,16); the player must stop on (30,17).
        reloaded.set_keys(GBA.KEY_UP)
        frames(reloaded, 350)
        reloaded.set_keys()
        frames(reloaded, 30)
        assert location(reloaded) == [0, 57, 30, 17], location(reloaded)
        collision_stop = location(reloaded)
        framebuffer2.to_pil().convert('RGB').save(ROOT/'logs/phase12-west-building.png')
        reloaded.set_keys(GBA.KEY_LEFT)
        frames(reloaded, 95)
        reloaded.set_keys()
        frames(reloaded, 25)
        framebuffer2.to_pil().convert('RGB').save(ROOT/'logs/phase12-building-left-end.png')
        reloaded.set_keys(GBA.KEY_RIGHT)
        frames(reloaded, 240)
        reloaded.set_keys()
        frames(reloaded, 25)
        framebuffer2.to_pil().convert('RGB').save(ROOT/'logs/phase12-building-right-end.png')
        reloaded.set_keys(GBA.KEY_DOWN)
        frames(reloaded, 155)
        reloaded.set_keys()
        frames(reloaded, 25)
        framebuffer2.to_pil().convert('RGB').save(ROOT/'logs/phase12-plaza-tram-edge.png')
        reloaded.set_keys(GBA.KEY_UP)
        frames(reloaded, 105)
        reloaded.set_keys()
        frames(reloaded, 25)
        framebuffer2.to_pil().convert('RGB').save(ROOT/'logs/phase12-plaza-north-trees.png')
        print(json.dumps({"extra_camera_location": location(reloaded)}), flush=True)
        print(json.dumps({"continue": [0, 57, 32, 28],
                          "collision_stop": collision_stop, "rom": str(ROM)}),flush=True)


def main():
    if len(sys.argv) == 3:
        save = Path(sys.argv[2])
        if sys.argv[1] == "create":
            return create_save(save)
        if sys.argv[1] == "reload":
            return check_reload(save)
    with tempfile.TemporaryDirectory(prefix="oberreut-gba-save-") as temp:
        save = Path(temp) / "isolated.sav"
        for phase in ("create", "reload"):
            subprocess.run([sys.executable, __file__, phase, str(save)], check=True)


if __name__ == "__main__":
    main()
