"""
Multi-Step RAG Generation Chain with Strict Guardrails

This module implements a controlled reasoning pipeline that enforces:
- Evidence-based reasoning (no guessing)
- Conservative architecture claims (prevents over-inference)
- Explicit uncertainty when signals are weak
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, List

# PASS 1: Evidence Extraction (Internal, Factual Only)
EVIDENCE_EXTRACTION_PROMPT = """You are a repository intelligence assistant performing PASS 1: Evidence Extraction.

CONTEXT:
{context}

USER QUESTION: {question}

**GLOBAL REASONING RULES:**
1. Never infer complex design, architecture, or patterns from weak signals.
2. Prefer the simplest explanation supported by evidence.
3. If evidence is incomplete or indirect, explicitly state uncertainty.
4. Do NOT assume industry best practices unless they are explicitly visible in the repository.
5. Conservative, grounded answers are ALWAYS preferred over confident speculation.

**File-Aware Search Heuristics:**
Architecture clues often exist in:
- Main entrypoints (main.py, app.py, index.ts, server.js)
- Dependency injection files (containers, providers, modules)
- Config files (settings.py, config.json, .env, docker-compose.yml)
- Service layers (services/, handlers/, controllers/)
- Database models (models/, entities/, schemas/)
- Infrastructure (Dockerfile, k8s/, terraform/)

**Task:** List ONLY factual signals present in the repository. Do NOT interpret or infer.

**Output Format:**
EVIDENCE:
- [Fact 1: "File X contains Y"]
- [Fact 2: "Folder Z has structure A"]
- [...]

Be precise. Quote file paths and structural elements."""

# PASS 2 + 3: Reasoning & Claim Verification (Internal)
REASONING_PROMPT = """You are performing PASS 2 & 3: Reasoning and Claim Verification.

EXTRACTED EVIDENCE:
{evidence}

USER QUESTION: {question}

**CONTROLLED REASONING PIPELINE:**

1. **Determine Supported Conclusions**: Using ONLY the extracted evidence, what can we conclude?

2. **Apply Evidence Thresholds:**
   - File purpose → requires ≥1 signal
   - Design pattern → requires ≥2 independent signals
   - Architecture → requires ≥3–4 strong signals

3. **Architecture-Specific Guardrails:**
   Do NOT classify as "microservices" unless STRONG signals exist:
   - Multiple independently deployable services
   - Service discovery or registry
   - API gateway
   - Inter-service communication (HTTP, messaging)
   - Container orchestration or infra separation
   
   FastAPI, service folders, or API tests ALONE do NOT imply microservices.
   
   If missing, prefer: "Layered Monolith" or "Modular Monolith" or "Architecture cannot be conclusively determined"

4. **Counterfactual Reasoning:**
   Ask: "What evidence would contradict this conclusion?"
   
5. **Claim Verification:**
   - Check each claim.
   - If a claim is not directly supported by evidence, REMOVE it.
   - Do not soften unsupported claims — eliminate them.

**Task:** Provide your reasoning, applying the above guardrails. State what is SUPPORTED and what is MISSING."""

# Final Answer (Shown to User)
FINAL_ANSWER_PROMPT = """You are formatting the final answer for a senior engineer.

USER QUESTION: {question}

EXTRACTED EVIDENCE:
{evidence}

REASONING & VALIDATION:
{reasoning}

**MANDATORY FORMAT:**

**Answer:**
- Clear, concise conclusion.
- Avoid overclaiming.

**Evidence:**
- Bullet list of concrete repository signals used.
- Reference files or folders explicitly (use `backticks`).

**Missing Signals:**
- List important signals that are NOT present but would be required for higher confidence.

**Confidence:** High / Medium / Low
- **High confidence:** Explicit code proves the claim.
- **Medium confidence:** Strong indirect signals support the claim.
- **Low confidence:** Weak or incomplete signals.

**FAIL-SAFE BEHAVIOR:**
If evidence is insufficient:
- Say so explicitly.
- Offer the most likely conservative interpretation.
- State assumptions clearly.

Never guess. Never over-generalize. Never present speculation as fact.

Provide your final answer now."""

def create_multistep_chain(llm):
    """Create the 3-step controlled reasoning chain."""
    
    # Pass 1: Evidence Extraction
    evidence_prompt = ChatPromptTemplate.from_template(EVIDENCE_EXTRACTION_PROMPT)
    evidence_chain = evidence_prompt | llm | StrOutputParser()
    
    # Pass 2+3: Reasoning & Claim Verification
    reasoning_prompt = ChatPromptTemplate.from_template(REASONING_PROMPT)
    reasoning_chain = reasoning_prompt | llm | StrOutputParser()
    
    # Final Answer
    final_prompt = ChatPromptTemplate.from_template(FINAL_ANSWER_PROMPT)
    final_chain = final_prompt | llm | StrOutputParser()
    
    return evidence_chain, reasoning_chain, final_chain
