import jwt
import time

def GetToken():
    access_key = "NDk0MzY5ZjctNzBkZi0zYzQwLWJjYTctMDY5YjY3Y2Y4ZWYxIDVhMjgzYjE0MTI5ZWFmNzUxZTNkYjI1ZSBVU0VSX0RFRkFVTFRfTkFNRQ"
    secret_key = "Lg95PR1mucpqtwzyoeEExjoz0p3DjY_2-srn06ihqcE"
    #secret_key = "ATATT3xFfGF0VPJFulHvFMvk-Z7tx9XTJvk8qxyPP8zok2jC7_dwaPjI3uMlYdbOwfSdk7PgYuAmKJ38dGecEcOIbBCgxPMJ3W16DUsIa1S5ERfcbsWnxrsO1xIhSCvzZzWdWCNc9AzXddNus8-QzJiZOr8AVketJGMXFJnCKHRmFcRhPc1bsPo=016B99B7"
    account_id = "5a283b14129eaf751e3db25e"

    # Construct the payload
    payload = {
        "sub": account_id,
        "iss": access_key,
        "exp": int(time.time()) + 3600, # Token expiration time (e.g., 1 hour)
        "iat": int(time.time())
    }

    # Encode the JWT
    return jwt.encode(payload, secret_key, algorithm="HS256")

if __name__ == "__main__":
    print(GetToken())
