import sys
import signal
import threading
import time

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

def send_msg(server, user, message):
    session.send_message(
        messages.Message(
            sender=messages.User(username, host), 
            to=messages.User(user, server), 
            contents=message
        )
    )

shared_bool = threading.Event()

def receive_messages(shared_bool):
    while True:
        try:
            if shared_bool.is_set():
                print("Quit thread")
                break

            time.sleep(0.1)
            # session.await_event()
            msg = session.receive_message()
            # assert type(msg) is messages.Message
            if msg is not None:
                print(f"\n Received: {msg} \n")
        except:
            print("Error reciving message")

thread = threading.Thread(target=receive_messages, args=(shared_bool, ))
thread.start()

def send_messages():
    try:
        while True:
            server = input("Choose server `knorr` or `lenor` : ")
            user = input("Choose user : ")
            userMessage = input("Write message: ")   
            send_msg(server, user, userMessage)
            time.sleep(1)
    except KeyboardInterrupt:
        shared_bool.set() 
        thread.join()     
        print("Crtl + C pressed")

send_messages()
