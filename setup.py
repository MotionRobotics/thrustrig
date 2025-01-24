# Setup script to install the package as a command line tool

from setuptools import setup, find_packages

setup(
    name='thrustrig',
	version='0.0.2',
	packages=find_packages(),
	install_requires=[
		'numpy',
		'pandas',
		'dash',
		'dash-bootstrap-components',
		'pyserial'
	],
	entry_points={
		'console_scripts': [
			'thrustrig = thrustrig.main:main'
		]
	},
)
