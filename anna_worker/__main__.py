import os
import re
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue
import threading

from docker import errors

from anna_client.client import Client
from anna_worker.worker import Worker

queue = Queue()


class Http(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def do_HEAD(self):
		self._set_headers()

	def do_GET(self):
		self._set_headers()
		self.wfile.write('What is thy bidding'.encode('utf-8'))

	def do_POST(self):
		content_length = int(self.headers['Content-Length'])
		post_data = self.rfile.read(content_length)
		queue.put(item=post_data, block=True, timeout=30)
		self._set_headers()
		self.wfile.write('one moment please\n'.encode('utf-8'))


client = Client(endpoint=os.environ['ANNA_HOST'])
if 'ANNA_TOKEN' in os.environ:
	client.inject_token(os.environ['ANNA_TOKEN'])
worker = Worker(max_concurrent=4)


def update():
	try:
		worker.prune()
	except errors.APIError:
		pass
	worker.update()


def handle_job_requests():
	http = HTTPServer(('localhost', 80), Http)
	http.serve_forever()


def process_queue():
	if worker.available() and queue.qsize() > 0:
		item = queue.get()
		if isinstance(item, bytes) and len(item) == 24:
			item = str(item, 'utf-8')
		if re.match('[A-Za-z0-9]*$', item):
			fields = ('id', 'site', 'driver', 'status', 'worker', 'container')
			jobs = client.get_jobs(where={'id': item}, fields=fields, limit=1)
			ids = tuple(job['id'] for job in jobs if job['worker'] is None)
			if len(ids) < 1:
				return
			client.reserve_jobs(worker=socket.gethostname(), job_ids=ids)
			if isinstance(jobs, list) and len(jobs) > 0:
				for job in jobs:
					container = worker.append(job)
					if len(container) > 0 and isinstance(container, str):
						client.update_jobs(where={'id': job['id']}, data={'container': container})
		queue.task_done()


if __name__ == '__main__':
	httpd = threading.Thread(target=handle_job_requests)
	httpd.start()
	while True:
		process_queue()
		update()
