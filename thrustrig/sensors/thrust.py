import serial
import time
from ..utils import time_it

class ThrustSensor:

	n_vals = 1

	def __init__(self, port, baudrate, offset, scale):
		self.port = port
		self.baudrate = baudrate
		self.ser = None
		self.offset = offset
		self.scale = scale
  
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
			val = (float(s[1:]) - self.offset) / self.scale
			val *= 85./114
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

