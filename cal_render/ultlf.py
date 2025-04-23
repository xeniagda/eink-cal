from __future__ import annotations
from typing import List, Optional
import json
import os

basepath = os.path.dirname(__file__)

baselines = json.load(open(os.path.join(basepath, "ultlf/trimmed_baselines.json")))
codepoints = json.load(open(os.path.join(basepath, "ultlf/codepoints.json")))
data = json.load(open(os.path.join(basepath, "ultlf/data.json")))

codepoint2idx = {}
for i, p in enumerate(codepoints):
    if "X" in data[i][0]:
        # invalid char
        continue
    codepoint2idx[p] = i

class UltlfCP:
    def __init__(
        self,
        baseline: int,
        bitmap: List[List[bool]],
    ):
        self.baseline_y = baseline
        self.width = len(bitmap[0])
        self.bitmap = bitmap

    def draw_to_stdout(self):
        for y in range(len(self.bitmap)):
            for x in range(self.width):
                ch = self.bitmap[y][x] if y < len(self.bitmap) else False
                if ch:
                    print("##", end="")
                elif y == self.baseline_y:
                    print("--", end="")
                else:
                    print("  ", end="")
            print()

    @staticmethod
    def from_ch(ch: str) -> UltlfCP:
        if ord(ch) not in codepoint2idx:
            baseline = 7
            bitmap_ch = [
                "#  ###  #",
                "# #   # #",
                "#     # #",
                "#    #  #",
                "#   #   #",
                "#       #",
                "#   #   #",
            ]
        else:
            i = codepoint2idx[ord(ch)]
            bitmap_ch = data[i]
            bitmap = [[ch == "#" for ch in line] for line in bitmap_ch]
        return UltlfCP(baselines[i], bitmap)
