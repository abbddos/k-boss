import os
from datetime import datetime, timedelta

class Config:
    # Get the base directory of the project
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    
    # Define the SQLite database URI. It will create `users.db` in the user-service directory.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASEDIR, 'k-boss.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppress warning
    SECRET_KEY = 'thisisasecretkeyforsomereasonidonotlikeatall'
    
    # Allow CORS from the frontend application's development server
    CORS_ORIGINS = ["http://localhost:3000"] # Adjust if your frontend runs on a different port/domain

    # Secret key for signing password reset and email verification tokens
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    # Expiry time for password reset tokens (e.g., 1 hour = 3600 seconds)
    PASSWORD_RESET_TOKEN_EXPIRATION = 3600
    # Expiry time for email verification tokens (e.g., 24 hours = 86400 seconds)
    EMAIL_VERIFICATION_TOKEN_EXPIRATION = 86400

    # Upload folder for profile pictures
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'profile_pics')
    PROJECTS_UPLOAD_FOLDER = os.path.join(BASEDIR, 'uploads', 'projects')
    
    JWT_SECRET_KEY = 'your-super-secret-jwt-key'  # Use environment variable in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)