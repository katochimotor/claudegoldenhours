"""Read Claude Code usage statistics from ~/.claude/stats-cache.json."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
CACHE_FILE = CLAUDE_DIR / "stats-cache.json"


def get_stats() -> dict:
    """Read stats-cache.json and return aggregated usage stats.

    Returns a dict with keys:
        today_messages, today_tool_calls,
        week_messages, week_tool_calls,
        total_messages, total_sessions,
        input_tokens, output_tokens,
        available (bool — False if file missing or unreadable)
    """
    result = {
        "today_messages": 0,
        "today_tool_calls": 0,
        "week_messages": 0,
        "week_tool_calls": 0,
        "total_messages": 0,
        "total_sessions": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "available": False,
    }

    try:
        if not CACHE_FILE.exists():
            return result

        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

        today_str = date.today().isoformat()
        week_ago_str = (date.today() - timedelta(days=6)).isoformat()

        for entry in data.get("dailyActivity", []):
            d = entry.get("date", "")
            mc = entry.get("messageCount", 0)
            tc = entry.get("toolCallCount", 0)
            if d == today_str:
                result["today_messages"] = mc
                result["today_tool_calls"] = tc
            if d >= week_ago_str:
                result["week_messages"] += mc
                result["week_tool_calls"] += tc

        result["total_messages"] = data.get("totalMessages", 0)
        result["total_sessions"] = data.get("totalSessions", 0)

        for _model, usage in data.get("modelUsage", {}).items():
            result["input_tokens"] += usage.get("inputTokens", 0)
            result["output_tokens"] += usage.get("outputTokens", 0)

        result["available"] = True

    except Exception:
        pass

    return result


def fmt_tokens(n: int) -> str:
    """Format large token counts compactly: 118335965 → '118.3M', 45231 → '45.2K'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
