from __future__ import annotations
import os
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, IntVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image, Menu
import json
from typing import Dict, List, Tuple, Any, Callable
import re
import datetime
from queue import Queue
import threading
import time


from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


from TkinterSaver import RGB, packKwargs, gridKwargs, ScrollFrame, Button_ParseBool, Button_WorkStart, ToggleElement
from JiraControls import CreateBugFrame
from JiraItem import ItemCard, JiraItem, JiraType
from ResultFiles import ResultFile, TableFrame, JadeTableResult, ResultFrame
from AsyncHandler import AsyncHandler
import JiraAgent


class CycleExplorerUI(Frame):
    itemScrollWidth = 500
    def __init__(self, parent:Frame, GetResultDirFunc:Callable[[], str], handler:AsyncHandler=None, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.GetResultDir = GetResultDirFunc
        if handler is None:
            self.handler = AsyncHandler(self)
            self.handler.StartAsync()
        else:
            self.handler = handler

        self.jira = JiraAgent.CreateStaticJiraInstance()

        self.selectedCycleCard:CycleItemCard = None

        self.cycleSelectFrame = Frame(self)
        self.cycleSelectFrame.pack(side="left", fill="y", **packKwargs)

        self.testCycleScrollFrame = ScrollFrame(self.cycleSelectFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.testCycleScrollFrame.packFrame.config(bg="grey55")
        self.testCycleScrollFrame.pack(side="top", fill="y", expand=True, **packKwargs)
        self.testCycleScrollFrame.hScroll.grid_forget()
        self.testCycleScrollFrame.ConfigureCanvas(overrideWidth=300)

        self.scanForTestCycleButton = Button(self.cycleSelectFrame, text="Scan for Test Cycles", command=self.Click_ScanForCycles)
        self.scanForTestCycleButton.pack(side="bottom", fill="x", **packKwargs)

        self.itemsFoundFrame = Frame(self)
        self.itemsFoundFrame.pack(side="left", fill="y", **packKwargs)

        self.itemsScrollFrame = ScrollFrame(self.itemsFoundFrame, width=500, bg="grey55", relief="sunken", bd=2)
        self.itemsScrollFrame.packFrame.config(bg="grey55")
        self.itemsScrollFrame.pack(side="top", fill="y", expand=True, **packKwargs)
        self.itemsScrollFrame.hScroll.grid_forget()
        self.itemsScrollFrame.ConfigureCanvas(overrideWidth=CycleExplorerUI.itemScrollWidth)

        self.uploadAllButton = Button(self.itemsFoundFrame, text="Upload All Result File", command=self.Click_UploadAllResults)
        self.uploadAllButton.pack(side="bottom", fill="x", **packKwargs)

        #self.testButton = Button(self, text="Test Func", command=self.TestFunc)
        #self.testButton.pack(side="left")

        self.summaryFrame = SummaryFrame(self)
        self.summaryFrame.pack(side="left", fill="both", expand=True, **packKwargs)

        self.allResultFiles:List[ResultFile] = []

    def Click_ScanForCycles(self):
        self.Handle_GetTestCycles()

    def Click_UploadAllResults(self):
        self.uploadAllButton.WorkStart()

        self.handler.AsyncWork(
            self.UploadAllResults,
            self.Callback_UploadAllResultFiles
        )
        
    def UploadAllResults(self) -> bool:
        allTestingCards = self.itemsScrollFrame.packFrame.winfo_children()
        for itemFrame in allTestingCards:
            itemFrame:TestingItemCard
            itemFrame.ClearStatus()

        overallSuccess = True
        for itemFrame in allTestingCards:
            itemFrame:TestingItemCard
            if not itemFrame.ValidClonedBy:
                self.handler.AsyncUiCall(itemFrame.Failed, None)
                continue

            success = itemFrame.UploadAll_NotAsync()
            if success:
                self.handler.AsyncUiCall(itemFrame.Success, None)
            else:
                self.handler.AsyncUiCall(itemFrame.Failed, None)

            if not success:
                overallSuccess = False

        return overallSuccess

    def Callback_UploadAllResultFiles(self, returnObject:bool):
        self.uploadAllButton.ParseBool(returnObject)

    def GetListOfResultFiles(self) -> List[ResultFile]:
        return self.allResultFiles    

    def Handle_CycleCardToggled(self, card:CycleItemCard, isSelected:bool):
        if self.selectedCycleCard is not None:
            temp = self.selectedCycleCard
            self.selectedCycleCard = None
            self.itemsScrollFrame.ClearControls_Pack()
            temp.toggle.DeselectControl()
            

        if isSelected:
            self.selectedCycleCard = card
            self.Handle_GetChildrenOfSelectedCycle()
            self.summaryFrame.UpdateSelectedCycle(card)

    def Handle_GetChildrenOfSelectedCycle(self):
        jqlString = f"parent = {self.selectedCycleCard.item.key} ORDER BY created DESC"

        self.handler.AsyncWork(
            JiraAgent.GetJQL,
            self.Callback_GetChildrenOfSelectedCycle,
            self.jira,
            jqlString
        )

    def Callback_GetChildrenOfSelectedCycle(self, returnObject):
        success, itemInfos = returnObject
        if not success:
            return
        
        for itemInfo in itemInfos["issues"]:
            item = JiraItem(itemInfo)
            itemFrame = TestingItemCard(self.itemsScrollFrame.packFrame, self.jira, item, self.handler, self.GetListOfResultFiles)
            itemFrame.pack(side="top", **packKwargs)
            
        self.itemsScrollFrame.ConfigureCanvas()
        self.after(250, self.WaitForResultFileChecksToBeComplete)
    
    def WaitForResultFileChecksToBeComplete(self):
        allCycleItems = self.itemsScrollFrame.packFrame.winfo_children()
        allCycleItems:List[TestingItemCard]
        allFirstChecksCompleted = all(itemFrame.firstLook for itemFrame in allCycleItems)

        if not allFirstChecksCompleted:
            self.after(250, self.WaitForResultFileChecksToBeComplete)
            return
        
        self.summaryFrame.UpdateSummary(allCycleItems)

    def TestFunc(self):
        self.Handle_GetTestCycles()

    def Handle_GetTestCycles(self):
        self.testCycleScrollFrame.ClearControls_Pack()

        jqlString = f"project = \"DIGTOOLS\" AND issuetype = \"EPIC\" AND labels = \"TestCycle\" ORDER BY created DESC"

        self.handler.AsyncWork(
            JiraAgent.GetJQL,
            self.Callback_GetTestCycles,
            self.jira,
            jqlString
        )
                #item = self.info.GetItem(key)

        self.testCycleScrollFrame.ConfigureCanvas()

    def Callback_GetTestCycles(self, returnObject):
        if not returnObject[0]:
            return
        
        for issueDict in returnObject[1]["issues"]:
            item = JiraItem(issueDict)
            temp = CycleItemCard(self.testCycleScrollFrame.packFrame, self.jira, item, self.handler, self.Handle_CycleCardToggled)
            #temp.SubscribeToGetChildrenEvent(self.CallProjectItemSelectedEvent)
            temp.pack(side="top", fill="x", **packKwargs)

        self.testCycleScrollFrame.ConfigureCanvas()

    def UpdateAllInputFiles(self):
        self.allResultFiles = self.ParseAllFilesFromInput(self.GetResultDir())

    def ParseAllFilesFromInput(self, dirPath:str, topLevelPath:str=None) -> List[ResultFile]:
        if topLevelPath is None:
            topLevelPath = dirPath
        allFiles:List[ResultFile] = []
        for file in os.listdir(dirPath):
            absPath = os.path.join(dirPath, file)
            if os.path.isdir(absPath):
                moreFiles = self.ParseAllFilesFromInput(absPath, dirPath)
                allFiles += moreFiles
            else:
                relPath = os.path.relpath(absPath, topLevelPath)
                rFileObject = ResultFile(topLevelPath, relPath)
                rFileObject.parser.ParseResultFile()
                allFiles.append(rFileObject)


        return allFiles

class CycleItemCard(ItemCard):
    def __init__(self, parent, jira, jiraItem, handler, parentToggleFunc:Callable[[Frame, bool],None], width=300, height=110, *args, **kwargs):
        ItemCard.__init__(self, parent, jira, jiraItem, handler, width, height, *args, **kwargs)
        self.parentToggleFunc = parentToggleFunc

        self.toggle = ToggleElement(self)
        self.toggle.Subscribe(self.Handle_Toggled)

        self.toggle.AddControlAndAllChildren(self)

    def Handle_Toggled(self, control:Frame, isSelected:bool):
        self.parentToggleFunc(control, isSelected)

class TestingItemCard(ItemCard):
    def __init__(self, parent, jira, jiraItem, handler, GetResultFilesFunc:Callable[[], List[ResultFile]], width=490, height=110, *args, **kwargs):
        ItemCard.__init__(self, parent, jira, jiraItem, handler, width, height, *args, **kwargs)
        self.GetResultFiles = GetResultFilesFunc
        self.clonedByItem:JiraItem = None
        self.foundResultFiles:List[ResultFile] = []
        self.firstLook = False # will be set to True once a check is performed to find the result file. 

        self.DeplaceLabels(self._reporterLabel, self.reporterLabel)

        Label(self, text="Cloned from:").place(
            x=150, y=6, width=70
        )

        self.parentKeyLabel = Label(self, text="Waiting...", relief="ridge", bd=2)
        self.parentKeyLabel.place(x=223, y=6, width=120)

        if not self.GetClonedByItem(): # will call self.LookForResultFile in callback.
            self.parentKeyLabel.config(text="Not Found")

        self.fileLabel = Label(self, text="Waiting...", relief="sunken", bd=2, justify="left", anchor="w", bg="grey75")
        self.fileLabel.place(x=3, y=60, width=width-8)

        self.statusChangeCanvas = Canvas(self, height=20, width=20, bd=0)
        self.statusCreatedImage = None
        self.statusChangeCanvas.place(x=250, y=82, height=20, width=20)


        self._pfLabel = Label(self, text="PF %")
        self._pfLabel.place(x=300, y=85, width=30)
        
        self.pfLabel = Label(self, text="-", relief="sunken", bd=2, bg="grey75")
        self.pfLabel.place(x=335, y=85, width=40)

    def UploadAll_NotAsync(self) -> bool:
        overAllSuccess = True
        for resultFile in self.foundResultFiles:
            (outputSuccess, response) = JiraAgent.AttachFile(self.jira, self.item.key, resultFile.absolutePath)
            (inputSuccess, response) = JiraAgent.AttachFile(self.jira, self.item.key, resultFile.inputFilePath)
            if not (outputSuccess and inputSuccess):
                overAllSuccess = False

        return overAllSuccess

    def ClearStatus(self, *args):
        if not self.statusCreatedImage is None:
            self.statusChangeCanvas.delete(self.statusCreatedImage)

    def Success(self, *args):
        self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=JiraItem.successImage)

    def Failed(self, *args):
        self.statusCreatedImage = self.statusChangeCanvas.create_image(10,10, image=JiraItem.errorImage)

    def LookForResultFile(self):
        if not self.ValidClonedBy:
            self.firstLook = True
            return
        
        allResultFiles = self.GetResultFiles()

        for resFile in allResultFiles:
            for req in resFile.reqs:
                if req == self.clonedByItem.key:
                    self.foundResultFiles.append(resFile)
                    
        count = len(self.foundResultFiles)
        if count == 0:
            self.fileLabel.config(text="No result files found", bg="lightsalmon")
        elif count == 1:
            self.fileLabel.config(text=self.foundResultFiles[0].pathFromInputDir)
        else:
            self.fileLabel.config(text=f"{self.foundResultFiles[0].pathFromInputDir} + {count-1} others")

        self.GetPfValue()
        self.firstLook = True

    def GetPfValue(self):
        count = len(self.foundResultFiles)
        if count > 0:
            pfPercent = self.foundResultFiles[0].pfPercent
            bgColor = "lightgreen" if pfPercent == 100 else "lightsalmon"
            self.pfLabel.config(text=f"{pfPercent:.1f}", bg=bgColor)
        else:
            self.pfLabel.config(text="?", bg="orange")

    @property
    def ValidClonedBy(self) -> bool:
        return self.clonedByItem is not None
        
    def GetClonedByItem(self) -> bool:
        links = self.item.fields.get("issuelinks", [])

        for linkedIssue in links:
            inwardType = linkedIssue["type"]["inward"]
            if inwardType == "is cloned by":
                outwardKey = linkedIssue["outwardIssue"]["key"]
                self.handler.AsyncWork(
                    JiraAgent.GetJiraItem,
                    self.Callback_GetClonedFromItem,
                    self.jira,
                    outwardKey
                )
                return True
        
        return False
    
    def Callback_GetClonedFromItem(self, returnObject):
        success, itemInfo = returnObject
        if not success:
            return
        self.clonedByItem = JiraItem(itemInfo)

        self.parentKeyLabel.config(text=self.clonedByItem.key)

        self.LookForResultFile()

class SummaryFrame(Frame):
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        Label(self, text="Cycle Selected:").place(x=3, y=3)

        self.cycleNameVar = StringVar()
        self.cycleNameVar.set("-")
        self.cycleNameLabel = Label(self, textvariable=self.cycleNameVar, relief="sunken", bd=2, bg="grey55")
        self.cycleNameLabel.place(x=90, y=3, width=400)

        Label(self, text="Items Found:").place(x=3, y=30)
        self.itemsFoundVar = IntVar()
        self.itemsFoundLabel = Label(self, textvariable=self.itemsFoundVar, relief="sunken", bd=2, bg="grey55")
        self.itemsFoundLabel.place(x=90, y=30, width=30)

        
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.bars = self.ax.bar(["Pass", "Fail", "Unknown"], [0, 0, 0], color=["green", "red", "orange"])

        self.ax.set_ylabel("Test Case Count")


        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().place(x=3, y=200, width=450, height=250)

    def UpdateSelectedCycle(self, cycleCard:CycleItemCard):
        self.cycleNameVar.set(cycleCard.item.summary)

    def UpdateSummary(self, testFrames:List[TestingItemCard]):
        self.itemsFoundVar.set(len(testFrames))

        passCount = 0
        failCount = 0
        unknownCount = 0

        for cFrame in testFrames:
            if cFrame.ValidClonedBy:
                try:
                    pf = cFrame.foundResultFiles[0].pfPercent
                except IndexError:
                    pf = -1
                    unknownCount += 1
                else:
                    if pf == 100:
                        passCount += 1
                    else:
                        failCount += 1
            else:
                unknownCount += 1

        self.UpdateGraph([passCount, failCount, unknownCount])

    def UpdateGraph(self, counts:Tuple[int, int, int]):
        for bar, newCount in zip(self.bars, counts):
            bar.set_height(newCount)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

def DummyGetResultDir() -> str:
    return r"C:\Users\E0498617\Documents\Local Scripts\Results"


if __name__ == "__main__":
    tk = Tk()

    ui = CycleExplorerUI(tk, DummyGetResultDir)
    ui.pack(side="top", fill="both", expand=True, **packKwargs)
    JiraType.PopulateImages()
    
    ui.Handle_GetTestCycles()

    tk.mainloop()

