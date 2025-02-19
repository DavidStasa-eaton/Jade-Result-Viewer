
from __future__ import annotations
import os
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image
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

class MainUI(Toplevel):
    instance = None
    def __init__(self, tk:Tk, *args, **kwargs):
        Toplevel.__init__(self, tk, *args, **kwargs)

        IssueFrame.PopulateImages()

        MainUI.instance = self

        self.ioFrame = IOFrame(self)
        self.ioFrame.pack(side="left", anchor='n')
        self.ioFrame.fileSelectedEvents.append(self.Handle_FileSelected)

        self.parentJiraFrame = Frame(self)
        self.jiraFrame = JiraFrame(self.parentJiraFrame)
        self.bugFrame = CreateBugFrame(self.parentJiraFrame)

        self.resultFrame = ResultViewerFrame(self)
        self.resultFrame.pack(side="left", fill="both", expand=True)

        self.parentJiraFrame.pack(side="left", fill="both", expand=True)

        if JiraAgent.jiraImported:
            self.jiraFrame.pack(side="top", fill="both", expand=True)
            #self.bugFrame.pack(side="top", fill="both")
            self.resultFrame.DoneLoadingEvents.append(self.jiraFrame.Callback_ResultFileLoaded)


        self.RestoreElements()

    def Handle_FileSelected(self, rFile:ResultFile):
        self.resultFrame.LoadResultFile(rFile)

    def SaveElements(self):
        saveDict:Dict[str, Any] = {
            "io": self.ioFrame.SaveElements(),
            "jira": self.jiraFrame.SaveElements()
        }

        jString = json.dumps(saveDict)

        with open(configPath, "w") as configFile:
            configFile.write(jString)

    def RestoreElements(self):
        if not os.path.exists(configPath):
            return 
        
        fileText = open(configPath, "r").readline()

        restoreDict = json.loads(fileText)

        if JiraAgent.jiraImported:
            self.jiraFrame.RestoreElements(restoreDict.get("jira", None))
        self.ioFrame.RestoreElements(restoreDict.get("io", None))

        if JiraAgent.jiraImported:
            self.after(1000, self.jiraFrame.StartJiraComms)
            
class ResultViewerFrame(Frame):  
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.selectedResultFile:ResultFile = None
        self.inputFilePath = ""
        self.fileLines:List[str] = []

        self.tableDict:Dict[int, TableResult] = {}
        
        self.summaryFrame = Frame(self, height=100, relief="groove", bd=4)
        self.summaryFrame.pack(side="top", fill="x")

        self.summaryFrame.columnconfigure(1, weight=1)

        Label(self.summaryFrame, text="Selcted File:").place(
            x=0, y=0
        )

        Label(self.summaryFrame, text="File Name:").place(
            x=0, y=30
        )

        self.fullPathVar = StringVar()
        self.absoluateLabel = Label(self.summaryFrame, textvariable=self.fullPathVar, relief="sunken", bd=2, bg="grey65", anchor="w")
        self.absoluateLabel.place(x=75, y=0, relwidth=.85)

        self.fileNameVar = StringVar()
        self.fileNameLabel = Label(self.summaryFrame, textvariable=self.fileNameVar, relief="sunken", bd=2, bg="grey65", anchor="w")
        self.fileNameLabel.place(x=75, y=30, width=300)

        Label(self.summaryFrame, text="Tables Found:").place(
            x=380, y=30
        )
        self.tableCountVar = StringVar()
        self.tableCountLabel = Label(self. summaryFrame, textvariable=self.tableCountVar, relief="sunken", bd=2, bg="grey65")
        self.tableCountLabel.place(x=460, y = 30, width=20)


        ##############################################################################################################
        #######################################          Viewer Frame        #########################################
        ##############################################################################################################

        self.viewerFrame = Frame(self)
        self.viewerFrame.pack(side="top", fill='both', expand=True)

        self.viewerFrame.columnconfigure(0, minsize=100)
        self.viewerFrame.columnconfigure(1, weight=1)
        self.viewerFrame.rowconfigure(0, weight=1)



        self.text = Text(self.viewerFrame, wrap="none")
        self.text.grid(row=0, column=1, sticky="wens")
        self.tagIndex = 1

        self.xScrollBar = Scrollbar(self.viewerFrame, orient="horizontal")
        self.xScrollBar.grid(row=1, column=1, sticky="wens")

        self.yScrollBar = Scrollbar(self.viewerFrame)
        self.yScrollBar.grid(row=0, column=2, sticky="wens")

        self.tablesScrollFrame = ScrollFrame(self.viewerFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.tablesScrollFrame.packFrame.config(bg="grey55")
        self.tablesScrollFrame.grid(row=0, column=0, sticky="wens")
        self.tablesScrollFrame.hScroll.grid_forget()
        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=256)

        ##############################################################################################################

        self.DoneLoadingEvents:List[Callable[[str, str, List[TableResult]], None]] = []

    def PopulateTableFrames(self):
        for child in self.tablesScrollFrame.packFrame.winfo_children():
            child:Frame
            child.grid_forget()
            child.destroy()

        for value in self.tableDict.values():
            f = TableFrame(self.tablesScrollFrame.packFrame, value, self.Handle_TableClicked, height=60, width=250)
            f.pack(side="top", fill="both", expand=True, pady=3, padx=3)
        self.tablesScrollFrame.ConfigureCanvas(overrideWidth=256)

    def DeleteAllTags(self):
        tags = self.text.tag_names()
        for tag in tags:
            self.text.tag_delete(tag)

    def ClearLog(self):
        self.text.delete(1.0, END)
        self.DeleteAllTags()
        self.tagIndex = 1

    def AddTag(self, tagName, lineLength, **formatDict):
        tagStart = f"{self.tagIndex}.0"
        tagEnd = f"{self.tagIndex}.{lineLength}"
        self.text.tag_add(tagName, tagStart, tagEnd)
        self.text.tag_config(tagName, **formatDict)

    def PopulateSummary(self):
        if self.selectedResultFile is None:
            return
        
        self.fullPathVar.set(self.selectedResultFile.absolutePath)
        self.fileNameVar.set(self.selectedResultFile.fileName)
        self.tableCountVar.set(len(self.tableDict))

    def LoadResultFile(self, resultFile:ResultFile):
        if not os.path.exists(resultFile.absolutePath):
            return
        
        self.selectedResultFile = resultFile
        
        
        self.ClearLog()

        self.tableDict = {}
        lastTableFound:TableResult = None
        with open(resultFile.absolutePath, "r") as rFile:
            self.fileLines = rFile.readlines()
            index = 0
            for line in self.fileLines:
                if re.match(r"^#Table:\s(?!.*::: )", line): # the "#Table:" match will be found twice. Once for header. once for footer. The non capture group ":::" only appears in footer
                    self.tableDict[index] = TableResult(line, index, self.fileLines[index:])
                    lastTableFound = self.tableDict[index]
                elif line.startswith("#Input File :   "):
                    self.inputFilePath = line[16:].strip()

                self.InsertLineWithFormmating(line, lastTableFound)
                #self.text.insert(END, line)
                index += 1

        self.PopulateSummary()
        self.PopulateTableFrames()

        self.text.config(xscrollcommand=self.xScrollBar.set)
        self.xScrollBar.config(command=self.text.xview)

        self.text.config(yscrollcommand=self.yScrollBar.set)
        self.yScrollBar.config(command=self.text.yview)

        for func in self.DoneLoadingEvents:
            func(self.inputFilePath, self.selectedResultFile.absolutePath, self.tableDict.values())

    def InsertLineWithFormmating(self, line:str, tableResult:TableResult):
        self.text.insert(END, line)

        if tableResult is None:
            tableStart = -1
            statsColor = "black"
        else:
            if tableResult.totalCount == 0:
                statsColor = "purple"
            elif tableResult.failCount > 0:
                statsColor = "red"
            else:
                statsColor = "green"

        tableStart = -1 if tableResult is None else tableResult.startIndex

        processLine = line.strip()
        lineLength = len(line)
        
        if "Fail <--" in processLine or processLine.endswith("F"):
            self.AddTag("fail", lineLength, foreground="red")

        elif tableStart + 1 == self.tagIndex:
            self.AddTag("header", lineLength, foreground="blue")
        elif line.startswith("#Table: ") or line.startswith("#Requirements Tested - "):
            self.AddTag(f"{statsColor}stats", lineLength, foreground=statsColor)

        elif processLine == "#=================================================================================================================================":
            self.AddTag("startdiv", lineLength, background="slategray", foreground="gainsboro")

        elif processLine == "#<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>":
            self.AddTag("enddiv", lineLength, background="darkslategray", foreground="gainsboro")

        elif processLine == "#":
            self.AddTag("commentonly", lineLength, foreground="gray70")

        elif processLine.startswith("#"):
            self.AddTag("comment", lineLength, foreground="gray55")
        
        self.tagIndex += 1

    def Handle_TableClicked(self, tableResult:TableResult):
        textIndex = f"{tableResult.startIndex+1}.0"
        self.text.see(textIndex)
        lineInfo = self.text.dlineinfo(textIndex)
        self.text.yview_scroll(lineInfo[1]-20, "pixels")

class IOFrame(Frame):
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.topFrame = Frame(self)
        self.topFrame.pack(side="top", fill="x")

        self.botFrame = Frame(self)
        self.botFrame.pack(side="top", fill="x")

        

        self.resultDirVar = StringVar()
        self.resultDirEntry = Entry(self.topFrame, textvariable=self.resultDirVar)
        self.resultDirEntry.pack(side="top", fill="x", anchor="w")

        self.selectDirButton = Button(self.topFrame, text="Select Results Directory", command=self.Handle_SelectResultDir)
        self.selectDirButton.pack(side="top", fill="x")

        
        self.availableFilesListBox = Listbox(self.botFrame, selectmode="single", width=30)
        self.availableFilesListBox.grid(row=0, column=0, sticky="wens", pady=5)
        self.availableFilesListBox.bind("<<ListboxSelect>>", self.Handle_ParentFileSelected)

        self.scrollBarAvailable = Scrollbar(self.botFrame)
        self.scrollBarAvailable.grid(row=0, column=1, sticky="ns", pady=5)

        self.selectedParentVar = StringVar()
        Label(self.botFrame, textvariable=self.selectedParentVar, relief="sunken", bd=2, bg="grey75").grid(
            row=1, column=0, columnspan=2, sticky="wens"
        )

        self.selectFileListBox = Listbox(self.botFrame, selectmode="single", width=30)
        self.selectFileListBox.grid(row=2, column=0, sticky="wens")
        self.selectFileListBox.bind("<<ListboxSelect>>", self.Handle_ResultFileSelected)

        self.scrollBarSelect = Scrollbar(self.botFrame)
        self.scrollBarSelect.grid(row=2, column=1, sticky="ns")

        self.fileDictList:Dict[str, List[ResultFile]] = {}

        self.selectedParentFile = ""
        self.fileToLoad = ""

        self.fileSelectedEvents:List[Callable[[ResultFile], []]] = []

    def Handle_ResultFileSelected(self, event=None):
        temp = self.selectFileListBox.curselection()
        if len(temp) == 0:
            return
        
        self.fileToLoad = self.selectFileListBox.get(temp[0])

        for func in self.fileSelectedEvents:
            func(self.fileDictList[self.selectedParentFile][temp[0]])

    def Handle_ParentFileSelected(self, event=None):
        temp = self.availableFilesListBox.curselection()
        if len(temp) == 0:
            return
        self.selectedParentFile = self.availableFilesListBox.get(temp[0])
        self.selectedParentVar.set(f"Versions Of:\n{self.selectedParentFile}")
        self.PopulateChildFiles()
        
    def Handle_SelectResultDir(self):
        temp = self.resultDirVar.get()
        inDir = filedialog.askdirectory(initialdir=temp)

        if inDir == "" and temp == "":
            self.resultDirVar.set(os.getcwd())
            return
        
        self.resultDirVar.set(os.path.normpath(inDir))

        self.PopulateFilesInDir()

    def PopulateFilesInDir(self):
        self.availableFilesListBox.delete(0, END)

        files = os.listdir(self.resultDirVar.get())

        textFiles = [f for f in files if f.endswith(".txt")]


        for tf in textFiles:
            rFile = ResultFile(self.resultDirVar.get(), tf)

            if rFile.coreFileName in self.fileDictList:
                self.fileDictList[rFile.coreFileName].append(rFile)
            else:
                self.fileDictList[rFile.coreFileName] = [rFile]

        for key in self.fileDictList.keys():
            self.availableFilesListBox.insert(END, key)

        if len(self.fileDictList) > 0:
            self.availableFilesListBox.selection_set(0,0)
            self.Handle_ParentFileSelected()

        self.availableFilesListBox.config(yscrollcommand=self.scrollBarAvailable.set)
        self.scrollBarAvailable.config(command=self.availableFilesListBox.yview)

    def PopulateChildFiles(self):
        self.selectFileListBox.delete(0, END)

        resultFiles = self.fileDictList[self.selectedParentFile]
        sortedResults = sorted(resultFiles, key=lambda resultFiles: resultFiles.dt)
        sortedResults.reverse()

        for rf in sortedResults:
            self.selectFileListBox.insert(END, rf.DateTimeString)

        self.selectFileListBox.config(yscrollcommand=self.scrollBarSelect.set)
        self.scrollBarSelect.config(command=self.selectFileListBox.yview)
        if len(sortedResults) > 0:
            self.selectFileListBox.selection_set(0,0)
            self.Handle_ResultFileSelected()

    def SaveElements(self) -> Dict[str, Any]:
        saveDict:Dict[str, Any] = {
            "resultDir": self.resultDirVar.get()
        }

        return saveDict

    def RestoreElements(self, restoreDict:Dict[str, Any]):
        if restoreDict is None:
            return
        

        self.resultDirVar.set(restoreDict.get("resultDir", ""))

        self.PopulateFilesInDir()

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

class TableResult:
    pfMatch = r":::\s*(?:PF%)?\s*(\d+)/(\d+) [+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)%"
    startTimeMatch = r"#Start Time:\s+(.*)"
    endTimeMatch = r"#End\s+Time:\s+(.*) ::: Duration ([0-9]+([.][0-9]*)?|[.][0-9]+)"
    def __init__(self, startTableLine:str, startIndex:int, restOfLines:str):
        self.startTableLine = startTableLine
        self.startIndex = startIndex
        
        endIndex = 0
        for line in restOfLines:
            if line.startswith("#<><><><><><><><>"):
                break
            endIndex += 1

        tempLines = restOfLines[0:endIndex]

        #remove lines that only have #
        self.tableLines:List[str] = []
        for line in tempLines:
            l = line.strip()
            if l != "#":
                self.tableLines.append(l)

        self.ParseTableHeader()
        self.ParseFooter()

    def ParseFooter(self):
        lineCount = len(self.tableLines)
        footerLines = self.tableLines[lineCount-4:lineCount]

        self.passCount = 0
        self.failCount = 0
        self.pfPercent = 0
        self.totalCount = 0

        self.startTime = datetime.datetime.min
        self.endTime = datetime.datetime.max
        self.duration = -1

        for line in footerLines:
            pfMatch = re.search(TableResult.pfMatch, line)
            if pfMatch:
                self.passCount = int(pfMatch.group(1))
                self.totalCount = int(pfMatch.group(2))
                self.pfPercent = float(pfMatch.group(3))
                self.failCount = self.totalCount - self.passCount
                
        
        for line in footerLines: # not sure if its better to combine with loop above. Not sure how much time that regex takes. 
            startTimeMatch = re.match(TableResult.startTimeMatch, line)
            endTimeMatch = re.match(TableResult.endTimeMatch, line)
            if startTimeMatch:
                self.startTime = datetime.datetime.strptime(startTimeMatch.group(1), "%A %B %d, %Y %I:%M:%S %p")
            elif endTimeMatch:
                self.endTime = datetime.datetime.strptime(endTimeMatch.group(1), "%A %B %d, %Y %I:%M:%S %p")
                self.duration = float(endTimeMatch.group(2))

    def ParseTableHeader(self):
        temp = self.startTableLine[8:] # removes "#Table: "

        values = temp.split(" // ")

        self.description = ""
        reqs = ""

        if len(values) == 1:
            self.tableName = values[0]
        elif len(values) == 2:
            self.tableName = values[0]
            if values[1].startswith("Reqs: "):
                reqs = values[1]
            else:
                self.description = values[1][13:]
        elif len(values) == 3:
            self.tableName = values[0]
            self.description = values[1][13:] # removes "Description: "
            reqs = values[2]
        else:
            raise ValueError(f"Found too many fields in table header. Found: {len(values)}")
        
        self.tableName = self.tableName.strip()
        self.description = self.description.strip()
        
        if len(reqs) > 0:
            reqs = reqs[6:].strip() # remove "reqs: "
            self.reqs = reqs.split(", ")
        else:
            self.reqs:List[str] = []

    def __str__(self):
        reqString = ", ".join(self.reqs)
        return f"Name: {self.tableName}\nDesc: {self.description}\nReqs: {reqString}"

    def AllLines(self) -> str:
        return "\n".join(self.tableLines)

class ResultFile:
    dtMatch = r"(\d{1,2}[A-Za-z]{3}\d{1,2}_\d{1,2},\d{1,2},\d{1,2})"
    dtFormat = r"%d%b%y_%H,%M,%S"
    def __init__(self, inputDir:str, pathFromInputDir:str):
        self.inputDir = inputDir
        self.pathFromInputDir = pathFromInputDir
        
        self.absolutePath = os.path.join(self.inputDir, self.pathFromInputDir)
        self.fileName = os.path.split(self.absolutePath)[1]

        dtMatch = re.search(ResultFile.dtMatch, self.fileName)

        if dtMatch is not None:
            self.dt = datetime.datetime.strptime(dtMatch.group(1), ResultFile.dtFormat)
            #self.dt = datetime.datetime(
            #    year=int(dtMatch.group(3)),
            #    month=dtMatch.group(2),
            #    day=int(dtMatch.group(1)),
            #    hour=int(dtMatch.group(4)),
            #    minute=int(dtMatch.group(5)),
            #    second=int(dtMatch.group(6)),
            #)

        findCoreFileName =self.fileName.find("_Results")
        self.coreFileName = self.fileName[0:findCoreFileName]

    @property
    def DateTimeString(self) -> str:
        return self.dt.strftime("%d %b %y   %H:%M:%S")

class TableFrame(Frame):
    def __init__(self, parent:Frame, tableResult:TableResult, clickFunc:Callable[[TableResult],[]], *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.tableResult = tableResult
        self.clickFunc = clickFunc

        self.config(relief="ridge", bd=3)

        self.indexLabel = Label(self, text=self.tableResult.startIndex, relief="groove", bd=2)
        self.indexLabel.place(x=3, y=2, width=50)

        self.titleLabel = Label(self, text=self.tableResult.tableName.strip(), relief="sunken", bd=2, bg="grey75", anchor="w")
        self.titleLabel.place(x=55, y=2, width=187, height=20)

        if tableResult.totalCount == 0:
            pfColor = "lightpurple"
        elif tableResult.failCount > 0:
            pfColor = "lightsalmon"
        else:
            pfColor = "lightgreen"

        pfString = f"{self.tableResult.passCount} / {self.tableResult.totalCount}     {self.tableResult.pfPercent} %"
        self.pfLabel = Label(self, text=pfString, bg=pfColor)
        self.pfLabel.place(x=3, y=27, width=175)

        reqsString = f"Reqs: {len(self.tableResult.reqs)}"
        self.reqsLabel = Label(self, text=reqsString)
        self.reqsLabel.place(x=180, y=27, width=50)

        self.bind("<Button-1>", self.Handle_Click)
        self.indexLabel.bind("<Button-1>", self.Handle_Click)
        self.titleLabel.bind("<Button-1>", self.Handle_Click)
        self.pfLabel.bind("<Button-1>", self.Handle_Click)

    def Handle_Click(self, event=None):
        self.clickFunc(self.tableResult)

class IssueFrame(Frame):
    RequiredHeight = 100
    RequiredWidth = 485
    
    # Popluate with static method IssueFrame.PopulateImages()
    taskImage = None
    bugImage = None
    epicImage = None
    storyImage = None
    unknownImage = None

    errorImage = None
    successImage = None

    def __init__(self, parent:Frame, jiraFrame:JiraFrame, issueKey:str, issueJson:Dict[str, Any], inputFilePath:str, outputFilePath:str, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.jiraFrame = jiraFrame
        self.key = issueKey
        self.id = issueJson["id"]
        self.issueJson = issueJson
        self.inputFilePath = inputFilePath
        self.outputFilePath = outputFilePath

        self.issueType = self.issueJson["issuetype"]["name"]
        self.status = self.issueJson["status"]["name"]
        self.projectDict = self.issueJson["project"]
        self.LoadImageBasedOnType()

        self.typeCanvas = Canvas(self, height=20, width=20)
        self.typeCanvas.create_image(10,10, image=self.image)
        self.typeCanvas.place(x=3, y=7, height=20, width=20)

        self.transitionCombo = ttk.Combobox(self, values=[])
        self.transitionCombo.place(x=125, y=6, width=100)
        self.transitionCombo.bind("<<ComboboxSelected>>", self.Handle_ChangeStatus)

        self.statusChangeCanvas = Canvas(self, height=20, width=20)
        self.statusCreatedImage = None
        self.statusChangeCanvas.place(x=228, y=7, height=20, width=20)

        self.keyLabel = Label(self, text=self.key, relief="ridge", bd=2)
        self.keyLabel.place(x=23, y=6, width=100)

        self.uploadButton = Button(self, text="Upload", command=self.Click_UploadButton)
        self.uploadButton.place(x=400, y=3, width=75)

        self.summaryLabel = Label(self, text=self.issueJson["summary"], relief="sunken", bd=2, bg="grey75")
        self.summaryLabel.place(x=3, y=35, width=480)

        Label(self, text="Reporter:").place(
            x=3, y=60, width=50)
        self.reporterLabel = Label(self, text=self.issueJson["reporter"]["displayName"])
        self.reporterLabel.place(x=55, y=60)

        Label(self, text="Assignee:").place(
            x=250, y=60, width=50)
        
        assignee = self.issueJson["assignee"]
        assignee = "No One" if assignee is None else assignee["displayName"]
        self.reporterLabel = Label(self, text=assignee)
        self.reporterLabel.place(x=300, y=60)

        self.createBugButton = Button(self, text="Log Bug", command=self.Toggle_BugFrame)
        self.createBugButton.place(x=30, y=80, width=75)

        self.transitionDict:Dict[str, int] = {}
        self.GetTransitions()

    def Toggle_BugFrame(self):
        MainUI.instance.bugFrame.UpdatedSelectedIssue(self)
        if CreateBugFrame.isVisible:
            MainUI.instance.bugFrame.pack_forget()
        else:
            MainUI.instance.bugFrame.pack(side="top", fill="x")

        CreateBugFrame.isVisible = not CreateBugFrame.isVisible
        
    def GetParentInfo(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key
        }

    def LoadImageBasedOnType(self):
        if self.issueType == "Task":
            self.image = IssueFrame.taskImage
        elif self.issueType == "Bug":
            self.image = IssueFrame.bugImage
        elif self.issueType == "Story":
            self.image = IssueFrame.storyImage
        elif self.issueType == "Epic":
            self.image = IssueFrame.epicImage
        else:
            self.image = IssueFrame.unknownImage

    @staticmethod
    def PopulateImages():
        '''Must be called after creation'''
        IssueFrame.taskImage = PhotoImage(file=r"Resources\task.png")
        IssueFrame.bugImage = PhotoImage(file=r"Resources\bug.png")
        IssueFrame.epicImage = PhotoImage(file=r"Resources\epic.png")
        IssueFrame.storyImage = PhotoImage(file=r"Resources\story.png")
        IssueFrame.unknownImage = PhotoImage(file=r"Resources\unknown.png")

        IssueFrame.errorImage = PhotoImage(file=r"Resources\error.png")
        IssueFrame.successImage = PhotoImage(file=r"Resources\success.png")

    def Handle_ChangeStatus(self, event=None):
        self.transitionCombo.config(state="disabled")
        value = self.transitionCombo.get()
        if self.statusCreatedImage is not None:
            self.statusChangeCanvas.delete(self.statusCreatedImage)
        self.jiraFrame.AsyncFunctionCall(
            JiraAgent.SetIssueStatus, 
            self.Callback_ChangeStatus,
            MainUI.instance.jiraFrame.jira, 
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
        self.jiraFrame.AsyncFunctionCall(
            JiraAgent.GetIssueTransitions, 
            self.Callback_GetTransitions,
            MainUI.instance.jiraFrame.jira, 
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
        self.jiraFrame.AsyncFunctionCall(
            JiraAgent.AttachFile, 
            None,
            MainUI.instance.jiraFrame.jira, 
            self.key, 
            self.outputFilePath
        )

        self.jiraFrame.AsyncFunctionCall(
            JiraAgent.AttachFile, 
            self.Callback_UpdateButton,
            MainUI.instance.jiraFrame.jira, 
            self.key, 
            self.inputFilePath
        )
        #print(MainUI.instance.resultFrame.selectedResultFile.absolutePath)

    def Callback_UpdateButton(self, returnObject):
        self.uploadButton.ParseBool(type(returnObject[0]) != tuple)

class CreateBugFrame(Frame):
    isVisible:bool = False
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.issueFrame:IssueFrame = None

        self.columnconfigure(2, weight=1)

        Label(self, text="Title:").grid(
            row=0, column=0, **gridKwargs
        )
        Label(self, text="Summary:").grid(
            row=1, column=0, **gridKwargs
        )
        Label(self, text="").grid(
            row=2, column=0, **gridKwargs
        ) # spacer
        Label(self, text="Priority:").grid(
            row=3, column=0, **gridKwargs
        )

        self.titleEntry = Entry(self)
        self.titleEntry.grid(row=0, column=1, columnspan=3, sticky="wens", padx=5, pady=1)

        self.summaryText = Text(self, height=4, width=1)
        self.summaryText.grid(row=1, column=1, columnspan=3, sticky="wens", padx=5, pady=1)

        self.priorityCombo = ttk.Combobox(self, values=["High", "Medium", "Low"])
        self.priorityCombo.grid(row=3, column=1)
        self.priorityCombo.set("High")

        self.createBugButton = Button(self, text="Create Bug", command=self.Click_CreateBugButton)
        self.createBugButton.grid(row=4, column=0, columnspan=4)

    def UpdatedSelectedIssue(self, issueFrame:IssueFrame):
        self.issueFrame = issueFrame

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

        [success, bugInfo] = JiraAgent.CreateBug(self.issueFrame.jiraFrame.jira, fields)

        if not success:
            print("\n\n\Failed to create bug\n\n")
            return
        
        createBugKey = bugInfo["key"]

        [success, linkInfo] = JiraAgent.LinkIssues(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.key)

        JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.inputFilePath)
        JiraAgent.AttachFile(self.issueFrame.jiraFrame.jira, createBugKey, self.issueFrame.outputFilePath)



def MainExitCall():

    mw.SaveElements()
    tk.destroy()

if __name__ == "__main__":
    tk = Tk()

    mw = MainUI(tk)

    tk.withdraw()

    mw.protocol("WM_DELETE_WINDOW", MainExitCall)

    mw.mainloop()

