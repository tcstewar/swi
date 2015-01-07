"""Simple Web Sockets

Based on 
http://sidekick.windforwings.com/2013/03/
       minimal-websocket-broadcast-server-in.html

Currently only handles messages up to 126 bytes long.  To extend this,
see http://tools.ietf.org/html/rfc6455#section-5.2
Currently does not handle ping / pong messages
"""


import socket
import hashlib
import base64
import threading
import traceback


class ClientSocket(object):
    def __init__(self, socket, addr):
        self.socket = socket
        self.addr = addr

    def set_timeout(self, timeout):
        self.socket.settimeout(timeout)

    def set_blocking(self, flag):
        self.socket.setblocking(flag)

    def read(self):
        # as a simple server, we expect to receive:
        #    - all data at one go and one frame
        #    - one frame at a time
        #    - text protocol
        #    - no ping pong messages
        try:
            data = bytearray(self.socket.recv(512))
        except socket.error, socket.timeout:
            return None

        if(len(data) < 6):
            raise Exception("Error reading data")
        # FIN bit must be set to indicate end of frame
        assert(0x1 == (0xFF & data[0]) >> 7)
        # data must be a text frame
        # 0x8 (close connection) is handled with assertion failure
        assert(0x1 == (0xF & data[0]))

        # assert that data is masked
        assert(0x1 == (0xFF & data[1]) >> 7)
        datalen = (0x7F & data[1])

        str_data = ''
        if(datalen > 0):
            mask_key = data[2:6]
            masked_data = data[6:(6+datalen)]
            unmasked_data = [masked_data[i] ^ mask_key[i % 4]
                             for i in range(len(masked_data))]
            str_data = str(bytearray(unmasked_data))
        return str_data

    def write(self, data):
        # 1st byte: fin bit set. text frame bits set.
        # 2nd byte: no mask. length set in 1 byte.
        resp = bytearray([0b10000001, len(data)])
        # append the data bytes
        for d in bytearray(data):
            resp.append(d)

        self.socket.send(resp)


class WebSocketServer(object):
    MAGIC = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    HSHAKE_RESP = ("HTTP/1.1 101 Switching Protocols\r\n"
                   "Upgrade: websocket\r\n"
                   "Connection: Upgrade\r\n"
                   "Sec-WebSocket-Accept: %s\r\n"
                   "\r\n")

    def __init__(self):
        self.clients = []

    def parse_headers(self, data):
        headers = {}
        lines = data.splitlines()
        for l in lines:
            parts = l.split(": ", 1)
            if len(parts) == 2:
                headers[parts[0]] = parts[1]
        headers['code'] = lines[len(lines) - 1]
        return headers

    def handshake(self, client):
        data = client.socket.recv(2048)
        headers = self.parse_headers(data)
        key = headers['Sec-WebSocket-Key']
        resp_data = (self.HSHAKE_RESP %
                     base64.b64encode(hashlib.sha1(key + self.MAGIC).digest()))
        return client.socket.send(resp_data)

    def handle_client(self, client):
        self.handshake(client)
        client.set_blocking(False)
        try:
            self.run(client)
        except Exception as e:
            traceback.print_exc()
        print('Client closed: ' + str(client.addr))
        self.clients.remove(client)
        client.socket.close()

    def start_server(self, port):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', port))
        s.listen(5)
        try:
            while(1):
                print ('Waiting for connection...')
                conn, addr = s.accept()
                client = ClientSocket(conn, addr=addr)
                print ('Connection from: ' + str(addr))
                threading.Thread(target=self.handle_client,
                                 args=(client,)).start()
                self.clients.append(client)
        except:
            for c in self.clients:
                c.socket.close()


if __name__ == '__main__':
    import time

    class TestServer(WebSocketServer):
        def run(self, client):
            tick = 0
            while True:
                msg = client.read()
                if msg is not None:
                    for c in self.clients:
                        c.write(msg)
                client.write('%d' % tick)
                tick += 1
                time.sleep(1)
    ws = TestServer()
    ws.start_server(4545)
