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
from JiraControls import JiraCredentialsFrame
from ProjectExplorer import ProjectViewerFrame
from RequirementsTracker import ReqTrackerUI
from TestingCycleExplorer import CycleExplorerUI
import JiraItem
from AsyncHandler import AsyncHandler

import JiraAgent

configPath = "ProjectTrackerConfig.txt"

class MainUI(Frame):
    def __init__(self, tk:Tk, *args, **kwargs):
        Frame.__init__(self, tk, *args, **kwargs)

        self.handler = AsyncHandler(self)
        self.handler.StartAsync()
        JiraAgent.CreateStaticJiraInstance()

        self.topFrame = Frame(self)
        self.topFrame.pack(side="top", fill="x", **packKwargs)

        Label(self.topFrame, text="Selected Result Directory:").pack(side="left", **packKwargs)

        self.selectedResultDirVar = StringVar()
        self.selectedResultsLabel = Label(self.topFrame, textvariable=self.selectedResultDirVar, relief="sunken", bg="grey75", justify="left", anchor="w")
        self.selectedResultsLabel.pack(side="left", fill="x", expand=True, **packKwargs)

        Label(self.topFrame, text="Selected Project:").pack(side="left", **packKwargs)

        self.selectedProjectVar = StringVar()
        self.selectedProjectsLabel = Label(self.topFrame, textvariable=self.selectedProjectVar, 
                                           relief="sunken", bg="grey75", width=15)
        self.selectedProjectsLabel.pack(side="left", **packKwargs)

        ##################################################################################################################
        ##############################                  Notebook                 #########################################
        ##################################################################################################################

        style = ttk.Style()
        style.theme_use("default")
        style.configure('lefttab.TNotebook', tabposition='wne', background="grey75")
        style.configure('lefttab.TNotebook.Tab', width=15, padding=[10,5])
        style.map("lefttab.TNotebook.Tab",
                  background=[("selected", "cyan"), ("!selected", "#D3D3D3")],
                  relief=[("selected", "sunken"), ("!selected", "raised")],
                  )

        self.noteBook = ttk.Notebook(self, style='lefttab.TNotebook')
        self.noteBook.pack(side='top', fill="both", expand=True)


        ##################################################################################################################
        ##############################                     Menu                  #########################################
        ##################################################################################################################

        self.masterMenu = Menu(self)
        tk.title("Jira Project Tracker Assistant")

        self.jiraMenu = Menu(self.masterMenu, tearoff=0)
        self.jiraMenu.add_command(label="Jira Credentials", command=self.Menu_UpdateJiraCredentials)
        #self.jiraMenu.add_command(label="Create Regression Epic", command=self.TempFunc)

        self.masterMenu.add_cascade(label="Jira", menu=self.jiraMenu)

        tk.config(menu=self.masterMenu)

        ##################################################################################################################

        ##################################################################################################################
        ##############################               Project Explorer            #########################################
        ##################################################################################################################

        self.projectViewer = ProjectViewerFrame(self)
        self.projectViewer.SubscribeToProjectedSelectedEvent(self.Callback_SelectProjectChangedEvent)
        self.noteBook.add(self.projectViewer, text="Project Viewer")

        ##################################################################################################################
        ##############################                 Req Tracker               #########################################
        ##################################################################################################################

        self.reqTrackerFrame = ReqTrackerUI(self, self.handler)
        self.reqTrackerFrame.ioFrame.SubscribeToResultDirChangedEvent(self.Callback_ResultDirChanged)
        self.noteBook.add(self.reqTrackerFrame, text="Req Tracker")

        ##################################################################################################################
        ##############################            Testing Cycle Tracker          #########################################
        ##################################################################################################################

        self.testCycleFrame = CycleExplorerUI(self, self.GetResultFileDir, self.handler)
        #self.testCycleFrame.ioFrame.SubscribeToResultDirChangedEvent(self.Callback_ResultDirChanged)
        self.noteBook.add(self.testCycleFrame, text="Testing Cycles")

        self.RestoreElements()

    def GetResultFileDir(self) -> str:
        return self.selectedResultDirVar.get()

    def Callback_SelectProjectChangedEvent(self, newProjectKey:str):
        self.selectedProjectVar.set(newProjectKey)
        self.testCycleFrame.Handle_GetTestCycles()

    def Callback_ResultDirChanged(self, newDir:str):
        self.selectedResultDirVar.set(newDir)
        self.testCycleFrame.UpdateAllInputFiles()

    def Menu_UpdateJiraCredentials(self):
        tl = Toplevel(self)
        tl.title("Update Jira Credentials")
        credFrame = JiraCredentialsFrame(tl)
        credFrame.pack(side="top", fill="both", expand=True)

        credFrame.Subscribed(self.Handle_CredentialsChangedEvent)

    def Handle_CredentialsChangedEvent(self, userName:str, _:str):
        if userName == "":
            tk.title("Project Tracker Assistant")
        else:
            tk.title(f"Project Tracker Assistant - {userName}")

    def SaveElements(self):
        reqTrackerData = self.reqTrackerFrame.SaveElements()
        projectExplorerData = self.projectViewer.SaveElements()

        saveDict = {
            "reqtracker": reqTrackerData,
            "projectexplorer": projectExplorerData
        }

        jString = json.dumps(saveDict)

        with open(configPath, "w") as configFile:
            configFile.write(jString)

    def RestoreElements(self):
        if not os.path.exists(configPath):
            return 
        
        fileText = open(configPath, "r").readline()

        restoreDict:Dict[str, Any] = json.loads(fileText)
        self.projectViewer.RestoreElements(restoreDict.get("projectexplorer", {}))
        self.reqTrackerFrame.RestoreElements(restoreDict.get("reqtracker", {}))
        

        self.Handle_CredentialsChangedEvent(JiraAgent.GetStoredUserName(), None)

        

def MainExitCall():
    ui.SaveElements()
    tk.destroy()




if __name__ == "__main__":
    tk = Tk()

    ui = MainUI(tk)
    ui.pack(fill="both", expand=True)

    tk.protocol("WM_DELETE_WINDOW", MainExitCall)

    tk.mainloop()

