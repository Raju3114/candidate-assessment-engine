from typing import Any, Dict, List, Optional


def build_question_generation_prompt(
    target_role: str,
    interview_type: str,
    experience_level: str,
    candidate_skills: List[str],
    num_questions: int = 5,
    categories: Optional[List[str]] = None,
) -> str:
    skills_str = ", ".join(candidate_skills) if candidate_skills else "General Backend Engineering"
    category_clause = (
        f"Focus specifically on the following categories: {', '.join(categories)}."
        if categories
        else "Select appropriate categories from: Python, FastAPI, PostgreSQL, Redis, Docker, System Design, Behavioral."
    )

    return f"""You are an Expert Technical Interviewer and Senior Software Architect.

Generate exactly {num_questions} high-quality interview questions tailored for the following candidate profile:
- Target Role: {target_role}
- Interview Type: {interview_type}
- Seniority/Experience Level: {experience_level}
- Candidate Technical Skills: {skills_str}

{category_clause}

STRICT OUTPUT FORMAT RULES:
1. Respond ONLY with a raw valid JSON object. Do not include markdown formatting ```json, preamble, or explanations.
2. The JSON object must strictly match this structure:
{{
  "questions": [
    {{
      "question_text": "Detailed question string...",
      "category": "Python", 
      "difficulty": "MEDIUM",
      "expected_topics": ["topic1", "topic2"]
    }}
  ]
}}
"""


def build_answer_evaluation_prompt(
    question_text: str,
    category: str,
    expected_topics: List[str],
    candidate_answer: str,
) -> str:
    topics_str = ", ".join(expected_topics) if expected_topics else "General domain accuracy"

    return f"""You are an Expert Technical Interview Assessor and Hiring Committee Member.

Evaluate the following candidate interview answer against the question requirements and expected topics rubric:

QUESTION:
{question_text}

CATEGORY: {category}
EXPECTED RUBRIC TOPICS: {topics_str}

CANDIDATE SUBMITTED ANSWER:
{candidate_answer}

STRICT OUTPUT FORMAT RULES:
Respond ONLY with a raw valid JSON object. Do not include markdown formatting ```json.
"""


def build_final_report_prompt(
    target_role: str,
    experience_level: str,
    overall_score: float,
    skill_breakdown: Dict[str, float],
    evaluations_summary: List[Dict[str, Any]],
) -> str:
    """Constructs prompt for generating executive summary report and hiring rationale."""
    evals_text = "\n".join(
        [
            f"- Question [{e.get('category')}]: Score {e.get('overall_score')}/10. Feedback: {e.get('feedback_text')}"
            for e in evaluations_summary
        ]
    )

    return f"""You are the VP of Engineering and Head of Technical Hiring.

Synthesize a comprehensive final interview report and executive summary for a candidate applying for:
- Role: {target_role}
- Seniority Level: {experience_level}
- Composite Overall Performance Score: {overall_score}/10.0
- Skill Category Scores: {skill_breakdown}

QUESTION-LEVEL EVALUATION RECAP:
{evals_text}

STRICT OUTPUT FORMAT RULES:
Respond ONLY with a raw valid JSON object. Do not include markdown formatting ```json, preambles, or explanations.

Expected JSON Structure:
{{
  "strengths": ["Demonstrates deep technical understanding of Python AsyncIO", "Strong PostgreSQL database query optimization skills"],
  "weaknesses": ["Needs improvement in Redis distributed caching strategies under high load"],
  "executive_summary": "The candidate performed exceptionally well across technical rounds, demonstrating senior-level competence in Python and PostgreSQL. Communication was clear and structured. Highly recommended for the Senior Backend Engineer role."
}}
"""
