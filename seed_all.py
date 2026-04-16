import os
import database, models, security
from sqlalchemy.orm import Session

def seed():
    db = next(database.get_db())
    
    # Grab from Render Environment Variables
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    guest_user = os.getenv("GUEST_USERNAME")
    guest_pass = os.getenv("GUEST_PASSWORD")

    # Use the name that is actually in your security.py (likely get_password_hash)
    if admin_user and admin_pass:
        admin_exists = db.query(models.User).filter(models.User.username == admin_user).first()
        if not admin_exists:
            new_admin = models.User(
                username=admin_user, 
                hashed_password=security.get_password_hash(admin_pass) 
            )
            db.add(new_admin)
            print("✅ Admin created!")

    if guest_user and guest_pass:
        guest_exists = db.query(models.User).filter(models.User.username == guest_user).first()
        if not guest_exists:
            new_guest = models.User(
                username=guest_user, 
                hashed_password=security.get_password_hash(guest_pass) 
            )
            db.add(new_guest)
            print("✅ Guest created!")
    
    db.commit()

if __name__ == "__main__":
    seed()