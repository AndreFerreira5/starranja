import os
from secrets import token_hex

from src.config import settings

if "PASETO_SECRET_KEY" not in os.environ:
    settings.auth.PASETO_SECRET_KEY = token_hex(32)
