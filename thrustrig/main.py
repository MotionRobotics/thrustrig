import threading
import datetime
import time
import os
import sys
import serial

import numpy as np
import pandas as pd

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc	
import plotly
import plotly.subplots
import plotly.graph_objects as go

from .sensors import TemperatureSensor, VoltAmpSensor, ThrustSensor
from .pwm_driver import PWMDriver
	
sensors = []
pwmdriver = None
collect_thread = None
columns = ['Timestamp', 'Coil Temperature (C)', 'Voltage (V)', 'Current (A)', 'Batt Temperature (C)', 'Thrust (N)']
data = np.ndarray(shape=(0, len(columns)))
data_lock = threading.Lock()

# Start dash app
app = Dash(__name__, assets_folder=os.path.join(os.path.dirname(__file__), 'assets'), external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
	html.H1('Thrust Rig'),
	html.Div([
		html.Button('Start', id='start-stop', n_clicks=0, className='fancy-button'),
		html.Button('Save', id='save', n_clicks=0, className='fancy-button'),
		html.Button('Config', id='cfg-btn', n_clicks=0, className='fancy-button'),
		html.Label('', id='data-mem')
	], style={'display': 'inline-block', 'width': '100%', 'text-align': 'center'}),
	dcc.Interval(id='interval', interval=100, n_intervals=0, disabled=True),
	dcc.Download(id='download'),
	html.Br(),
	html.Br(),
	dbc.Row([
		dbc.Col(html.Label('PWM Value: '), style={'text-align': 'right'}),
		dbc.Col(dcc.Slider(id='pwm-slider', min=0, max=200, step=1, value=0, marks={
				0: '0',
				50: '50',
				100: '100',
				150: '150',
				200: '200',
			}, disabled=True)),
		dbc.Col(html.Label('0', id='pwm-val', style={'display': 'inline-block', 'margin-left': '10px'})),
	], align='center'),
	html.Br(),
	html.Div([
		dcc.Graph(id='tempgraph', className='graph'),
		dcc.Graph(id='voltgraph', className='graph'),
		dcc.Graph(id='ampgraph', className='graph'),
		dcc.Graph(id='batttempgraph', className='graph'),
		dcc.Graph(id='thrustgraph', className='graph'),
	], className='graph-panel'),
	dbc.Modal([
			dbc.ModalHeader(dbc.ModalTitle('Configuration'), close_button=False),
			dbc.ModalBody([
				html.H3('Coil Temperature', style={'margin-top': '20px'}),
				html.Br(),
				dcc.Checklist(['Enable'], ['Enable'], id='temp-enable'),
				html.Br(),
				html.Label('Port: '),
				dcc.Input(id='tempport', type='text', value='/dev/ttyUSB0'),
				html.Br(),
				html.Label('Baudrate: '),
				dcc.Input(id='tempbaudrate', type='number', value=115200),
		
				html.H3('Battery', style={'margin-top': '20px'}),
				html.Br(),
				dcc.Checklist(['Enable'], ['Enable'], id='batt-enable'),
				html.Br(),
				html.Label('Port: '),
				dcc.Input(id='battport', type='text', value='/dev/ttyUSB1'),
				html.Br(),
				html.Label('Baudrate: '),
				dcc.Input(id='battbaudrate', type='number', value=115200),
		
				html.H3('Thrust', style={'margin-top': '20px'}),
				html.Br(),
				dcc.Checklist(['Enable'], ['Enable'], id='thrust-enable'),
				html.Br(),
				html.Label('Port: '),
				dcc.Input(id='thrustport', type='text', value='/dev/ttyUSB2'),
				html.Br(),
				html.Label('Baudrate: '),
				dcc.Input(id='thrustbaudrate', type='number', value=115200),
    
				html.H3('PWM Driver', style={'margin-top': '20px'}),
				html.Br(),
				dcc.Checklist(['Enable'], ['Enable'], id='pwm-enable'),
				html.Br(),
				html.Label('Port: '),
				dcc.Input(id='pwmdriverport', type='text', value='/dev/ttyUSB3'),
				html.Br(),
				html.Label('Baudrate: '),
				dcc.Input(id='pwmdriverbaudrate', type='number', value=115200),
			]),
			dbc.ModalFooter([
				html.Button('Ok', id='ok-config', n_clicks=0, className='fancy-button'),
			]),
		],
		id='config-modal',
		is_open=False,
		keyboard=True,
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

if os.name == 'posix':
	tmpfile = os.path.join(os.environ['TEMP'], 'tmp.csv')
elif os.name == 'nt':
	tmpfile = os.path.join(os.environ['TEMP'], 'tmp.csv')

with open(tmpfile, 'w') as f:
	f.write(', '.join(columns) + '\n')

stop_thread = False
def collect_data():
	global sensors, data, stop_thread, tmpfile
	while not stop_thread:
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
		time.sleep(0.01)
		
# Callback to start/stop the data collection
@app.callback(
	Output('start-stop', 'children'),
	Output('cfg-btn', 'className'),
	Output('interval', 'disabled'),
	Output('pwm-slider', 'disabled'),
	Output('pwm-slider', 'value', allow_duplicate=True),
	Output('pwm-val', 'children', allow_duplicate=True),
	Output('error-msg', 'children'),
	Output('error-modal', 'is_open'),
	Input('start-stop', 'n_clicks'),
	Input('ok-error', 'n_clicks'),
	State('temp-enable', 'value'),
	State('tempport', 'value'),
	State('tempbaudrate', 'value'),
	State('batt-enable', 'value'),
	State('battport', 'value'),
	State('battbaudrate', 'value'),
	State('thrust-enable', 'value'),
	State('thrustport', 'value'),
	State('thrustbaudrate', 'value'),
	State('pwm-enable', 'value'),
	State('pwmdriverport', 'value'),
	State('pwmdriverbaudrate', 'value'),
	prevent_initial_call=True
)
def start_stop(
    start_stop,
    ok_err,
    tempenable,
    tempport,
    tempbaudrate,
	battenable,
    battport,
    battbaudrate,
	thrustenable,
	thrustport,
	thrustbaudrate,
	pwmenable,
	pwmdriverport,
	pwmdriverbaudrate
	):
	global sensors, collect_thread, data, stop_thread, pwmdriver
	if ctx.triggered_id == 'ok-error':
		if ok_err:
			return 'Start', 'fancy-button', True, True, 0, '0', '', False
	if start_stop % 2 == 1:
		sensors = [
			TemperatureSensor(tempport, tempbaudrate),
			VoltAmpSensor(battport, battbaudrate),
			ThrustSensor(thrustport, thrustbaudrate),
		]
		try:
			if 'Enable' in tempenable:
				sensors[0].start()
			if 'Enable' in battenable:
				sensors[1].start()
			if 'Enable' in thrustenable:
				sensors[2].start()
			if 'Enable' in pwmenable:
				pwmdriver = PWMDriver(pwmdriverport, pwmdriverbaudrate)
				pwmdriver.start()
		except serial.SerialException as e:
			sensors = []
			pwmdriver = None
			return 'Start', 'fancy-button', True, True, 0, '0', f'Error opening serial port: {e.strerror}', True
		collect_thread = threading.Thread(target=collect_data)
		collect_thread.start()
		return 'Stop', 'hide', False, False, 0, '0', '', False
	else:
		stop_thread = True
		if collect_thread is not None:
			collect_thread.join()
		collect_thread = None
		stop_thread = False
		for sensor in sensors: sensor.close()
		sensors = []
		if pwmdriver is not None:
			pwmdriver.set(0)
			time.sleep(0.1)
			pwmdriver.close()
			del pwmdriver
			pwmdriver = None
		return 'Start', 'fancy-button', True, True, 0, '0', '', False

# Callback to update the PWM value
@app.callback(
	Output('pwm-slider', 'value'),
	Output('pwm-val', 'children'),
	Input('pwm-slider', 'value'),
)
def update_pwm(val):
	global pwmdriver
	if pwmdriver is None:
		return 0, '0'
	pwmdriver.set(val)
	return val, str(val * 10)

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
	Output('data-mem', 'children'),
	Input('interval', 'n_intervals'),
)
def update_tempgraph(id):
	global sensors, data, data_lock

	# tempfig = plotly.subplots.make_subplots(rows=1, cols=1)
	# voltfig = plotly.subplots.make_subplots(rows=1, cols=1)
	# ampfig = plotly.subplots.make_subplots(rows=1, cols=1)
	# batttempfig = plotly.subplots.make_subplots(rows=1, cols=1)
	# thrustfig = plotly.subplots.make_subplots(rows=1, cols=1)
 
	tempfig = go.Figure()
	voltfig = go.Figure()
	ampfig = go.Figure()
	batttempfig = go.Figure()
	thrustfig = go.Figure()

	with data_lock:
		if len(data) == 0:
			ts = np.array([])
			temps = np.array([])
			voltages = np.array([])
			currents = np.array([])
			batt_temps = np.array([])
			thrusts = np.array([])
		else:
			npd = np.array(data)
			ts = npd[:, 0]
			temps = npd[:, 1]
			voltages = npd[:, 2]
			currents = npd[:, 3]
			batt_temps = npd[:, 4]
			thrusts = npd[:, 5]

	# tempfig.append_trace({
	# 	'x': ts,
	# 	'y': temps,
	# 	'mode': 'lines',
	# 	'name': 'Coil Temperature',
	# }, 1, 1)

	# voltfig.append_trace({
	# 	'x': ts,
	# 	'y': voltages,
	# 	'mode': 'lines',
	# 	'name': 'Voltage',
	# }, 1, 1)
	# ampfig.append_trace({
	# 	'x': ts,
	# 	'y': currents,
	# 	'mode': 'lines',
	# 	'name': 'Current',
	# }, 1, 1)
	# batttempfig.append_trace({
	# 	'x': ts,
	# 	'y': batt_temps,
	# 	'mode': 'lines',
	# 	'name': 'Battery Temperature',
	# }, 1, 1)

	# thrustfig.append_trace({
	# 	'x': ts,
	# 	'y': thrusts,
	# 	'mode': 'lines',
	# 	'name': 'Thrust',
	# }, 1, 1)
 
	tempfig.add_trace(go.Line(x=ts, y=temps, mode='lines', name='Coil Temperature'))
	voltfig.add_trace(go.Line(x=ts, y=voltages, mode='lines', name='Voltage'))
	ampfig.add_trace(go.Line(x=ts, y=currents, mode='lines', name='Current'))
	batttempfig.add_trace(go.Line(x=ts, y=batt_temps, mode='lines', name='Battery Temperature'))
	thrustfig.add_trace(go.Line(x=ts, y=thrusts, mode='lines', name='Thrust'))
	
	curtemp = '' if len(temps) == 0 else get_curval(temps[-1])
	curvolt = '' if len(voltages) == 0 else get_curval(voltages[-1])
	curamp = '' if len(currents) == 0 else get_curval(currents[-1])
	curbatttemp = '' if len(batt_temps) == 0 else get_curval(batt_temps[-1])
	curthrust = '' if len(thrusts) == 0 else get_curval(thrusts[-1])

	voltfig.update_layout(title=f'Voltage vs Time{curvolt}', xaxis_title='Time', yaxis_title='Voltage', uirevision=0)
	ampfig.update_layout(title=f'Current vs Time{curamp}', xaxis_title='Time', yaxis_title='Current', uirevision=0)
	batttempfig.update_layout(title=f'Battery Temperature vs Time{curbatttemp}', xaxis_title='Time', yaxis_title='Battery Temperature (C)', uirevision=0)
	tempfig.update_layout(title=f'Coil Temperature vs Time{curtemp}', xaxis_title='Time', yaxis_title='Coil Temperature (C)', uirevision=0)
	thrustfig.update_layout(title=f'Thrust vs Time{curthrust}', xaxis_title='Time', yaxis_title='Thrust (N)', uirevision=0)
 
	with data_lock:
		mem_used = sys.getsizeof(data) / 1024
	return tempfig, voltfig, ampfig, batttempfig, thrustfig, f'Memory used: {mem_used:.2f} KB'

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
		df = pd.concat([tmpdf, df])
		csv_str = df.to_csv(index=False)
		return dict(content=csv_str, filename='data.csv')

# Callback to show the configuration modal
@app.callback(
	Output('config-modal', 'is_open'),
	Input('cfg-btn', 'n_clicks'),
	Input('ok-config', 'n_clicks'),
	State('config-modal', 'is_open'),
	prevent_initial_call=True
)
def config_modal(config_clicks, ok_clicks, is_open):
	if config_clicks or ok_clicks:
		return not is_open
	return is_open

def main():
	app.run_server(debug=False)

if __name__ == '__main__':
	main()
