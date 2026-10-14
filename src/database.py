"""
src/database.py
===============
Stage 12 — Optional Persistence with SQLite

WHAT THIS MODULE DOES:
    Stores structured analysis results in a local SQLite database so
    that users can review past analyses without re-uploading a resume.

WHY SQLite?
    SQLite is built into Python (no installation needed) and works
    perfectly for a single-user local application. It is a simple
    flat-file database — just one .db file on disk.

PRIVACY NOTES:
    - We do NOT store raw PDF bytes or full resume text.
    - We store only the structured analysis result (scores, skills, name).
    - The SQLite file is added to .gitignore so it is never committed.
    - The application works correctly even if the database is unavailable.

TABLE SCHEMA:
    analyses
    --------
    id          : TEXT PRIMARY KEY  (generated UUID — not the filename)
    created_at  : TEXT              (ISO 8601 timestamp)
    candidate_name: TEXT
    overall_score : INTEGER
    resume_skills : TEXT            (JSON)
    jd_skills     : TEXT            (JSON)
    matched_skills: TEXT            (JSON)
    missing_skills: TEXT            (JSON)
    recommendations: TEXT           (JSON)
    jd_title      : TEXT
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.utils import get_logger, get_env, ensure_dir

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Database path (configurable via .env)
# ---------------------------------------------------------------
_DEFAULT_DB_PATH = "resume_intelligence.db"


def _get_db_path() -> str:
    return get_env("DATABASE_PATH", _DEFAULT_DB_PATH)


# ---------------------------------------------------------------
# Internal: connection helper
# ---------------------------------------------------------------

def _get_connection() -> Optional[sqlite3.Connection]:
    """
    Open a connection to the SQLite database.

    Returns None if the database cannot be opened (so callers can
    degrade gracefully).
    """
    try:
        db_path = _get_db_path()
        if db_path != ":memory:":
            Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(Path(db_path).expanduser()), timeout=10)
        conn.row_factory = sqlite3.Row  # allows dict-like row access
        return conn
    except Exception as exc:
        logger.error("Cannot open database: %s", exc)
        return None


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def create_database() -> bool:
    """
    Create the database schema if it does not already exist.

    Returns True on success, False on failure.
    This is called once at application startup.
    """
    conn = _get_connection()
    if conn is None:
        return False

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id               TEXT PRIMARY KEY,
                created_at       TEXT NOT NULL,
                candidate_name   TEXT,
                jd_title         TEXT,
                overall_score    INTEGER,
                resume_skills    TEXT,
                jd_skills        TEXT,
                matched_skills   TEXT,
                missing_skills   TEXT,
                recommendations  TEXT
            )
        """)
        conn.commit()
        logger.info("Database ready at: %s", _get_db_path())
        return True
    except Exception as exc:
        logger.error("Failed to create database schema: %s", exc)
        return False
    finally:
        conn.close()


def save_analysis(pipeline_result: Dict) -> Optional[str]:
    """
    Save a pipeline result to the database.

    Parameters
    ----------
    pipeline_result : The dict returned by pipeline.analyze_resume().

    Returns
    -------
    The generated analysis ID (str), or None on failure.

    We use a UUID as the ID so that:
    1. IDs are globally unique.
    2. No personal information (e.g., filename) is used as an identifier.
    """
    if not pipeline_result.get("success"):
        logger.warning("Attempted to save a failed pipeline result.")
        return None

    conn = _get_connection()
    if conn is None:
        return None

    try:
        analysis_id = str(uuid.uuid4())
        created_at  = datetime.now(timezone.utc).isoformat()

        candidate    = pipeline_result.get("candidate", {})
        matching     = pipeline_result.get("matching", {})
        skill_gap    = pipeline_result.get("skill_gap", {})
        jd           = pipeline_result.get("jd", {})

        conn.execute("""
            INSERT INTO analyses (
                id, created_at, candidate_name, jd_title, overall_score,
                resume_skills, jd_skills, matched_skills, missing_skills,
                recommendations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_id,
            created_at,
            candidate.get("name", "Unknown"),
            jd.get("job_title", ""),
            matching.get("overall_score", 0),
            json.dumps(pipeline_result.get("resume_skills", [])),
            json.dumps(pipeline_result.get("jd_skills", [])),
            json.dumps(skill_gap.get("matched_skills", [])),
            json.dumps(skill_gap.get("missing_required_skills", [])),
            json.dumps(pipeline_result.get("recommendations", [])),
        ))
        conn.commit()
        logger.info("Saved analysis %s", analysis_id)
        return analysis_id

    except Exception as exc:
        logger.error("Failed to save analysis: %s", exc)
        return None
    finally:
        conn.close()


def retrieve_recent_analyses(limit: int = 10) -> List[Dict]:
    """
    Retrieve the most recent analysis records.

    Parameters
    ----------
    limit : Maximum number of records to return (default: 10).

    Returns
    -------
    List of dicts representing analysis records (newest first).
    Returns empty list if the database is unavailable.
    """
    conn = _get_connection()
    if conn is None:
        return []

    try:
        cursor = conn.execute("""
            SELECT id, created_at, candidate_name, jd_title, overall_score
            FROM analyses
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to retrieve analyses: %s", exc)
        return []
    finally:
        conn.close()


def cleanup_old_analyses(keep_latest: int = 50) -> int:
    """
    Delete old analysis records, keeping only the most recent ones.

    Parameters
    ----------
    keep_latest : Number of most recent records to keep (default: 50).

    Returns
    -------
    Number of records deleted (0 if nothing was deleted or on error).
    """
    conn = _get_connection()
    if conn is None:
        return 0

    try:
        cursor = conn.execute("""
            DELETE FROM analyses
            WHERE id NOT IN (
                SELECT id FROM analyses
                ORDER BY created_at DESC
                LIMIT ?
            )
        """, (keep_latest,))
        conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info("Cleaned up %d old analysis record(s).", deleted)
        return deleted
    except Exception as exc:
        logger.error("Failed to clean up analyses: %s", exc)
        return 0
    finally:
        conn.close()
