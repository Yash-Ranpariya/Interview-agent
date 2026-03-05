# AIVA Prime v2.8: Global Architecture Interviewer

AIVA is a production-ready AI Interview Agent that conducts high-stakes technical evaluations using **Human-Logic v2.8**. It moves beyond simple Q&A to simulate a real, non-linear technical discussion.

## 🚀 Key Evolutionary Features
- **🧠 Deep-Branching Logic (v2.8)**: Uses a CSV question bank as a foundation but generates dynamic follow-up questions based on the candidate's specific architectural choices.
- **💓 Human Vitality**: Features a "breathing" avatar and a "Neural Aura" glow that reacts to speech and thought processes.
- **🛡️ Shield Proctoring**: Real-time tab-switching detection, webcam monitoring, and automatic disqualification for integrity violations.
- **🎙️ Conversational Interleaving**: Candidates can "barge in" (interrupt) the AI, and the AI automatically starts listening after speaking, creating a natural dialogue loop.
- **🎭 Developer Mock Mode**: A built-in "No-API" mode allowing developers to test voice, proctoring, and UI flows without consuming Gemini credits.
- **🌍 Polyglot Support**: Native Technical Hindi and Gujarati support for global candidate reach.

## 🛠️ Setup & Deployment

1. **Environment Config**:
   Copy `.env.example` to `.env` and configure your `GEMINI_API_KEY` and Gmail SMTP credentials for automated report delivery.

2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Execution**:
   ```bash
   python app.py
   ```

## 📊 Evaluation Workflow
AIVA tracks candidate confidence via **Sentiment-Aware Calibration**. At the end of every session, a **Command Center Report** is generated, saved to the database, and automatically emailed to both the company and the candidate.
