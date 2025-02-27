
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
from JiraControls import JiraFrame, IssueFrame, CreateBugFrame, JiraAgent
from ResultFiles import ResultFile, TableFrame, JadeTableResult, ResultFrame

configPath = "JadeResultParserConfig.txt"

Button.WorkStart = Button_WorkStart
Button.Parsebool = Button_ParseBool

class MainUI(Toplevel):
    instance = None
    def __init__(self, tk:Tk, *args, **kwargs):
        Toplevel.__init__(self, tk, *args, **kwargs)

        self.masterMenu = Menu(self)

        self.jiraMenu = Menu(self.masterMenu, tearoff=0)
        self.jiraMenu.add_command(label="Create Regression Epic", command=self.TempFunc)

        self.masterMenu.add_cascade(label="Jira", menu=self.jiraMenu)

        self.config(menu=self.masterMenu)

        self.title("Result Viewer and Jira Uploader")

        IssueFrame.PopulateImages()

        MainUI.instance = self

        self.ioFrame = IOFrame(self)
        self.ioFrame.pack(side="left", anchor='n', fill="y")
        self.ioFrame.fileSelectedEvents.append(self.Handle_FileSelected)

        self.parentJiraFrame = Frame(self)
        self.jiraFrame = JiraFrame(self.parentJiraFrame)
        #self.bugFrame = CreateBugFrame(self.parentJiraFrame)

        self.resultFrame = ResultViewerFrame(self)
        self.resultFrame.pack(side="left", fill="both", expand=True)

        self.parentJiraFrame.pack(side="left", fill="both")

        if JiraAgent.jiraImported:
            self.jiraFrame.pack(side="top", fill="both", expand=True)
            #self.bugFrame.pack(side="top", fill="both")
            self.resultFrame.DoneLoadingEvents.append(self.jiraFrame.Callback_ResultFileLoaded)


        self.RestoreElements()

    def TempFunc(self):
        pass

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
            
class IOFrame(Frame):
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.selectedParentFile = ""
        self.fileToLoad = ""

        self.fileSelectedEvents:List[Callable[[ResultFile], []]] = []
        self.fileDictList:Dict[str, List[ResultFile]] = {}

        self.topFrame = Frame(self)
        self.topFrame.pack(side="top", fill="x")

        self.botFrame = Frame(self)
        self.botFrame.pack(side="top", fill="both", expand=True)
        self.botFrame.rowconfigure(1, weight=1)

        self.resultDirVar = StringVar()
        self.resultDirEntry = Entry(self.topFrame, textvariable=self.resultDirVar)
        self.resultDirEntry.pack(side="top", fill="x", anchor="w")

        self.selectDirButton = Button(self.topFrame, text="Select Results Directory", command=self.Handle_SelectResultDir)
        self.selectDirButton.pack(side="top", fill="x")

        self.availableFilesListBox = Listbox(self.botFrame, selectmode="multiple", width=30)
        self.availableFilesListBox.grid(row=0, column=0, sticky="wens", pady=5)
        self.availableFilesListBox.bind("<<ListboxSelect>>", self.Handle_ParentFileSelected)

        self.scrollBarAvailable = Scrollbar(self.botFrame)
        self.scrollBarAvailable.grid(row=0, column=1, sticky="ns", pady=5)

        self.selectedParentVar = StringVar()
        #Label(self.botFrame, textvariable=self.selectedParentVar, relief="sunken", bd=2, bg="grey75").grid(
        #    row=1, column=0, columnspan=2, sticky="wens"
        #)

        #self.selectFileListBox = Listbox(self.botFrame, selectmode="single", width=30)
        #self.selectFileListBox.grid(row=2, column=0, sticky="wens")
        #self.selectFileListBox.bind("<<ListboxSelect>>", self.Handle_ResultFileSelected)

        self.scrollBarSelect = Scrollbar(self.botFrame)
        #self.scrollBarSelect.grid(row=2, column=1, sticky="ns")

        self.resultFilesScrollFrame = ScrollFrame(self.botFrame, width=1, bg="grey55", relief="sunken", bd=2)
        self.resultFilesScrollFrame.packFrame.config(bg="grey55")
        self.resultFilesScrollFrame.grid(row=1, column=0, columnspan=2, sticky="wens")
        self.resultFilesScrollFrame.hScroll.grid_forget()
        self.resultFilesScrollFrame.ConfigureCanvas(overrideWidth=150)

        self.parseThread = None
        self.parseQueue = Queue()
        self.uiQueue = Queue()
        
        self.UI_Async_Loop()

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
        
        fileKeys = []
        for index in temp:
            fileKeys.append(self.availableFilesListBox.get(index))
        self.PopulateChildFiles(fileKeys)
        
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
            rFile = ResultFile(self.resultDirVar.get(), tf, MainUI.instance.resultFrame)

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

        self.AsyncParseResultFiles()

    def AsyncParseResultFiles(self):
        self.availableFilesListBox.config(state="disabled")
        self.parseThread = threading.Thread(target=self.Thread_ParseResultFiles)
        for key in self.fileDictList.keys():
            for resultFile in self.fileDictList[key]:
                self.parseQueue.put(resultFile)

        self.parseThread.start()

    def Thread_ParseResultFiles(self):
        startTime = datetime.datetime.now()
        while not self.parseQueue.empty():
            rFile = self.parseQueue.get()
            rFile:ResultFile

            rFile.parser.ParseResultFile()
        self.Async_UI_Call(self.DoneParsingResultDir)

    def Async_UI_Call(self, func, *args, **kwargs):
        self.uiQueue.put([func, args, kwargs])

    def UI_Async_Loop(self):
        if not self.uiQueue.empty():
            [func, args, kwargs] = self.uiQueue.get()
            func(*args, **kwargs)

        self.after(100, self.UI_Async_Loop)

    def DoneParsingResultDir(self):
        self.availableFilesListBox.config(state="normal")
        self.Handle_ParentFileSelected()

    def Click_ResultFileFrame(self, resultFile:ResultFile):
        MainUI.instance.resultFrame.LoadResultFile(resultFile)

    def PopulateChildFiles(self, fileKeys:List[str]):
        self.resultFilesScrollFrame.ClearControls_Pack()

        frame = self.resultFilesScrollFrame.packFrame
        for key in fileKeys:
            for resultFile in self.fileDictList[key]:
                temp = ResultFrame(frame, resultFile, self.Click_ResultFileFrame, relief="groove", bd=2)
                temp.pack(side="top", fill="x", pady=2)
            Label(frame, text=" ", bg="steelblue").pack(side="top", fill="x")
        self.resultFilesScrollFrame.ConfigureCanvas()
            

        #resultFiles = self.fileDictList[self.selectedParentFile]
        #sortedResults = sorted(resultFiles, key=lambda resultFiles: resultFiles.dt)
        #sortedResults.reverse()

        #for rf in sortedResults:
        #    self.selectFileListBox.insert(END, rf.DateTimeString)

        #self.selectFileListBox.config(yscrollcommand=self.scrollBarSelect.set)
        #self.scrollBarSelect.config(command=self.selectFileListBox.yview)
        #if len(sortedResults) > 0:
        #    self.selectFileListBox.selection_set(0,0)
        #    self.Handle_ResultFileSelected()

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

class ResultViewerFrame(Frame):  
    def __init__(self, parent:Frame, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)

        self.selectedResultFile:ResultFile = None
        self.inputFilePath = ""
        self.fileLines:List[str] = []

        self.chunkDict:Dict[int, JadeTableResult] = {}
        self.DoneLoadingEvents:List[Callable[[str, str, List[JadeTableResult]], None]] = []
        
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

    def PopulateChunkFrames(self):
        self.tablesScrollFrame.ClearControls_Grid()

        for value in self.chunkDict.values():
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
        self.tableCountVar.set(len(self.chunkDict))

    def LoadResultFile(self, resultFile:ResultFile):
        if not os.path.exists(resultFile.absolutePath):
            return
        
        self.selectedResultFile = resultFile
        
        self.ClearLog()

        self.chunkDict = {}
        lastTableFound:JadeTableResult = None
        with open(resultFile.absolutePath, "r") as rFile:
            self.fileLines = rFile.readlines()
            index = 0
            for line in self.fileLines:
                if re.match(r"^#Table:\s(?!.*::: )", line): # the "#Table:" match will be found twice. Once for header. once for footer. The non capture group ":::" only appears in footer
                    self.chunkDict[index] = JadeTableResult(index, self.fileLines[index:])
                    lastTableFound = self.chunkDict[index]
                elif line.startswith("#Input File :   "):
                    self.inputFilePath = line[16:].strip()

                self.InsertLineWithFormmating(line, lastTableFound)
                #self.text.insert(END, line)
                index += 1

        self.PopulateSummary()
        self.PopulateChunkFrames()

        self.text.config(xscrollcommand=self.xScrollBar.set)
        self.xScrollBar.config(command=self.text.xview)

        self.text.config(yscrollcommand=self.yScrollBar.set)
        self.yScrollBar.config(command=self.text.yview)

        for func in self.DoneLoadingEvents:
            func(self.inputFilePath, self.selectedResultFile.absolutePath, self.chunkDict.values())

    def InsertLineWithFormmating(self, line:str, tableResult:JadeTableResult):
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

    def Handle_TableClicked(self, tableResult:JadeTableResult):
        textIndex = f"{tableResult.startIndex+1}.0"
        self.text.see(textIndex)
        lineInfo = self.text.dlineinfo(textIndex)
        self.text.yview_scroll(lineInfo[1]-20, "pixels")


def MainExitCall():

    mw.SaveElements()
    tk.destroy()

if __name__ == "__main__":
    tk = Tk()

    mw = MainUI(tk)

    tk.withdraw()

    mw.protocol("WM_DELETE_WINDOW", MainExitCall)

    mw.mainloop()

