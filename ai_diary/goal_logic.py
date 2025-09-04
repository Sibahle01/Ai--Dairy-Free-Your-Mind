# goal_logic.py
import re
from typing import List, Dict, Optional

def _parse_money(text: str) -> Optional[float]:
    m = re.search(r"(R|\$)?\s?(\d{1,3}(?:[,\s]\d{3})*|\d+)(?:[.,]\d+)?", text)
    if not m:
        return None
    raw = m.group(2).replace(",", "").replace(" ", "")
    try: return float(raw)
    except: return None

def extract_goals_from_text(entry_text: str, main_category: str, sub_category: Optional[str]) -> List[Dict]:
    text = entry_text.lower()
    out: List[Dict] = []

    looks_like_goal = main_category == "Goals" or any(kw in text for kw in ["i want to", "my goal is", "i plan to", "i will", "i'm going to"])
    if not looks_like_goal: return out

    if any(k in text for k in ["save", "savings", "emergency fund", "budget"]):
        amount = _parse_money(text)
        out.append({"goal_text": entry_text.strip(), "category":"Goals", "sub_category":"Savings/Finance", "target_amount": amount, "status":"planned"})
        return out
    if any(k in text for k in ["learn", "course", "study", "class", "certificate"]):
        out.append({"goal_text": entry_text.strip(), "category":"Goals","sub_category":"Education/Learning","status":"planned"})
        return out
    if any(k in text for k in ["run", "gym", "workout", "exercise", "marathon", "steps"]):
        out.append({"goal_text": entry_text.strip(), "category":"Goals","sub_category":"Health/Fitness","status":"planned"})
        return out
    if any(k in text for k in ["every day", "daily", "habit", "consistency", "routine"]):
        out.append({"goal_text": entry_text.strip(),"category":"Goals","sub_category":"Habit Building","status":"planned"})
        return out
    # fallback
    out.append({"goal_text": entry_text.strip(),"category":"Goals","sub_category":sub_category or None,"status":"planned"})
    return out

def detect_goal_completion_mentions(entry_text: str) -> List[str]:
    text = entry_text.lower()
    patterns = [
        r"\bi (finally )?(finished|completed|achieved|reached|hit|nailed)\b",
        r"\bi saved\b",
        r"\bgoal (done|complete|achieved)\b",
    ]
    hits = []
    for p in patterns:
        if re.search(p, text):
            hits.append(p)
    return hits
