import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "verifications.db")

def get_db_connection():
    """Get a database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verified users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            discord_id INTEGER PRIMARY KEY,
            discord_name TEXT NOT NULL,
            roblox_id INTEGER NOT NULL,
            roblox_username TEXT NOT NULL,
            roblox_display TEXT NOT NULL,
            special_id TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Pending verifications table (for bot-generated codes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_verifications (
            code TEXT PRIMARY KEY,
            discord_id INTEGER NOT NULL,
            discord_name TEXT NOT NULL,
            roblox_user_id TEXT NOT NULL,
            roblox_username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    """)
    
    # Special IDs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS special_ids (
            roblox_user_id TEXT PRIMARY KEY,
            special_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            display_name TEXT,
            friends_count TEXT DEFAULT '0',
            verified BOOLEAN DEFAULT 0,
            verified_at TIMESTAMP,
            discord_id INTEGER,
            discord_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_verifications_code 
        ON pending_verifications(code)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pending_verifications_expires 
        ON pending_verifications(expires_at)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_special_ids_special_id 
        ON special_ids(special_id)
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database tables created/verified")

# ============================================
# PENDING VERIFICATION FUNCTIONS
# ============================================

def store_pending_verification(code: str, discord_id: int, discord_name: str, roblox_user_id: str, roblox_username: str):
    """Store a pending verification code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expires_at = datetime.now() + timedelta(minutes=10)
    
    cursor.execute("""
        INSERT OR REPLACE INTO pending_verifications 
        (code, discord_id, discord_name, roblox_user_id, roblox_username, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (code, discord_id, discord_name, roblox_user_id, roblox_username, expires_at))
    
    conn.commit()
    conn.close()
    return True

def get_pending_verification(code: str) -> Optional[Dict[str, Any]]:
    """Get a pending verification by code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM pending_verifications WHERE code = ?
    """, (code,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "code": row["code"],
            "discord_id": row["discord_id"],
            "discord_name": row["discord_name"],
            "roblox_user_id": row["roblox_user_id"],
            "roblox_username": row["roblox_username"],
            "created_at": datetime.fromisoformat(row["created_at"]),
            "expires_at": datetime.fromisoformat(row["expires_at"])
        }
    return None

def delete_pending_verification(code: str):
    """Delete a pending verification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM pending_verifications WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def cleanup_expired_pending():
    """Delete expired pending verifications"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM pending_verifications 
        WHERE expires_at < CURRENT_TIMESTAMP
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"🗑️ Cleaned up {deleted} expired pending verifications")

# ============================================
# SPECIAL ID FUNCTIONS
# ============================================

def save_special_id(roblox_user_id: str, special_id: str, username: str, display_name: str = None, friends_count: str = '0'):
    """Save a special ID for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO special_ids 
        (roblox_user_id, special_id, username, display_name, friends_count)
        VALUES (?, ?, ?, ?, ?)
    """, (roblox_user_id, special_id, username, display_name or username, friends_count))
    
    conn.commit()
    conn.close()

def get_special_id(roblox_user_id: str) -> Optional[Dict[str, Any]]:
    """Get a special ID by user ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM special_ids WHERE roblox_user_id = ?
    """, (roblox_user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "roblox_user_id": row["roblox_user_id"],
            "special_id": row["special_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "friends_count": row["friends_count"],
            "verified": bool(row["verified"]),
            "verified_at": datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
            "discord_id": row["discord_id"],
            "discord_username": row["discord_username"],
            "created_at": datetime.fromisoformat(row["created_at"])
        }
    return None

def get_special_id_by_code(special_id: str) -> Optional[Dict[str, Any]]:
    """Get user by special ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM special_ids WHERE special_id = ?
    """, (special_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "roblox_user_id": row["roblox_user_id"],
            "special_id": row["special_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "friends_count": row["friends_count"],
            "verified": bool(row["verified"]),
            "verified_at": datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
            "discord_id": row["discord_id"],
            "discord_username": row["discord_username"],
            "created_at": datetime.fromisoformat(row["created_at"])
        }
    return None

def mark_user_verified(roblox_user_id: str, discord_id: int, discord_username: str):
    """Mark a user as verified"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE special_ids 
        SET verified = 1, 
            verified_at = CURRENT_TIMESTAMP,
            discord_id = ?,
            discord_username = ?
        WHERE roblox_user_id = ?
    """, (discord_id, discord_username, roblox_user_id))
    
    conn.commit()
    conn.close()

def get_verified_user_by_discord(discord_id: int) -> Optional[Dict[str, Any]]:
    """Get verified user by Discord ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM special_ids WHERE discord_id = ? AND verified = 1
    """, (discord_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "roblox_user_id": row["roblox_user_id"],
            "special_id": row["special_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "friends_count": row["friends_count"],
            "verified": bool(row["verified"]),
            "verified_at": datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
            "discord_id": row["discord_id"],
            "discord_username": row["discord_username"],
            "created_at": datetime.fromisoformat(row["created_at"])
        }
    return None

def get_all_special_ids() -> List[Dict[str, Any]]:
    """Get all special IDs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM special_ids ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "roblox_user_id": row["roblox_user_id"],
        "special_id": row["special_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "friends_count": row["friends_count"],
        "verified": bool(row["verified"]),
        "verified_at": datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
        "discord_id": row["discord_id"],
        "discord_username": row["discord_username"],
        "created_at": datetime.fromisoformat(row["created_at"])
    } for row in rows]

def get_verified_users() -> List[Dict[str, Any]]:
    """Get all verified users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM special_ids WHERE verified = 1 ORDER BY verified_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "roblox_user_id": row["roblox_user_id"],
        "special_id": row["special_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "friends_count": row["friends_count"],
        "verified": bool(row["verified"]),
        "verified_at": datetime.fromisoformat(row["verified_at"]) if row["verified_at"] else None,
        "discord_id": row["discord_id"],
        "discord_username": row["discord_username"],
        "created_at": datetime.fromisoformat(row["created_at"])
    } for row in rows]