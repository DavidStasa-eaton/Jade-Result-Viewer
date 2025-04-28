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
import pandas as pd
import difflib

from TkinterSaver import RGB, packKwargs, gridKwargs, ScrollFrame, Button_ParseBool, Button_WorkStart, AskForFile
from ProjectExplorer import Project, ProjectSelectCard
from JiraItem import JiraItem, ItemCard, JiraType
from AsyncHandler import AsyncHandler

import JiraAgent

configPath = "Uploader_Config.txt"

class JiraUploaderFrame(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.fieldsList = [
            ["Project"],
            ["Parent"],
            ["Issue Type", "Type"],
            ["Summary", "Title"],
            ["Description"], 
            ["Fix Version"], 
            ["Assignee"], 
            ["Sprint"]
        ]

        self.handler = AsyncHandler(self)
        self.jira = JiraAgent.CreateStaticJiraInstance()
        self.handler.StartAsync()
        self.keyPairs:List[Tuple[str, str]] = [] # first arg will be property key used by Jira. Second key will be key used by excel sheet
        self.itemToUploadCardList:List[ItemToUploadFrame] = []
        self.projectsFoundList:List[str] = []
        self.parentsFoundDict:Dict[str, ProjectSelectCard] = {}

        self.filePathVar = StringVar()
        self.filePathVar.trace_add("write", self.FilePathChanged)

        self.topFrame = Frame(self, bg="grey55", relief="sunken", bd=2)
        self.topFrame.pack(side="top", fill="x")
        self.projectFrame = Frame(self, relief="ridge", bd=2, height=55)
        self.projectFrame.pack(side="top", fill="x", **packKwargs)
        self.parentsFrame = Frame(self, relief="ridge", bd=2, height=55)
        self.parentsFrame.pack(side="top", fill="x", **packKwargs)
        self.botFrame = Frame(self)
        self.botFrame.pack(side="top", fill="both", expand=True)

        self.askForFileButton = Button(self.topFrame, text="Select File", command=self.AskForFile)
        self.askForFileButton.pack(side="left", **packKwargs)

        self.filePathLabel = Entry(self.topFrame, textvariable=self.filePathVar, width=160)
        self.filePathLabel.pack(side="left", fill="x", expand=True, **packKwargs)

        ###########################################################################################################3

        self.expectedFieldsFrame = ScrollFrame(self.botFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.expectedFieldsFrame.packFrame.config(bg="grey55")
        self.expectedFieldsFrame.pack(side="left", fill="y", **packKwargs)
        self.expectedFieldsFrame.hScroll.grid_forget()
        self.expectedFieldsFrame.ConfigureCanvas(overrideWidth=200)

        self.itemToUploadFrame = ScrollFrame(self.botFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.itemToUploadFrame.packFrame.config(bg="grey55")
        self.itemToUploadFrame.pack(side="left", fill="both", expand=True, **packKwargs)
        self.itemToUploadFrame.hScroll.grid_forget()
        #self.itemToUploadFrame.ConfigureCanvas(overrideWidth=150)

        self.df = None
        self.headers = []

        self.PackExpectedFieldsFrame()

        # test code, delete
        self.filePathVar.set("C:/Users/E0498617/Desktop/Jira booklet for Passcode.xlsx")

    def AskForFile(self):
         self.filePathVar.set(AskForFile("Select Excel Sheet", [("Excel Files", "*.xlsx *.xls"), ("All Files", "*")]))

    def FilePathChanged(self, *args):
        if not os.path.exists(self.filePathVar.get()):
            self.filePathLabel.config(bg="lightsalmon")
            return
        else:
            self.filePathLabel.config(bg="white")

        self.df = pd.read_excel(self.filePathVar.get())
        self.headers = list(self.df.columns)
        self.UpdateFieldFrames() # updates frame on the left with the column headers defined in the excel sheet. 
        self.GenerateItemCards()
        self.GetAndLookupUniqueProjects()
        self.GetAndLookupParentInfo()
        #for head in self.headers:
        #    closest = difflib.get_close_matches(
        #        head,
        #        self.fieldsList, 
        #        n=1, cutoff=0.6
        #    )
        #    print(f"Head: {head} ::: Closest: {closest}")
        #for index, row in self.df.iterrows():
        #    print(f"Index: {index} ::: Summary: {row["Summary"]}")

    def UpdateFieldFrames(self):
        for fFrame in self.GetListOfFieldFrames():
            fFrame.UpdateHeaderValues(self.headers)

    def GenerateItemCards(self):
        keyPairs = []
        for fFrame in self.GetListOfFieldFrames():
            keyPairs.append(fFrame.GetKeysForJiraAndExcel())

        self.itemToUploadCardList = []
        for index, row in self.df.iterrows():
            uInfo = UploadInfo.FromRow(row, keyPairs, self.LookupParentCard)
            temp = ItemToUploadFrame(self.itemToUploadFrame.packFrame, uInfo, self.jira, self.handler)
            temp.pack(side='top')
            self.itemToUploadCardList.append(temp)

    def GetAndLookupUniqueProjects(self):
        if len(self.itemToUploadCardList) == 0:
            return
        
        uniqueProjects = {getattr(card.uploadInfo, "project") for card in self.itemToUploadCardList}

        self.projectsFoundList = []
        widgets = self.projectFrame.winfo_children()
        for control in widgets:
            self.projectFrame.pack_forget(control)

        for key in uniqueProjects:
            self.GetProjectInfo(key)

    def GetProjectInfo(self, key:str):
        self.handler.AsyncWork(JiraAgent.GetProject, self.Callback_ProcessProjectInfo, self.jira, key)
        
    def Callback_ProcessProjectInfo(self, returnObject:Tuple[bool, Dict[str, Any]]):
        if not returnObject[0]:
            print("Failed to get project info")
            return
        
        projectInfo = Project(self.jira, returnObject[1])
        card = ProjectSelectCard(self.projectFrame, projectInfo, self.handler)
        card.pack(side="left", **packKwargs)
        self.projectsFoundList.append(projectInfo.key)

    def GetAndLookupParentInfo(self):
        if len(self.itemToUploadCardList) == 0:
            return
        
        uniqueParents = {getattr(card.uploadInfo, "parent") for card in self.itemToUploadCardList}

        self.parentsFoundDict = {}
        widgets = self.parentsFrame.winfo_children()
        for control in widgets:
            self.parentsFrame.pack_forget(control)

        for key in uniqueParents:
            self.GetParentInfo(key)

    def GetParentInfo(self, key:str):
        self.handler.AsyncWork(JiraAgent.GetJiraItem, self.Callback_ProcessParentInfo, self.jira, key)
        
    def Callback_ProcessParentInfo(self, returnObject:Tuple[bool, Dict[str, Any]]):
        if not returnObject[0]:
            print("Failed to get jira item info")
            return
        
        itemInfo = JiraItem(returnObject[1])
        card = ItemCard(self.parentsFrame, self.jira, itemInfo, self.handler)
        card.config(relief="ridge", bd=2)
        card.pack(side="left", **packKwargs)
        self.parentsFoundDict[itemInfo.key] = card

    def LookupParentCard(self, key):
        return self.parentsFoundDict.get(key, None)


    def PackExpectedFieldsFrame(self):
        self.expectedFieldsFrame.ClearControls_Pack()
        for expectedHeader in self.fieldsList:
            temp = FieldFrame(self.expectedFieldsFrame.packFrame, self.fieldsList, expectedHeader)
            temp.pack(side="top", fill="both", **packKwargs)

        self.expectedFieldsFrame.ConfigureCanvas()
        
    def GetListOfFieldFrames(self) -> List[FieldFrame]:
        return self.expectedFieldsFrame.packFrame.winfo_children()

class FieldFrame(Frame):
    def __init__(self, frame, validFields:List[str], expectedFields:List[str], *args, **kwargs):
        Frame.__init__(self, frame, *args, **kwargs)

        self.columnconfigure(1, weight=1)

        self.validFields = validFields
        self.expectedField = expectedFields[0]
        self.allExpected = expectedFields

        self.expectedLabel = Label(self, text=self.expectedField, relief="sunken", bd=2, bg="grey55")
        self.expectedLabel.grid(row=0, column=0, columnspan=2, **gridKwargs)

        Label(self, text="Header:").grid(row=1, column=0, **gridKwargs)

        self.selectFieldCombobox = ttk.Combobox(self)
        self.selectFieldCombobox.grid(row=1, column=1, **gridKwargs)

        self.percentMatchLabel = Label(self, text="-", width=5)
        self.percentMatchLabel.grid(row=2, column=0, **gridKwargs)

    def UpdateHeaderValues(self, excelHeaders:List[str], expectedIndex:int=0):
        expected = self.allExpected[expectedIndex]

        self.selectFieldCombobox.config(values=excelHeaders)

        closest = difflib.get_close_matches(
                expected,
                excelHeaders, 
                n=1, cutoff=0.6
            )
        
        if closest:
            value = closest[0]
            sim = difflib.SequenceMatcher(None, value, expected).ratio()
            self.percentMatchLabel.config(text=round(sim, 3))
            self.expectedLabel.config(bg="lightgreen")
            self.selectFieldCombobox.set(closest)
        else:
            expectedIndex += 1
            if expectedIndex >= len(self.allExpected):
                self.expectedLabel.config(bg="lightsalmon")
            else:
                self.UpdateHeaderValues(excelHeaders, expectedIndex)
        
    def GetKeysForJiraAndExcel(self) -> Tuple[str, str]:
        return [self.expectedField, self.selectFieldCombobox.get()]

class ItemToUploadFrame(Frame):
    width = 750
    height = 185
    def __init__(self, frame, uploadInfo:UploadInfo, jira, asyncHandler:AsyncHandler, *args, **kwargs):
        Frame.__init__(self, frame, *args, **kwargs)
        self.uploadInfo = uploadInfo
        self.jira = jira
        self.handler = asyncHandler

        self.config(relief="ridge", bd=2, width=ItemToUploadFrame.width, height=ItemToUploadFrame.height)

        Label(self, text=uploadInfo.project, relief="groove", bd=2).place(x=3, y=3, width=100)
        Label(self, text=uploadInfo.summary, relief="sunken", bd=2, bg="grey55").place(x=106, y=3, width=ItemToUploadFrame.width - 112)

        xLeftFields = 75
        fieldKwargs = dict(relief="sunken", bd="2", width=20, bg="grey55")

        Label(self, text="Parent:").place(x=3, y=30)
        Label(self, text=uploadInfo.parent, **fieldKwargs).place(x=xLeftFields, y=30)

        self.image = JiraType.LoadImageBasedOnType(uploadInfo.issueType)
        Label(self, text="Type:").place(x=3, y=55)
        Label(self, text=uploadInfo.issueType, relief="sunken", bd="2", width=17, bg="grey55").place(x=xLeftFields+20, y=55)
        self.typeCanvas = Canvas(self, height=20, width=20)
        self.typeCanvas.create_image(10,10, image=self.image)
        self.typeCanvas.place(x=xLeftFields, y=55, height=20, width=20)


        Label(self, text="Assignee:").place(x=3, y=80)
        Label(self, text=uploadInfo.assignee, **fieldKwargs).place(x=xLeftFields, y=80)

        Label(self, text="Sprint:").place(x=3, y=105)
        Label(self, text=uploadInfo.sprint, **fieldKwargs).place(x=xLeftFields, y=105)

        Label(self, text="Fix Version:").place(x=3, y=130)
        Label(self, text=uploadInfo.fixVersion, **fieldKwargs).place(x=xLeftFields, y=130)

        Label(self, text=uploadInfo.description, relief='sunken', bd=2, bg="grey75", ).place(
                  x=xLeftFields + 160, y = 30, height=120, width=ItemToUploadFrame.width - 245
              )
        
        self.uploadFrame = Frame(self, relief="groove", bd=2)
        self.uploadFrame.place(x=3, y=155, width=ItemToUploadFrame.width - 6)

        self.uploadButton = Button(self.uploadFrame, text="Upload", command=self.Click_UploadItem)
        self.uploadButton.pack(side="left", **packKwargs)

        self.statusLabel = Label(self.uploadFrame, text="-", anchor="w", relief="sunken", bd=2, bg="grey55", width=50)
        self.statusLabel.pack(side="left", **packKwargs)

    def Click_UploadItem(self):
        self.statusLabel.config(text=f"Creating Jira Item")
        Button_WorkStart(self.uploadButton)
        #JiraAgent.CreateAndGetItem(self.jira, {})
        fields = self.uploadInfo.Json()
        self.handler.AsyncWork(JiraAgent.CreateAndGetItem,
                               self.Callback_UploadItem,
                               self.jira,
                               fields)

    def Callback_UploadItem(self, returnObject):
        Button_ParseBool(self.uploadButton, returnObject[0])
        if not returnObject[0]:
            return
        
        item = JiraItem(returnObject[1])
        self.statusLabel.config(text=f"Succesfully created item: {item.key}")
        
class UploadInfo:
    def __init__(self, lookupFunc:Callable[[], ItemCard], project:str, summary:str, issueType:str, parent="", description:str="", fixVersion:str="", assignee:str="", sprint=""):
        self.lookupFunc:Callable[[], ItemCard] = lookupFunc
        self.project = project
        self.summary = summary      
        self.issueType = issueType
        self.parent = parent
        self.description = description      
        self.fixVersion = fixVersion      
        self.assignee = assignee      
        self.sprint = sprint
        
    def Json(self):
        #fields = {
        #    "project": {"key": self.GetLoadedProject().key},
        #    "issuetype": {"name": "Epic"},
        #    "summary": self.cycleNameVar.get(),
        #    "labels": ["TestCycle"],
        #    "description": f"Testing cycle with {len(self.childItems)} item(s).",
        #}

        rDict = {
            "project": {"key": self.project},
            "issuetype": {"name": self.issueType},
            "summary": self.summary,
        }

        #"parent": {"key:": epicItem.key, "id": str(epicItem.id)},

        if self.parent != "":
            card = self.lookupFunc(self.parent)
            card:ItemCard

            values = {"key": card.item.key, "id": str(card.item.id)}
            rDict["parent"] = {"key": card.item.key, "id": str(card.item.id)}

        #rDict = self.AddToDictIfNotEmpty(rDict, "parent", self.parent)
        rDict = self.AddToDictIfNotEmpty(rDict, "description", self.description)
        #rDict = self.AddToDictIfNotEmpty(rDict, "fixversion", self.fixVersion)
        #rDict = self.AddToDictIfNotEmpty(rDict, "assignee", self.assignee)
        #rDict = self.AddToDictIfNotEmpty(rDict, "sprint", self.sprint)

        return rDict

    def AddToDictIfNotEmpty(self, rDict, skey, valueToAdd):
        if valueToAdd == "":
            return rDict
        
        rDict[skey] = valueToAdd

        return rDict

    @classmethod
    def FromRow(cls, row:pd.DataFrame, keyLookupPairs:List[Tuple[str, str]], lookupFunc):
        project = ""
        parent = ""
        summary = ""
        issueType = ""
        description = ""
        fixVersion = ""
        assignee = ""
        sprint = ""
        
        for keyPair in keyLookupPairs:
            jiraValue = keyPair[0]
            excelHeader = keyPair[1]

            


            if jiraValue == "Project":
                project = row[excelHeader]
            elif jiraValue == "Parent":
                parent = row[excelHeader]
            elif jiraValue == "Summary":   
                summary = row[excelHeader]
            elif jiraValue == "Issue Type":
                issueType = row[excelHeader]
            elif jiraValue == "Description":
                description = row[excelHeader]
            elif jiraValue == "Fix Version":
                fixVersion = row[excelHeader]
            elif jiraValue == "Assignee":
                assignee = row[excelHeader]
            elif jiraValue == "Sprint":
                sprint = row[excelHeader]

        return cls(lookupFunc, project, summary, issueType, parent, description, fixVersion, assignee, sprint)



def MainExitCall():
    tk.destroy()
    quit()

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

if __name__ == "__main__":
    tk = Tk()

    RestoreJiraElements()

    JiraType.PopulateImages()
    mainUI = JiraUploaderFrame(tk)
    mainUI.pack(side='top', fill="both", expand=True)
    #mainUI.Click_TestButton()

    if os.path.exists(configPath): 
        fileText = open(configPath, "r").readline()
        restoreDict = json.loads(fileText)
        #mainUI.RestoreElements(restoreDict)

    tk.protocol("WM_DELETE_WINDOW", MainExitCall)
    

    tk.mainloop()