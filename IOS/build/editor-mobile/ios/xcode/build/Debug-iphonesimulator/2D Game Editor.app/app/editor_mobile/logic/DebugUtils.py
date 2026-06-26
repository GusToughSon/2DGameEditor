import time
from datetime import datetime

class DebugUtils:
    @staticmethod
    def log(message, level="DEBUG"):
        """ Prints a message to the console with a high-precision timestamp. """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")

    @staticmethod
    def benchmark(name):
        """ Returns a context manager for benchmarking a block of code. """
        return BenchmarkContext(name)

class BenchmarkContext:
    """ Context manager for measuring execution time. """
    def __init__(self, name):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        DebugUtils.log(f"START: {self.name}", level="BENCH")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        DebugUtils.log(f"FINISH: {self.name} - Elapsed: {elapsed:.4f}s", level="BENCH")
