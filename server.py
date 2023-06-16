from time import sleep
import signal
from collections import defaultdict
from typing import Any

from common import net

signal.signal(signal.SIGTERM, lambda dont, care: exit(0))


DISPATCH_TABLE: defaultdict[type, list[Any]] = defaultdict(list)
def bind(msg_type: type):
    """Decorator for neatly dispatching incoming messages to handler functions
    """
    def decorator(function):
        DISPATCH_TABLE[msg_type].append(function)
        return function
    return decorator

class Server:
    def __init__(self, hostname: str, port: int):
        """Start a new server
        """
        self.hostname = hostname
        self.listener = net.Listener(port)
        self.user_map: defaultdict[str, list[net.Stream]] = defaultdict(list)
        self.pending_messages: defaultdict[str, list[net.messages.NetMessage]] = defaultdict(list)

    def event_loop(self):
        """The main event loop. This function never returns.
        """
        while True:
            self.listener.await_event()
            self.listener.accept_incoming_connections()
            for addr, stream in self.listener.sessions.items():
                if msg := stream.receive_message():
                    self.dispatch(msg, stream)
            self.listener.remove_closed_connections()

    @bind(net.messages.SignIn)
    def bind_user(self, msg: net.messages.SignIn, stream: net.Stream):
        self.user_map[msg.name].append(stream)

    @bind(net.messages.SignIn)
    def send_pending_messages(self, msg: net.messages.SignIn, stream: net.Stream):
        print("send_pending_messages")
        for message in self.pending_messages[msg.name]:
            stream.send_message(message)

        self.pending_messages[msg.name] = []

    @bind(net.messages.Message)
    def pass_local_message(self, msg: net.messages.Message, stream: net.Stream):
        destination = msg.to
        # If message is to a local user
        if destination.host == self.hostname:
            if destination_streams := self.user_map[destination.name]:
                # User is online, send the message to them
                successful_deliveries = 0
                for destination_stream in destination_streams:
                    try:
                        destination_stream.send_message(msg)
                        successful_deliveries += 1
                    except net.SocketClosed:
                        continue
                if not successful_deliveries:
                    self.pending_messages[destination.name].append(msg)

            else:
                # User is offline, store the message 
                self.pending_messages[destination.name].append(msg)


    @bind(net.messages.Message)
    def print_message(self, msg: net.messages.Message, stream: net.Stream):
        print(msg)

    def dispatch(self, msg: net.messages.NetMessage, stream: net.Stream):
        """Passes the incoming message to appropriate handler methods"""
        for func in DISPATCH_TABLE[type(msg)]:
            result = func(self, msg, stream)
            if result == False:
                print("dispatch reject at {func}")
                break
    

if __name__ == "__main__":
    print(DISPATCH_TABLE)
    server = Server("knorr", 3333)
    server.event_loop()
