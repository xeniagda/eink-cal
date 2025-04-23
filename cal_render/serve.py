from canvas import Canvas, Background, CANVAS_WIDTH, CANVAS_HEIGHT

import socket
from tqdm import tqdm

def send(conn: socket.socket, c: Canvas):
    header = conn.recv(6)
    if header != b"hii^_^":
        print("incorrect handshake:", repr(header))
        return

    print("correct handshake. sending back")
    conn.send(b"hewwo")

    print("sending image")
    for i in tqdm(range(CANVAS_HEIGHT * CANVAS_WIDTH), unit="px", unit_scale=True):
        y = i % CANVAS_HEIGHT
        x = CANVAS_WIDTH - (i // CANVAS_HEIGHT) - 1
        col = c(x, y)
        conn.send(bytes([col.to_screen_color_idx()]))
