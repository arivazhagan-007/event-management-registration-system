# Event Management & Registration System

An educational prototype built with Python, Streamlit, SQLite, simple ML-style keyword matching, and an optional LLM-powered event assistant.

## Features
- Dashboard for events, participants, and registrations
- Event creation and status management
- Participant profiles with interests and skills
- Event recommendations using keyword-overlap matching
- Event registration with duplicate and capacity checks
- Registration cancellation
- Feedback collection and rating summary
- Optional generative AI assistant for descriptions, promotion plans, agendas, and attendance ideas

## Run locally
1. Install Python 3.10 or newer.
2. Extract this project folder.
3. Open a terminal in this folder.
4. Create and activate a virtual environment (recommended).
5. Install dependencies:
   `pip install -r requirements.txt`
6. Start the app:
   `streamlit run app.py`
7. Open the local URL shown in the terminal.

## Enable the LLM assistant (optional)
Copy `.env.example` to `.env`, add your API key, and load environment variables in your terminal/session before running Streamlit. Never upload a real API key to GitHub. If you use a different LLM provider, adapt `ai_generate()` in `app.py`.

## Demo data
Sample events and participant profiles are inserted automatically when the database is empty. The local SQLite database `events.db` is created automatically at runtime.

## Matching approach
The recommendation baseline compares comma-separated participant interests/skills with event category/tags. The score is the percentage of event tags that overlap with the participant profile. This is a transparent keyword-based baseline, not a trained ML model. It can later be replaced with TF-IDF, embeddings, or a trained ranking model.

## Limitations
- This is a learning/demo prototype, not a production deployment.
- No authentication, payment gateway, email/SMS notifications, or cloud database is included.
- The LLM assistant works only when a valid API key and network access are configured.
- Use fictional sample data; do not store sensitive participant information in a public demo.
