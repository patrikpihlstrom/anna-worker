import os
import time

from docker import errors
from worker import Worker

from anna_client.client import Client

client = Client(host=os.environ['ANNA_HOST'], token=os.environ['ANNA_TOKEN'])
worker = Worker(max_concurrent=2)
last_status_check = 0


def update():
	try:
		worker.prune()
	except errors.APIError:
		pass
	if time.time() - last_status_check >= 3:
		remove_manually_stopped_jobs_from_host()
	worker.update()
	if len(worker.jobs) > 0:
		client.update([job.dict() for job in worker.jobs if job.changed])
		for job in worker.jobs:
			if job.changed:
				if job.status in ('done', 'failed', 'error', 'rm'):
					worker.jobs.remove(job)
				else:
					job.changed = False


def remove_manually_stopped_jobs_from_host():
	jobs = client.query({'id': [job.id for job in worker.jobs]})
	for job in jobs:
		if job is None or job['status'] == 'rm':
			job.status = 'rm'


def request_work():
	if worker.should_request_work():
		job = client.request_job()
		if isinstance(job, dict):
			worker.append(job)
		remove_manually_stopped_jobs_from_host()


if __name__ == '__main__':
	if not ('ANNA_HOST' in os.environ and 'ANNA_TOKEN' in os.environ):
		print('Please set both ANNA_HOST and ANNA_TOKEN in your env')
		exit(0)

	while True:
		update()
		request_work()
