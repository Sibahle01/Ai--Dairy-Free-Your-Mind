# Ai--Dairy-Free-Your-Mind

**AI Diary Assistant** is a smart journaling tool that helps you organize your diary entries, classify them into categories, track goals, and analyze your personal reflections using AI. It combines natural language processing (NLP) with a clean, ChatGPT-inspired interface for a seamless journaling experience.

---

## Features

- **Smart Classification:** Automatically categorizes diary entries into main, secondary, and subcategories (e.g., Goals, Emotions, Plans, Health, Habits, Reflection).  
- **Goal Tracking:** Detects goals mentioned in your entries and tracks their status (planned, in_progress, completed, dropped).  
- **Entry Management:** Add, browse, and delete diary entries.  
- **Interactive UI:** Streamlit-based interface with clean, professional theme inspired by ChatGPT.  
- **Confidence Scores:** See AI confidence levels for each classification to understand model predictions.  
- *(Future) Voice-to-Text:* Plan to integrate real-time voice journaling.

---

## Example Categories

| Main Category | Subcategories (Examples) |
|---------------|-------------------------|
| Emotions      | Anxiety, Sadness, Joy, Calm |
| Goals         | Career/Skill, Savings, Education, Health |
| Plans         | Study Plan, Fitness Plan, Travel Plan |
| Health        | Exercise, Sleep, Nutrition, Therapy |
| Habits        | Routine, Focus, Consistency |
| Reflection    | Self-Awareness, Lesson Learned, Acceptance |

---

## Tech Stack

- **Python 3.10+**
- **Streamlit** – Web interface
- **Hugging Face Transformers** – Zero-shot classification (`facebook/bart-large-mnli`)
- **SQLite** – Lightweight database for entries and goals
- **pandas** – Data manipulation
- **Whisper (optional)** – Speech-to-text (planned)

---

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ai-diary-assistant.git
cd ai-diary-assistant

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt


Run Locally
streamlit run app.py


Open your browser at http://localhost:8501

Navigate between Add Entry, Browse Entries, and Goals Dashboard
