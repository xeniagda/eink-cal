from fetch_calendar import Secrets
from layout import CalendarCanvas
from data import Rectangle, Color
from canvas import Background
from serve import send
import socket
import toml
import os

secrets_path = os.path.join(os.path.dirname(__file__), "secrets.toml")

from datetime import datetime, date

import argparse

parser = argparse.ArgumentParser("cal-render")

parser.add_argument("-d", "--date", required=False, help="Date (in YYYY-MM-DD) to render calendar for")
parser.add_argument("-n", "--n-days", nargs=1, required=False, default=7, type=int, help="Number of days in the future to show")
parser.add_argument("--dark", action="store_true", help="Dark mode")

subparser = parser.add_subparsers(dest="subcommand")

parser_preview = subparser.add_parser("preview")

parser_serve = subparser.add_parser("serve")
parser_serve.add_argument("-o", "--once", action="store_true", help="Quit after one request has been served")
parser_serve.add_argument("-p", "--port", default=2137, type=int, help="Port to listen on")

env = parser.parse_args()

def render_date() -> date:
    if env.date is None:
        return datetime.today().date()
    return datetime.strptime(env.date, "%Y-%m-%d").date()

# early exit if the date is unparsable
print("(initially) working with", render_date())

if env.subcommand == "preview":
    secrets = Secrets.from_obj(toml.load(open(secrets_path, "r")))

    events = [ev for cal in secrets.calendars for ev in cal.load_events(render_date(), env.n_days)]

    c = CalendarCanvas(bounding_rect=Rectangle(x0=0, y0=0, x1=480, y1=800), events=events, dark_mode=env.dark)

    c.preview()

elif env.subcommand == "serve":
    while True:
        secrets = Secrets.from_obj(toml.load(open(secrets_path, "r")))

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", env.port))
        s.listen(1)
        print(f"Listening on port {env.port}")

        conn, addr = s.accept()
        print(f"Connection from {addr}. Fetching calendar")

        events = [ev for cal in secrets.calendars for ev in cal.load_events(render_date(), env.n_days)]

        c = CalendarCanvas(bounding_rect=Rectangle(x0=0, y0=0, x1=480, y1=800), events=events, dark_mode=env.dark)

        print(f"Sending content")
        send(conn, c)
        print(f"Closing connection")
        s.close()

        if env.once:
            break
