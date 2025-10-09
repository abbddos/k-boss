from flask import Blueprint, request, Response, jsonify, url_for, current_app, redirect 
import requests
from config import Config 
from models.ProjectsModel import Project, ProjectDocument
from database import db
import string
import random
import os
from werkzeug.utils import secure_filename
import uuid
from PIL import Image
import datetime 
from flask_jwt_extended import jwt_required, get_jwt_identity
import shutil


projects_bp = Blueprint('proejects_pb', __name__)


@projects_bp.route('/', methods = ['POST'])
@jwt_required()
def create_project():
    
    data = request.get_json(silent = True)
    if data is None:
        data = request.form
        
        
    if not data and not request.files:
        return jsonify({"error": "No data or files provided for update"}), 400
    
    try:
        code = data.get('code')
        description = data.get('description')
        
        new_project = Project(
            code = code, 
            description = description
        )
        
        #new_project.validate_code() 
        
        db.session.add(new_project)
        db.session.flush()
        
        
        project_folder = os.path.join(current_app.config['PROJECTS_UPLOAD_FOLDER'], code)
        os.makedirs(project_folder, exist_ok = True)
        
        files = request.files.getlist('documents')
        for file in files:
            if file.filename:
                
                file.seek(0, 2)  # Seek to end to get size
                file_size = file.tell()
                file.seek(0)
                
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(project_folder, unique_name)
                file.save(file_path)
                
                document = ProjectDocument(
                    project_id=new_project.id,
                    filename=unique_name,
                    original_filename=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    file_type=file.content_type
                )
                
                #document.validate_file_size()
                
                db.session.add(document)
                
        db.session.commit()
        print("Request form:", request.form)
        print("Request files:", request.files)
        print("Files list:", request.files.getlist('documents'))
        return jsonify(new_project.serialize()), 200
    
    except Exception as e:
        db.session.rollback()
        print("Request form:", request.form)
        print("Request files:", request.files)
        print("Files list:", request.files.getlist('documents'))
        return jsonify({"error": str(e)}), 500
                
                
                
@projects_bp.route('/all', methods = ['GET'])
@jwt_required()
def get_all_projects():
    all_projects = Project.query.all()
    return jsonify([project.serialize() for project in all_projects]), 200



@projects_bp.route('/<string:code>', methods = ['GET'])
@jwt_required()
def get_project_by_code(code):
    project = Project.query.filter_by(code = code).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    return jsonify(project.serialize()), 200



@projects_bp.route('/<string:code>', methods = ['PUT'])
@jwt_required()
def update_project(code):
    project = Project.query.filter_by(code = code).first()
    
    if not project:
        return jsonify({"error":"Project not found"}), 404 
    
    
    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    
    if not data and not request.files:
        return jsonify({"error": "No data or files provided for update"}), 400
    
    try:
        if 'description' in data:
            project.description = data['description']
        if 'documents' in request.files and request.files['documents'] != '':
            files = request.files.getlist('documents')
            project_folder = os.path.join(current_app.config['PROJECTS_UPLOAD_FOLDER'], code)
            os.makedirs(project_folder, exist_ok=True)
            for file in files:
                if file.filename:
                    
                    file.seek(0, 2)  # Seek to end to get size
                    file_size = file.tell()
                    file.seek(0)
                    
                    filename = secure_filename(file.filename)
                    unique_name = f"{uuid.uuid4().hex}_{filename}"
                    file_path = os.path.join(project_folder, unique_name)
                    file.save(file_path)
                    
                    document = ProjectDocument(
                        project_id=project.id,
                        filename=unique_name,
                        original_filename=filename,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type=file.content_type
                    )
                    
                    document.validate_file_size()
                    
                    db.session.add(document)
        
        db.session.commit()
        return jsonify(project.serialize()), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating project {code}: {e}")
        return jsonify({"error": "Failed to update project", "details": str(e)}), 500
            

@projects_bp.route('/documents/<int:doc_id>', methods = ['DELETE'])
@jwt_required()
def delete_document(doc_id):
    document = ProjectDocument.query.get(doc_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404 
    
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
            
        db.session.delete(document)
        db.session.commit()
        return jsonify({"message":"Document deleted successfully"}) , 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting document {doc_id}: {e}")
        return jsonify({"error": "Failed to delete document", "details": str(e)}), 500
    
    
@projects_bp.route('/<string:code>', methods=['DELETE'])
@jwt_required()
def delete_project(code):
    project = Project.query.filter_by(code=code).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404 
    
    try:
        project_folder = os.path.join(current_app.config['PROJECTS_UPLOAD_FOLDER'], code)
        
        # Delete project folder and all files
        if os.path.exists(project_folder):
            shutil.rmtree(project_folder)
        
        # Delete project (cascade will handle documents in database)
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({"message": "Project deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting project {code}: {e}")
        return jsonify({"error": "Failed to delete project", "details": str(e)}), 500