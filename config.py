import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-jwt-key-2026")
    # رابط قاعدة بيانات بوستجرام (PostgreSQL) باستخدام مكتبة psycopg الرسمية
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg://skills_user:secret_password_123@localhost:5432/skills_db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-skills-app-2026")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False