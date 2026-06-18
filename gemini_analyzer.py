import json
from json_repair import repair_json
from google import genai
from google.genai import types
from config import GEMINI_MODEL, get_google_key

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
- 반드시 아래 JSON 구조 그대로 반환 (추가 필드 없음, 설명 텍스트 없음)

출력 JSON 구조:
{
  "song_info": {"title": "string", "artist": "string", "overall_jlpt_estimate": "string"},
  "lines": [{"line_number": integer, "japanese": "string", "korean_phonetic": "string", "korean_translation": "string", "is_section_break": boolean}],
  "vocabulary": [{"word": "string", "reading": "string", "korean_phonetic": "string", "meaning_korean": "string", "jlpt_level": "N1|N2|N3|N4|N5|unknown", "example_line_number": integer, "collocations": ["string"], "is_polysemous": boolean, "colloquial_note": "string or null"}],
  "grammar_points": [{"pattern": "string", "pattern_korean_phonetic": "string", "explanation_korean": "string", "jlpt_level": "N1|N2|N3|N4|N5|unknown", "example_japanese": "string", "example_line_number": integer, "function_tags": ["string"], "standard_form": "string or null", "confusion_note": "string or null"}],
  "kanji_list": [{"kanji": "string", "reading_on": "string", "reading_kun": "string", "meaning_korean": "string", "korean_reading": "string", "jlpt_level": "N1|N2|N3|N4|N5", "is_key_kanji": boolean, "example_words": ["string"]}],
  "jlpt_distribution": {"N1": integer, "N2": integer, "N3": integer, "N4": integer, "N5": integer, "unknown": integer},
  "study_summary": "string",
  "conversation_practice": [{"situation": "string", "dialogue": [{"speaker": "A|B", "japanese": "string", "korean_translation": "string", "korean_phonetic": "string", "used_items": ["string"]}]}]
}"""


def analyze_lyrics(song_title: str, artist: str, lyrics: str, api_key: str = None) -> dict:
    if not lyrics.strip():
        raise ValueError("가사를 입력해주세요.")

    client = genai.Client(api_key=api_key or get_google_key())

    user_message = f"""다음 J-POP 곡의 가사를 JLPT 학습 자료로 분석해주세요.

곡명: {song_title}
가수: {artist}

가사:
{lyrics}"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )

    raw = response.text
    if not raw or not raw.strip():
        raise ValueError("Gemini 응답이 비어 있습니다. 가사가 너무 길거나 API 할당량을 초과했을 수 있습니다.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return json.loads(repair_json(raw))
        except Exception as e:
            raise ValueError(f"Gemini 응답 파싱 오류: {e}")
