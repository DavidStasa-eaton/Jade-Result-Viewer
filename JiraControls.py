
from __future__ import annotations
import os
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image, Menu
import json
from typing import Dict, List, Tuple, Any, Callable
import re
import datetime
from queue import Queue
import threading
import time

from TkinterSaver import RGB, packKwargs, gridKwargs, ScrollFrame, Button_ParseBool, Button_WorkStart

import JiraAgent as JiraAgent

configPath = "JadeResultParserConfig.txt"

Button.WorkStart = Button_WorkStart
Button.Parsebool = Button_ParseBool

class JiraFrame(Frame):
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.userFrame = Frame(self)
        self.userFrame.pack(side="top", fill="x")
        self.userFrame.columnconfigure(1, weight=1)

        self.inputFilePath:str = ""

        Label(self.userFrame, text="User").grid(
            row=0, column=0, sticky="wens"
        )

        self.userVar = StringVar()
        self.userVar.trace_add("write", self.Handle_UserNameChanged)
        self.userEntry = Entry(self.userFrame, textvariable=self.userVar)
        self.userEntry.grid(row=0, column=1, **gridKwargs)

        self.enterTokenButton = Button(self.userFrame, text="Enter Token", command=self.Click_HandleToken)
        self.enterTokenButton.grid(row=1, column=0, columnspan=2, **gridKwargs)

        self.tablesScrollFrame = ScrollFrame(self, width=1, bg="grey55", relief="sunken", bd=2)
        self.tablesScrollFrame.packFrame.config(bg="grey55")
        #self.tablesScrollFrame.grid(row=0, column=0, sticky="wens")
        self.tablesScrollFrame.pack(side="top", fill="both", expand=True)
        self.tablesScrollFrame.hScroll.grid_forget()
        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=500)

        Button(self, text="Test", command=self.Click_TestFunc).pack(side='bottom')

        self.userToken = None

        self.jiraQueue = Queue()
        self.uiQueue = Queue()

        self.jiraThread = threading.Thread(target=self.JiraThread)
        self.jiraThread.daemon = True

    def GetJiraIssue(self, key:str) -> Tuple[str, Dict[str, Any]]:
        if not JiraAgent.jiraImported:
            return {
                "key": key,
                "issueDict": {}
            }
        
        issueDict = JiraAgent.GetJiraIssue(self.jira, key)

        return {
            "key": key,
            "id": issueDict["id"],
            "issueDict": issueDict
        }

    def Callback_ResultFileLoaded(self, inputFilePath:str, resultFilePath:str, results:List[TableResult]):
        """Subscribed from ResultViewerer frame. Will be called when a new result file is loaded. Will ascychroniously load each jira issue found in the result files. 

        Args:
            results (List[TableResult]): List of all the TableResults parsed in the results file
        """
        self.inputFilePath = inputFilePath
        self.resultFilePath = resultFilePath
        for child in self.tablesScrollFrame.packFrame.winfo_children():
            child:Frame
            child.pack_forget()
            child.destroy()

        for r in results:
            for req in r.reqs:
                self.AsyncFunctionCall(self.GetJiraIssue, self.AddIssueCard, req)

    def AddIssueCard(self, issueInfo:Dict[str, Any]):
        """Add a card for a jira issue. 

        Args:
            issueInfo (Dict[str, Any]): keys will be "key" and "issueDict"
        """
        key = issueInfo["key"]
        issueDict = issueInfo["issueDict"]

        if issueDict == {}:
            return

        temp = IssueFrame(self.tablesScrollFrame.packFrame, self, key, issueDict, self.inputFilePath, self.resultFilePath,
                          width=IssueFrame.RequiredWidth, height=IssueFrame.RequiredHeight)
        temp.pack(side="top", fill="both", expand=True, pady=3, padx=3)

        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=500)

    def Click_TestFunc(self):
        #
        # TEST FUNCTION - CAN BE FREELY OVERWRITTEN
        #
        print(JiraAgent.WriteIssueToFile(self.jira, "DIGTOOLS-56"))

    def Handle_UserNameChanged(self, *args):
        JiraAgent.userName = self.userVar.get()

    def Click_HandleToken(self):
        results = simpledialog.askstring("Enter Token String", "Enter the token generated from Jira for your account.")
        
        if results is None:
            return
        
        self.userToken = results
        JiraAgent.TOKEN = self.userToken

    #region Async Threads and UI Loops
    def StartJiraComms(self):
        if self.userVar.get() == "" or self.userToken == "":
            print(self.userVar.get())
            print(self.userToken)
            # handle user inputs not given. 
            return
        
        self.jira = JiraAgent.GetJiraInstance()
        self.jiraThread.start()

        self.UI_Loop()

    def AsyncFunctionCall(self, func:Callable, callBack:Callable=None, *args, **kwargs):
        self.jiraQueue.put([func, callBack, args, kwargs])

    def Async_UI_Call(self, func:Callable, returnObject:Any):
        self.uiQueue.put([func, returnObject])

    def JiraThread(self):
        while True:
            if not self.jiraQueue.empty():
                [func, callback, args, kwargs] = self.jiraQueue.get()

                returnObject = func(*args, **kwargs)

                if callback is not None:
                    self.Async_UI_Call(callback, returnObject)

            time.sleep(0.100)

    def UI_Loop(self):
        if not self.uiQueue.empty():
            [func, returnObject] = self.uiQueue.get()

            func(returnObject)


        self.after(100, self.UI_Loop)

    #endregion __ Async Threads and UI Loops __

    def SaveElements(self) -> Dict[str, Any]:
        return {
            "user": self.userVar.get(),
            "token": self.userToken
        }
    
    def RestoreElements(self, rDict:Dict[str, Any]):
        if rDict is None:
            return
        
        self.userVar.set(rDict.get("user", ""))
        self.userToken = rDict.get("token", None)
        JiraAgent.TOKEN = self.userToken
