
import sys
import os
from passlib.hash import pbkdf2_sha256
from db import create_user, get_user_by_email

# Add current dir to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def provision_test_user():
    email = "test@test.com"
    raw_pw = "test1234"
    name = "Test User"
    
    # Check if exists
    existing = get_user_by_email(email)
    if existing:
        print(f"User {email} already exists.")
        # Verify password if possible, or just reset?
        # For now, just assume it works or update if needed.
        # But we can't update pw easily with create_user.
        # Let's create a NEW one 'debug@test.com' to be sure.
        email = "debug@test.com"
        print(f"Creating alternate user {email}...")
    
    # Hash password
    pw_hash = pbkdf2_sha256.hash(raw_pw)
    
    if create_user(email, pw_hash, name):
        print(f"✅ User Created: {email} / {raw_pw}")
    else:
        print("❌ Failed to create user")

if __name__ == "__main__":
    provision_test_user()
