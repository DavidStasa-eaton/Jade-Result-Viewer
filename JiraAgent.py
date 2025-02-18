
import json
import os

from typing import Any, Dict, List, Tuple, TYPE_CHECKING

try:
    from atlassian import Jira
except ImportError:
    jiraImported = False
    if not TYPE_CHECKING:
        Jira = None

TOKEN = ""

serverAddress = "https://eaton-corp.atlassian.net/"
userName = ""


def GetJiraInstance() -> Jira:
    jiraOptions = {"server": serverAddress, "verify": True}
    j = Jira(serverAddress,
            username=userName,
            password=TOKEN, verify_ssl=False)
    return j

def WriteIssueToFile(jira:Jira, issueKey:str):
    issue = jira.issue(issueKey)

    fields = issue["fields"]
    copyDict = {}
    for key, value in fields.items():
        key:str
        if not key.startswith("customfield"):
            copyDict[key] = value

    issue["fields"] = copyDict

    fileName = f"JiraIssue_{issueKey}.txt"
    with open(fileName, "w", encoding="utf-16") as wFile:
        wFile.write(json.dumps(issue, indent=4))

def CreateBug(jira:Jira, summary:str, description:str):
    fields={
        "project": {"key": "TUPCTOOL"},
        "issuetype": {"name": "Bug"},
        "summary": "TEST BUG - From a python script. Can delete",
        "description": "Testing out the JIRA api via python. Not a real bug.",
    }

    jira.create_issue(fields=fields)

def AttachFile(jira:Jira, issueKey:str, pathToAttachment:str):
    if not os.path.exists(pathToAttachment):
        raise FileNotFoundError(f"File of '{pathToAttachment}' not found")
    
    jira.add_attachment(issueKey, pathToAttachment)
    
def GetJiraProjects(jira:Jira) -> List[Any]:
    return jira.projects()

def GetJiraIssue(jira:Jira, key:str) -> Dict[str, Any]:
    issue = jira.issue(key)

    fields = issue["fields"]
    copyDict = {}
    for key, value in fields.items():
        key:str
        if not key.startswith("customfield"):
            copyDict[key] = value

    return copyDict

if __name__ == "__main__":
    #issueKey = "TUPCTOOL-3"
    #WriteIssueToFile(j, issueKey)
    #issueKey = "DIGTOOLS-50"
    #WriteIssueToFile(j, issueKey)

    #CreateBug(j, "test bug", "test description")

    AttachFile(j, "TUPCTOOL-32", "JiraIssue_DIGTOOLS-50.txt")

    #j.issue_add_comment(issueKey, "Comment from test")



