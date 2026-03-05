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
from google import genai
from google.genai import types

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

def send_interview_report(to_email, candidate_name, role, company_name, report_content):
    """Sends the final evaluation report to the candidate."""
    if not EMAIL_USER or not EMAIL_PASS or EMAIL_USER == "your_gmail@gmail.com":
        print("[REPORT EMAIL] Skipped - Gmail credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Interview Result: {role} at {company_name}"
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        
        # Format the report content for HTML
        formatted_report = report_content.replace('\n', '<br>')
        
        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; background: #0f1117; color: #e2e8f0; padding: 30px;">
        <div style="max-width: 600px; margin: auto; background: #1e2433; padding: 30px; border-radius: 16px; border: 1px solid #334155;">
            <h2 style="color: #60a5fa;">📊 AIVA Interview Report</h2>
            <p>Hi <strong>{candidate_name}</strong>,</p>
            <p>Thank you for completing the technical interview for <strong>{role}</strong> at <strong>{company_name}</strong>.</p>
            <hr style="border-color: #334155;">
            <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; color: #cbd5e1; line-height: 1.6;">
                {formatted_report}
            </div>
            <hr style="border-color: #334155;">
            <p style="color: #64748b; font-size: 0.8em;">This report was generated by AIVA (Artificial Interview & Validation Assistant).</p>
        </div></body></html>"""
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        
        print(f"[REPORT EMAIL] Report sent to {to_email}")
        return True
    except Exception as e:
        print(f"[REPORT EMAIL ERROR] {e}")
        return False

# Initialize Gemini
client = genai.Client(api_key=api_key)
generation_config = types.GenerateContentConfig(
    temperature=0.7,
    top_p=0.95,
    top_k=40,
    max_output_tokens=8192,
)

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

    # Personality Training
    custom_instructions = db.Column(db.Text, nullable=True)

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

def get_master_prompt(language="English", role="Candidate", selected_questions=None, custom_instructions=None):
    if selected_questions is None:
        selected_questions = []
        
    return f"""You are AIVA Prime, a Senior Technical Interviewer and Global Architect conducting a high-stakes technical evaluation for the role of: {role}.
{f"MISSION CRITICAL INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

STRICT OPERATIONAL RULES (HUMAN-LOGIC v2.8):
1. ASK ONLY ONE QUESTION AT A TIME. This is an interactive chat.
2. OUTPUT PLAIN TEXT ONLY. No markdown, no bolding, no italics.
3. DEEP-BRANCHING & ADAPTIVE DRILLING:
   - YOU ARE NOT A SCRIPT. Do not just read from the technical bank.
   - If the candidate gives an answer, you MUST evaluate it and immediately generate a follow-up question that branches from their specific response.
   - Example: If they mention "Redux," drill into state management trade-offs even if it's not in the bank.
   - PUSH THEM: If they sound comfortable, push them to the absolute edge of their knowledge with "What if...?" and "Why...?" architectural scenarios.
4. SENTIMENT-AWARE CALIBRATION:
   - Support the candidate if they struggle; accelerate the complexity if they are confident.
5. CONTEXTUAL BRIDGING:
   - Every question must be a bridge from the previous interaction.
6. SPEAK EXACTLY IN THIS LANGUAGE: {language}.

INTERVIEW FLOW:
Phase 1 (Warmup): Welcome them warmly and state your name (AIVA).
Phase 2 (Adaptive Technical Drill): Use the CSV Bank as anchor points, but generate at least 2 dynamic follow-up questions for every 1 bank question.
Phase 3 (Close): provide a final "COMMAND CENTER REPORT" in plain text.

CORE TECHNICAL BANK (FOUNDATION ONLY - BRACH FREELY):
{chr(10).join(f"- {q}" for q in selected_questions) if selected_questions else f"Generate your own specialized senior-level questions for {role}."}
"""

# Store chat sessions in memory (for MVP; normally use DB or Redis)
chat_sessions = {}

def get_or_create_chat(session_id, language="English", role="Candidate", custom_instructions=None):
    if session_id not in chat_sessions:
        # Filter questions by role/category (Precision matching + Keyword fallbacks)
        role_keywords = [w.lower() for w in role.lower().split() if len(w) > 2]
        
        relevant_pool = []
        for q in DATASET_QUESTIONS:
            q_text = q['question'].lower()
            q_cat = q['category'].lower()
            
            # Direct Match
            if role.lower() in q_cat or role.lower() in q_text:
                relevant_pool.append(q['question'])
            # Keyword Match
            elif any(word in q_cat or word in q_text for word in role_keywords):
                relevant_pool.append(q['question'])
        
        # Ensure variety and take a good sample
        random.shuffle(relevant_pool)
        
        if len(relevant_pool) >= 1:
            selected_questions = relevant_pool[:6] # Take top 6 matched questions
        else:
            selected_questions = []

        
        sys_prompt = get_master_prompt(language, role, selected_questions, custom_instructions)
        config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            system_instruction=sys_prompt,
        )
        chat = client.chats.create(model="gemini-2.0-flash", config=config)
        chat_sessions[session_id] = {
            "chat": chat,
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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = Company.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check username and password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

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
        
        login_user(new_user, remember=True)
        flash('Account created and logged in!')
        return redirect(url_for('dashboard'))
        
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
        # Check if updating instructions
        if 'update_instructions' in request.form:
            current_user.custom_instructions = request.form.get('instructions')
            db.session.commit()
            flash('Company Personality Training successfully updated!')
            return redirect(url_for('dashboard'))

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
            flash(f'Interview link generated & invite sent to {candidate_email}! <br><div style="margin-top:10px; display:flex; gap:10px; align-items:center;"><a href="{interview_url}" style="font-weight:bold; text-decoration:underline; color:white;">Open Interview</a> <button onclick="copyLink(\'{interview_url}\')" style="background:rgba(255,255,255,0.2); border:none; color:white; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.8rem;"><i class="fas fa-copy"></i> Copy Link</button></div>')
        else:
            flash(f'<b>Interview link generated:</b> <br><div style="margin-top:10px; display:flex; gap:10px; align-items:center;"><a href="{interview_url}" target="_blank" style="font-weight:bold; text-decoration:underline; font-size: 1.1em; color:white;">{interview_url}</a> <button onclick="copyLink(\'{interview_url}\')" style="background:rgba(255,255,255,0.2); border:none; color:white; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:0.8rem;"><i class="fas fa-copy"></i> Copy</button></div> <br><small>⚠️ Auto-email skipped (Configure Gmail App Password in Google Settings to enable emails)</small>')
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

    # Get company instructions for this interview
    token = data.get("token")
    custom_instructions = None
    if token:
        interview = Interview.query.filter_by(token=token).first()
        if interview and interview.company:
            custom_instructions = interview.company.custom_instructions

    # Mock Mode Logic
    is_mock = data.get("mock", False)
    if is_mock:
        import time
        time.sleep(1.5) # Simulate thinking
        mock_responses = [
            "I see your point about distributed systems. How would you handle eventual consistency in that scenario?",
            "That's a valid architectural trade-off. Can you explain the Big O complexity of your proposed solution?",
            "I'm interested in how this would scale to 10M concurrent users. What load balancing strategy would you pick?",
            "Good point on concurrency. Don't worry about the exact syntax, just walk me through the logic of your locking mechanism.",
            "That sounds like a solid approach. Given that, how would you ensure zero-downtime deployments for this service?"
        ]
        return jsonify({
            "response": random.choice(mock_responses),
            "status": "success",
            "mocked": True
        })

    try:
        session_data = get_or_create_chat(session_id, language, role, custom_instructions)
        chat = session_data["chat"]
        
        # Try real Gemini API first
        response = chat.send_message(user_message)
        return jsonify({
            "response": response.text,
            "status": "success",
            "mocked": False
        })
    except Exception as e:
        error_msg = str(e)
        print(f"Chat API Error: {error_msg}")
        
        # Friendly handling for Quota/Rate Limit errors
        if "429" in error_msg or "quota" in error_msg.lower() or "exhausted" in error_msg.lower():
            return jsonify({
                "error": "Gemini API Quota Exceeded. You can switch to 'Mock Mode' in the setup screen to continue testing UI/UX.",
                "type": "quota"
            }), 429
            
        return jsonify({"error": f"Gemini API Error: {error_msg}"}), 500

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
    
    try:
        chat = session_data["chat"]
        history = chat.get_history()
    except AttributeError:
        # Fallback if the chat object exposes .history instead of get_history()
        history = getattr(session_data["chat"], "history", getattr(session_data["chat"], "_history", []))
    
    # Format history for prompt
    convo_text = ""
    for msg in history:
        convo_text += f"{msg.role.upper()}: {msg.parts[0].text}\n"
        
    report_prompt = f"""
    Based on the following interview transcript, please generate a detailed professional Evaluation Report for the candidate named '{interview.candidate_name}' interviewing for '{interview.role}'.
    
    **CRITICAL SELECTION RULE**: Evaluate if the candidate answered correctly and confidently for at least **60%** of the technical questions.
    - If accuracy >= 60%: Hiring Recommendation MUST be "Strong Hire" or "Selected".
    - If accuracy < 60%: Hiring Recommendation MUST be "Not Ready Yet" or "Not Selected".

    Format exactly like this strictly using text/markdown without any preamble:
    
    **Overall Skill Level**: [Beginner / Intermediate / Advanced]
    **Technical Strengths**: [List 2-3 points]
    **Weak Areas**: [List 2-3 points]
    **Technical Accuracy**: [X% score based on correctness of answers]
    **Soft Skills Analysis**: [Score /10 for Communication, Confidence, Tone]
    **Improvement Suggestions**: [List 2-3 points]
    **Hiring Recommendation**: [Selected / Not Selected]
    
    TRANSCRIPT:
    {convo_text}
    """
    
    try:
        result = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=report_prompt, 
            config=generation_config
        )
        report_text = result.text.strip()
        
        # Save to DB
        interview.result_report = report_text
        interview.status = "Completed"
        db.session.commit()
        
        # Auto-send report to candidate email
        if interview.candidate_email:
            send_interview_report(
                to_email=interview.candidate_email,
                candidate_name=interview.candidate_name,
                role=interview.role,
                company_name=interview.company.company_name,
                report_content=report_text
            )
        
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
