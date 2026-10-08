"""
src/matcher.py
==============
Stage 6 & 9 — Resume–Job Matching Engine

WHAT THIS MODULE DOES:
    Compares a parsed resume with a parsed job description and produces:
        - An overall match score (0–100)
        - Matched skills list
        - Missing skills list
        - Component scores (skill, text similarity, semantic similarity)

WHY IT EXISTS:
    The core question of this system is: "How well does this candidate
    match this job?" This module answers that question numerically.

HOW THE SCORE IS CALCULATED:
    We use a weighted combination of three signals:

    1. SKILL MATCH SCORE (weight: 50%)
       Jaccard similarity between resume skills and JD required skills.
       Formula: |intersection| / |union|
       Why Jaccard? It rewards having the right skills, not just having
       many skills.

    2. TF-IDF COSINE SIMILARITY (weight: 30%)
       We vectorise the full resume text and JD text using TF-IDF,
       then compute the cosine of the angle between the two vectors.
       This captures keywords that appear in both documents even if
       they are not in our skill dictionary.

    3. SEMANTIC SIMILARITY (weight: 20%)
       We embed the resume and JD using sentence-transformers
       (all-MiniLM-L6-v2) and compute cosine similarity between the
       embeddings. This captures meaning rather than just keywords.
       FALLBACK: If the model fails to load, this component is skipped
       and its weight is redistributed to TF-IDF.

    Final Score = 0.50 × skill_score
                + 0.30 × tfidf_score
                + 0.20 × semantic_score

IMPORTANT DISCLAIMER:
    This score is a system-generated matching indicator, NOT a
    scientifically validated hiring probability. It should not be
    used as the sole basis for employment decisions.
"""

from typing import Dict, List, Optional
import numpy as np

from src.utils import get_logger
from src.text_preprocessor import preprocess_for_similarity

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Weights (documented here so they are easy to adjust)
# ---------------------------------------------------------------
WEIGHT_SKILL   = 0.50   # Skill Jaccard similarity
WEIGHT_TFIDF   = 0.30   # TF-IDF cosine similarity
WEIGHT_SEMANTIC = 0.20  # Semantic (sentence-transformer) similarity

# ---------------------------------------------------------------
# Lazy imports — only loaded if available
# ---------------------------------------------------------------
_tfidf_vectorizer = None
_semantic_model = None
_semantic_available = None   # None = untested, True/False = result


def _get_semantic_model():
    """
    Load the sentence-transformers model (once, then cache it).

    Returns the model, or None if it cannot be loaded.
    We try gracefully so the app doesn't crash if torch is not installed
    or if the model cannot be downloaded.
    """
    global _semantic_model, _semantic_available

    if _semantic_available is True:
        return _semantic_model

    if _semantic_available is False:
        return None

    try:
        from sentence_transformers import SentenceTransformer
        import os
        model_name = os.getenv("SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _semantic_model = SentenceTransformer(model_name)
        _semantic_available = True
        logger.info("Semantic model loaded: %s", model_name)
        return _semantic_model
    except Exception as exc:
        _semantic_available = False
        logger.warning(
            "Semantic model unavailable (%s). Falling back to TF-IDF only.", exc
        )
        return None


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def calculate_match(
    resume_text: str,
    jd_text: str,
    resume_skills: List[str],
    jd_required_skills: List[str],
) -> Dict:
    """
    Calculate how well a resume matches a job description.

    Parameters
    ----------
    resume_text         : Full text of the resume (for TF-IDF/semantic).
    jd_text             : Full text of the job description.
    resume_skills       : List of canonical skills from the resume.
    jd_required_skills  : List of canonical required skills from the JD.

    Returns
    -------
    dict with keys:
        overall_score     : int  (0–100)
        skill_score       : float (0.0–1.0)
        tfidf_score       : float (0.0–1.0)
        semantic_score    : float (0.0–1.0) or None
        matched_skills    : list of str
        missing_skills    : list of str
        semantic_used     : bool
    """
    # --- 1. Skill matching ---
    skill_score, matched, missing = _skill_jaccard(
        resume_skills, jd_required_skills
    )

    # --- 2. TF-IDF cosine similarity ---
    tfidf_score = _tfidf_cosine(resume_text, jd_text)

    # --- 3. Semantic similarity ---
    semantic_model = _get_semantic_model()
    if semantic_model is not None:
        semantic_score = _semantic_cosine(resume_text, jd_text, semantic_model)
        semantic_used = True
        # Use documented weights
        overall = (
            WEIGHT_SKILL    * skill_score
            + WEIGHT_TFIDF  * tfidf_score
            + WEIGHT_SEMANTIC * semantic_score
        )
    else:
        semantic_score = None
        semantic_used = False
        # Redistribute semantic weight to TF-IDF
        w_skill  = WEIGHT_SKILL  / (WEIGHT_SKILL + WEIGHT_TFIDF)
        w_tfidf  = WEIGHT_TFIDF  / (WEIGHT_SKILL + WEIGHT_TFIDF)
        overall  = w_skill * skill_score + w_tfidf * tfidf_score

    overall_score = int(round(overall * 100))
    overall_score = max(0, min(100, overall_score))  # clamp to [0, 100]

    return {
        "overall_score":   overall_score,
        "skill_score":     round(skill_score, 4),
        "tfidf_score":     round(tfidf_score, 4),
        "semantic_score":  round(semantic_score, 4) if semantic_score is not None else None,
        "matched_skills":  matched,
        "missing_skills":  missing,
        "semantic_used":   semantic_used,
    }


# ---------------------------------------------------------------
# Internal scoring functions
# ---------------------------------------------------------------

def _skill_jaccard(
    resume_skills: List[str],
    jd_skills: List[str],
) -> tuple:
    """
    Compute Jaccard similarity between two skill lists.

    Jaccard = |A ∩ B| / |A ∪ B|

    WHY JACCARD:
        Jaccard similarity naturally handles different set sizes.
        A candidate with 20 skills but only 3 matching is penalised
        compared to a candidate with 6 skills and 5 matching.

    Returns (score, matched_list, missing_list)
    """
    if not jd_skills:
        return 0.0, [], []

    # Normalise to lowercase sets for comparison
    resume_set = {s.lower() for s in resume_skills}
    jd_set     = {s.lower() for s in jd_skills}

    intersection = resume_set & jd_set
    union        = resume_set | jd_set

    score = len(intersection) / len(union) if union else 0.0

    # Reconstruct original casing from jd_skills
    jd_lower_to_orig = {s.lower(): s for s in jd_skills}
    matched = [jd_lower_to_orig[s] for s in intersection]
    missing = [jd_lower_to_orig[s] for s in (jd_set - resume_set)]

    return score, sorted(matched), sorted(missing)


def _tfidf_cosine(text_a: str, text_b: str) -> float:
    """
    Compute TF-IDF cosine similarity between two documents.

    WHAT IS TF-IDF?
        Term Frequency–Inverse Document Frequency. It measures how
        important a word is to a document relative to a collection.
        Words that appear often in both documents get high scores.

    WHAT IS COSINE SIMILARITY?
        The cosine of the angle between two TF-IDF vectors.
        A score of 1.0 means identical, 0.0 means no overlap at all.

    WHY USE THIS?
        It captures keyword overlap beyond our explicit skill dictionary.
        For example, if both documents mention "distributed systems",
        TF-IDF will pick that up even if it's not in skills.csv.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        # Preprocess both texts
        a = preprocess_for_similarity(text_a)
        b = preprocess_for_similarity(text_b)

        if not a.strip() or not b.strip():
            return 0.0

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        tfidf_matrix = vectorizer.fit_transform([a, b])
        score = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
        return float(score)

    except Exception as exc:
        logger.warning("TF-IDF cosine failed: %s", exc)
        return 0.0


def _semantic_cosine(text_a: str, text_b: str, model) -> float:
    """
    Compute semantic similarity using a sentence-transformers model.

    WHAT IS SEMANTIC SIMILARITY?
        Unlike TF-IDF, which compares exact words, semantic similarity
        compares the *meaning* of texts. Two texts can have high
        semantic similarity even if they use different words.

        Example:
            "Experience with distributed computing" and
            "Knowledge of cloud-based parallel processing"
            → high semantic similarity, low TF-IDF similarity

    HOW IT WORKS:
        1. Encode both texts into fixed-size embedding vectors using
           the pretrained all-MiniLM-L6-v2 model.
        2. Compute cosine similarity between the two embedding vectors.

    LIMITATION:
        The model truncates text at ~256 tokens. Very long resumes
        or JDs may lose information at the end.
    """
    try:
        # Truncate to ~512 words to stay within model limits
        def truncate(text: str, max_words: int = 400) -> str:
            words = text.split()
            return " ".join(words[:max_words])

        a = truncate(text_a)
        b = truncate(text_b)

        embeddings = model.encode([a, b], convert_to_numpy=True)
        emb_a, emb_b = embeddings[0], embeddings[1]

        # Cosine similarity formula:
        # cos(θ) = (A · B) / (||A|| × ||B||)
        dot      = float(np.dot(emb_a, emb_b))
        norm_a   = float(np.linalg.norm(emb_a))
        norm_b   = float(np.linalg.norm(emb_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        score = dot / (norm_a * norm_b)
        # Clamp to [0, 1] (cosine can be slightly negative for dissimilar texts)
        return float(max(0.0, min(1.0, score)))

    except Exception as exc:
        logger.warning("Semantic cosine failed: %s", exc)
        return 0.0
