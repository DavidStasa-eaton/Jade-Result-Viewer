from typing import Dict, List, Tuple, Any

from tkinter import PhotoImage

class JiraItem:
    taskImage = None
    bugImage = None
    epicImage = None
    storyImage = None
    testCaseImage = None
    unknownImage = None

    errorImage = None
    successImage = None

    def __init__(self, issueDict:Dict[str, Any]):
        self.issueDict = issueDict

        self.key = issueDict["key"]
        self.fields:Dict[str, Any] = issueDict["fields"]

        self.parent = self.fields.get("parent", {})
        self.issueType = self.fields["issuetype"]["name"]

        self.projectKey = self.fields["project"]["key"]

        self.description = self.fields["description"]
        self.summary = self.fields["summary"]

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
        JiraItem.unknownImage = PhotoImage(file=r"Resources\unknown.png")

        JiraItem.errorImage = PhotoImage(file=r"Resources\error.png")
        JiraItem.successImage = PhotoImage(file=r"Resources\success.png")


