import os


class Job(object):
	def __init__(self, id=0, driver='', site='', status='', tag='', container='', log=''):
		self.id = id
		self.driver = driver
		self.site = site
		self.status = status
		self.tag = tag
		self.container = container
		self.log = log
		self.changed = False

	def get_image_volumes_and_command(self):
		return ('patrikpihlstrom/anna-' + self.driver + ':latest', {'/tmp/anna/': {'bind': '/tmp', 'mode': 'rw'}},
		        'python3 /home/seluser/anna/anna/__main__.py -v -H -d ' + self.driver + ' -s ' + self.site + ' --token ' +
		        os.environ['ANNA_TOKEN'] + ' --host ' + os.environ['ANNA_HOST'])

	def dict(self):
		return {'id': self.id, 'tag': self.tag, 'driver': self.driver,
		        'site': self.site, 'container': self.container,
		        'status': self.status, 'log': self.log}


attributes = ('id', 'container', 'driver', 'site', 'status', 'tag', 'log')
