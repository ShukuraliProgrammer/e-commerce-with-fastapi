from fastapi import (BackgroundTasks, UploadFile, File, Form, Depends, HTTPException, status)
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import dotenv_values
from pydantic import BaseModel, EmailStr
from typing import List
from models import User
import jwt

config = dotenv_values('.env')

conf = ConnectionConfig(
    MAIL_USERNAME=config['EMAIL'],
    MAIL_PASSWORD=config['PASSWORD'],
    MAIL_FROM=config['EMAIL'],
    MAIL_STARTTLS=True,
    MAIL_PORT=587,
    MAIL_SERVER='smtp.gmail.com',
    VALIDATE_CERTS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)


class EmailSchema(BaseModel):
    email: List[EmailStr]


async def send_email(email: EmailSchema, instance: User):
    token_data = {
        "id": instance.id,
        "username": instance.username,
    }
    token = jwt.encode(token_data, config["SECRET"])

    template = f"""
                    <DOCTYPE html>
                    <html>
                        <head>
                        
                        </head>
                        <body>
                            <div>
                                <h3>Account Verification</h3>
                                <br>
                                
                                <p>Thanks for choosing this project</p>
                                
                                <a href="http://127.0.0.1:8000/verification/?token={token}"> Verify Your email Addresss</a>
                                
                            </div>
                        </body>
                    </html>
                """

    message = MessageSchema(
        subject="E-Commerce Account Verification EMail",
        recipients=email,
        body=template,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    await fm.send_message(message)
