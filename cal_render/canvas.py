from __future__ import annotations
from PIL import Image
import numpy as np
import unicodedata

from typing import Optional, Tuple, List
from abc import ABC, abstractmethod
from enum import Enum
from tqdm import tqdm

from ultlf import UltlfCP

from data import EventLayout, Rectangle, Color, Event

CANVAS_WIDTH = 480
CANVAS_HEIGHT = 800

class Canvas(ABC):
    @abstractmethod
    def __call__(self, x: int, y: int) -> Color:
        pass

    def preview(self):
        img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT))
        for i in tqdm(range(CANVAS_HEIGHT * CANVAS_WIDTH), unit="px", unit_scale=True):
            y = i // CANVAS_WIDTH
            x = i % CANVAS_WIDTH
            img.putpixel((x, y), self(x, y).rgb())

        img.show()

class Background(Canvas):
    def __init__(self, color: Color):
        self.color = color

    def __call__(self, x: int, y: int) -> Color:
        return self.color



class DitheredRectangle(Canvas):
    def __init__(
        self,
        inner: Canvas,
        *,
        color: Color,
        color2: Optional[Color] = None,
        fill: Optional[Color] = None,
        rect: Rectangle,
        skip_top: bool = False,
        skip_bottom: bool = False,
        dither_inside_density=0, # 0 = no dithering inside
    ):
        self.inner = inner

        self.color1 = color
        self.color2 = color2
        self.fill = fill
        self.rect = rect
        self.skip_top = skip_top
        self.skip_bottom = skip_bottom
        self.dither_inside_density = dither_inside_density

    def __call__(self, x: int, y: int) -> Color:
        if (x, y) not in self.rect:
            return self.inner(x, y)

        def inside():
            if self.dither_inside_density != 0:
                dx, dy = x - self.rect.x0, y - self.rect.y0
                res = (dx + 2 * dy) % self.dither_inside_density
                if res == 0:
                    return self.color1
                # elif res == 2:
                #     return self.color2

            if self.fill is None:
                return self.inner(x, y)
            else:
                return self.fill

        color = self.color1 if (x + y) % 2 == 0 else (self.color2 if self.color2 is not None else inside())

        dy = 1000
        if not self.skip_top:
            dy = min(dy, y - self.rect.y0)
        if not self.skip_bottom:
            dy = min(dy, self.rect.y1-1 - y)

        dx = min(x - self.rect.x0, self.rect.x1-1 - x)

        if dx <= 1:
            return color

        if dy <= 1:
            return color

        checker = (x + y) % 4 > 1
        if checker:
            return inside()

        if dx == 2:
            return color

        if dy == 2:
            return color

        return inside()

LETTER_SPACING = 1

# gives a list of indices where it's "okay" to put a line break in text
def text_breakpoint_indices(text: str) -> List[int]:
    indices = []
    for ch_idx, (ch, next) in enumerate(zip(text[:-1], text[1:])):
        i = ch_idx+1
        ch_cat = unicodedata.category(ch)
        next_cat = unicodedata.category(next)

        # stupid stupid stupid
        if ch_cat[0] != next_cat[0]:
            indices.append(i)

    indices.reverse()
    return indices

class Text(Canvas):
    def __init__(
        self,
        inner: Canvas,
        text: str,
        color: Color,
        *,
        scale: int = 1,
        x0: int,
        y0: int,
        align_right: bool = False,
    ):
        self.inner = inner
        self.chars: List[UltlfCP] = [UltlfCP.from_ch(ch) for ch in text]
        self.total_width = sum(ch.width for ch in self.chars) + LETTER_SPACING * (len(self.chars) - 1)
        self.text = text

        self.color = color
        self.scale = scale
        self.x0 = x0
        self.y0 = y0
        self.align_right = align_right

    # cuts of text such that it is less pixels wide than width
    # tries to cut at a word boundary
    # if ellipsis is set, we add '...' if the text is broken
    def fit_width(self, width: int, ellipsis: bool) -> Optional[str]:
        width //= self.scale

        prefix_widths = [] # index i is total width of self.chars[:i+1]
        at = -LETTER_SPACING
        for ch in self.chars:
            at += ch.width + LETTER_SPACING
            prefix_widths.append(at)

        if prefix_widths[-1] < width:
            # don't need to cut anything
            return None

        ellipsis_width = 0
        if ellipsis:
            period = UltlfCP.from_ch('.')
            ellipsis_width = (period.width + LETTER_SPACING) * 3

        for i in text_breakpoint_indices(self.text):
            if prefix_widths[i-1] + ellipsis_width < width:
                # we can fit up to and including index i
                self.chars = self.chars[:i]
                remaining = self.text[i:]
                if ellipsis:
                    for i in range(3):
                        self.chars.append(UltlfCP.from_ch('.'))
                self.total_width = sum(ch.width for ch in self.chars) + LETTER_SPACING * (len(self.chars) - 1)
                return remaining
        self.chars = []
        return self.text

    def __call__(self, x, y):
        xr = (x - self.x0) // self.scale
        yr = (y - self.y0) // self.scale
        if self.align_right:
            xr += self.total_width
        yr -= 6 # baseline adjust

        if xr < 0:
            return self.inner(x, y)

        for ch in self.chars:
            if xr >= ch.width + LETTER_SPACING:
                xr -= ch.width + LETTER_SPACING
                continue
            if xr >= ch.width:
                break
            yr += ch.baseline_y

            if yr < 0 or yr >= len(ch.bitmap):
                break

            if ch.bitmap[yr][xr]:
                return self.color
            else:
                return self.inner(x, y)

        return self.inner(x, y)

class CalendarEvent(Canvas):
    @staticmethod
    def from_event(
        inner: Canvas,
        event: Event,
        layout: EventLayout,
    ) -> CalendarEvent:
        return CalendarEvent(
            inner,
            rect=layout.rect,
            title=event.title,
            color1=event.color1,
            color2=event.color2,
            time_start=layout.start_time,
            time_end=layout.end_time,
        )

    def __init__(
        self,
        inner: Canvas,
        rect: Rectangle,
        *,
        title: str,
        color1: Color,
        color2: Color,
        time_start: Optional[str], # None = no top, no title
        time_end: Optional[str], # None = no bottom
    ):
        assert(rect.height >= 33) # minimum pixel size
        self.inner = inner
        self.color1 = color1
        self.color2 = color2

        self.title = title
        self.rect = rect
        self.time_start = time_start
        self.time_end = time_end

        self.canvas: Canvas = inner

        # add rectangle
        self.canvas = DitheredRectangle(
            self.canvas,
            color=color1,
            color2=color2,
            fill=Color.WHITE,
            rect=rect,
            skip_top=time_start is None,
            skip_bottom=time_end is None,
            dither_inside_density=7,
        )
        self.inner_rect = rect.shrink(3) # at least Nx27

        if time_start is not None:
            # add title
            title_canvas = Text(
                self.canvas,
                text=title,
                scale=2,
                x0=self.inner_rect.x0,
                y0=self.inner_rect.y0,
                color=Color.BLACK,
            )

            time_width_px = 24 if self.time_start is not None or self.time_end is not None else 0

            remaining_width = self.inner_rect.width - time_width_px
            # TODO: This should maybe try only to break between words
            remaining_text = title_canvas.fit_width(remaining_width, ellipsis=False)
            if remaining_text is None:
                self.canvas = title_canvas
            else:
                subtitle = Text(
                    title_canvas,
                    text=remaining_text,
                    scale=1,
                    x0=self.inner_rect.x0,
                    y0=self.inner_rect.y0 + 18, # scale*2 gives 18 pixel of title
                    color=Color.BLACK,
                )
                subtitle.fit_width(remaining_width, ellipsis=True)
                self.canvas = subtitle

        # draw times
        if self.time_start is not None:
            self.canvas = Text(
                self.canvas,
                text=self.time_start,
                scale=1,
                x0=self.inner_rect.x1,
                y0=self.inner_rect.y0,
                color=Color.BLACK,
                align_right=True,
            )
        if self.time_end is not None:
            self.canvas = Text(
                self.canvas,
                text=self.time_end,
                scale=1,
                x0=self.inner_rect.x1,
                y0=self.inner_rect.y1-7,
                color=Color.BLACK,
                align_right=True,
            )

    def __call__(self, x, y):
        if (x, y) in self.rect: # cut off anything outside the box
            return self.canvas(x, y)
        else:
            return self.inner(x, y)


if __name__ == "__main__":
    canvas: Canvas = Background(Color.WHITE)

    for i in range(6):
        canvas = CalendarEvent(
            canvas,
            Rectangle(x0=100, y0=100+40*i, width=100+30*i, height=33),
            title="Vattna lila blomma och murgröna",
            color1=Color.BLUE,
            color2=Color.BLUE,
            time_start="10:00",
            time_end="11:00",
        )

    canvas.preview()
