from __future__ import annotations
import os
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image, Menu, messagebox, Checkbutton, BooleanVar
import json
from typing import Dict, List, Tuple, Any, Callable, TYPE_CHECKING
import re
import datetime
from queue import Queue
import threading
import time

from TkinterSaver import RGB, packKwargs, gridKwargs, ScrollFrame, Button_ParseBool, Button_WorkStart, LoadButton, ToolTip, ToggleElement
from AsyncHandler import AsyncHandler
from JiraItem import JiraItem as Item
from JiraItem import JiraType
from JiraItem import ItemCard as ParentItemCard
from JiraControls import IssueFrame

import JiraAgent as JiraAgent

configPath = "Projects_Config.txt"

class ProjectViewerFrame(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.handler = AsyncHandler(self)
        self.jira = JiraAgent.CreateStaticJiraInstance()
        self.handler.StartAsync()

        self.selectFrame = Frame(self)
        self.selectFrame.pack(side="left", fill="y")

        self.addProjectFrame = AddProjectFrame(self.selectFrame, self)
        self.addProjectFrame.pack(side="top", fill="x", **packKwargs)

        self.projectDict:Dict[str, Project] = {}
        self.selectDict:Dict[str, ProjectSelectCard] = {}

        self.projectsScrollFrame = ScrollFrame(self.selectFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.projectsScrollFrame.packFrame.config(bg="grey55")
        self.projectsScrollFrame.pack(side="top", fill="both", expand=True, **packKwargs)
        self.projectsScrollFrame.hScroll.grid_forget()
        self.projectsScrollFrame.ConfigureCanvas(overrideWidth=256)

        #####################################################################################################################
        ##############################                Project Inspector                ######################################
        #####################################################################################################################

        self.selectedProjectVar = StringVar()
        self.selectedProjectVar.set("")
        self.selectedProjectVar.trace_add("write", self.Handle_ProjectSelected)

        self.inspector = ProjectInspecterFrame(self, None, self.handler, width=500, height=500, relief="ridge", bd=2)
        self.inspector.pack(side='left', fill="both", expand=True, **packKwargs)

        self.childInspecter = CycleInspectorFrame(self, self.handler, self.jira, self.GetLoadedProject)
        self.childInspecter.pack(side="left", fill="y", **packKwargs)
        self.inspector.SubscribeProjectItemSelectedEvent(self.childInspecter.AdoptChildren)

        #self.testButton = Button(self, text="Test", command=self.Click_TestButton)
        #self.testButton.pack()

        JiraType.PopulateImages()

    def GetLoadedProject(self) -> Project:
        return self.projectDict[self.selectedProjectVar.get()]

    def EventHandler_ProjectSelected(self, key:str):
        selectecedProject = self.selectedProjectVar.get()
        if selectecedProject != "":
            self.selectDict[selectecedProject].DeselectProject()

        self.selectedProjectVar.set(key)

    def Handle_ProjectSelected(self, var, index=-1, event=None):
        key = self.selectedProjectVar.get()
        self.inspector.ChangeLoadedProject(key, self.projectDict[key])

    def Click_TestButton(self):
        self.handler.AsyncWork(self.TestFunc, self.TestCallback)

    def TestFunc(self):
        return JiraAgent.GetAllIssueKeysInProject(self.jira, "MT")
    
    def AddProjectInfo(self, projectInfo:Dict[str, Any]):
        project = Project(self.jira, projectInfo)
        self.projectDict[project.key] = project

        self.AddProjectFrame(project)

    def AddProjectFrame(self, projectInfo:Project):
        temp = ProjectSelectCard(self.projectsScrollFrame.packFrame, projectInfo, self.handler)
        temp.SubscribeToClickEvent(self.EventHandler_ProjectSelected)
        self.selectDict[projectInfo.key] = temp
        temp.pack(side="top", fill="x", expand=True, **packKwargs)

        self.projectsScrollFrame.ConfigureCanvas()

    def SaveElements(self) -> Dict[str, Any]:
        tempProjectDict = {}
        itemsInProjects = {}
        for key, value in self.projectDict.items():
            value:Project
            tempProjectDict[key] = value.rawInfo
            itemsInProjects[key] = [item.issueDict for item in value.items.values()]
        return {
            "projects": tempProjectDict,
            "items": itemsInProjects
        }
    
    def RestoreElements(self, rDict:Dict[str, Any]):
        if rDict is None:
            return
        
        tempProjectDict = rDict.get("projects", {})
        itemsDict = rDict.get("items", {})

        for key, value in tempProjectDict.items():
            project = Project(self.jira, value)
            self.projectDict[key] = project
            self.projectDict[key].UpdateItems(itemsDict.get(key, []))
            self.AddProjectFrame(project)
            
    def TestCallback(self, returnObject):
        for issue in returnObject[1]:
             print(issue)
        JiraAgent.WriteDictToFile(returnObject[1], "MT_AllProjects.txt")

class AddProjectFrame(Frame):
    def __init__(self, parent:Frame, projectUI:ProjectViewerFrame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.mainUI = projectUI

        self.columnconfigure(0, weight=1)

        Label(self, text="Add Project", relief="sunken", bd=2, bg="grey75").grid(
            row=0, column=0, columnspan=2, **gridKwargs
        )

        self.entry = Entry(self)
        self.entry.grid(row=1, column=0, **gridKwargs)
        self.entry.insert(0, "MT")
        
        self.addButton = Button(self, text="Add", command=self.Click_AddProject)
        self.addButton.grid(row=1, column=1, **gridKwargs)

    def Click_AddProject(self):
        key = self.entry.get().strip()

        self.mainUI.handler.AsyncWork(JiraAgent.GetProject, self.Callback_ProcessProjectInfo, self.mainUI.jira, key)
        

    def Callback_ProcessProjectInfo(self, returnObject:Tuple[bool, Dict[str, Any]]):
        if not returnObject[0]:
            print("Failed to get project info")
            return
        
        self.mainUI.AddProjectInfo(returnObject[1])
     
class Project:
    def __init__(self, jiraInstance:JiraAgent.Jira, projectInfo:Dict[str, Any]):
        self.jira = jiraInstance
        self.rawInfo = projectInfo

        self.id = projectInfo["id"]
        self.key = projectInfo["key"]
        self.projectName = projectInfo["name"]

        self.items:Dict[str, Item] = []

        self.typeDict:Dict[str, List[str]] = {} # key will be issue type (eg: bug, task, epic...). Value will be list of issue keys with that issue type

    def UpdateItems(self, items:List[Dict[str, Any]]):
        self.items = {}
        for rawItem in items:
            item = Item(rawItem)
            self.items[item.key] = Item(rawItem)
        self.SortIssuesByType()

    def AddItems(self, items:List[Dict[str, Any]]):
        for rawItem in items:
            item = Item(rawItem)
            self.items[item.key] = Item(rawItem)
        self.SortIssuesByType()

    def SortIssuesByType(self):
        self.typeDict = {}
        for item in self.items.values():
            if item.issueType not in self.typeDict:
                self.typeDict[item.issueType] = [item.key]
            else:
                self.typeDict[item.issueType].append(item.key)

        #for key, value in self.items

    def GetItemsByType(self, itemType:str) -> List[str]:
        return self.typeDict.get(itemType, [])
    
    def GetItem(self, key:str) -> Item:
        return self.items[key]

class ProjectInspecterFrame(Frame):
    def __init__(self, parent:Frame, info:Project, asyncHandler:AsyncHandler, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.key = ""
        self.info = info
        self.handler = asyncHandler

        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        self.summaryFrame = Frame(self, width=500, height=100)
        self.summaryFrame.grid(row=0, column=0, columnspan=2, **gridKwargs)

        Label(self.summaryFrame, text="Project:").place(x=5, y=5)

        self.nameVar = StringVar()
        self.nameLabel = Label(self.summaryFrame, textvariable=self.nameVar)
        self.nameLabel.place(x=5, y=30, width=100)

        self.reqsOnlyVar = BooleanVar()
        self.reqsOnlyVar.set(True)
        self.requirementsOnlyCheckbox = Checkbutton(self, text="Only get Functional Requirements", variable=self.reqsOnlyVar)
        self.requirementsOnlyCheckbox.grid(row=1, column=0, columnspan=2, **gridKwargs)

        self.typesScrollFrame = ScrollFrame(self, width=1, bg="grey55", relief="sunken", bd=2)
        self.typesScrollFrame.packFrame.config(bg="grey55")
        self.typesScrollFrame.grid(row=2, column=0, **gridKwargs)
        self.typesScrollFrame.hScroll.grid_forget()
        self.typesScrollFrame.ConfigureCanvas(overrideWidth=125)

        self.itemsScrollFrame = ScrollFrame(self, width=1, bg="grey55", relief="sunken", bd=2)
        self.itemsScrollFrame.packFrame.config(bg="grey55")
        self.itemsScrollFrame.grid(row=2, column=1, **gridKwargs)
        self.itemsScrollFrame.hScroll.grid_forget()
        self.itemsScrollFrame.ConfigureCanvas(overrideWidth=125)

        self.typesSelected:List[str] = []

        self.projectItemSelectedEvents:List[Callable[[], List[Item]]] = []

    def SubscribeProjectItemSelectedEvent(self, func:Callable[[], List[Item]]):
        self.projectItemSelectedEvents.append(func)
    
    def CallProjectItemSelectedEvent(self, items:List[Item]):
        for func in self.projectItemSelectedEvents:
            func(items)

    def ChangeLoadedProject(self, key:str, info:Project):
        self.info = info

        self.UpdateProjectInfo()

    def UpdateProjectInfo(self):
        self.nameVar.set(self.info.projectName)

        self.typesScrollFrame.ClearControls_Pack()

        for itemType in self.info.typeDict:
            temp = IssueTypeCard(self.typesScrollFrame.packFrame, itemType, self.Handle_TypeSelectedEvent)
            temp.pack(side="top", fill="x", **packKwargs)
        self.typesScrollFrame.ConfigureCanvas(125)

    def Handle_TypeSelectedEvent(self, typeFrame:IssueTypeCard, isSelected:bool):
        if isSelected:
            self.typesSelected.append(typeFrame.issueType)
        else:
            self.typesSelected.remove(typeFrame.issueType)

        self.PackSelectedItemsByType()

    def PackSelectedItemsByType(self):
        self.itemsScrollFrame.ClearControls_Pack()

        for issueType in self.typesSelected:
            #keys = self.info.GetItemsByType(type)
            if self.reqsOnlyVar.get():
                jqlString = f"project = {self.info.key} AND issuetype = {issueType} AND labels = \"FunctionalRequirements\" ORDER BY created DESC"
            else:
                jqlString = f"project = {self.info.key} AND issuetype = {issueType}  ORDER BY created DESC"

            self.handler.AsyncWork(
                JiraAgent.GetJQL,
                self.Callback_GetItems,
                self.info.jira,
                jqlString
            )
                #item = self.info.GetItem(key)
                #temp = ItemFrame(self.itemsScrollFrame.packFrame, self.info.jira, item, self.handler)
                #temp.pack(side="top", fill="x", **packKwargs)
        self.itemsScrollFrame.ConfigureCanvas()

    def Callback_GetItems(self, returnObject):
        if not returnObject[0]:
            return
        
        for issueDict in returnObject[1]["issues"]:
            item = Item(issueDict)
            temp = ProjectItemCard(self.itemsScrollFrame.packFrame, self.info.jira, item, self.handler)
            temp.SubscribeToGetChildrenEvent(self.CallProjectItemSelectedEvent)
            temp.pack(side="top", fill="x", **packKwargs)

class ProjectSelectCard(Frame):
    SelectedColor = RGB(150, 230, 250)
    def __init__(self, parent:Frame, info:Project, asyncHandler:AsyncHandler, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.info = info
        self.handler = asyncHandler

        self.config(bd=2, relief="raised")

        self.isSelected = False

        self.Clicked:List[Callable[[str],None]] = []

        self.columnconfigure(1, weight=1)

        self.keyLabel = Label(self, text=self.info.key, relief="groove", bd=2, width=8)
        self.keyLabel.grid(row=0, column=0, **gridKwargs)

        self.nameLabel = Label(self, text=self.info.projectName, width=24, anchor="w")
        self.nameLabel.grid(row=0, column=1, columnspan=2, **gridKwargs)

        self._IssueCountLabel = Label(self, text="Items:")
        self._IssueCountLabel.grid(row=1, column=0, **gridKwargs)

        self.issueCountLabel = Label(self, text=len(self.info.items), relief="sunken", bd=2, bg="grey75")
        self.issueCountLabel.grid(row=1, column=1, **gridKwargs)

        self.refreshButton = LoadButton(self, text=u"\u21C5", command=self.GetNewIssues, width=2)
        self.refreshButton.UseCircleLoadingIcons()
        self.refreshButton.grid(row=1, column=2, **gridKwargs)

        self.refreshToolTip = ToolTip(self.refreshButton, "Click to find check and retreive new items")

        self.BindAll("<Button-1>", self.Handle_Click)
        self.BindAll("<Button-3>", self.Handle_RightClick)
        self.CreateRightClickMenu()

    def BindAll(self, eventKey:str, func:Callable):
        self.bind(eventKey, func)
        self.nameLabel.bind(eventKey, func)
        self._IssueCountLabel.bind(eventKey, func)
        self.issueCountLabel.bind(eventKey, func)
        self.refreshButton.bind(eventKey, func)

    def Handle_Click(self, event=None):
        if self.isSelected:
            self.DeselectProject()
        else:
            self.SelectProject()

    def SelectProject(self):
        for func in self.Clicked: # call first to handle desclection
            func(self.info.key)

        self.config(bg="cyan", relief="sunken", bd=2)
        self.keyLabel.config(bg=ProjectSelectCard.SelectedColor)
        self.nameLabel.config(bg=ProjectSelectCard.SelectedColor)
        self._IssueCountLabel.config(bg=ProjectSelectCard.SelectedColor)
        self.issueCountLabel.config(bg=RGB(75, 220, 220))
        self.refreshButton.config(bg=ProjectSelectCard.SelectedColor)

        self.isSelected = True

    def DeselectProject(self):

        self.config(bg="SystemButtonFace", relief="raised", bd=2)
        self.keyLabel.config(bg="SystemButtonFace")
        self.nameLabel.config(bg="SystemButtonFace")
        self._IssueCountLabel.config(bg="SystemButtonFace")
        self.issueCountLabel.config(bg="grey75")
        self.refreshButton.config(bg="SystemButtonFace")

        self.isSelected = False

    def SubscribeToClickEvent(self, func:Callable[[str],None]):
        self.Clicked.append(func)

    def MenuClick_Test(self):
        items = self.info.items

        allTasks = [item for item in items if item["fields"]["issuetype"]["name"] == "Epic"]

        for task in allTasks:
            print(task["key"])

    def CreateRightClickMenu(self):
        self.rightClickMenu = Menu(self, tearoff=0)

        self.rightClickMenu.add_command(label="Refresh All Items", command=self.GetAllIssues)

    def Handle_RightClick(self, event):
        try:
            self.rightClickMenu.tk_popup(event.x_root, event.y_root)
        finally:
            self.rightClickMenu.grab_release()

    def GetNewIssues(self):
        startCount = len(self.info.items)
        self.issueCountLabel.config(text=f"Fetching... Found: 0")
        self.refreshButton.StartLoading()
        self.handler.AsyncWork(JiraAgent.GetNewIssuesInProject, self.Callback_GetNewIssues, self.info.jira, self.info.key, 
                               UpdateFunc=self.Handle_GetAllItems_Update, startIndex=startCount)
    
    def Callback_GetNewIssues(self, returnObject:Tuple[bool, List[Dict[str, Any]]]):
        self.refreshButton.StopLoading()
        if not returnObject[0]:
            print("Failed to get items")
            return
        
        self.info.AddItems(returnObject[1])
        self.issueCountLabel.config(text=len(self.info.items))

    def GetAllIssues(self):
        self.issueCountLabel.config(text=f"Fetching... Found: 0")
        self.refreshButton.StartLoading()
        self.handler.AsyncWork(JiraAgent.GetAllIssuesInProject, self.Callback_GetIssues, self.info.jira, self.info.key, UpdateFunc=self.Handle_GetAllItems_Update)

    def Handle_GetAllItems_Update(self, newCount:int, totalCount:int):
        """Will be called by JiraAgen.GetAllIssuesInProject. Will give user updates while it retreives all issues from a project. 
        Likely called by seperate thread so will need to handle UI update 

        Args:
            newCount (int): _description_
            totalCount (int): _description_
        """

        self.handler.AsyncUiCall(lambda totalCount: self.issueCountLabel.config(text=f"Fetching... Found: {totalCount}"), totalCount)

    def Callback_GetIssues(self, returnObject:Tuple[bool, List[Dict[str, Any]]]):
        self.refreshButton.StopLoading()
        if not returnObject[0]:
            print("Failed to get items")
            return
        
        self.info.UpdateItems(returnObject[1])
        self.issueCountLabel.config(text=len(returnObject[1]))
        
class IssueTypeCard(Frame):
    def __init__(self, parent:Frame, issueType:str, clickEvent:Callable[[IssueTypeCard], None], *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.issueType = issueType

        self.config(width=120, height=25, bd=2, relief="raised")

        self.image = JiraType.LoadImageBasedOnType(self.issueType)

        self.typeCanvas = Canvas(self, height=20, width=20)
        self.typeCanvas.create_image(10,10, image=self.image)
        self.typeCanvas.place(x=3, y=1, height=20, width=20)

        self.typeLabel = Label(self, text=self.issueType)
        self.typeLabel.place(x=30, y=0)

        self.toggle = ToggleElement(self)
        self.toggle.AddControl(self, ProjectSelectCard.SelectedColor)
        self.toggle.AddControl(self.typeCanvas, ProjectSelectCard.SelectedColor)
        self.toggle.AddControl(self.typeLabel, ProjectSelectCard.SelectedColor)
        self.toggle.Subscribe(clickEvent)

class ProjectItemCard(ParentItemCard):
    def __init__(self, parent, jira, jiraItem, handler, width=300, height=110, *args, **kwargs):
        ParentItemCard.__init__(self, parent, jira, jiraItem, handler, width, height, *args, **kwargs)

        self.toggle = ToggleElement(self)
        self.toggle.AddControl(self)

        self.toggle.AddControl(self.typeCanvas)
        self.toggle.AddControl(self.summaryLabel, RGB(75, 220, 220))
        self.toggle.AddControl(self.keyLabel)
        self.toggle.AddControl(self._assigneLabel)
        self.toggle.AddControl(self._reporterLabel)
        self.toggle.AddControl(self.assigneeLabel)
        self.toggle.AddControl(self.reporterLabel)

        self.toggle.Subscribe(self.Handle_Toggle)

        self.AddToRightClick()
        self.lastChildIssues:List[Item] = []

        self.getChildrenEvents:List[Callable[[], List[Item]]] = []

    def SubscribeToGetChildrenEvent(self, func:Callable[[], List[Item]]):
        self.getChildrenEvents.append(func)

    def Handle_Toggle(self, frame:ProjectItemCard, isActive:bool):
        if isActive:
            self.Handle_GetChildren()
        else:
            pass


    def AddToRightClick(self):
        self.rightClickMenu.add_command(label="Get Children", command=self.Handle_GetChildren)

    def Handle_GetChildren(self):
        self.handler.AsyncWork(
            JiraAgent.GetLinkIssues,
            self.Callback_GetChildren,
            self.jira,
            self.item.key
        )

    def Callback_GetChildren(self, returnObject):
        if not returnObject[0]:
            print("Failed to get children")
            return
        
        values = returnObject[1]["issues"]
        childIssues = [Item(issue) for issue in values if issue["key"] != self.item.key]
        self.lastChildIssues = childIssues
        for func in self.getChildrenEvents:
            func(childIssues)
        #CycleInspectorFrame.instance.AdoptChildren(childIssues)

class CycleInspectorFrame(Frame):
    instance:CycleInspectorFrame = None
    def __init__(self, parent:Frame, asyncHandler:AsyncHandler, jira:JiraAgent.Jira, getProjFunc:Callable[[], Project], *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.handler = asyncHandler
        self.jira = jira
        self.GetLoadedProject = getProjFunc

        CycleInspectorFrame.instance = self

        frameWidth = 325

        self.cycleFrame = Frame(self, width=frameWidth, height=100)
        self.cycleFrame.pack(side="top", fill="x", **packKwargs)

        Label(self.cycleFrame, text="Create Testing Cycle", relief="sunken", bd=2, bg="grey75").place(
            x=3, y=3, width=frameWidth-6
        )

        self.cycleNameVar = StringVar()
        self.cycleNameVar.set("New_Testing_Cycle")
        self.cycleNameEntry = Entry(self.cycleFrame, textvariable=self.cycleNameVar)
        self.cycleNameEntry.place(x=3, y=25, width=frameWidth-6)

        self.createCycleButton = Button(self.cycleFrame, text="Create Test Cycle", command=self.CreateTestCycle)
        self.createCycleButton.place(x=3, y=50, width=frameWidth-6)


        ##############################################################################################################
        ##############################################################################################################

        self.childIssueScrollFrame = ScrollFrame(self, width=1, bg="grey55", relief="sunken", bd=2)
        self.childIssueScrollFrame.packFrame.config(bg="grey55")
        self.childIssueScrollFrame.pack(side="top", fill="both", expand=True)
        self.childIssueScrollFrame.hScroll.grid_forget()
        self.childIssueScrollFrame.ConfigureCanvas(overrideWidth=275)

        ##############################################################################################################
        ##############################################################################################################

        self.statusFrame = Frame(self, bd=2, relief="ridge", width=300, height=100)
        self.statusFrame.pack(side="top", fill="x")

        Label(self.statusFrame, text="Status", relief="sunken", bd=2, bg="grey75").place(
            x=3, y=3, width=frameWidth-6
        )

        Label(self.statusFrame, text="Epic:").place(
            x=3, y=30, width=30
        )

        self.epicLabel= Label(self.statusFrame, text="-", relief="sunken", bd=2, bg="grey75")
        self.epicLabel.place(x=35, y=30, width=150)


        ##############################################################################################################
        ##############################################################################################################

        self.childItems:List[Item] = []

    def CreateCycleEpic(self):
        fields = {
            "project": {"key": self.GetLoadedProject().key},
            "issuetype": {"name": "Epic"},
            "summary": self.cycleNameVar.get(),
            "labels": ["TestCycle"],
            "description": f"Testing cycle with {len(self.childItems)} item(s).",
        }

        self.handler.AsyncWork(
            JiraAgent.CreateAndGetItem,
            self.CallBack_CreateCycleEpic,
            self.jira,
            fields
        )

    def CallBack_CreateCycleEpic(self, returnObject):
        if not returnObject[0]:
            self.epicLabel.config(text="Failed to create Cycle Epic")
            return
        
        epicItem = Item(returnObject[1])
        self.epicLabel.config(text=f"Epic Created: {epicItem.key}")

        for childFrame in self.childIssueScrollFrame.packFrame.winfo_children():
            childFrame:ChildItemCard
            childFrame.AddItemToTestCycle(epicItem)
        

    def CreateTestCycle(self):
        numberOfChildren = len(self.childItems)

        result = messagebox.askyesno("Create Test Cycle", f"Are you sure you want to create\n\n\"{self.cycleNameVar.get()}\"\n\nTest cycle with {numberOfChildren} item(s)?")

        if not result:
            return
        
        self.CreateCycleEpic()

    def ClearChildren(self):
        self.childIssueScrollFrame.ClearControls_Pack()
        #self.childItems = []

    def AdoptChildren(self, adoptees:List[Item]):
        self.childItems += adoptees

        self.Repopulate()

    def AdoptChild(self, newChild:Item):
        self.childItems.append(newChild)

        self.Repopulate()

    def RemoveChildren(self, exiles:List[Item]):
        for item in exiles:
            self.childItems.remove(item)

        self.Repopulate()

    def Repopulate(self):
        self.ClearChildren()
        self.PackChildren()

    def PackChildren(self):
        for item in self.childItems:
            temp = ChildItemCard(self.childIssueScrollFrame.packFrame, self.jira, item, self.handler)
            temp.pack(side="top", fill="x", **packKwargs)

        self.childIssueScrollFrame.ConfigureCanvas()

class ChildItemCard(ParentItemCard):
    def __init__(self, parent, jira, jiraItem, handler, width=300, height=110, *args, **kwargs):
        ParentItemCard.__init__(self, parent, jira, jiraItem, handler, width, height, *args, **kwargs)

        self.statusChangeCanvas = Canvas(self, height=20, width=20, bd=0)
        self.statusCreatedImage = None
        self.statusChangeCanvas.place(x=145, y=6, height=20, width=20)

        self.progressVar = StringVar()
        self.progressVar.set("-")
        self.progressInfoLabel = Label(self, height=2, width=15, bg="grey75", relief="sunken", bd=2, textvariable=self.progressVar)
        self.progressInfoLabel.place(x=175, y=60)

        self.toggle = ToggleElement(self)
        self.toggle.AddControl(self)
        self.toggle.AddControl(self.typeCanvas)
        self.toggle.AddControl(self.summaryLabel, RGB(75, 220, 220))
        self.toggle.AddControl(self.keyLabel)
        self.toggle.AddControl(self._assigneLabel)
        self.toggle.AddControl(self._reporterLabel)
        self.toggle.AddControl(self.assigneeLabel)
        self.toggle.AddControl(self.reporterLabel)
        self.toggle.AddControl(self.statusChangeCanvas)
        self.toggle.SelectControl()


        self.AddToRightClick()

    def AddItemToTestCycle(self, epicItem:Item):
        if self.statusCreatedImage is not None:
            self.statusChangeCanvas.delete(self.statusCreatedImage)

        self.progressVar.set("Creating Test Case")

        itemKey = f"TC - {self.item.summary}"
        description = f"Test case for cycle: {epicItem.key} - \"{epicItem.summary}\"\nOriginal Description:\n{self.item.description}"

        fields = {
            "project": {"key": self.item.projectKey},
            "parent": {"key:": epicItem.key, "id": str(epicItem.id)},
            "issuetype": {"name": "Test"},
            "summary": itemKey,
            "description": description,
        }

        self.handler.AsyncWork(
            JiraAgent.CreateAndGetItem,
            self.Callback_CreateItemForTestCycle,
            self.jira,
            fields
        )

    def Callback_CreateItemForTestCycle(self, returnObject):
        if not returnObject[0]:
            self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=Item.errorImage)
            return
        
        childItem = Item(returnObject[1])
        self.progressVar.set("Test Case Created.\nLinking Issues")
        
        self.handler.AsyncWork(
            JiraAgent.LinkClonedIssue,
            self.Callback_LinkIssues,
            self.jira,
            childItem.key,
            self.item.key
        )
        
    def Callback_LinkIssues(self, returnObject):
        if not returnObject[0]:
            self.progressVar.set("Error")
            self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=Item.errorImage)
        else:
            self.progressVar.set("Success!")
            self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=Item.successImage)

    def AddToRightClick(self):
        self.rightClickMenu.add_command(label="Test Func", command=self.Handle_TestFun)

    def Handle_TestFun(self):
        self.handler.AsyncWork(
            JiraAgent.WriteIssueToFile,
            None,
            self.jira,
            "TUPCTOOL-33"
        )

    def Callback_TestFunc(self, returnObject):
        pass

def MainExitCall():
    jString = json.dumps(mainUI.SaveElements())

    with open(configPath, "w") as configFile:
        configFile.write(jString)
    
    tk.destroy()


def RestoreJiraElements():
        jiraConfigPath = "JadeResultParserConfig.txt"
        if not os.path.exists(jiraConfigPath):
            return 
        
        fileText = open(jiraConfigPath, "r").readline()

        restoreDict = json.loads(fileText)
        restoreDict = restoreDict["jira"]

        JiraAgent.userName = restoreDict.get("user", "")
        JiraAgent.TOKEN = restoreDict.get("token", None)

if __name__ == "__main__":
    tk = Tk()

    RestoreJiraElements()

    mainUI = ProjectViewerFrame(tk)
    mainUI.pack(side='top', fill="both", expand=True)
    #mainUI.Click_TestButton()

    if os.path.exists(configPath): 
        fileText = open(configPath, "r").readline()
        restoreDict = json.loads(fileText)
        mainUI.RestoreElements(restoreDict)

    tk.protocol("WM_DELETE_WINDOW", MainExitCall)

    tk.mainloop()