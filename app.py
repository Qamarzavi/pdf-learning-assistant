import os
import re
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import PyPDF2
from google import genai
import os
from dotenv import load_dotenv
from io import BytesIO

# Import database module
from database import db, User, PDFDocument, QuizAttempt, Flashcard, Note, ChatMessage, init_db

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdf_assistant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create uploads folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
init_db(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    print("WARNING: GEMINI_API_KEY not found. AI features will not work.")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def extract_text_from_pdf(pdf_path):
    """Extract text from uploaded PDF"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def generate_summary(text):
    """Generate summary using Gemini API"""
    if not client:
        return "AI service not configured. Please check your GEMINI_API_KEY in .env file."
    
    if not text or len(text) < 100:
        return "Text too short for meaningful summary. Please upload a PDF with more content."
    
    try:
        truncated_text = text[:30000]  # Gemini can handle more text
        
        prompt = f"""Please provide a comprehensive summary of the following document in 3-5 well-structured paragraphs. 
Focus on the main ideas, key arguments, and important conclusions.

Document content:
{truncated_text}

Summary:"""
        
        response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
        )
        return response.text if response.text else "Unable to generate summary."
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Unable to generate summary. Error: {str(e)}"

def extract_keywords(text):
    """Extract keywords using Gemini API"""
    if not client:
        return "AI service not configured."
    
    if not text:
        return "No keywords available."
    
    try:
        truncated_text = text[:20000]
        
        prompt = f"""Extract 15-20 important keywords or key phrases from the following document. 
Return them as a comma-separated list. Focus on technical terms, concepts, and important topics.

Document content:
{truncated_text}

Keywords (comma-separated list only):"""
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )
        keywords = response.text if response.text else "Unable to extract keywords."
        return keywords
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return f"Unable to extract keywords. Error: {str(e)}"

def generate_questions(text):
    """Generate important questions using Gemini API"""
    if not client:
        return "AI service not configured."
    
    if not text:
        return "No questions available."
    
    try:
        truncated_text = text[:25000]
        
        prompt = f"""Based on the following document, generate 5 important study questions that would help someone understand the content better. 
Make the questions thought-provoking and focused on key concepts.

Format each question on a new line with a number (1. 2. 3. etc.)

Document content:
{truncated_text}

Important Study Questions:"""
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )
        questions = response.text if response.text else "Unable to generate questions."
        return questions
    except Exception as e:
        print(f"Error generating questions: {e}")
        return f"Unable to generate questions. Error: {str(e)}"

def generate_quiz(text):
    """Generate quiz using Gemini API"""
    if not client:
        return json.dumps([{"question": "AI service not configured", "options": ["N/A"], "correct_answer": "N/A"}])
    
    if not text:
        return json.dumps([{"question": "No content available", "options": ["N/A"], "correct_answer": "N/A"}])
    
    try:
        truncated_text = text[:25000]
        
        prompt = f"""Based on the following document, create a 5-question multiple choice quiz.

Return ONLY valid JSON array where each question object has EXACTLY this format:
[
    {{
        "question": "What is...?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "A"
    }}
]

Important: 
- The correct_answer must be exactly "A", "B", "C", or "D"
- There must be exactly 4 options for each question
- Return ONLY the JSON array, no other text

Document content:
{truncated_text}

Quiz JSON:"""
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )
        quiz_text = response.text if response.text else "[]"
        
        # Clean the response to extract JSON
        quiz_text = quiz_text.strip()
        if quiz_text.startswith('```json'):
            quiz_text = quiz_text[7:]
        if quiz_text.startswith('```'):
            quiz_text = quiz_text[3:]
        if quiz_text.endswith('```'):
            quiz_text = quiz_text[:-3]
        quiz_text = quiz_text.strip()
        
        # Validate JSON
        try:
            quiz_json = json.loads(quiz_text)
            if isinstance(quiz_json, list):
                return json.dumps(quiz_json)
            else:
                return json.dumps([quiz_json])
        except json.JSONDecodeError:
            return json.dumps([{
                "question": "Quiz generation partially failed",
                "options": ["Please try again", "", "", ""],
                "correct_answer": "A"
            }])
            
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return json.dumps([{
            "question": f"Error generating quiz: {str(e)}",
            "options": ["N/A", "", "", ""],
            "correct_answer": "A"
        }])

def generate_pdf_report(summary, keywords, questions, quiz, filename):
    """Generate PDF report"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib import colors
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#4A90E2'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph("PDF Learning Assistant Report", title_style))
        story.append(Paragraph(f"<b>Original File:</b> {filename}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary
        story.append(Paragraph("<b>📝 Summary</b>", styles['Heading2']))
        story.append(Paragraph(summary.replace('\n', '<br/>') if summary else "No summary", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Keywords
        story.append(Paragraph("<b>🔑 Keywords</b>", styles['Heading2']))
        story.append(Paragraph(keywords.replace('\n', '<br/>') if keywords else "No keywords", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Questions
        story.append(Paragraph("<b>❓ Important Questions</b>", styles['Heading2']))
        story.append(Paragraph(questions.replace('\n', '<br/>') if questions else "No questions", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Quiz
        story.append(Paragraph("<b>📋 Quiz</b>", styles['Heading2']))
        try:
            quiz_data = json.loads(quiz) if quiz else []
            for i, q in enumerate(quiz_data, 1):
                story.append(Paragraph(f"<b>Q{i}: {q.get('question', 'N/A')}</b>", styles['Normal']))
                for opt in q.get('options', []):
                    if opt:
                        story.append(Paragraph(f"• {opt}", styles['Normal']))
                story.append(Paragraph(f"<b>Correct Answer: {q.get('correct_answer', 'N/A')}</b>", styles['Normal']))
                story.append(Spacer(1, 10))
        except:
            story.append(Paragraph(str(quiz), styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

# ==================== ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Input validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        if not email or '@' not in email or '.' not in email:
            errors.append("Please enter a valid email address")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        # Check existing user
        if User.query.filter_by(username=username).first():
            errors.append("Username already exists")
        if User.query.filter_by(email=email).first():
            errors.append("Email already registered")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Create user
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    pdfs = PDFDocument.query.filter_by(user_id=current_user.id).order_by(PDFDocument.upload_date.desc()).all()
    return render_template('dashboard.html', pdfs=pdfs)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('No file selected', 'error')
            return render_template('upload.html')
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return render_template('upload.html')
        
        if not allowed_file(file.filename):
            flash('Please upload a PDF file only (.pdf extension required)', 'error')
            return render_template('upload.html')
        
        try:
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            saved_filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
            file.save(filepath)
            
            # Extract text
            text = extract_text_from_pdf(filepath)
            
            if not text or len(text.strip()) < 50:
                flash('Could not extract sufficient text from PDF. Make sure it contains selectable text (not scanned images).', 'error')
                os.remove(filepath)
                return render_template('upload.html')
            
            # Generate content
            flash('PDF uploaded successfully! Generating AI-powered content...', 'info')
            
            summary = generate_summary(text)
            keywords = extract_keywords(text)
            questions = generate_questions(text)
            quiz = generate_quiz(text)
            
            # Save to database
            pdf_doc = PDFDocument(
                filename=saved_filename,
                original_filename=filename,
                user_id=current_user.id,
                summary=summary,
                keywords=keywords,
                questions=questions,
                quiz=quiz,
                content_text=text[:1000],
                processing_status='completed'
            )
            db.session.add(pdf_doc)
            db.session.commit()
            
            flash('PDF processed successfully! View your results below.', 'success')
            return redirect(url_for('view_pdf', pdf_id=pdf_doc.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing PDF: {str(e)}', 'error')
            if os.path.exists(filepath):
                os.remove(filepath)
            return render_template('upload.html')
    
    return render_template('upload.html')

@app.route('/view/<int:pdf_id>')
@login_required
def view_pdf(pdf_id):
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    # Ensure user owns this PDF
    if pdf.user_id != current_user.id:
        flash('Access denied. You can only view your own documents.', 'error')
        return redirect(url_for('dashboard'))
    
    # Update last accessed time
    pdf.last_accessed = datetime.utcnow()
    db.session.commit()
    
    # Parse quiz JSON
    quiz_data = []
    try:
        if pdf.quiz:
            quiz_data = json.loads(pdf.quiz)
    except (json.JSONDecodeError, TypeError):
        quiz_data = []
    
    return render_template('view.html', pdf=pdf, quiz_data=quiz_data)

@app.route('/delete/<int:pdf_id>')
@login_required
def delete_pdf(pdf_id):
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Delete file from storage
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    db.session.delete(pdf)
    db.session.commit()
    
    flash('PDF deleted successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/download_report/<int:pdf_id>')
@login_required
def download_report(pdf_id):
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    pdf_buffer = generate_pdf_report(pdf.summary, pdf.keywords, pdf.questions, pdf.quiz, pdf.original_filename)
    
    if pdf_buffer:
        return send_file(
            pdf_buffer,
            download_name=f'report_{pdf.original_filename.replace(".pdf", "")}.pdf',
            as_attachment=True,
            mimetype='application/pdf'
        )
    else:
        flash('Error generating PDF report. Please try again.', 'error')
        return redirect(url_for('view_pdf', pdf_id=pdf_id))

    # ==================== NEW: FLASHCARD GENERATION ====================

def generate_flashcards(text):
    """Generate flashcards using Gemini API"""
    if not client:
        return json.dumps([])
    
    if not text:
        return json.dumps([])
    
    try:
        truncated_text = text[:25000]
        
        prompt = f"""Based on the following document, create 10 flashcards for studying.
Each flashcard should have a "front" (question/term) and "back" (answer/definition).

Return ONLY valid JSON array:
[
    {{"front": "What is X?", "back": "X is...", "difficulty": "easy"}},
    ...
]

Difficulty must be: "easy", "medium", or "hard"

Document content:
{truncated_text}

Flashcards JSON:"""
        
        response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt
                )
        flashcards_text = response.text if response.text else "[]"
        
        # Clean JSON
        flashcards_text = flashcards_text.strip()
        if flashcards_text.startswith('```json'):
            flashcards_text = flashcards_text[7:]
        if flashcards_text.startswith('```'):
            flashcards_text = flashcards_text[3:]
        if flashcards_text.endswith('```'):
            flashcards_text = flashcards_text[:-3]
        flashcards_text = flashcards_text.strip()
        
        try:
            flashcards_json = json.loads(flashcards_text)
            return json.dumps(flashcards_json)
        except:
            return json.dumps([])
            
    except Exception as e:
        print(f"Error generating flashcards: {e}")
        return json.dumps([])

# ==================== NEW: CHAT WITH PDF ====================

def chat_with_pdf(pdf_text, user_message, chat_history):
    """Chat with PDF content using Gemini API"""
    if not client:
        return "AI service not configured."
    
    try:
        # Build conversation context
        context = f"""You are a helpful AI assistant. Answer questions based on this document content:
        
Document: {pdf_text[:20000]}

Previous conversation:
{chat_history}

User: {user_message}

Assistant:"""
        
        response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=context
                )
        return response.text if response.text else "I couldn't generate a response."
        
    except Exception as e:
        return f"Error: {str(e)}"

# ==================== NEW ROUTES ====================

@app.route('/api/stats')
@login_required
def get_stats():
    """API endpoint for dashboard statistics"""
    stats = {
        'total_pdfs': PDFDocument.query.filter_by(user_id=current_user.id).count(),
        'total_summaries': PDFDocument.query.filter(
            PDFDocument.user_id == current_user.id,
            PDFDocument.summary.isnot(None)
        ).count(),
        'total_quiz_attempts': QuizAttempt.query.filter_by(user_id=current_user.id).count(),
        'average_quiz_score': current_user.get_average_quiz_score()
    }
    return jsonify(stats)

@app.route('/api/recent_pdfs')
@login_required
def get_recent_pdfs():
    """API endpoint for recent PDFs"""
    pdfs = PDFDocument.query.filter_by(user_id=current_user.id)\
        .order_by(PDFDocument.upload_date.desc())\
        .limit(5)\
        .all()
    
    return jsonify([pdf.to_dict() for pdf in pdfs])

@app.route('/submit_quiz/<int:pdf_id>', methods=['POST'])
@login_required
def submit_quiz(pdf_id):
    """Submit quiz answers and calculate score"""
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    user_answers = data.get('answers', {})
    
    # Get correct answers from stored quiz
    try:
        quiz_data = json.loads(pdf.quiz)
    except:
        return jsonify({'error': 'Quiz data not found'}), 400
    
    total_questions = len(quiz_data)
    correct_count = 0
    
    for i, question in enumerate(quiz_data):
        user_answer = user_answers.get(str(i))
        if user_answer and user_answer == question.get('correct_answer'):
            correct_count += 1
    
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    # Save quiz attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        pdf_id=pdf_id,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_count,
        answers=json.dumps(user_answers)
    )
    db.session.add(attempt)
    db.session.commit()
    
    return jsonify({
        'score': score,
        'correct': correct_count,
        'total': total_questions,
        'message': f'You scored {score:.1f}% ({correct_count}/{total_questions})'
    })

@app.route('/api/flashcards/<int:pdf_id>')
@login_required
def get_flashcards(pdf_id):
    """Get flashcards for a PDF"""
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Check if flashcards exist in database
    flashcards = Flashcard.query.filter_by(pdf_id=pdf_id, user_id=current_user.id).all()
    
    if not flashcards:
        # Generate new flashcards
        if pdf.flashcards:
            try:
                flashcards_data = json.loads(pdf.flashcards)
                # Save to Flashcard model
                for fc in flashcards_data:
                    flashcard = Flashcard(
                        user_id=current_user.id,
                        pdf_id=pdf_id,
                        front=fc.get('front', ''),
                        back=fc.get('back', ''),
                        difficulty=fc.get('difficulty', 'medium')
                    )
                    db.session.add(flashcard)
                db.session.commit()
                flashcards = Flashcard.query.filter_by(pdf_id=pdf_id, user_id=current_user.id).all()
            except:
                pass
    
    return jsonify([{
        'id': f.id,
        'front': f.front,
        'back': f.back,
        'difficulty': f.difficulty,
        'review_count': f.review_count
    } for f in flashcards])

@app.route('/api/flashcards/review/<int:flashcard_id>', methods=['POST'])
@login_required
def review_flashcard(flashcard_id):
    """Mark flashcard as reviewed"""
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    
    if flashcard.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    flashcard.review_count += 1
    flashcard.last_reviewed = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'review_count': flashcard.review_count})

@app.route('/api/notes/<int:pdf_id>', methods=['GET', 'POST'])
@login_required
def manage_notes(pdf_id):
    """Get or create notes for a PDF"""
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        notes = Note.query.filter_by(pdf_id=pdf_id, user_id=current_user.id)\
            .order_by(Note.created_at.desc()).all()
        
        return jsonify([{
            'id': n.id,
            'content': n.content,
            'color': n.color,
            'page_number': n.page_number,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': n.updated_at.strftime('%Y-%m-%d %H:%M')
        } for n in notes])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        note = Note(
            user_id=current_user.id,
            pdf_id=pdf_id,
            content=data.get('content', ''),
            color=data.get('color', 'yellow'),
            page_number=data.get('page_number')
        )
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'note': {
                'id': note.id,
                'content': note.content,
                'color': note.color,
                'created_at': note.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

@app.route('/api/notes/delete/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    """Delete a note"""
    note = Note.query.get_or_404(note_id)
    
    if note.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    db.session.delete(note)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/chat/<int:pdf_id>', methods=['POST'])
@login_required
def chat_with_pdf_route(pdf_id):
    """Chat with PDF content"""
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Get chat history
    chat_history = ChatMessage.query.filter_by(
        pdf_id=pdf_id, 
        user_id=current_user.id
    ).order_by(ChatMessage.timestamp).limit(10).all()
    
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])
    
    # Save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        pdf_id=pdf_id,
        role='user',
        content=user_message
    )
    db.session.add(user_msg)
    
    # Get AI response
    pdf_text = pdf.content_text if pdf.content_text else ""
    ai_response = chat_with_pdf(pdf_text, user_message, history_text)
    
    # Save AI response
    ai_msg = ChatMessage(
        user_id=current_user.id,
        pdf_id=pdf_id,
        role='assistant',
        content=ai_response
    )
    db.session.add(ai_msg)
    db.session.commit()
    
    return jsonify({
        'response': ai_response,
        'timestamp': datetime.utcnow().strftime('%H:%M')
    })

@app.route('/api/chat/history/<int:pdf_id>')
@login_required
def get_chat_history(pdf_id):
    """Get chat history for a PDF"""
    pdf = PDFDocument.query.get_or_404(pdf_id)
    
    if pdf.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    messages = ChatMessage.query.filter_by(
        pdf_id=pdf_id,
        user_id=current_user.id
    ).order_by(ChatMessage.timestamp).all()
    
    return jsonify([{
        'role': msg.role,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%H:%M')
    } for msg in messages])

# Update the upload route to also generate flashcards
# Find your existing upload route and add this line after the quiz generation:
# flashcards = generate_flashcards(text)
# And update the PDFDocument creation to include flashcards=flashcards

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html', error="Internal server error. Please try again later."), 500

@app.errorhandler(413)
def too_large(error):
    flash('File is too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('upload'))

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("\n" + "="*60)
    print("📚 PDF Learning Assistant is running!")
    print("🌐 Open: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)