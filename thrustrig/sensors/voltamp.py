import serial
import time

class VoltAmpSensor:
	def __init__(self, port, baudrate):
		self.port = port
		self.baudrate = baudrate
		self.start()

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate)
		self.ser.flushInput()
		self.ser.flushOutput()
  
	def read(self):
		val = None
		try:
			while True:
				s = self.ser.readline().decode().strip()
				if len(s) > 0 and s[:4] == ':r50':
					break
		except UnicodeDecodeError:
			return None
		try:
			val = self.parse(s)
		except ValueError:
			pass
		return val

	def parse(self, s):
		parts = s.split(',')
		
		voltage = float(parts[2]) / 100
		current = float(parts[3]) / 100
		temperature = float(parts[8]) % 100
  
		return voltage, current, temperature

	def flush(self):
		self.ser.flushInput()
		self.ser.flushOutput()

	def close(self):
		if self.ser is not None:
			self.ser.close()
			self.ser = None
  
	def __del__(self):
		self.close()

