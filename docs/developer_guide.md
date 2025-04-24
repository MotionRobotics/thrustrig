# Developer Guide

This document provides information for developers who want to extend, modify, or contribute to the Thrust Rig project.

## Project Structure

The Thrust Rig is structured as a Python package with the following organization:

```
thrustrig/
├── setup.py                 # Package installation configuration
├── README.md                # Main project documentation
├── docs/                    # Documentation files
│   ├── hardware_setup.md    # Hardware setup guide
│   └── sensor_configuration.md  # Sensor configuration guide
└── thrustrig/               # Main package directory
    ├── __init__.py          # Package initialization
    ├── main.py              # Application entry point and UI
    ├── pwm_driver.py        # PWM controller interface
    ├── utils.py             # Utility functions
    ├── assets/              # Web assets for the dashboard
    │   └── style.css        # CSS styling for the dashboard
    └── sensors/             # Sensor modules
        ├── __init__.py      # Sensor package initialization
        ├── rpm.py           # RPM sensor implementation
        ├── temperature.py   # Temperature sensor implementation
        ├── thrust.py        # Thrust sensor implementation
        └── voltamp.py       # Voltage/current sensor implementation
```

## Key Components

### main.py

The main application file contains:
- The Dash web application setup and UI layout
- Data collection thread management
- Configuration handling
- UI callbacks for interactivity

### Sensor Modules

Each sensor type has its own module:

- **temperature.py**: Interfaces with the temperature sensor
- **voltamp.py**: Interfaces with the voltage/current/battery temperature sensor
- **thrust.py**: Interfaces with the thrust sensor
- **rpm.py**: Interfaces with the RPM sensor via sigrok-cli

Each sensor class follows a common interface:
- `__init__()`: Initialize with connection parameters
- `start()`: Connect to the sensor
- `read()`: Read a value from the sensor
- `flush()`: Clear any buffered data
- `close()`: Disconnect from the sensor
- `enabled()`: Check if the sensor is connected and enabled

### pwm_driver.py

Handles communication with the PWM controller:
- `set(val)`: Set a specific PWM value
- `ramp(peak, step, period)`: Start a PWM ramp sequence
- `stop_ramp()`: Stop an active ramp sequence

### utils.py

Contains utility functions for the application:
- `time_it`: Decorator for function execution timing

## Adding a New Sensor

To add a new sensor type to the system:

1. Create a new module in the `sensors/` directory
2. Implement a class with the standard sensor interface
3. Update `sensors/__init__.py` to export your new sensor
4. Modify `main.py` to:
   - Add configuration parameters for the new sensor
   - Include the sensor in the sensors list
   - Add UI elements for configuration
   - Add a graph for visualization

Example of a new sensor module:

```python
import time

class NewSensor:
    n_vals = 1  # Number of values this sensor returns
    
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
        self.device = None
    
    def enabled(self):
        return self.device is not None
        
    def start(self):
        # Initialize connection to the sensor
        self.device = SomeLibrary.connect(self.param1, self.param2)
        
    def read(self):
        # Read and possibly process a value
        if not self.enabled():
            return None
        return self.device.get_value()
        
    def flush(self):
        # Clear any buffered data
        if self.enabled():
            self.device.flush()
            
    def close(self):
        # Clean up and disconnect
        if self.device is not None:
            self.device.disconnect()
            self.device = None
            
    def __del__(self):
        self.close()
```

## Modifying the UI

The UI is built using Dash, a Python framework for building web applications.

To modify the UI:

1. Locate the `app.layout` section in `main.py`
2. Add or modify the HTML and Dash components
3. For new interactive elements, add corresponding callbacks

Example of adding a new graph:

```python
# Add to the HTML layout
html.Div([
    # ... existing graphs
    dcc.Graph(id='newgraph', className='graph'),
], className='graph-panel')

# Add a callback for the new graph
@app.callback(
    Output('newgraph', 'figure'),
    Input('interval', 'n_intervals'),
)
def update_new_graph(n_intervals):
    global data, data_lock
    newfig = go.Figure()
    
    with data_lock:
        if len(data) == 0:
            newdata = np.array([])
        else:
            newdata = np.array(data)[:, new_column_index]
            
    newfig.add_trace(go.Line(x=np.array(data)[:, 0], y=newdata, mode='lines', name='New Data'))
    newfig.update_layout(title='New Data vs Time', xaxis_title='Time', yaxis_title='Units', uirevision=0)
    
    return newfig
```

## Data Storage

Data is handled as follows:

1. Data is stored in a NumPy array in memory
2. When the array reaches 1200 rows, the oldest 200 rows are written to a temporary CSV file
3. When saving data, both the in-memory data and the temporary file data are combined

If you need to modify the data storage:

1. Update the `columns` variable if adding new data fields
2. Modify the `collect_data()` function to handle new data sources
3. Update the data saving logic in the `save()` callback if needed

## Configuration Management

The configuration is stored as a JSON file in the user's home directory (`~/thrustrig.cfg`).

If adding new configuration options:

1. Add default values to the `config` dictionary in `main.py`
2. Add UI elements to the configuration modal
3. Update the configuration callback to handle the new options

## Running in Development Mode

For development:

1. Install the package in development mode:
   ```
   pip install -e .
   ```

2. Run the application directly from the source code:
   ```
   python -m thrustrig.main run
   ```
