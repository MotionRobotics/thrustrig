import time

def time_it(name):
	def deco(fn):
		def wrap(*args, **kwargs):
			start = time.time()
			ret = fn(*args, **kwargs)
			print(f"{name} took {time.time() - start} seconds")
			return ret
		return wrap