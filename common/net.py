import socket
from select import select
from typing import Tuple, Union
from common import messages

BUFSIZE = 4096

class SocketError(Exception):
    pass

class SocketClosed(Exception):
    pass

class Stream:
    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.closed = False
        self.remainder = bytes()
        self.pending = False
        
    @classmethod
    def tcp(cls, host: str, port: int) -> "Stream":
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return cls(s)
    
    @classmethod
    def sctp(cls, host: str, port: int) -> "Stream":
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
        s.connect((host, port))
        return cls(s)

    @property
    def has_pending_data(self):
        pending = self.pending
        self.pending = False
        return pending

    def read(self) -> Union[bytes, None]:
        if self.closed:
            raise SocketClosed

        readable, writable, errored = select([self.socket], [], [self.socket], 0)
        if readable:
            read_bytes = self.socket.recv(BUFSIZE)
            if len(read_bytes) == 0:
                self.closed = True
                return None
            return read_bytes
        
        if errored:
            raise SocketError

        return None
    
    def write(self, buf: bytes):
        if self.closed:
            raise SocketClosed
        
        sent_bytes_amount = self.socket.send(buf)
        assert sent_bytes_amount == len(buf)

    def receive_message(self) -> Union[messages.NetMessage, None]:
        buf = self.read()
        if buf is None:
            buf = bytes()
        
        buf = self.remainder + buf
        #print(buf)
        
        if len(buf) == 0:
            return None

        msg, self.remainder = messages.NetMessage.deserialize(buf)
        self.pending = len(self.remainder) != 0
        return msg
        # return messages.NetMessage.deserialize(buf)[0]
    
    def send_message(self, message: messages.NetMessage):
        #print(f"Sending: {message}")
        self.write(message.serialize())

    def await_event(self):
        #print("waiting for message...")
        readable, writable, errored = select([self.socket], [], [])
        return

def await_any(listeners: list["Listener"]):
    # waits for any event in any of the listeners
    sockets = [listener.socket for listener in listeners]
    for listener in listeners:
        sockets += [session.socket for session in listener.sessions.values()]
    readable, writable, errored = select(sockets, [], [])
    return

class Listener:
    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.sessions: dict[Tuple[str, int], Stream] = {}

    @classmethod
    def tcp(cls, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", port))
        s.listen()

        return cls(s)

    @classmethod
    def sctp(cls, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
        s.bind(("", port))
        s.listen()

        return cls(s)

    @property
    def connection_count(self):
        return len(self.sessions)

    def accept_incoming_connections(self):
        readable, writable, errored = select([self.socket], [], [], 0)
        while readable:
            session_socket, remote_address = self.socket.accept()
            self.sessions[remote_address] = Stream(session_socket)
            readable, writable, errored = select([self.socket], [], [], 0)

    def remove_closed_connections(self):
        self.sessions = {
            addr: session 
            for (addr, session) in self.sessions.items()
            if not session.closed
        }

    def await_event(self):
        for session in self.sessions.values():
            if session.has_pending_data:
                return
        sessions = [session.socket for session in self.sessions.values()]
        readable, writable, errored = select([self.socket]+sessions, [], [])
        return
