import sys

from common import net
from common import messages


session = net.Stream.to_ip("127.0.0.1", int(sys.argv[1]))

session.send_message(
    messages.SignIn(
        "sznio"
    )
)

session.send_message(
    messages.Message(
        sender=messages.User("dromiarz", "knorr", 3333), 
        to=messages.User("sznio", "knorr", 3333), 
        contents="hejka"
    )
)

session.await_event()

print(session.receive_message())

session.socket.close()