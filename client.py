import sys

from common import net
from common import messages


session = net.TcpStream.to_ip("127.0.0.1", int(sys.argv[1]))

session.send_message(
    messages.Message(
        sender=messages.User("dupa", "dupa"), 
        to=messages.User("cipa", "cipa"), 
        contents="hejka"
    )
)

session.socket.close()