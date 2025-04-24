# Thrust Rig

A comprehensive data acquisition and control system for motor thrust testing designed to work with various sensors for temperature, voltage, current, thrust, and RPM measurements.

## Overview

The Thrust Rig is designed for collecting and analyzing data from electric motor test stands. It provides:

- Real-time data visualization of multiple sensor readings
- PWM control for motor speed adjustment 
- Data recording for later analysis
- Configurable sensors and connections
- Automated ramping for controlled testing sequences

## Features

- **Multi-sensor Support**:
  - Coil temperature monitoring
  - Battery voltage and current monitoring
  - Battery temperature monitoring
  - Thrust measurement
  - RPM measurement
  
- **Real-time Data Visualization**:
  - Six concurrent graphs displaying all sensor readings
  - Current values displayed on graphs
  
- **PWM Control**:
  - Manual control via slider (1000-2000 μs PWM values)
  - Automated ramping with configurable peak, step size, and duration
  
- **Data Management**:
  - Save recorded data to CSV file
  - Memory-efficient storage for extended recording sessions
  
- **Configurable Setup**:
  - All sensor parameters configurable through UI
  - Calibration tools for thrust sensor
  - Serial port and baudrate settings for each component

## Installation

### Prerequisites

- Python 3.6+
- pip
- Git
- [sigrok-cli](https://sigrok.org/wiki/Downloads) for RPM measurement (optional)

### Install from Source

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd thrustrig
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Install the sigrok-cli tool (optional, for RPM measurement):
   - **Linux**: Follow the instructions at [sigrok.org Linux packages](https://sigrok.org/wiki/Downloads#Linux_distribution_packages)
   - **Windows**: Follow the instructions at [sigrok.org Windows packages](https://sigrok.org/wiki/Downloads#windows)

## Usage

### Starting the Application

Run the application:
```bash
thrustrig run
```

Update the application (if installed from git):
```bash
thrustrig update
```

### Basic Operation

1. **Configure Sensors**:
   - Click the "Config" button
   - Enable/disable sensors as needed
   - Set port/baudrate for each sensor
   - Configure calibration values for thrust sensor
   - Set path to sigrok-cli for RPM measurement
   - Click "Ok" to save configuration

2. **Start Data Collection**:
   - Click "Start" to begin collecting data
   - Real-time graphs will update with sensor readings

3. **Control PWM**:
   - Use the slider to manually control PWM value (1000-2000)
   - Or use the PWM Ramp feature for automated control:
     - Set peak value, step size, and duration
     - Click "Start" to begin the ramp sequence
     - Click "Stop" to interrupt the sequence

4. **Save Data**:
   - Click "Save" to download all collected data as a CSV file

5. **Reset**:
   - Click "Reset" to clear all data and start fresh

## Configuration

The configuration is stored in `~/thrustrig.cfg` and includes:

- Serial port settings for each sensor
- Calibration values for thrust sensor
- Path to sigrok-cli tool
- Enable/disable status for each sensor
