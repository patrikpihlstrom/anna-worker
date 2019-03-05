class Job(object):
	def __init__(self, id=0, driver='', site='', status='', tag='', container='', log='', host='', token=''):
		self.id = id
		self.driver = driver
		self.site = site
		self.status = status
		self.tag = tag
		self.container = container
		self.log = log
		self.host = host
		self.token = token
		self.changed = False

	def get_image_volumes_and_command(self):
		return ('patrikpihlstrom/anna-' + self.driver + ':latest', {'/tmp/anna/': {'bind': '/tmp', 'mode': 'rw'}},
		        'python3 /home/seluser/anna/anna/__main__.py -v -H -d ' + self.driver + ' -i ' + str(
			        self.id) + ' -s ' + self.site + ' -t ' + self.token + ' --host ' + self.host)

	def dict(self):
		return {'id': self.id, 'tag': self.tag, 'driver': self.driver,
		        'site': self.site, 'container': self.container,
		        'status': self.status, 'log': self.log}


attributes = ('id', 'container', 'driver', 'site', 'status', 'tag', 'log')
