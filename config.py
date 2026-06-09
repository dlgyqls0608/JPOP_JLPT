import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash-lite"
NOTION_BATCH_SIZE = 90
WORD_FONT = "Malgun Gothic"

JLPT_LEVELS = ["N5", "N4", "N3", "N2", "N1", "unknown"]

JLPT_BADGE_COLORS = {
    "N5":      {"bg": "#AED6F1", "fg": "#FFFFFF", "notion": "blue"},
    "N4":      {"bg": "#A9DFBF", "fg": "#FFFFFF", "notion": "green"},
    "N3":      {"bg": "#F9E79F", "fg": "#000000", "notion": "yellow"},
    "N2":      {"bg": "#FAD7A0", "fg": "#000000", "notion": "orange"},
    "N1":      {"bg": "#F1948A", "fg": "#FFFFFF", "notion": "red"},
    "unknown": {"bg": "#E8E8E8", "fg": "#000000", "notion": "gray"},
}

DOCX_CELL_COLORS = {
    "N5":      "AED6F1",
    "N4":      "A9DFBF",
    "N3":      "F9E79F",
    "N2":      "FAD7A0",
    "N1":      "F1948A",
    "unknown": "E8E8E8",
}

TAB_NAMES = [
    "📖 전체가사",
    "📚 단어장",
    "📐 문법정리",
    "🈶 한자",
    "💬 회화",
    "📊 분포",
    "🎯 포인트",
]

SPEAKER_COLORS = {
    "A": "#EBF5FB",
    "B": "#F2F3F4",
}


def get_anthropic_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY가 .env 파일에 설정되지 않았습니다.")
    return key


def get_google_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError("GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
    return key


def get_notion_config() -> tuple[str, str]:
    api_key = os.getenv("NOTION_API_KEY", "")
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID", "")
    return api_key, parent_id


def is_notion_configured() -> bool:
    api_key, parent_id = get_notion_config()
    return bool(api_key and parent_id)


def jlpt_badge_html(level: str) -> str:
    c = JLPT_BADGE_COLORS.get(level, JLPT_BADGE_COLORS["unknown"])
    return (
        f'<span style="background:{c["bg"]};color:{c["fg"]};'
        f'padding:2px 8px;border-radius:4px;font-weight:bold;'
        f'font-size:12px;">{level}</span>'
    )
