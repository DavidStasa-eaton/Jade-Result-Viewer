
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
from AsyncHandler import AsyncHandler

import JiraAgent as JiraAgent

if TYPE_CHECKING:
    from RequirementsTracker import JadeTableResult
    from atlassian import Jira

configPath = "JadeResultParserConfig.txt"

Button.WorkStart = Button_WorkStart
Button.Parsebool = Button_ParseBool

class JiraFrame(Frame):
    instance:JiraFrame = None
    def __init__(self, parent:Frame, handler:AsyncHandler, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.handler = handler

        self.inputFilePath:str = ""

        self.tablesScrollFrame = ScrollFrame(self, width=1, bg="grey55", relief="sunken", bd=2)
        self.tablesScrollFrame.packFrame.config(bg="grey55")
        #self.tablesScrollFrame.grid(row=0, column=0, sticky="wens")
        self.tablesScrollFrame.pack(side="top", fill="both", expand=True)
        self.tablesScrollFrame.hScroll.grid_forget()
        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=500)

        Button(self, text="Test", command=self.Click_TestFunc).pack(side='bottom')

        ##################################################################################################################
        ####################################                Bug Frame              #######################################
        ##################################################################################################################
        
        self.bugFrame = CreateBugFrame(self, bd=3, relief="groove")
        
    def GetJiraIssue(self, key:str) -> Tuple[str, Dict[str, Any]]:
        if not JiraAgent.jiraImported:
            return {
                "key": key,
                "issueDict": {}
            }
        
        issueDict = JiraAgent.GetJiraIssue(self.jira, key)

        if issueDict == {}:
            return {
                "key": key,
                "issueDict": {}
            }

        return {
            "key": key,
            "issueDict": issueDict
        }

    def Callback_ResultFileLoaded(self, inputFilePath:str, resultFilePath:str, results:List[JadeTableResult]):
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

        uniqueReqs:List[str] = []
        for r in results:
            for req in r.reqs:
                if req not in uniqueReqs:
                    uniqueReqs.append(req)

        for req in uniqueReqs:
            self.handler.AsyncWork(self.GetJiraIssue, self.AddIssueCard, req)

        self.jira = JiraAgent.CreateStaticJiraInstance()

    def AddIssueCard(self, issueInfo:Dict[str, Any]):
        """Add a card for a jira issue. 

        Args:
            issueInfo (Dict[str, Any]): keys will be "key" and "issueDict"
        """
        key = issueInfo["key"]
        issueDict = issueInfo["issueDict"]

        if issueDict == {}:
            temp = IssueFrame.FromInvalidReq(self.tablesScrollFrame.packFrame, self, key, self.inputFilePath, self.resultFilePath)
        else:
            temp = IssueFrame(self.tablesScrollFrame.packFrame, self, key, issueDict, self.inputFilePath, self.resultFilePath)
        temp.pack(side="top", fill="both", expand=True, pady=3, padx=3)

        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=500)

    def Click_TestFunc(self):
        #
        # TEST FUNCTION - CAN BE FREELY OVERWRITTEN
        #
        #fields = {
        #    "project": {"key": "MT"},
        #    "issuetype": {"name": "Test"},
        #    "parent": {"key:": "MT-1613", "id": "8175273"},
        #    "summary": "Test Case From Automation With Parent 2",
        #    "priority": {"name": "High"},
        #    "description": "Test descriptoin from automation.\nTroubleshooting here",
        #}

        #[success, bugInfo] = JiraAgent.CreateBug(self.jira, fields)
        #print(bugInfo)

        xray = JiraAgent.GetXrayInstance()

        print(JiraAgent.TestFunc(xray, "MT-1618"))

    #region Async Threads and UI Loops
    def StartJiraComms(self):
        self.jira = JiraAgent.CreateStaticJiraInstance()
    #endregion __ Async Threads and UI Loops __

    def SaveElements(self) -> Dict[str, Any]:
        return {}
    
    def RestoreElements(self, rDict:Dict[str, Any]):
        if rDict is None:
            return

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

class IssueFrame(Frame):
    RequiredHeight = 100
    RequiredWidth = 485
    
    # Popluate with static method IssueFrame.PopulateImages()
    taskImage = None
    bugImage = None
    epicImage = None
    storyImage = None
    testCaseImage = None
    requirementImage = None
    unknownImage = None

    errorImage = None
    successImage = None

    def __init__(self, parent:Frame, jiraFrame:JiraFrame, issueKey:str, issueJson:Dict[str, Any], inputFilePath:str, outputFilePath:str, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.jiraFrame = jiraFrame
        self.key = issueKey
        self.issueJson = issueJson
        self.inputFilePath = inputFilePath
        self.outputFilePath = outputFilePath

        self.config(width=IssueFrame.RequiredWidth, height=IssueFrame.RequiredHeight)

        self.validReq = self.issueJson != {}

        self.CreateRightClickMenu()

        

        if self.validReq:
            self.id = issueJson.get("id", -1)
            self.issueType = self.issueJson["issuetype"]["name"]
            self.status = self.issueJson["status"]["name"]
            self.projectDict = self.issueJson["project"]
            controlState = "normal"

            self.summary = self.issueJson["summary"]
            self.reporter = self.issueJson["reporter"]["displayName"]

            self.assignee = self.issueJson["assignee"]
            self.assignee = "No One" if self.assignee is None else self.assignee["displayName"]

            self.bind("<Button-3>", self.Handle_RightClick)
            
        else:
            self.id = -1
            self.issueType = "?"
            self.status = "None"
            self.projectDict = {}
            controlState = "disabled"

            self.summary = "!! Req Not Found !!"
            self.reporter = "?"
            self.assignee = "?"
        self.LoadImageBasedOnType()
        

        self.typeCanvas = Canvas(self, height=20, width=20)
        self.typeCanvas.create_image(10,10, image=self.image)
        self.typeCanvas.place(x=3, y=7, height=20, width=20)

        self.transitionCombo = ttk.Combobox(self, values=[], state=controlState)
        self.transitionCombo.place(x=125, y=6, width=100)
        self.transitionCombo.bind("<<ComboboxSelected>>", self.Handle_ChangeStatus)

        self.statusChangeCanvas = Canvas(self, height=20, width=20)
        self.statusCreatedImage = None
        self.statusChangeCanvas.place(x=228, y=7, height=20, width=20)

        self.keyLabel = Label(self, text=self.key, relief="ridge", bd=2)
        self.keyLabel.place(x=23, y=6, width=100)

        self.uploadButton = Button(self, text="Upload", command=self.Click_UploadButton, state=controlState)
        self.uploadButton.place(x=400, y=3, width=75)

        self.summaryLabel = Label(self, text=self.summary, relief="sunken", bd=2, bg="grey75")
        self.summaryLabel.place(x=3, y=35, width=480)

        Label(self, text="Reporter:").place(
            x=3, y=60, width=50)
        self.reporterLabel = Label(self, text=self.reporter)
        self.reporterLabel.place(x=55, y=60)

        Label(self, text="Assignee:").place(
            x=3, y=80, width=50)
        
        
        self.assigneeLabel = Label(self, text=self.assignee)
        self.assigneeLabel.place(x=55, y=80)

        self.createBugButton = Button(self, text="Log Bug", command=self.Toggle_BugFrame, state=controlState)
        self.createBugButton.place(x=300, y=60, width=75)

        self.transitionDict:Dict[str, int] = {}

        if self.validReq:
            self.GetTransitions()

    def Toggle_BugFrame(self):
        if CreateBugFrame.isVisible and self.jiraFrame.bugFrame.activeKey == self.key:
            self.jiraFrame.bugFrame.CancelBug()
        elif CreateBugFrame.isVisible and self.jiraFrame.bugFrame.activeKey != self.key:
            self.jiraFrame.bugFrame.UpdatedSelectedIssue(self)
        else:
            self.jiraFrame.bugFrame.UpdatedSelectedIssue(self)
            self.jiraFrame.bugFrame.pack(side="top", fill="x", padx=1, pady=2)

        CreateBugFrame.isVisible = not CreateBugFrame.isVisible
        
    def GetParentInfo(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key
        }
    
    def Handle_RightClick(self, event):
        try:
            self.rightClickMenu.tk_popup(event.x_root, event.y_root)
        finally:
            self.rightClickMenu.grab_release()

    def CreateRightClickMenu(self):
        self.rightClickMenu = Menu(self, tearoff=0)

        self.rightClickMenu.add_command(label="Save Info", command=self.MenuClick_SaveInfo)
        self.rightClickMenu.add_command(label="LinkIssue", command=self.MenuClick_LinkIssue)

    def MenuClick_SaveInfo(self, event=None):
        self.jiraFrame.handler.AsyncWork(
            JiraAgent.WriteIssueToFile, 
            None,
            self.jiraFrame.jira, 
            self.key,
            False
        )

    def MenuClick_LinkIssue(self, event=None):
        results = simpledialog.askstring("Enter Issue Key", "Enter the key of the jira item you wish to link")
        
        if results is None:
            return
        
        print(results)
        
        self.jiraFrame.handler.AsyncWork(
            JiraAgent.LinkClonedIssue, 
            None,
            self.jiraFrame.jira, 
            self.key,
            results
        )

    def LoadImageBasedOnType(self):
        if self.issueType == "Task":
            self.image = IssueFrame.taskImage
        elif self.issueType == "Bug":
            self.image = IssueFrame.bugImage
        elif self.issueType == "Story":
            self.image = IssueFrame.storyImage
        elif self.issueType == "Epic":
            self.image = IssueFrame.epicImage
        elif self.issueType == "Test":
            self.image = IssueFrame.testCaseImage
        elif self.issueType == "Requirement":
            self.image = IssueFrame.requirementImage
        else:
            self.image = IssueFrame.unknownImage

    def Handle_ChangeStatus(self, event=None):
        self.transitionCombo.config(state="disabled")
        value = self.transitionCombo.get()
        if self.statusCreatedImage is not None:
            self.statusChangeCanvas.delete(self.statusCreatedImage)
        self.jiraFrame.handler.AsyncWork(
            JiraAgent.SetIssueStatus, 
            self.Callback_ChangeStatus,
            self.jiraFrame.jira, 
            self.key, 
            value
        )

    def Callback_ChangeStatus(self, returnObject):
        self.transitionCombo.config(state="normal")
        

        if returnObject[0]:
            temp = IssueFrame.successImage
        else:
            temp = IssueFrame.errorImage

        self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=temp)

    def GetTransitions(self):
        self.jiraFrame.handler.AsyncWork(
            JiraAgent.GetIssueTransitions, 
            self.Callback_GetTransitions,
            self.jiraFrame.jira, 
            self.key, 
        )

    def Callback_GetTransitions(self, transTuple:Tuple[bool, List[Dict[str, Any]]]):
        if not transTuple[0]:

            return
        
        self.transitionDict = {}
        selectIndex = -1
        for tDict in transTuple[1]:
            self.transitionDict[tDict["name"]] = tDict["id"]

        self.transitionCombo.config(values=list(self.transitionDict.keys()))
        self.transitionCombo.set(self.status)

    def Click_UploadButton(self):
        self.uploadButton.WorkStart()
        self.jiraFrame.handler.AsyncWork(
            JiraAgent.AttachFile, 
            None,
            self.jira,  
            self.key, 
            self.outputFilePath
        )

        self.jiraFrame.handler.AsyncWork(
            JiraAgent.AttachFile, 
            self.Callback_UpdateButton,
            self.jira, 
            self.key, 
            self.inputFilePath
        )
        #print(MainUI.instance.resultFrame.selectedResultFile.absolutePath)

    def Callback_UpdateButton(self, returnObject):
        self.uploadButton.ParseBool(type(returnObject[0]) != tuple)

    @classmethod
    def FromInvalidReq(cls, parent:Frame, jiraFrame:JiraFrame, issueKey:str, inputFilePath, outputFilePath, *args, **kwargs):
        return cls(parent, jiraFrame, issueKey, {}, inputFilePath, outputFilePath, *args, **kwargs)

    @staticmethod
    def PopulateImages():
        '''Must be called after creation'''
        IssueFrame.taskImage = PhotoImage(file=r"Resources\task.png")
        IssueFrame.bugImage = PhotoImage(file=r"Resources\bug.png")
        IssueFrame.epicImage = PhotoImage(file=r"Resources\epic.png")
        IssueFrame.storyImage = PhotoImage(file=r"Resources\story.png")
        IssueFrame.testCaseImage = PhotoImage(file=r"Resources\testcase.png")
        IssueFrame.requirementImage = PhotoImage(file=r"Resources\requirement.png")
        IssueFrame.unknownImage = PhotoImage(file=r"Resources\unknown.png")

        IssueFrame.errorImage = PhotoImage(file=r"Resources\error.png")
        IssueFrame.successImage = PhotoImage(file=r"Resources\success.png")


    @property
    def jira(self) -> Jira:
        return self.jiraFrame.jira

class CreateBugFrame(Frame):
    isVisible:bool = False
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.issueFrame:IssueFrame = None
        self.activeKey = ""

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

    def UpdatedSelectedIssue(self, issueFrame:IssueFrame):
        self.issueFrame = issueFrame
        self.activeKey = self.issueFrame.key
        self.attachedIssueLabel.config(text=f"Log bug for: {self.activeKey}")

    def CancelBug(self):
        self.issueFrame = None
        self.activeKey = ""
        self.pack_forget()

    def Click_CreateBugButton(self):
        issueLinkData = {
            "type": {"name": "Depends"},
            "inwardIssue": self.issueFrame.GetParentInfo()
        }

        projectKey = self.issueFrame.projectDict["key"]

        fields = {
            "project": {"key": projectKey},
            "issuetype": {"name": "Bug"},
            "summary": self.titleEntry.get(),
            "priority": {"name": self.priorityCombo.get()},
            "description": self.summaryText.get("1.0", END),
        }

        [success, bugInfo] = JiraAgent.CreateItem(self.issueFrame.jiraFrame.jira, fields)

        if not success:
            print("\n\nFailed to create bug\n\n")
            return
        
        createBugKey = bugInfo["key"]

        [success, linkInfo] = JiraAgent.LinkClonedIssue(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.key)

        JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.inputFilePath)
        JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.outputFilePath)

