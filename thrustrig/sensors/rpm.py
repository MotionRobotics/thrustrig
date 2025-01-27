import os
import time
import subprocess
from ..utils import time_it

class RPMSensor:

	n_vals = 1

	def __init__(self, sigrokpath):
		self.sigrokpath = sigrokpath
		self._enabled = False
  
	def enabled(self):
		return self._enabled

	def start(self):
		if os.path.isfile(self.sigrokpath):
			self._enabled = True
		else:
			self._enabled = False
			raise ValueError("sigrok-cli not found")

	@time_it("RPM read")
	def read(self):
		val = None
		try:
			results = subprocess.Popen([self.sigrokpath,"--driver=uni-t-ut372:conn=1a86.e008", "--samples=1"], stdout=subprocess.PIPE)
			out, err = results.communicate()
			if isinstance(out, bytes):
				out = out.decode()
			val = float(out.split(' ')[1])
		except (ValueError, IndexError):
			pass
		return val

	def flush(self):
		pass

	def close(self):
		self._enabled = False
  
	def __del__(self):
		self.close()

