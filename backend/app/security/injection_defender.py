"""Sanitizer and heuristic prompt injection detector to protect the AI pipeline."""

import re
import logging

logger = logging.getLogger(__name__)

# Heuristic patterns for instruction overrides, jailbreaks, prompt leakage and exfiltration.
_SUSPICIOUS_PATTERNS = [
    # System Instruction Override
    r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|system)\s+(instructions|directives|rules|prompts)",
    r"override\s+(the\s+)?(system|rules|directives)",
    r"you\s+must\s+now\s+act\s+as",
    r"new\s+(instruction|rule|directive):",
    # Prompt / Instructions Leakage
    r"(reveal|print|show|tell|display|leak)\s+(your\s+)?(system\s+)?(prompt|instructions|rules|directives|guidelines)",
    r"what\s+is\s+your\s+system\s+prompt",
    r"copy\s+the\s+text\s+above",
    # Jailbreak / Role Confusion
    r"dan\s+mode",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"acting\s+as\s+a\s+developer",
    r"ignore\s+safety",
    # Exfiltration attempts (suspicious outbound script injection in prompts)
    r"http[s]?://[^\s]+\.(webhook|requestbin|mockbin|ngrok|herokuapp)\.com",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SUSPICIOUS_PATTERNS]


def scan_prompt(prompt: str) -> tuple[bool, str | None]:
    """Scan a user prompt for potential prompt injection attempts.
    
    Returns:
        (is_malicious, reason)
    """
    if not prompt or not isinstance(prompt, str):
        return False, None
        
    normalized = prompt.strip()
    
    # 1. Length check: very long strings can be payload stuffing
    if len(normalized) > 8000:
        return True, "Prompt exceeds maximum allowed size (8000 characters)"
        
    # 2. Heuristic regex matches
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(normalized):
            logger.warning("Prompt injection signature matched for prompt block: '%s'", pattern.pattern)
            return True, f"Suspicious prompt pattern detected: '{pattern.pattern}' is not allowed."
            
    # 3. Check for shell/system command injection patterns in the prompt input
    shell_words = ["rm -rf ", "format c:", "drop database", "truncate table"]
    for word in shell_words:
        if word in normalized.lower():
            logger.warning("Dangerous command pattern detected: '%s'", word)
            return True, f"Dangerous command pattern detected: '{word}'"

    return False, None
