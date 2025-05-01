from __future__ import annotations
import re
import datetime
import os
from typing import Dict, List, Tuple, Any, Callable, TYPE_CHECKING
from tkinter import Tk, Toplevel, Frame, Button, Entry, Label, StringVar, ttk, filedialog, Listbox, END, Scrollbar, Text, simpledialog, PhotoImage, Canvas, Image, Menu

import enum

if TYPE_CHECKING:
    from ResultViewer import ResultViewerFrame

class FileTypes(enum.Enum):
    Unknown = 0
    Jade = 1

class ResultFile:
    dtMatch = r"(\d{1,2}[A-Za-z]{3}\d{1,2}_\d{1,2},\d{1,2},\d{1,2})"
    dtFormat = r"%d%b%y_%H,%M,%S"
    def __init__(self, inputDir:str, pathFromInputDir:str):
        self.resultsDir = inputDir
        self.pathFromInputDir = pathFromInputDir
        #self.viewerFrame = viewerFrame
        self.fileType:FileTypes = FileTypes.Unknown
        self.parser:Parser = Parser(self)
        self.chunkDict:Dict[str, ChunkResults] = {}
        
        self.absolutePath = os.path.join(self.resultsDir, self.pathFromInputDir)
        self.fileName = os.path.split(self.absolutePath)[1]

        self.DoneLoadingEvents:List[Callable[[str, str, List[ChunkResults]], None]] = []

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
        self.inputFilePath = ""

        self.InitalParse()

    def GetLines(self, startIndex:int=0, endIndex:int=-1) -> List[str]:
        with open(self.absolutePath, "r") as rfile:
            allLines = rfile.readlines()
            return allLines[startIndex:endIndex]

    def InitalParse(self):
        if self.ParseCheck_Jade(self.GetLines(0, 6)):
            self.parser = JadeParser(self)
            self.fileType = FileTypes.Jade
            return

    def ParseCheck_Jade(self, lines:List[str]) -> bool:
        if len(lines) < 6:
            return False
        
        checks:List[bool] = [
            lines[0].startswith("#Output File:"),
            lines[1].startswith("#Output Dir :"),
            lines[2].startswith("#Input File :"),
            lines[3].startswith("#Start Time :"),
            lines[4].startswith("#Commit ID  :"),
            lines[5].startswith("#Input Hash :"),
        ]
        
        return all(checks)
    
    @property
    def passCount(self) -> int:
        return sum(chunk.passCount for chunk in self.chunkDict.values())
    
    @property
    def failCount(self) -> int:
        return sum(chunk.failCount for chunk in self.chunkDict.values())
    
    @property
    def errorCount(self) -> int:
        return sum(chunk.errorCount for chunk in self.chunkDict.values())
    
    @property
    def totalCount(self) -> int:
        return sum(chunk.totalCount for chunk in self.chunkDict.values())
    
    @property
    def pfPercent(self) -> float:
        if self.totalCount == 0:
            return 0

        return 100.0 * float(self.passCount)/float(self.totalCount) 

    @property
    def reqs(self) -> List[str]:
        allReqs = []
        for chunk in self.chunkDict.values():
            allReqs += chunk.reqs
        return allReqs

    @property
    def DateTimeString(self) -> str:
        return self.dt.strftime("%d %b %y   %H:%M:%S")

class Parser:
    def __init__(self, resultFile:ResultFile):
        self.resultFile = resultFile

    def ParseResultFile(self):
        pass

class JadeParser(Parser):
    def __init__(self, resultFile:ResultFile):
        Parser.__init__(self, resultFile)

    def ParseResultFile(self):
        if not os.path.exists(self.resultFile.absolutePath):
            return
        
        headerLines = self.resultFile.GetLines(0, 3)
        inputLine = headerLines[2]
        self.resultFile.inputFilePath = inputLine[16:].strip()

        with open(self.resultFile.absolutePath, "r") as rFile:
            self.fileLines = rFile.readlines()
            index = 0
            for line in self.fileLines:
                if re.match(r"^#Table:\s(?!.*::: )", line): # the "#Table:" match will be found twice. Once for header. once for footer. The non capture group ":::" only appears in footer
                    self.resultFile.chunkDict[index] = JadeTableResult(index, self.fileLines[index:])
                index += 1

        for func in self.resultFile.DoneLoadingEvents:
            func(self.resultFile.inputFilePath, self.resultFile.absolutePath, self.resultFile.chunkDict.values())

class ChunkResults:
    def __init__(self, startIndex:int, restOfLines:List[str]):
        self.startIndex = startIndex

        self.chunkLines:List[str] = []

        self.chunkName:str = ""
        self.description:str = ""
        self.reqs:List[str] = []

        self.passCount = -1
        self.failCount = -1
        self.errorCount = -1
        self.totalCount = -1

        self.startTime = datetime.datetime.min
        self.endTime = datetime.datetime.max
        self.duration = -1

    def ParseChunks(self):
        pass

class JadeTableResult(ChunkResults):
    pfMatch = r":::\s*(?:PF%)?\s*(\d+)/(\d+) [+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)%"
    startTimeMatch = r"#Start Time:\s+(.*)"
    endTimeMatch = r"#End\s+Time:\s+(.*) ::: Duration ([0-9]+([.][0-9]*)?|[.][0-9]+)"
    def __init__(self, startIndex:int, restOfLines:str):
        ChunkResults.__init__(self, startIndex, restOfLines)

        endIndex = 0
        for line in restOfLines:
            if line.startswith("#<><><><><><><><>"):
                break
            endIndex += 1

        tempLines = restOfLines[0:endIndex]

        #remove lines that only have #
        self.chunkLines:List[str] = []
        for line in tempLines:
            l = line.strip()
            if l != "#":
                self.chunkLines.append(l)

        self.ParseChunks()

    def ParseChunks(self):
        self.ParseTableHeader()
        self.ParseFooter()

    def ParseFooter(self):
        lineCount = len(self.chunkLines)
        footerLines = self.chunkLines[lineCount-4:lineCount]

        self.passCount = 0
        self.failCount = 0
        self.pfPercent = 0
        self.totalCount = 0

        self.startTime = datetime.datetime.min
        self.endTime = datetime.datetime.max
        self.duration = -1

        for line in footerLines:
            pfMatch = re.search(JadeTableResult.pfMatch, line)
            if pfMatch:
                self.passCount = int(pfMatch.group(1))
                self.totalCount = int(pfMatch.group(2))
                self.pfPercent = float(pfMatch.group(3))
                self.failCount = self.totalCount - self.passCount
                
        
        for line in footerLines: # not sure if its better to combine with loop above. Not sure how much time that regex takes. 
            startTimeMatch = re.match(JadeTableResult.startTimeMatch, line)
            endTimeMatch = re.match(JadeTableResult.endTimeMatch, line)
            if startTimeMatch:
                self.startTime = datetime.datetime.strptime(startTimeMatch.group(1), "%A %B %d, %Y %I:%M:%S %p")
            elif endTimeMatch:
                self.endTime = datetime.datetime.strptime(endTimeMatch.group(1), "%A %B %d, %Y %I:%M:%S %p")
                self.duration = float(endTimeMatch.group(2))

    def ParseTableHeader(self):
        temp = self.chunkLines[0][8:] # removes "#Table: "

        values = temp.split(" // ")

        self.description = ""
        reqs = ""

        if len(values) == 1:
            self.chunkName = values[0]
        elif len(values) == 2:
            self.chunkName = values[0]
            if values[1].startswith("Reqs: "):
                reqs = values[1]
            else:
                self.description = values[1][13:]
        elif len(values) == 3:
            self.chunkName = values[0]
            self.description = values[1][13:] # removes "Description: "
            reqs = values[2]
        else:
            raise ValueError(f"Found too many fields in table header. Found: {len(values)}")
        
        self.chunkName = self.chunkName.strip()
        self.description = self.description.strip()
        
        if len(reqs) > 0:
            reqs = reqs[6:].strip() # remove "reqs: "
            self.reqs = reqs.split(", ")
        else:
            self.reqs:List[str] = []

    def __str__(self):
        reqString = ", ".join(self.reqs)
        return f"Name: {self.chunkName}\nDesc: {self.description}\nReqs: {reqString}"

    def AllLines(self) -> str:
        return "\n".join(self.chunkLines)

class ResultFrame(Frame):
    def __init__(self, parent:Frame, rFile:ResultFile, clickFunc:Callable[[ResultFile], None], *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.rFile = rFile
        self.clickFunc = clickFunc

        self.config(height=78, width=180)

        self.config(relief="ridge", bd=3)

        self.coreTitleLabel = Label(self, text=self.rFile.coreFileName, relief="groove", bd=2)
        self.coreTitleLabel.place(x=3, y=2, width=170)

        self.tsLabel = Label(self, text=self.rFile.DateTimeString, relief="sunken", bd=2, bg="grey75")
        self.tsLabel.place(x=3, y=25, width=170, height=20)

        if rFile.totalCount == 0:
            pfColor = "purple"
        elif rFile.failCount > 0:
            pfColor = "lightsalmon"
        else:
            pfColor = "lightgreen"

        pfString = f"{self.rFile.passCount} / {self.rFile.totalCount}     {self.rFile.pfPercent:.2f} %"
        self.pfLabel = Label(self, text=pfString, bg=pfColor)
        self.pfLabel.place(x=3, y=48, width=110)

        reqsString = f"Reqs: {len(self.rFile.reqs)}"
        self.reqsLabel = Label(self, text=reqsString)
        self.reqsLabel.place(x=115, y=48, width=50)

        self.bind("<Button-1>", self.Handle_Click)
        self.coreTitleLabel.bind("<Button-1>", self.Handle_Click)
        self.tsLabel.bind("<Button-1>", self.Handle_Click)
        self.pfLabel.bind("<Button-1>", self.Handle_Click)
        self.reqsLabel.bind("<Button-1>", self.Handle_Click)

    def Handle_Click(self, event=None):
        self.clickFunc(self.rFile)

class TableFrame(Frame):
    def __init__(self, parent:Frame, tableResult:JadeTableResult, clickFunc:Callable[[JadeTableResult],[]], *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.tableResult = tableResult
        self.clickFunc = clickFunc

        self.config(relief="ridge", bd=3)

        self.indexLabel = Label(self, text=self.tableResult.startIndex, relief="groove", bd=2)
        self.indexLabel.place(x=3, y=2, width=50)

        self.titleLabel = Label(self, text=self.tableResult.chunkName.strip(), relief="sunken", bd=2, bg="grey75", anchor="w")
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
        self.reqsLabel.bind("<Button-1>", self.Handle_Click)

    def Handle_Click(self, event=None):
        self.clickFunc(self.tableResult)