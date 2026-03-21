from sqlalchemy.orm import Session
import models
import database
import security

def create_the_admin():
    # 1. Open a connection to the database
    db = database.SessionLocal()
    
    try:
        # 2. Pick your credentials
        username = "admin"
        password = "MySecurePassword2026toTestForNow" 

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
    