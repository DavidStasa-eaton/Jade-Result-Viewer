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

        self.activeTasks = 0
        self.TaskCompleteEvent:List[Callable[[], None]] = []

        self.keepAlive = True

        self.workerThread:threading.Thread = None
        self.workerQueue = queue.Queue()
        self.uiQueue = queue.Queue()

    def SubscribeToTaskCompleteEvent(self, func:Callable[[], None]):
        """Subscribe to TaskCompleteEvent. If there are no active tasks the event will be triggered immediately. 

        Args:
            func (Callable[[], None]): Function to subscribe to the event. 
        """
        
        self.TaskCompleteEvent.append(func)

        if not self.ActiveWork:
            for func in self.TaskCompleteEvent:
                func()

    @property
    def ActiveWork(self) -> bool:
        """Check if there are any background tasks occuring. 

        Returns:
            bool: True if background tasks are still being processed. 
        """        
        return self.activeTasks > 0

    def StartAsync(self):
        self.workerThread = threading.Thread(target=self.__WorkerThread)
        self.workerThread.daemon = True
        self.workerThread.start()

        self.__UiLoop()

    def AsyncWork(self, func:Callable, callback:Callable=None, *args, **kwargs):
        self.activeTasks += 1
        self.workerQueue.put([func, callback, args, kwargs])

    def AsyncUiCall(self, func:Callable, returnObject:Any, doDecrement:bool=False):
        self.uiQueue.put([func, returnObject, doDecrement])

    def __WorkerThread(self):
        while self.keepAlive:
            if self.workerQueue.empty():
                time.sleep(self.workerSleepTime)
                continue

            [func, callback, args, kwargs] = self.workerQueue.get()

            returnObject = func(*args, **kwargs)

            
            if callback is not None:
                self.AsyncUiCall(callback, returnObject, True)


            

    def __UiLoop(self):
        if not self.uiQueue.empty():
            [callback, returnObject, doDecrement] = self.uiQueue.get()

            callback(returnObject)
            if doDecrement:
                self.activeTasks -= 1

                if self.activeTasks == 0:
                    for func in self.TaskCompleteEvent:
                        func()

        self.tkElement.after(self.uiUpdateInterval, self.__UiLoop)
            
