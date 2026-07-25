"""
Database configuration and models for PDF Learning Assistant.
Uses SQLAlchemy with SQLite for data storage.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# ==================== USER MODEL ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    pdfs = db.relationship('PDFDocument', backref='owner', lazy='dynamic', 
                          cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    flashcards = db.relationship('Flashcard', backref='user', lazy='dynamic',
                                cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='user', lazy='dynamic',
                           cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def get_pdf_count(self):
        return self.pdfs.count()
    
    def get_average_quiz_score(self):
        attempts = self.quiz_attempts.all()
        if not attempts:
            return 0
        total = sum(a.score for a in attempts)
        return round(total / len(attempts), 1)

# ==================== PDF DOCUMENT MODEL ====================

class PDFDocument(db.Model):
    __tablename__ = 'pdf_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.Integer)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), 
                       nullable=False, index=True)
    
    # AI Generated Content
    summary = db.Column(db.Text)
    keywords = db.Column(db.Text)
    questions = db.Column(db.Text)
    quiz = db.Column(db.Text)
    flashcards = db.Column(db.Text)  # JSON string of flashcards
    notes = db.Column(db.Text)       # User notes
    
    # Metadata
    page_count = db.Column(db.Integer)
    content_text = db.Column(db.Text)
    processing_status = db.Column(db.String(20), default='pending')
    
    # Relationships
    quiz_attempts = db.relationship('QuizAttempt', backref='pdf', lazy='dynamic',
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PDFDocument {self.original_filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'upload_date': self.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
            'has_summary': bool(self.summary),
            'has_keywords': bool(self.keywords),
            'has_questions': bool(self.questions),
            'has_quiz': bool(self.quiz),
            'processing_status': self.processing_status
        }

# ==================== QUIZ ATTEMPT MODEL ====================

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_documents.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Percentage score
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    attempt_date = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.Text)  # JSON string of user answers
    
    def __repr__(self):
        return f'<QuizAttempt {self.id} - Score: {self.score}%>'

# ==================== FLASHCARD MODEL ====================

class Flashcard(db.Model):
    __tablename__ = 'flashcards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_documents.id', ondelete='CASCADE'), nullable=False)
    front = db.Column(db.String(500), nullable=False)
    back = db.Column(db.String(1000), nullable=False)
    difficulty = db.Column(db.String(10), default='medium')  # easy, medium, hard
    review_count = db.Column(db.Integer, default=0)
    last_reviewed = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Flashcard {self.id}: {self.front[:30]}...>'

# ==================== NOTE MODEL ====================

class Note(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_documents.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    color = db.Column(db.String(20), default='yellow')  # yellow, green, blue, pink
    
    def __repr__(self):
        return f'<Note {self.id}>'

# ==================== AI CHAT HISTORY MODEL ====================

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_documents.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.id} - {self.role}>'

# ==================== DATABASE INITIALIZATION ====================

def init_db(app):
    """Initialize database with the Flask app."""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully!")

def get_db_stats(user_id):
    """Get statistics for a specific user."""
    stats = {
        'total_pdfs': PDFDocument.query.filter_by(user_id=user_id).count(),
        'total_summaries': PDFDocument.query.filter(
            PDFDocument.user_id == user_id,
            PDFDocument.summary.isnot(None)
        ).count(),
        'total_quiz_attempts': QuizAttempt.query.filter_by(user_id=user_id).count(),
        'average_quiz_score': User.query.get(user_id).get_average_quiz_score(),
        'total_flashcards': Flashcard.query.filter_by(user_id=user_id).count(),
        'total_notes': Note.query.filter_by(user_id=user_id).count()
    }
    return stats