
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

TOKEN = ""

serverAddress = "https://eaton-corp.atlassian.net/"
userName = ""

global jiraInstance
jiraInstance = None

def GetJiraInstance(createStaticInstant:bool=True) -> Jira:
    global jiraInstance
    jiraOptions = {"server": serverAddress, "verify": True}
    j = Jira(serverAddress,
            username=userName,
            password=TOKEN, verify_ssl=False)
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
            username=userName,
            password=TOKEN, verify_ssl=False)
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
    
def TestFunc(xray:Xray, key:str) -> Tuple[bool, Dict[str, Any]]:
    token = "ATATT3xFfGF0VPJFulHvFMvk-Z7tx9XTJvk8qxyPP8zok2jC7_dwaPjI3uMlYdbOwfSdk7PgYuAmKJ38dGecEcOIbBCgxPMJ3W16DUsIa1S5ERfcbsWnxrsO1xIhSCvzZzWdWCNc9AzXddNus8-QzJiZOr8AVketJGMXFJnCKHRmFcRhPc1bsPo=016B99B7"
    cycle_id = "ade7d934-a6b4-4128-92e7-a7a65112625"
    issueKey = "MT-1618"
    version_id = -1
    project_id = "12661"
    #"https://eaton-corp.atlassian.net/projects/rest/zapi/latest/teststep/MT-1618"
    accessToken = "NDk0MzY5ZjctNzBkZi0zYzQwLWJjYTctMDY5YjY3Y2Y4ZWYxIDVhMjgzYjE0MTI5ZWFmNzUxZTNkYjI1ZSBVU0VSX0RFRkFVTFRfTkFNRQ"
    url = f"https://eaton-corp.atlassian.net/jira/projects/rest/api/2.0/teststep/8175269?projectId=12661"
    #url = f"https://prod-api.zephyr4jiracloud.com/connect/public/rest/api/2.0/teststep/8175269?12661={GetJWT()}"
    url = f"https://prod-api.zephyr4jiracloud.com/connect/public/rest/api/1.0/projectID=12661"
    url = f"https://prod-api.zephyr4jiracloud.com/connect/public/rest/zapi/latest/execution?projectId={project_id}&versionId={version_id}&cycleId={cycle_id}"
    url = f"https://prod-api.zephyr4jiracloud.com/connect/public/rest/api/1.0/cycle/cycleId?projectId={project_id}&versionId={version_id}"
    url = f"https://prod-api.zephyr4jiracloud.com/connect/public/rest/api/1.0/cycle/{cycle_id}?projectId={project_id}&versionId={version_id}"
    #url = f"{serverAddress}jira/rest/zapi/latest/cycle/cycleID{cycle_id}&versionId=-1&projectId:{project_id}"
    #url = f"https://prod-api.zephyr4jiracloud.com/v2/rest/zapi/latest/cycle/cycleID{cycle_id}&versionId=-1&projectId:{project_id}"
    
    headers = {
        "zapiAccessKey": "NDk0MzY5ZjctNzBkZi0zYzQwLWJjYTctMDY5YjY3Y2Y4ZWYxIDVhMjgzYjE0MTI5ZWFmNzUxZTNkYjI1ZSBVU0VSX0RFRkFVTFRfTkFNRQ",
        "Authorization": f"JWT {GetJWT()}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        test_case_data = response.json()
        print(json.dumps(test_case_data, indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n\n")
    print(url)
    print("\n\n")
    
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



