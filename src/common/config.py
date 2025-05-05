import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_KEY = os.environ["JWT_KEY"]
ACCESS_TOKEN_EXPIRES = int(os.environ["ACCESS_TOKEN_EXPIRES"])
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

from fastapi_mail import ConnectionConfig

# Email configuration for FastAPI Mail
EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=os.environ["MAIL_USERNAME"],
    MAIL_PASSWORD=os.environ["MAIL_PASSWORD"],
    MAIL_FROM=os.environ["MAIL_FROM"],
    MAIL_PORT=587,
    MAIL_SERVER=os.environ["MAIL_SERVER"],
    MAIL_FROM_NAME="Your App Name",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)