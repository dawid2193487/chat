from common import net
from time import sleep

listener = net.TcpListener(3333)
while True:
    sleep(0.05)
    print(listener.connection_count)
    listener.accept_incoming_connections()
    for addr, stream in listener.sessions.items():
        if data := stream.read():
            print(data)
    listener.remove_closed_connections()