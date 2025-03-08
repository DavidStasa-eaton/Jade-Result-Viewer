
import json
import os
from requests import exceptions as httpExceptions
import requests
from JWT_Handler import GetToken as GetJWT

from typing import Any, Dict, List, Tuple, TYPE_CHECKING, Callable

try:
    from atlassian import Jira, Xray
    jiraImported = True
except ImportError:
    jiraImported = False
    if not TYPE_CHECKING:
        Jira = None

import atlassian

configPath = "JiraCreds.txt"

serverAddress = "https://eaton-corp.atlassian.net/"

global jiraInstance
jiraInstance = None

#linkedissue = DIGTOOLS-64

def UpdateStoredCredentials(userName:str=None, newToken:str=None):
    if os.path.exists(configPath):
        with open(configPath, "r") as cFile:
            data = json.loads(cFile.readline())
    else:
        data = {"user": "", "token": ""}

    if userName is not None:
        data["user"] = userName

    if newToken is not None:
        data["token"] = newToken

    with open(configPath, "w") as cFile:
        cFile.write(json.dumps(data))

def GetStoredToken() -> str:
    if not os.path.exists(configPath):
        return ""
    
    with open(configPath, "r") as cFile:
        data = json.loads(cFile.readline())
        return data.get("token", "")
    
def GetStoredUserName() -> str:
    if not os.path.exists(configPath):
        return ""
    
    with open(configPath, "r") as cFile:
        data = json.loads(cFile.readline())
        return data.get("user", "")

def GetJiraInstance(createStaticInstant:bool=True) -> Jira:
    global jiraInstance
    jiraOptions = {"server": serverAddress, "verify": True}
    j = Jira(serverAddress,
            username=GetStoredUserName(),
            password=GetStoredToken(), verify_ssl=False)
    if createStaticInstant:
        jiraInstance = j
    return j

def CreateStaticJiraInstance() -> Jira:
    global jiraInstance
    if jiraInstance is None:
        return GetJiraInstance()
    return jiraInstance

def GetXrayInstance() -> Jira:
    jiraOptions = {"server": serverAddress, "verify": True}
    x = Xray(serverAddress,
            username=GetStoredUserName(),
            password=GetStoredToken(), verify_ssl=False)
    return x

def WriteDictToFile(dictToWrite:Dict[Any, Any], fileName="JiraStuff.txt"):
    with open(fileName, "w", encoding="utf-16") as wFile:
        wFile.write(json.dumps(dictToWrite, indent=4))

def WriteIssueToFile(jira:Jira, issueKey:str, filterCustomFields:bool=True):
    
    issue = jira.issue(issueKey)

    fields = issue["fields"]
    copyDict = {}
    for key, value in fields.items():
        key:str
        if not key.startswith("customfield"):
            copyDict[key] = value
        elif key.startswith("customfield") and value is not None:
            copyDict[key] = value

    issue["fields"] = copyDict

    fileName = f"JiraIssue_{issueKey}.txt"
    with open(fileName, "w", encoding="utf-16") as wFile:
        wFile.write(json.dumps(issue, indent=4))

def LinkClonedIssue(jira:Jira, childIssue:str, parentIssue:str) -> Tuple[bool, Dict[str, Any]]:
    data = {
            "type": {"name": "Cloners" },
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
    
def GetJQL(jira:Jira, jqlRequest:str) -> Tuple[bool, Dict[str, Any]]:
    try:
        return (True, jira.jql(jqlRequest))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def GetLinkIssues(jira:Jira, linkedKey:str) -> Tuple[bool, Dict[str, Any]]:
    jqlRequest = f"linkedissue = {linkedKey}"
    try:
        return (True, jira.jql(jqlRequest))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)

def CreateItem(jira:Jira, fields:Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        return (True, jira.create_issue(fields=fields))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def CreateAndGetItem(jira:Jira, fields:Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    (success, info) = CreateItem(jira, fields)
    if not success:
        return (success, info)
    
    key = info["key"]
    return GetJiraItem(jira, key)
    
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
    
def GetJiraItem(jira:Jira, issueKey:str, filterCustomFields:bool=True):
    try:
        issueDict = jira.issue(issueKey)
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
    fields = issueDict["fields"]
    copyDict = {}
    for key, value in fields.items():
        key:str
        if not key.startswith("customfield"):
            copyDict[key] = value
        elif key.startswith("customfield") and value is not None:
            copyDict[key] = value

    issueDict["fields"] = copyDict

    return (True, issueDict)

def GetJiraIssue(jira:Jira, key:str) -> Dict[str, Any]:
    try:
        issue = jira.issue(key)
    except httpExceptions.HTTPError as e:
        print(e)
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


########################################################################################################################
####################################               Projects                 ############################################
########################################################################################################################

def GetAllProjects(jira:Jira):
    try:
        return (True, jira.get_all_projects())
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def GetProject(jira:Jira, projectKey:str):
    try:
        return (True, jira.project(projectKey))
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def GetNewIssuesInProject(jira:Jira, projectKey:str, UpdateFunc:Callable=None, startIndex:int=0):
    allIssues = []
    returnCount = 100
    try:
        while returnCount == 100:
            moreIssues = jira.get_all_project_issues(projectKey, start=startIndex+len(allIssues), limit=100)
            returnCount = len(moreIssues)

            allIssues += moreIssues

            if UpdateFunc:
                UpdateFunc(returnCount, len(allIssues))
  
        return (True, allIssues)
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)

def GetAllIssuesInProject(jira:Jira, projectKey:str, UpdateFunc:Callable=None):
    allIssues = []
    returnCount = 100
    try:
        while returnCount == 100:
            moreIssues = jira.get_all_project_issues(projectKey, start=len(allIssues), limit=100)
            returnCount = len(moreIssues)

            allIssues += moreIssues

            if UpdateFunc:
                UpdateFunc(returnCount, len(allIssues))
  
        return (True, allIssues)
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)
    
def GetAllIssueKeysInProject(jira:Jira, projectKey:str):
    allIssues = []
    returnCount = 100
    try:
        while returnCount == 100:
            print(returnCount, len(allIssues))
            moreIssues = jira.get_project_issuekey_all(projectKey, start=len(allIssues), limit=100)
            returnCount = len(moreIssues)

            allIssues += moreIssues
        return (True, allIssues)
    except httpExceptions.HTTPError as e:
        return (False, e.args)
    except httpExceptions.ConnectionError as e:
        return (False, e.args)
    except httpExceptions.ConnectTimeout as e:
        return (False, e.args)

if __name__ == "__main__":
    print("Don't run this")
    #issueKey = "TUPCTOOL-3"
    #WriteIssueToFile(j, issueKey)
    #issueKey = "DIGTOOLS-50"
    #WriteIssueToFile(j, issueKey)

    #CreateBug(j, "test bug", "test description")

    #AttachFile(j, "TUPCTOOL-32", "JiraIssue_DIGTOOLS-50.txt")

    #j.issue_add_comment(issueKey, "Comment from test")



