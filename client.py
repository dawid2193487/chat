from common import net

session = net.TcpStream.to_ip("127.0.0.1", 3333)

session.write(b"dupa")

session.socket.close()