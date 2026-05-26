"""
LLM-as-judge for RAG answer quality.

Scores each (question, gold_answer, predicted_answer, context) tuple on:
- faithfulness: is the predicted answer supported by the retrieved context?
- correctness: does the predicted answer match the gold answer?

Both scores are integers 0-5. Bias warning: the judge model is correlated
with the generator model (both are Cohere). Use trends across runs, not
absolute values, as the primary signal.
"""

import json
import sys
from typing import Dict, List

import cohere


JUDGE_PROMPT = """You are an impartial judge scoring an answer from a RAG system.

Score TWO axes on integer scales 0-5:

faithfulness: Is the predicted answer supported by the retrieved context?
  5 = every claim is grounded in the context
  3 = mostly grounded, minor unsupported additions
  0 = fabricated / contradicts context

correctness: Does the predicted answer match the gold answer in meaning?
  5 = same key facts, equivalent meaning
  3 = partially correct, missing or extra info
  0 = wrong or unrelated

Return STRICT JSON, no prose, no code fences:
{{"faithfulness": <int>, "correctness": <int>, "reason": "<one short sentence>"}}

Question: {question}

Gold answer: {gold_answer}

Predicted answer: {predicted_answer}

Retrieved context:
{context}
"""


def _parse(text: str) -> Dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def judge_one(
    co: cohere.Client,
    question: str,
    gold_answer: str,
    predicted_answer: str,
    context_docs: List[Dict],
    model: str = "command-r7b-12-2024",
) -> Dict:
    context = "\n\n".join(
        f"[{i+1}] {d.get('text','')}" for i, d in enumerate(context_docs)
    )[:6000]
    prompt = JUDGE_PROMPT.format(
        question=question,
        gold_answer=gold_answer,
        predicted_answer=predicted_answer,
        context=context,
    )
    try:
        resp = co.chat(message=prompt, model=model, temperature=0.0)
        scores = _parse(resp.text)
        return {
            "faithfulness": int(scores.get("faithfulness", 0)),
            "correctness": int(scores.get("correctness", 0)),
            "reason": str(scores.get("reason", ""))[:300],
        }
    except Exception as e:
        print(f"  ! judge failed: {e}", file=sys.stderr)
        return {"faithfulness": 0, "correctness": 0, "reason": f"judge_error: {e}"}
