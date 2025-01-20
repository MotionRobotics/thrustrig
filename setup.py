# Setup script to install the package as a command line tool

from setuptools import setup

setup(
    name='thrustrig',
	version='0.0.1',
	packages=['thrustrig'],
	install_requires=[
		'numpy',
		'pandas',
		'dash',
		'pyserial'
	],
	entry_points={
		'console_scripts': [
			'thrustrig = thrustrig.main:main'
		]
	},
)
