import pathlib
import urllib.parse
import mimetypes
import socket
import json
import logging
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler


BASE_DIR = pathlib.Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = "0.0.0.0"
SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 5000


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)

        match pr_url.path:
            case '/':
                self.send_html_file('index.html')
            case '/message':
                self.send_html_file('message.html')
            case _:
                file = BASE_DIR.joinpath(pr_url.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html_file('error.html', 404)

    def send_static(self, file):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(file, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

def write_json(new_data, filename='storage/data.json'):
    with open(filename,'r+') as file:
        file_data = json.load(file)
        file_data.update(new_data)
        file.seek(0)
        json.dump(file_data, file, indent = 4)

def save_data_from_form(data):
    data_parse = urllib.parse.unquote_plus(data.decode())
    try:
        data_dict = {str(datetime.now()): {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}}
        # with open(BASE_DIR.joinpath('storage/data.json'), 'w', encoding='utf-8') as fd:
        #     json.dump(data_dict, fd, ensure_ascii=False, indent=4)
        write_json(data_dict)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)

def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Socket recieved {address}: {msg}")
            save_data_from_form(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()

def run_http_server(host, port, server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (host, port)
    http_server = server_class(server_address, handler_class)
    # server = Thread(target=http.serve_forever)
    try:
        logging.info("Starting http server")
        http_server.serve_forever()
        # server.start()
    except KeyboardInterrupt:
        http_server.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")
    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()

