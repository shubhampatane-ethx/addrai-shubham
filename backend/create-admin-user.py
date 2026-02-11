#!/usr/bin/env python3
"""
Create Admin User with Correct Bcrypt Hash
Runs automatically during container startup
"""
import bcrypt
import psycopg2
import os
import sys
import time

def wait_for_database(max_retries=30):
    """Wait for database to be ready"""
    db_host = os.getenv('DB_HOST', 'addrai-db')
    db_name = os.getenv('DB_NAME', 'AddrAI-database')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres123')
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password
            )
            conn.close()
            print(f"✅ Database connection successful!")
            return True
        except psycopg2.OperationalError:
            if i < max_retries - 1:
                print(f"⏳ Waiting for database... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"❌ Database not available after {max_retries} attempts")
                return False
    return False

def create_admin_user():
    """Create admin user with bcrypt-hashed password"""
    
    # Database connection settings
    db_host = os.getenv('DB_HOST', 'addrai-db')
    db_name = os.getenv('DB_NAME', 'AddrAI-database')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres123')
    
    # Admin credentials
    admin_username = 'admin'
    admin_password = 'admin'
    admin_email = 'admin@addrai.com'
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cur = conn.cursor()
        
        # Check if admin user already exists
        cur.execute(
            "SELECT username, password_hash FROM users WHERE username = %s",
            (admin_username,)
        )
        existing_user = cur.fetchone()
        
        # Generate bcrypt hash
        password_bytes = admin_password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hash_bytes = bcrypt.hashpw(password_bytes, salt)
        hash_string = hash_bytes.decode('utf-8')
        
        # Verify the hash works
        test_verify = bcrypt.checkpw(password_bytes, hash_bytes)
        if not test_verify:
            print(f"❌ ERROR: Generated hash failed verification test!")
            return False
        
        print(f"✅ Generated bcrypt hash: {hash_string[:30]}...")
        print(f"✅ Hash verification test: PASSED")
        
        if existing_user:
            # Check if existing hash works
            existing_hash = existing_user[1]
            try:
                if bcrypt.checkpw(password_bytes, existing_hash.encode('utf-8')):
                    print(f"✅ Admin user already exists with correct password")
                    return True
                else:
                    print(f"⚠️  Admin user exists but password doesn't match - updating...")
            except Exception as e:
                print(f"⚠️  Admin user exists but hash is invalid - updating...")
            
            # Update existing user with new hash
            cur.execute(
                """
                UPDATE users 
                SET password_hash = %s, updated_at = NOW()
                WHERE username = %s
                """,
                (hash_string, admin_username)
            )
            print(f"✅ Updated admin user password")
        else:
            # Create new admin user
            cur.execute(
                """
                INSERT INTO users (user_id, username, email, password_hash, full_name, role_id, is_active, created_at)
                VALUES (gen_random_uuid(), %s, %s, %s, 'System Administrator', 1, true, NOW())
                """,
                (admin_username, admin_email, hash_string)
            )
            print(f"✅ Created admin user")
        
        conn.commit()
        
        # Verify the user was created/updated correctly
        cur.execute(
            "SELECT username, email, LENGTH(password_hash) as hash_len FROM users WHERE username = %s",
            (admin_username,)
        )
        result = cur.fetchone()
        
        if result:
            print(f"✅ Admin user verified in database:")
            print(f"   Username: {result[0]}")
            print(f"   Email: {result[1]}")
            print(f"   Hash length: {result[2]} chars")
            print(f"✅ Login credentials: {admin_username} / {admin_password}")
            return True
        else:
            print(f"❌ ERROR: Admin user not found after creation")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  AddrAI - Admin User Setup")
    print("=" * 60)
    
    # Wait for database
    if not wait_for_database():
        print("❌ Failed to connect to database")
        sys.exit(1)
    
    # Create admin user
    if create_admin_user():
        print("=" * 60)
        print("✅ ADMIN USER SETUP COMPLETE")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ ADMIN USER SETUP FAILED")
        print("=" * 60)
        sys.exit(1)
