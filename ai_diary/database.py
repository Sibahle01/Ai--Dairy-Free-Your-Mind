# database.py
import sqlite3
from json import dumps, loads
from typing import Dict, List, Optional
from datetime import datetime

from classifier import ClassificationResult
from goal_logic import extract_goals_from_text, detect_goal_completion_mentions

DB_PATH = "diary.db"

def get_conn(db_path: str = DB_PATH):
    return sqlite3.connect(db_path)

# ------------------ Initialization ------------------

def init_db(db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        entry_text TEXT NOT NULL,
        main_category TEXT NOT NULL,
        secondary_category TEXT,
        sub_category TEXT,
        confidence_scores TEXT,
        success BOOLEAN NOT NULL DEFAULT 1,
        error_message TEXT,
        processing_time REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS tags (
        tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY (entry_id) REFERENCES entries(entry_id)
    );

    CREATE TABLE IF NOT EXISTS goals (
        goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_text TEXT NOT NULL,
        category TEXT,
        sub_category TEXT,
        status TEXT NOT NULL DEFAULT 'planned',
        target_amount REAL,
        current_amount REAL DEFAULT 0,
        due_date TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS goal_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        entry_id INTEGER NOT NULL,
        link_type TEXT NOT NULL DEFAULT 'reference',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (goal_id) REFERENCES goals(goal_id),
        FOREIGN KEY (entry_id) REFERENCES entries(entry_id)
    );
    """)
    # Ensure default user exists
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (1, "default_user"))
    conn.commit()
    conn.close()

# ------------------ Entry Functions ------------------

def save_entry(result: ClassificationResult, db_path: str = DB_PATH) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO entries (
        user_id, entry_text, main_category, secondary_category, sub_category,
        confidence_scores, processing_time, success, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,
        result.entry,
        result.main_category,
        result.secondary_category,
        result.sub_category,
        dumps(result.confidence_scores or {}),
        result.processing_time,
        int(result.success),
        result.error_message
    ))
    entry_id = cur.lastrowid

    # Insert tags
    tags = [result.main_category]
    if result.secondary_category:
        tags.append(result.secondary_category)
    if result.sub_category:
        tags.append(result.sub_category)
    for tag in tags:
        cur.execute("INSERT INTO tags (entry_id, tag) VALUES (?, ?)", (entry_id, tag))

    conn.commit()
    conn.close()
    return entry_id

def delete_entry(entry_id: int, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM tags WHERE entry_id = ?", (entry_id,))
    cur.execute("DELETE FROM entries WHERE entry_id = ?", (entry_id,))
    conn.commit()
    conn.close()

def update_entry(entry_id: int, entry_text: str, main_category: str, secondary_category: Optional[str],
                 sub_category: Optional[str], confidence_scores: Dict, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
    UPDATE entries
    SET entry_text = ?, main_category = ?, secondary_category = ?, sub_category = ?, confidence_scores = ?
    WHERE entry_id = ?
    """, (entry_text, main_category, secondary_category, sub_category, dumps(confidence_scores), entry_id))
    conn.commit()
    conn.close()

def get_entries_df(db_path: str = DB_PATH):
    import pandas as pd
    conn = get_conn(db_path)
    df = pd.read_sql_query("""
    SELECT e.entry_id, e.entry_text, e.main_category, e.secondary_category, e.sub_category,
           e.confidence_scores, e.processing_time, e.success, e.error_message,
           e.created_at, GROUP_CONCAT(t.tag) AS tags
    FROM entries e
    LEFT JOIN tags t ON e.entry_id = t.entry_id
    GROUP BY e.entry_id
    ORDER BY e.created_at DESC
    """, conn)
    conn.close()
    if not df.empty:
        df["tags"] = df["tags"].apply(lambda x: x.split(",") if isinstance(x, str) else [])
        df["confidence_scores"] = df["confidence_scores"].apply(lambda x: loads(x) if x else {})
    return df

# ------------------ Goals Functions ------------------

def add_goal(goal_text: str, category: Optional[str] = None, sub_category: Optional[str] = None,
             target_amount: Optional[float] = None, due_date: Optional[str] = None,
             notes: Optional[str] = None, status: str = "planned", db_path: str = DB_PATH) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO goals (user_id, goal_text, category, sub_category, status, target_amount, due_date, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, goal_text, category, sub_category, status, target_amount, due_date, notes))
    goal_id = cur.lastrowid
    conn.commit()
    conn.close()
    return goal_id

def update_goal(goal_id: int, goal_text: str, status: str, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("""
    UPDATE goals
    SET goal_text = ?, status = ?, updated_at = CURRENT_TIMESTAMP
    WHERE goal_id = ?
    """, (goal_text, status, goal_id))
    conn.commit()
    conn.close()

def get_goals_df(db_path: str = DB_PATH):
    import pandas as pd
    conn = get_conn(db_path)
    df = pd.read_sql_query("""
    SELECT goal_id, goal_text, category, sub_category, status, target_amount, current_amount, due_date,
           created_at, updated_at
    FROM goals
    ORDER BY created_at DESC
    """, conn)
    conn.close()
    return df

# ------------------ Auto-process ------------------

def auto_process_entry_for_goals(entry_id: int, entry_text: str, main_category: str,
                                 sub_category: Optional[str], db_path: str = DB_PATH):
    goals = extract_goals_from_text(entry_text, main_category, sub_category)
    for g in goals:
        existing = find_existing_goals_like(entry_text, db_path=db_path)
        if existing:
            link_goal_to_entry(existing[0][0], entry_id, link_type="progress", db_path=db_path)
        else:
            new_id = add_goal(goal_text=g["goal_text"], category=g.get("category"), sub_category=g.get("sub_category"),
                              target_amount=g.get("target_amount"), due_date=g.get("due_date"), notes=g.get("notes"),
                              status=g.get("status", "planned"), db_path=db_path)
            link_goal_to_entry(new_id, entry_id, link_type="created", db_path=db_path)

    completions = detect_goal_completion_mentions(entry_text)
    for phrase in completions:
        candidates = find_existing_goals_like(entry_text, db_path=db_path)
        for (goal_id, _txt) in candidates[:1]:
            update_goal(goal_id, _txt, "completed", db_path=db_path)
            link_goal_to_entry(goal_id, entry_id, link_type="completed", db_path=db_path)

def find_existing_goals_like(text: str, db_path: str = DB_PATH, limit: int = 5):
    terms = [t for t in text.lower().split() if len(t) > 3]
    if not terms:
        return []
    q = " OR ".join(["goal_text LIKE ?"] * min(len(terms), 5))
    params = [f"%{t}%" for t in terms[:5]]
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT goal_id, goal_text FROM goals WHERE {q} ORDER BY goal_id DESC LIMIT ?", (*params, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def link_goal_to_entry(goal_id: int, entry_id: int, link_type: str = "reference", db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO goal_links (goal_id, entry_id, link_type) VALUES (?, ?, ?)", (goal_id, entry_id, link_type))
    conn.commit()
    conn.close()
