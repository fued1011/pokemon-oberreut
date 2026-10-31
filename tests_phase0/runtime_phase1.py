#!/usr/bin/env python3
"""Real mGBA Phase 1.1 transition, collision, fresh-process flash save/load.

Uses temporary cartridge saves only. No existing desktop emulator save is touched.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mgba.gba import GBA
from runtime_mgba import ROOT, open_game, frames, press, location

EAST = 58  # generated map_groups.h: TownsAndRoutes OberreutOst (verify below)


def continue_game(gba):
    frames(gba, 650)
    # The west-map framebuffer sentinel differs from the eastern tileset view.
    # Advance the title/Continue prompts, then prove overworld by movement.
    for _ in range(15):
        press(gba, 'A', 55)
    frames(gba, 250)


def travel(save, evidence):
    gba, framebuffer = open_game(save)
    frames(gba, 400)
    press(gba, 'START', 90)
    for _ in range(250):
        press(gba, 'A')
        if location(gba) == [0, 57, 30, 28]:
            break
    else:
        raise AssertionError('New Game did not reach Oberreut')
    frames(gba, 900)
    assert location(gba) == [0, 57, 30, 28], location(gba)
    # X=59 is the last reachable square before a building at y=28.
    gba.set_keys(GBA.KEY_RIGHT)
    for _ in range(700):
        gba.run_frame()
        if location(gba) == [0, 57, 59, 28]:
            break
    gba.set_keys()
    frames(gba, 25)
    assert location(gba) == [0, 57, 59, 28], location(gba)
    gba.set_keys(GBA.KEY_UP)
    for _ in range(60):
        gba.run_frame()
        if location(gba) == [0, 57, 59, 27]:
            break
    gba.set_keys()
    frames(gba, 20)
    assert location(gba) == [0, 57, 59, 27], location(gba)
    gba.set_keys(GBA.KEY_RIGHT)
    for _ in range(240):
        gba.run_frame()
        if location(gba) and location(gba)[:2] == [0, EAST]:
            break
    gba.set_keys()
    frames(gba, 100)
    at_east = location(gba)
    assert at_east[:2] == [0, EAST], at_east
    assert at_east[3] == 27, at_east
    # Outer eastern perimeter is solid, but the reciprocal west seam is open.
    framebuffer.to_pil().convert('RGB').save(evidence)
    press(gba, 'START', 60)
    press(gba, 'DOWN', 12)
    press(gba, 'DOWN', 12)
    press(gba, 'A', 90)
    press(gba, 'A', 80)
    press(gba, 'A', 80)
    frames(gba, 305)  # first-save flash write; exit before binding crash
    framebuffer.to_pil().convert('RGB').save(ROOT / 'logs/phase1-save-final.png')
    assert save.stat().st_size >= 131072
    print(json.dumps({'transition': at_east, 'evidence': str(evidence), 'save_bytes': save.stat().st_size}), flush=True)


def reload_east(save):
    gba, framebuffer = open_game(save)
    frames(gba, 650)
    saved = location(gba)
    assert saved[:2] == [0, EAST], saved
    continue_game(gba)
    initial = location(gba)
    gba.set_keys(GBA.KEY_LEFT)
    frames(gba, 45)
    gba.set_keys()
    frames(gba, 60)
    moved = location(gba)
    assert moved != initial and moved[:2] in ([0, EAST], [0, 57]), (initial, moved)
    print(json.dumps({'fresh_continue': saved, 'after_left': moved}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 4:
        save = Path(sys.argv[2])
        if sys.argv[1] == 'travel':
            travel(save, Path(sys.argv[3]))
        else:
            reload_east(save)
    else:
        evidence = ROOT / 'logs/phase1-mgba-east.png'
        with tempfile.TemporaryDirectory(prefix='oberreut-phase1-isolated-') as temp:
            save = Path(temp) / 'phase1.sav'
            for phase in ('travel', 'reload'):
                subprocess.run([sys.executable, __file__, phase, str(save), str(evidence)], check=True)
