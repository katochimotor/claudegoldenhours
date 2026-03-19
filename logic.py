"""Business logic: golden hours calculation and countdown."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except (ImportError, KeyError):
    import pytz
    ET = pytz.timezone("America/New_York")

PROMO_START = date(2026, 3, 13)
PROMO_END   = date(2026, 3, 28)
PEAK_START  = 8   # 8:00 AM ET (inclusive)
PEAK_END    = 14  # 2:00 PM ET (exclusive)

# ── Motivational phrases ─────────────────────────────────────────────────────

GOLDEN_PHRASES = [
    "Золотое время — Claude на максималках!",
    "Двойной лимит активен, жги токены!",
    "Сейчас Claude щедрый, пользуйся!",
    "Off-peak режим: Claude раздаёт бонусы",
    "Самое время для сложных запросов!",
    "Лимиты x2 — разгоняй нейросеть!",
    "Claude в ударе, задавай вопросы!",
    "Бесплатные токены не ждут!",
    "Золотой час пробил — кодь на полную!",
    "Пока все спят — ты качаешь скилл!",
    "Двойная порция AI — налетай!",
    "Экономия токенов: режим бога",
    "Off-peak = тебе повезло!",
    "Claude сегодня добрый, проверено",
    "Хватай бонусы пока горячие!",
]

PEAK_PHRASES = [
    "Пиковые часы... но мы ждём!",
    "Скоро золотое время, держись!",
    "Обратный отсчёт до халявы запущен",
    "Копи силы, скоро будет жарко!",
    "Пик-часы — время планировать запросы",
    "Терпение... бонусы уже близко!",
    "Готовь промпты, скоро x2!",
    "Стратегия: подожди и сэкономь!",
    "Тик-так... золотое время на подходе",
    "Пока передышка, потом разгон!",
]

ENDING_PHRASES = [
    "Торопись! Золотое время заканчивается!",
    "Осталось чуть-чуть, дожимай!",
    "Финальный рывок — успей спросить!",
    "10 минут до конца бонусов!",
    "Последний шанс — жги токены!",
]


def get_random_phrase(state: str, ending_soon: bool = False) -> str:
    if ending_soon:
        return random.choice(ENDING_PHRASES)
    if state == "golden":
        return random.choice(GOLDEN_PHRASES)
    if state == "peak":
        return random.choice(PEAK_PHRASES)
    return "Акция Claude: 13–28 марта 2026"


def get_next_transition(et_dt: datetime) -> datetime:
    """Return the next state-change boundary in ET."""
    wd = et_dt.weekday()

    if wd >= 5:
        days_to_monday = 7 - wd
        return (et_dt + timedelta(days=days_to_monday)).replace(
            hour=PEAK_START, minute=0, second=0, microsecond=0
        )

    if et_dt.hour < PEAK_START:
        return et_dt.replace(hour=PEAK_START, minute=0, second=0, microsecond=0)

    if PEAK_START <= et_dt.hour < PEAK_END:
        return et_dt.replace(hour=PEAK_END, minute=0, second=0, microsecond=0)

    days_ahead = 1
    next_wd = (wd + 1) % 7
    if next_wd == 5:
        days_ahead = 3
    elif next_wd == 6:
        days_ahead = 2
    return (et_dt + timedelta(days=days_ahead)).replace(
        hour=PEAK_START, minute=0, second=0, microsecond=0
    )


def get_status(now_local: datetime | None = None) -> dict:
    if now_local is None:
        now_local = datetime.now().astimezone()
    elif now_local.tzinfo is None:
        now_local = now_local.astimezone()

    et_dt = now_local.astimezone(ET)
    et_date = et_dt.date()
    in_promo = PROMO_START <= et_date <= PROMO_END

    if not in_promo:
        return {
            "state": "inactive",
            "et_time": et_dt,
            "local_time": now_local,
            "next_transition_et": None,
            "countdown_seconds": None,
            "ending_soon": False,
            "in_promo": False,
        }

    wd = et_dt.weekday()
    is_weekend = wd >= 5
    in_peak = (not is_weekend) and (PEAK_START <= et_dt.hour < PEAK_END)
    state = "peak" if in_peak else "golden"

    next_trans = get_next_transition(et_dt)
    delta = next_trans - et_dt
    countdown_seconds = max(0, int(delta.total_seconds()))

    # Golden ending soon: less than 10 minutes left
    ending_soon = (state == "golden") and (countdown_seconds <= 600)

    return {
        "state": state,
        "et_time": et_dt,
        "local_time": now_local,
        "next_transition_et": next_trans,
        "countdown_seconds": countdown_seconds,
        "ending_soon": ending_soon,
        "in_promo": True,
    }


def format_countdown(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
