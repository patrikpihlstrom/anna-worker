import copy
import unittest

from anna_worker.worker import Worker
from anna_worker.job import Job


class TestWorker(unittest.TestCase):
	def setUp(self):
		self.mock_firefox = Job(driver='firefox', site='test', status='PENDING')
		self.mock_chrome = Job(driver='chrome', site='test', status='PENDING')
		self.worker = Worker(2)
		self.worker.keep_hub_alive()

	def tearDown(self):
		self.worker.prune()

	def test_prune(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.worker.start_job(job)
		self.assertNotEqual(False, self.worker.get_container(job))
		self.assertEqual('running', self.worker.get_container(job).status)
		self.worker.prune()
		self.assertEqual('running', self.worker.get_container(job).status)
		self.assertNotEqual(False, self.worker.get_container(job))
		self.worker.stop_container(job)
		self.assertEqual(False, self.worker.get_container(job))

	def test_start_next_job(self):
		self.assertEqual(0, len(self.worker.jobs))
		self.worker.jobs.append(copy.copy(self.mock_firefox))
		self.worker.jobs.append(copy.copy(self.mock_firefox))
		for i in range(0, 2):
			self.assertIsStartedJob(self.mock_firefox, self.worker.start_next_job())

	def test_start_job(self):
		self.worker.jobs.append(copy.copy(self.mock_firefox))
		self.worker.jobs.append(copy.copy(self.mock_chrome))
		for job in self.worker.jobs:
			self.worker.start_job(job)
			self.assertNotEqual('', job.container)
			self.assertIsNotNone(self.worker.client.containers.get(job.container).id)

	def test_run_container(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.worker.start_job(job)
		self.assertIsNotNone(job.container)
		self.assertNotEqual(False, job.container)
		self.assertIsNotNone(self.worker.get_container(job).id)

	def test_get_logs(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.worker.get_logs(job)
		self.assertEqual('unable to get logs from container', job.log)
		self.worker.start_job(job)
		self.worker.get_logs(job)
		self.assertEqual('', job.log)
		#self.assertTrue(os.path.isdir('/tmp/anna/' + job.tag))
		#self.assertTrue(os.path.isfile('/tmp/anna/' + job.tag + '/anna.log'))

	def test_stop_container(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.assertFalse(self.worker.get_container(job))
		self.worker.start_job(job)
		self.assertNotEqual(False, self.worker.get_container(job))
		self.assertEqual('running', self.worker.get_container(job).status)
		self.worker.stop_container(job)
		self.assertEqual(False, self.worker.get_container(job))

	def test_running(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.assertFalse(self.worker.is_running(job))
		self.worker.start_job(job)
		self.assertTrue(self.worker.is_running(job))
		self.worker.stop_container(job)
		self.assertFalse(self.worker.is_running(job))

	def test_update_jobs(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.assertIsNewJob(self.mock_firefox, job)
		self.worker.update_jobs()
		self.assertIsNewJob(self.mock_firefox, job)
		self.worker.start_job(job)
		self.assertIsStartedJob(self.mock_firefox, job)
		self.worker.update_jobs()
		self.assertIsStartedJob(self.mock_firefox, job)
		self.worker.stop_container(job)
		self.assertNotEqual('DONE', job.status)
		self.worker.update_jobs()
		self.assertIn(job.status, ('DONE', 'ERROR'))

	def test_keep_hub_alive(self):
		self.assertEqual('running', self.worker.client.containers.get(self.worker.hub.id).status)
		self.worker.hub.stop()
		self.worker.keep_hub_alive()
		self.assertEqual('running', self.worker.client.containers.get(self.worker.hub.id).status)
		self.worker.hub.stop()
		self.worker.hub.remove()
		self.worker.keep_hub_alive()
		self.assertEqual('running', self.worker.client.containers.get(self.worker.hub.id).status)

	def test_before_start(self):
		job = copy.copy(self.mock_firefox)
		self.worker.jobs.append(job)
		self.assertEqual('PENDING', job.status)
		self.worker.before_start(job)
		self.assertEqual('STARTING', job.status)
		job.driver = 'edge'
		with self.assertRaises(TypeError):
			self.worker.before_start(job)
		job.driver = self.mock_firefox.driver
		return job

	def test_after_start(self):
		job = self.test_before_start()
		self.assertEqual('STARTING', job.status)
		self.worker.after_start(job)
		self.assertEqual('RUNNING', job.status)

	def assertIsStartedJob(self, mock, job, id=None):
		self.assertEqual(mock.driver, job.driver)
		self.assertEqual(mock.site, job.site)
		self.assertIsInstance(job.id, int)
		if id is not None:
			self.assertEqual(id, job.id)
		self.assertNotEqual('', job.container)
		self.assertEqual('', job.log)
		self.assertIn(job.status, ['STARTING', 'RUNNING', 'DONE'])
		self.assertIsNotNone(self.worker.client.containers.get(job.container).id)

	def assertIsNewJob(self, mock, job, id=None):
		self.assertEqual(mock.driver, job.driver)
		self.assertEqual(mock.site, job.site)
		self.assertIsInstance(job.id, int)
		if id is not None:
			self.assertEqual(id, job.id)
		self.assertEqual('', job.container)
		self.assertEqual('', job.log)
		self.assertEqual('PENDING', job.status)
		self.assertIsNotNone(job.log)
