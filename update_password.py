from sqlalchemy.orm import Session
import models, database, security

def update_admin_password():
    db = database.SessionLocal()
    try:
        # 1. Target the specific user
        username = "admin"
        new_password = "YourNewSecurePassword123" # 👈 Put your NEW password here!

        user = db.query(models.User).filter(models.User.username == username).first()

        if user:
            # 🔐 Create a FRESH hash for the NEW password
            user.hashed_password = security.get_password_hash(new_password)
            db.commit()
            print(f"✅ SUCCESS: Password for '{username}' has been updated!")
        else:
            print(f"❌ ERROR: User '{username}' not found. Did you delete the database?")

    except Exception as e:
        print(f"⚠️ Something went wrong: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_password()
    