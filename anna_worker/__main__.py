import socket
import threading
from _thread import *
from queue import Queue
import socket
import yaml

from docker import errors

from anna_client.client import Client
from worker import Worker
from pprint import pprint

lock = threading.Lock()
queue = Queue()

config = None
with open('../config.yml', 'r') as stream:
	try:
		config = yaml.safe_load(stream)
	except yaml.YAMLError as e:
		print(e)
		exit()

client = Client(endpoint=config['api']['host'])
client.inject_token(config['api']['token'])
worker = Worker(max_concurrent=4)


def update():
	try:
		worker.prune()
	except errors.APIError:
		pass
	worker.update()


def listen():
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((config['socket']['host'], config['socket']['port']))
	sock.listen(5)
	while True:
		connection, addr = sock.accept()
		lock.acquire()
		data = connection.recv(1024)
		if not data or len(data) < 24:
			lock.release()
		else:
			data = data.decode('utf-8').rsplit('\n', 1)[-1]
			queue.put(item=data)

		# Clearly state that connection will be closed after this response,
		# and specify length of response body
		response_headers = {
			'Content-Type': 'text/html; encoding=utf8',
			'Content-Length': 0,
			'Connection': 'close',
		}

		response_headers_raw = bytes(''.join('%s: %s\n' % (k, v) for k, v in response_headers.items()), 'utf8')
		response_proto = 'HTTP/1.1'
		response_status = '200'
		connection.send(bytes('%s %s' % (response_proto, response_status), 'utf8'))
		connection.send(response_headers_raw)
		connection.close()


def process_queue():
	if worker.available() and queue.qsize() > 0:
		item = queue.get()
		ids = item.split(',')
		print(ids)
		if len(ids) <= 0:
			return
		client.reserve_jobs(worker=socket.gethostname(), job_ids=ids)
		fields = ('id', 'site', 'driver', 'status', 'worker', 'container')
		jobs = client.get_jobs(where={'id_in': ids}, fields=fields, limit=1)
		if isinstance(jobs, list) and len(jobs) > 0:
			for job in jobs:
				container = worker.append(job)
				if len(container) > 0 and isinstance(container, str):
					client.update_jobs(where={'id': job['id']}, data={'container': container})
		queue.task_done()


if __name__ == '__main__':
	start_new_thread(listen, ())
	while True:
		process_queue()
		update()
