"""nexus_os/nexusclaw/wiki_helpers.py — Shared wiki pipeline search helper.

Centralizes the get_wiki_pipeline import + try/except fallback pattern that
was duplicated between evidence.py and research_synthesis.py. A pipeline
API change (e.g. pipeline → search_service) now only needs to be made here.
"""

from typing import List, Dict, Any


def safe_wiki_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search the wiki pipeline with graceful fallback.

    Wraps `get_wiki_pipeline().search(...)` in a try/except and returns
    an empty list if the pipeline is unavailable (import failure, service
    down, schema mismatch). Returned dict shape: {slug, title, snippet}.

    Args:
        query: Search query string.
        limit: Max results to return (capped by pipeline).

    Returns:
        List of result dicts with keys 'slug', 'title', 'snippet'.
        Empty list on failure.
    """
    try:
        from nexus_cli_ctl.integrations.wiki_pipeline import get_wiki_pipeline
        pipeline = get_wiki_pipeline()
        results = pipeline.search(query, limit=limit)
        normalized = []
        for r in results:
            normalized.append({
                "slug": r.get("slug", ""),
                "title": r.get("title", ""),
                "snippet": r.get("snippet", "")[:200],
            })
        return normalized
    except Exception:
        return []
