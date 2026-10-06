"""Stand-in for socketpool: answers every HTTP request with the example summary of the home hub."""
import os

SAMPLE = os.path.join(os.path.dirname(__file__), "hub_beispiel.json")


class _Socket:
    def __init__(self):
        self.answer = b""

    def settimeout(self, seconds):
        pass

    def connect(self, address):
        pass

    def send(self, data):
        with open(SAMPLE, "rb") as f:
            self.answer = b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + f.read()
        return len(data)

    def recv_into(self, buffer):
        count = min(len(buffer), len(self.answer))
        buffer[:count] = self.answer[:count]
        self.answer = self.answer[count:]
        return count

    def close(self):
        pass


class SocketPool:
    AF_INET = 2
    SOCK_STREAM = 1
    SOCK_DGRAM = 2

    def __init__(self, radio):
        pass

    def getaddrinfo(self, host, port):
        return [(2, 1, 0, "", ("127.0.0.1", port))]

    def socket(self, family=AF_INET, type=SOCK_STREAM):
        return _Socket()
