import plotly.subplots
from .sensors import TemperatureSensor, VoltAmpSensor

import threading
import datetime
import time
import os

import numpy as np
import pandas as pd

import dash
from dash import Dash, dcc, html, Input, Output, State
import plotly
	
sensors = []
collect_thread = None
columns = ['Timestamp', 'Coil Temperature (C)', 'Voltage (V)', 'Current (A)', 'Batt Temperature (C)']
data = []
data_lock = threading.Lock()

# Start dash app
app = Dash(__name__)

# Add layout
# Inputs for temperature sensor port and baudrate
# Button to start/stop the data collection
# Graph to display the data
# Button to save the data
app.layout = html.Div([
	html.H1('Thrustrig', style={'text-align': 'center', 'color': 'blue'}),
	html.Div([
		html.Button('Start', id='start-stop', n_clicks=0, style={'display': 'inline-block', 'margin': '0 auto', 'font-size': '20px'}),
		html.Label('\t\t'),
		html.Button('Save', id='save', n_clicks=0, style={'display': 'inline-block', 'margin': '0 auto', 'font-size': '20px'}),
	], style={'display': 'inline-block', 'width': '100%', 'text-align': 'center'}),
	dcc.Interval(id='interval', interval=1000, n_intervals=0),
	dcc.Download(id='download'),
	html.Br(),
	html.Br(),
	html.Div([
		html.H2('Coil Temperature', style={'margin-top': '20px'}),
		html.Br(),
		html.Label('Port: '),
		dcc.Input(id='tempport', type='text', value='/dev/ttyUSB0'),
		html.Br(),
		html.Label('Baudrate: '),
		dcc.Input(id='tempbaudrate', type='number', value=115200),
		dcc.Graph(id='tempgraph'),
	], style={'display': 'inline-block', 'width': '47%', 'border': '1px solid black', 'margin': '10px', 'padding': '10px'}),
	html.Div([
		html.H2('Battery', style={'margin-top': '20px'}),
		html.Br(),
		html.Label('Port: '),
		dcc.Input(id='battport', type='text', value='/dev/ttyUSB1'),
		html.Br(),
		html.Label('Baudrate: '),
		dcc.Input(id='battbaudrate', type='number', value=115200),
		dcc.Graph(id='voltgraph'),
		dcc.Graph(id='ampgraph'),
		dcc.Graph(id='batttempgraph'),
	], style={'display': 'inline-block', 'width': '47%', 'border': '1px solid black', 'margin': '10px', 'padding': '10px'}),
])

stop_thread = False
def collect_data():
	global sensors, data, stop_thread
	while not stop_thread:
		timestamp = datetime.datetime.now()
		readings = []
		for sensor in sensors:
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
	Input('start-stop', 'n_clicks'),
	State('tempport', 'value'),
	State('tempbaudrate', 'value'),
	State('battport', 'value'),
	State('battbaudrate', 'value'),
	prevent_initial_call=True
)
def start_stop(n_clicks, tempport, tempbaudrate, battport, battbaudrate):
	global sensors, collect_thread, data, stop_thread
	if n_clicks % 2 == 1:
		sensors = [
			TemperatureSensor(tempport, tempbaudrate),
			VoltAmpSensor(battport, battbaudrate)
		]
		collect_thread = threading.Thread(target=collect_data)
		collect_thread.start()
		return 'Stop'
	else:
		stop_thread = True
		if collect_thread is not None:
			collect_thread.join()
		collect_thread = None
		stop_thread = False
		for sensor in sensors: sensor.close()
		sensors = []
		return 'Start'

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
	fig.update_layout(title='Coil Temperature vs Time', xaxis_title='Time', yaxis_title='Coil Temperature (C)')

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
	voltfig.update_layout(title='Voltage vs Time', xaxis_title='Time', yaxis_title='Voltage')
	ampfig.update_layout(title='Current vs Time', xaxis_title='Time', yaxis_title='Current')
	batttempfig.update_layout(title='Battery Temperature vs Time', xaxis_title='Time', yaxis_title='Battery Temperature (C)')

	return voltfig, ampfig, batttempfig

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

def main():
	app.run_server(debug=False)

if __name__ == '__main__':
	main()
