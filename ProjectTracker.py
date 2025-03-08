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
from JiraControls import IssueFrame, JiraCredentialsFrame
from ProjectExplorer import ProjectViewerFrame
from RequirementsTracker import ReqTrackerUI
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
        self.noteBook.add(self.projectViewer, text="Project Viewer")

        ##################################################################################################################
        ##############################                 Req Tracker               #########################################
        ##################################################################################################################

        self.reqTrackerFrame = ReqTrackerUI(self, self.handler)
        self.noteBook.add(self.reqTrackerFrame, text="Req Tracker")

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

    def CallStaticInits(self):
        IssueFrame.PopulateImages()

    def SaveElements(self):
        self.reqTrackerFrame.SaveElements()

    def RestoreElements(self):
        self.reqTrackerFrame.RestoreElements()

        self.Handle_CredentialsChangedEvent(JiraAgent.GetStoredUserName(), None)

        

def MainExitCall():
    #ui.SaveElements()
    tk.destroy()




if __name__ == "__main__":
    tk = Tk()

    ui = MainUI(tk)
    ui.pack(fill="both", expand=True)

    tk.protocol("WM_DELETE_WINDOW", MainExitCall)

    tk.mainloop()

