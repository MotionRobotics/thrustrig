# Sensor Configuration Guide

This document provides detailed information on configuring the sensors and components in the Thrust Rig system.

## Configuration File

The Thrust Rig application stores its configuration in `~/thrustrig.cfg`. This is a JSON file that contains settings for each sensor and component. The file is automatically created with default values when the application is first run and updated whenever you save changes in the configuration panel.

## Configuration Parameters

### Coil Temperature Sensor

```json
"temp": {
    "enable": true,
    "port": "/dev/ttyUSB0",
    "baudrate": 115200
}
```

- **enable**: Set to `true` to use this sensor, `false` to disable it
- **port**: The serial port the temperature sensor is connected to
- **baudrate**: Communication speed (default: 115200)

### Battery Monitoring Sensor

```json
"batt": {
    "enable": true,
    "port": "/dev/ttyUSB1",
    "baudrate": 115200
}
```

- **enable**: Set to `true` to use this sensor, `false` to disable it
- **port**: The serial port the battery monitoring sensor is connected to
- **baudrate**: Communication speed (default: 115200)

### Thrust Sensor

```json
"thrust": {
    "enable": true,
    "port": "/dev/ttyUSB2",
    "baudrate": 115200,
    "offset": 991.5,
    "scale": 117.6,
    "senlen": 85,
    "efflen": 114
}
```

- **enable**: Set to `true` to use this sensor, `false` to disable it
- **port**: The serial port the thrust sensor is connected to
- **baudrate**: Communication speed (default: 115200)
- **offset**: Tare value for zero thrust (use the "Tare" button to set this automatically)
- **scale**: Calibration factor to convert raw values to Newtons
- **senlen**: Sensor arm length in mm (for torque calculation)
- **efflen**: Effective arm length in mm (for torque calculation)

### RPM Sensor

```json
"rpm": {
    "enable": true,
    "sigrokpath": "/home/user/sigrok-cli"
}
```

- **enable**: Set to `true` to use this sensor, `false` to disable it
- **sigrokpath**: Full path to the sigrok-cli executable

### PWM Controller

```json
"pwm": {
    "enable": true,
    "port": "/dev/ttyUSB3",
    "baudrate": 115200
}
```

- **enable**: Set to `true` to use this controller, `false` to disable it
- **port**: The serial port the PWM controller is connected to
- **baudrate**: Communication speed (default: 115200)

## Configuration Through the UI

The Thrust Rig application provides a graphical interface for configuring all sensors. To access it:

1. Start the Thrust Rig application
2. Click the "Config" button (only available when data collection is not running)
3. Modify settings as needed
4. Click "Ok" to save the configuration

### Sensor Calibration

#### Thrust Sensor Calibration

The thrust sensor requires proper calibration for accurate measurements:

1. **Tare (Zero) Calibration**:
   - Remove all weight/force from the thrust sensor
   - In the Configuration panel, click the "Tare" button next to the Offset field
   - This will automatically measure and set the zero point

2. **Scale Calibration**:
   - Apply a known force to the thrust sensor (e.g., hang a calibrated weight)
   - Calculate the appropriate scale factor: `scale = (raw_value - offset) / known_force_in_newtons`
   - Enter this value in the "Scale" field

3. **Arm Length Configuration**:
   - Measure the distance from the pivot point to the sensor attachment point (senlen)
   - Measure the distance from the pivot point to the motor/thrust point (efflen)
   - These values are used to correctly calculate the thrust based on the different lever arms

#### Finding Correct Serial Ports

On Linux systems, you can find the serial ports for your devices:

```bash
ls -l /dev/ttyUSB*
```

To identify which device is which:

1. Disconnect all serial devices
2. Connect one device at a time
3. Run `dmesg | tail` to see which device was just connected
4. Note the assigned port (e.g., /dev/ttyUSB0)
5. Repeat for each device

On Windows systems, use Device Manager to identify COM ports.

## Testing Sensor Configuration

After configuring the sensors, you can test them:

1. Click the "Start" button on the main interface
2. Verify that each graph shows appropriate readings
3. If any sensor shows no data or incorrect data, stop the collection, check the configuration, and try again

## Troubleshooting

### No Data from a Sensor

If a sensor is not providing data:

1. Check that the sensor is enabled in the configuration
2. Verify the correct serial port is specified
3. Ensure the baudrate matches what the sensor expects
4. Confirm the sensor is powered and properly connected

### Incorrect Readings

If a sensor shows data but with incorrect values:

1. For the thrust sensor, check the offset and scale values
2. For temperature sensors, verify the conversion formula in the sensor firmware
3. For voltage/current sensors, check the calibration in the sensor firmware

### RPM Sensor Issues

If the RPM sensor is not working:

1. Verify the path to sigrok-cli is correct
2. Run sigrok-cli manually to test the connection:
   ```
   sigrok-cli --driver=uni-t-ut372:conn=1a86.e008 --samples=1
   ```
3. Ensure the tachometer is properly positioned to detect rotation

### PWM Controller Issues

If the PWM controller is not responding:

1. Check the serial connection settings
2. Verify the controller firmware responds to the expected commands
3. Test the connection using a serial terminal program