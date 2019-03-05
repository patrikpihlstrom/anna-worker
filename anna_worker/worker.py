import re

import docker
from docker import errors


class Worker:
	"""
	This module handles communication between the job queue and docker
	"""

	def __init__(self, max_concurrent=2):
		self.client = docker.from_env()
		self.max_concurrent = max_concurrent
		self.hub = None
		self.jobs = []
		self.container_options = {'links': {'hub': 'hub'}, 'shm_size': '2G', 'detach': True}

	def __del__(self):
		self.prune()
		self.client.close()

	def run(self):
		"""
		Prune & start working through the queue
		"""
		while True:
			self.keep_hub_alive()  # Make sure the hub is running
			self.update_jobs()  # Retrieve logs & handle containers
			if self.can_run_more():  # Check if we can run more concurrent containers
				self.start_next_job()  # Get the next job in the queue and fire up a container

	def keep_hub_alive(self):
		"""
		Makes sure the selenium hub is running & removes any stopped hub containers
		:return:
		"""
		try:
			try:
				self.hub = self.client.containers.get('hub')
				if self.hub.status != 'running':
					self.hub.remove()
					self.keep_hub_alive()
			except docker.errors.NotFound:
				try:
					self.hub = self.client.containers.run('selenium/hub', name='hub', ports={'4444/tcp': 4444}, detach=True)
				except docker.errors.APIError:
					self.hub.stop()
					self.keep_hub_alive()
		except docker.errors.APIError:
			pass

	def update_jobs(self):
		"""
		Get all jobs that have exited for one reason or another and remove their containers
		"""
		for job in self.jobs:
			if job.status == 'rm':
				self.stop_container(job)
				self.jobs.pop(job)
			elif job.status in ('starting', 'running') and not self.is_running(job):
				self.complete_job(job)
			elif job.status == 'done':
				container = self.get_container(job)
				if container:
					if container.status != 'exited':
						container.stop()
					container.remove()

	def is_running(self, job):
		"""
		Check if the job's container is running
		:param job:
		:return:
		"""
		if len(job.container) > 0:
			container = self.get_container(job)
			if container is not False:
				return container.status in ('starting', 'running')
		return False

	def get_running(self):
		result = []
		for job in self.jobs:
			if self.is_running(job):
				result.append(job)
		return result

	def complete_job(self, job):
		self.get_logs(job)
		# TODO: This is a temporary hack
		result = job.log.rstrip().split('\n')[-1].split('/')
		if len(result) < 2:
			job.status = 'error'
		else:
			try:
				if len(result) != 2 or int(result[0]) != int(result[1]):
						job.status = 'failed'
				else:
						job.status = 'done'
			except ValueError:
				job.status = 'error'

		job.changed = True

	def stop_container(self, job):
		container = self.get_container(job)
		if container is not False and container.status == 'running':
			container.stop()

	def get_container(self, job):
		if len(job.container) == 0:
			return False
		try:
			return self.client.containers.get(job.container)
		except docker.errors.NotFound:
			return False

	def prune(self):
		try:
			self.client.containers.prune()
		except docker.errors.APIError as e:
			if 'a prune operation is already running' in e.explanation:  # ghetto
				return False
			raise docker.errors.APIError(e)

	def get_logs(self, job):
		container = self.get_container(job)
		log = job.log
		if container is not False:
			job.log = re.sub("\\x1b\[0m|\\x1b\[92m|\\x1b\[91m|\\x1b\[93m", '', container.logs().decode('utf-8'))  # colorless
		else:
			job.log = 'unable to get logs from container'

		# TODO: move this to the client
		#if not os.path.isdir('/tmp/anna/' + job.tag):
		#	os.mkdir('/tmp/anna/' + job.tag)
		#if log != job.log:
		#	f = open('/tmp/anna/' + job.tag + '/anna.log', 'a+')
		#	f.write('\n' + job.log)
		#	f.close()

	def can_run_more(self):
		"""
		Just a simple check against max_concurrent
		"""
		queue_length = len(self.jobs)
		if queue_length == 0:
			return False
		running = len(self.get_running())
		return queue_length - running > 0 and running < self.max_concurrent

	def start_next_job(self):
		"""
		Starts the next pending job in the queue
		"""
		job = self.get_next_job()
		if job is not None:
			self.start_job(job)
			return job
		return False

	@staticmethod
	def before_start(job):
		"""
		Make sure we can run the job, set the status & report to slack
		:param job:
		:return:
		"""
		if job.driver not in ('chrome', 'firefox'):
			raise TypeError('desired driver(s) not supported: ' + job.driver)

		job.status = 'starting'
		job.tag = '-'.join((job.driver, job.site))
		job.changed = True

	def __start__(self, job):
		job.container = str(self.run_container(job).short_id)
		job.changed = True

	@staticmethod
	def after_start(job):
		"""
		Set the status & report to slack
		:param job:
		:return:
		"""
		job.status = 'running'
		job.tag = '-'.join((job.driver, job.site, job.container))
		job.changed = True

	def start_job(self, job):
		"""
		Starts the next pending job in the queue
		"""
		self.before_start(job)
		self.__start__(job)
		self.after_start(job)

	def run_container(self, job):
		"""
		Attempt to start the container
		:param job:
		:return:
		"""
		#if not os.path.isdir('/tmp/anna'):
		#	os.mkdir('/tmp/anna')
		image, volumes, command = job.get_image_volumes_and_command()
		return self.client.containers.run(
			image=image,
			links=self.container_options['links'],
			shm_size=self.container_options['shm_size'],
			detach=self.container_options['detach'],
			command=command)

	def get_next_job(self):
		for job in self.jobs:
			if job.status == 'pending':
				return job
