import serial
import time

class TemperatureSensor:
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
			s = self.ser.readline().decode().strip()
		except UnicodeDecodeError:
			return None
		if len(s) == 0 or s[0] != 'T':
			return None
		try:
			val = float(s[1:]) / 1000
		except ValueError:
			pass
		return val

	def flush(self):
		self.ser.flushInput()
		self.ser.flushOutput()

	def close(self):
		if self.ser is not None:
			self.ser.close()
			self.ser = None
  
	def __del__(self):
		self.close()

