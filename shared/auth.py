from datetime import timedelta

from authx import AuthX, AuthXConfig

from shared.config import settings

auth_config = AuthXConfig(
    JWT_SECRET_KEY=settings.jwt_secret_key,
    JWT_TOKEN_LOCATION=["headers"],
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),
)

auth = AuthX(config=auth_config)
