import serial
import time
from ..utils import time_it

class TemperatureSensor:

	n_vals = 1
    
	def __init__(self, port, baudrate):
		self.port = port
		self.baudrate = baudrate
		self.ser = None
  
	def enabled(self):
		return self.ser is not None

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate)
		self.ser.flushInput()
		self.ser.flushOutput()

	# @time_it("Temp read")
	def read(self):
		val = None
		try:
			s = self.ser.readline().decode().strip()
		except UnicodeDecodeError:
			return None
		if len(s) == 0 or s[0] != 'T':
			return None
		try:
			val = float(s[1:]) * 80 / 1000 / 60
			if val < 25 or val > 300:
				val = 25
		except ValueError:
			pass
		return val

	def flush(self):
		if self.ser is None:
			return
		self.ser.flushInput()
		self.ser.flushOutput()

	def close(self):
		if self.ser is not None:
			self.ser.close()
			self.ser = None
  
	def __del__(self):
		self.close()

