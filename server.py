from common import net
from time import sleep
import signal

signal.signal(signal.SIGTERM, lambda foo, bar: exit(0))

listener = net.TcpListener(3333)
while True:
    listener.await_event()
    listener.accept_incoming_connections()
    for addr, stream in listener.sessions.items():
        if msg := stream.receive_message():
            print(msg)
    listener.remove_closed_connections()