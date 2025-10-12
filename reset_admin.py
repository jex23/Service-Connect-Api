#!/usr/bin/env python3
"""
Script to reset/recreate the superadmin account
Usage: python3 reset_admin.py
"""

from app import app, db
from models import Admin

def reset_superadmin():
    with app.app_context():
        # Delete existing admin
        email = 'jay.villaflor@gmail.com'
        Admin.query.filter_by(email=email).delete()
        db.session.commit()
        print(f"✓ Deleted existing admin with email {email}")

        # Create new superadmin
        superadmin = Admin(
            full_name='Jay Villaflor',
            email=email,
            role='superadmin',
            address='Admin Office'
        )
        superadmin.set_password('admin123')

        db.session.add(superadmin)
        db.session.commit()

        print("✓ Superadmin account created successfully!")
        print(f"Email: {email}")
        print("Password: admin123")
        print(f"Password hash: {superadmin.password_hash[:50]}...")

        # Test login
        test_admin = Admin.query.filter_by(email=email).first()
        if test_admin and test_admin.check_password('admin123'):
            print("✓ Password verification test PASSED!")
        else:
            print("✗ Password verification test FAILED!")

if __name__ == '__main__':
    reset_superadmin()
