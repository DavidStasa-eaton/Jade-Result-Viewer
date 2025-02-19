
import json
import os
from requests import exceptions as httpExceptions

from typing import Any, Dict, List, Tuple, TYPE_CHECKING

try:
    from atlassian import Jira
    jiraImported = True
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

def LinkIssues(jira:Jira, childIssue:str, parentIssue:str) -> Tuple[bool, Dict[str, Any]]:
    data = {
            "type": {"name": "Depends" },
            "inwardIssue": { "key": childIssue},
            "outwardIssue": {"key": parentIssue},
            }
    try:
        return (True, jira.create_issue_link(data))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)

def CreateBug(jira:Jira, fields:Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        return (True, jira.create_issue(fields=fields))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)

def AttachFile(jira:Jira, issueKey:str, pathToAttachment:str):
    if not os.path.exists(pathToAttachment):
        raise FileNotFoundError(f"File of '{pathToAttachment}' not found")
    
    try:
        return jira.add_attachment(issueKey, pathToAttachment)
    except httpExceptions.HTTPError as e:
        return [e.args]
    except httpExceptions.ConnectionError as e:
        return [e.args]
    except httpExceptions.ConnectTimeout as e:
        return [e.args]
    
def GetJiraProjects(jira:Jira) -> List[Any]:
    return jira.projects()

def GetJiraIssue(jira:Jira, key:str) -> Dict[str, Any]:
    try:
        issue = jira.issue(key)
    except httpExceptions.HTTPError:
        return {}

    fields = issue["fields"]
    copyDict = {}
    for key, value in fields.items():
        key:str
        if not key.startswith("customfield"):
            copyDict[key] = value

    copyDict['id'] = issue['id']

    return copyDict

def GetIssueTransitions(jira:Jira, key:str, *args, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
    try:
        return (True, jira.get_issue_transitions(key)) # returns list for some reason. First arg is dictionary of statuses
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def SetIssueStatus(jira:Jira, key:str, newStatus:int) -> Tuple[bool, List[Dict[str, Any]]]:
    try:
        return (True, jira.issue_transition(key, newStatus))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)


if __name__ == "__main__":
    #issueKey = "TUPCTOOL-3"
    #WriteIssueToFile(j, issueKey)
    #issueKey = "DIGTOOLS-50"
    #WriteIssueToFile(j, issueKey)

    #CreateBug(j, "test bug", "test description")

    AttachFile(j, "TUPCTOOL-32", "JiraIssue_DIGTOOLS-50.txt")

    #j.issue_add_comment(issueKey, "Comment from test")



