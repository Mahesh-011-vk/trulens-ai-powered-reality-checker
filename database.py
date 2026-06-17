import sqlite3
import json
from datetime import datetime

DB_FILE = "history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence_real REAL NOT NULL,
            confidence_fake REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: Add explanation column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN explanation TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_prediction(text, prediction, confidence_real, confidence_fake, explanation):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions (text, prediction, confidence_real, confidence_fake, explanation)
        VALUES (?, ?, ?, ?, ?)
    """, (text, prediction, confidence_real, confidence_fake, explanation))
    conn.commit()
    conn.close()

def get_history(limit=50):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, text, prediction, confidence_real, confidence_fake, timestamp, explanation 
        FROM predictions 
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "text": row[1],
            "prediction": row[2],
            "confidence": {
                "REAL": row[3],
                "FAKE": row[4]
            },
            "timestamp": row[5],
            "explanation": row[6] if len(row) > 6 else ""
        })
    return history

def delete_all_predictions():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()

def delete_prediction(pred_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions WHERE id = ?", (pred_id,))
    conn.commit()
    conn.close()
