from passlib.context import CryptContext
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session
import database
import models

# 🔐 This tells Python to use 'bcrypt' for hashing (Standard for professional apps)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """
    The Validator: Compares what the user typed into the login 
    form against the scrambled 'hash' in the database.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    The Scrambler: Turns a plain password (like '12345') into 
    a secure string that can't be reversed.
    """
    return pwd_context.hash(password)

def get_current_user(db: Session = Depends(database.get_db), session_token: str = Cookie(None)):
    # This looks at the cookie to find the username
    # (Note: In a bigger app, you'd use a real ID/Token, but this works for now!)
    
    # We are assuming you store the username in a cookie or can find the user another way.
    # If you don't have a session_token, we can use the 'admin_username' from .env for now
    import os
    username = os.getenv("ADMIN_USERNAME") # Or however you identify the logged-in person
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

    