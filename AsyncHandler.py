import threading
import queue
from typing import Dict, Tuple, Callable, List, Any
import tkinter
import time

class AsyncHandler:
    def __init__(self, tkElement:tkinter.Tk, workerSleepTime:float=0.1, uiUpdateInterval:int=100):
        """Create async handler that will do background work and update the UI in a thread safe manner. 

        Args:
            tkElement (tkinter.Tk): Tk element to use the .after function to update the UI
            workerSleepTime (float, optional, seconds): How long to wait before checking background worker queue. Defaults to 0.1.
            uiUpdateInterval (int, optional, miliseconds): How long to wait before checking UI update queue. Defaults to 100.
        """        
        self.tkElement = tkElement
        self.workerSleepTime = workerSleepTime
        self.uiUpdateInterval = uiUpdateInterval

        self.keepAlive = True

        self.workerThread:threading.Thread = None
        self.workerQueue = queue.Queue()
        self.uiQueue = queue.Queue()

    def StartAsync(self):
        self.workerThread = threading.Thread(target=self.__WorkerThread)
        self.workerThread.daemon = True
        self.workerThread.start()

        self.__UiLoop()

    def AsyncWork(self, func:Callable, callback:Callable=None, *args, **kwargs):
        self.workerQueue.put([func, callback, args, kwargs])

    def AsyncUiCall(self, func:Callable, returnObject:Any):
        self.uiQueue.put([func, returnObject])

    def __WorkerThread(self):
        while self.keepAlive:
            if self.workerQueue.empty():
                time.sleep(self.workerSleepTime)
                continue

            [func, callback, args, kwargs] = self.workerQueue.get()

            returnObject = func(*args, **kwargs)

            if callback is not None:
                self.AsyncUiCall(callback, returnObject)

    def __UiLoop(self):
        if not self.uiQueue.empty():
            [callback, returnObject] = self.uiQueue.get()

            callback(returnObject)

        self.tkElement.after(self.uiUpdateInterval, self.__UiLoop)
            
