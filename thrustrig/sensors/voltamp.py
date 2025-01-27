import serial
import time

class VoltAmpSensor:

	n_vals = 3

	def __init__(self, port, baudrate, ser_timeout):
		self.port = port
		self.baudrate = baudrate
		self.ser = None
		self.ser_timeout = ser_timeout
  
	def enabled(self):
		return self.ser is not None

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate, timeout=self.ser_timeout)
		self.ser.flushInput()
		self.ser.flushOutput()
  
	def read(self, timeout_s):
		val = None
		s = ''
		try:
			# ':r50{data}\n'
			start = time.time()
			while True:
				if time.time() - start > timeout_s:
					break
				ss = self.ser.read(1).decode('utf-8')
				if ss == ':':
					ss += self.ser.read(3).decode('utf-8')
					if ss == ':r50':
						s = ss
						continue
				if s:
					s += ss
					if ss == '\n':
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

