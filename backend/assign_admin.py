from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Find the current admin user (if any) or just add this one as admin
    # The user wants +91 9025570209 as admin
    mobile = "+91 9025570209"
    
    # 1. Check if user exists
    user = conn.execute(text("SELECT id FROM users WHERE mobile = :mobile"), {"mobile": mobile}).fetchone()
    
    if not user:
        print(f"User with mobile {mobile} not found. Creating...")
        conn.execute(text("INSERT INTO users (mobile, is_active, created_at, updated_at) VALUES (:mobile, true, now(), now())"), {"mobile": mobile})
        user = conn.execute(text("SELECT id FROM users WHERE mobile = :mobile"), {"mobile": mobile}).fetchone()
    
    user_id = user[0]
    print(f"User ID for {mobile} is {user_id}")

    # 2. Get ADMIN role id
    role = conn.execute(text("SELECT id FROM roles WHERE name = 'ADMIN'")).fetchone()
    # Get first org id
    org = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
    
    if not role:
        print("ADMIN role not found!")
    elif not org:
        print("No organization found! Create an organization first.")
    else:
        role_id = role[0]
        org_id = org[0]
        # 3. Assign role to user
        # Check if already assigned
        existing = conn.execute(text("SELECT 1 FROM user_roles WHERE user_id = :user_id AND role_id = :role_id AND org_id = :org_id"), 
                               {"user_id": user_id, "role_id": role_id, "org_id": org_id}).fetchone()
        if not existing:
            print(f"Assigning ADMIN role to user {user_id} in org {org_id}...")
            conn.execute(text("INSERT INTO user_roles (user_id, role_id, org_id, created_at, updated_at) VALUES (:user_id, :role_id, :org_id, now(), now())"), 
                        {"user_id": user_id, "role_id": role_id, "org_id": org_id})
        else:
            print("User is already an ADMIN in this organization.")

            
    conn.commit()
print("Done.")
