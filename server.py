from time import sleep
import signal
import socket
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
    def __init__(self, port: int = 3333):
        """Start a new server
        """
        self.hostname = socket.gethostname()
        self.tcp_listener = net.Listener.tcp(port)
        self.sctp_listener = net.Listener.sctp(port)
        self.user_map: defaultdict[str, list[net.Stream]] = defaultdict(list)
        self.pending_messages: defaultdict[str, list[net.messages.NetMessage]] = defaultdict(list)
        print(f"Server running at hostname {self.hostname}.")

    def event_loop(self):
        """The main event loop. This function never returns.
        """
        while True:
            # # listen for either tcp or sctp traffic
            listeners = [self.tcp_listener, self.sctp_listener]
            net.await_any(listeners)

            for listener in listeners:
                listener.accept_incoming_connections()
                for addr, stream in listener.sessions.items():
                    if msg := stream.receive_message():
                        self.dispatch(msg, stream)
                listener.remove_closed_connections()

    @bind(net.messages.SignIn)
    def bind_user(self, msg: net.messages.SignIn, stream: net.Stream):
        print(f"User {msg.name} connected.")
        self.user_map[msg.name].append(stream)

    @bind(net.messages.SignIn)
    def send_ident(self, msg: net.messages.SignIn, stream: net.Stream):
        #print(f"Ident sent to {msg.name}.")
        stream.send_message(net.messages.ServerIdentity(self.hostname))

    @bind(net.messages.SignIn)
    def send_pending_messages(self, msg: net.messages.SignIn, stream: net.Stream):
        for message in self.pending_messages[msg.name]:
            stream.send_message(message)

        self.pending_messages[msg.name] = []

    # @bind(net.messages.Message)
    # def print_message(self, msg: net.messages.Message, stream: net.Stream):
    #     print(msg)

    @bind(net.messages.Message)
    def pass_local_message(self, msg: net.messages.Message, stream: net.Stream):
        destination = msg.to
        # If message is to a local user
        if destination.host.strip() == self.hostname:
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
            return False #we handled this message, so don't send it to other handlers
    
    @bind(net.messages.Message)
    def pass_remote_message(self, msg: net.messages.Message, stream: net.Stream):
        #print("passing remote message")
        #print(f"Message server: ##{msg.to.host}##")
        remote_stream = net.Stream.sctp(msg.to.host.strip(), 3333)
        remote_stream.send_message(msg)

    def dispatch(self, msg: net.messages.NetMessage, stream: net.Stream):
        """Passes the incoming message to appropriate handler methods"""
        for func in DISPATCH_TABLE[type(msg)]:
            result = func(self, msg, stream)
            if result == False:
                #print("dispatch reject at {func}")
                break
    

if __name__ == "__main__":
    #print(DISPATCH_TABLE)
    server = Server()
    server.event_loop()
