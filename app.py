"""
app.py — Resume Intelligence System
=====================================
Streamlit user interface (entry point).

HOW TO RUN:
    streamlit run app.py

WHAT THIS FILE DOES:
    - Renders the Streamlit web UI.
    - Accepts user inputs (PDF upload, job description text).
    - Calls pipeline.analyze_resume() for all analysis.
    - Displays results in a clean dashboard.

DESIGN RULE:
    This file contains ONLY UI code.
    ALL business logic lives in the src/ modules.
"""

import streamlit as st
import plotly.graph_objects as go
import json

# ---------------------------------------------------------------
# Page configuration (MUST be first Streamlit call)
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Resume Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------
# Imports from our pipeline
# ---------------------------------------------------------------
from src.pipeline import analyze_resume
from src.database import create_database, save_analysis
from src.skill_gap import get_gap_summary

# Initialise the database (silently; app works even if DB fails)
create_database()


# ---------------------------------------------------------------
# Helper: display a skill as a coloured badge
# ---------------------------------------------------------------
def _skill_badge(skill: str, color: str = "#4A90D9") -> str:
    """Return an HTML span that looks like a skill tag/badge."""
    return (
        f'<span style="background-color:{color};color:white;'
        f'padding:3px 10px;border-radius:12px;margin:3px;'
        f'display:inline-block;font-size:0.85rem;">{skill}</span>'
    )


def _badges(skills, color="#4A90D9"):
    """Render a list of skills as HTML badges."""
    if not skills:
        return "<em>None detected</em>"
    return " ".join(_skill_badge(s, color) for s in skills)


# ---------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/000000/resume.png",
        width=64,
    )
    st.title("📄 Resume Intelligence")
    st.markdown("---")

    st.subheader("1. Upload Your Resume")
    uploaded_file = st.file_uploader(
        "Upload a PDF resume",
        type=["pdf"],
        help="Only text-based PDFs are supported. Scanned PDFs will not work.",
    )

    st.subheader("2. Job Description")
    jd_input_method = st.radio(
        "How would you like to provide the JD?",
        options=["Paste text", "Upload .txt file"],
        horizontal=True,
    )

    job_description = ""
    if jd_input_method == "Paste text":
        job_description = st.text_area(
            "Paste the job description here",
            height=250,
            placeholder=(
                "Example:\n"
                "We are looking for a Data Scientist with experience in Python, SQL, "
                "Machine Learning, and TensorFlow..."
            ),
        )
    else:
        jd_file = st.file_uploader("Upload Job Description (.txt)", type=["txt"])
        if jd_file:
            job_description = jd_file.read().decode("utf-8", errors="replace")
            st.success("Job description loaded from file.")

    st.markdown("---")
    analyze_button = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")

    st.markdown("---")
    st.caption(
        "ℹ️ **Disclaimer**: Match scores are system-generated indicators, "
        "not scientifically validated hiring probabilities. "
        "Do not use this tool as the sole basis for employment decisions."
    )


# ---------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------
st.title("📄 Resume Intelligence System")
st.markdown(
    "Upload a resume and a job description, then click **Analyze Resume** to get started."
)

if not analyze_button:
    # Show a welcome screen when no analysis has been run yet
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Step 1**\nUpload your PDF resume in the sidebar.")
    with col2:
        st.info("**Step 2**\nPaste or upload the job description.")
    with col3:
        st.info("**Step 3**\nClick **Analyze Resume** to see results.")
    st.stop()

# ---------------------------------------------------------------
# Validation before running the pipeline
# ---------------------------------------------------------------
errors_found = False

if not uploaded_file:
    st.error("❌ Please upload a PDF resume in the sidebar.")
    errors_found = True

if not job_description or not job_description.strip():
    st.error("❌ Please provide a job description in the sidebar.")
    errors_found = True

if errors_found:
    st.stop()

# ---------------------------------------------------------------
# Run the pipeline
# ---------------------------------------------------------------
with st.spinner("⏳ Analysing your resume... This may take a moment on first run."):
    # Read the uploaded PDF into bytes
    pdf_bytes = uploaded_file.read()

    result = analyze_resume(
        resume_source   = pdf_bytes,
        job_description = job_description,
        top_n_roles     = 5,
    )

# ---------------------------------------------------------------
# Handle pipeline errors
# ---------------------------------------------------------------
if not result.get("success"):
    st.error("❌ Analysis failed")
    st.markdown(result.get("error", "Unknown error occurred."))
    st.stop()

# Show non-fatal warnings
for warning in result.get("warnings", []):
    st.warning(warning)

# Optionally save to DB (silent failure is acceptable)
save_analysis(result)

# ---------------------------------------------------------------
# Unpack result
# ---------------------------------------------------------------
candidate       = result.get("candidate", {})
resume_skills   = result.get("resume_skills", [])
jd_info         = result.get("jd", {})
jd_skills       = result.get("jd_skills", [])
matching        = result.get("matching", {})
skill_gap       = result.get("skill_gap", {})
recommendations = result.get("recommendations", [])

overall_score   = matching.get("overall_score", 0)
skill_score_pct = int(matching.get("skill_score", 0) * 100)
tfidf_score_pct = int(matching.get("tfidf_score", 0) * 100)
semantic_score  = matching.get("semantic_score")
semantic_used   = matching.get("semantic_used", False)

matched_skills         = skill_gap.get("matched_skills", [])
missing_required       = skill_gap.get("missing_required_skills", [])
missing_preferred      = skill_gap.get("missing_preferred_skills", [])
additional_skills      = skill_gap.get("additional_skills", [])
match_percentage       = skill_gap.get("match_percentage", 0)

st.markdown("---")

# ================================================================
# Section 1: Candidate Information
# ================================================================
st.header("👤 Candidate Information")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown(f"**Name:** {candidate.get('name') or '_Not detected_'}")
    st.markdown(f"**Email:** {candidate.get('email') or '_Not detected_'}")
    st.markdown(f"**Phone:** {candidate.get('phone') or '_Not detected_'}")

with col_b:
    edu = candidate.get("education", [])
    if edu:
        with st.expander(f"🎓 Education ({len(edu)} entries)"):
            for line in edu:
                st.markdown(f"- {line}")
    else:
        st.markdown("**Education:** _Not detected_")

    exp = candidate.get("experience", [])
    if exp:
        with st.expander(f"💼 Experience ({len(exp)} entries)"):
            for line in exp[:10]:  # limit display
                st.markdown(f"- {line}")
    else:
        st.markdown("**Experience:** _Not detected_")

# ================================================================
# Section 2: Resume Skills
# ================================================================
st.header("🛠️ Resume Skills")
if resume_skills:
    st.markdown(
        _badges(resume_skills, "#2196F3"),
        unsafe_allow_html=True,
    )
    st.caption(f"Total skills detected: {len(resume_skills)}")
else:
    st.warning(
        "No skills were detected in the resume. "
        "Try uploading a resume that lists skills in a Skills section."
    )

# ================================================================
# Section 3: Job Requirements
# ================================================================
st.header("📋 Job Requirements")

col_req, col_pref = st.columns(2)
with col_req:
    st.subheader("Required Skills")
    if jd_skills:
        st.markdown(_badges(jd_skills, "#9C27B0"), unsafe_allow_html=True)
    else:
        st.markdown("_None detected_")

with col_pref:
    st.subheader("Preferred Skills")
    pref = jd_info.get("preferred_skills", [])
    if pref:
        st.markdown(_badges(pref, "#FF9800"), unsafe_allow_html=True)
    else:
        st.markdown("_None listed_")

jd_exp = jd_info.get("experience", [])
jd_edu = jd_info.get("education", [])
if jd_exp or jd_edu:
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if jd_exp:
            with st.expander("Experience Requirements"):
                for line in jd_exp:
                    st.markdown(f"- {line}")
    with col_e2:
        if jd_edu:
            with st.expander("Education Requirements"):
                for line in jd_edu:
                    st.markdown(f"- {line}")

# ================================================================
# Section 4: Resume–Job Match Score
# ================================================================
st.header("🎯 Resume–Job Match")

# Big score gauge
fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=overall_score,
    title={"text": "Overall Match Score", "font": {"size": 20}},
    gauge={
        "axis": {"range": [0, 100]},
        "bar":  {"color": "#4A90D9"},
        "steps": [
            {"range": [0,  40], "color": "#FFEBEE"},
            {"range": [40, 65], "color": "#FFF9C4"},
            {"range": [65, 100],"color": "#E8F5E9"},
        ],
        "threshold": {
            "line": {"color": "green", "width": 3},
            "thickness": 0.75,
            "value": 70,
        },
    },
    number={"suffix": "%"},
))
fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, use_container_width=True)

# Component score breakdown
st.subheader("Score Components")
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.metric("Skill Match", f"{skill_score_pct}%", help="Jaccard similarity between your skills and required skills (weight: 50%)")
with col_s2:
    st.metric("Text Similarity", f"{tfidf_score_pct}%", help="TF-IDF cosine similarity between resume and JD text (weight: 30%)")
with col_s3:
    if semantic_used and semantic_score is not None:
        sem_pct = int(semantic_score * 100)
        st.metric("Semantic Similarity", f"{sem_pct}%", help="Sentence-transformer embedding similarity (weight: 20%)")
    else:
        st.metric("Semantic Similarity", "N/A", help="Semantic model unavailable — score is based on Skill + TF-IDF only.")

with st.expander("ℹ️ How is the score calculated?"):
    st.markdown("""
    The **Overall Match Score** is a weighted combination of three signals:

    | Component | Weight | What it measures |
    |---|---|---|
    | Skill Match | 50% | Jaccard similarity between your skills and the job's required skills |
    | Text Similarity | 30% | TF-IDF cosine similarity between full resume and JD text |
    | Semantic Similarity | 20% | Meaning-based similarity using a neural embedding model |

    If the semantic model is unavailable, its weight (20%) is redistributed
    proportionally between Skill Match and Text Similarity.

    **This score is a system-generated indicator, not a hiring probability.**
    """)

# ================================================================
# Section 5 & 6: Skill Analysis & Gap
# ================================================================
st.header("📊 Skill Analysis & Gap")

tab_matched, tab_missing, tab_additional = st.tabs([
    f"✅ Matched ({len(matched_skills)})",
    f"❌ Missing Required ({len(missing_required)})",
    f"➕ Additional ({len(additional_skills)})",
])

with tab_matched:
    if matched_skills:
        st.markdown(_badges(matched_skills, "#4CAF50"), unsafe_allow_html=True)
        st.caption("These are required job skills you already have on your resume.")
    else:
        st.markdown("_No direct skill matches found._")

with tab_missing:
    if missing_required:
        st.markdown(_badges(missing_required, "#F44336"), unsafe_allow_html=True)
        st.caption(
            "These are required skills not found on your resume. "
            "Consider learning them to improve your chances."
        )
    else:
        st.success("✅ You have all the required skills for this job!")

    if missing_preferred:
        st.markdown("**Missing Preferred (nice-to-have) Skills:**")
        st.markdown(_badges(missing_preferred, "#FF9800"), unsafe_allow_html=True)

with tab_additional:
    if additional_skills:
        st.markdown(_badges(additional_skills, "#607D8B"), unsafe_allow_html=True)
        st.caption("These skills are on your resume but not listed in this job description. They may be valuable for other roles.")
    else:
        st.markdown("_No additional skills detected._")

# Gap summary
st.markdown("### Skill Gap Summary")
summary_text = get_gap_summary(skill_gap)
st.markdown(summary_text)

# Progress bar for skill match
st.progress(match_percentage / 100, text=f"Required skill coverage: {match_percentage}%")

# ================================================================
# Section 7: Job Role Recommendations
# ================================================================
st.header("💼 Recommended Job Roles")
st.markdown(
    "Based on your skills, these roles may be a good fit for you. "
    "Scores reflect what fraction of each role's typical skills you already have."
)

if recommendations:
    for i, rec in enumerate(recommendations):
        with st.expander(
            f"#{i+1}  {rec['role']}  —  {rec['score']}% match",
            expanded=(i == 0),
        ):
            st.markdown(f"**{rec['description']}**")

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("**Skills you have:**")
                if rec["matched_skills"]:
                    st.markdown(_badges(rec["matched_skills"], "#4CAF50"), unsafe_allow_html=True)
                else:
                    st.markdown("_None_")

            with col_r2:
                st.markdown("**Skills to learn:**")
                if rec["missing_skills"]:
                    st.markdown(_badges(rec["missing_skills"], "#F44336"), unsafe_allow_html=True)
                else:
                    st.markdown("_You already have all the core skills!_")

            st.progress(rec["score"] / 100, text=f"Role match: {rec['score']}%")
else:
    st.info("No role recommendations available. Add more skills to your resume for better recommendations.")

# ================================================================
# Section 8: Explainability / Raw Data
# ================================================================
with st.expander("🔍 See full analysis details (for debugging / explainability)"):
    st.json({
        "candidate_name": candidate.get("name"),
        "overall_score":  overall_score,
        "resume_skills":  resume_skills,
        "jd_skills":      jd_skills,
        "matched_skills": matched_skills,
        "missing_required": missing_required,
        "semantic_used":  semantic_used,
    })

# ================================================================
# Footer
# ================================================================
st.markdown("---")
st.caption(
    "Resume Intelligence System v1.0 · "
    "Built with Python, spaCy, scikit-learn, sentence-transformers & Streamlit · "
    "Academic/prototype use only · Not for production hiring decisions."
)
