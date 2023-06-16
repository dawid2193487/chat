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
        
    @classmethod
    def to_ip(cls, ip: str, port: int) -> "Stream":
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # FIXME: pierdolnij to mu tak żeby było nieczytelnie żeby był zadowolony
        s = socket.create_connection((ip, port))
        return cls(s)

    @property
    def has_pending_data(self):
        pending = self.pending
        self.pending = False
        return pending

    # @classmethod
    # def from_socket(cls, socket: socket.socket):
    #     self = cls()
    #     return self

    def read(self) -> Union[bytes, None]:
        if self.closed:
            return None

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
        print(buf)
        
        if len(buf) == 0:
            return None

        msg, self.remainder = messages.NetMessage.deserialize(buf)
        self.pending = len(self.remainder) != 0
        return msg
        # return messages.NetMessage.deserialize(buf)[0]
    
    def send_message(self, message: messages.NetMessage):
        self.write(message.serialize())

    def await_event(self):
        readable, writable, errored = select([self.socket], [], [])
        return



class Listener:
    def __init__(self, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("", port))
        self.socket.listen()

        self.sessions: dict[Tuple[str, int], Stream] = {}

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
