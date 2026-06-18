from notion_client import Client
from config import get_notion_config, JLPT_BADGE_COLORS, NOTION_BATCH_SIZE

_MAX_RICH_TEXT = 1900  # Notion API 실제 한도 2000자보다 여유 있게


def _truncate(text: str, limit: int = _MAX_RICH_TEXT) -> str:
    s = str(text or "")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _rich_text(content, bold: bool = False, color: str = "default") -> dict:
    ann = {"bold": bold, "color": color}
    return {"type": "text", "text": {"content": _truncate(str(content or ""))}, "annotations": ann}


def _paragraph(text: str) -> list[dict]:
    """2000자 초과 텍스트를 여러 paragraph 블록으로 분할."""
    s = str(text or "")
    if not s:
        return [{"object": "block", "type": "paragraph",
                 "paragraph": {"rich_text": [_rich_text("")]}}]
    blocks = []
    for i in range(0, len(s), _MAX_RICH_TEXT):
        chunk = s[i: i + _MAX_RICH_TEXT]
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_rich_text(chunk)]},
        })
    return blocks


def _heading1(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_1",
        "heading_1": {"rich_text": [_rich_text(text, bold=True)]},
    }


def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [_rich_text(text, bold=True)]},
    }


def _callout(text: str, icon: str = "💬", color: str = "blue_background") -> list[dict]:
    """2000자 초과 시 여러 callout으로 분할."""
    s = str(text or "")
    blocks = []
    chunks = [s[i: i + _MAX_RICH_TEXT] for i in range(0, max(1, len(s)), _MAX_RICH_TEXT)]
    for chunk in chunks:
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [_rich_text(chunk)],
                "icon": {"type": "emoji", "emoji": icon},
                "color": color,
            },
        })
    return blocks


def _table_row(cells: list[list[dict]]) -> dict:
    return {
        "object": "block",
        "type": "table_row",
        "table_row": {"cells": cells},
    }


def _table(rows: list[dict], col_count: int, has_header: bool = True) -> dict:
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": col_count,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": rows,
        },
    }


def _notion_color(jlpt_level: str) -> str:
    c = JLPT_BADGE_COLORS.get(jlpt_level, JLPT_BADGE_COLORS["unknown"])
    return c["notion"]


def _cell(text: str, color: str = "default") -> list[dict]:
    return [_rich_text(_truncate(text), color=color)]


def _colored_cell(text, bg_color: str) -> list[dict]:
    return [{"type": "text",
             "text": {"content": _truncate(str(text or ""))},
             "annotations": {"color": bg_color + "_background"}}]


def _append_in_batches(notion: Client, block_id: str, children: list[dict]) -> None:
    for i in range(0, len(children), NOTION_BATCH_SIZE):
        notion.blocks.children.append(
            block_id=block_id,
            children=children[i: i + NOTION_BATCH_SIZE],
        )


def _split_tables(rows: list[dict], col_count: int) -> list[dict]:
    """헤더 포함 행 목록을 100행 이하 테이블로 분할."""
    if not rows:
        return []
    header = rows[0]
    data = rows[1:]
    chunk_size = NOTION_BATCH_SIZE - 1
    result = []
    for i in range(0, max(1, len(data)), chunk_size):
        result.append(_table([header] + data[i: i + chunk_size], col_count=col_count))
    return result


def _build_lyrics_table(lines: list[dict]) -> list[dict]:
    header_row = _table_row([
        _cell("📄 일본어 원문", "gray"),
        _cell("🔤 한국어 음차", "gray"),
        _cell("🇰🇷 한국어 해석", "gray"),
    ])
    rows = [header_row]
    for line in lines:
        if line.get("is_section_break"):
            rows.append(_table_row([_cell(""), _cell(""), _cell("")]))
        else:
            rows.append(_table_row([
                _cell(line.get("japanese", "")),
                _cell(line.get("korean_phonetic", "")),
                _cell(line.get("korean_translation", "")),
            ]))
    return _split_tables(rows, col_count=3)


def _build_vocabulary_table(vocabulary: list[dict]) -> list[dict]:
    header_row = _table_row([
        _cell("단어", "gray"),
        _cell("읽기", "gray"),
        _cell("한국어 음차", "gray"),
        _cell("뜻", "gray"),
        _cell("JLPT", "gray"),
        _cell("가사 예문 / 정보", "gray"),
    ])
    rows = [header_row]
    for v in vocabulary:
        level = v.get("jlpt_level", "unknown")
        notion_color = _notion_color(level)

        meaning = v.get("meaning_korean", "")
        if v.get("is_polysemous"):
            meaning += " ⚡"

        extra_parts = [f"예문 #{v.get('example_line_number', '')}"]
        collocations = v.get("collocations", [])
        if collocations:
            extra_parts.append("콜로: " + " / ".join(collocations[:3]))
        note = v.get("colloquial_note")
        if note:
            extra_parts.append(f"⚠️ {note}")

        rows.append(_table_row([
            _colored_cell(v.get("word", ""), notion_color),
            _cell(v.get("reading", "")),
            _cell(v.get("korean_phonetic", "")),
            _cell(meaning),
            _colored_cell(level, notion_color),
            _cell("\n".join(extra_parts)),
        ]))
    return _split_tables(rows, col_count=6)


def _build_grammar_table(grammar_points: list[dict]) -> list[dict]:
    header_row = _table_row([
        _cell("패턴", "gray"),
        _cell("한국어 음차", "gray"),
        _cell("기능 태그", "gray"),
        _cell("설명", "gray"),
        _cell("JLPT", "gray"),
        _cell("예문 / 주의", "gray"),
    ])
    rows = [header_row]
    for g in grammar_points:
        level = g.get("jlpt_level", "unknown")
        notion_color = _notion_color(level)
        tags = " ".join([f"[{t}]" for t in g.get("function_tags", [])])

        extra_parts = []
        ex = g.get("example_japanese", "")
        if ex:
            extra_parts.append(ex)
        confusion = g.get("confusion_note")
        if confusion:
            extra_parts.append(f"📌 {confusion}")
        standard = g.get("standard_form")
        if standard:
            extra_parts.append(f"→ 표준형: {standard}")

        rows.append(_table_row([
            _colored_cell(g.get("pattern", ""), notion_color),
            _cell(g.get("pattern_korean_phonetic", "")),
            _cell(tags),
            _cell(g.get("explanation_korean", "")),
            _colored_cell(level, notion_color),
            _cell("\n".join(extra_parts)),
        ]))
    return _split_tables(rows, col_count=6)


def _build_kanji_table(kanji_list: list[dict]) -> list[dict]:
    header_row = _table_row([
        _cell("한자", "gray"),
        _cell("한국식 음", "gray"),
        _cell("음독(音読み)", "gray"),
        _cell("훈독(訓読み)", "gray"),
        _cell("뜻 / 예시 단어", "gray"),
        _cell("JLPT / ★", "gray"),
    ])
    rows = [header_row]
    for k in kanji_list:
        level = k.get("jlpt_level", "N5")
        notion_color = _notion_color(level)
        star = "★" if k.get("is_key_kanji") else ""
        example_words = " / ".join(k.get("example_words", [])[:3])
        meaning_extra = k.get("meaning_korean", "")
        if example_words:
            meaning_extra += f"\n예시: {example_words}"

        rows.append(_table_row([
            _colored_cell(k.get("kanji", ""), notion_color),
            _cell(k.get("korean_reading", "")),
            _cell(k.get("reading_on", "")),
            _cell(k.get("reading_kun", "")),
            _cell(meaning_extra),
            _colored_cell(f"{level} {star}".strip(), notion_color),
        ]))
    return _split_tables(rows, col_count=5)


def _build_conversation_blocks(conversation_practice: list[dict]) -> list[dict]:
    blocks: list[dict] = []
    for i, practice in enumerate(conversation_practice, 1):
        blocks.append(_heading2(f"📍 상황 {i}: {practice.get('situation', '')}"))
        for turn in practice.get("dialogue", []):
            speaker = turn.get("speaker", "A")
            icon = "🔵" if speaker == "A" else "⚫"
            color = "blue_background" if speaker == "A" else "gray_background"
            lines = [
                f"{icon} {speaker}: {turn.get('japanese', '')}",
                f"  ({turn.get('korean_phonetic', '')})",
                f"  {turn.get('korean_translation', '')}",
                f"  ✨ {', '.join(turn.get('used_items', []))}",
            ]
            blocks.extend(_callout("\n".join(lines), icon=icon, color=color))
    return blocks


def export_to_notion(analysis: dict, page_title: str, api_key: str = None, parent_id: str = None) -> str:
    if not api_key or not parent_id:
        api_key, parent_id = get_notion_config()
    notion = Client(auth=api_key)

    song_info = analysis.get("song_info", {})
    distribution = analysis.get("jlpt_distribution", {})

    page = notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": {
                "title": [{"type": "text", "text": {"content": _truncate(page_title, 250)}}]
            }
        },
    )
    page_id = page["id"]

    info_rows = [
        _table_row([_cell("항목", "gray"), _cell("내용", "gray")]),
        _table_row([_cell("곡명"), _cell(song_info.get("title", ""))]),
        _table_row([_cell("가수"), _cell(song_info.get("artist", ""))]),
        _table_row([_cell("전체 레벨 추정"), _cell(song_info.get("overall_jlpt_estimate", ""))]),
    ]

    dist_text = "  ".join(
        [f"{lvl}: {distribution.get(lvl, 0)}개" for lvl in ["N5", "N4", "N3", "N2", "N1", "unknown"]]
    )

    children: list[dict] = [
        _heading1("🎵 노래 정보"),
        _table(info_rows, col_count=2),
        _heading1("📖 전체 가사 — 원문·음차·해석"),
        *_build_lyrics_table(analysis.get("lines", [])),
        _heading1("📚 단어장"),
        *_build_vocabulary_table(analysis.get("vocabulary", [])),
        _heading1("📐 문법정리"),
        *_build_grammar_table(analysis.get("grammar_points", [])),
        _heading1("🈶 한자 목록"),
        *_build_kanji_table(analysis.get("kanji_list", [])),
        _heading1("💬 간단 회화 실습"),
        *_build_conversation_blocks(analysis.get("conversation_practice", [])),
        _heading1("📊 JLPT 분포"),
        *_paragraph(dist_text),
        _heading1("🎯 시험 학습 포인트"),
        *_paragraph(analysis.get("study_summary", "")),
    ]

    _append_in_batches(notion, page_id, children)

    return f"https://notion.so/{page_id.replace('-', '')}"
