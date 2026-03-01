import os
import uuid
import json
import random
import csv
import requests
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gtts import gTTS
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# Database & Auth
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-aiva-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aiva.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")

if not api_key:
    print("WARNING: GEMINI_API_KEY is not set in .env")

# --- EMAIL HELPER ---
def send_interview_invite(to_email, candidate_name, role, company_name, interview_url):
    """Sends an interview invite email via Gmail SMTP."""
    if not EMAIL_USER or not EMAIL_PASS or EMAIL_USER == "your_gmail@gmail.com":
        print("[EMAIL] Skipped - Gmail credentials not configured in .env")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Interview Invitation: {role} at {company_name}"
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        
        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; background: #0f1117; color: #e2e8f0; padding: 30px;">
        <div style="max-width: 600px; margin: auto; background: #1e2433; padding: 30px; border-radius: 16px; border: 1px solid #334155;">
            <h2 style="color: #60a5fa;">🤖 AIVA Interview Invitation</h2>
            <p>Hi <strong>{candidate_name}</strong>,</p>
            <p>You have been invited to complete a <strong>technical AI interview</strong> for the role of:</p>
            <h3 style="color: #34d399;">🎯 {role} at {company_name}</h3>
            <p>Click the button below to start your interview. Make sure you have a working microphone and a stable internet connection.</p>
            <a href="{interview_url}" style="display: inline-block; background: #3b82f6; color: white; padding: 14px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 20px 0;">🚀 Start My Interview</a>
            <p style="color: #94a3b8; font-size: 0.85em;">Or copy this link: <a href="{interview_url}" style="color: #60a5fa;">{interview_url}</a></p>
            <hr style="border-color: #334155;">
            <p style="color: #64748b; font-size: 0.8em;">Powered by AIVA - AI Interview System. This link is unique to you.</p>
        </div></body></html>"""
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        
        print(f"[EMAIL] Invite sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# Initialize Gemini
genai.configure(api_key=api_key)
generation_config = genai.types.GenerationConfig(temperature=0.7)

# Load Dataset
DATASET_QUESTIONS = []
try:
    with open('coding_interview_question_bank.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            DATASET_QUESTIONS.append({
                'question': row.get('question', ''),
                'category': row.get('category', ''),
                'difficulty': row.get('difficulty', '')
            })
except Exception as e:
    print(f"Error loading dataset: {e}")

# --- DATABASE MODELS ---

class Company(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)

    # Relationships
    interviews = db.relationship('Interview', backref='company', lazy=True)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    candidate_name = db.Column(db.String(100), nullable=False)
    candidate_email = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="Pending") # Pending, In Progress, Completed
    result_report = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return Company.query.get(int(user_id))

# --- MASTER PROMPT LOGIC ---

def get_master_prompt(language="English", role="Candidate", selected_questions=None):
    if selected_questions is None:
        selected_questions = []
        
    return f"""You are AIVA (Artificial Interview & Validation Assistant) —
a highly professional AI Interview Agent Avatar designed to conduct real-world job interviews.

You simulate a human technical interviewer using AI/ML adaptive intelligence.

You NEVER break character.
**CRITICAL LANGUAGE INSTRUCTION**: You MUST speak natively and ONLY in {language}. 
If {language} is Hindi or Gujarati, you MUST reply exclusively in that native script (e.g. નમસ્તે for Gujarati, नमस्ते for Hindi). DO NOT use English letters to write the language. DO NOT reply in English.

🔹 CORE OBJECTIVE
Your task is to:
Conduct an interview for the role of: {role}.
Start from basic → advanced.
Adapt difficulty using AI/ML-style evaluation.
CRITICAL: You MUST analyze the candidate's answer before asking the next question. 
If the answer is incorrect, ask a follow-up or provide a hint. 
If the answer is correct, provide brief feedback and then proceed to the next technical question from the provided list.

🔹 INTERVIEW START FLOW (MANDATORY)
Begin ONLY by warmly welcoming the candidate and asking them to confirm their proficiency level (Fresher / Junior / Mid / Senior) before you begin technical questions.
DO NOT output markdown bolding (**text**) or asterisks for actions. Output pure text only to ensure seamless Text-To-Speech matching.
Speak entirely in {language}.

🔹 INTERVIEW RULES
You MUST base your technical evaluation on the following questions if they are relevant to the role:
{chr(10).join(f"- {q}" for q in selected_questions) if selected_questions else "No specific dataset questions matching this role were found. Please generate your own highly technical and role-specific questions."}

If the above questions are NOT relevant to the role of {role}, you SHOULD generate your own role-specific technical questions.
Ask ONE question at a time. Wait for user answer before continuing.
After the user answers, ANALYZE the response first. 
If the candidate answers a question well, move to the next dataset question only AFTER providing brief feedback.
If the candidate's answer is weak or partial, ask a related sub-question or clarifying question to test deeper knowledge.
Never reveal internal scoring or logic.
Do NOT give full answers unless user explicitly asks.
Use professional, calm, encouraging tone.

🔹 CODING CHALLENGE REQUIREMENT (CRITICAL)
AT LEAST 50% of your questions MUST be hands-on coding tasks where you ask the candidate to write actual code. Examples:
- "Write a Python function to reverse a linked list"
- "Implement binary search and explain its time complexity"
- "Write a SQL query to find the top 3 highest-paid employees per department"
- "Solve: Given an array, find the two numbers that sum to a target value"
When asking a coding question, tell the candidate they can type their code in the Code Editor panel on the right side of the screen, then click 'Send Code' to submit it.
When you receive code from the candidate (it will be in markdown code blocks), evaluate it thoroughly: check for correctness, efficiency, edge cases, and style.

🔹 FEEDBACK STYLE
After each answer: Give brief feedback only, Do NOT reveal full solution, Move to next adaptive question.

🔹 INTERVIEW COMPLETION (MANDATORY)
At the end, provide:
FINAL EVALUATION REPORT
Overall Skill Level: Beginner / Intermediate / Advanced
Technical Strengths
Weak Areas
Soft Skills Analysis: (Score /10 for Communication, Confidence, and Tone)
Code Quality Assessment: (Score /10 for correctness, efficiency, and readability)
Improvement Suggestions
Hiring Recommendation: Strong Hire / Consider / Not Ready Yet
"""

# Store chat sessions in memory (for MVP; normally use DB or Redis)
chat_sessions = {}

def get_or_create_chat(session_id, language="English", role="Candidate"):
    if session_id not in chat_sessions:
        # Filter questions by role/category (broader matching)
        role_keywords = role.lower().split()
        relevant_pool = [q['question'] for q in DATASET_QUESTIONS if 
                         role.lower() in q['category'].lower() or 
                         role.lower() in q['question'].lower() or
                         any(word in q['category'].lower() for word in role_keywords if len(word) > 2)]
        
        # If the pool is too small, don't force unrelated questions
        if len(relevant_pool) >= 3:
            selected_questions = random.sample(relevant_pool, min(5, len(relevant_pool)))
        else:
            # Provide an empty list so the prompt handles it by generating role-specific questions
            selected_questions = []
        
        sys_prompt = get_master_prompt(language, role, selected_questions)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=sys_prompt,
            generation_config=generation_config
        )
        chat_sessions[session_id] = {
            "chat": model.start_chat(history=[]),
            "questions": selected_questions
        }
    return chat_sessions[session_id]

# --- COMPANY AUTH & DASHBOARD ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Company.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check username and password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        company_name = request.form.get('company_name')

        if Company.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        new_user = Company(
            username=username, 
            company_name=company_name, 
            password_hash=generate_password_hash(password, method='scrypt')
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created! Please log in.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        candidate_name = request.form.get('candidate_name')
        candidate_email = request.form.get('candidate_email')
        role = request.form.get('role')
        
        new_interview = Interview(
            company_id=current_user.id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            role=role
        )
        db.session.add(new_interview)
        db.session.commit()
        
        # Auto-send email invite
        interview_url = url_for('interview_page', token=new_interview.token, _external=True)
        email_sent = send_interview_invite(
            to_email=candidate_email,
            candidate_name=candidate_name,
            role=role,
            company_name=current_user.company_name,
            interview_url=interview_url
        )
        
        if email_sent:
            flash(f'Interview link generated & invite sent to {candidate_email}! <br><a href="{interview_url}" style="font-weight:bold; text-decoration:underline;">Open Interview</a>')
        else:
            flash(f'<b>Interview link generated:</b> <br><a href="{interview_url}" target="_blank" style="font-weight:bold; text-decoration:underline; font-size: 1.1em;">{interview_url}</a> <br><br><small>⚠️ Auto-email skipped (Configure Gmail App Password in Google Settings to enable emails)</small>')
        return redirect(url_for('dashboard'))
        
    interviews = Interview.query.filter_by(company_id=current_user.id).order_by(Interview.id.desc()).all()
    
    # Analytics Data
    total_interviews = len(interviews)
    completed_interviews = sum(1 for i in interviews if i.status == 'Completed')
    pending_interviews = sum(1 for i in interviews if i.status == 'Pending' or i.status == 'In Progress')
    
    return render_template(
        'dashboard.html', 
        interviews=interviews,
        total_interviews=total_interviews,
        completed_interviews=completed_interviews,
        pending_interviews=pending_interviews
    )


# --- CANDIDATE INTERVIEW ROUTES ---

@app.route('/interview/<token>')
def interview_page(token):
    interview = Interview.query.filter_by(token=token).first_or_404()
    
    # If already completed or in progress, logic could easily be added here
    if interview.status == "Pending":
        interview.status = "In Progress"
        db.session.commit()
        
    return render_template('index.html', interview=interview)

@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.json
    user_message = data.get("message", "")
    session_id = data.get("session_id", "default")
    language = data.get("language", "English")
    role = data.get("role", "Candidate")
    
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Reset chat if it's a fresh start from the UI
    if user_message.startswith("[SYSTEM COMMAND]"):
        if session_id in chat_sessions:
            del chat_sessions[session_id]

    session_data = get_or_create_chat(session_id, language, role)
    chat = session_data["chat"]
    
    try:
        # Try real Gemini API first
        response = chat.send_message(user_message)
        return jsonify({
            "response": response.text,
            "status": "success",
            "mocked": False
        })
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return jsonify({"error": f"Gemini API Error: {str(e)}"}), 500
@app.route("/api/reset", methods=["POST"])
def reset_chat():
    data = request.json
    session_id = data.get("session_id", "default")
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return jsonify({"status": "success", "message": "Chat reset"})

@app.route("/api/generate_report", methods=["POST"])
def generate_report():
    data = request.json
    session_id = data.get("session_id", "default")
    token = data.get("token")
    
    interview = Interview.query.filter_by(token=token).first()
    if not interview:
        return jsonify({"error": "Invalid interview token"}), 404
        
    if session_id not in chat_sessions:
        return jsonify({"error": "No chat session found"}), 404
        
    session_data = chat_sessions[session_id]
    
    if "chat" not in session_data:
        return jsonify({"error": "No active chat found. Please restart the interview."}), 400
    
    chat = session_data["chat"]
    history = chat.history
    
    # Format history for prompt
    convo_text = ""
    for msg in history:
        convo_text += f"{msg.role.upper()}: {msg.parts[0].text}\n"
        
    report_prompt = f"""
    Based on the following interview transcript, please generate a concise, professional Evaluation Report for the candidate named '{interview.candidate_name}' interviewing for '{interview.role}'.
    Format exactly like this strictly using text/markdown without any preamble:
    
    **Overall Skill Level**: [Beginner / Intermediate / Advanced]
    **Technical Strengths**: [List 1-2 points]
    **Weak Areas**: [List 1-2 points]
    **Soft Skills Analysis**: [Score /10 for Communication, Confidence, Tone]
    **Improvement Suggestions**: [List 1-2 points]
    **Hiring Recommendation**: [Strong Hire / Consider / Not Ready Yet]
    
    TRANSCRIPT:
    {convo_text}
    """
    
    try:
        report_model = genai.GenerativeModel(model_name="gemini-2.0-flash", generation_config=generation_config)
        result = report_model.generate_content(report_prompt)
        report_text = result.text.strip()
        
        # Save to DB
        interview.result_report = report_text
        interview.status = "Completed"
        db.session.commit()
        
        return jsonify({"status": "success", "report": report_text})
        
    except Exception as e:
        print(f"Failed to generate report: {e}")
        error_msg = str(e)
        # If it's a quota error, return a friendly message
        if "429" in error_msg.lower() or "exhausted" in error_msg.lower():
            return jsonify({"error": "Gemini API Quota Reached. Please try again in a few minutes or use Mock Mode."}), 500
        return jsonify({"error": f"Failed to generate report: {error_msg}"}), 500

@app.route("/api/speak", methods=["POST"])
def speak_api():
    data = request.json
    text = data.get("text", "")
    language = data.get("language", "English")

    if not text:
        return jsonify({"error": "Empty text"}), 400

    # Map the dropdown language selection to gTTS language codes
    lang_code = 'en'
    if language == "Hindi":
        lang_code = 'hi'
    elif language == "Gujarati":
        lang_code = 'gu'
        
    # Strip markdown specific characters before text-to-speech
    clean_text = text.replace('*', '').replace('`', '').replace('#', '').strip()

    try:
        # Generate Audio
        tts = gTTS(text=clean_text, lang=lang_code, slow=False)
        
        # Save to BytesIO in memory rather than generating files on disk continuously
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        return send_file(fp, mimetype="audio/mpeg", as_attachment=False)
    except Exception as e:
        print(f"gTTS Audio Generation Error: {e}")
        return jsonify({"error": "Audio generation failed"}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5001)
