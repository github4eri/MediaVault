import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import models
import database
import security

# 1. Load the sticky note (.env)
load_dotenv()

def create_the_admin():
    db = database.SessionLocal()
    
    try:
        # 2. CHANGE THIS PART: Grab from .env instead of typing it here
        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")

        # Validation: Make sure the .env actually had data
        if not username or not password:
            print("❌ ERROR: ADMIN_USERNAME or ADMIN_PASSWORD is missing in .env!")
            return

        # 3. Check if this user already exists (so we don't make duplicates)
        existing_user = db.query(models.User).filter(models.User.username == username).first()

        if not existing_user:
            # 🔐 HASH the password (don't store it as plain text!)
            hashed = security.get_password_hash(password)
            
            # 🏗️ Create the User object
            new_user = models.User(
                username=username, 
                hashed_password=hashed
            )
            
            # 💾 Save it to the database
            db.add(new_user)
            db.commit()
            print(f"🎉 SUCCESS: Admin user '{username}' has been created!")
        else:
            print(f"⚠️ NOTICE: The user '{username}' already exists in the vault.")

    except Exception as e:
        print(f"❌ ERROR: Something went wrong: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_the_admin()
    