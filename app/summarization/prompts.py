"""Phase 4 — Summarization: prompts.

Prompt text lives here, separately from the calling logic in
summarizer.py, so prompts can be read, reviewed, and tweaked without
touching any code that talks to the LLM service.

The system prompt only ever asks for the four fields the model is
actually trusted to generate (``headline``, ``summary``, ``key_points``,
``why_it_matters``) -- see the design note at the top of
structured_output.py for why ``category``/``entities``/``source_url``
are deliberately never requested from the model.
"""

from __future__ import annotations

from app.processing.normalization import ProcessedItem

SYSTEM_PROMPT = """You are an AI-news summarization assistant for an AI intelligence platform.

You will be given the content of a single article/post. Your job is to summarize ONLY \
what is stated in that content -- nothing else.

Rules:
- Base every statement strictly on the ARTICLE CONTENT provided in the user message. \
Do not use outside knowledge, do not assume facts about the companies/people/products \
involved beyond what's written, and do not invent numbers, quotes, dates, or details \
that are not present in the content.
- If the content is too short or too thin to summarize with confidence, say so plainly \
in the "summary" field (e.g. "Limited detail available; ...") rather than filling in \
gaps with assumptions.
- Keep "headline" under 100 characters, and different from the original title if the \
original title is not itself a clear headline.
- "key_points" should be 2-5 short bullet-style strings, each a single self-contained fact \
from the content.
- "why_it_matters" is 1-2 sentences on the significance of this specific development, \
grounded only in what the content says.
- Respond with ONLY a single JSON object, and nothing else: no prose before or after it, \
no markdown code fences. The object must have exactly these keys:

{
  "headline": "string",
  "summary": "string (2-4 sentences)",
  "key_points": ["string", "..."],
  "why_it_matters": "string"
}
"""

# Content fed to the model is capped to keep prompts small/cheap and to
# avoid encouraging the model to "fill in" a very long, choppy input.
MAX_CONTENT_CHARS = 4000


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " [content truncated]"


def build_user_prompt(item: ProcessedItem, max_content_chars: int = MAX_CONTENT_CHARS) -> str:
    """Build the user-turn prompt for one ``ProcessedItem``.

    Includes the item's own already-known metadata (source, category,
    published date) as context, then the article content itself, clearly
    fenced off as the only material to summarize from.
    """

    published = item.published_at.isoformat() if item.published_at else "unknown"

    content_parts = [p for p in (item.summary, item.raw_text) if p]
    content = "\n\n".join(content_parts) or "(no additional content beyond the title)"
    content = _truncate(content, max_content_chars)

    return f"""Title: {item.title}
Source: {item.source} ({item.source_type})
Published: {published}
Pre-classified category: {item.primary_category or "unknown"}

ARTICLE CONTENT:
\"\"\"
{content}
\"\"\"

Summarize the ARTICLE CONTENT above according to your instructions, returning only the JSON object."""
