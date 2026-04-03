"""
database.py
===========
SQLite database setup with all tables for the FYT application.
Compatible with MySQL — just change the connection driver.
"""

import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "fyt_database.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        style_preference TEXT DEFAULT 'Minimal',
        climate_region TEXT DEFAULT 'Tropical',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Body profile (1:1 with users)
    CREATE TABLE IF NOT EXISTS body_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        height_cm REAL,
        weight_kg REAL,
        shoulder_cm REAL,
        chest_cm REAL,
        waist_cm REAL,
        hip_cm REAL,
        inseam_cm REAL,
        body_type TEXT,
        bmi REAL,
        bmi_category TEXT,
        shoulder_to_hip_ratio REAL,
        waist_to_hip_ratio REAL,
        leg_to_height_ratio REAL,
        proportion_summary TEXT,
        styling_suggestions TEXT DEFAULT '[]',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Wardrobe items (1:N with users)
    CREATE TABLE IF NOT EXISTS wardrobe_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT,
        category TEXT NOT NULL,
        color TEXT NOT NULL,
        pattern TEXT,
        fabric TEXT,
        fit_type TEXT,
        formality TEXT NOT NULL,
        style_tags TEXT DEFAULT '[]',
        occasion_tags TEXT DEFAULT '[]',
        active_flag INTEGER DEFAULT 1,
        image_path TEXT,
        usage_count INTEGER DEFAULT 0,
        last_used TIMESTAMP,
        last_worn_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- User preferences (1:1 with users, updated dynamically)
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        preferred_colors TEXT DEFAULT '[]',
        disliked_colors TEXT DEFAULT '[]',
        preferred_styles TEXT DEFAULT '[]',
        disliked_styles TEXT DEFAULT '[]',
        disliked_categories TEXT DEFAULT '[]',
        preferred_formality TEXT DEFAULT 'Smart Casual',
        comfort_priority REAL DEFAULT 0.5,
        confidence_priority REAL DEFAULT 0.5,
        temporary_constraints TEXT DEFAULT '{}',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Recommendations log
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        occasion TEXT NOT NULL,
        mood TEXT,
        climate TEXT,
        outfit_items TEXT NOT NULL,
        scores TEXT NOT NULL,
        explanation TEXT,
        saved INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Recommendation sessions for next-best queue flow
    CREATE TABLE IF NOT EXISTS recommendation_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        occasion_input TEXT NOT NULL,
        mood TEXT,
        climate TEXT,
        base_constraints TEXT DEFAULT '{}',
        shown_signatures TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Feedback loop for lightweight ML ranking updates
    CREATE TABLE IF NOT EXISTS recommendation_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recommendation_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Chat logs
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        context_data TEXT,
        extracted_preferences TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    def ensure_column(table: str, col_def: str) -> None:
        col_name = col_def.split()[0]
        cols = [r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")

    # migration-safe additions for existing DB files
    ensure_column("wardrobe_items", "pattern TEXT")
    ensure_column("wardrobe_items", "fit_type TEXT")
    ensure_column("wardrobe_items", "style_tags TEXT DEFAULT '[]'")
    ensure_column("wardrobe_items", "occasion_tags TEXT DEFAULT '[]'")
    ensure_column("wardrobe_items", "active_flag INTEGER DEFAULT 1")
    ensure_column("wardrobe_items", "last_used TIMESTAMP")
    ensure_column("user_preferences", "disliked_styles TEXT DEFAULT '[]'")
    ensure_column("user_preferences", "disliked_categories TEXT DEFAULT '[]'")
    ensure_column("user_preferences", "temporary_constraints TEXT DEFAULT '{}'")

    conn.commit()
    conn.close()


def insert_sample_data():
    """Insert sample data for testing."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if sample data already exists
    existing = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    # Sample user
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, style_preference, climate_region)
        VALUES ('Demo User', 'demo@fyt.app', 'demo123hash', 'Minimal', 'Tropical')
    """)
    user_id = cursor.lastrowid

    # Sample body profile
    cursor.execute("""
        INSERT INTO body_profile (user_id, height_cm, weight_kg, shoulder_cm, chest_cm,
                                  waist_cm, hip_cm, inseam_cm, body_type, bmi, bmi_category,
                                  shoulder_to_hip_ratio, waist_to_hip_ratio, leg_to_height_ratio,
                                  proportion_summary, styling_suggestions)
        VALUES (?, 170, 68, 42, 92, 78, 94, 79, 'Rectangle', 23.5, 'Healthy',
                0.45, 0.83, 0.46,
                'Rectangle profile. Shoulders and hips are balanced with a softer waist transition.',
                '["Create shape with belted layers", "Use monochrome columns", "Mix textures at waist"]')
    """, (user_id,))

    # Sample wardrobe items
    wardrobe_data = [
        (user_id, 'White Oxford Shirt', 'Top', 'White', 'Solid', 'Cotton', 'Regular', 'Smart Casual', '["office","formal","meeting"]', '["classic","minimal"]', 1, None),
        (user_id, 'Navy Chinos', 'Bottom', 'Navy', 'Solid', 'Cotton', 'Slim', 'Smart Casual', '["office","casual"]', '["classic"]', 1, None),
        (user_id, 'Black Blazer', 'Outerwear', 'Black', 'Solid', 'Wool', 'Tailored', 'Formal', '["office","interview","formal"]', '["formal","sharp"]', 1, None),
        (user_id, 'Grey T-Shirt', 'Top', 'Grey', 'Solid', 'Cotton', 'Regular', 'Casual', '["casual","outing"]', '["casual","minimal"]', 1, None),
        (user_id, 'Blue Jeans', 'Bottom', 'Blue', 'Solid', 'Denim', 'Regular', 'Casual', '["casual","outing"]', '["casual"]', 1, None),
        (user_id, 'Beige Kurta', 'Top', 'Beige', 'Solid', 'Linen', 'Regular', 'Semi-Formal', '["festival","family","semi-formal"]', '["ethnic","classic"]', 1, None),
        (user_id, 'Cream Trousers', 'Bottom', 'Cream', 'Solid', 'Cotton', 'Regular', 'Semi-Formal', '["semi-formal","office"]', '["classic"]', 1, None),
        (user_id, 'Black Formal Shirt', 'Top', 'Black', 'Solid', 'Cotton', 'Slim', 'Formal', '["formal","dinner","office"]', '["formal"]', 1, None),
        (user_id, 'Dark Grey Pants', 'Bottom', 'Dark Grey', 'Solid', 'Polyester', 'Tailored', 'Formal', '["formal","office"]', '["formal"]', 1, None),
        (user_id, 'Maroon Polo', 'Top', 'Maroon', 'Solid', 'Cotton', 'Regular', 'Casual', '["casual","party"]', '["casual"]', 1, None),
        (user_id, 'Khaki Shorts', 'Bottom', 'Khaki', 'Solid', 'Cotton', 'Regular', 'Casual', '["casual","outing"]', '["casual"]', 1, None),
        (user_id, 'Light Blue Shirt', 'Top', 'Light Blue', 'Solid', 'Linen', 'Regular', 'Smart Casual', '["office","meeting"]', '["classic"]', 1, None),
    ]
    cursor.executemany("""
        INSERT INTO wardrobe_items (
            user_id, name, category, color, pattern, fabric, fit_type, formality,
            occasion_tags, style_tags, active_flag, image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, wardrobe_data)

    # Sample preferences
    cursor.execute("""
        INSERT INTO user_preferences (user_id, preferred_colors, disliked_colors,
                                      preferred_styles, preferred_formality,
                                      comfort_priority, confidence_priority)
        VALUES (?, '["Navy", "Beige", "White"]', '["Neon", "Orange"]',
                '["Minimal", "Classic"]', 'Smart Casual', 0.6, 0.7)
    """, (user_id,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    insert_sample_data()
    print("Database initialized with sample data.")
