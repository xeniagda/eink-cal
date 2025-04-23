from __future__ import annotations
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from data import Event, Rectangle, Color
from canvas import Canvas, CalendarEvent, Text, Background

weekday_names = ["Må", "Ti", "On", "To", "Fr", "Lö", "Sö"]

@dataclass
class TimeRange:
    start: datetime
    end: datetime

    # rounds start and end to the nearest hours
    @staticmethod
    def round_to_hour(start: datetime, end: datetime) -> TimeRange:
        start = start.replace(minute=0, second=0, microsecond=0)
        end = (end + timedelta(seconds=3600 - 1)).replace(minute=0, second=0, microsecond=0) # should round up ?
        return TimeRange(start=start, end=end)

    def labels(self) -> Tuple[str, str]:
        sday = self.start.weekday()
        eday = self.end.weekday()
        return (
            weekday_names[sday] + " " + self.start.strftime("%H:%M"),
            weekday_names[eday] + " " + self.end.strftime("%H:%M"),
        )

    def __contains__(self, t: datetime) -> bool:
        return t >= self.start and t <= self.end

def test_timerange():
    t = TimeRange.round_to_hour(datetime(2025, 1, 1, 13, 33, 37), datetime(2025, 1, 1, 13, 33, 38))
    assert t.start == datetime(2025, 1, 1, 13, 0, 0)
    assert t.end == datetime(2025, 1, 1, 14, 0, 0)

    t = TimeRange.round_to_hour(datetime(2025, 1, 1, 13, 0, 0), datetime(2025, 1, 1, 14, 0, 0))
    assert t.start == datetime(2025, 1, 1, 13, 0, 0)
    assert t.end == datetime(2025, 1, 1, 14, 0, 0)

    t = TimeRange.round_to_hour(datetime(2025, 1, 1, 13, 0, 0), datetime(2025, 1, 1, 14, 0, 1))
    assert t.start == datetime(2025, 1, 1, 13, 0, 0)
    assert t.end == datetime(2025, 1, 1, 15, 0, 0)

# gives hour-aligned ranges
def time_ranges(
    events: List[Event],
    coalesce: timedelta = timedelta(hours=1), # how long between two ranges for them to combine
    inactive: timedelta = timedelta(hours=1), # how long with no activity for range to break
) -> List[TimeRange]:
    if len(events) == 0:
        return []

    # should be non-overlapping
    ranges: List[TimeRange] = []

    def does_overlap(r1: TimeRange, r2: TimeRange) -> bool:
        return r1.start <= r2.end + coalesce and r2.start <= r1.end + coalesce

    for event in events:
        if event.end - event.start < 2 * inactive:
            ranges.append(TimeRange.round_to_hour(event.start, event.end))
        else:
            ranges.append(TimeRange.round_to_hour(event.start, event.start + inactive))
            ranges.append(TimeRange.round_to_hour(event.end - inactive, event.end))

    ranges.sort(key=lambda x: x.start)

    # coalesce ranges
    coalesced = []
    current = ranges[0]
    for r in ranges[1:]:
        if does_overlap(current, r):
            current.end = r.end
        else:
            coalesced.append(current)
            current = r

    return coalesced + [current]

def test_timeranges():
    import random
    e = lambda dhm0, dhm1: Event(title="mjau", start=datetime(2025, 1, *dhm0, 0), end=datetime(2025, 1, *dhm1, 0), color1=Color.RED, color2=Color.RED)

    ts = [
        # these should generate one range each
        e((20, 0, 0), (20, 1, 0)),
        e((20, 3, 0), (20, 4, 0)),

        # these should be merged
        e((20, 8, 0), (20, 9, 0)),
        e((20, 10, 0), (20, 11, 0)),

        # this should go from 15:00-17:00
        e((20, 15, 59), (20, 16, 1)),

        # these should overlap from 22-00
        e((20, 22, 1), (20, 22, 2)),
        e((20, 23, 1), (20, 23, 2)),

        # this should be split into 2-3 and 7-8
        e((21, 2, 0), (21, 8, 0)),

        # should be 10-11, 13-14, 17-18
        e((21, 10, 0), (21, 18, 0)),
        e((21, 13, 0), (21, 14, 0)),
    ]
    for i in range(20):
        random.shuffle(ts)
        assert [(x.start.hour, x.end.hour) for x in time_ranges(ts)] == [
            (0, 1), (3, 4), # first two
            (8, 11), # three merged
            (15, 17), # expanded
            (22, 00), # expanded+overlapped
            (2, 3), (7, 8), # split
            (10, 11), (13, 14), (17, 18), # split+middle
        ]


@dataclass
class LayoutedEvent:
    event: Event
    start_ratio: float # 0 = all the way to the left
    end_ratio: float # 1 = all the way to the right

def layout_events(events: List[Event], sort_by_length: bool = True) -> List[LayoutedEvent]:
    if sort_by_length:
        events.sort(key=lambda e: e.end - e.start, reverse=True)

    layouted = [
        LayoutedEvent(event=e, start_ratio=0, end_ratio=0) for e in events
    ]
    n_later_overlaps = [0 for _ in events]
    for i in range(len(events) - 1, -1, -1):
        e = events[i]
        n_overlaps = 0
        for j in range(i+1, len(events)):
            e2 = events[j]
            if e.overlaps_with(e2):
                n_overlaps = max(n_overlaps, 1 + n_later_overlaps[j])
        n_later_overlaps[i] = n_overlaps

    for i, (layout, overlaps) in enumerate(zip(layouted, n_later_overlaps)):
        remaining = 1 - layout.start_ratio
        size = remaining / (1 + overlaps)
        layout.end_ratio = layout.start_ratio + size
        for l in layouted[i+1:]:
            if layout.event.overlaps_with(l.event):
                l.start_ratio = layout.end_ratio

    return layouted

def test_layout():
    e = lambda dhm0, dhm1: Event(title="mjau", start=datetime(2025, 1, *dhm0, 0), end=datetime(2025, 1, *dhm1, 0), color1=Color.RED, color2=Color.RED)

    es = [
        # these don't overlap, 0-1 each
        e((20, 9, 0), (20, 10, 0)),
        e((20, 11, 0), (20, 12, 0)),

        # these overlap, 0-1/4, 1/4-1/2, 1/2-3/4, 3/4-1
        e((20, 15, 0), (20, 16, 30)),
        e((20, 16, 0), (20, 17, 30)),
        e((20, 17, 0), (20, 18, 30)),
        e((20, 18, 0), (20, 19, 30)),

        # these overlap 0-1/2, 1/2-1, 1/2-1
        e((20, 20, 00), (20, 22, 0)),
        e((20, 20, 00), (20, 21, 0)),
        e((20, 21, 00), (20, 22, 0)),
    ]

    assert [(l.start_ratio, l.end_ratio) for l in layout_events(es, sort_by_length=False)] == [
        (0, 1), (0, 1), # first two
        (0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1), # second four
        (0, 0.5), (0.5, 1), (0.5, 1), # last three
    ]

class TimeTick(Canvas):
    def __init__(
        self,
        background: Canvas,
        at_x0: int,
        at_x1: int,
        at_y: int,
        label: str,
        dark_mode: bool
    ):
        self.at_x0 = at_x0
        self.at_x1 = at_x1
        self.at_y = at_y
        self.canvas = background
        self.text = Text(self.canvas, label, Color.WHITE if dark_mode else Color.BLACK, scale=2, x0 = at_x0-5, y0=at_y-3, align_right=True)
        self.dark_mode = dark_mode

    def __call__(self, x: int, y: int) -> Color:
        if -5 < x - self.at_x0 < 0 and -1 <= y - self.at_y <= 1:
            return Color.WHITE if self.dark_mode else Color.BLACK
        return self.text(x, y)

class TimeBreak(Canvas):
    def __init__(
        self,
        background: Canvas,
        rect: Rectangle,
        dark_mode: bool
    ):
        self.background = background
        self.rect = rect
        self.dark_mode = dark_mode

    def __call__(self, x: int, y: int) -> Color:
        if (x, y) not in self.rect:
            return self.background(x, y)

        dx = min(x - self.rect.x0, (self.rect.x1-1) - x)
        dy = min(y - self.rect.y0, (self.rect.y1-1) - y)

        if dy < 4:
            if ((x + y) % 5 < 2) ^ self.dark_mode:
                return Color.BLACK
            else:
                return Color.WHITE

        return self.background(x, y)


class CalendarCanvas(Canvas):
    def __init__(
        self,
        *,
        bounding_rect: Rectangle,
        events: List[Event],

        background: Optional[Canvas] = None,
        dark_mode: bool = False,
        pixels_per_hour: int = 50,
        pixels_per_break: int = 30,
    ):
        bounding_rect.x0 += 80 # offset for tick marks
        bounding_rect.y0 += 6 # offset for tick marks
        bounding_rect.x1 -= 6 # equal spacing on other edge

        if background is not None:
            self.canvas: Canvas = background
        else:
            self.canvas = Background(Color.BLACK if dark_mode else Color.WHITE)

        self.time_ranges = time_ranges(events)
        time_range_pixel_intervals: List[Tuple[int, int]] = []
        y = bounding_rect.y0
        is_first = True
        for t in self.time_ranges:
            height = int(pixels_per_hour * (t.end - t.start).seconds / 3600)
            l1, l2 = t.labels()
            print(t, height, l1, l2, y, y+height)
            if not is_first:
                self.canvas = TimeBreak(self.canvas, Rectangle(x0=bounding_rect.x0, x1=bounding_rect.x1, y0=y-pixels_per_break, y1=y), dark_mode=dark_mode)
            self.canvas = TimeTick(self.canvas, bounding_rect.x0, bounding_rect.x1, y, l1, dark_mode=dark_mode)
            self.canvas = TimeTick(self.canvas, bounding_rect.x0, bounding_rect.x1, y + height, l2, dark_mode=dark_mode)
            time_range_pixel_intervals.append((y, y + height))
            y += height + pixels_per_break
            is_first = False

        layouted = layout_events(events)

        for l in layouted:
            e = l.event
            for rng, (rp0, rp1) in zip(self.time_ranges, time_range_pixel_intervals):
                r0 = (e.start - rng.start) / (rng.end - rng.start)
                r1 = (e.end - rng.start) / (rng.end - rng.start)

                if r0 <= 1 and r1 >= 0:
                    # within this range
                    y0 = max(0, r0) * (rp1 - rp0) + rp0
                    y1 = min(1, r1) * (rp1 - rp0) + rp0
                    if y1 - y0 < 33:
                        y1 = y0 + 33 # force size
                    x0 = l.start_ratio * (bounding_rect.x1 - bounding_rect.x0) + bounding_rect.x0
                    x1 = l.end_ratio * (bounding_rect.x1 - bounding_rect.x0) + bounding_rect.x0
                    self.canvas = CalendarEvent(
                        self.canvas,
                        Rectangle(x0=round(x0), x1=round(x1), y0=round(y0), y1=round(y1)),
                        title=e.title,
                        color1=e.color1,
                        color2=e.color2,
                        time_start=e.start.strftime("%H:%M") if r0 >= 0 else None,
                        time_end=e.end.strftime("%H:%M") if r1 <= 1 else None,
                    )


    def __call__(self, x, y):
        return self.canvas(x, y)


if __name__ == "__main__":
    test_timeranges()
    test_timerange()
    test_layout()


    e = lambda t, dhm0, dhm1: Event(title=t, start=datetime(2025, 1, *dhm0, 0), end=datetime(2025, 1, *dhm1, 0), color1=Color.RED, color2=Color.RED)

    es = [
        e("a", (20, 5, 0), (20, 12, 0)),
        e("b", (20, 9, 0), (20, 10, 0)),

        e("c", (20, 15, 0), (20, 16, 30)),
        e("d", (20, 16, 0), (20, 17, 30)),
        e("e", (20, 17, 0), (20, 18, 30)),
        e("f", (20, 18, 0), (20, 19, 30)),

        e("g", (20, 21, 00), (20, 23, 0)),
        e("h", (20, 21, 00), (20, 22, 0)),
        e("i", (20, 22, 00), (20, 23, 0)),
    ]
    b = Background(Color.WHITE)

    c = CalendarCanvas(b, Rectangle(x0=60, y0=40, x1=440, y1=740), es)
    c.preview()
