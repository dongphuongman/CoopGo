from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "CoopGo API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "mysql+aiomysql://docgen:docgenpassword@db:3306/docgen"

    # Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "storage" / "outputs"
    TEMP_DIR: Path = BASE_DIR / "storage" / "temp"

    # LibreOffice
    LIBREOFFICE_BIN: str = "libreoffice"

    # Ollama Cloud AI (cho auto-label)
    OLLAMA_API_KEY: str = "658916e60a664876bfed75d75c9c717d.O9cj7KJSt4_zw5kmMFfNnorf"  # Lấy tại https://ollama.com/settings/keys
    AI_ENABLED: bool = True

    # Rate limiting
    MAX_CONCURRENT_RENDERS: int = 10
    RENDER_TIMEOUT_SECONDS: int = 60

    # Upload
    MAX_UPLOAD_MB: float = 20

    # Thông báo hết hạn
    SCHEDULER_ENABLED: bool = False  # bật job chạy đêm nhắc hết hạn
    NOTIFY_WITHIN_DAYS: int = 30
    # Email (SMTP) — để trống = không gửi mail
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    NOTIFY_EMAILS: str = ""  # cách nhau dấu phẩy
    # Zalo OA — để trống = không gửi Zalo
    ZALO_OA_TOKEN: str = ""
    ZALO_USER_IDS: str = ""  # cách nhau dấu phẩy

    # API Key (đơn giản, có thể nâng lên JWT sau)
    API_SECRET_KEY: str = "changeme-in-production"

    # URL web công khai (để sinh QR trỏ tới trang /verify/:code)
    PUBLIC_WEB_URL: str = "http://localhost:3000"

    def ensure_dirs(self):
        for d in [self.UPLOAD_DIR, self.OUTPUT_DIR, self.TEMP_DIR]:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
