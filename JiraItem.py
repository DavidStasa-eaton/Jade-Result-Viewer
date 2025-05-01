from __future__ import annotations
from typing import Dict, List, Tuple, Any, TYPE_CHECKING, Callable

from tkinter import PhotoImage, Frame, Label, Button, Canvas, ttk, Menu
from TkinterSaver import packKwargs, gridKwargs, ToggleButton, ToggleElement
from AsyncHandler import AsyncHandler

import JiraAgent

if TYPE_CHECKING:
    from ResultViewer import JadeTableResult
    from atlassian import Jira

class JiraItem:
    taskImage = None
    bugImage = None
    epicImage = None
    storyImage = None
    testCaseImage = None
    requirementImage = None
    unknownImage = None
    initiativesImage = None

    errorImage = None
    successImage = None

    def __init__(self, issueDict:Dict[str, Any]):
        self.issueDict = issueDict
        self.ChildFoundEvent:List[Callable[[], JiraItem]] = []
        self.FamilyTreeChangedEvent:List[Callable[[], JiraItem]] = []

        self.key = issueDict["key"]
        self.id = issueDict["id"]
        self.fields:Dict[str, Any] = issueDict["fields"]

        self.parent = self.fields.get("parent", {})
        self.issueType = self.fields["issuetype"]["name"]

        self.projectKey = self.fields["project"]["key"]

        self.description = self.fields["description"]
        self.summary = self.fields["summary"]
        self.status = self.fields["status"]["name"]

        self.reporter = self.fields["reporter"]["displayName"]
        self.assignee = self.fields["assignee"]
        self.assignee = "No One" if self.assignee is None else self.assignee["displayName"]

        self.children:List[JiraItem] = []

    @property
    def ChildrenCount(self) -> int:
        return len(self.children)
    
    @property
    def FamilyCount(self) -> int:
        count = len(self.children)

        for child in self.children:
            count += child.FamilyCount

        return count
    
    @property
    def DeadEndDecendentCount(self) -> int:
        count = 0

        for child in self.children:
            if child.ChildrenCount == 0:
                count += 1
            else:
                count += child.DeadEndDecendentCount

        return count
    
    def GetAllDeadEndDecendents(self) -> List[JiraItem]:
        deadEnds = []

        for child in self.children:
            if child.ChildrenCount == 0:
                deadEnds.append(child)
            else:
                deadEnds.extend(child.GetAllDeadEndDecendents())

        return deadEnds

        

    def GetParentInfo(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key
        }

    def GetFamilyTree(self, jira:Jira, handler:AsyncHandler):
        [success, infoPacket] = JiraAgent.GetJQL(jira, f"parent = {self.key} ORDER BY created DESC")

        if not success:
            return [success, None]
        
        self.children = []
        index = 0
        for childInfo in infoPacket["issues"]:
            self.children.append(JiraItem(childInfo))
            self.children[index].GetFamilyTree(jira, handler)
            index += 1

        return [success, self]

        

    def Async_GetFamilyTree(self, jira:Jira, handler:AsyncHandler):
        handler.AsyncWork(
            self.GetFamilyTree,
            self.Callback_GetFamilyTree,
            jira,
            handler
        )


    def Callback_GetFamilyTree(self, returnObject):
        if not returnObject[0]:
            return
        
        for func in self.FamilyTreeChangedEvent:
            func(self)

    def GetChildren(self, jira:Jira, handler:AsyncHandler):
        handler.AsyncWork(
            JiraAgent.GetJQL,
            self.Callback_GetChildren,
            jira,
            f"parent = {self.key} ORDER BY created DESC"
        )

    def Callback_GetChildren(self, returnObject):
        if not returnObject[0]:
            return
        
        self.children = []
        for childInfo in returnObject[1]["issues"]:
            self.children.append(JiraItem(childInfo))

        for func in self.ChildFoundEvent:
            func(self)


class ItemCard(Frame):
    def __init__(self, parent:Frame, jira:Jira, jiraItem:JiraItem, handler:AsyncHandler, width=300, height=110, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.jira = jira
        self.item = jiraItem
        self.handler = handler

        self.item.ChildFoundEvent.append(self.Callback_GetChildren)
        self.item.FamilyTreeChangedEvent.append(self.Callback_GetFamilyTree)

        self.config(width=width, height=height)

        self.image = JiraType.LoadImageBasedOnType(self.item.issueType)

        #controlState = "disabled" if self.item.fields == {} else "normal"

        self.typeCanvas = Canvas(self, height=20, width=20)
        self.typeCanvas.create_image(10,10, image=self.image)
        self.typeCanvas.place(x=3, y=7, height=20, width=20)

        #self.transitionCombo = ttk.Combobox(self, values=[], state=controlState)
        #self.transitionCombo.place(x=125, y=6, width=100)
        #self.transitionCombo.bind("<<ComboboxSelected>>", self.Handle_ChangeStatus)

        #self.statusChangeCanvas = Canvas(self, height=20, width=20)
        #self.statusCreatedImage = None
        #self.statusChangeCanvas.place(x=228, y=7, height=20, width=20)

        self.keyLabel = Label(self, text=self.item.key, relief="ridge", bd=2)
        self.keyLabel.place(x=23, y=6, width=120)

        self.summaryLabel = Label(self, text=self.item.summary, relief="sunken", bd=2, bg="grey75")
        self.summaryLabel.place(x=3, y=35, width=width-8)

        self._reporterLabel = Label(self, text="Reporter:")
        self._reporterLabel.place(x=3, y=60, width=50)
        self.reporterLabel = Label(self, text=self.item.reporter)
        self.reporterLabel.place(x=55, y=60)

        self._assigneLabel = Label(self, text="Assignee:")
        self._assigneLabel.place(x=3, y=80, width=50)
        
        self.assigneeLabel = Label(self, text=self.item.assignee)
        self.assigneeLabel.place(x=55, y=80)

        self.bind("<Button-3>", self.Handle_RightClick)
        self.CreateRightClickMenu()

    def GetChildren(self):
        self.item.GetChildren(self.jira, self.handler)

    def Callback_GetChildren(self, item:JiraItem):
        print(item)

    def Callback_GetFamilyTree(self, item:JiraItem):
        pass

    def DeplaceLabels(self, *args:List[Label]):
        for label in args:
            label:Label
            label.place_forget()

    def Handle_RightClick(self, event):
        try:
            self.rightClickMenu.tk_popup(event.x_root, event.y_root)
        finally:
            self.rightClickMenu.grab_release()

    def CreateRightClickMenu(self):
        self.rightClickMenu = Menu(self, tearoff=0)

        self.rightClickMenu.add_command(label="Save Info", command=self.MenuClick_SaveInfo)
        self.rightClickMenu.add_command(label="Get Children2", command=self.MenuClick_GetChildren)
        self.rightClickMenu.add_command(label="Get Family Tree", command=self.MenuClick_GetFamilyTree)
        #self.rightClickMenu.add_command(label="LinkIssue", command=self.MenuClick_LinkIssue)

    def MenuClick_SaveInfo(self, event=None):
        self.handler.AsyncWork(
            JiraAgent.WriteIssueToFile, 
            None,
            self.jira, 
            self.item.key,
            False
        )

    def MenuClick_GetChildren(self, event=None):
        self.GetChildren()

    def MenuClick_GetFamilyTree(self, event=None):
        self.item.Async_GetFamilyTree(self.jira, self.handler)

class JiraType:
    @staticmethod
    def LoadImageBasedOnType(issueType:str) -> PhotoImage:
        if issueType == "Task":
            return JiraItem.taskImage
        elif issueType == "Bug":
            return JiraItem.bugImage
        elif issueType == "Story":
            return JiraItem.storyImage
        elif issueType == "Epic":
            return JiraItem.epicImage
        elif issueType == "Test":
            return JiraItem.testCaseImage
        elif issueType == "Requirement":
            return JiraItem.requirementImage
        elif issueType == "Initiatives":
            return JiraItem.initiativesImage
        else:
            return JiraItem.unknownImage

    @staticmethod
    def PopulateImages():
        '''Must be called after creation'''
        if JiraItem.taskImage: # exit if already populated
            return
        JiraItem.taskImage = PhotoImage(file=r"Resources\task.png")
        JiraItem.bugImage = PhotoImage(file=r"Resources\bug.png")
        JiraItem.epicImage = PhotoImage(file=r"Resources\epic.png")
        JiraItem.storyImage = PhotoImage(file=r"Resources\story.png")
        JiraItem.testCaseImage = PhotoImage(file=r"Resources\testcase.png")
        JiraItem.requirementImage = PhotoImage(file=r"Resources\requirement.png")
        JiraItem.initiativesImage = PhotoImage(file=r"Resources\Initiatives.png")
        JiraItem.unknownImage = PhotoImage(file=r"Resources\unknown.png")

        JiraItem.errorImage = PhotoImage(file=r"Resources\error.png")
        JiraItem.successImage = PhotoImage(file=r"Resources\success.png")


