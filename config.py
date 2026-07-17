import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot configuration"""
    
    # Discord Settings
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD_ID = os.getenv("GUILD_ID")
    
    # Verification Settings
    VERIFICATION_CHANNEL_ID = os.getenv("VERIFICATION_CHANNEL_ID")
    CODE_EXPIRY_MINUTES = int(os.getenv("CODE_EXPIRY_MINUTES", 10))
    
    # API Settings
    API_BASE_URL = os.getenv("API_BASE_URL", "https://apisevers.onrender.com")
    
    # Database
    DB_PATH = os.path.join(os.path.dirname(__file__), "data", "verifications.db")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is required")
        
        if not cls.GUILD_ID:
            print("⚠️ GUILD_ID not set - commands will be global")
        
        return True