import os

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
SESSION_TTL = int(os.getenv("SESSION_TTL", "31536000"))  # 1 year (365 days)
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", "31536000"))  # 1 year (365 days)
COOKIE_NAME = "ustb_sid"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # false for local dev