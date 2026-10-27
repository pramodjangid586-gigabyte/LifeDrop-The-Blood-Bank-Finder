import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "BloodConnect – Emergency Blood & Donor Finder"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "bloodconnect_super_secret_production_key_2026_xyz987")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "bloodconnect.db"))
    OUTDATED_THRESHOLD_HOURS: int = 24
    
    # Coordinates default (e.g., Delhi NCR / Central hub for realistic testing)
    DEFAULT_LAT: float = 28.6139
    DEFAULT_LNG: float = 77.2090

settings = Settings()
