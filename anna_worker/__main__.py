import os
import socket

from docker import errors
from worker import Worker

from anna_client.client import Client

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


def request_work():
	if worker.should_request_work():
		jobs = client.get_jobs(where={'status': 'PENDING'}, fields=('id', 'site', 'driver', 'status', 'worker', 'container'))
		ids = tuple(job['id'] for job in jobs if job['worker'] is None)
		if len(ids) < 1:
			return
		client.reserve_jobs(worker=socket.gethostname(), job_ids=ids)
		if isinstance(jobs, list) and len(jobs) > 0:
			for job in jobs:
				container = worker.append(job)
				if len(container) > 0 and isinstance(container, str):
					client.update_jobs(where={'id': job['id']}, data={'container': container})


if __name__ == '__main__':
	while True:
		update()
		request_work()
