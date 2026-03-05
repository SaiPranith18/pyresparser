import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

logger = logging.getLogger(__name__)


class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    structured_data = db.Column(db.JSON, nullable=False)
    extracted_text = db.Column(db.Text)
    layout_html = db.Column(db.Text)
    original_pdf_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Resume {self.id}: {self.filename}>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "structured_data": self.structured_data,
            "extracted_text": self.extracted_text[:500] + "..." if self.extracted_text and len(self.extracted_text) > 500 else self.extracted_text,
            "has_layout_html": bool(self.layout_html),
            "original_pdf_path": self.original_pdf_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "structured_data": self.structured_data,
            "extracted_text": self.extracted_text,
            "layout_html": self.layout_html,
            "original_pdf_path": self.original_pdf_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def sections(self) -> List[str]:
        if not self.structured_data:
            return []
        return list(self.structured_data.keys())
    
    @property
    def name(self) -> str:
        if self.structured_data and 'name' in self.structured_data:
            name_data = self.structured_data.get('name', {})
            if isinstance(name_data, dict):
                return name_data.get('raw_text', '')
            return str(name_data)
        return ''
    
    @property
    def email(self) -> str:
        if self.structured_data and 'email' in self.structured_data:
            email_data = self.structured_data.get('email', {})
            if isinstance(email_data, dict):
                return email_data.get('raw_text', '')
            return str(email_data)
        return ''


def init_database(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")


def save_resume(
    filename: str,
    structured_data: Dict[str, Any],
    extracted_text: str = "",
    layout_html: str = "",
    original_pdf_path: str = ""
) -> Resume:
    resume = Resume(
        filename=filename,
        structured_data=structured_data,
        extracted_text=extracted_text,
        layout_html=layout_html,
        original_pdf_path=original_pdf_path
    )
    db.session.add(resume)
    db.session.commit()
    logger.info(f"Resume saved: {filename} (ID: {resume.id})")
    return resume


def get_resume(resume_id: int) -> Optional[Resume]:
    return Resume.query.get(resume_id)


def get_all_resumes() -> List[Resume]:
    return Resume.query.order_by(Resume.created_at.desc()).all()


def delete_resume(resume_id: int) -> bool:
    resume = Resume.query.get(resume_id)
    if resume:
        db.session.delete(resume)
        db.session.commit()
        logger.info(f"Resume deleted: ID {resume_id}")
        return True
    return False


def update_resume(
    resume_id: int,
    structured_data: Dict[str, Any] = None,
    layout_html: str = None
) -> Optional[Resume]:
    resume = Resume.query.get(resume_id)
    if not resume:
        return None
    
    if structured_data is not None:
        resume.structured_data = structured_data
    if layout_html is not None:
        resume.layout_html = layout_html
    
    resume.updated_at = datetime.utcnow()
    db.session.commit()
    logger.info(f"Resume updated: ID {resume_id}")
    return resume


def search_resumes(query: str) -> List[Resume]:
    return Resume.query.filter(
        db.or_(
            Resume.filename.ilike(f"%{query}%"),
            Resume.extracted_text.ilike(f"%{query}%")
        )
    ).order_by(Resume.created_at.desc()).all()


if __name__ == "__main__":

    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resumes.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    init_database(app)
    
  
    test_data = {
        "name": {"raw_text": "John Doe", "confidence": 0.9},
        "email": {"raw_text": "john@example.com", "confidence": 0.95},
        "skills": {"raw_text": "Python, JavaScript", "confidence": 0.85}
    }
    
  
    resume = save_resume(
        filename="test_resume.pdf",
        structured_data=test_data,
        extracted_text="Test resume text",
        original_pdf_path="uploads/test_resume.pdf"
    )
    
    print(f"Created resume: {resume.id}")

    retrieved = get_resume(resume.id)
    print(f"Retrieved: {retrieved.filename}")

    all_resumes = get_all_resumes()
    print(f"Total resumes: {len(all_resumes)}")

    delete_resume(resume.id)
    print("Deleted test resume")
