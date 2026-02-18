from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str = ""
    DB_URL: str
    REDIS_URL: str
    SHOP_CHANNEL_ID: int = 0
    COURIER_CHANNEL_ID: int = 0
    WEBAPP_URL: str = "https://example.com"
    BOT_USERNAME: str = "fiesta_bot"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = "secret"

    @property
    def admin_ids(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
