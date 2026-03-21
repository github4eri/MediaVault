from passlib.context import CryptContext

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
    