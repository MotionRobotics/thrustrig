import serial
import time
import threading

class PWMDriver:

	n_vals = 1
    
	def __init__(self, port, baudrate):
		self.port = port
		self.baudrate = baudrate
		self.ser = None
		self.t = None
		self.val = 0
		self.stop = False
  
	def enabled(self):
		return self.ser is not None

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate)
		self.ser.flushInput()
		self.ser.flushOutput()
		self.t = threading.Thread(target=self.loop)
		self.t.start()

	def set(self, val):
		if val < 0 or val > 200:
			return False
		self.val = val
		return True

	def loop(self):
		while not self.stop:
			self.ser.write(self.val.to_bytes(1, 'big'))
			time.sleep(0.01)

	def flush(self):
		if self.ser is None:
			return
		self.ser.flushInput()
		self.ser.flushOutput()

	def close(self):
		if self.ser is not None and self.t is not None:
			self.stop = True
			self.t.join()
			self.ser.close()
			self.ser = None
			self.t = None
  
	def __del__(self):
		self.close()

