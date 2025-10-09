from flask import Flask, jsonify, request, Response 
from flask_cors import CORS
import requests 
import json 
from config import Config
from database import db, init_db 
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object(Config) 
CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

init_db(app)
jwt = JWTManager(app)

from routs.users import users_bp 
from routs.projects import projects_bp

app.register_blueprint(users_bp, url_prefix = "/api/vi/users")
app.register_blueprint(projects_bp, url_prefix = "/api/vi/projects")

@app.route('/')
def home():
    """Root endpoint for the User Service."""
    return jsonify({"message": "User Service is running!", "status": "OK"})


if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables are created when app is run directly
        db.create_all()
    app.run(port=5000, debug=True)