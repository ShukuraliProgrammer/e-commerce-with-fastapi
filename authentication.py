from passlib.context import CryptContext
import jwt
from dotenv import dotenv_values
from models import User
from fastapi.exceptions import HTTPException
from fastapi import status

config = dict(dotenv_values('.env'))

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_hash_password(password):
    return pwd_context.hash(password)


async def verify_token(token: str):
    try:
        pyload = jwt.decode(token, config["SECRET"], algorithms=['HS256'])
        user = await User.get(id=pyload.get("id"))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(username, password):
    user = await User.get(username=username)
    if user and verify_password(password, user.password):
        return user
    else:
        return False


async def token_generator(username: str, password: str):
    user = await authenticate_user(username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User data",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_data = {
        "id": user.id,
        "username": user.username
    }

    token = jwt.encode(token_data, config["SECRET"])
    return token
