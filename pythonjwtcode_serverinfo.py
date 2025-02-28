import json
import jwt
import time
import hashlib
import requests


def is_json(data):
    try:
        json.loads(data)
    except ValueError:
        return False
    return True


# USER
ACCOUNT_ID = ''

# ACCESS KEY from navigation >> Tests >> API Keys
ACCESS_KEY = ''

# ACCESS KEY from navigation >> Tests >> API Keys
SECRET_KEY = ''

# JWT EXPIRE how long token been to be active? 3600 == 1 hour
JWT_EXPIRE = 3600

# BASE URL for Zephyr for Jira Cloud
BASE_URL = 'https://prod-api.zephyr4jiracloud.com/connect'

# RELATIVE PATH for token generation and make request to api
RELATIVE_PATH = '/public/rest/api/1.0/serverinfo'
#public/rest/api/1.0/teststep/8175324/1?projectId=12661
            

# CANONICAL PATH (Http Method & Relative Path & Query String)
CANONICAL_PATH = 'GET&'+ RELATIVE_PATH

# TOKEN HEADER: to generate jwt token
payload_token = {
            'sub': ACCOUNT_ID,
            'qsh': hashlib.sha256(CANONICAL_PATH.encode('utf-8')).hexdigest(),
            'iss': ACCESS_KEY,
            'exp': int(time.time())+JWT_EXPIRE,
            'iat': int(time.time())
        }

# GENERATE TOKEN
token = jwt.encode(payload_token, SECRET_KEY, algorithm='HS256')

# REQUEST HEADER: to authenticate and authorize api
headers = {
            'Authorization': 'JWT '+token,
            'Content-Type': 'text/plain',
            'zapiAccessKey': ACCESS_KEY
        }
'''
# REQUEST HEADER: to create cycle
headers = {
    'Authorization': 'JWT '+token,
    'Content-Type': 'application/json',
    'zapiAccessKey': ACCESS_KEY
}
'''
# REQUEST PAYLOAD: to create cycle

FinalAPI = '/public/rest/api/1.0/serverinfo'
# MAKE REQUEST:
raw_result = requests.get(BASE_URL + FinalAPI, headers=headers, verify=False)
if is_json(raw_result.text):

    # JSON RESPONSE: convert response to JSON
    json_result = json.loads(raw_result.text)

    # PRINT RESPONSE: pretty print with 4 indent
    print(json.dumps(json_result, indent=4, sort_keys=True))

else:
    print(raw_result.text)