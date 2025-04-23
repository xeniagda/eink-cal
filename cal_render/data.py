from __future__ import annotations
from typing import Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

class Color(Enum):
    BLACK = (49, 40, 56)
    WHITE = (174, 173, 168)
    GREEN = (48, 101, 68)
    BLUE = (57, 63, 104)
    RED = (146, 61, 62)
    YELLOW = (173, 160, 73)
    ORANGE = (160, 83, 65)

    INVALID = (255, 0, 255)

    def rgb(self) -> Tuple[int, int, int]:
        return self.value

    def to_screen_color_idx(self) -> int:
        if self == Color.BLACK:
            return 0
        elif self == Color.WHITE:
            return 1
        elif self == Color.GREEN:
            return 2
        elif self == Color.BLUE:
            return 3
        elif self == Color.RED:
            return 4
        elif self == Color.YELLOW:
            return 5
        elif self == Color.ORANGE:
            return 6
        return 7 # should be unreachable

    @staticmethod
    def from_str(name: str) -> Color:
        name = name.upper()
        if name == "BLACK":
            return Color.BLACK
        if name == "WHITE":
            return Color.WHITE
        if name == "GREEN":
            return Color.GREEN
        if name == "BLUE":
            return Color.BLUE
        if name == "RED":
            return Color.RED
        if name == "YELLOW":
            return Color.YELLOW
        if name == "ORANGE":
            return Color.ORANGE
        raise ValueError(f"No such color: {name}")

class Rectangle:
    # contains x0, y0, does not contain x1, y1
    def __init__(
        self,
        *,
        x0: int,
        y0: int,
        x1: Optional[int] = None,
        y1: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        assert(x1 is not None or width is not None)
        assert(y1 is not None or height is not None)
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1 or x0 + width # type: ignore
        self.y1 = y1 or y0 + height # type: ignore

    def __repr__(self):
        return f"Rectangle(xy0=({self.x0}, {self.y0}), xy1=({self.x1}, {self.y1}))"

    __str__ = __repr__

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    def __contains__(self, xy: Tuple[float, float]) -> bool:
        x, y = xy
        return x >= self.x0 and x < self.x1 and y >= self.y0 and y < self.y1

    def shrink(self, by: int) -> Rectangle:
        assert(self.width - 2 * by > 0)
        assert(self.height - 2 * by > 0)

        return Rectangle(x0=self.x0+by, y0=self.y0+by, x1=self.x1-by, y1=self.y1-by)

    def grow(self, by: int) -> Rectangle:
        return self.shrink(-by)

@dataclass
class Event:
    title: str
    start: datetime
    end: datetime

    color1: Color
    color2: Color

    def duration(self) -> timedelta:
        return self.end - self.start

    def overlaps_with(self, other: Event) -> bool:
        return self.start < other.end and other.start < self.end

@dataclass
class EventLayout:
    rect: Rectangle
    start_time: Optional[str]
    end_time: Optional[str]

