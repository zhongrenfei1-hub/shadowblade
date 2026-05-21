"""LLM-replacement script generator.

For now we don't call any external LLM. We use a curated template bank covering
the most common local-business scenarios (beauty, nail, spa, café, fitness,
consultation, grand opening, holiday promotion). The bank generates a
realistic Chinese script + keywords from a single ``topic`` string.

The :func:`generate_script` interface matches what an OpenAI / DeepSeek /
Ollama provider would expose, so swapping in a real LLM later is a one-file
change.
"""

from app.services.llm.script_generator import (
    SCENARIOS,
    Script,
    detect_scenario,
    generate_script,
)

__all__ = ["SCENARIOS", "Script", "detect_scenario", "generate_script"]
