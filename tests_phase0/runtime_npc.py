#!/usr/bin/env python3
"""Real-ROM acceptance for the Julius-Leber-Platz resident dialogue."""
import json
import tempfile
from pathlib import Path

import numpy as np
from mgba.gba import GBA

from runtime_mgba import ROOT, frames, location, open_game, press


def main():
    with tempfile.TemporaryDirectory(prefix="oberreut-npc-") as folder:
        gba, framebuffer = open_game(Path(folder) / "isolated.sav")
        frames(gba, 400)
        press(gba, "START", 90)
        for _ in range(250):
            press(gba, "A")
            if location(gba) == [0, 57, 30, 28]:
                break
        else:
            raise AssertionError("New Game did not reach Oberreut")
        frames(gba, 900)

        gba.set_keys(GBA.KEY_RIGHT)
        frames(gba, 100)
        gba.set_keys()
        frames(gba, 30)
        assert location(gba) == [0, 57, 34, 28], location(gba)

        before = np.asarray(framebuffer.to_pil().convert("RGB")).copy()
        press(gba, "A", 180)
        first_page = np.asarray(framebuffer.to_pil().convert("RGB")).copy()
        assert location(gba) == [0, 57, 34, 28], location(gba)
        changed = int(np.count_nonzero(np.any(before[104:] != first_page[104:], axis=2)))
        assert changed > 1000, changed

        press(gba, "A", 180)
        second_page = np.asarray(framebuffer.to_pil().convert("RGB")).copy()
        page_changed = int(np.count_nonzero(np.any(first_page[104:] != second_page[104:], axis=2)))
        assert page_changed > 500, page_changed

        output = ROOT / "logs/npc-resident-dialogue.png"
        framebuffer.to_pil().convert("RGB").save(output)
        print(json.dumps({
            "npc_position": [35, 28],
            "player_position": location(gba),
            "dialogue_pixels_changed": changed,
            "page_pixels_changed": page_changed,
            "framebuffer": str(output),
        }))


if __name__ == "__main__":
    main()
