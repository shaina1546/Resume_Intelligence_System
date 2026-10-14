"""Explainable JD matching using required-skill coverage and text similarity.

Base weights: skill coverage 50%, TF-IDF 30%, optional semantic similarity 20%.
Unavailable signals are excluded and weights are normalised. Default weights
are 62.5% coverage / 37.5% TF-IDF. With no detected requirements the skill
signal is excluded; the result is text similarity only. Extra resume skills
never reduce coverage. Scores are heuristics, not hiring probabilities.
"""

import os
from typing import Dict, List, Optional
import numpy as np

from src.utils import get_logger
from src.text_preprocessor import preprocess_for_similarity

logger = get_logger(__name__)

# ---------------------------------------------------------------
# Weights (documented here so they are easy to adjust)
# ---------------------------------------------------------------
WEIGHT_SKILL   = 0.50   # Required-skill coverage
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

    if os.getenv("ENABLE_SEMANTIC", "false").lower() not in {"true", "1", "yes"}:
        return None

    if _semantic_available is True:
        return _semantic_model

    if _semantic_available is False:
        return None

    try:
        from sentence_transformers import SentenceTransformer
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
    jd_requirement_groups=None,
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
    from src.requirements import coverage_stats
    groups = jd_requirement_groups if jd_requirement_groups is not None else [[s.strip()] for s in jd_required_skills if s.strip()]
    stats = coverage_stats(resume_skills, groups)
    skill_score, matched, missing = stats["coverage"], stats["matched_skills"], stats["missing"]

    # --- 2. TF-IDF cosine similarity ---
    tfidf_score = _tfidf_cosine(resume_text, jd_text)

    # --- 3. Semantic similarity ---
    semantic_model = _get_semantic_model()
    semantic_score = (_semantic_cosine(resume_text, jd_text, semantic_model)
                      if semantic_model is not None else None)
    semantic_used = semantic_score is not None
    # Only score available signals, normalising the documented base weights.
    weights = {"skill": WEIGHT_SKILL if groups else 0.0,
               "tfidf": WEIGHT_TFIDF,
               "semantic": WEIGHT_SEMANTIC if semantic_used else 0.0}
    total_weight = sum(weights.values())
    weights = {key: value / total_weight for key, value in weights.items()}
    overall = (weights["skill"] * skill_score + weights["tfidf"] * tfidf_score
               + weights["semantic"] * (semantic_score or 0.0))

    overall_score = int(round(overall * 100))
    overall_score = max(0, min(100, overall_score))  # clamp to [0, 100]

    return {
        "overall_score":   overall_score,
        "weights": weights,
        "skill_metric": "required_skill_coverage",
        "required_skills_detected": bool(groups),
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

def _required_skill_coverage(resume_skills: List[str], jd_skills: List[str]) -> tuple:
    """Fraction of unique required skills present; extra skills never lower this signal."""
    required = {s.strip().casefold(): s.strip() for s in jd_skills if s.strip()}
    present = {s.strip().casefold() for s in resume_skills if s.strip()}
    matched = sorted(required[key] for key in required.keys() & present)
    missing = sorted(required[key] for key in required.keys() - present)
    return (len(matched) / len(required) if required else 0.0), matched, missing


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

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000,
                                     token_pattern=r"(?u)(?<!\w)[\w+#.-]+")
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
        return None
