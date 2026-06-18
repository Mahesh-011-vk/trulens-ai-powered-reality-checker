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
            "timestamp": f"{row[5].replace(' ', 'T')}Z" if row[5] else None,
            "explanation": row[6] if len(row) > 6 else ""
        })
    return history

def get_stats():
    """Return aggregate statistics for the dashboard."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM predictions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE prediction = 'FAKE'")
    fake_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE prediction = 'REAL'")
    real_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT AVG(
            CASE WHEN prediction = 'FAKE' THEN confidence_fake ELSE confidence_real END
        ) FROM predictions
    """)
    avg_conf_raw = cursor.fetchone()[0]
    avg_confidence = round((avg_conf_raw or 0) * 100, 1)

    cursor.execute("""
        SELECT prediction, COUNT(*) as cnt
        FROM predictions
        GROUP BY prediction
        ORDER BY cnt DESC
        LIMIT 1
    """)
    top_row = cursor.fetchone()
    most_common = top_row[0] if top_row else "N/A"

    conn.close()

    return {
        "total": total,
        "fake": fake_count,
        "real": real_count,
        "fake_ratio": round((fake_count / total * 100), 1) if total > 0 else 0.0,
        "avg_confidence": avg_confidence,
        "most_common_verdict": most_common,
    }

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
