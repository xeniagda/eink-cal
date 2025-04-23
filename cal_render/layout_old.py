from datetime import datetime, timedelta, date, time

from typing import List, Tuple
from data import Rectangle, EventLayout, Event, Color

# allocates a rectangle for each event
# all events may not be before day or more than 24 hours after day
def layout(
    events: List[Event],
    day: date,
    width: int,
    height: int,
) -> List[EventLayout]:
    day_start = datetime.combine(day, time.min)
    day_end = day + timedelta(days=1)

    MIN_HEIGHT = 33

    def date_to_pixel(date: datetime) -> int:
        time_into_day = date - day_start
        hours_per_day = 24 # TODO: Handle daylight saving day
        seconds_per_day = hours_per_day * 60 * 60 # handle leap second?
        ratio = time_into_day.total_seconds() / seconds_per_day
        return int(ratio * height)

    layouts: List[EventLayout] = []
    for event in events:
        start_pixel = date_to_pixel(event.start) if event.start > day_start else 0
        end_pixel = date_to_pixel(event.end) if event.end < day_end else height
        end_pixel = max(end_pixel, start_pixel + MIN_HEIGHT)

        layouts.append(EventLayout(
            rect = Rectangle(y0=start_pixel, y1=end_pixel, x0=0, x1=-1), # uninitialized x1
            start_time = event.start.strftime("%H:%M") if event.start > day_start else None,
            end_time = event.end.strftime("%H:%M") if event.end < day_end else None,
        ))


    order = sorted(
        enumerate(events),
        key=lambda x: -x[1].duration(),
    )

    for i, (ri, event) in enumerate(order):
        this_rect = layouts[ri].rect
        # find number of overlapping rects
        # all rects before in order have been placed to the left of this rectangle, so we only need to worry about later rects
        # TODO: We could do this a lot more efficiently. Instead of tracking each pixel we should track intervals
        # and split the intervals whenever needed
        overlap = [0 for i in range(height)]
        for j, _other_event in order[i+1:]:
            other_rect = layouts[j].rect
            for px in range(other_rect.y0, other_rect.y1):
                overlap[px] += 1

        max_overlap = max(overlap[this_rect.y0:this_rect.y1]) + 1 # + 1 to include this rectangle

        remaining_width = width - this_rect.x0
        this_rect.x1 = this_rect.x0 + remaining_width // max_overlap

        for j, _other_event in order[i+1:]:
            other_rect = layouts[j].rect
            if other_rect.y0 >= this_rect.y1 or other_rect.y1 <= this_rect.y0:
                # no overlap
                continue
            other_rect.x0 = max(other_rect.x0, this_rect.x1)

    return layouts


if __name__ == "__main__":
    from canvas import Canvas, Background, CalendarEvent, CANVAS_WIDTH, CANVAS_HEIGHT
    import random

    day = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    def random_dates() -> Tuple[datetime, datetime]:
        duration_s = abs(random.gauss(0, 3600 * 2))
        start_s = random.random() * 86400
        start = day + timedelta(seconds=start_s - duration_s/2)
        end = start + timedelta(seconds=duration_s)
        if start < day:
            start = day
        if end >= day + timedelta(days=1):
            end = day + timedelta(days=1)
        return start, end

    events = []
    for i in range(30):
        start, end = random_dates()
        events.append(Event(f"event #{i}", start=start, end=end, color1=Color.BLUE, color2=Color.BLUE))
    print(events)

    rects = layout(events, day, CANVAS_WIDTH, CANVAS_HEIGHT)
    print(rects)

    canvas: Canvas = Background(Color.WHITE)
    for event, e_layout in zip(events, rects):
        # canvas = DitheredRectangle(canvas, color=event.color1, color2=event.color2, rect = rect)
        print(rect)
        canvas = CalendarEvent.from_event(
            canvas,
            event,
            e_layout,
        )

    canvas.preview()
