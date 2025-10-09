from database import db 
import datetime 
from flask import current_app 

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key = True)
    code  = db.Column(db.String(20), nullable = False, unique = True)
    description = db.Column(db.Text, nullable = True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    documents = db.relationship('ProjectDocument', backref='project', lazy=True, cascade='all, delete-orphan')
    
    
    def __init__(self, code, description = None):
        self.code  = code 
        self.description = description
        
    def validate_code(self):
        """Validate project code format"""
        if not self.code or len(self.code) > 20:
            raise ValueError("Project code must be between 1 and 20 characters")
    
    def serialize(self):
        return {
            "id": self.id, 
            "code": self.code,
            "description": self.description, 
            "created_at": self.created_at,
            "documents": [document.serialize() for document in self.documents]
        }
    
    
    

class ProjectDocument(db.Model):
    __tablename__ = 'project_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    file_type = db.Column(db.String(100), nullable=False)  # MIME type
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.now)
    
    def __init__(self, project_id, filename, original_filename, file_path, file_size, file_type):
        self.project_id = project_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size 
        self.file_type = file_type 
        
        
    def validate_file_size(self):
        """Validate file size is reasonable"""
        if self.file_size <= 0:
            raise ValueError("File size must be positive")
        if self.file_size > 100 * 1024 * 1024:  # 100MB max
            raise ValueError("File size too large")
        
        
    def serialize(self):
        return{
            "id": self.id,
            "project_id": self.project_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "uploaded_at": self.uploaded_at
        } 