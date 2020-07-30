import socket
import yaml

from docker import errors

from anna_client.client import Client
from worker import Worker


class Main:
    config = None
    client = None
    worker = None

    def __init__(self):
        self.queue = []
        with open('../config.yml', 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print(e)
                exit()
        self.client = Client(endpoint=self.config['api']['host'])
        self.client.inject_token(self.config['api']['token'])
        self.worker = Worker(self.config)

    def update(self):
        try:
            self.worker.prune()
        except errors.APIError:
            pass
        self.worker.update()

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.config['socket']['host'], self.config['socket']['port']))
        while True:
            self.worker.keep_hub_alive()
            sock.listen(5)
            connection, addr = sock.accept()
            data = connection.recv(1024)
            if data:
                self.queue.append(data.decode('utf-8').rsplit('\n', 1)[-1])
            response_headers = {
                'Content-Type': 'text/html; encoding=utf8',
                'Content-Length': 0,
                'Connection': 'close',
            }

            response_headers_raw = ''.join('%s: %s\r\n' % (k, v) for k, v in response_headers.items())

            response_proto = 'HTTP/1.1'
            response_status = '200'
            response_status_text = 'OK'

            r = '%s %s %s\r\n' % (response_proto, response_status, response_status_text)
            connection.send(bytes(r.encode(encoding='utf-8')))
            connection.send(bytes(response_headers_raw.encode(encoding='utf-8')))
            connection.send(bytes('\r\n'.encode('utf-8')))  # to separate headers from body
            connection.send(bytes(''.encode(encoding='utf-8')))

            connection.close()
            self.process_queue()
            self.update()

    def process_queue(self):
        while self.worker.available() and len(self.queue) > 0:
            id = self.queue[0]
            if len(id) <= 0:
                return
            self.client.reserve_jobs(worker=socket.gethostname(), job_ids=(id,))
            fields = ('id', 'site', 'driver', 'status', 'worker', 'container')
            job = self.client.get_jobs(where={'id': id}, fields=fields, limit=1)
            if isinstance(job, list) and len(job) > 0:
                job = job[0]
            if isinstance(job, dict):
                print(job)
                container = self.worker.append(job)
                if len(container) > 0 and isinstance(container, str):
                    self.client.update_jobs(where={'id': job['id']}, data={'container': container})
            self.queue.remove(self.queue[0])


if __name__ == '__main__':
    main = Main()
    main.listen()
