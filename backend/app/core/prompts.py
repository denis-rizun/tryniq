from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.core.constants import (
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    CHAT_USER_CONTEXT_TEMPLATE,
    GRAPH_EXTRACTION_SYSTEM_PROMPT,
    METADATA_SYSTEM_PROMPT,
)


@dataclass(frozen=True, slots=True)
class PromptIdentity:
    name: str
    version: str
    sha256: str

    def metadata(self) -> dict[str, str]:
        return {
            "prompt.name": self.name,
            "prompt.version": self.version,
            "prompt.sha256": self.sha256,
        }


def identify_prompt(name: str, version: str, body: str) -> PromptIdentity:
    return PromptIdentity(name=name, version=version, sha256=sha256(body.encode()).hexdigest())


GRAPH_PROMPT = identify_prompt(
    "graph-extraction",
    "1.0.0",
    GRAPH_EXTRACTION_SYSTEM_PROMPT,
)
METADATA_PROMPT = identify_prompt(
    "meeting-metadata",
    "1.0.0",
    METADATA_SYSTEM_PROMPT,
)
CHAT_PROMPT = identify_prompt(
    "chat-answer",
    "1.0.0",
    f"{CHAT_SYSTEM_PROMPT_TEMPLATE}\n{CHAT_USER_CONTEXT_TEMPLATE}",
)
GRAPH_FIDELITY_JUDGE_CRITERIA = (
    "Compare the extracted meeting graph with the transcript and reviewed reference graph. "
    "Reward correct decisions, actions, questions, topics, owners, due dates, and source "
    "grounding. Penalize unsupported, duplicated, contradictory, or omitted material."
)
METADATA_RELEVANCE_JUDGE_CRITERIA = (
    "Assess whether the meeting summary captures the reviewed meeting's important decisions, "
    "actions, open questions, and topics without irrelevant detail."
)
METADATA_UNSUPPORTED_JUDGE_CRITERIA = (
    "Assess whether every factual claim in the meeting summary is supported by the transcript. "
    "Any invented fact, owner, deadline, or conclusion must reduce the score."
)
ONLINE_TRACE_QUALITY_JUDGE_CRITERIA = (
    "Assess whether the completed model output is relevant to its input, internally coherent, "
    "and free of claims unsupported by the context present in the trace."
)
GRAPH_FIDELITY_JUDGE_PROMPT = identify_prompt(
    "judge-graph-fidelity",
    "1.0.0",
    GRAPH_FIDELITY_JUDGE_CRITERIA,
)
METADATA_SUMMARY_JUDGE_PROMPT = identify_prompt(
    "judge-metadata-summary",
    "1.0.0",
    "Assess meeting-summary factuality, coverage, relevance, and unsupported claims.",
)
METADATA_RELEVANCE_JUDGE_PROMPT = identify_prompt(
    "judge-metadata-relevance",
    "1.0.0",
    METADATA_RELEVANCE_JUDGE_CRITERIA,
)
METADATA_UNSUPPORTED_JUDGE_PROMPT = identify_prompt(
    "judge-metadata-unsupported-claims",
    "1.0.0",
    METADATA_UNSUPPORTED_JUDGE_CRITERIA,
)
ONLINE_TRACE_QUALITY_JUDGE_PROMPT = identify_prompt(
    "judge-online-trace-quality",
    "1.0.0",
    ONLINE_TRACE_QUALITY_JUDGE_CRITERIA,
)
RAG_FAITHFULNESS_JUDGE_PROMPT = identify_prompt(
    "judge-rag-faithfulness",
    "1.0.0",
    "Assess whether every answer claim is supported by the supplied retrieval context.",
)
RAG_RELEVANCY_JUDGE_PROMPT = identify_prompt(
    "judge-rag-answer-relevancy",
    "1.0.0",
    "Assess whether the answer directly and completely addresses the user's question.",
)
