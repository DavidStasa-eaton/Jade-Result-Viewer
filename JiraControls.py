
from __future__ import annotations
import os
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image, Menu
import json
from typing import Dict, List, Tuple, Any, Callable, TYPE_CHECKING
import re
import datetime
from queue import Queue
import threading
import time

from TkinterSaver import RGB, packKwargs, gridKwargs, ScrollFrame, Button_ParseBool, Button_WorkStart
from JiraItem import JiraItem
from AsyncHandler import AsyncHandler

import JiraAgent as JiraAgent

if TYPE_CHECKING:
    from ResultViewer import JadeTableResult
    from atlassian import Jira

configPath = "JadeResultParserConfig.txt"

Button.WorkStart = Button_WorkStart
Button.Parsebool = Button_ParseBool

class JiraCredentialsFrame(Frame):
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        
        Label(self, text="User Name:", relief="sunken", bg="grey75", bd=2).pack(
            side="top", fill="x", **packKwargs
        )
        
        self.userVar = StringVar()
        self.userVar.set(JiraAgent.GetStoredUserName())
        self.userVar.trace_add("write", self.Handle_UserNameChanged)
        self.userEntry = Entry(self, textvariable=self.userVar)
        self.userEntry.pack(side="top", fill="x", **packKwargs)

        Label(self, text="Enter new user Token below and\nclick the \"Enter Token\" button", relief="sunken", bg="lightyellow", bd=2).pack(
            side="top", fill="x", **packKwargs
        )

        self.userTokenText = Text(self, wrap="char")
        self.userTokenText.pack(side="top", fill="both", expand=True, **packKwargs)

        self.enterTokenButton = Button(self, text="Enter Token", command=self.Click_HandleToken)
        self.enterTokenButton.pack(side="top", fill="x", **packKwargs)

        self.CredentialsChangedEvent:List[Callable[[str, str], None]] = []

    def Subscribed(self, func:Callable[[str, str], None]):
        self.CredentialsChangedEvent.append(func)

    def Handle_UserNameChanged(self, *args):
        JiraAgent.UpdateStoredCredentials(self.userVar.get())

        for func in self.CredentialsChangedEvent:
            func(self.userVar.get(), None)

    def Click_HandleToken(self):
        newToken = self.userTokenText.get("1.0", END)
        JiraAgent.UpdateStoredCredentials(self.userVar.get(), newToken)

        for func in self.CredentialsChangedEvent:
            func(self.userVar.get(), newToken)

        self.userTokenText.delete("1.0", END)

class CreateBugFrame(Frame):
    isVisible:bool = False
    def __init__(self, parent, handler:AsyncHandler, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.handler = handler
        self.activeItem:JiraItem = None
        self.inputPath = ""
        self.outputPath = ""

        self.jira = JiraAgent.CreateStaticJiraInstance()

        self.columnconfigure(2, weight=1)

        Label(self, text="Title:").grid(
            row=1, column=0, **gridKwargs
        )
        Label(self, text="Summary:").grid(
            row=2, column=0, **gridKwargs
        )
        Label(self, text="").grid(
            row=3, column=0, **gridKwargs
        ) # spacer
        Label(self, text="Priority:").grid(
            row=4, column=0, **gridKwargs
        )

        self.attachedIssueLabel = Label(self, text="-", relief="sunken", bd=2, bg="grey75")
        self.attachedIssueLabel.grid(row=0, column=0, columnspan=4, sticky="wens", padx=5, pady=1)

        self.titleEntry = Entry(self)
        self.titleEntry.grid(row=1, column=1, columnspan=3, sticky="wens", padx=5, pady=1)

        self.summaryText = Text(self, height=4, width=1)
        self.summaryText.grid(row=2, column=1, columnspan=3, sticky="wens", padx=5, pady=1)

        self.priorityCombo = ttk.Combobox(self, values=["High", "Medium", "Low"])
        self.priorityCombo.grid(row=4, column=1)
        self.priorityCombo.set("High")

        self.createBugButton = Button(self, text="Create Bug", command=self.Click_CreateBugButton)
        self.createBugButton.grid(row=5, column=0, columnspan=4)

    def UpdatedSelectedIssue(self, item:JiraItem, outputPath:str, inputPath:str):
        self.outputPath = outputPath
        self.inputPath = inputPath
        self.activeItem = item
        self.attachedIssueLabel.config(text=f"Log bug for: {self.activeItem.key}")

    def CancelBug(self):
        self.activeItem = None
        self.inputPath = ""
        self.outputPath = ""
        self.pack_forget()

    def Click_CreateBugButton(self):
        self.createBugButton.WorkStart()
        issueLinkData = {
            "type": {"name": "Depends"},
            "inwardIssue": self.activeItem.GetParentInfo()
        }

        fields = {
            "project": {"key": self.activeItem.projectKey},
            "issuetype": {"name": "Bug"},
            "summary": self.titleEntry.get(),
            "priority": {"name": self.priorityCombo.get()},
            "description": self.summaryText.get("1.0", END),
        }

        self.handler.AsyncWork(
            self.Handle_CreateBug,
            self.CallBack_CreateBug,
            fields
        )

        #[success, bugInfo] = JiraAgent.CreateItem(self.issueFrame.jiraFrame.jira, fields)

        #if not success:
        #    print("\n\nFailed to create bug\n\n")
        #    return
        #
        #createBugKey = bugInfo["key"]

        #[success, linkInfo] = JiraAgent.LinkClonedIssue(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.key)

        #JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.inputFilePath)
        #JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.outputFilePath)

    def Handle_CreateBug(self, fields:Dict[str, Any]):
        errors:List[str] = []

        (success, itemInfo) = JiraAgent.CreateAndGetItem(self.jira, fields)
        if not success:
            errors.append("Failed to create bug")
            return [False, errors]
        
        bugItem = JiraItem(itemInfo)

        [success, linkInfo] = JiraAgent.LinkDependsIssue(self.jira, bugItem.key, self.activeItem.key)
        if not success:
            errors.append("Failed to link issues.")

        if not os.path.exists(self.inputPath):
            errors.append("Input file could not be found")
        else:
            [success, info] = JiraAgent.AttachFile(self.jira, bugItem.key, self.inputPath)
            if not success:
                errors.append("Failed to attach input file")


        if not os.path.exists(self.outputPath):
            errors.append("Output file could not be found")
        else:
            [success, info] = JiraAgent.AttachFile(self.jira, bugItem.key, self.outputPath)
            if not success:
                errors.append("Failed to attach output file")

        return [len(errors)==0, errors]
        

    def CallBack_CreateBug(self, returnObject):
        success = returnObject[0]
        self.createBugButton.ParseBool(success)
        if not success:
            print("\n\nFailed to create bug\n\n")
            return
        
        errors = returnObject[1]
        

