import sys
import signal
from common import net
from common import messages

signal.signal(signal.SIGTERM, lambda dont, care: exit(0))

try:
    username = sys.argv[1]
    host = sys.argv[2]
except IndexError:
    print(f"syntax: {sys.argv[0]} username host [port]")
    exit(1)

try:
    port = int(sys.argv[3])
except IndexError:
    port = 3333

print(f"connecting to {host}:{port}")
session = net.Stream.tcp(host, port)

session.send_message(
    messages.SignIn(
        username
    )
)

session.await_event()
ident = session.receive_message()
assert type(ident) is net.messages.ServerIdentity
host = ident.hostname
print(f"Connected to {host}.")

while True:
    session.await_event()
    msg = session.receive_message()
    assert type(msg) is messages.Message
    print(f"Received: {msg}")
    response = messages.Message(msg.to, msg.sender, msg.contents)
    session.send_message(response)
