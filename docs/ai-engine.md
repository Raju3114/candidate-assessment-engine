# Gemini AI Engine & Prompt Parsers Documentation

## 1. Overview

The AI engine integrates **Google Gemini 1.5 Pro** via `google-generativeai` SDK to power two core capabilities:
1. **Dynamic Question Generation**: Tailors technical questions to candidate skills and target role.
2. **Automated Answer Evaluation**: Evaluates candidate text responses against rubric criteria.

---

## 2. Structured Output & Markdown Stripping Pipeline

LLMs frequently wrap JSON responses in markdown code fences (` ```json ... ``` `). The parser pipeline strips formatting and validates payload structure using Pydantic:

```
[ Raw Gemini API Output ]
          │
          ▼
[ Regex Markdown Stripper ]  (Removes ```json and trailing ```)
          │
          ▼
 [ json.loads() Decoder ]
          │
          ▼
[ Pydantic Schema Validator ]  (Clamps scores between 0.0 - 10.0)
          │
          ▼
  [ Domain Entity / DTO ]
```

---

## 3. Fallback Resilience Strategy

If Gemini API encounters network timeouts, rate limit quotas (`429 Too Many Requests`), or server errors, the system triggers a fallback generator to ensure zero-downtime interview execution:

- **Question Generation Fallback**: Returns curated domain questions matching candidate role and experience level.
- **Answer Evaluation Fallback**: Synthesizes rule-based qualitative feedback based on answer word count and rubric topic matching.
