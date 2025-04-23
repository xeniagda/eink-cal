from __future__ import annotations
from typing import List, Any, Union, Optional
import caldav
import toml
from dataclasses import dataclass
from data import Event, Color
from datetime import datetime, timedelta, date, time
import requests
import icalendar
import re

TE_COURSE = re.compile(r"^(?:Kurskod: (?P<kurskod>[^.]+). Kursnamn: (?P<kursnamn>[^,]+), )+(?P<sak>.*)$")
TE_RUBRIK= re.compile(r"^(?:Rubrik: )(?P<rubrik>.+)$")
def timeedit_parse(summary):
    m = re.match(TE_COURSE, summary)
    if not m:
        m = re.match(TE_RUBRIK, summary)
        return m.group("rubrik")
    kod = m.group("kurskod")
    namn = m.group("kursnamn")
    sak = m.group("sak")
    return f"{kod} — {sak} ({namn})"

@dataclass
class Calendar:
    is_caldav: bool
    timeedit_parse: bool
    username: Optional[str]
    password: Optional[str]
    url: str
    color1: Color
    color2: Color

    @staticmethod
    def from_obj(data: Any) -> Calendar:
        return Calendar(
            is_caldav = data["is_caldav"],
            timeedit_parse = data.get("timeedit_parse", False),
            username = data.get("username"),
            password = data.get("password"),
            url = data["url"],
            color1=Color.from_str(data["color1"]),
            color2=Color.from_str(data["color2"]),
        )

    def load_events(self, day: date, n_days: int) -> List[Event]:
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=n_days)

        def to_datetime(t: Union[datetime, date], start: bool) -> datetime:
            if isinstance(t, datetime):
                return t.replace(tzinfo=None)
            else:
                return datetime.combine(t, time.min)

        if self.is_caldav:
            with caldav.DAVClient(url=self.url, username=self.username, password=self.password) as client:
                conn = client.principal()
                calendar = conn.calendar()
                caldav_events = calendar.search(start=day_start, end=day_end, event=True, expand=True)
                events = []
                for caldav_event in caldav_events:
                    vevent = caldav_event.vobject_instance.vevent
                    title = vevent.summary.value

                    start: datetime = to_datetime(vevent.dtstart.value, start=True)
                    end: datetime = to_datetime(vevent.dtend.value, start=False)

                    if start >= day_end or end <= day_start:
                        # event is out of range
                        continue

                    events.append(Event(title=title, start=start, end=end, color1=self.color1, color2=self.color2))

                return events
        else:
            data = requests.get(self.url).text
            ical = icalendar.Calendar.from_ical(data)
            events = []

            for vevent in ical.walk("VEVENT"):
                title = vevent.get("SUMMARY")
                if self.timeedit_parse:
                    title = timeedit_parse(title)

                start = to_datetime(vevent.get("DTSTART").dt, start=True)
                end = to_datetime(vevent.get("DTEND").dt, start=False)
                if end == start and start.time() == time.min:
                    end += timedelta(days=1) # adjust for whole-day events

                if start >= day_end or end <= day_start:
                    # event is out of range
                    continue

                events.append(Event(title=title, start=start, end=end, color1=self.color1, color2=self.color2))

            return events

@dataclass
class Secrets:
    calendars: List[Calendar]

    @staticmethod
    def from_obj(data: Any) -> Secrets:
        return Secrets(calendars=[Calendar.from_obj(x) for x in data["calendar"]])

run_old = False

if __name__ == "__main__" and run_old:
    from canvas import Canvas, Background, CalendarEvent, CANVAS_WIDTH, CANVAS_HEIGHT
    from layout_old import layout

    secrets = Secrets.from_obj(toml.load(open("./secrets.toml", "r")))

    day = datetime.today()
    day = datetime(year=2024, month=12, day=27)

    events = [ev for cal in secrets.calendars for ev in cal.load_events(day, 1)]

    rects = layout(events, day, CANVAS_WIDTH, CANVAS_HEIGHT)
    print(rects)

    canvas: Canvas = Background(Color.WHITE)
    for event, e_layout in zip(events, rects):
        # canvas = DitheredRectangle(canvas, color=event.color1, color2=event.color2, rect = rect)
        print(event, e_layout)
        canvas = CalendarEvent.from_event(
            canvas,
            event,
            e_layout,
        )

    canvas.preview()

if __name__ == "__main__" and not run_old:
    from canvas import Canvas, Background
    from data import Color, Rectangle
    from layout import CalendarCanvas

    secrets = Secrets.from_obj(toml.load(open("./secrets.toml", "r")))

    day = datetime.today()
    # day = datetime(year=2024, month=3, day=5)
    # day = datetime(year=2024, month=12, day=26)
    days = 3

    events = [ev for cal in secrets.calendars for ev in cal.load_events(day, days)]
    print("events")
    for e in events:
        print(e)

    bg = Background(Color.WHITE)
    c = CalendarCanvas(bg, Rectangle(x0=0, y0=0, x1=480, y1=800), events)

    c.preview()
