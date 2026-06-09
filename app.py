import os
import re
import streamlit as st
import pandas as pd

from config import (
    TAB_NAMES, JLPT_LEVELS, SPEAKER_COLORS,
    jlpt_badge_html, is_notion_configured,
)
from notion_exporter import export_to_notion
from docx_exporter import export_to_docx

_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def _save_to_env(key_name: str, key_value: str):
    if os.path.exists(_ENV_PATH):
        text = open(_ENV_PATH, encoding="utf-8").read()
        if re.search(rf"^{key_name}=", text, re.MULTILINE):
            text = re.sub(rf"^{key_name}=.*$", f"{key_name}={key_value}", text, flags=re.MULTILINE)
        else:
            text = text.rstrip("\n") + f"\n{key_name}={key_value}\n"
    else:
        text = f"{key_name}={key_value}\n"
    open(_ENV_PATH, "w", encoding="utf-8").write(text)
    os.environ[key_name] = key_value

st.set_page_config(
    page_title="J-POP JLPT 학습 도우미",
    page_icon="🎵",
    layout="wide",
)

# ── 사이드바: AI 제공자 선택 ──────────────────────────────────────────────────

with st.sidebar:
    st.subheader("⚙️ AI 설정")
    provider = st.radio(
        "AI 제공자 선택",
        options=["Google Gemini (무료)", "Claude (유료)"],
        index=0,
    )

    if provider == "Google Gemini (무료)":
        from gemini_analyzer import analyze_lyrics

        st.markdown("**Google Gemini** — 무료 (일 1,500회)")
        st.markdown("[API Key 발급받기](https://aistudio.google.com/app/apikey)")

        saved_google_key = os.getenv("GOOGLE_API_KEY", "")
        google_key_input = st.text_input(
            "Google API Key",
            value=st.session_state.get("google_api_key", saved_google_key),
            type="password",
            placeholder="AIzaSy...",
        )
        if google_key_input:
            st.session_state["google_api_key"] = google_key_input

        if google_key_input and google_key_input != saved_google_key:
            if st.button("💾 저장 (.env에 기록)", use_container_width=True):
                _save_to_env("GOOGLE_API_KEY", google_key_input)
                st.success("저장 완료! 다음 실행부터 자동 입력됩니다.")

        if not google_key_input:
            st.warning("API Key를 입력하세요.")

    else:
        from claude_analyzer import analyze_lyrics

        st.markdown("**Claude** — 유료 (Anthropic)")
        st.markdown("[API Key 발급받기](https://console.anthropic.com/settings/keys)")

        saved_claude_key = os.getenv("ANTHROPIC_API_KEY", "")
        claude_key_input = st.text_input(
            "Anthropic API Key",
            value=st.session_state.get("claude_api_key", saved_claude_key),
            type="password",
            placeholder="sk-ant-...",
        )
        if claude_key_input:
            st.session_state["claude_api_key"] = claude_key_input

        if claude_key_input and claude_key_input != saved_claude_key:
            if st.button("💾 저장 (.env에 기록)", use_container_width=True):
                _save_to_env("ANTHROPIC_API_KEY", claude_key_input)
                st.success("저장 완료!")

        if not claude_key_input:
            st.warning("API Key를 입력하세요.")

    st.divider()
    st.subheader("🗒️ Notion 설정")
    saved_notion_key = os.getenv("NOTION_API_KEY", "")
    saved_notion_page = os.getenv("NOTION_PARENT_PAGE_ID", "")

    notion_key_input = st.text_input(
        "Notion API Key",
        value=st.session_state.get("notion_api_key", saved_notion_key),
        type="password",
        placeholder="secret_...",
    )
    notion_page_input = st.text_input(
        "Notion 페이지 ID",
        value=st.session_state.get("notion_page_id", saved_notion_page),
        placeholder="페이지 ID 붙여넣기",
    )
    if notion_key_input:
        st.session_state["notion_api_key"] = notion_key_input
    if notion_page_input:
        st.session_state["notion_page_id"] = notion_page_input

st.title("🎵 J-POP JLPT 학습 도우미")
st.caption("J-POP 가사로 JLPT 학습 자료를 자동 생성합니다.")


# ── 입력 폼 ──────────────────────────────────────────────────────────────────

with st.form("analysis_form"):
    col1, col2 = st.columns(2)
    with col1:
        song_title = st.text_input("곡명 *", placeholder="예) 紅蓮華")
    with col2:
        artist = st.text_input("가수 *", placeholder="예) LiSA")
    lyrics = st.text_area(
        "가사 붙여넣기 *",
        height=300,
        placeholder="일본어 가사를 여기에 붙여넣으세요.",
    )
    submitted = st.form_submit_button("🔍 분석하기", use_container_width=True)


# ── 분석 실행 ────────────────────────────────────────────────────────────────

if submitted:
    if not song_title.strip() or not artist.strip() or not lyrics.strip():
        st.error("곡명, 가수, 가사를 모두 입력해주세요.")
        st.stop()

    if provider.startswith("Google"):
        runtime_key = st.session_state.get("google_api_key", "")
        provider_label = "Google Gemini"
        key_hint = "Google API Key"
    else:
        runtime_key = st.session_state.get("claude_api_key", "")
        provider_label = "Claude"
        key_hint = "Anthropic API Key"

    if not runtime_key:
        st.error(f"❌ 사이드바에서 {key_hint}를 먼저 입력해주세요.")
        st.stop()

    with st.spinner(f"⏳ {provider_label}가 가사를 분석하고 있습니다... (30~60초 소요)"):
        try:
            result = analyze_lyrics(song_title.strip(), artist.strip(), lyrics.strip(), api_key=runtime_key)
            st.session_state["analysis"] = result
            st.session_state["song_title"] = song_title.strip()
            st.session_state["artist"] = artist.strip()
        except ValueError as e:
            st.error(f"❌ 입력 오류: {e}")
            st.stop()
        except Exception as e:
            st.error(f"❌ API 오류: {e}\n{key_hint}가 올바른지 확인하거나 잠시 후 다시 시도해주세요.")
            st.stop()


# ── 결과 표시 ────────────────────────────────────────────────────────────────

if "analysis" not in st.session_state:
    st.stop()

analysis = st.session_state["analysis"]
song_title_display = st.session_state.get("song_title", "")
artist_display = st.session_state.get("artist", "")
song_info = analysis.get("song_info", {})

st.markdown(f"### 🎵 {song_title_display} — {artist_display}")
st.caption(f"전체 레벨 추정: **{song_info.get('overall_jlpt_estimate', '')}**")

lines_data = analysis.get("lines", [])
vocab_data = analysis.get("vocabulary", [])
grammar_data = analysis.get("grammar_points", [])
kanji_data = analysis.get("kanji_list", [])

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 가사 줄 수", len([l for l in lines_data if not l.get("is_section_break")]))
col2.metric("📚 단어 수", len(vocab_data))
col3.metric("📐 문법 수", len(grammar_data))
col4.metric("🈶 한자 수", len(kanji_data))

tabs = st.tabs(TAB_NAMES)


# ── 탭 1: 전체 가사 ───────────────────────────────────────────────────────────

with tabs[0]:
    st.subheader("📖 전체 가사 — 원문·음차·해석")
    rows = []
    for line in lines_data:
        if line.get("is_section_break"):
            rows.append({"📄 일본어 원문": "", "🔤 한국어 음차": "", "🇰🇷 한국어 해석": ""})
        else:
            rows.append({
                "📄 일본어 원문": line.get("japanese", ""),
                "🔤 한국어 음차": line.get("korean_phonetic", ""),
                "🇰🇷 한국어 해석": line.get("korean_translation", ""),
            })
    if rows:
        df_lyrics = pd.DataFrame(rows)
        st.dataframe(df_lyrics, use_container_width=True, hide_index=True)


# ── 탭 2: 단어장 ─────────────────────────────────────────────────────────────

with tabs[1]:
    st.subheader("📚 단어장")

    filter_col, search_col = st.columns([3, 2])
    with filter_col:
        level_filter = st.radio(
            "JLPT 레벨 필터",
            options=["전체"] + JLPT_LEVELS,
            horizontal=True,
            label_visibility="collapsed",
        )
    with search_col:
        search_word = st.text_input("🔍 단어 검색", placeholder="단어 검색...")

    filtered_vocab = vocab_data
    if level_filter != "전체":
        lvl = "unknown" if level_filter == "미분류" else level_filter
        filtered_vocab = [v for v in filtered_vocab if v.get("jlpt_level") == lvl]
    if search_word.strip():
        q = search_word.strip().lower()
        filtered_vocab = [
            v for v in filtered_vocab
            if q in v.get("word", "").lower()
            or q in v.get("reading", "").lower()
            or q in v.get("meaning_korean", "").lower()
        ]

    st.caption(f"총 {len(filtered_vocab)}개")

    for v in filtered_vocab:
        level = v.get("jlpt_level", "unknown")
        badge = jlpt_badge_html(level)
        poly = " ⚡다의어" if v.get("is_polysemous") else ""
        label = f"{v.get('word', '')} [{v.get('reading', '')}] — {v.get('meaning_korean', '')}{poly}"

        with st.expander(label):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                st.markdown(f"**한국어 음차:** {v.get('korean_phonetic', '')}")
                st.markdown(f"**JLPT:** {badge}", unsafe_allow_html=True)
            with c2:
                ex_line = v.get("example_line_number", 0)
                ex_text = ""
                if ex_line and ex_line <= len(lines_data):
                    ex_text = lines_data[ex_line - 1].get("japanese", "")
                if ex_text:
                    st.markdown(f"**가사 예문:** _{ex_text}_")
            with c3:
                collocations = v.get("collocations", [])
                if collocations:
                    st.markdown(f"**콜로케이션:** {' / '.join(collocations)}")
            note = v.get("colloquial_note")
            if note:
                st.warning(f"⚠️ 구어체 주의: {note}")


# ── 탭 3: 문법정리 ───────────────────────────────────────────────────────────

with tabs[2]:
    st.subheader("📐 문법정리")
    for g in grammar_data:
        level = g.get("jlpt_level", "unknown")
        badge = jlpt_badge_html(level)
        tags = " ".join([f"`[{t}]`" for t in g.get("function_tags", [])])
        label = f"{g.get('pattern', '')} — {g.get('explanation_korean', '')}"

        with st.expander(label):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**한국어 음차:** {g.get('pattern_korean_phonetic', '')}")
                st.markdown(f"**JLPT:** {badge}", unsafe_allow_html=True)
                if tags:
                    st.markdown(f"**기능 태그:** {tags}")
            with c2:
                ex = g.get("example_japanese")
                if ex:
                    st.markdown(f"**예문:** _{ex}_")
                standard = g.get("standard_form")
                if standard:
                    st.info(f"→ 표준형: **{standard}**")
            confusion = g.get("confusion_note")
            if confusion:
                st.warning(f"📌 혼동 주의: {confusion}")


# ── 탭 4: 한자 목록 ──────────────────────────────────────────────────────────

with tabs[3]:
    st.subheader("🈶 한자 목록 (JLPT N1~N5 등재 한자)")
    if kanji_data:
        rows_k = []
        for k in kanji_data:
            level = k.get("jlpt_level", "N5")
            badge_html = jlpt_badge_html(level)
            star = "★" if k.get("is_key_kanji") else ""
            example_words = " / ".join(k.get("example_words", [])[:3])
            rows_k.append({
                "한자": k.get("kanji", ""),
                "음독(音読み)": k.get("reading_on", ""),
                "훈독(訓読み)": k.get("reading_kun", ""),
                "뜻": k.get("meaning_korean", ""),
                "빈출어": example_words,
                "JLPT": level,
                "★": star,
            })
        df_kanji = pd.DataFrame(rows_k)
        st.dataframe(df_kanji, use_container_width=True, hide_index=True)
        st.caption("★ = 해당 레벨 중요 한자")
    else:
        st.info("한자 데이터가 없습니다.")


# ── 탭 5: 회화 실습 ──────────────────────────────────────────────────────────

with tabs[4]:
    st.subheader("💬 간단 회화 실습")
    conversation = analysis.get("conversation_practice", [])
    if conversation:
        for i, practice in enumerate(conversation, 1):
            with st.expander(f"📍 상황 {i}: {practice.get('situation', '')}", expanded=(i == 1)):
                for turn in practice.get("dialogue", []):
                    speaker = turn.get("speaker", "A")
                    bg = SPEAKER_COLORS.get(speaker, "#F2F3F4")
                    icon = "🔵" if speaker == "A" else "⚫"
                    used = ", ".join(turn.get("used_items", []))
                    html = f"""
<div style="background:{bg};padding:12px 16px;border-radius:8px;margin:6px 0;line-height:1.8;">
<strong>{icon} {speaker}</strong><br>
<span style="font-size:15px;">{turn.get('japanese','')}</span><br>
<span style="color:#626567;font-size:13px;">({turn.get('korean_phonetic','')})</span><br>
<span style="font-size:14px;">{turn.get('korean_translation','')}</span><br>
<span style="font-size:12px;color:#1A5276;">✨ {used}</span>
</div>"""
                    st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("회화 데이터가 없습니다.")


# ── 탭 6: JLPT 분포 ──────────────────────────────────────────────────────────

with tabs[5]:
    st.subheader("📊 JLPT 레벨 분포")
    distribution = analysis.get("jlpt_distribution", {})

    vocab_dist = {lvl: distribution.get(lvl, 0) for lvl in ["N5", "N4", "N3", "N2", "N1", "unknown"]}
    df_dist = pd.DataFrame(
        {"단어 수": list(vocab_dist.values())},
        index=list(vocab_dist.keys()),
    )
    st.bar_chart(df_dist)

    total = sum(vocab_dist.values())
    if total > 0:
        dist_text = "  |  ".join(
            [f"**{lvl}**: {cnt}개 ({cnt/total*100:.0f}%)" for lvl, cnt in vocab_dist.items() if cnt > 0]
        )
        st.markdown(dist_text)

    st.caption(f"전체 레벨 추정: **{song_info.get('overall_jlpt_estimate', '')}**")


# ── 탭 7: 학습 포인트 ────────────────────────────────────────────────────────

with tabs[6]:
    st.subheader("🎯 시험 학습 포인트")
    study_summary = analysis.get("study_summary", "")
    if study_summary:
        st.info(study_summary)
    else:
        st.info("학습 포인트 데이터가 없습니다.")


# ── 내보내기 섹션 ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("📤 내보내기")
exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    st.markdown("**🗒️ Notion으로 내보내기**")
    runtime_notion_key = st.session_state.get("notion_api_key", "")
    runtime_notion_page = st.session_state.get("notion_page_id", "")
    if runtime_notion_key and runtime_notion_page:
        if st.button("Notion 페이지 생성하기", use_container_width=True):
            page_title = f"{song_title_display} - {artist_display}"
            with st.spinner("Notion 페이지를 생성하고 있습니다..."):
                try:
                    url = export_to_notion(analysis, page_title, api_key=runtime_notion_key, parent_id=runtime_notion_page)
                    st.success("✅ Notion 페이지 생성 완료!")
                    st.markdown(f"🔗 [페이지 열기]({url})")
                except Exception as e:
                    st.error(f"❌ Notion 내보내기 오류: {e}")
    else:
        st.warning("⚠️ 사이드바에서 Notion API Key와 페이지 ID를 입력하세요.")

with exp_col2:
    st.markdown("**📄 Word 파일 다운로드** (Google Docs 업로드용)")
    try:
        docx_bytes = export_to_docx(analysis, song_title_display)
        safe_title = "".join(c for c in song_title_display if c.isalnum() or c in " _-")
        st.download_button(
            label=".docx 다운로드",
            data=docx_bytes,
            file_name=f"{safe_title or 'jpop_jlpt'}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"❌ Word 파일 생성 오류: {e}")
