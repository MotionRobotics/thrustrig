import plotly.subplots
from .sensors import TemperatureSensor, VoltAmpSensor, ThrustSensor

import threading
import datetime
import time
import os
import serial

import numpy as np
import pandas as pd

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc	
import plotly
	
sensors = []
collect_thread = None
columns = ['Timestamp', 'Coil Temperature (C)', 'Voltage (V)', 'Current (A)', 'Batt Temperature (C)', 'Thrust (N)']
data = []
data_lock = threading.Lock()

# Start dash app
app = Dash(__name__, assets_folder=os.path.join(os.path.dirname(__file__), 'assets'), external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
	html.H1('Thrust Rig'),
	html.Div([
		html.Button('Start', id='start-stop', n_clicks=0, className='fancy-button'),
		html.Button('Save', id='save', n_clicks=0, className='fancy-button'),
		html.Button('Config', id='cfg-btn', n_clicks=0, className='fancy-button'),
	], style={'display': 'inline-block', 'width': '100%', 'text-align': 'center'}),
	dcc.Interval(id='interval', interval=100, n_intervals=0, disabled=True),
	dcc.Download(id='download'),
	html.Br(),
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

stop_thread = False
def collect_data():
	global sensors, data, stop_thread
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
			data.append([timestamp] + readings)
		for sensor in sensors: sensor.flush()
		time.sleep(0.01)
		
# Callback to start/stop the data collection
@app.callback(
	Output('start-stop', 'children'),
	Output('cfg-btn', 'className'),
	Output('interval', 'disabled'),
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
	thrustbaudrate
	):
	global sensors, collect_thread, data, stop_thread
	if ctx.triggered_id == 'ok-error':
		if ok_err:
			return 'Start', 'fancy-button', True, '', False
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
		except serial.SerialException as e:
			sensors = []
			return 'Start', 'fancy-button', True, f'Error opening serial port: {e.strerror}', True
		collect_thread = threading.Thread(target=collect_data)
		collect_thread.start()
		return 'Stop', 'hide', False, '', False
	else:
		stop_thread = True
		if collect_thread is not None:
			collect_thread.join()
		collect_thread = None
		stop_thread = False
		for sensor in sensors: sensor.close()
		sensors = []
		return 'Start', 'fancy-button', True, '', False

def get_curval(val):
	if val is None:
		return ''
	return f'\t{val:.2f}'

# Callback to update the graph
@app.callback(
	Output('tempgraph', 'figure'),
	Input('interval', 'n_intervals'),
)
def update_tempgraph(id):
	global sensors, data, data_lock
	fig = plotly.subplots.make_subplots(rows=1, cols=1)
	with data_lock:
		ts = np.array([d[0] for d in data])
		temps = np.array([d[1] for d in data])

	fig.append_trace({
		'x': ts,
		'y': temps,
		'mode': 'lines',
		'name': 'Coil Temperature',
	}, 1, 1)
	curtemp = '' if len(temps) == 0 else get_curval(temps[-1])
	fig.update_layout(title=f'Coil Temperature vs Time{curtemp}', xaxis_title='Time', yaxis_title='Coil Temperature (C)', uirevision=0)

	return fig

@app.callback(
	[Output('voltgraph', 'figure'),
	Output('ampgraph', 'figure'),
	Output('batttempgraph', 'figure')],
	Input('interval', 'n_intervals'),
)
def update_battgraph(id):
	global sensors, data, data_lock
	voltfig = plotly.subplots.make_subplots(rows=1, cols=1)
	ampfig = plotly.subplots.make_subplots(rows=1, cols=1)
	batttempfig = plotly.subplots.make_subplots(rows=1, cols=1)
	with data_lock:
		if len(data) == 0:
			ts = np.array([])
			voltages = np.array([])
			currents = np.array([])
			batt_temps = np.array([])
		else:
			ts = np.array(data)[:, 0]
			voltages = np.array(data)[:, 2]
			currents = np.array(data)[:, 3]
			batt_temps = np.array(data)[:, 4]

	voltfig.append_trace({
		'x': ts,
		'y': voltages,
		'mode': 'lines',
		'name': 'Voltage',
	}, 1, 1)
	ampfig.append_trace({
		'x': ts,
		'y': currents,
		'mode': 'lines',
		'name': 'Current',
	}, 1, 1)
	batttempfig.append_trace({
		'x': ts,
		'y': batt_temps,
		'mode': 'lines',
		'name': 'Battery Temperature',
	}, 1, 1)
	
	curvolt = '' if len(voltages) == 0 else get_curval(voltages[-1])
	curamp = '' if len(currents) == 0 else get_curval(currents[-1])
	curbatttemp = '' if len(batt_temps) == 0 else get_curval(batt_temps[-1])

	voltfig.update_layout(title=f'Voltage vs Time{curvolt}', xaxis_title='Time', yaxis_title='Voltage', uirevision=0)
	ampfig.update_layout(title=f'Current vs Time{curamp}', xaxis_title='Time', yaxis_title='Current', uirevision=0)
	batttempfig.update_layout(title=f'Battery Temperature vs Time{curbatttemp}', xaxis_title='Time', yaxis_title='Battery Temperature (C)', uirevision=0)

	return voltfig, ampfig, batttempfig

@app.callback(
	Output('thrustgraph', 'figure'),
	Input('interval', 'n_intervals'),
)
def update_thrustgraph(id):
	global sensors, data, data_lock
	fig = plotly.subplots.make_subplots(rows=1, cols=1)
	with data_lock:
		if len(data) == 0:
			ts = np.array([])
			thrusts = np.array([])
		else:
			ts = np.array(data)[:, 0]
			thrusts = np.array(data)[:, 5]

	fig.append_trace({
		'x': ts,
		'y': thrusts,
		'mode': 'lines',
		'name': 'Thrust',
	}, 1, 1)

	curthrust = '' if len(thrusts) == 0 else get_curval(thrusts[-1])
 
	fig.update_layout(title=f'Thrust vs Time{curthrust}', xaxis_title='Time', yaxis_title='Thrust (N)', uirevision=0)

	return fig

# Callback to save the data
@app.callback(
	Output('download', 'data'),
	Input('save', 'n_clicks')
)
def save(n_clicks):
	global data
	if n_clicks:
		df = pd.DataFrame(data, columns=columns)
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
