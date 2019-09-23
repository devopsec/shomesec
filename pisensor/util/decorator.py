'''
@Summary: Contains methods to be applied as python decorators
@Author: devopsec
'''

from threading import Thread, Lock
from multiprocessing import Process

class ThreadingIter():
    """
    Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """
    def __init__(self, iter):
        self.iter = iter
        self.lock = Lock()

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            return self.iter.next()

def async_thread(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs, daemon=True)
        thr.start()
    return wrapper

def async_proc(f):
    def wrapper(*args, **kwargs):
        proc = Process(target=f, args=args, kwargs=kwargs, daemon=True)
        proc.start()
    return wrapper
