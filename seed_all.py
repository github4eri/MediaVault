import database, models, security
from sqlalchemy.orm import Session

def seed():
    db = next(database.get_db())
    
    # 1. Create Admin
    admin = db.query(models.User).filter(models.User.username == "admin100").first()
    if not admin:
        new_admin = models.User(
            username="admin100", 
            hashed_password=security.hash_password("your_secret_admin_pw") # 👈 Put your real admin pw here
        )
        db.add(new_admin)
        print("✅ Admin created!")
    
    # 2. Create Guest
    guest = db.query(models.User).filter(models.User.username == "guest").first()
    if not guest:
        new_guest = models.User(
            username="guest", 
            hashed_password=security.hash_password("guest123")
        )
        db.add(new_guest)
        print("✅ Guest created!")
    
    db.commit()
    print("🚀 Database is ready!")

if __name__ == "__main__":
    seed()