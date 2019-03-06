import os

from worker import Worker

from anna_client.client import Client


if __name__ == '__main__':
	if not ('ANNA_HOST' in os.environ and 'ANNA_TOKEN' in os.environ):
		print('Please set both ANNA_HOST and ANNA_TOKEN in your env')

	else:
		client = Client(host=os.environ['ANNA_HOST'], token=os.environ['ANNA_TOKEN'])
		worker = Worker(2)
		while True:
			worker.update()  # <intended API endpoint>:<data>
			if len(worker.jobs) > 0:
				client.update([job.dict() for job in worker.jobs if job.changed])
				for job in worker.jobs:
					if job.changed:
						if job.status in ('done', 'failed', 'error', 'rm'):
							worker.jobs.remove(job)
						else:
							job.changed = False
			if worker.should_request_work():
				job = client.request_job()
				if isinstance(job, dict):
					worker.append(job)
