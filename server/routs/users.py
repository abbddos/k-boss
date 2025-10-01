from flask import Blueprint, request, Response, jsonify, url_for, current_app, redirect 
import requests
from config import Config 
from models.UsersModel import User
from database import db
import string
import random
import os
from werkzeug.utils import secure_filename
import uuid
from PIL import Image
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired, BadTimeSignature 
import datetime 
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity

users_bp = Blueprint('users_bp', __name__)


ALLOWED_ROLES = ['admin', 'project manager', 'team member']
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TARGET_PROFILE_PIC_SIZE = (200, 200)

def allowed_file(filename):
    """Checks if a file's extension is allowed."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        

def process_profile_picture(filepath):
    """
    Resizes an image saved at filepath to TARGET_PROFILE_PIC_SIZE.
    Saves the resized image, overwriting the original.
    Returns the original filepath (as the file is processed in place).
    """
    try:
        img = Image.open(filepath)
        img.thumbnail(TARGET_PROFILE_PIC_SIZE, Image.Resampling.LANCZOS) 
        img.save(filepath) 
        return filepath
    except Exception as e:
        current_app.logger.error(f"Error processing image {filepath}: {e}")
        return filepath # Return original path, indicating processing failed.
    
    
def generate_random_password(email):
    """Generates a predictable password for development."""
    if '@' in email:
        username = email.split('@')[0]
        return f"{username}@123"
    else:
        return "default123" 



@users_bp.route('/', methods = ['POST'])
def create_user():
    data = request.get_json(silent = True)
    if data is None: 
        data = request.form 
        
    email = data.get('email')
    
    if not email or '@' not in email:
        return jsonify({"error": "Valid email is required"}), 400
    
    
    password = generate_random_password(email)
    first_name = data.get('first_name', None)
    last_name = data.get('last_name', None)
    role = data.get('role', 'team member')
    
    profile_pic_path = None
    if 'profile_pic' in request.files and request.files['profile_pic'].filename != '':
        file = request.files['profile_pic']
        if file and allowed_file(file.filename):
            filename_orig = secure_filename(file.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename_orig
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            try:
                file.save(file_path)
                processed_file_path = process_profile_picture(file_path)
                profile_pic_path = f"/static/profile_pics/{os.path.basename(processed_file_path)}"
            except Exception as e:
                current_app.logger.error(f"Error during profile picture save/process for create_user: {e}")
                return jsonify({"error": "Failed to save or process profile picture"}), 500
        else:
            return jsonify({"error": "Invalid file type for profile picture"}), 400
    elif 'profile_pic' in data: # Allows setting by URL directly or clearing it
        profile_pic_path = data.get('profile_pic')
    
    
    if role not in ALLOWED_ROLES:
        return jsonify({"error": f"Invalid role. Allowed roles are: {', '.join(ALLOWED_ROLES)}"}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409
    
    try:
        new_user = User(
            email=email,
            password=password, 
            first_name=first_name,
            last_name=last_name,
            role=role,
            profile_pic=profile_pic_path
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({**new_user.serialize(), "generated_password": password}), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during profile picture save/process for create_user: {e}")
        return jsonify({"error": str(e)})
    

@users_bp.route('/all', methods = ['GET'])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200 


@users_bp.route('/<int:user_id>', methods = ['GET'])
def get_user_by_id(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify(user.serialize()), 200
    
    return jsonify({"error": "User not found"}), 404


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Updates an existing user's general information (excluding password).
    Allows updating username, email, first_name, last_name, role, and profile_pic (file upload or URL).
    Password changes must be done via the dedicated /users/<id>/password endpoint.
    Returns: JSON of the updated user (excluding password_hash) or error.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    
    if not data and not request.files:
        return jsonify({"error": "No data or files provided for update"}), 400

    try:
        if 'email' in data:
            if User.query.filter(User.email == data['email'], User.id != user_id).first():
                return jsonify({"error": "Email already taken"}), 409
            user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'role' in data:
            new_role = data['role']
            if new_role not in ALLOWED_ROLES:
                return jsonify({"error": f"Invalid role. Allowed roles are: {', '.join(ALLOWED_ROLES)}"}), 400
            user.role = new_role

        if 'profile_pic' in request.files and request.files['profile_pic'].filename != '':
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename_orig = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + '_' + filename_orig
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                try:
                    # Delete old profile picture if it exists
                    if user.profile_pic and \
                        os.path.exists(os.path.join(current_app.root_path, user.profile_pic.lstrip('/'))):
                        os.remove(os.path.join(current_app.root_path, user.profile_pic.lstrip('/')))

                    file.save(file_path)
                    processed_file_path = process_profile_picture(file_path)
                    user.profile_pic = f"/static/profile_pics/{os.path.basename(processed_file_path)}"
                except Exception as e:
                    current_app.logger.error(f"Error during profile picture save/process for update_user: {e}")
                    return jsonify({"error": "Failed to save or process profile picture"}), 500
            else:
                return jsonify({"error": "Invalid file type for profile picture"}), 400
        elif 'profile_pic' in data: # Allows setting by URL directly or clearing it
            user.profile_pic = data.get('profile_pic')
            
        if 'isActive' in data:
            user.isActive = data.get('isActive') 
            
        if 'theme' in data:
            user.theme = data.get('theme')
            
        if 'language' in data:
            user.language = data.get('language')
            
        if 'notifications' in data:
            user.notifications = data.get('notifications')

        db.session.commit()
        return jsonify(user.serialize()), 200
    
    except (ValueError, TypeError):
        db.session.rollback()
        return jsonify({"error": "Invalid type for data fields"}), 400
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({"error": "Failed to update user", "details": str(e)}), 500
    
    

@users_bp.route('/<int:user_id>/password', methods = ['PUT'])
def change_user_password(user_id):
    user = User.query.get(user_id)
    
    data = request.get_json()
    if not user or not all(key in data for key in ['current_password', 'new_password']):
        return jsonify({"error": "Missing current_password or new_password"}), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not user.check_password(current_password):
        return jsonify({"error": "Incorrect current password"}), 401
    
    try:
        user.set_password(new_password)
        db.session.commit()
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password for user {user_id}: {e}")
        return jsonify({"error": "Failed to change password", "details": str(e)}), 500
    
    
@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Deletes a user by ID.
    Returns: Success message or 404 if not found.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # Delete associated profile picture file if it exists
        if user.profile_pic and \
            os.path.exists(os.path.join(current_app.root_path, user.profile_pic.lstrip('/'))):
            os.remove(os.path.join(current_app.root_path, user.profile_pic.lstrip('/')))

        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User {user_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({"error": "Failed to delete user", "details": str(e)}), 500
    
    
@users_bp.route('/login', methods = ['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "missing email or password"}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error":"Email and password are required"}), 400
    
    user = User.query.filter_by(email = email).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity = user.id)
        refresh_token = create_refresh_token(identity = user.id)
        
        user.last_login = datetime.datetime.now()
        db.session.commit()
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.serialize()
        }), 200
    
    return jsonify({"error":"Invalid credentials"}), 401