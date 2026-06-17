import os

# Intentional vulnerability: hardcoded secrets
SECRET_KEY = "super_secret_key_123"
DATABASE_URL = "postgresql://admin:password123@localhost/prod_db"
API_KEY = "sk-prod-openai-abc123xyz987"

DEBUG = True  # Should be False in production
