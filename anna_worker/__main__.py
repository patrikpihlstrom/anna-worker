import os
import socket
import time

from docker import errors
from worker import Worker

from anna_client.client import Client

if not ('ANNA_HOST' in os.environ and 'ANNA_TOKEN' in os.environ):
	os.environ['ANNA_HOST'] = 'https://api.annahub.se/'
client = Client(endpoint='https://api.annahub.se/')
if 'ANNA_TOKEN' in os.environ:
	client.inject_token(os.environ['ANNA_TOKEN'])
worker = Worker(max_concurrent=4)
last_status_check = 0


def update():
	global last_status_check
	try:
		worker.prune()
	except errors.APIError:
		pass
	if time.time() - last_status_check >= 3:
		remove_manually_stopped_jobs_from_host()
		last_status_check = time.time()
	worker.update()
	if len(worker.jobs) > 0:
		jobs = [job for job in worker.jobs if job.changed]
		if len(jobs) > 0:
			for job in jobs:
				client.update_jobs(where={'id': job.id}, data=job.dict())
				if job.status in ('DONE', 'ERROR', 'STOPPED', 'FAILED'):
					worker.stop_container(job)
					worker.jobs.remove(job)
				job.changed = False


def should_check_host_for_stopped_jobs():
	if len(worker.jobs) == 0:
		return False


def remove_manually_stopped_jobs_from_host():
	if should_check_host_for_stopped_jobs():
		jobs = client.get_jobs(where={'id_in': [job.id for job in worker.jobs]}, fields=('id', 'status'))
		if isinstance(jobs, list):
			for job in jobs:
				if job is None or job['status'] == 'STOPPED':
					worker.remove(job)


def request_work():
	if worker.should_request_work():
		jobs = client.get_jobs(where={'status': 'PENDING'}, fields=('id', 'site', 'driver', 'status', 'worker', 'log', 'container'))
		ids = tuple(job['id'] for job in jobs if job['worker'] is None)
		if len(ids) < 1:
			return
		client.reserve_jobs(worker=socket.gethostname(), job_ids=ids)
		if isinstance(jobs, list) and len(jobs) > 0:
			for job in jobs:
				worker.append(job)


if __name__ == '__main__':
	while True:
		update()
		request_work()
