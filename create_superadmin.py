#!/usr/bin/env python3
"""
Script to create the first superadmin account
Usage: python3 create_superadmin.py
"""

from app import app, db
from models import Admin

def create_superadmin():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Check if superadmin already exists
        email = 'jay.villaflor@gmail.com'
        existing_admin = Admin.query.filter_by(email=email).first()

        if existing_admin:
            print(f"Admin with email {email} already exists!")
            print(f"Role: {existing_admin.role}")
            print(f"Active: {existing_admin.is_active}")
            return

        # Create superadmin
        superadmin = Admin(
            full_name='Jay Villaflor',
            email=email,
            role='superadmin',
            address='Admin Office'
        )
        superadmin.set_password('admin123')  # Change this password!

        db.session.add(superadmin)
        db.session.commit()

        print("✓ Superadmin account created successfully!")
        print(f"Email: {email}")
        print("Password: admin123")
        print("\n⚠️  IMPORTANT: Please change this password after first login!")

if __name__ == '__main__':
    create_superadmin()
