from dataclasses import dataclass
import dataclasses
from typing import Tuple

class UnregisteredNetMessageClassException(Exception):
    pass


class InvalidNetMessageIdentifierException(Exception):
    pass


class NetMessageManager:
    """
        Assigns unique identifiers to NetMessage classes
        Call .register(cls) for every class you wanna send over a network.
    """
    def __init__(self):
        self.next_identifier: int = 0x01
        self.identifiers: dict[str, int] = {}
        self.classes: dict[int, type] = {}

    def register(self, cls: type):
        self.identifiers[cls.__name__] = self.next_identifier
        self.classes[self.next_identifier] = cls
        self.next_identifier += 1

    def get_identifier(self, cls: type) -> int:
        try:
            return self.identifiers[cls.__name__]
        except KeyError:
            raise UnregisteredNetMessageClassException
        
    def get_class(self, identifier: int) -> type:
        try:
            return self.classes[identifier]
        except KeyError:
            raise InvalidNetMessageIdentifierException
NET_MESSAGE_MANAGER = NetMessageManager()


class NetMessage:
    @staticmethod
    def serialize_str(s: str) -> bytes:
        msg_len = len(s).to_bytes(2, "big")
        msg = bytes(s, "utf-8")
        return msg_len + msg
    
    @staticmethod
    def deserialize_str(buf: bytes) -> Tuple[str, bytes]:
        str_len, buf = int.from_bytes(buf[0:2], "big"), buf[2:]
        str_data, buf = buf[0:str_len], buf[str_len:] 
        s = str_data.decode("utf-8")
        return s, buf
    
    @staticmethod
    def serialize_int(n: int) -> bytes:
        return n.to_bytes(4, "big")
    
    @staticmethod
    def deserialize_int(buf: bytes) -> Tuple[int, bytes]:
        n, buf = int.from_bytes(buf[0:4], "big"), buf[4:]
        return n, buf

    @staticmethod
    def deserialize(buf: bytes) -> Tuple["NetMessage", bytes]:
        identifier, buf = int(buf[0]), buf[1:]
        cls = NET_MESSAGE_MANAGER.get_class(identifier)
        fields = dataclasses.fields(cls)
        reconstructed_fields = {}
        for field in fields:
            if field.type is str:
                s, buf = NetMessage.deserialize_str(buf)
                reconstructed_fields[field.name] = s
            elif field.type is int:
                n, buf = NetMessage.deserialize_int(buf)
                reconstructed_fields[field.name] = n
            else:
                obj, buf = NetMessage.deserialize(buf)
                reconstructed_fields[field.name] = obj

        obj = cls(**reconstructed_fields)
        return obj, buf

    def serialize(self) -> bytes:
        identifier = NET_MESSAGE_MANAGER.get_identifier(self.__class__)
        fields = dataclasses.fields(self) # type: ignore
        buf = identifier.to_bytes(1, "big")
        for field in fields:
            if field.type is str:
                buf += NetMessage.serialize_str(self.__getattribute__(field.name))
            elif field.type is int:
                buf += NetMessage.serialize_int(self.__getattribute__(field.name))
            else:
                buf += self.__getattribute__(field.name).serialize()
        
        return buf

@dataclass
class SignIn(NetMessage):
    name: str
NET_MESSAGE_MANAGER.register(SignIn)

@dataclass
class User(NetMessage):
    name: str
    host: str
NET_MESSAGE_MANAGER.register(User)

@dataclass
class ServerIdentity(NetMessage):
    hostname: str
NET_MESSAGE_MANAGER.register(ServerIdentity)


@dataclass
class Message(NetMessage):
    sender: User
    to: User
    contents: str
    def __str__(self) -> str:
        return f"{self.sender.name}@{self.sender.host} -> {self.to.name}@{self.to.host}: {self.contents}"

NET_MESSAGE_MANAGER.register(Message)


if __name__ == "__main__":
    msg = Message(sender=User("a", "b", 3333), to=User("a", "b", 3333), contents="siema eniu")
    serialized = msg.serialize()
    deserialized, _ = NetMessage.deserialize(serialized)
    assert msg == deserialized
    print("PASS")