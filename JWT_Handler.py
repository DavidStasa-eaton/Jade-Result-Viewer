import jwt
import time

def GetToken():
    access_key = ""
    secret_key = ""
    account_id = ""

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
