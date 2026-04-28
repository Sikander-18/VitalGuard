"""
VitalGuard v2 — Centralized LLM Factory
Groq-powered LLM with deterministic fallback.
"""

import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger("vitalguard.llm")

_llm_instance = None
_llm_init_attempted = False


def get_llm():
    """
    Get the Groq LLM instance. Returns None if not configured.
    Cached after first successful init.
    """
    global _llm_instance, _llm_init_attempted

    if _llm_instance is not None:
        return _llm_instance

    if _llm_init_attempted:
        return None

    _llm_init_attempted = True

    if not settings.GROQ_API_KEY:
        logger.warning("No GROQ_API_KEY — agents will use deterministic fallback")
        return None

    try:
        from langchain_groq import ChatGroq
        _llm_instance = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
        logger.info(f"Groq LLM initialized: {settings.LLM_MODEL}")
        return _llm_instance
    except Exception as e:
        logger.error(f"Groq LLM init failed: {e}")
        return None


def get_structured_llm(schema):
    """Get LLM with structured output for a given Pydantic schema."""
    llm = get_llm()
    if llm is None:
        return None
    try:
        return llm.with_structured_output(schema)
    except Exception as e:
        logger.warning(f"Structured output failed: {e}")
        return llm


def reset_llm():
    """Reset the cached LLM (for testing/reconnection)."""
    global _llm_instance, _llm_init_attempted
    _llm_instance = None
    _llm_init_attempted = False
