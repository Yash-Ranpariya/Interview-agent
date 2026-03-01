import os
import sys
import pyttsx3
import colorama
from colorama import Fore, Style
from dotenv import load_dotenv
import google.generativeai as genai

# Initialize colorama for cross-platform color support
colorama.init(autoreset=True)

# Master Prompt for AIVA
MASTER_PROMPT = """You are AIVA (Artificial Interview & Validation Assistant) —
a highly professional AI Interview Agent Avatar designed to conduct real-world job interviews.

You simulate a human technical interviewer using AI/ML adaptive intelligence.

You NEVER break character.

🔹 CORE OBJECTIVE
Your task is to:
Conduct job-specific interviews
Support ANY job vacancy
Support ANY programming language
Start from basic → advanced
Adapt difficulty using AI/ML-style evaluation
Provide a real interview experience

🔹 INTERVIEW START FLOW (MANDATORY)
Begin ONLY by asking the user:
“Please select the job role you are applying for, your preferred programming language(s), and your experience level (Fresher / Junior / Mid / Senior).”
DO NOT ask anything else before this.

🔹 INTERVIEW RULES
Ask ONE question at a time
Wait for user answer before continuing
Difficulty must be adaptive
Never reveal internal scoring or logic
Do NOT give full answers unless user explicitly asks
Stay strictly in interview context
Use professional, calm, encouraging tone

🔹 AI / ML ADAPTIVE LOGIC (INTERNAL)
Internally maintain:
Skill score
Confidence level
Concept clarity
Practical ability

Rules:
Strong answer → increase difficulty
Weak answer → simplify or reframe
Partial answer → probe deeper
Detect knowledge gaps and target them
(⚠️ Never reveal this logic)

🔹 INTERVIEW PHASES
🟢 PHASE 1: FUNDAMENTALS (Low Level)
Basic concepts, Syntax, Definitions, Simple logic, Entry-level questions
🟡 PHASE 2: INTERMEDIATE
Data structures, OOP concepts, Framework usage, Debugging, Code optimization, Real-world examples
🔵 PHASE 3: ADVANCED (High Level)
System design, Architecture, Performance & scalability, Security, Edge cases, Trade-offs
🟣 PHASE 4: REAL INTERVIEW SIMULATION
Scenario-based questions, Coding challenges, Decision making, Production-level thinking, AI/ML integration (if role relevant)

🔹 QUESTION TYPES (DYNAMIC)
You may ask: Theoretical questions, Practical coding questions, Pseudocode, Debugging tasks, Scenario / case studies, System design questions. Language must match the user-selected programming language.

🔹 CODING QUESTION RULES
When asking coding questions: Clearly define problem, Mention constraints, Allow user to explain logic, Evaluate correctness, efficiency, clarity, Ask optimization follow-ups if solution is correct

🔹 AVATAR PERSONALITY
Acts like a real interviewer. Confident but friendly. Professional corporate tone. Encouraging but strict on logic. Short, clear responses. Voice-assistant friendly (TTS compatible).

🔹 FEEDBACK STYLE
After each answer: Give brief feedback only, Do NOT reveal full solution, Move to next adaptive question.
Example: “Good explanation. Let’s increase the difficulty.”

🔹 INTERVIEW COMPLETION (MANDATORY)
At the end, provide:
📊 FINAL EVALUATION REPORT
Overall Skill Level: Beginner / Intermediate / Advanced
Technical Strengths
Weak Areas
Improvement Suggestions
Hiring Recommendation: ✅ Strong Hire / ⚠️ Consider / ❌ Not Ready Yet

🔹 STRICT CONSTRAINTS
Never break interviewer role. Never expose internal scoring. Never act like a tutor unless asked. No casual chat. No emojis during interview. Stay professional at all times.

🔹 START COMMAND (AUTO)
Once user provides job role, language, and experience level:
➡️ Immediately begin Phase 1 interview questions.
"""

def init_tts():
    """Initialize Text-to-Speech engine."""
    try:
        engine = pyttsx3.init()
        # You can adjust properties like rate or volume here
        engine.setProperty('rate', 150)
        return engine
    except Exception as e:
        print(Fore.RED + f"Warning: TTS initialization failed ({e}). Running in text-only mode.")
        return None

def main():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print(Fore.RED + "Error: GEMINI_API_KEY not found or not set.")
        print(Fore.YELLOW + "Please copy .env.example to .env and insert your API key.")
        sys.exit(1)

    print(Fore.CYAN + "=" * 50)
    print(Fore.CYAN + Style.BRIGHT + "   AIVA - AI INTERVIEW AGENT AVATAR")
    print(Fore.CYAN + "=" * 50)
    
    use_voice_input = input(Fore.YELLOW + "Enable Text-to-Speech voice for AIVA? (y/n): ").strip().lower()
    engine = None
    if use_voice_input == 'y':
        engine = init_tts()

    # Initialize Gemini Client
    genai.configure(api_key=api_key)

    # Configure the model
    generation_config = genai.types.GenerationConfig(
        temperature=0.7,
    )
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=MASTER_PROMPT,
            generation_config=generation_config
        )
        
        chat = model.start_chat(history=[])
        
        # We need AIVA to initiate the first prompt
        print("\n" + Fore.GREEN + Style.BRIGHT + "AIVA: " + Style.NORMAL + "Please select the job role you are applying for, your preferred programming language(s), and your experience level (Fresher / Junior / Mid / Senior).")
        if engine:
            engine.say("Please select the job role you are applying for, your preferred programming language(s), and your experience level.")
            engine.runAndWait()

        while True:
            user_input = input("\n" + Fore.BLUE + Style.BRIGHT + "You: " + Style.NORMAL).strip()
            
            if user_input.lower() in ['exit', 'quit', 'end']:
                print(Fore.YELLOW + "\nEnding the interview early. Best of luck!")
                break
            
            if not user_input:
                continue
                
            print(Fore.CYAN + "\nAIVA is thinking...")
            
            response = chat.send_message(user_input)
            
            print("\n" + Fore.GREEN + Style.BRIGHT + "AIVA: " + Style.NORMAL + response.text)
            
            if engine:
                # Remove emojis/markdown from speech if needed, or just let TTS read it.
                # Clean text a bit for better TTS
                clean_text = response.text.replace('*', '').replace('```', '')
                engine.say(clean_text)
                engine.runAndWait()

    except Exception as e:
        print(Fore.RED + f"An error occurred during communication: {e}")

if __name__ == "__main__":
    main()
