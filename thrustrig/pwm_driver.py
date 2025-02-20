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
		self.ramp_active = False
  
	def enabled(self):
		return self.ser is not None

	def start(self):
		self.ser = serial.Serial(self.port, self.baudrate)
		self.ser.flushInput()
		self.ser.flushOutput()
		self.t = threading.Thread(target=self.loop)
		self.t.start()

	def set(self, val):
		if self.ramp_active:
			return False
		if val < 1000 or val > 2000:
			return False
		self.val = val
		if self.enabled():
			data = f"set {val}\n".encode()
			self.ser.write(data)
		return True

	def ramp(self, peak, step, period):
		if self.ramp_active:
			return False
		if peak < 1000 or peak > 2000:
			return False
		if step < 0:
			return False
		if period < 0:
			return False

		self.ramp_active = True
		if self.enabled():
			data = f"ramp {peak} {step} {period}\n".encode()
			self.ser.write(data)
   
		return True

	def stop_ramp(self):
		if self.ramp_active:
			if self.enabled():
				data = "stop \n".encode()
				self.ser.write(data)
			self.ramp_active = False
			return True

	def loop(self):
		while not self.stop:
			if self.ser.in_waiting > 0:
				line = self.ser.readline().decode().strip()
				if line.startswith("PWM: "):
					self.val = int(line[5:])
				elif line == "Ramp complete":
					self.ramp_active = False
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

