import serial
import time
from ..utils import time_it

class ThrustSensor:

	n_vals = 1

	def __init__(self, port, baudrate, offset = None, scale = None, senlen = 1, efflen = 1):
		self.port = port
		self.baudrate = baudrate
		self.ser = None
		self.offset = offset
		self.scale = scale
		self.senlen = senlen
		self.efflen = efflen
  
	def enabled(self):
		return self.ser is not None

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate)
		self.ser.flushInput()
		self.ser.flushOutput()

	# @time_it("Thrust read")
	def read(self):
		val = None
		try:
			s = self.ser.readline().decode().strip()
		except UnicodeDecodeError:
			return None
		if len(s) == 0 or s[0] != 'H':
			return None
		try:
			val = float(s[1:])
			if self.offset is not None and self.scale is not None:
				val = (val - self.offset) / self.scale
				val *= self.senlen / self.efflen
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

