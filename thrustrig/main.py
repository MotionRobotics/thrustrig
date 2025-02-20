import threading
import datetime
import time
import os
import sys
import serial
import json
import argparse
import subprocess
import re

import numpy as np
import pandas as pd

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc	
import plotly
import plotly.subplots
import plotly.graph_objects as go

from .sensors import TemperatureSensor, VoltAmpSensor, ThrustSensor, RPMSensor
from .pwm_driver import PWMDriver

sensors = []
pwmdriver = None
collect_thread = None
columns = ['Timestamp', 'Coil Temperature (C)', 'Voltage (V)', 'Current (A)', 'Batt Temperature (C)', 'Thrust (N)', 'RPM', 'PWM']
data = np.ndarray(shape=(0, len(columns)))
data_lock = threading.Lock()

sigrokcli_dl = 'https://sigrok.org/wiki/Downloads'
if os.name == 'posix':
	sigrokcli_dl = 'https://sigrok.org/wiki/Downloads#Linux_distribution_packages'
elif os.name == 'nt':
	sigrokcli_dl = 'https://sigrok.org/wiki/Downloads#windows'

config = {
	'temp': {
		'enable': True,
		'port': '/dev/ttyUSB0',
		'baudrate': 115200
	},
	'batt': {
		'enable': True,
		'port': '/dev/ttyUSB1',
		'baudrate': 115200
	},
	'thrust': {
		'enable': True,
		'port': '/dev/ttyUSB2',
		'baudrate': 115200,
		'offset': 991.5,
		'scale': 117.6,
		'senlen': 85,
		'efflen': 114
	},
	'rpm': {
		'enable': True,
		'sigrokpath': os.environ['HOME'] + '/sigrok-cli'
	},
	'pwm': {
		'enable': True,
		'port': '/dev/ttyUSB3',
		'baudrate': 115200
	}
}

config_path = os.path.join(os.environ['HOME'], 'thrustrig.cfg')

if os.path.isfile(config_path):
	with open(config_path, 'r') as f:
		new_config = json.load(f)
		for key in new_config:
			config[key].update(new_config[key])

if os.name == 'posix':
	tmpfile = os.path.join('/tmp', 'tmp.csv')
elif os.name == 'nt':
	tmpfile = os.path.join(os.environ['TEMP'], 'tmp.csv')

with open(tmpfile, 'w') as f:
	f.write(', '.join(columns) + '\n')

stop_thread = False
last_ts = None

sigchk = {
	'ok': ({'color': 'green'}, 'bi bi-check-circle-fill me-2'),
	'err': ({'color': 'red'}, 'bi bi-exclamation-triangle-fill me-2')
}

def create_app():
	# Start dash app
	app = Dash(
		__name__,
		assets_folder=os.path.join(os.path.dirname(__file__), 'assets'),
		external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
	)

	app.layout = html.Div([
		html.H1('Thrust Rig'),
		html.Div([
			html.Button('Reset', id='reset', n_clicks=0, className='fancy-button'),
			html.Button('Start', id='start-stop', n_clicks=0, className='fancy-button'),
			html.Button('Save', id='save', n_clicks=0, className='fancy-button'),
			html.Button('Config', id='cfg-btn', n_clicks=0, className='fancy-button'),
			html.Label('', id='data-mem')
		], style={'display': 'inline-block', 'width': '100%', 'text-align': 'center'}),
		dcc.Interval(id='interval', interval=500, n_intervals=0, disabled=True),
		dcc.Download(id='download'),
		html.Br(),
		html.Br(),
		dbc.Row([
			dbc.Col(html.Label('PWM Value: '), style={'text-align': 'right'}),
			dbc.Col(dcc.Slider(id='pwm-slider', min=1000, max=2000, step=50, value=0, marks={v: str(v) for v in range(1000, 2050, 50)}, disabled=True)),
			dbc.Col(html.Label('0', id='pwm-val', style={'display': 'inline-block', 'margin-left': '10px'})),
		], align='center'),
		html.Br(),
		dbc.Row([
			# PWM Ramp driver
			dbc.Col([html.Label('PWM Ramp: ', style={'font-size': '1.5em'})], style={'text-align': 'right'}),
			dbc.Col([html.Label('Peak (1000-2000): ')], style={'text-align': 'right'}),
			dbc.Col([dcc.Input(id='pwm-peak', type='number', value=200, persistence=True)]),
			dbc.Col([html.Label('Step size: ')], style={'text-align': 'right'}),
			dbc.Col([dcc.Input(id='pwm-steps', type='number', value=20, persistence=True)]),
			dbc.Col([html.Label('Step duration (s): ')], style={'text-align': 'right'}),
			dbc.Col([dcc.Input(id='pwm-period', type='number', value=1, persistence=True)]),
			dbc.Col([html.Button('Start', id='start-ramp', n_clicks=0, className='fancy-button')]),
			dbc.Col([html.Button('Stop', id='stop-ramp', n_clicks=0, className='fancy-button')]),
			dcc.Interval(id='ramp-interval', interval=250, n_intervals=0, disabled=True),
		], align='center'),
		html.Br(),
		html.Div([
			dcc.Graph(id='tempgraph', className='graph'),
			dcc.Graph(id='voltgraph', className='graph'),
			dcc.Graph(id='ampgraph', className='graph'),
			dcc.Graph(id='batttempgraph', className='graph'),
			dcc.Graph(id='thrustgraph', className='graph'),
			dcc.Graph(id='rpmgraph', className='graph'),
		], className='graph-panel'),
		dbc.Modal([
				dbc.ModalHeader(dbc.ModalTitle('Configuration'), close_button=False),
				dbc.ModalBody([
					html.H3('Coil Temperature', style={'margin-top': '20px'}),
					html.Br(),
					dcc.Checklist(['Enable'], ['Enable'] if config['temp']['enable'] else [], id='temp-enable', persistence=True),
					html.Br(),
					html.Label('Port: '),
					dcc.Input(id='tempport', type='text', value=config['temp']['port'], persistence=True),
					html.Br(),
					html.Label('Baudrate: '),
					dcc.Input(id='tempbaudrate', type='number', value=config['temp']['baudrate'], persistence=True),
			
					html.H3('Battery', style={'margin-top': '20px'}),
					html.Br(),
					dcc.Checklist(['Enable'], ['Enable'] if config['batt']['enable'] else [], id='batt-enable', persistence=True),
					html.Br(),
					html.Label('Port: '),
					dcc.Input(id='battport', type='text', value=config['batt']['port'], persistence=True),
					html.Br(),
					html.Label('Baudrate: '),
					dcc.Input(id='battbaudrate', type='number', value=config['batt']['baudrate'], persistence=True),
			
					html.H3('Thrust', style={'margin-top': '20px'}),
					html.Br(),
					dcc.Checklist(['Enable'], ['Enable'] if config['thrust']['enable'] else [], id='thrust-enable', persistence=True),
					html.Br(),
					html.Label('Port: '),
					dcc.Input(id='thrustport', type='text', value=config['thrust']['port'], persistence=True),
					html.Br(),
					html.Label('Baudrate: '),
					dcc.Input(id='thrustbaudrate', type='number', value=config['thrust']['baudrate'], persistence=True),
					html.Br(),
					html.Label('Offset: '),
					dcc.Input(id='thrustoffset', type='number', value=config['thrust']['offset'], persistence=True),
					html.Button('Tare', id='tare-thrust', n_clicks=0, className='fancy-button'),
					html.Br(),
					html.Label('Scale: '),
					dcc.Input(id='thrustscale', type='number', value=config['thrust']['scale'], persistence=True),
					html.Button('Calibrate', id='calibrate-thrust', n_clicks=0, className='fancy-button', disabled=True),
					html.Br(),
					html.Label('Sensor arm length: '),
					dcc.Input(id='thrustsenlen', type='number', value=config['thrust']['senlen'], persistence=True),
					html.Br(),
					html.Label('Effector arm length: '),
					dcc.Input(id='thrustefflen', type='number', value=config['thrust']['efflen'], persistence=True),
		
					html.H3('RPM Sensor', style={'margin-top': '20px'}),
					html.Br(),
					dcc.Checklist(['Enable'], ['Enable'] if config['rpm']['enable'] else [], id='rpm-enable', persistence=True),
					html.Br(),
					html.Label('Path to sigrok-cli: '),
					dcc.Input(id='sigrokpath', type='text', value=config['rpm']['sigrokpath'], persistence=True),
					html.I(className='bi bi-check-circle-fill me-2', id='sigrok-check', style={'color': 'green'}),
					html.Br(),
					html.A('Download sigrok-cli', href=sigrokcli_dl, target='_blank'),
		
					html.H3('PWM Driver', style={'margin-top': '20px'}),
					html.Br(),
					dcc.Checklist(['Enable'], ['Enable'] if config['pwm']['enable'] else [], id='pwm-enable', persistence=True),
					html.Br(),
					html.Label('Port: '),
					dcc.Input(id='pwmdriverport', type='text', value=config['pwm']['port'], persistence=True),
					html.Br(),
					html.Label('Baudrate: '),
					dcc.Input(id='pwmdriverbaudrate', type='number', value=config['pwm']['baudrate'], persistence=True),
				]),
				dbc.ModalFooter([
					html.Button('Ok', id='ok-config', n_clicks=0, className='fancy-button'),
				]),
			],
			id='config-modal',
			is_open=False,
			keyboard=False,
			size='lg',
		),
		dbc.Modal([
				dbc.ModalHeader(dbc.ModalTitle('Error'), close_button=False),
				dbc.ModalBody([
					html.P(id='error-msg'),
				]),
				dbc.ModalFooter([
					html.Button('Ok', id='ok-error', n_clicks=0, className='fancy-button'),
				]),
			],
			id='error-modal',
			is_open=False,
			keyboard=True,
		),
	])
 
	def collect_data():
		global sensors, data, stop_thread, tmpfile, last_ts
		while not stop_thread:
			if last_ts is not None and (datetime.datetime.now() - last_ts).total_seconds() < 0.5:
				time.sleep(0.1)
				continue
			timestamp = datetime.datetime.now()
			readings = []
			for sensor in sensors:
				if not sensor.enabled():
					readings.extend([None] * sensor.n_vals)
					continue
				reading = sensor.read()
				if isinstance(reading, (list, tuple)):
					readings.extend(reading)
				else:
					readings.append(reading)
			readings.append(None if pwmdriver is None else pwmdriver.val)
			if len(readings) != len(columns) - 1:
				continue
			with data_lock:
				data = np.vstack([data, np.array([timestamp] + readings)])
				if len(data) > 1200:
					with open(tmpfile, 'a') as f:
						arch = data[:200]
						data = data[200:]
						for line in arch:
							f.write(', '.join(['' if val is None else str(val) for val in line]) + '\n')
			for sensor in sensors: sensor.flush()
			last_ts = timestamp
			
	# Callback to reset the data
	@app.callback(
		Output('interval', 'n_intervals'),
		Input('reset', 'n_clicks'),
		prevent_initial_call=True
	)
	def reset_data(reset):
		global data
		with data_lock:
			data = np.ndarray(shape=(0, len(columns)))
	
		if os.path.isfile(tmpfile):
			os.remove(tmpfile)
			with open(tmpfile, 'w') as f:
				f.write(', '.join(columns) + '\n')
	
		return 0
	
	# Callback to start/stop the data collection
	@app.callback(
		Output('start-stop', 'children'),
		Output('cfg-btn', 'className'),
		Output('interval', 'disabled'),
		Output('pwm-slider', 'disabled'),
		Output('pwm-slider', 'value', allow_duplicate=True),
		Output('pwm-val', 'children', allow_duplicate=True),
		Output('start-ramp', 'disabled', allow_duplicate=True),
		Output('ramp-interval', 'disabled', allow_duplicate=True),
		Output('error-msg', 'children', allow_duplicate=True),
		Output('error-modal', 'is_open', allow_duplicate=True),
		Input('start-stop', 'n_clicks'),
		prevent_initial_call=True
	)
	def start_stop(
		start_stop,
		):
		global sensors, collect_thread, data, stop_thread, pwmdriver
		if start_stop % 2 == 1:
			sensors = [
				TemperatureSensor(config['temp']['port'], config['temp']['baudrate']),
				VoltAmpSensor(config['batt']['port'], config['batt']['baudrate']),
				ThrustSensor(
					config['thrust']['port'],
					config['thrust']['baudrate'],
					config['thrust']['offset'],
					config['thrust']['scale'],
					config['thrust']['senlen'],
					config['thrust']['efflen']
				),
				RPMSensor(config['rpm']['sigrokpath'])
			]
			try:
				if config['temp']['enable']:
					sensors[0].start()
				if config['batt']['enable']:
					sensors[1].start()
				if config['thrust']['enable']:
					sensors[2].start()
				if config['rpm']['enable']:
					sensors[3].start()
				if config['pwm']['enable']:
					pwmdriver = PWMDriver(config['pwm']['port'], config['pwm']['baudrate'])
					pwmdriver.start()
			except serial.SerialException as e:
				sensors = []
				pwmdriver = None
				return 'Start', 'fancy-button', True, True, 0, '0', True, True, f'Error opening serial port: {e.strerror}', True
			except ValueError:
				sensors = []
				pwmdriver = None
				return 'Start', 'fancy-button', True, True, 0, '0', True, True, 'Check path to sigrok-cli', True
			collect_thread = threading.Thread(target=collect_data)
			collect_thread.start()
			return 'Stop', 'hide', False, False, 0, '0', False, True, '', False
		else:
			stop_thread = True
			if collect_thread is not None:
				collect_thread.join()
			collect_thread = None
			stop_thread = False
			for sensor in sensors: sensor.close()
			sensors = []
			if pwmdriver is not None:
				pwmdriver.set(1000)
				time.sleep(0.1)
				pwmdriver.close()
				del pwmdriver
				pwmdriver = None
			return 'Start', 'fancy-button', True, True, 0, '0', True, True, '', False

	# Callback to close the error modal
	@app.callback(
		Output('error-modal', 'is_open', allow_duplicate=True),
		Input('ok-error', 'n_clicks'),
		prevent_initial_call=True
	)
	def close_error(n_clicks):
		if n_clicks:
			return False
		return True

	# Callback to tare the thrust sensor
	@app.callback(
		Output('thrustoffset', 'value'),
		Output('error-modal', 'is_open', allow_duplicate=True),
		Output('error-msg', 'children'),
		Input('tare-thrust', 'n_clicks'),
		State('thrustoffset', 'value'),
		prevent_initial_call=True
	)
	def tare_thrust(
		n_clicks,
		offset
		):
		thrustsensor = ThrustSensor(config['thrust']['port'], config['thrust']['baudrate'])
		try:
			thrustsensor.start()
		except serial.SerialException as e:
			thrustsensor.close()
			return offset, True, f'Error opening serial port: {e.strerror}'
		time.sleep(0.1)
		vals = []
		for _ in range(10):
			val = thrustsensor.read()
			if val is not None:
				vals.append(val)
			time.sleep(0.1)
		thrustsensor.close()
		if len(vals) == 0:
			return offset, True, 'Error reading thrust sensor'
		offset = np.mean(vals)
		return offset, False, ''

	# Callback to update the PWM value
	@app.callback(
		Output('pwm-slider', 'value'),
		Output('pwm-val', 'children', allow_duplicate=True),
		Input('pwm-slider', 'value'),
		prevent_initial_call=True
	)
	def update_pwm(val):
		global pwmdriver
		if pwmdriver is None:
			return 1000, '1000'
		pwmdriver.set(val)
		return val, str(val)

	@app.callback(
		Output('start-ramp', 'disabled', allow_duplicate=True),
		Output('pwm-slider', 'disabled', allow_duplicate=True),
		Output('ramp-interval', 'disabled', allow_duplicate=True),
		Input('start-ramp', 'n_clicks'),
		State('pwm-peak', 'value'),
		State('pwm-steps', 'value'),
		State('pwm-period', 'value'),
		prevent_initial_call=True
	)
	def start_ramp(
		n_clicks,
		peak,
		steps,
		period
		):
		global pwmdriver
		if pwmdriver is None:
			return True, True, True
		if pwmdriver.ramp_active:
			pwmdriver.stop_ramp()
		pwmdriver.ramp(peak, steps, period)
		return True, True, False

	@app.callback(
		Output('start-ramp', 'disabled', allow_duplicate=True),
		Output('pwm-slider', 'disabled', allow_duplicate=True),
		Output('ramp-interval', 'disabled', allow_duplicate=True),
		Input('stop-ramp', 'n_clicks'),
		prevent_initial_call=True
	)
	def stop_ramp(n_clicks):
		global pwmdriver
		pwmdriver.stop_ramp()
		return False, False, True

	# Callback to update the PWM value
	@app.callback(
		Output('start-ramp', 'disabled', allow_duplicate=True),
		Output('pwm-slider', 'disabled', allow_duplicate=True),
		Output('ramp-interval', 'disabled', allow_duplicate=True),
		Output('pwm-val', 'children', allow_duplicate=True),
		Input('ramp-interval', 'n_intervals'),
		prevent_initial_call=True
	)
	def update_ramp(n_intervals):
		global pwmdriver
		if pwmdriver is None:
			return True, True, False, '1000'
		if pwmdriver.ramp_active:
			return True, True, False, str(pwmdriver.val)
		return False, False, True, str(pwmdriver.val)

	def get_curval(val):
		if val is None:
			return ''
		return f'\t{val:.2f}'

	# Callback to update the graph
	@app.callback(
		Output('tempgraph', 'figure'),
		Output('voltgraph', 'figure'),
		Output('ampgraph', 'figure'),
		Output('batttempgraph', 'figure'),
		Output('thrustgraph', 'figure'),
		Output('rpmgraph', 'figure'),
		Output('data-mem', 'children'),
		Input('interval', 'n_intervals'),
	)
	def update_graphs(id):
		global sensors, data, data_lock
	
		tempfig = go.Figure()
		voltfig = go.Figure()
		ampfig = go.Figure()
		batttempfig = go.Figure()
		thrustfig = go.Figure()
		rpmfig = go.Figure()

		with data_lock:
			if len(data) == 0:
				ts = np.array([])
				temps = np.array([])
				voltages = np.array([])
				currents = np.array([])
				batt_temps = np.array([])
				thrusts = np.array([])
				rpms = np.array([])
			else:
				npd = np.array(data)
				ts = npd[:, 0]
				temps = npd[:, 1]
				voltages = npd[:, 2]
				currents = npd[:, 3]
				batt_temps = npd[:, 4]
				thrusts = npd[:, 5]
				rpms = npd[:, 6]
	
		tempfig.add_trace(go.Line(x=ts, y=temps, mode='lines', name='Coil Temperature'))
		voltfig.add_trace(go.Line(x=ts, y=voltages, mode='lines', name='Voltage'))
		ampfig.add_trace(go.Line(x=ts, y=currents, mode='lines', name='Current'))
		batttempfig.add_trace(go.Line(x=ts, y=batt_temps, mode='lines', name='Battery Temperature'))
		thrustfig.add_trace(go.Line(x=ts, y=thrusts, mode='lines', name='Thrust'))
		rpmfig.add_trace(go.Line(x=ts, y=rpms, mode='lines', name='RPM'))
		
		curtemp = '' if len(temps) == 0 else get_curval(temps[-1])
		curvolt = '' if len(voltages) == 0 else get_curval(voltages[-1])
		curamp = '' if len(currents) == 0 else get_curval(currents[-1])
		curbatttemp = '' if len(batt_temps) == 0 else get_curval(batt_temps[-1])
		curthrust = '' if len(thrusts) == 0 else get_curval(thrusts[-1])
		currpm = '' if len(rpms) == 0 else get_curval(rpms[-1])

		voltfig.update_layout(title=f'Voltage vs Time{curvolt}', xaxis_title='Time', yaxis_title='Voltage', uirevision=0)
		ampfig.update_layout(title=f'Current vs Time{curamp}', xaxis_title='Time', yaxis_title='Current', uirevision=0)
		batttempfig.update_layout(title=f'Battery Temperature vs Time{curbatttemp}', xaxis_title='Time', yaxis_title='Battery Temperature (C)', uirevision=0)
		tempfig.update_layout(title=f'Coil Temperature vs Time{curtemp}', xaxis_title='Time', yaxis_title='Coil Temperature (C)', uirevision=0)
		thrustfig.update_layout(title=f'Thrust vs Time{curthrust}', xaxis_title='Time', yaxis_title='Thrust (N)', uirevision=0)
		rpmfig.update_layout(title=f'RPM vs Time{currpm}', xaxis_title='Time', yaxis_title='RPM', uirevision=0)
	
		with data_lock:
			mem_used = sys.getsizeof(data) / 1024
		return tempfig, voltfig, ampfig, batttempfig, thrustfig, rpmfig, f'Memory used: {mem_used:.2f} KB'

	# Callback to save the data
	@app.callback(
		Output('download', 'data'),
		Input('save', 'n_clicks')
	)
	def save(n_clicks):
		global data
		if n_clicks:
			tmpdf = pd.read_csv(tmpfile)
			df = pd.DataFrame(data, columns=columns)
			if len(tmpdf) > 0:
				df = pd.concat([tmpdf, df])
			csv_str = df.to_csv(index=False)
			return dict(content=csv_str, filename='data.csv')

	# Callback to show the configuration modal
	@app.callback(
		Output('config-modal', 'is_open', allow_duplicate=True),
		Output('sigrok-check', 'style', allow_duplicate=True),
		Output('sigrok-check', 'className', allow_duplicate=True),
		Input('cfg-btn', 'n_clicks'),
		State('config-modal', 'is_open'),
		State('sigrokpath', 'value'),
		prevent_initial_call=True
	)
	def config_modal(config_clicks, is_open, sigrokpath):
		global sigchk

		sigchk_style = None
		sigchk_class = None
		if os.path.isfile(sigrokpath):
			sigchk_style, sigchk_class = sigchk['ok']
		else:
			sigchk_style, sigchk_class = sigchk['err']

		if config_clicks:
			return True, sigchk_style, sigchk_class
		return False, sigchk_style, sigchk_class

	# Callback to close the configuration modal
	@app.callback(
		Output('config-modal', 'is_open'),
		Input('ok-config', 'n_clicks'),
		prevent_initial_call=True
	)
	def close_config(
		ok_clicks,
		):

		global config

		with open(config_path, 'w') as f:
			json.dump(config, f)

		if ok_clicks:
			return False
		return True

	@app.callback(
		Input('temp-enable', 'value'),
		Input('tempport', 'value'),
		Input('tempbaudrate', 'value'),
		Input('batt-enable', 'value'),
		Input('battport', 'value'),
		Input('battbaudrate', 'value'),
		Input('thrust-enable', 'value'),
		Input('thrustport', 'value'),
		Input('thrustbaudrate', 'value'),
		Input('thrustoffset', 'value'),
		Input('thrustscale', 'value'),
		Input('thrustsenlen', 'value'),
		Input('thrustefflen', 'value'),
		Input('rpm-enable', 'value'),
		Input('sigrokpath', 'value'),
		Input('pwm-enable', 'value'),
		Input('pwmdriverport', 'value'),
		Input('pwmdriverbaudrate', 'value')
	)
	def update_config(
		tempenable,
		tempport,
		tempbaudrate,
		battenable,
		battport,
		battbaudrate,
		thrustenable,
		thrustport,
		thrustbaudrate,
		thrustoffset,
		thrustscale,
		thrustsenlen,
		thrustefflen,
		rpmenable,
		sigrokpath,
		pwmenable,
		pwmdriverport,
		pwmdriverbaudrate
		):
		global config

		config['temp']['enable'] = 'Enable' in tempenable
		config['temp']['port'] = tempport
		config['temp']['baudrate'] = tempbaudrate

		config['batt']['enable'] = 'Enable' in battenable
		config['batt']['port'] = battport
		config['batt']['baudrate'] = battbaudrate

		config['thrust']['enable'] = 'Enable' in thrustenable
		config['thrust']['port'] = thrustport
		config['thrust']['baudrate'] = thrustbaudrate
		config['thrust']['offset'] = thrustoffset
		config['thrust']['scale'] = thrustscale
		config['thrust']['senlen'] = thrustsenlen
		config['thrust']['efflen'] = thrustefflen

		config['rpm']['enable'] = 'Enable' in rpmenable
		config['rpm']['sigrokpath'] = sigrokpath

		config['pwm']['enable'] = 'Enable' in pwmenable
		config['pwm']['port'] = pwmdriverport
		config['pwm']['baudrate'] = pwmdriverbaudrate

	@app.callback(
		Output('sigrok-check', 'style'),
		Output('sigrok-check', 'className'),
		Input('sigrokpath', 'value'),
		prevent_initial_call=True
	)
	def check_sigrokpath(path):
		if os.path.isfile(path):
			return sigchk['ok']
		return sigchk['err']

	return app

def main():

	# Parse command line arguments
	parser = argparse.ArgumentParser()

	parser.add_argument('command', choices=['run', 'update'], help='Command to run', default='run')
 
	args = parser.parse_args()
 
	# Check for update subcommand
	if args.command == 'update':
		# Run git pull on parent directory of thrustrig module
		result = subprocess.Popen(['git', 'pull'], cwd=os.path.dirname(os.path.dirname(__file__)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = result.communicate()
		if isinstance(out, bytes):
			out = out.decode()
		if isinstance(err, bytes):
			err = err.decode()
		if err:
			print(err)
			return
		if out:
			# Check if there are any changes
			no_updates = re.search(r'Already up-to-date', out)
			if no_updates:
				print('The app is already up-to-date')
			else:
				print('The app has been updated')
			return

	app = create_app()

	app.run_server(debug=False)

if __name__ == '__main__':
	main()
