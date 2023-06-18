from collections import defaultdict
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
    to = messages.User(user, server)
    msg = messages.Message(
        sender=messages.User(username, host), 
        to=to, 
        contents=message
    )
    session.send_message(
        msg
    )

    return to, msg

shared_bool = threading.Event()
contacts: dict[net.messages.User, list[net.messages.Message]] = defaultdict(list)

def receive_messages(shared_bool):
    global contacts

    while True:
        try:
            if shared_bool.is_set():
                print("Quit thread")
                break

            time.sleep(0.1)
            msg = session.receive_message()
            if msg is not None:
                if type(msg) is messages.Message:
                    contacts[msg.sender].append(msg)
        except:
            print("Error reciving message")

thread = threading.Thread(target=receive_messages, args=(shared_bool, ))
thread.start()

def timeout_input(prompt, timeout=5):
    import sys
    import select
    print(prompt)
    inputs, _, _ = select.select([sys.stdin], [], [], timeout)

    if inputs:
        user_input = sys.stdin.readline().strip()
        return user_input
    else:
        return None


def send_messages():
    try:
        while True:
            import sys
            sys.stdout.write("\033[H\033[J")
            sys.stdout.flush() 
            print(f"Logged in: {username}@{host}")
            contact_selector: dict[int, net.messages.User] = {}
            for i, (contact, messages) in enumerate(contacts.items()):
                contact_selector[i] = contact
                print(f"[{i}] {contact.name}@{contact.host} [{len(messages)}]")

            print("[+] Add new contact")
            print("[.] Refresh")
            
            chosen_user_str = timeout_input("Pick a contact: ")
            if chosen_user_str is None:
                continue

            match chosen_user_str:
                case "+":
                    server = input("Choose server `knorr` or `lenor` : ")
                    user = input("Choose user : ")
                    userMessage = input("Write message: ") 
                    sent_to, sent_msg = send_msg(server, user, userMessage)
                    contacts[sent_to].append(sent_msg)
                case ".":
                    continue
                case other:
                    try:
                        if int(chosen_user_str) in contact_selector:
                            chosen_user = int(chosen_user_str)
                            selected_contact = contact_selector[chosen_user]
                            contact_messages = contacts[selected_contact]
                            for message in contact_messages:
                                print(message)

                            print("")
                            print("[1] Return to menu.")
                            print("[2] Send a message")

                            match int(input("Pick an option: ")):
                                case 1:
                                    continue
                                case 2:
                                    userMessage = input("Write message: ")
                                    sent_to, sent_msg = send_msg(selected_contact.host, selected_contact.name, userMessage)
                                    contacts[sent_to].append(sent_msg)
                        else:
                            print("No contact with that number")
                    except (ValueError, KeyError):
                        print("Invalid option.")

            time.sleep(1)
    except KeyboardInterrupt:
        shared_bool.set() 
        thread.join()     
        print("Crtl + C pressed")

send_messages()
