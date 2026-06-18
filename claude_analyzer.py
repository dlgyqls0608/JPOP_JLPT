import anthropic
from config import CLAUDE_MODEL, get_anthropic_key

SYSTEM_PROMPT = """당신은 JLPT 전문 일본어 교육자입니다. J-POP 가사를 분석해 JLPT 학습 자료를 JSON으로 반환합니다.

규칙:
- 모든 한국어 음차는 로마자가 아닌 한글로 표기 (예: さいきん → 사이킨)
- 장음: おう → 오우, えい → 에이 / 촉음: っ → 받침 (きって → 킷테)
- 어휘·문법 JLPT 레벨은 N1~N5 또는 unknown으로만 표기
- vocabulary에는 명사·동사·형용사·부사 등 실질 단어만 포함 (조사, 접속사, 조동사, 문법 패턴·표현은 grammar_points에만 기재, vocabulary에 절대 포함 금지)
- kanji_list에는 JLPT N1~N5에 등재된 한자 중 학습 가치 있는 것만 포함 (비JLPT 한자 완전 제외)
- kanji_list 제외 대상: 가사에 히라가나로만 쓰인 단어, 조사·조동사 전용 한자, 純수 오쿠리가나(送り仮名)로만 구성된 어미
- korean_reading은 전통 한국식 한자 독법 '뜻 음' 형식으로 표기 (예: 火→'불 화', 水→'물 수', 木→'나무 목', 愛→'사랑 애', 心→'마음 심')
- 구어체 단축형(てる/ちゃう/じゃ/なきゃ 등)은 colloquial_note에 표준형 명시
- conversation_practice: 3~5세트, 각 세트당 2~4줄 대화, 노래 속 단어/문법 최소 2개 사용
- 순수 JSON만 반환 (설명 텍스트 없음)"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "song_info", "lines", "vocabulary", "grammar_points",
        "kanji_list", "jlpt_distribution", "study_summary", "conversation_practice"
    ],
    "properties": {
        "song_info": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "artist", "overall_jlpt_estimate"],
            "properties": {
                "title": {"type": "string"},
                "artist": {"type": "string"},
                "overall_jlpt_estimate": {"type": "string"},
            },
        },
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["line_number", "japanese", "korean_phonetic", "korean_translation", "is_section_break"],
                "properties": {
                    "line_number": {"type": "integer"},
                    "japanese": {"type": "string"},
                    "korean_phonetic": {"type": "string"},
                    "korean_translation": {"type": "string"},
                    "is_section_break": {"type": "boolean"},
                },
            },
        },
        "vocabulary": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "word", "reading", "korean_phonetic", "meaning_korean",
                    "jlpt_level", "example_line_number", "collocations",
                    "is_polysemous", "colloquial_note"
                ],
                "properties": {
                    "word": {"type": "string"},
                    "reading": {"type": "string"},
                    "korean_phonetic": {"type": "string"},
                    "meaning_korean": {"type": "string"},
                    "jlpt_level": {"type": "string", "enum": ["N1", "N2", "N3", "N4", "N5", "unknown"]},
                    "example_line_number": {"type": "integer"},
                    "collocations": {"type": "array", "items": {"type": "string"}},
                    "is_polysemous": {"type": "boolean"},
                    "colloquial_note": {"type": ["string", "null"]},
                },
            },
        },
        "grammar_points": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "pattern", "pattern_korean_phonetic", "explanation_korean",
                    "jlpt_level", "example_japanese", "example_line_number",
                    "function_tags", "standard_form", "confusion_note"
                ],
                "properties": {
                    "pattern": {"type": "string"},
                    "pattern_korean_phonetic": {"type": "string"},
                    "explanation_korean": {"type": "string"},
                    "jlpt_level": {"type": "string", "enum": ["N1", "N2", "N3", "N4", "N5", "unknown"]},
                    "example_japanese": {"type": "string"},
                    "example_line_number": {"type": "integer"},
                    "function_tags": {"type": "array", "items": {"type": "string"}},
                    "standard_form": {"type": ["string", "null"]},
                    "confusion_note": {"type": ["string", "null"]},
                },
            },
        },
        "kanji_list": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kanji", "reading_on", "reading_kun", "meaning_korean",
                    "korean_reading", "jlpt_level", "is_key_kanji", "example_words"
                ],
                "properties": {
                    "kanji": {"type": "string"},
                    "reading_on": {"type": "string"},
                    "reading_kun": {"type": "string"},
                    "meaning_korean": {"type": "string"},
                    "korean_reading": {"type": "string"},
                    "jlpt_level": {"type": "string", "enum": ["N1", "N2", "N3", "N4", "N5"]},
                    "is_key_kanji": {"type": "boolean"},
                    "example_words": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "jlpt_distribution": {
            "type": "object",
            "additionalProperties": False,
            "required": ["N1", "N2", "N3", "N4", "N5", "unknown"],
            "properties": {
                "N1": {"type": "integer"},
                "N2": {"type": "integer"},
                "N3": {"type": "integer"},
                "N4": {"type": "integer"},
                "N5": {"type": "integer"},
                "unknown": {"type": "integer"},
            },
        },
        "study_summary": {"type": "string"},
        "conversation_practice": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["situation", "dialogue"],
                "properties": {
                    "situation": {"type": "string"},
                    "dialogue": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "speaker", "japanese", "korean_translation",
                                "korean_phonetic", "used_items"
                            ],
                            "properties": {
                                "speaker": {"type": "string", "enum": ["A", "B"]},
                                "japanese": {"type": "string"},
                                "korean_translation": {"type": "string"},
                                "korean_phonetic": {"type": "string"},
                                "used_items": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                },
            },
        },
    },
}


TOOL_DEF = {
    "name": "return_jlpt_analysis",
    "description": "J-POP 가사의 JLPT 분석 결과를 구조화된 JSON으로 반환합니다.",
    "input_schema": SCHEMA,
}


def analyze_lyrics(song_title: str, artist: str, lyrics: str, api_key: str = None) -> dict:
    if not lyrics.strip():
        raise ValueError("가사를 입력해주세요.")

    client = anthropic.Anthropic(api_key=api_key or get_anthropic_key())

    user_message = f"""다음 J-POP 곡의 가사를 JLPT 학습 자료로 분석해주세요.

곡명: {song_title}
가수: {artist}

가사:
{lyrics}"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16384,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[TOOL_DEF],
        tool_choice={"type": "tool", "name": "return_jlpt_analysis"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "return_jlpt_analysis":
            return block.input

    raise ValueError("Claude API에서 분석 결과를 받지 못했습니다. 다시 시도해주세요.")
