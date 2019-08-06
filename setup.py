import setuptools

with open('README.md', 'r') as f:
    description = f.read()

setuptools.setup(
    name='anna-worker',
    version='0.0.13',
    author='Patrik Pihlstrom',
    author_email='patrik.pihlstrom@gmail.com',
    url='https://github.com/patrikpihlstrom/anna-worker',
    description='anna worker',
    long_description=description,
    long_description_content_type='text/markdown',
    packages=['anna_worker'],
    install_requires=['anna_client', 'docker']
)
