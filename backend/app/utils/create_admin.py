import argparse
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, Base, engine
from app.services.auth_service import create_admin_user
from app.schemas.user import AdminUserCreate
from app.models.user import AdminUser


def main():
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("username")
    parser.add_argument("password")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        existing = db.query(AdminUser).filter_by(username=args.username).first()
        if existing:
            print("User already exists")
            return
        user = create_admin_user(db, AdminUserCreate(username=args.username, password=args.password, is_active=True))
        print(f"Created admin user {user.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
