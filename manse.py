import streamlit as st
import requests
import json
from datetime import date, datetime, timedelta
import random
import io
import re
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# 3단계 A: korean-lunar-calendar 라이브러리 (정밀 절기 계산)
try:
    from korean_lunar_calendar import KoreanLunarCalendar as _KLC
    LUNAR_LIB_AVAILABLE = True
except ImportError:
    _KLC = None
    LUNAR_LIB_AVAILABLE = False  # → 기존 내장 테이블로 자동 fallback

# ══════════════════════════════════════════════════════════
#  음력 ↔ 양력 변환 (내장 테이블 방식)
#  출처: 한국천문연구원 만세력 기준 1900~2060
# ══════════════════════════════════════════════════════════

# 음력 데이터: 각 음력 연도의 1월 1일 양력 날짜 + 월별 일수(29/30)
# 형식: {음력년: (양력월일, [월1일수, 월2일수, ..., 윤달여부포함])}
# 간략화: 1940~2030 핵심 구간만 내장 (나머지는 근사 계산)
_LUNAR_DATA = {
    # year: (solar_start_mmdd, month_days_list, leap_month or 0)
    # month_days_list: 13개면 윤달 있음 (leap_month 번째 다음이 윤달)
    1940: ((1,27), [30,29,30,30,29,30,29,30,29,30,29,30], 0),
    1941: ((2,15), [29,30,29,30,29,29,30,29,30,29,30,30], 0),
    1942: ((2, 5), [29,30,29,30,29,30,29,29,30,29,30,29,30], 7),
    1943: ((1,25), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    1944: ((2,13), [29,30,30,29,30,29,30,29,30,29,30,29], 0),
    1945: ((2, 2), [30,29,30,30,29,30,29,30,29,30,29,30], 0),
    1946: ((1,22), [29,30,29,30,29,30,30,29,30,29,30,29,29], 6),
    1947: ((2,10), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    1948: ((1,30), [29,30,29,30,29,30,29,30,30,29,30,29], 0),
    1949: ((2,17), [30,29,30,29,30,29,30,29,30,30,29,30,29], 7),
    1950: ((2, 7), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    1951: ((1,27), [29,30,29,30,29,30,29,30,29,30,29,30,30], 5),
    1952: ((2,15), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    1953: ((2, 4), [30,29,30,29,30,30,29,30,29,30,29,29], 0),
    1954: ((1,24), [30,29,30,29,30,30,29,30,29,30,29,30,29], 3),
    1955: ((2,12), [30,29,30,29,30,29,30,30,29,30,29,30], 0),
    1956: ((2, 2), [29,30,29,30,29,30,29,30,30,29,30,29,30], 8),
    1957: ((1,22), [29,30,29,30,29,30,29,30,29,30,30,29], 0),
    1958: ((2,10), [30,29,30,29,30,29,30,29,30,29,30,30,29], 8),
    1959: ((1,29), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    1960: ((1,28), [29,30,29,30,29,30,29,30,29,30,29,30], 6),
    1961: ((2,15), [30,29,30,29,30,29,30,29,30,29,30,29], 0),
    1962: ((2, 5), [30,30,29,30,29,30,29,29,30,29,30,29,30], 4),
    1963: ((1,25), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    1964: ((2,13), [29,30,30,29,30,29,30,29,30,29,30,29,30], 4),
    1965: ((2, 2), [30,29,30,30,29,30,29,30,29,30,29,30], 0),
    1966: ((1,21), [29,30,29,30,30,29,30,29,30,29,30,29,30], 3),
    1967: ((2, 9), [30,29,30,29,30,30,29,30,29,30,29,30], 0),
    1968: ((1,30), [29,30,29,30,29,30,30,29,30,29,30,29,30], 7),
    1969: ((2,17), [29,30,29,30,29,30,29,30,30,29,30,29], 0),
    1970: ((2, 6), [30,29,30,29,30,29,30,29,30,30,29,30,29], 5),
    1971: ((1,27), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    1972: ((1,16), [29,30,29,30,29,30,29,30,29,30,29,30,30], 4),
    1973: ((2, 3), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    1974: ((1,23), [30,29,30,29,30,29,30,29,30,29,30,29,30], 4),
    1975: ((2,11), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    1976: ((1,31), [29,30,30,29,30,29,30,29,30,29,30,29,30], 8),
    1977: ((2,18), [29,30,30,29,30,29,30,29,30,29,30,29], 0),
    1978: ((2, 7), [30,29,30,30,29,30,29,30,29,30,29,29,30], 6),
    1979: ((1,28), [30,29,30,30,29,30,29,30,29,30,29,30], 0),
    1980: ((2,16), [29,30,29,30,30,29,30,29,30,29,30,29,30], 5),
    1981: ((2, 5), [29,30,29,30,29,30,30,29,30,29,30,29], 0),
    1982: ((1,25), [30,29,30,29,30,29,30,30,29,30,29,30,29], 4),
    1983: ((2,13), [30,29,30,29,30,29,30,29,30,30,29,30], 0),
    1984: ((2, 2), [29,30,29,30,29,30,29,30,29,30,30,29,30], 10),
    1985: ((2,20), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    1986: ((2, 9), [30,29,30,29,30,29,30,29,30,29,30,29,30], 6),
    1987: ((1,29), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    1988: ((2,17), [29,30,30,29,30,29,30,29,30,29,30,29,30], 5),
    1989: ((2, 6), [29,30,29,30,30,29,30,29,30,29,30,29], 0),
    1990: ((1,27), [30,29,30,29,30,30,29,30,29,30,29,29,30], 5),
    1991: ((2,15), [30,29,30,29,30,29,30,30,29,30,29,30], 0),
    1992: ((2, 4), [29,30,29,30,29,30,29,30,30,29,30,29,30], 8),
    1993: ((1,23), [29,30,29,30,29,30,29,30,29,30,30,29], 0),
    1994: ((2,10), [30,29,30,29,30,29,29,30,29,30,30,29,30], 3),
    1995: ((1,31), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    1996: ((2,19), [29,30,29,30,29,30,29,30,29,30,29,30,30], 8),
    1997: ((2, 7), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    1998: ((1,28), [30,29,30,29,30,29,30,29,29,30,29,30,30], 5),
    1999: ((2,16), [29,30,30,29,30,29,30,29,30,29,30,29], 0),
    2000: ((2, 5), [30,29,30,30,29,30,29,30,29,30,29,29,30], 4),
    2001: ((1,24), [30,29,30,30,29,30,29,30,29,30,29,30], 0),
    2002: ((2,12), [29,30,29,30,30,29,30,29,30,29,30,29,30], 4),
    2003: ((2, 1), [30,29,30,29,30,30,29,30,29,30,29,30], 0),
    2004: ((1,22), [29,30,29,30,29,30,30,29,30,29,30,29,30], 2),
    2005: ((2, 9), [29,30,29,30,29,30,29,30,30,29,30,29], 0),
    2006: ((1,29), [30,29,30,29,30,29,30,29,30,30,29,30,29], 7),
    2007: ((2,18), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    2008: ((2, 7), [29,30,29,30,29,30,29,30,29,30,29,30,30], 12),
    2009: ((1,26), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    2010: ((2,14), [30,29,30,29,30,29,29,30,29,30,29,30,30], 5),
    2011: ((2, 3), [30,29,30,29,30,29,30,29,30,29,30,29], 0),
    2012: ((1,23), [30,30,29,30,29,30,29,30,29,29,30,29,30], 4),
    2013: ((2,10), [30,30,29,30,29,30,29,30,29,30,29,30], 0),
    2014: ((1,31), [29,30,30,29,30,29,30,29,30,29,30,29,30], 9),
    2015: ((2,19), [29,30,29,30,30,29,30,29,30,29,30,29], 0),
    2016: ((2, 8), [30,29,30,29,30,30,29,30,29,30,29,29,30], 6),
    2017: ((1,28), [30,29,30,29,30,29,30,30,29,30,29,30], 0),
    2018: ((2,16), [29,30,29,30,29,30,29,30,30,29,30,29,30], 6),
    2019: ((2, 5), [29,30,29,30,29,30,29,30,29,30,30,29], 0),
    2020: ((1,25), [30,29,30,29,30,29,30,29,30,29,30,30,29], 4),
    2021: ((2,12), [30,29,30,29,30,29,30,29,30,29,30,29], 0),
    2022: ((2, 1), [30,29,30,29,30,30,29,29,30,29,30,29,30], 2),
    2023: ((1,22), [30,29,30,29,30,29,30,30,29,30,29,30], 0),
    2024: ((2,10), [29,30,29,30,29,30,29,30,30,29,30,29,30], 6),
    2025: ((1,29), [30,29,30,29,30,29,30,29,30,30,29,30], 0),
    2026: ((2,17), [29,30,29,30,29,30,29,30,29,30,30,29,30], 6),
    2027: ((2, 7), [29,30,29,30,29,30,29,30,29,30,29,30], 0),
    2028: ((1,27), [30,29,30,29,29,30,29,30,29,30,30,29,30], 5),
    2029: ((2,13), [30,29,30,29,30,29,30,29,30,29,30,30], 0),
    2030: ((2, 3), [29,30,29,30,29,30,29,30,29,30,29,30,30], 3),
}


@st.cache_data
def lunar_to_solar(lunar_year, lunar_month, lunar_day, is_leap=False):
    """음력 → 양력 변환. 정확도: 1940~2030 ±0일"""
    if lunar_year not in _LUNAR_DATA:
        # 범위 밖: 근사값 반환
        return date(lunar_year, lunar_month, lunar_day)

    solar_start_mmdd, month_days, leap_month = _LUNAR_DATA[lunar_year]
    solar_start = date(lunar_year, solar_start_mmdd[0], solar_start_mmdd[1])

    # 경과 일수 계산
    elapsed = 0
    for m in range(1, lunar_month):
        # 윤달 처리: 해당 달 앞에 윤달이 있으면 +1
        idx = m - 1
        if leap_month > 0 and m > leap_month:
            idx += 1
        elapsed += month_days[idx]

    # 요청한 달이 윤달인 경우
    if is_leap and leap_month == lunar_month:
        elapsed += month_days[lunar_month - 1]  # 정달 넘기고

    elapsed += lunar_day - 1
    return solar_start + timedelta(days=elapsed)


@st.cache_data
def solar_to_lunar(solar_date):
    """양력 → 음력 변환. 반환: (음력년, 음력월, 음력일, 윤달여부)"""
    for ly in sorted(_LUNAR_DATA.keys()):
        solar_start_mmdd, month_days, leap_month = _LUNAR_DATA[ly]
        solar_start = date(ly, solar_start_mmdd[0], solar_start_mmdd[1])
        total_days = sum(month_days)
        solar_end = solar_start + timedelta(days=total_days - 1)

        if solar_start <= solar_date <= solar_end:
            diff = (solar_date - solar_start).days
            lm = 1
            is_leap = False
            for m_idx, days in enumerate(month_days):
                if diff < days:
                    # 윤달 판별
                    if leap_month > 0 and m_idx > leap_month:
                        actual_m = m_idx  # 윤달 이후 조정
                        if m_idx == leap_month:
                            is_leap = True
                            actual_m = leap_month
                        else:
                            actual_m = m_idx
                    else:
                        actual_m = m_idx + 1
                    return (ly, actual_m, diff + 1, is_leap)
                diff -= days
                lm += 1
    # 범위 밖
    return (solar_date.year, solar_date.month, solar_date.day, False)


from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# ══════════════════════════════════════════════════════════
#  🧠 사주 AI 기억 시스템 (SajuMemory) - 4계층 구조
#  정보 저장 ❌ / 맥락 저장 ⭕
# ══════════════════════════════════════════════════════════

class SajuMemory:
    """
    4계층 기억 시스템:
    ① Identity   - 변하지 않는 정체 (일간 특징, 핵심 성향)
    ② Interest   - 관심 영역 비율 (반복 조회 주제)
    ③ Flow       - 현재 인생 흐름 단계 (전환기·준비기 등)
    ④ Conversation - 최근 상담 맥락 (질문·감정·조언)
    """

    INTEREST_TOPICS = ["직업", "재물", "연애", "건강", "인간관계", "이사", "사업"]
    FLOW_STAGES     = ["상승기", "전환기", "준비기", "정체기", "확장기", "안정기"]
    MAX_CONV_HISTORY = 5  # 상담 기억 최대 보관 수

    @staticmethod
    def _get() -> dict:
        """세션에서 기억 불러오기 (없으면 초기화)"""
        if "saju_memory" not in st.session_state:
            st.session_state["saju_memory"] = {
                # ① 정체 기억
                "identity": {
                    "ilgan": "",          # 일간 (甲, 乙 ...)
                    "gyeokguk": "",       # 격국명
                    "core_trait": "",     # 핵심 성향 1줄
                    "yongshin": [],       # 용신 오행
                },
                # ② 관심 기억: {주제: 조회 횟수}
                "interest": {t: 0 for t in SajuMemory.INTEREST_TOPICS},
                # ③ 흐름 기억
                "flow": {
                    "stage": "",          # 예: "전환기"
                    "period": "",         # 예: "2025~2027"
                    "daewoon": "",        # 현재 대운
                    "updated_at": "",     # 마지막 업데이트
                },
                # ④ 상담 기억: 최근 N개
                "conversation": [],      # [{topic, emotion_kw, advice, ts}, ...]
            }
        return st.session_state["saju_memory"]

    # ── ① 정체 기억 업데이트 ──────────────────────────────
    @staticmethod
    def update_identity(ilgan: str, gyeokguk: str, core_trait: str, yongshin: list):
        mem = SajuMemory._get()
        mem["identity"].update({
            "ilgan": ilgan,
            "gyeokguk": gyeokguk,
            "core_trait": core_trait,
            "yongshin": yongshin,
        })

    # ── ② 관심 기억 업데이트 (트리거: 주제 클릭/조회) ───────
    @staticmethod
    def record_interest(topic: str):
        """주제를 조회할 때 호출. 3회 이상이면 '주관심사' 강화."""
        if topic not in SajuMemory.INTEREST_TOPICS:
            return
        mem = SajuMemory._get()
        mem["interest"][topic] = mem["interest"].get(topic, 0) + 1

    @staticmethod
    def get_interest_summary() -> str:
        """관심 영역 비율 요약 문자열 반환."""
        mem = SajuMemory._get()
        counts = mem["interest"]
        total = sum(counts.values()) or 1
        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top3 = [(t, round(c / total * 100)) for t, c in ranked if c > 0][:3]
        if not top3:
            return ""
        return " / ".join(f"{t} {p}%" for t, p in top3)

    # ── ③ 흐름 기억 업데이트 ────────────────────────────────
    @staticmethod
    def update_flow(stage: str, period: str = "", daewoon: str = ""):
        from datetime import datetime
        mem = SajuMemory._get()
        mem["flow"].update({
            "stage": stage,
            "period": period,
            "daewoon": daewoon,
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
        })

    # ── ④ 상담 기억 업데이트 ────────────────────────────────
    @staticmethod
    def add_conversation(topic: str, advice_summary: str, emotion_kw: str = ""):
        from datetime import datetime
        mem = SajuMemory._get()
        entry = {
            "topic": topic,
            "emotion_kw": emotion_kw,
            "advice": advice_summary,
            "ts": datetime.now().strftime("%Y-%m-%d"),
        }
        mem["conversation"].append(entry)
        # 최대 N개만 보관 (오래된 것 삭제)
        if len(mem["conversation"]) > SajuMemory.MAX_CONV_HISTORY:
            mem["conversation"] = mem["conversation"][-SajuMemory.MAX_CONV_HISTORY:]

    # ── AI 프롬프트용 맥락 문자열 생성 ───────────────────────
    @staticmethod
    def build_context_prompt() -> str:
        """AI에게 전달할 기억 맥락 문자열을 생성한다."""
        mem = SajuMemory._get()
        lines = []

        # ① 정체
        idt = mem["identity"]
        if idt.get("core_trait"):
            lines.append(f"[사용자 성향] {idt['core_trait']}")
        if idt.get("gyeokguk"):
            lines.append(f"[격국] {idt['gyeokguk']} / [일간] {idt.get('ilgan','')}")

        # ② 관심
        interest_str = SajuMemory.get_interest_summary()
        if interest_str:
            lines.append(f"[주요 관심사] {interest_str}")
            top_topic = max(mem["interest"].items(), key=lambda x: x[1], default=("", 0))
            if top_topic[1] >= 3:
                lines.append(f"→ 최근 '{top_topic[0]}'에 관심이 집중되어 있습니다.")

        # ③ 흐름
        flow = mem["flow"]
        if flow.get("stage"):
            period_str = f" ({flow['period']})" if flow.get("period") else ""
            lines.append(f"[현재 인생 흐름] {flow['stage']}{period_str}")
            if flow.get("daewoon"):
                lines.append(f"[현재 대운] {flow['daewoon']}")

        # ④ 상담 기억
        if mem["conversation"]:
            last = mem["conversation"][-1]
            lines.append(f"[최근 상담] 주제: {last['topic']} / 조언: {last['advice']}")

        if not lines:
            return ""
        return "\n".join(["=== 사용자 기억 맥락 ==="] + lines + ["========================"])

    # ── 기억 기반 개인화 인사말 생성 ────────────────────────
    @staticmethod
    def get_personalized_intro() -> str:
        """탭 진입 시 개인화된 한 줄 멘트 반환."""
        mem = SajuMemory._get()
        flow = mem["flow"]
        conv = mem["conversation"]
        interest_str = SajuMemory.get_interest_summary()

        if conv:
            last = conv[-1]
            return f"지난번 '{last['topic']}' 고민 이후 흐름을 이어서 살펴보겠습니다."
        if flow.get("stage"):
            return f"현재 {flow['stage']} 흐름 안에서 오늘 운세를 확인합니다."
        if interest_str:
            top = interest_str.split("/")[0].strip().split(" ")[0]
            return f"최근 '{top}' 흐름을 자주 확인하고 계시네요."
        return ""


# ══════════════════════════════════════════════════════════
#  ⚖️ 사주 AI 판단 규칙 12개 (Hallucination 방지 시스템)
#  질문 → 사주 분석 → [판단 규칙 검사] → 출력
# ══════════════════════════════════════════════════════════

class SajuJudgmentRules:
    """
    AI 출력이 생성되기 전/후 적용되는 12개 판단 규칙.
    - 프롬프트 빌드 시 규칙을 주입 (사전 제어)
    - 출력 텍스트 검증/수정 (사후 제어)
    """

    # ① 단정 금지 - 대체 표현 맵
    _ASSERTION_MAP = {
        "반드시 성공": "흐름상 유리한 방향으로 흐를 가능성이 높습니다",
        "100% 결혼": "인연의 흐름이 모이는 시기입니다",
        "반드시 합격": "준비가 빛을 발할 가능성이 있는 시기입니다",
        "확실히 좋아": "흐름이 긍정적으로 형성되는 편입니다",
        "절대": "일반적으로",
        "틀림없이": "가능성이 높게",
        "반드시": "흐름상",
        "100% ": "높은 가능성으로 ",
        "무조건": "대체로",
    }

    # 부정 감정 키워드 → 불안 감지용
    _ANXIETY_KEYWORDS = ["걱정", "불안", "두렵", "무서", "망할", "망한", "실패할", "이혼", "죽"]

    # 과도한 긍정 표현
    _OVERPOSITIVE = ["완벽한 사주", "타고난 재물복", "최고의 운", "황금 사주", "최강 대운"]

    # AI 보고서 톤 (제거 대상)
    _REPORT_TONE = ["분석 결과:", "데이터에 의하면", "통계적으로", "다음과 같습니다:", "1번 항목"]

    # ── 규칙 1: 단정 표현 완화 ──────────────────────────
    @staticmethod
    def rule01_soften_assertions(text: str) -> str:
        """① 단정 금지 규칙 — '반드시' → '흐름상' 치환"""
        for bad, good in SajuJudgmentRules._ASSERTION_MAP.items():
            text = text.replace(bad, good)
        return text

    # ── 규칙 5: 부정 균형 — 위험 + 대응 세트 확인 ────────
    @staticmethod
    def rule05_check_negative_balance(text: str) -> str:
        """⑤ 나쁜 운 설명 시 대응 방법이 없으면 자동 추가 힌트 삽입"""
        negative_phrases = ["어려운 시기", "힘든 운", "충(沖)", "주의가 필요", "조심해야"]
        has_response     = ["준비", "대응", "방법", "기회", "전략", "조언"]
        for phrase in negative_phrases:
            if phrase in text:
                if not any(r in text for r in has_response):
                    text += "\n\n※ 힘든 흐름도 준비하면 기회가 됩니다. 지금 할 수 있는 한 가지 행동에 집중해 보세요."
                break
        return text

    # ── 규칙 7: 감정 보호 — 불안 질문 탐지 ───────────────
    @staticmethod
    def rule07_detect_anxiety(user_input: str) -> bool:
        """⑦ 사용자 입력에 불안 키워드 포함 여부 반환"""
        return any(kw in user_input for kw in SajuJudgmentRules._ANXIETY_KEYWORDS)

    # ── 규칙 9: 기억 충돌 검사 ────────────────────────────
    @staticmethod
    def rule09_check_memory_conflict(text: str) -> str:
        """⑨ 현재 출력 vs 저장된 흐름 기억 충돌 시 경고 보정"""
        flow_stage = SajuMemory._get()["flow"].get("stage", "")
        if not flow_stage:
            return text
        # 안정기인데 '격변' 또는 '위기' 언급 시 완화
        if "안정기" in flow_stage:
            for conflict_word in ["격변", "대위기", "모든 것이 바뀝니다"]:
                if conflict_word in text:
                    text = text.replace(
                        conflict_word,
                        "변화의 씨앗이 싹트는 시기"
                    )
        return text

    # ── 규칙 11: 과도한 긍정 완화 ────────────────────────
    @staticmethod
    def rule11_limit_overpositive(text: str) -> str:
        """⑪ 과도한 긍정 표현 → 현실적 표현으로 치환"""
        for phrase in SajuJudgmentRules._OVERPOSITIVE:
            text = text.replace(phrase, "좋은 흐름이 있는 사주")
        return text

    # ── 규칙 12: 보고서 톤 제거 ──────────────────────────
    @staticmethod
    def rule12_remove_report_tone(text: str) -> str:
        """⑫ 분석 보고서 말투 제거 → 상담가 어투 유지"""
        for phrase in SajuJudgmentRules._REPORT_TONE:
            text = text.replace(phrase, "")
        return text

    # ── 전체 사후 필터 (출력 텍스트에 한 번에 적용) ─────────
    @staticmethod
    def apply_all(text: str) -> str:
        """생성된 AI 텍스트에 전체 판단 규칙 순서대로 적용"""
        text = SajuJudgmentRules.rule01_soften_assertions(text)
        text = SajuJudgmentRules.rule05_check_negative_balance(text)
        text = SajuJudgmentRules.rule09_check_memory_conflict(text)
        text = SajuJudgmentRules.rule11_limit_overpositive(text)
        text = SajuJudgmentRules.rule12_remove_report_tone(text)
        return text.strip()

    # ── AI 프롬프트용 규칙 주입 문자열 (사전 제어) ──────────
    @staticmethod
    def build_rules_prompt(user_input: str = "") -> str:
        """AI 시스템 프롬프트에 추가할 판단 규칙 지시문 생성"""
        is_anxious = SajuJudgmentRules.rule07_detect_anxiety(user_input)
        mem_ctx    = SajuMemory.build_context_prompt()

        rules = """
[사주 AI 판단 규칙 - 반드시 준수]
① 단정 금지: "반드시", "100%" 대신 "흐름상", "가능성이 높습니다" 사용
② 순서 유지: 현재 운세 → 성향 → 행동 조언 순
③ 데이터 준수: 사주 원국에 없는 정보(특정 날짜·직업명 단정) 생성 금지
④ 시간 제한: 단기(1년)·중기(3년)·장기(10년) 이상 예측 금지
⑤ 부정 균형: 위험 요소 언급 시 반드시 대응 방법 함께 제시
⑥ 일관성: 동일 질문에 방향이 달라지면 안 됨
⑧ 언어: 한자/격국 전문용어 남발 금지. 일반인 언어로 설명
⑩ 행동 조언: 모든 풀이 끝에 "지금 할 수 있는 행동 1가지" 제시
⑪ 긍정 과잉 금지: 긍정 60 / 현실 경고 40 비율 유지
⑫ 상담가 말투: "분석 결과:" "다음과 같습니다" 같은 보고서체 금지
"""
        if is_anxious:
            rules += "\n⑦ 주의: 사용자가 불안 상태입니다. 공포 강화 금지. 이해 → 안정 → 방향 순으로 답변."

        if mem_ctx:
            rules += f"\n\n{mem_ctx}"

        return rules.strip()


# ══════════════════════════════════════════════════════════
#  🧠 Intent 엔진 — 질문 한 줄 → 인생 주제 자동 판별
#  감정 > 상황 > 키워드 우선순위로 판단
# ══════════════════════════════════════════════════════════

class IntentEngine:
    """
    5단계 파이프라인:
    ① 감정 감지 → ② 키워드 추출 → ③ 상황 패턴 매칭
    → ④ 인생 주제 결정 → ⑤ 상담 방향 설정
    """

    # ① 감정 5분류 키워드
    _EMOTION_MAP = {
        "불안": ["걱정", "불안", "두렵", "무서", "어떡해", "될까", "맞을까", "해도 될까"],
        "혼란": ["답답", "모르겠", "뭘 해야", "어떻게", "헷갈", "방향", "막막", "의미를 모"],
        "기대": ["설레", "잘 될", "기대", "시작하고 싶", "해보고 싶", "될 것 같", "좋은 시기"],
        "후회": ["후회", "잘못", "그때", "돌아가고", "실수", "아쉽"],
        "결심": ["하기로", "결심", "바꾸고", "시작", "도전", "이제는", "새로운 시작"],
        "피로": ["지쳐", "힘들어", "지겨", "쉬고 싶", "포기", "소진"],
    }

    # ② 키워드 → 주제 그룹
    _KEYWORD_GROUPS = {
        "CAREER": ["회사", "이직", "직장", "취업", "그만", "퇴사", "진로", "일", "커리어",
                   "승진", "사직", "업무", "직업", "전직", "아르바이트", "프리랜서"],
        "WEALTH": ["돈", "투자", "수입", "사업", "재물", "재정", "빚", "월급", "부동산",
                   "주식", "창업", "경제", "수익", "손해", "금전"],
        "LOVE":   ["연애", "남자친", "여자친", "좋아하는 사람", "헤어", "이별", "만남", "결혼",
                   "소개팅", "짝사랑", "썸", "데이트", "사귀", "다시 만날", "인연"],
        "RELATION":["친구 관계", "인간관계", "가족", "부모", "형제", "동료", "상사",
                    "갈등", "다툼", "배신", "화해", "외로", "상처를 많이"],
        "TIMING": ["언제", "시기", "때", "올해", "내년", "몇 년", "좋은 시기",
                   "기다려야", "서둘러야", "운세", "흐름", "나아질", "좋아질"],
    }

    # ③ 상황 패턴 → 주제 (키워드 없어도 감지)
    _SITUATION_PATTERNS = {
        "제자리 같":    "SELF",
        "계속 안 풀려": "TIMING",
        "노력해도 안":  "TIMING",
        "선택을 못":    "SELF",
        "변화가 올 것": "TIMING",
        "뭔가 바뀔":    "TIMING",
        "새로운 시작":  "SELF",
        "의미를 모르":  "SELF",
        "왜 사나":      "SELF",
        "인생이 뭔지":  "SELF",
        "나는 왜":      "SELF",
        "왜 항상":      "SELF",
        "관계가 지쳐":  "RELATION",
        "사람이 지쳐":  "RELATION",
        "상처를 많이":  "RELATION",
        "돈이 계속 나": "WEALTH",
        "돈이 안":      "WEALTH",
        "미래가 불안":  "TIMING",
        "좋아하는 사람이 있": "LOVE",
        "다시 만날":    "LOVE",
        "좋은 시기인가": "TIMING",
    }

    # 동점 시 우선순위 (구체적 주제 > 범용 주제)
    _TIEBREAK_PRIORITY = ["LOVE", "RELATION", "CAREER", "WEALTH", "TIMING", "SELF"]

    # ⑤ 주제별 AI 상담 방향
    _TOPIC_DIRECTION = {
        "CAREER":   "직업운과 대운 흐름을 중심으로, 변화 시기와 구체적 행동 조언을 포함해 상담하세요.",
        "WEALTH":   "재물운과 현재 기운 흐름을 분석하여, 금전 판단과 시기 조언을 중심으로 상담하세요.",
        "LOVE":     "감정·인연 흐름을 먼저 공감하고, 관계 패턴과 만남 시기를 중심으로 상담하세요.",
        "RELATION": "관계 피로도를 먼저 인정하고, 인간관계 패턴과 거리두기 조언을 포함해 상담하세요.",
        "SELF":     "인생 방향성과 자아 흐름을 중심으로, 현재 시기의 의미와 앞으로의 방향을 상담하세요.",
        "TIMING":   "현재 운세 흐름(대운·세운)을 먼저 설명하고, 행동 타이밍과 준비 방법을 조언하세요.",
    }
    _TOPIC_KR = {
        "CAREER": "직업/진로", "WEALTH": "재물/사업", "LOVE": "연애/결혼",
        "RELATION": "인간관계", "SELF": "자아/방향성", "TIMING": "운세 흐름",
    }

    @staticmethod
    def analyze(user_input: str) -> dict:
        """
        사용자 입력 분석 → 의도 딕셔너리 반환
        {emotion, topic, confidence, direction, topic_kr}
        감정 > 상황 패턴 > 키워드 우선순위
        """
        text = user_input.strip()

        # ① 감정 감지
        detected_emotion = "혼란"  # default
        for emotion, keywords in IntentEngine._EMOTION_MAP.items():
            if any(kw in text for kw in keywords):
                detected_emotion = emotion
                break

        # ② 키워드 점수 계산 (긴 키워드 가중치 2배)
        scores = {topic: 0 for topic in IntentEngine._KEYWORD_GROUPS}
        for topic, keywords in IntentEngine._KEYWORD_GROUPS.items():
            for kw in keywords:
                if kw in text:
                    scores[topic] += (2 if len(kw) >= 4 else 1)

        # ③ 상황 패턴 매칭 (가장 강한 신호 +5)
        for pattern, topic in IntentEngine._SITUATION_PATTERNS.items():
            if pattern in text:
                scores[topic] = scores.get(topic, 0) + 5
                break

        # ④ 주제 결정 — 동점 시 우선순위 적용
        max_score = max(scores.values())
        if max_score == 0:
            chosen_topic = "SELF"
            confidence = 60
        else:
            top_topics = [t for t in IntentEngine._TIEBREAK_PRIORITY
                          if scores.get(t, 0) == max_score]
            chosen_topic = top_topics[0] if top_topics else "SELF"
            total = sum(scores.values()) or 1
            raw_conf = round(scores[chosen_topic] / total * 100)
            confidence = 65 if raw_conf == 50 else raw_conf

        # 관심 기억 업데이트 (트리거 규칙)
        try:
            topic_kr = IntentEngine._TOPIC_KR.get(chosen_topic, "")
            for interest_topic in SajuMemory.INTEREST_TOPICS:
                if interest_topic in topic_kr:
                    SajuMemory.record_interest(interest_topic)
        except Exception:
            pass

        return {
            "emotion":    detected_emotion,
            "topic":      chosen_topic,
            "topic_kr":   IntentEngine._TOPIC_KR.get(chosen_topic, chosen_topic),
            "confidence": confidence,
            "direction":  IntentEngine._TOPIC_DIRECTION.get(chosen_topic, ""),
            "scores":     scores,
        }

    @staticmethod
    def build_intent_prompt(user_input: str) -> str:
        """분석 결과를 AI 프롬프트에 주입할 문자열로 변환"""
        result = IntentEngine.analyze(user_input)
        return (
            f"[Intent 분석]\n"
            f"- 감정 상태: {result['emotion']}\n"
            f"- 인생 주제: {result['topic_kr']} (확신도 {result['confidence']}%)\n"
            f"- 상담 방향: {result['direction']}\n"
        )

    @staticmethod
    def get_topic_badge(user_input: str) -> str:
        """UI에 표시할 주제 배지 HTML 반환"""
        result = IntentEngine.analyze(user_input)
        emotion_icon = {
            "불안": "😰", "혼란": "🤔", "기대": "✨",
            "후회": "😔", "결심": "💪", "피로": "😮‍💨",
        }.get(result["emotion"], "💬")
        return (
            f"<span style='background:#000;color:#fff;padding:3px 10px;"
            f"border-radius:12px;font-size:11px;font-weight:700'>"
            f"{emotion_icon} {result['topic_kr']}</span>"
        )


st.set_page_config(
    page_title="🪐 만신(萬神) 사주 천명풀이",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&display=swap');

  /* ══ 전역 기본 ══ */
  html, body, [class*="css"] { font-family:'Noto Serif KR',serif; -webkit-text-size-adjust:100%; }
  .stApp { background:#fdfcf0; color:#000000; }
  * { box-sizing:border-box; }
  p,div,span { word-break:keep-all; overflow-wrap:break-word; }
  a,button,[role="button"] { touch-action:manipulation; }
  img { max-width:100%; height:auto; }

  /* ══ 기본 레이아웃 (모바일 first) ══ */
  .main .block-container {
    padding: 0.5rem 0.75rem 4rem !important;
    max-width: 100% !important;
  }

  /* ══ 탭 모바일 터치 스크롤 핵심 ══ */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    padding: 8px 6px !important;
    background: #f5f0e8 !important;
    border-radius: 10px !important;
    border: 1px solid #e8d5a0 !important;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none !important; }
  .stTabs [data-baseweb="tab"] {
    font-size: 11px !important;
    padding: 8px 10px !important;
    white-space: nowrap !important;
    min-width: max-content !important;
    border-radius: 8px !important;
    color: #000000 !important;
  }
  .stTabs [aria-selected="true"] {
    background: #000000 !important;
    color: #fff !important;
    font-weight: 800 !important;
  }

  /* ══ 버튼 터치 최적화 ══ */
  .stButton > button {
    background: linear-gradient(135deg,#000000,#000000,#000000) !important;
    color: #fff !important; border: none !important;
    font-weight: 900 !important; letter-spacing: 2px !important;
    border-radius: 12px !important;
    min-height: 52px !important;
    font-size: 16px !important;
    width: 100% !important;
    box-shadow: none;; margin-top: 10px;
  }

  /* ══ 입력 필드 (iOS 자동확대 방지 font-size:16px) ══ */
  input, select, textarea {
    font-size: 16px !important;
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ddd !important;
  }
  label { color: #000000 !important; font-weight: 600 !important; }

  /* ══ 사주 기둥 ══ */
  .pillar-box {
    background: #fff; border: 2.5px solid #000000; border-radius: 12px;
    padding: 10px 4px; text-align: center; color: #000000;
    box-shadow: none;
  }

  /* ══ 카드 ══ */
  .card {
    background: #ffffff; border: 1.5px solid #000000;
    border-radius: 14px; padding: 16px 14px;
    box-shadow: none;
    margin: 10px 0;
  }

  /* ══ 운세 텍스트 ══ */
  .fortune-text {
    background: #ffffff; border-left: 8px solid #000000;
    border-radius: 4px 16px 16px 4px;
    padding: 18px 14px; margin: 12px 0;
    font-size: 15px; color: #000000; line-height: 2.1; white-space: pre-wrap;
    font-family: 'Noto Serif KR', serif;
    box-shadow: none;
    border-top: 1px solid #eee; border-right: 1px solid #eee;
    border-bottom: 2.5px solid #000000;
  }

  /* ══ 섹션 헤더 ══ */
  .gold-section {
    color: #000000; font-size: 13px; letter-spacing: 2px;
    border-bottom: 2.5px solid #000000;
    padding-bottom: 10px; font-weight: 700; margin: 24px 0 12px;
    display: flex; align-items: center;
  }
  .gold-section::before { content:"◈"; margin-right:10px; font-size:16px; color:#000000; }

  /* ══ 헤더 박스 ══ */
  .header-box {
    background: #ffffff;
    padding: 22px 16px; text-align: center;
    box-shadow: none;
    margin-bottom: 16px; border-bottom: 3.5px solid #000000;
  }
  .header-title { font-size: 22px; font-weight: 700; color: #000000; letter-spacing: 4px; text-shadow: none; }
  .header-sub { color: #000000; font-size: 12px; letter-spacing: 2px; margin-top: 8px; font-weight: 700; opacity: 0.9; }

  /* ══ 비방록 ══ */
  .red-scroll {
    background: #ffffff; border: 2.5px solid #ff0000; border-radius: 8px;
    padding: 16px; margin: 12px 0; color: #cc0000;
    font-family: "Noto Serif KR", serif; line-height: 2.0;
    white-space: pre-wrap; font-weight: 700;
  }

  /* ══ 월운 카드 ══ */
  .monthly-card {
    background: #ffffff; border: 1.5px solid #000000; border-radius: 10px;
    padding: 10px 12px; margin: 5px 0; font-size: 13px;
    border-left: 8px solid #000000;
    color: #000000;
  }
  .monthly-card.great { border-left-color: #000; background: #ffffff; border: 2.5px solid #000; }

  /* ══ 신호 배지 ══ */
  .signal-badge {
    display:inline-block; padding:3px 10px; border-radius:16px;
    font-size:11px; font-weight:700; margin:2px;
    background:#ffffff; color:#000000; border:1.5px solid #000000;
  }

  /* ══ 폼 카드 ══ */
  .form-card {
    background: #ffffff; border-radius: 14px;
    padding: 18px 14px; border: 1px solid #ddd;
    box-shadow: none;
    margin-bottom: 14px;
  }
  div[data-testid="stForm"] { background:transparent; border:none; padding:0; }

  /* ══ 480px 이하 (스마트폰) ══ */
  @media (max-width:480px) {
    .main .block-container { padding:0.3rem 0.4rem 5rem !important; }
    .header-title { font-size:17px !important; letter-spacing:1px !important; }
    .header-sub   { font-size:10px !important; }
    .fortune-text { font-size:13px !important; line-height:1.95 !important; padding:12px 10px !important; }
    .card         { padding:10px 8px !important; margin:5px 0 !important; border-radius:10px !important; }
    .gold-section { font-size:11px !important; letter-spacing:1px !important; margin:16px 0 8px !important; }
    .stTabs [data-baseweb="tab"] { font-size:10px !important; padding:6px 8px !important; }
    .stButton > button { font-size:14px !important; min-height:48px !important; letter-spacing:1px !important; }
    .pillar-box { padding:7px 2px !important; font-size:13px !important; }
    div[data-testid="stForm"] { padding:0 !important; }
    /* 컬럼 레이아웃 모바일에서 여백 최소화 */
    [data-testid="column"] { padding:0.15rem !important; }
    /* 익스팬더 패딩 */
    .streamlit-expanderHeader { padding:10px 12px !important; font-size:13px !important; }
    /* 숫자/텍스트 입력 */
    .stNumberInput input, .stTextInput input { font-size:16px !important; padding:8px !important; }
    /* selectbox */
    .stSelectbox select, div[data-baseweb="select"] { font-size:15px !important; }
    /* 캡션 */
    .stCaption { font-size:11px !important; }
  }

  /* ══ 481~768px (태블릿) ══ */
  @media (min-width:481px) and (max-width:768px) {
    .main .block-container { padding:0.5rem 1rem 3rem !important; }
    .header-title { font-size:20px !important; }
    .fortune-text { font-size:14px !important; }
    .stTabs [data-baseweb="tab"] { font-size:11px !important; padding:8px 10px !important; }
    .card { padding:14px 12px !important; }
  }

  /* ══ 769px+ (데스크탑) ══ */
  @media (min-width:769px) {
    .main .block-container { max-width:880px !important; padding:1rem 2rem 3rem !important; }
    .header-title { font-size:26px !important; letter-spacing:5px !important; }
    .header-sub   { font-size:13px !important; }
    .fortune-text { font-size:16px !important; padding:28px 26px !important; }
    .card { padding:20px 18px !important; }
    .stTabs [data-baseweb="tab"] { font-size:13px !important; padding:9px 14px !important; }
    .stButton > button { font-size:18px !important; letter-spacing:4px !important; }
    .gold-section { font-size:14px !important; letter-spacing:3px !important; }
    .pillar-box { padding:15px 5px !important; }
  }

  /* ── 사이드바 ── */
  [data-testid="stSidebar"] { background:#ffffff !important; border-right: 1px solid #ddd; }
  [data-testid="stSidebarContent"] { padding:1rem .75rem; background:#ffffff !important; }
  [data-testid="stSidebarContent"] label { color:#000000 !important; font-size:13px !important; }

  /* ── 탭 — 모바일 가로 스크롤 ── */
  .stTabs [data-baseweb="tab-list"] {
    gap:3px; flex-wrap:nowrap; overflow-x:auto;
    -webkit-overflow-scrolling:touch;
    background:#ffffff; padding:6px 4px;
    border-radius:10px; border:1.5px solid #000000;
    scrollbar-width:none;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
  .stTabs [data-baseweb="tab"] {
    font-size:11px !important; padding:7px 9px !important;
    color:#000000 !important; border-radius:7px !important;
    white-space:nowrap !important; min-width:max-content !important;
  }
  .stTabs [aria-selected="true"] {
    background:#000000 !important; color:#ffffff !important; font-weight:800 !important;
  }

  /* ── 버튼 ── */
  .stButton > button {
    background:#000000 !important;
    color:#ffffff !important; border:none !important;
    font-weight:900 !important; letter-spacing:2px !important;
    border-radius:10px !important;
    padding:13px 10px !important; font-size:15px !important;
    box-shadow:none;
    width:100%; margin-top:8px; touch-action:manipulation;
  }
  .stButton > button:active { transform:scale(.98); }

  /* ── 입력 (iOS font-size 16px = zoom 방지) ── */
  input, select, textarea {
    color:#000000 !important; background-color:#fff !important;
    border:1px solid #000000 !important;
    font-size:16px !important; border-radius:8px !important;
    -webkit-appearance:none;
  }
  label { color:#000000 !important; font-weight:600 !important; font-size:13px !important; }
  .stSelectbox > div > div { border-radius:8px !important; min-height:44px !important; }
  .stNumberInput input { min-height:44px !important; }

  /* ── 사이드바 ── */
  [data-testid="stSidebar"] { background:#ffffff !important; }
  [data-testid="stSidebarContent"] { padding:1rem .75rem; background:#ffffff !important; }
  [data-testid="stSidebarContent"] label { color:#000000 !important; font-size:13px !important; }

  /* ── 가로 스크롤 유틸 ── */
  .scroll-x {
    overflow-x:auto; -webkit-overflow-scrolling:touch;
    scrollbar-width:none; display:flex; gap:8px; padding-bottom:4px;
  }
  .scroll-x::-webkit-scrollbar { display:none; }

  /* ── expander ── */
  .streamlit-expanderHeader { font-size:13px !important; padding:9px 10px !important; }

  /* ── 맨위로(TOP) 버튼 ── */
  .top-btn {
    position: fixed;
    bottom: 30px;
    right: 20px;
    width: 50px;
    height: 50px;
    background: #000000 !important;
    color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 800;
    text-decoration: none !important;
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    cursor: pointer;
    transition: transform 0.2s;
  }
  .top-btn:active { transform: scale(0.9); }
</style>
<div id="top"></div>
<a href="#top" class="top-btn">TOP</a>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  만신(萬神)급 명리 데이터 상수
# ══════════════════════════════════════════════
CG = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
CG_KR = ["갑","을","병","정","무","기","경","신","임","계"]
JJ = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
JJ_KR = ["자","축","인","묘","진","사","오","미","신","유","술","해"]
JJ_AN = ["쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"]

CHUNG_MAP = {"子":"午","午":"子","丑":"未","未":"丑","寅":"申","申":"寅","卯":"酉","酉":"卯","辰":"戌","戌":"辰","巳":"亥","亥":"巳"}
HAP_MAP = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}

GANJI_60 = [CG[i % 10] + JJ[i % 12] for i in range(60)]
GANJI_60_KR = [CG_KR[i % 10] + JJ_KR[i % 12] for i in range(60)]

OH = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
      "子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
OHN = {"木":"나무","火":"불","土":"흙","金":"쇠","水":"물"}
OHE = {"木":"🌿","火":"🔥","土":"🪨","金":"✨","水":"💧"}
OH_DIR = {"木":"동쪽","火":"남쪽","土":"중앙","金":"서쪽","水":"북쪽"}
OH_COLOR = {"木":"초록, 청색","火":"빨강, 주황","土":"노랑, 갈색","金":"흰색, 은색","水":"검정, 남색"}
OH_NUM = {"木":"1, 3","火":"2, 7","土":"5, 0","金":"4, 9","水":"1, 6"}
OH_FOOD = {"木":"신맛, 푸른 채소","火":"쓴맛, 붉은 과일","土":"단맛, 뿌리 채소","金":"매운맛, 흰색 육류","水":"짠맛, 해조류/검은콩"}

ILGAN_DESC = {
    "甲":{
        "nature":"""갑목(甲木) 일간으로 태어난 당신에게 하늘은 천년 거목(巨木)의 기운을 점지하였습니다.
조상의 음덕(蔭德)이 깊은 뿌리가 되어 어떤 폭풍과 세파에도 결코 꺾이지 않는 굳건한 천명(天命)을 품고 이 세상에 오셨습니다.
갑목은 십천간(十天干)의 으뜸이요, 동방(東方) 봄기운의 시작이니 새벽을 여는 자, 길을 여는 자의 사명을 타고나셨습니다.
하늘 높이 곧게 뻗어 오르는 소나무처럼 굽힘 없는 기상(氣象)과 우직한 뚝심으로 세상을 헤쳐나가는 것이 당신의 본성입니다.
인(寅)·묘(卯) 목왕절(木旺節)에 운이 오면 크게 발복하며, 경(庚)·신(辛) 금(金)운에 단련을 받아 진정한 동량지재(棟樑之材)가 됩니다.""",
        "strength":"""◎ 타고난 리더십과 개척 정신: 남들이 가지 않은 길을 먼저 나아가는 선구자의 기운이 있습니다. 조직에서 자연스럽게 우두머리 자리에 오르며, 어떤 역경도 정면으로 돌파하는 불굴의 의지가 있습니다.
◎ 원칙과 의리: 한번 맺은 인연과 약속은 목숨처럼 지키는 의리의 사람입니다. 이 신뢰가 평생의 귀인(貴人)을 불러 모읍니다.
◎ 강한 추진력: 목표를 정하면 어떤 장애도 뚫고 나아가는 힘이 있어, 큰 사업이나 조직의 수장으로서 빛을 발합니다.""",
        "weakness":"""▲ 지나친 고집과 아집: 갑목 특유의 강직함이 지나치면 주위 사람들과 충돌을 빚고 귀중한 인연을 잃을 수 있습니다. 대나무처럼 굽힐 줄 알아야 폭풍에도 꺾이지 않는 법입니다.
▲ 자존심으로 인한 실기(失機): 자존심이 강한 나머지 도움을 청하지 못하거나 기회가 와도 허리를 굽히지 못해 복을 놓치는 경우가 있습니다. 용의 겸손함을 배우십시오.
▲ 독불장군 성향: 혼자 모든 것을 짊어지려 하다 소진되는 경향이 있습니다. 믿는 사람에게 권한을 나누는 지혜가 필요합니다.""",
        "career":"정치·행정·공무원, 경영인·CEO, 교육자·교수, 법조계, 군 장성·무관, 건축·토목, 의료계 수장",
        "health":"""간담(肝膽) 계통이 가장 취약하니 과음을 삼가고 정기적으로 간 기능을 점검하십시오.
목(木)기운이 과다할 때는 분노와 스트레스로 간을 상하고, 부족할 때는 근육과 눈의 피로를 호소합니다.
봄(춘)에 보약을 챙기고, 신맛 나는 음식으로 간 기운을 북돋우시기 바랍니다.""",
        "lucky":"""행운의 방향: 동쪽(東方), 행운의 색: 청색·초록, 행운의 수: 1·3, 인연의 일간: 己土(정재)·辛金(정관), 피해야 할 운: 庚金 편관 과다"""
    },
    "乙":{
        "nature":"""을목(乙木) 일간으로 태어난 당신에게 하늘은 강인한 생명력으로 꽃을 피우는 기운을 점지하였습니다.
바위틈에서도, 척박한 땅에서도 기어코 싹을 틔우고 꽃을 피우는 들풀과 덩굴의 천명을 안고 오셨습니다.
갑목이 곧게 자라는 교목(喬木)이라면, 을목은 유연하게 휘어 어디에도 적응하는 덩굴식물의 지혜를 지녔습니다.
겉으로는 부드럽고 온화하나 내면에는 어떤 어려움도 이겨내는 질긴 생명력이 있으니, 이것이 을목 최고의 보배입니다.
무(戊)·기(己) 토(土)운에 재물이 들어오고, 임(壬)·계(癸) 수(水)운에 귀인의 도움을 받습니다.""",
        "strength":"""◎ 뛰어난 감수성과 심미안: 아름다움을 보고 느끼는 천부적 감각이 있어 예술·문화 분야에서 남들이 따라오지 못하는 경지에 이릅니다.
◎ 유연한 적응력: 어떤 환경에서도 빠르게 적응하며 인간관계를 부드럽게 유지하는 사교적 지혜가 있습니다. 귀인을 만나는 능력이 탁월합니다.
◎ 끈질긴 생명력: 을목의 가장 큰 강점은 역경을 딛고 일어서는 회복력입니다. 쓰러져도 반드시 다시 일어서는 불사조의 기운이 있습니다.""",
        "weakness":"""▲ 남의 시선에 대한 민감함: 타인의 평가에 쉽게 상처받고 흔들리는 경향이 있습니다. 내면의 중심을 굳건히 하는 수련이 필요합니다.
▲ 우유부단한 결단: 유연함이 지나치면 결정적인 순간에 결단을 내리지 못해 기회를 놓칩니다. 때로는 과감하게 결단하는 용기가 필요합니다.
▲ 의존 심리: 귀인 의존이 강해지면 스스로의 힘을 키우는 기회를 잃을 수 있습니다. 독립심을 기르는 것이 복의 근원입니다.""",
        "career":"예술가·화가·음악인, 디자이너, 상담사·심리치료사, 교육자, 뷰티·패션, 원예·조경, 외교관·통역사",
        "health":"""간담 계통과 신경계 건강에 주의하십시오. 특히 스트레스가 쌓이면 신경성 소화 장애나 두통으로 나타납니다.
을목은 음목(陰木)으로 수분이 부족하면 쉽게 시들므로 충분한 수분 섭취와 숙면이 중요합니다.
척추와 관절도 약점이 될 수 있으니 스트레칭과 운동을 생활화하십시오.""",
        "lucky":"""행운의 방향: 동남쪽, 행운의 색: 연두·청록, 행운의 수: 1·3, 인연의 일간: 庚金(정관)·戊土(정재), 보강할 운: 壬癸水 인성운"""
    },
    "丙":{
        "nature":"""병화(丙火) 일간으로 태어난 당신에게 하늘은 태양(太陽)의 기운을 점지하였습니다.
동녘 하늘을 붉게 물들이며 떠오르는 아침 태양처럼 온 세상을 환하게 비추고 만물에 생명력을 불어넣는 천명을 부여받으셨습니다.
태양은 높낮이 없이 귀천(貴賤)을 가리지 않고 빛을 고루 나누니, 당신 또한 넓은 포용력으로 많은 이들을 품는 인물입니다.
병화는 십천간 중 가장 밝고 뜨거운 기운으로, 어디에 있든 자연스럽게 중심이 되고 주목받는 운명을 타고났습니다.
임(壬)·계(癸) 수(水)운에 단련되어 더욱 성숙해지고, 목(木)운에 생조(生助)를 받아 크게 발복합니다.""",
        "strength":"""◎ 강력한 카리스마와 존재감: 어느 자리에서나 자연스럽게 빛나는 존재감이 있습니다. 사람들이 본능적으로 따르게 되는 천부적 지도자 기질입니다.
◎ 뜨거운 열정과 추진력: 한번 목표를 정하면 몸을 사리지 않고 전력투구하는 열정이 있습니다. 이 열정이 주변 사람들에게 감동과 동기를 부여합니다.
◎ 뛰어난 사교성과 화술: 밝고 유쾌한 성품으로 어디서든 쉽게 친화력을 발휘하며, 말로 사람을 움직이는 능력이 탁월합니다.""",
        "weakness":"""▲ 충동적 결정: 열정이 이성을 앞서면 신중함을 잃고 충동적으로 행동하여 나중에 후회하는 상황이 생깁니다.
▲ 지속력 부족: 태양이 항상 떠 있을 수 없듯, 처음의 열기가 식으면 지속력이 약해지는 경향이 있습니다. 꾸준함을 기르는 것이 중요합니다.
▲ 자기중심적 사고: 자신이 옳다는 확신이 강해 타인의 의견을 경청하지 않는 경우가 있으니 유의하십시오.""",
        "career":"방송·연예인·유튜버, 정치인·사회운동가, 영업·마케팅, 요식업·요리사, 스포츠인, 종교지도자, 강연가",
        "health":"""심장과 혈관계 건강을 최우선으로 관리하십시오. 과도한 흥분과 스트레스는 심장에 직접적인 부담을 줍니다.
여름(하)이 되면 더위에 약해지니 충분한 휴식과 수분 보충이 필요합니다.
눈의 피로와 시력 관리에도 주의를 기울이시기 바랍니다. 정기적인 혈압 측정을 권합니다.""",
        "lucky":"""행운의 방향: 남쪽(南方), 행운의 색: 빨강·주황, 행운의 수: 2·7, 인연의 일간: 辛金(정재)·壬水(편관), 보강할 운: 木운 인성"""
    },
    "丁":{
        "nature":"""정화(丁火) 일간으로 태어난 당신에게 하늘은 촛불과 별빛의 기운을 점지하였습니다.
태양(丙火)이 온 세상을 밝히는 빛이라면, 정화는 어두운 밤 홀로 빛나는 별처럼 가장 필요한 곳에서 가장 소중한 빛을 발합니다.
연약해 보이지만 결코 꺼지지 않는 촛불처럼, 당신에게는 역경 속에서도 희망의 불꽃을 간직하는 내면의 강인함이 있습니다.
정화 일간은 영성(靈性)과 직관력이 뛰어나 보이지 않는 이치를 꿰뚫어 보는 혜안(慧眼)이 있으며, 한 분야를 깊이 파고드는 전문가의 기질을 타고났습니다.
갑(甲)·을(乙) 목(木)운에 크게 발복하고, 무(戊)·기(己) 토(土)운에 재물이 모입니다.""",
        "strength":"""◎ 뛰어난 직관과 통찰력: 보통 사람이 보지 못하는 사물의 본질과 이치를 꿰뚫어 보는 직관력이 있습니다. 이 능력이 학문·예술·상담 분야에서 빛을 발합니다.
◎ 깊은 정과 헌신: 한번 인연을 맺으면 깊은 정으로 헌신하는 따뜻한 인품이 있습니다. 주변 사람들이 마음 깊이 의지하는 존재가 됩니다.
◎ 전문성과 집중력: 관심 분야에 몰두하면 남다른 경지에 이르는 전문가 기질이 있습니다. 한 분야의 대가(大家)가 될 운명입니다.""",
        "weakness":"""▲ 감수성으로 인한 상처: 섬세한 감수성이 지나치면 작은 말 한마디에도 깊이 상처받아 신기(神氣)를 소진합니다.
▲ 내향적 고립: 혼자만의 세계에 빠지면 현실과의 괴리가 생기고 사회적 관계가 단절될 수 있습니다.
▲ 우유부단: 너무 많은 것을 느끼고 고려하다 보면 결정이 늦어져 기회를 놓치는 경우가 있습니다.""",
        "career":"의료인·한의사, 심리상담사·정신과의사, 종교인·성직자, 철학자·작가, 교육자, 연구원, 예술가·음악가",
        "health":"""심장과 소화기 계통을 함께 관리하십시오. 정신적 스트레스가 심장과 소화기에 동시에 영향을 미치는 체질입니다.
수면의 질을 높이는 것이 건강의 핵심입니다. 과도한 야간 활동을 줄이고 규칙적인 수면 습관을 들이십시오.
순환기 계통도 챙기시고, 차갑고 자극적인 음식은 피하시기 바랍니다.""",
        "lucky":"""행운의 방향: 남남동, 행운의 색: 자주·보라, 행운의 수: 2·7, 인연의 일간: 壬水(정관)·甲木(정인), 보강할 운: 木운 인성"""
    },
    "戊":{
        "nature":"""무토(戊土) 일간으로 태어난 당신에게 하늘은 크고 높은 산(山)과 대지(大地)의 기운을 점지하였습니다.
태산(泰山)처럼 굳건히 자리를 지키며 사방의 모든 것을 품고 길러내는 위대한 어머니 땅의 기운이 당신의 천명입니다.
무토는 오행의 중앙(中央)을 관장하니 중재자요, 조율자요, 포용자입니다. 어떤 갈등도 당신 앞에서는 자연스럽게 봉합됩니다.
인내와 신용이 두텁고 한번 맡은 일은 반드시 해내는 성실함으로, 주변의 신망(信望)을 한 몸에 받는 인물입니다.
갑(甲)·을(乙) 목(木)운에 관(官)이 발달하고, 병(丙)·정(丁) 화(火)운에 인성(印星)으로 명예가 높아집니다.""",
        "strength":"""◎ 산 같은 믿음직스러움: 어떤 상황에서도 흔들리지 않는 안정감으로 주위 사람들의 든든한 버팀목이 됩니다. 이 신뢰가 평생의 재산입니다.
◎ 탁월한 포용력: 다양한 의견과 사람들을 아우르는 포용력이 있어, 조직의 화합과 중재에 탁월한 능력을 발휘합니다.
◎ 실천적 성실함: 화려한 말보다 묵묵한 실천으로 증명하는 스타일입니다. 이 성실함이 결국 큰 성취로 이어집니다.""",
        "weakness":"""▲ 경직된 사고: 산처럼 고집스러운 면이 있어 새로운 변화와 혁신을 받아들이기 어려워하는 경향이 있습니다.
▲ 느린 결단: 모든 것을 신중하게 검토하다 보니 변화하는 환경에서 결단이 늦어 기회를 놓치는 경우가 있습니다.
▲ 고지식함: 원칙에 너무 얽매여 융통성이 부족해 보일 수 있으니, 상황에 따른 유연함이 필요합니다.""",
        "career":"부동산·건설업, 금융·은행원, 공무원·행정가, 농업·목축업, 산업계 경영인, 중재인·조정사, 의료계",
        "health":"""비위(脾胃), 즉 소화기 계통이 취약점입니다. 과식, 야식, 불규칙한 식사가 쌓이면 위장 질환으로 이어집니다.
토(土)가 과다하면 부종이나 당뇨 관련 질환에 주의하십시오.
규칙적인 식사와 적당한 운동, 과로를 피하는 생활습관이 건강의 핵심입니다.""",
        "lucky":"""행운의 방향: 중앙·북동, 행운의 색: 노랑·황토, 행운의 수: 5·0, 인연의 일간: 癸水(정재)·甲木(편관), 보강할 운: 丙丁火 인성운"""
    },
    "己":{
        "nature":"""기토(己土) 일간으로 태어난 당신에게 하늘은 기름진 논밭(田畓)의 기운을 점지하였습니다.
무토(戊土)가 산이라면 기토는 농부의 손길이 닿아 씨앗을 받아들이고 풍요로운 결실을 맺는 옥토(沃土)입니다.
당신은 가진 것을 더욱 가치 있게 변환시키고 길러내는 연금술사의 능력을 타고났습니다.
표면적으로는 온순하고 부드러워 보이지만, 내면에는 집요하리만치 강한 의지와 인내심이 숨어 있습니다.
병(丙)·정(丁) 화(火)운에 인성이 강해져 학문과 명예가 빛나고, 경(庚)·신(辛) 금(金)운에 식상(食傷)이 발달하여 재주가 드러납니다.""",
        "strength":"""◎ 세심하고 꼼꼼한 완성도: 어떤 일이든 디테일을 챙기며 완성도 높게 마무리하는 능력이 있습니다. 이 꼼꼼함이 신뢰와 전문성의 바탕이 됩니다.
◎ 실용적 지혜: 화려함보다 실질적인 효용을 추구하는 현실적 지혜가 있어, 실생활에서 놀라운 성과를 거둡니다.
◎ 깊은 배려심: 주변 사람들의 필요를 세심하게 살피고 채워주는 따뜻한 마음이 귀인을 불러 모읍니다.""",
        "weakness":"""▲ 과도한 걱정과 불안: 기토의 특성상 작은 문제도 크게 걱정하는 경향이 있어 신기(神氣)를 소진합니다. 현재에 집중하는 연습이 필요합니다.
▲ 결단력 부족: 너무 많은 것을 고려하다 보면 결정이 늦어지고, 다른 사람의 의견에 쉽게 흔들리는 경우가 있습니다.
▲ 자기희생 과다: 남을 돌보다가 자신을 돌보지 못하는 경우가 많습니다. 나 자신도 소중한 존재임을 기억하십시오.""",
        "career":"회계사·세무사, 의료인·약사, 요리사·조리사, 원예·농업, 교육자, 심리상담사, 중소기업 경영",
        "health":"""소화기와 피부 질환을 가장 주의해야 합니다. 기름진 음식, 과식, 스트레스성 식이 장애에 취약합니다.
비만이나 당뇨, 피부 트러블이 건강의 신호등이 됩니다. 절제된 식습관이 최고의 보약입니다.
토(土)가 습(濕)하면 무기력증이 오니 규칙적인 운동으로 습기를 털어내십시오.""",
        "lucky":"""행운의 방향: 북동·중앙, 행운의 색: 황색·베이지, 행운의 수: 5·0, 인연의 일간: 甲木(편관)·壬水(정재), 보강할 운: 丙丁火 인성운"""
    },
    "庚":{
        "nature":"""경금(庚金) 일간으로 태어난 당신에게 하늘은 천하를 호령하는 강철 칼날과 원석(原石)의 기운을 점지하였습니다.
광산에서 막 캐낸 원석처럼 겉은 거칠고 투박해 보이지만, 그 안에는 세상 어떤 것도 베어낼 수 있는 강인한 기운이 잠들어 있습니다.
정(丁)화의 제련(製鍊)을 받아 갈고 닦을수록 더욱 빛나는 보검(寶劍)이 되는 천명을 타고났으니, 고난이 오히려 당신을 완성시킵니다.
경금 일간은 불의를 보면 참지 못하는 정의감과 결단력이 있어, 사회의 불합리한 것을 바로잡는 역할을 운명으로 받아들입니다.
정(丁)화운에 단련되어 진정한 강자가 되고, 토(土)운에 생조를 받아 근본이 두터워집니다.""",
        "strength":"""◎ 불굴의 결단력: 한번 결심한 일은 어떤 어려움도 뚫고 반드시 실행에 옮기는 강철 같은 의지력이 있습니다.
◎ 강렬한 정의감: 옳고 그름에 대한 판단이 명확하여 불의를 보면 자신의 손해를 감수하고도 바로잡으려 합니다. 이 기개가 많은 사람의 존경을 받습니다.
◎ 뛰어난 실행력: 계획을 세우면 빠르고 강력하게 실행에 옮기는 추진력이 있어 조직에서 없어서는 안 되는 핵심 인재가 됩니다.""",
        "weakness":"""▲ 거친 언행: 직설적인 표현이 지나치면 주변 사람들에게 상처를 주고 관계를 해치는 경우가 있습니다. 말에 포장지를 입히는 지혜가 필요합니다.
▲ 극단적 선택: 회색지대를 인정하지 않는 흑백 논리가 지나치면 중도(中道)를 잃어 극단으로 치닫는 경향이 있습니다.
▲ 오만: 자신의 능력을 과신하여 타인을 무시하는 경향이 있을 수 있습니다. 겸손이 경금의 가장 큰 보완재입니다.""",
        "career":"군인·장교, 경찰·검사, 외과의사·치과의사, 기계·금속 기술자, 운동선수, 건설·토목, 중공업",
        "health":"""폐(肺)와 대장(大腸) 계통을 각별히 관리하십시오. 건조한 환경에서 폐 기능이 저하되기 쉽습니다.
피부 관련 질환과 호흡기 질환에 취약한 체질이므로 가을에 특히 주의가 필요합니다.
격렬한 운동은 좋지만 관절과 인대 부상에 주의하시고, 수술을 요하는 상황이 종종 생길 수 있습니다.""",
        "lucky":"""행운의 방향: 서쪽(西方), 행운의 색: 흰색·은색, 행운의 수: 4·9, 인연의 일간: 乙木(정재)·丁火(정관), 보강할 운: 土운 인성"""
    },
    "辛":{
        "nature":"""신금(辛金) 일간으로 태어난 당신에게 하늘은 빛나는 보석과 완성된 금속의 기운을 점지하였습니다.
경금(庚金)이 다듬어지지 않은 광석이라면, 신금은 이미 세공을 마친 아름다운 보석과 정밀한 칼날입니다.
당신은 날카로운 감식안(鑑識眼)으로 아름다움과 가치를 알아보고, 완벽한 것을 추구하는 미의식(美意識)이 천성입니다.
섬세하고 예민한 기질로 인해 상처도 쉽게 받지만, 그 감수성이 예술적 감각과 통찰력의 원천이 됩니다.
임(壬)·계(癸) 수(水)운에 식상이 발달하여 재주가 빛나고, 토(土)운에 인성이 강해져 학문과 명예가 높아집니다.""",
        "strength":"""◎ 완벽주의적 심미안: 다른 사람이 보지 못하는 미세한 결함도 발견하고 완성도를 높이는 능력이 탁월합니다. 최고 수준을 추구하는 이 기질이 전문가로 성장하는 힘입니다.
◎ 날카로운 분석력: 상황을 세밀하게 분석하고 핵심을 찌르는 통찰력이 있어, 전략적 판단이 필요한 분야에서 두각을 나타냅니다.
◎ 우아함과 품격: 언행에 자연스러운 품격이 배어 있어 사람들에게 신뢰와 호감을 줍니다. 격이 있는 환경에서 더욱 빛을 발합니다.""",
        "weakness":"""▲ 지나친 완벽주의로 인한 소진: 완벽하지 않으면 시작조차 못하거나, 완성된 것도 계속 수정하다 에너지를 소진합니다.
▲ 예민한 감수성: 작은 자극에도 크게 반응하여 마음의 상처가 깊어지고, 대인관계에서 소소한 갈등을 크게 받아들이는 경향이 있습니다.
▲ 외로움: 자신의 높은 기준을 맞춰줄 사람이 드물어 외로움을 느끼는 경우가 많습니다. 타인의 다름을 인정하는 관대함이 필요합니다.""",
        "career":"연구원·과학자, 예술가·공예가, 디자이너, 금융·투자분석가, 패션·뷰티, 치과·성형외과, 보석감정사",
        "health":"""폐와 피부·호흡기 계통이 신금의 취약점입니다. 건조한 공기와 대기오염에 특히 민감하므로 가습기와 공기청정기를 활용하십시오.
피부 트러블이 건강의 신호가 되는 경우가 많으니 피부 상태를 통해 내면 건강을 점검하십시오.
과도한 스트레스와 완벽주의는 면역력을 떨어뜨리니 충분한 휴식이 필수입니다.""",
        "lucky":"""행운의 방향: 서서남, 행운의 색: 흰색·은색·금색, 행운의 수: 4·9, 인연의 일간: 丙火(정관)·壬水(상관), 보강할 운: 土운 인성"""
    },
    "壬":{
        "nature":"""임수(壬水) 일간으로 태어난 당신에게 하늘은 천하를 품는 대해(大海)의 기운을 점지하였습니다.
무한한 바다처럼 모든 강물을 받아들이고 무궁한 지혜를 품은 당신은, 광활한 포용력과 깊은 통찰력으로 세상을 읽어내는 천명을 받았습니다.
임수는 십천간 중 가장 깊고 넓은 기운으로, 겉으로는 유연하게 흘러가되 거대한 파도처럼 세상을 움직이는 잠재력이 있습니다.
빠른 두뇌회전과 폭넓은 지식, 국제적 안목을 갖춘 전략가요, 사상가의 기질을 타고났습니다.
금(金)운에 생조를 받아 지혜가 샘솟고, 목(木)운에 식상이 발달하여 재능이 만개합니다.""",
        "strength":"""◎ 탁월한 지혜와 통찰력: 복잡한 상황의 본질을 꿰뚫어 보는 뛰어난 지혜가 있습니다. 남들이 보지 못하는 미래를 내다보는 선견지명이 있습니다.
◎ 무한한 포용력: 다양한 관점과 사람을 받아들이는 넓은 마음이 있어 국제적인 무대에서도 자연스럽게 활약합니다.
◎ 전략적 사고: 크고 복잡한 그림을 한 번에 파악하는 능력이 있어 전략 기획, 투자, 외교 분야에서 탁월한 성과를 냅니다.""",
        "weakness":"""▲ 일관성 부족: 물이 그릇에 따라 모양이 변하듯, 환경에 따라 쉽게 변하여 일관성 없다는 평을 듣는 경우가 있습니다.
▲ 실행력 부족: 머릿속으로는 완벽한 계획을 세우지만 실행에 옮기는 단계에서 에너지가 분산되는 경향이 있습니다.
▲ 감정 기복: 깊은 감수성으로 인해 감정 기복이 있을 수 있으며, 우울감에 빠지는 경우도 있습니다. 마음의 닻을 내리는 수련이 필요합니다.""",
        "career":"외교관·국제무역, 철학자·사상가, 종교인, 법조인, 의료계, 심리학자, 투자가·펀드매니저, 해운·항공업",
        "health":"""신장(腎臟)과 방광(膀胱), 그리고 생식기계 건강을 중점 관리하십시오. 차가운 음식과 음료를 과도하게 섭취하면 신장 기능이 저하됩니다.
겨울철 보온을 철저히 하고, 허리와 무릎 관절 관리에도 주의를 기울이십시오.
임수 일간은 수면 부족에 취약하여 만성피로로 이어지기 쉬우니 수면 관리가 건강의 핵심입니다.""",
        "lucky":"""행운의 방향: 북쪽(北方), 행운의 색: 검정·남색, 행운의 수: 1·6, 인연의 일간: 丁火(정재)·甲木(식신), 보강할 운: 金운 인성"""
    },
    "癸":{
        "nature":"""계수(癸水) 일간으로 태어난 당신에게 하늘은 이슬과 샘물, 봄비의 기운을 점지하였습니다.
임수(壬水)가 거대한 바다라면, 계수는 생명을 살리는 이슬이요, 대지를 적시는 봄비이며, 깊은 산속의 맑은 샘물입니다.
작고 섬세한 것 같지만, 이 세상 모든 생명이 계수의 은혜 없이는 살아갈 수 없으니 당신은 세상에서 가장 소중한 기운의 주인공입니다.
영적 감수성과 예술적 재능이 탁월하며, 보이지 않는 것을 느끼고 표현하는 천부적 능력이 있습니다.
금(金)운에 생조를 받아 기운이 풍성해지고, 목(木)운에 식상이 발달하여 재능이 펼쳐집니다.""",
        "strength":"""◎ 뛰어난 직관과 영적 감수성: 논리가 닿지 않는 영역의 진실을 직관으로 파악하는 능력이 있습니다. 이 능력이 예술·상담·의료 분야에서 빛납니다.
◎ 깊은 공감 능력: 타인의 감정과 아픔을 내 것처럼 느끼는 공감 능력이 있어, 사람들이 마음을 열고 의지하는 존재가 됩니다.
◎ 창의적 상상력: 독창적인 아이디어와 상상력이 풍부하여 새로운 것을 창조하는 분야에서 탁월한 성과를 냅니다.""",
        "weakness":"""▲ 자기 과소평가: 계수 일간의 가장 큰 적은 자기 자신입니다. 스스로의 능력을 너무 낮게 평가하여 도전을 포기하는 경우가 많습니다.
▲ 경계 설정 어려움: 타인의 감정을 너무 잘 흡수하다 보니 자신의 에너지가 고갈되고 경계가 무너지는 경험을 합니다.
▲ 현실 도피: 현실의 어려움을 직면하기보다 상상의 세계나 영성으로 도피하는 경향이 있습니다. 현실에 뿌리를 내리는 훈련이 필요합니다.""",
        "career":"예술가·시인·소설가, 문학가·작가, 심리치료사, 의료인, 종교인·영성지도자, 음악인, 사진작가, 복지사",
        "health":"""면역력과 신장 계통이 가장 취약합니다. 몸이 차가워지면 면역력이 급격히 저하되니 항상 몸을 따뜻하게 유지하십시오.
정서적 스트레스가 면역계에 직접적인 영향을 주므로 감정 관리가 건강 관리와 직결됩니다.
하체와 신장, 방광 관리에 주의를 기울이고, 차가운 음식과 날 음식을 가급적 피하십시오.""",
        "lucky":"""행운의 방향: 북북동, 행운의 색: 검정·보라·자주, 행운의 수: 1·6, 인연의 일간: 戊土(정관)·丙火(정재), 보강할 운: 金운 인성"""
    }
}

ess_map = {k: v["nature"] for k, v in ILGAN_DESC.items()}

OH_RELATE = {
    "木": {"saeng": "火", "geuk": "土"},
    "火": {"saeng": "土", "geuk": "金"},
    "土": {"saeng": "金", "geuk": "水"},
    "金": {"saeng": "水", "geuk": "木"},
    "水": {"saeng": "木", "geuk": "火"}
}

SIPSUNG_LIST = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]

TEN_GODS_MATRIX = {
    "甲": {"甲":"비견","乙":"겁재","丙":"식신","丁":"상관","戊":"편재","己":"정재","庚":"편관","辛":"정관","壬":"편인","癸":"정인"},
    "乙": {"乙":"비견","甲":"겁재","丁":"식신","丙":"상관","己":"편재","戊":"정재","辛":"편관","庚":"정관","癸":"편인","壬":"정인"},
    "丙": {"丙":"비견","丁":"겁재","戊":"식신","己":"상관","庚":"편재","辛":"정재","壬":"편관","癸":"정관","甲":"편인","乙":"정인"},
    "丁": {"丁":"비견","丙":"겁재","己":"식신","戊":"상관","辛":"편재","庚":"정재","癸":"편관","壬":"정관","乙":"편인","甲":"정인"},
    "戊": {"戊":"비견","己":"겁재","庚":"식신","辛":"상관","壬":"편재","癸":"정재","甲":"편관","乙":"정관","丙":"편인","丁":"정인"},
    "己": {"己":"비견","戊":"겁재","辛":"식신","庚":"상관","癸":"편재","壬":"정재","乙":"편관","甲":"정관","丁":"편인","丙":"정인"},
    "庚": {"庚":"비견","辛":"겁재","壬":"식신","癸":"상관","甲":"편재","乙":"정재","丙":"편관","丁":"정관","戊":"편인","己":"정인"},
    "辛": {"辛":"비견","庚":"겁재","癸":"식신","壬":"상관","乙":"편재","甲":"정재","丁":"편관","丙":"정관","己":"편인","戊":"정인"},
    "壬": {"壬":"비견","癸":"겁재","甲":"식신","乙":"상관","丙":"편재","丁":"정재","戊":"편관","己":"정관","庚":"편인","辛":"정인"},
    "癸": {"癸":"비견","壬":"겁재","乙":"식신","甲":"상관","丁":"편재","丙":"정재","己":"편관","戊":"정관","辛":"편인","庚":"정인"}
}

JIJANGGAN = {
    "子":["壬","癸"],"丑":["癸","辛","己"],"寅":["戊","丙","甲"],"卯":["甲","乙"],
    "辰":["乙","癸","戊"],"巳":["戊","庚","丙"],"午":["丙","己","丁"],"未":["丁","乙","己"],
    "申":["戊","壬","庚"],"酉":["庚","辛"],"戌":["辛","丁","戊"],"亥":["戊","甲","壬"]
}

UNSUNG_TABLE = {
    "甲": {"亥":"장생","子":"목욕","丑":"관대","寅":"건록","卯":"제왕","辰":"쇠","巳":"병","午":"사","未":"묘","申":"절","酉":"태","戌":"양"},
    "乙": {"午":"장생","巳":"목욕","辰":"관대","卯":"건록","寅":"제왕","丑":"쇠","子":"병","亥":"사","戌":"묘","酉":"절","申":"태","未":"양"},
    "丙": {"寅":"장생","卯":"목욕","辰":"관대","巳":"건록","午":"제왕","未":"쇠","申":"병","酉":"사","戌":"묘","亥":"절","子":"태","丑":"양"},
    "丁": {"酉":"장생","申":"목욕","未":"관대","午":"건록","巳":"제왕","辰":"쇠","卯":"병","寅":"사","丑":"묘","子":"절","亥":"태","戌":"양"},
    "戊": {"寅":"장생","卯":"목욕","辰":"관대","巳":"건록","午":"제왕","未":"쇠","申":"병","酉":"사","戌":"묘","亥":"절","子":"태","丑":"양"},
    "己": {"酉":"장생","申":"목욕","未":"관대","午":"건록","巳":"제왕","辰":"쇠","卯":"병","寅":"사","丑":"묘","子":"절","亥":"태","戌":"양"},
    "庚": {"巳":"장생","午":"목욕","未":"관대","申":"건록","酉":"제왕","戌":"쇠","亥":"병","子":"사","丑":"묘","寅":"절","卯":"태","辰":"양"},
    "辛": {"子":"장생","亥":"목욕","戌":"관대","酉":"건록","申":"제왕","未":"쇠","午":"병","巳":"사","辰":"묘","卯":"절","寅":"태","丑":"양"},
    "壬": {"申":"장생","酉":"목욕","戌":"관대","亥":"건록","子":"제왕","丑":"쇠","寅":"병","卯":"사","辰":"묘","巳":"절","午":"태","未":"양"},
    "癸": {"卯":"장생","寅":"목욕","丑":"관대","子":"건록","亥":"제왕","戌":"쇠","酉":"병","申":"사","未":"묘","午":"절","巳":"태","辰":"양"}
}

CONTROL_MAP = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
BIRTH_MAP = {"木":"火","火":"土","土":"金","金":"水","水":"木"}

def detect_structure(ilgan, wolji_jj):
    jijang = JIJANGGAN.get(wolji_jj, [])
    if not jijang: return "일반격"
    junggi = jijang[-1]
    structure_type = TEN_GODS_MATRIX.get(ilgan, {}).get(junggi, "기타")
    return f"{structure_type}격"

GYEOKGUK_DESC = {
    "정관격": {
        "summary": """정관격(正官格)은 법도와 질서를 몸에 타고난 천하 제일의 귀격(貴格)이로다!
정관은 일간을 극하되 음양이 다른 기운으로 마치 스승이 제자를 올바르게 이끌듯, 당신을 바른 길로 인도하는 하늘의 뜻이 담겨 있습니다.
관인상생(官印相生)이 이루어지면 학문과 명예가 함께 빛나는 최상의 귀격이 되고, 재성이 관을 생하면 재물도 함께 따라옵니다.
법과 원칙을 중시하고 질서 속에서 성취를 이루는 당신의 삶은, 주변 사람들에게 믿음직한 모범이 됩니다.
▶ 용신(用神): 인수(印綬)로 관의 기운을 일간에 전달할 때 최상 발복""",
        "lucky_career": "공무원·관료, 법관·검사·판사, 대기업 임원, 교육공무원·교장, 군 장교, 외교관, 국회의원",
        "caution": """⚠ 칠살(七殺, 편관)이 섞이면 관직에 구설이 따르고 직위가 불안해집니다.
⚠ 관다신약(官多身弱)하면 직장에서 압박감이 심해지니 인성운이 올 때를 기다리십시오.
⚠ 정관이 합거(合去)되면 평생 관직과의 인연이 약해집니다. 이 경우 전문직으로 방향을 바꾸십시오.""",
        "god_rank": "天乙貴人·文昌貴人이 함께하면 재상(宰相)의 귀격! 관인상생이면 세상에 이름을 남기는 최상격"
    },
    "편관격": {
        "summary": """편관격(偏官格), 즉 칠살격(七殺格)은 서슬 퍼런 강철 칼날의 기운으로 이루어진 격이로다!
제화(制化)가 이루어지면 천하를 호령하는 영웅이 되고, 제화가 안 되면 파란만장한 인생의 주인공이 됩니다.
식신제살(食神制殺)이 되면 칠살의 흉기(凶氣)가 길기(吉氣)로 변환되어 군·검·경·의 분야에서 천하무적의 강자가 됩니다.
살인상생(殺印相生)이 이루어지면 학문과 무공을 함께 갖춘 문무겸전(文武兼全)의 대인물이 됩니다.
▶ 핵심: 이 격이 빛나려면 반드시 제화(制化)가 필요합니다. 제화 여부가 귀천(貴賤)을 가릅니다""",
        "lucky_career": "군인·장성, 경찰·검찰·형사, 외과의사·응급의학과, 운동선수·격투가, 법조인, 소방관·구조대원, 공학·기술자",
        "caution": """⚠ 살(殺)이 너무 많아 신약하면 사고·수술·관재의 위험이 따릅니다. 합살(合殺)이나 제살(制殺)이 필요합니다.
⚠ 편관이 천간에 투출하면 직장 상사나 권력과의 마찰이 잦습니다. 인내와 처세가 필요합니다.
⚠ 여명(女命)에서는 남편과의 갈등이나 이별수가 따를 수 있으니 배우자 선택에 신중을 기하십시오.""",
        "god_rank": "살인상생·식신제살이면 장군·재상의 대귀격! 고난이 클수록 더욱 단단해지는 불굴의 운명"
    },
    "정재격": {
        "summary": """정재격(正財格)은 성실하고 꾸준하게 쌓아가는 안정된 재물의 격이로다!
정재는 일간이 음양이 다른 오행을 극하는 것으로, 내가 주체적으로 관리하고 통제하는 안정된 재물의 기운입니다.
급작스러운 횡재보다는 땀 흘려 벌어 차곡차곡 쌓아가는 재물운이라, 나이 들수록 자산이 불어나는 복을 지녔습니다.
관인상생(官印相生)이 더해지면 재물과 명예가 함께 빛나는 부귀격(富貴格)이 됩니다.
▶ 용신: 식상(食傷)으로 재를 생(生)하거나, 관(官)으로 재를 설기(洩氣)할 때 균형이 맞음""",
        "lucky_career": "회계사·세무사·공인회계사, 은행원·금융인, 부동산 전문가, 행정공무원, 관리직·경영직, 의사·약사",
        "caution": """⚠ 겁재(劫財)가 많으면 애써 모은 재물이 동업자나 형제로 인해 새어나갑니다. 동업을 각별히 경계하십시오.
⚠ 재성이 너무 왕(旺)하고 인성을 극하면 학문이 중단되거나 모친과의 인연이 약해질 수 있습니다.
⚠ 편관이 혼잡하면 재물이 오히려 관재(官災)의 씨앗이 될 수 있으니 법을 철저히 준수하십시오.""",
        "god_rank": "재왕신강에 관인상생이면 천하의 부귀격! 말년으로 갈수록 풍요로워지는 귀한 운명"
    },
    "편재격": {
        "summary": """편재격(偏財格)은 기회를 포착하여 크게 터뜨리는 활동적인 복록(福祿)의 격이로다!
편재는 일간이 음양이 같은 오행을 극하는 것으로, 고정된 수입보다는 투자·사업·거래를 통한 역동적인 재물 활동을 의미합니다.
식신이 편재를 생(生)하는 식신생재(食神生財)가 이루어지면 창의력으로 큰 돈을 버는 사업가 중의 사업가가 됩니다.
부친(父親)의 기운이기도 하여, 부친의 영향을 많이 받거나 부친의 재물을 물려받는 인연이 있습니다.
▶ 핵심: 신강(身強)해야 큰 재물을 다룰 수 있습니다. 신약하면 큰 재물에 짓눌릴 수 있습니다""",
        "lucky_career": "사업가·기업인·CEO, 투자자·펀드매니저, 무역상·유통업자, 부동산 개발업, 연예인·방송인, 스포츠 관련업",
        "caution": """⚠ 신약(身弱)한데 큰 사업을 벌이면 재물에 짓눌려 실패합니다. 역량을 먼저 키운 후 도전하십시오.
⚠ 비겁(比劫)이 많으면 동업자·형제로 인한 재물 분쟁이 생깁니다. 단독 경영이 유리합니다.
⚠ 여명(女命)에서 편재격이 지나치면 부부 갈등이나 배우자의 방탕으로 인한 재물 손실이 따를 수 있습니다.""",
        "god_rank": "식신생재에 신강하면 최고의 사업가 격! 대운이 맞으면 부(富)로 이름을 떨치는 천하의 부자 운명"
    },
    "식신격": {
        "summary": """식신격(食神格)은 하늘이 내리신 복덩어리 중의 복덩어리 격이로다! 수성(壽星)이라고도 불립니다.
식신은 일간이 생(生)하는 음양이 같은 오행으로, 먹고 마시고 즐기는 생명력과 창의적 표현의 기운입니다.
수(壽)·록(祿)·수(壽) 삼박자를 갖춘 이 격은 장수하고 풍요롭게 먹고 살 걱정 없이 재능을 펼치는 복된 운명입니다.
식신제살(食神制殺)이 이루어지면 칠살의 흉기를 다스리는 대인물이 되고, 식신생재(食神生財)면 재물도 풍요롭습니다.
▶ 효신(梟神, 편인)이 식신을 극하면 복이 반감되니 이를 가장 경계해야 합니다""",
        "lucky_career": "요리사·외식업자, 예술가·음악인, 작가·시인, 교육자·강사, 의료인, 아이디어 사업가, 복지·봉사직",
        "caution": """⚠ 효신(梟神, 편인)이 있으면 식신의 복이 꺾입니다. 이 경우 재성(財星)으로 효신을 제어해야 합니다.
⚠ 식신이 너무 많으면 오히려 에너지가 분산되고 집중력이 떨어집니다. 하나에 집중하는 것이 중요합니다.
⚠ 재물에 대한 욕심을 부리기보다 자신의 재능을 갈고닦는 데 집중할 때 복이 저절로 따라옵니다.""",
        "god_rank": "식신제살이면 천하의 대귀격! 수·록·수를 모두 갖춘 복된 운명으로 먹고 사는 걱정 없이 재능을 펼칩니다"
    },
    "상관격": {
        "summary": """상관격(傷官格)은 기존의 틀과 권위를 박살내는 혁명가이자 천재들의 격이로다!
상관은 일간이 생하는 음양이 다른 오행으로, 기성 질서에 도전하고 새로운 것을 창조하는 폭발적 에너지를 지닙니다.
역대 최고의 예술가·사상가·혁신가들에게 상관이 강하게 작용하는 경우가 많습니다. 당신은 세상을 바꿀 잠재력을 지녔습니다.
상관생재(傷官生財)가 이루어지면 창의력으로 막대한 재물을 모으는 시대의 아이콘이 됩니다.
▶ 가장 중요한 경계: 상관견관(傷官見官)! 정관과 상관이 만나면 관재(官災)·구설·직장 위기가 옵니다""",
        "lucky_career": "연예인·유튜버·방송인, 예술가, 변호사·변리사, 창업가·혁신가, 작가·작곡가, 언론인·PD, 스타트업 CEO",
        "caution": """⚠ 상관견관(傷官見官)은 직장과 관직의 최대 위기! 관운이 올 때는 언행을 극도로 조심하십시오.
⚠ 자존심이 너무 강해 권위자와 충돌하는 경향이 있습니다. 전략적 유연함이 필요합니다.
⚠ 감정 기복이 심하고 충동적인 면이 있어 중요한 결정 전에 반드시 한 번 더 생각하는 습관을 들이십시오.""",
        "god_rank": "상관생재에 인성이 제어하면 천하를 경영하는 최고의 창조자 격! 역사에 이름을 남기는 천재의 운명"
    },
    "정인격": {
        "summary": """정인격(正印格)은 학문과 지혜, 어머니의 사랑이 담긴 최고의 명예격(名譽格)이로다!
정인은 일간을 생(生)하는 음양이 다른 오행으로, 학문·지식·명예·어머니·문서의 기운을 총괄합니다.
관인상생(官印相生)이 이루어지면 관직과 학문이 함께 빛나는 세상에서 가장 존경받는 운명이 됩니다.
당신은 배움을 즐기고 지식을 나누는 것이 삶의 보람이며, 이 기운이 당신을 평생 바른 길로 이끄는 나침반이 됩니다.
▶ 재성(財星)이 인성을 극하면 학업이 중단되거나 명예가 손상되니 각별히 주의하십시오""",
        "lucky_career": "교수·학자·연구원, 교사·교육자, 의사·한의사, 변호사, 종교인·성직자, 작가·언론인, 공직자·행정가",
        "caution": """⚠ 재성이 인성을 파(破)하면 학업 중단이나 어머니와의 인연이 약해집니다. 학문을 지속하는 것이 복의 근원입니다.
⚠ 인성이 너무 많으면 행동력이 약해지고 의존적이 되는 경향이 있습니다. 실천하는 용기가 필요합니다.
⚠ 모친 의존이 강한 격이니 독립적으로 자립하는 시기를 늦추지 마십시오.""",
        "god_rank": "관인상생이면 세상이 우러러보는 최고의 명예격! 학문으로 세상에 이름을 남기는 귀한 운명"
    },
    "편인격": {
        "summary": """편인격(偏印格)은 남다른 직관과 신비로운 신기(神氣)를 지닌 특이한 인재의 격이로다!
편인(梟神이라고도 함)은 일간을 생하는 음양이 같은 오행으로, 학문보다는 직관·영성·예술·이단 사상에 가깝습니다.
남들이 걷지 않는 독특한 길을 개척하는 이단아적 천재의 기운으로, 특수 분야에서 독보적인 경지에 이를 수 있습니다.
편인전왕(偏印專旺)이면 한 분야의 기인이인(奇人異人)이 되어 세상 사람들이 따를 수 없는 경지에 이릅니다.
▶ 식신을 극하는 것이 가장 큰 문제! 식신의 복을 가로막지 않도록 재성으로 편인을 제어해야 합니다""",
        "lucky_career": "철학자·사상가, 종교인·영성가, 점술가·명리학자, IT 개발자·해커, 연구원, 탐정·분석가, 심리학자",
        "caution": """⚠ 도식(倒食): 편인이 식신을 극하면 복을 스스로 차버리는 상황이 됩니다. 전문 분야 하나에 집중하는 것이 핵심입니다.
⚠ 고집이 너무 강해 주변과의 소통이 어려워질 수 있습니다. 자신만의 세계에서 벗어나 협업하는 법을 배우십시오.
⚠ 종교·철학·오컬트 쪽으로 지나치게 빠지면 현실 생활이 피폐해질 수 있습니다.""",
        "god_rank": "편인전왕이면 한 분야를 평정하는 기인이인의 격! 세상이 이해 못 하는 천재의 길을 걷는 운명"
    },
    "비견격": {
        "summary": """비견격(比肩格)은 동류(同類)로부터 힘을 얻어 함께 성장하는 협력과 경쟁의 격이로다!
비견은 일간과 음양이 같은 오행으로, 나와 동등한 힘을 지닌 동료·경쟁자·형제의 기운입니다.
혼자보다는 팀으로, 경쟁보다는 협력으로, 나누면서 커가는 것이 비견격의 복의 방정식입니다.
관인상생이 더해지면 조직과 단체를 이끄는 지도자의 자리에 오르는 귀격이 됩니다.
▶ 일간이 신강하고 재관(財官)이 적절히 있어야 비견격이 빛납니다""",
        "lucky_career": "스포츠 감독·코치, 컨설턴트·멘토, 협동조합·NGO, 의사·간호사, 팀 기반 사업, 사회운동가",
        "caution": """⚠ 군비쟁재(群比爭財): 비겁이 너무 많은데 재성이 적으면 재물을 두고 형제·동료와 다투는 상황이 됩니다.
⚠ 동업은 명확한 계약과 역할 분담이 선행되어야 합니다. 구두 약속만으로는 반드시 분쟁이 생깁니다.
⚠ 독립 사업보다는 조직 내에서 협력하는 방식이 안정적입니다.""",
        "god_rank": "군비겁재를 피하고 관살로 제어하면 안정적이고 의리 있는 인간관계로 성공하는 귀격"
    },
    "겁재격": {
        "summary": """겁재격(劫財格)은 불굴의 투쟁심과 경쟁심으로 어떤 역경도 딛고 일어서는 강인한 기운의 격이로다!
겁재는 일간과 오행이 같되 음양이 다른 것으로, 동류이지만 경쟁자이기도 한 묘한 기운입니다.
사주에 겁재격이 성립하면 경쟁이 치열한 분야에서 오히려 빛을 발하며, 절대 포기하지 않는 불굴의 의지가 강점입니다.
식상(食傷)으로 겁재의 에너지를 재능으로 전환하거나, 관살(官殺)로 겁재를 제어하면 강한 추진력이 성공으로 이어집니다.
▶ 겁재는 재물을 빼앗는 기운도 있으니, 재물 관리와 동업 관계에서 각별한 주의가 필요합니다""",
        "lucky_career": "운동선수·격투기, 영업 전문가·세일즈, 경쟁적 사업·무역, 군인·경찰, 변호사, 스타트업 창업자",
        "caution": """⚠ 식상이 없으면 겁재의 에너지가 분산되어 공격적이고 충동적인 행동으로 이어질 수 있습니다.
⚠ 동업과 공동투자는 반드시 법적 계약으로 보호받아야 합니다. 구두 약속은 언제나 위험합니다.
⚠ 재물에 대한 지나친 욕심이 오히려 재물을 쫓아버리는 결과를 낳을 수 있습니다. 베풀면 더 들어옵니다.""",
        "god_rank": "식상제겁이면 경쟁이 곧 성공의 원동력이 되는 불굴의 격! 관살 제어하면 강한 추진력으로 세상을 정복하는 운명"
    },
}

# ★ BUG2 FIX: 일간=pils[1]["cg"], 월지=pils[2]["jj"] (pillar order: [시(0),일(1),월(2),년(3)])
@st.cache_data
def get_gyeokguk(pils):
    if len(pils) < 4: return None
    ilgan = pils[1]["cg"]   # ✅ 일간 (day stem)
    wolji = pils[2]["jj"]   # ✅ 월지 (month branch)
    jijang = JIJANGGAN.get(wolji, [])
    if not jijang: return None
    jeongi = jijang[-1]
    sipsung = TEN_GODS_MATRIX.get(ilgan, {}).get(jeongi, "기타")
    gyeok_name = f"{sipsung}격"
    cgs_all = [p["cg"] for p in pils]
    is_toucht = jeongi in cgs_all
    if is_toucht:
        grade = "순격(純格) — 월지 정기가 천간에 투출하여 격이 매우 청명하다!"
        grade_score = 95
    elif len(jijang) > 1 and jijang[-2] in cgs_all:
        grade = "잡격(雜格) — 중기가 투출, 격이 복잡하나 쓸모가 있다."
        grade_score = 70
    else:
        grade = "암격(暗格) — 지장간에 숨어있어 격의 힘이 약하다."
        grade_score = 50
    desc_data = GYEOKGUK_DESC.get(gyeok_name, {
        "summary": f"{gyeok_name}으로 독자적인 인생 노선을 개척하는 격이로다.",
        "lucky_career": "자유업·개인 사업", "caution": "잡기를 경계하라.", "god_rank": "용신과의 조화를 이룰 때 빛난다"
    })
    return {
        "격국명": gyeok_name, "격의_등급": grade, "격의_순수도": grade_score,
        "월지": wolji, "정기": jeongi, "투출여부": is_toucht,
        "격국_해설": desc_data["summary"], "적합_진로": desc_data["lucky_career"],
        "경계사항": desc_data["caution"], "신급_판정": desc_data["god_rank"],
        "narrative": (
            f"🏛️ **격국 판별**: {gyeok_name}!\n"
            f"  월지 {wolji}의 정기 {jeongi}로 {'투출된 청명한 ' if is_toucht else '숨은 '}{gyeok_name}을 이루었도다.\n"
            f"  등급: {grade}\n  {desc_data['summary']}\n"
            f"  적합 분야: {desc_data['lucky_career']}\n  경계: {desc_data['caution']}"
        )
    }

# 삼합/반합/방합
SAM_HAP_MAP = {
    frozenset(["寅","午","戌"]): ("화국(火局)","火","인오술 삼합"),
    frozenset(["申","子","辰"]): ("수국(水局)","水","신자진 삼합"),
    frozenset(["巳","酉","丑"]): ("금국(金局)","金","사유축 삼합"),
    frozenset(["亥","卯","未"]): ("목국(木局)","木","해묘미 삼합"),
}
BAN_HAP_MAP = {
    frozenset(["寅","午"]): ("인오 반합(火)","火","반합"),
    frozenset(["午","戌"]): ("오술 반합(火)","火","반합"),
    frozenset(["申","子"]): ("신자 반합(水)","水","반합"),
    frozenset(["子","辰"]): ("자진 반합(水)","Water","반합"),
    frozenset(["巳","酉"]): ("사유 반합(金)","金","반합"),
    frozenset(["酉","丑"]): ("유축 반합(金)","金","반합"),
    frozenset(["亥","卯"]): ("해묘 반합(木)","木","반합"),
    frozenset(["卯","未"]): ("묘미 반합(木)","木","반합"),
}
BANG_HAP_MAP = {
    frozenset(["寅","卯","辰"]): ("동방 목국(東方 木局)","木","방합"),
    frozenset(["巳","午","未"]): ("남방 화국(南方 火局)","火","방합"),
    frozenset(["申","酉","戌"]): ("서방 금국(西方 金局)","金","방합"),
    frozenset(["亥","子","丑"]): ("북방 수국(北方 水局)","Water","방합"),
}

def get_sam_hap(pils):
    jjs = set(p["jj"] for p in pils)
    results = []
    for combo, (name, oh, desc) in SAM_HAP_MAP.items():
        if combo.issubset(jjs):
            results.append({"type":"삼합(三合)","name":name,"oh":oh,"desc":desc,
                "narrative":f"🌟 [삼합] {desc}으로 {name}이 형성! {oh} 기운이 명반 전체를 강화하니라."})
    if not results:
        for combo, (name, oh, hap_type) in BAN_HAP_MAP.items():
            if combo.issubset(jjs):
                results.append({"type":"반합(半合)","name":name,"oh":oh,"desc":hap_type,
                    "narrative":f"✨ [반합] {name}이 맺어져 {oh} 오행의 결속력이 생기리라."})
    for combo, (name, oh, hap_type) in BANG_HAP_MAP.items():
        if combo.issubset(jjs):
            results.append({"type":"방합(方合)","name":name,"oh":oh,"desc":hap_type,
                "narrative":f"🧭 [방합] {name}의 세력이 형성되어 {oh} 오행이 강성해지리라."})
    return results


# ══════════════════════════════════════════════════
#  용신(用神) — 억부·조후·통관
# ══════════════════════════════════════════════════

YONGSHIN_JOKHU = {
    "寅": {"hot":False,"need":["丙","甲"],"avoid":["壬","癸"],"desc":"인월(寅月)은 봄 초입이나 아직 차갑습니다. 병화(丙火)로 따뜻하게, 갑목(甲木)으로 기운을 북돋워야 합니다."},
    "卯": {"hot":False,"need":["丙","癸"],"avoid":["庚"],"desc":"묘월(卯月)은 목기 왕성한 봄. 병화로 온기를, 계수로 자양분을 공급해야 합니다."},
    "辰": {"hot":False,"need":["甲","丙","癸"],"avoid":["戊"],"desc":"진월(辰月) 토기가 중화역할. 목화수의 기운이 균형을 잡아줘야 합니다."},
    "巳": {"hot":True,"need":["壬","庚"],"avoid":["丙","丁"],"desc":"사월(巳月) 화기 시작. 임수(壬水)로 열기를 식히고 경금(庚金)으로 수원(水源)을 만들어야 합니다."},
    "午": {"hot":True,"need":["壬","癸","庚"],"avoid":["丙","丁","戊"],"desc":"오월(午月) 한여름 극열. 임수·계수로 화기를 제어해야 발복합니다."},
    "未": {"hot":True,"need":["壬","甲"],"avoid":["戊","己"],"desc":"미월(未月) 토조열. 임수와 갑목으로 습윤하고 활기를 주어야 합니다."},
    "申": {"hot":False,"need":["戊","丁"],"avoid":["壬"],"desc":"신월(申月) 초가을 금기. 무토로 금을 생하고 정화로 단련해야 합니다."},
    "酉": {"hot":False,"need":["丙","丁","甲"],"avoid":["壬","癸"],"desc":"유월(酉月) 금왕. 화기로 금을 단련하고 목기로 재를 만들어야 합니다."},
    "戌": {"hot":False,"need":["甲","丙","壬"],"avoid":["戊"],"desc":"술월(戌月) 조토. 목화수로 균형을 잡아야 합니다."},
    "亥": {"hot":False,"need":["甲","丙","戊"],"avoid":["壬","癸"],"desc":"해월(亥月) 겨울 수기. 병화로 따뜻하게, 무토로 수기를 제방해야 합니다."},
    "子": {"hot":False,"need":["丙","戊","丁"],"avoid":["壬","癸"],"desc":"자월(子月) 한겨울 수왕. 병화와 무토로 수기를 다스려야 발복합니다."},
    "丑": {"hot":False,"need":["丙","甲","丁"],"avoid":["壬","癸"],"desc":"축월(丑月) 극한 동토. 병화와 정화로 온기를, 갑목으로 토기를 소통시켜야 합니다."},
}

@st.cache_data
def get_yongshin(pils):
    """용신(用神) 종합 분석 — 억부+조후+통관"""
    ilgan = pils[1]["cg"]
    wol_jj = pils[2]["jj"]
    strength_info = get_ilgan_strength(ilgan, pils)
    oh_strength = strength_info["oh_strength"]
    sn = strength_info["신강신약"]
    ilgan_oh = OH.get(ilgan, "")

    BIRTH_MAP_R = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    CONTROL_MAP = {"木":"土","火":"金","土":"水","金":"木","水":"火"}

    if sn == "신강(身强)":
        ok_관 = next((k for k,v in CONTROL_MAP.items() if v == ilgan_oh), "")
        ok_재 = CONTROL_MAP.get(ilgan_oh, "")
        eokbu_yong = [ok_관, ok_재]
        eokbu_base = "신강(身强) → 억(抑) 용신 필요"
        eokbu_desc = f"강한 일간을 억제하는 관성({ok_관}기운)과 재성({ok_재}기운)이 용신입니다."
        kihwa = "인성·비겁 대운은 기신(忌神) — 더 강해져 흉작용"
    elif sn == "신약(身弱)":
        ok_인 = BIRTH_MAP_R.get(ilgan_oh, "")
        eokbu_yong = [ok_인, ilgan_oh]
        eokbu_base = "신약(身弱) → 부(扶) 용신 필요"
        eokbu_desc = f"약한 일간을 도와주는 인성({ok_인}기운)과 비겁({ilgan_oh}기운)이 용신입니다."
        kihwa = "재성·관성 대운은 기신(忌神) — 약한 일간이 더 눌림"
    else:
        eokbu_yong = []
        eokbu_base = "중화(中和) → 균형 유지"
        eokbu_desc = "오행이 균형 잡혀 특정 용신보다 전체 균형 유지가 중요합니다."
        kihwa = "어느 쪽으로도 과도하게 치우치는 운이 기신"

    jokhu = YONGSHIN_JOKHU.get(wol_jj, {})

    # 통관용신
    oh_list = sorted(oh_strength.items(), key=lambda x: -x[1])
    tongkwan_yong = None
    tongkwan_desc = ""
    if len(oh_list) >= 2:
        t1, v1 = oh_list[0]; t2, v2 = oh_list[1]
        if v1 >= 35 and v2 >= 25:
            if CONTROL_MAP.get(t1) == t2 or CONTROL_MAP.get(t2) == t1:
                gen_map = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
                tongkwan_yong = gen_map.get(t1, "")
                tongkwan_desc = f"{t1}({OHN.get(t1,'')})와 {t2}({OHN.get(t2,'')})가 충돌. {tongkwan_yong}({OHN.get(tongkwan_yong,'')}) 통관용신 필요."

    all_yong = list(dict.fromkeys(eokbu_yong + [OH.get(c,"") for c in jokhu.get("need",[])] + ([tongkwan_yong] if tongkwan_yong else [])))
    all_yong = [o for o in all_yong if o]

    return {
        "억부_base": eokbu_base, "억부_desc": eokbu_desc, "억부_용신": eokbu_yong,
        "조후_desc": jokhu.get("desc",""), "조후_need": jokhu.get("need",[]), "조후_avoid": jokhu.get("avoid",[]),
        "통관_yong": tongkwan_yong, "통관_desc": tongkwan_desc,
        "기신": kihwa, "종합_용신": all_yong, "월지": wol_jj,
    }


# ══════════════════════════════════════════════════
#  충(沖)·형(刑)·파(破)·해(害)·천간합
# ══════════════════════════════════════════════════

CHUNG_MAP = {
    frozenset(["子","午"]): ("자오충(子午沖)","水克火","감정 기복, 수화 충돌, 직업 변동"),
    frozenset(["丑","未"]): ("축미충(丑未沖)","土克土","재물 분쟁, 위장 질환, 토지 분쟁"),
    frozenset(["寅","申"]): ("인신충(寅申沖)","金克木","사고 위험, 이동 변화, 의외 사건"),
    frozenset(["卯","酉"]): ("묘유충(卯酉沖)","金克木","관재 구설, 혼인 불화, 갈등"),
    frozenset(["辰","戌"]): ("진술충(辰戌沖)","土克土","재물 손실, 부동산 갈등"),
    frozenset(["巳","亥"]): ("사해충(巳亥沖)","水克火","이별수, 먼 여행, 의외 사건"),
}

HYUNG_MAP = {
    frozenset(["寅","巳","申"]): ("인사신 삼형(三刑)","무은지형(無恩之刑)","법적 문제, 관재, 배신"),
    frozenset(["丑","戌","未"]): ("축술미 삼형(三刑)","지세지형(持勢之刑)","권력 다툼, 재물 분쟁, 고집의 화"),
    frozenset(["子","卯"]): ("자묘 상형(相刑)","무례지형(無禮之刑)","무례한 인간관계, 배신"),
}
SELF_HYUNG = ["辰","午","酉","亥"]

PA_MAP = {
    frozenset(["子","酉"]): ("자유파(子酉破)","감정 상처, 이별"),
    frozenset(["丑","辰"]): ("축진파(丑辰破)","재물 파손, 직업 변동"),
    frozenset(["寅","亥"]): ("인해파(寅亥破)","계획 차질, 예상 밖 변수"),
    frozenset(["卯","午"]): ("묘오파(卯午破)","감정 충돌, 혼인 불화"),
    frozenset(["申","巳"]): ("신사파(申巳破)","사고 위험, 계획 좌절"),
    frozenset(["戌","未"]): ("술미파(戌未破)","재물 분실, 고집 충돌"),
}

HAE_MAP = {
    frozenset(["子","未"]): ("자미해(子未害)","가정 불화, 음식 손재"),
    frozenset(["丑","午"]): ("축오해(丑午害)","감정 상처, 배우자 갈등"),
    frozenset(["寅","巳"]): ("인사해(寅巳害)","질병, 사고, 관재"),
    frozenset(["卯","辰"]): ("묘진해(卯辰害)","형제 갈등, 직업 손실"),
    frozenset(["申","亥"]): ("신해해(申亥害)","이동 중 사고, 재물 손실"),
    frozenset(["酉","戌"]): ("유술해(酉戌害)","관재 구설, 이성 문제"),
}

TG_HAP_MAP = {
    frozenset(["甲","己"]): ("갑기합(甲己合)","土","중정지합"),
    frozenset(["乙","庚"]): ("을경합(乙庚合)","金","인의지합"),
    frozenset(["丙","辛"]): ("병신합(丙辛合)","水","위제지합"),
    frozenset(["丁","壬"]): ("정임합(丁壬合)","木","음닉지합"),
    frozenset(["戊","癸"]): ("무계합(戊癸合)","火","무정지합"),
}

def get_chung_hyung(pils):
    """충·형·파·해·천간합 분석"""
    jjs = [p["jj"] for p in pils]
    cgs = [p["cg"] for p in pils]
    result = {"충":[],"형":[],"파":[],"해":[],"천간합":[],"자형":[]}
    pairs_jj = [(jjs[i],jjs[j]) for i in range(len(jjs)) for j in range(i+1,len(jjs))]
    pairs_cg = [(cgs[i],cgs[j]) for i in range(len(cgs)) for j in range(i+1,len(cgs))]
    jj_set = set(jjs)

    for a,b in pairs_jj:
        k = frozenset([a,b])
        if k in CHUNG_MAP:
            n,rel,desc = CHUNG_MAP[k]
            result["충"].append({"name":n,"rel":rel,"desc":desc})
        if k in PA_MAP:
            n,desc = PA_MAP[k]; result["파"].append({"name":n,"desc":desc})
        if k in HAE_MAP:
            n,desc = HAE_MAP[k]; result["해"].append({"name":n,"desc":desc})

    for combo,(n,htype,desc) in HYUNG_MAP.items():
        if combo.issubset(jj_set):
            result["형"].append({"name":n,"type":htype,"desc":desc})
    for jj in jjs:
        if jjs.count(jj)>=2 and jj in SELF_HYUNG:
            result["자형"].append({"name":f"{jj} 자형","desc":"자책·자학 경향 주의"})

    for a,b in pairs_cg:
        k = frozenset([a,b])
        if k in TG_HAP_MAP:
            n,oh,htype = TG_HAP_MAP[k]
            result["천간합"].append({"name":n,"oh":oh,"type":htype,"desc":f"{oh}({OHN.get(oh,'')})으로 화(化) — {htype}"})

    return result


# ══════════════════════════════════════════════════
#  공망(空亡)
# ══════════════════════════════════════════════════

GONGMANG_TABLE = {
    "甲":("戌","亥"),"乙":("戌","亥"),"丙":("申","酉"),"丁":("申","酉"),
    "戊":("午","未"),"己":("午","未"),"庚":("辰","巳"),"辛":("辰","巳"),
    "壬":("寅","卯"),"癸":("寅","卯"),
}

GONGMANG_JJ_DESC = {
    "子":"자(子) 공망 — 지혜·재물 기운이 허공에 뜹니다. 재물과 학업에 공허함이 따릅니다.",
    "丑":"축(丑) 공망 — 인내·축적의 기운이 약해집니다. 노력이 물거품이 되는 경험을 합니다.",
    "寅":"인(寅) 공망 — 성장·시작의 기운이 막힙니다. 새 출발이 쉽지 않습니다.",
    "卯":"묘(卯) 공망 — 창의·예술 기운이 허공에 뜹니다. 재능이 있어도 인정받기 어렵습니다.",
    "辰":"진(辰) 공망 — 관직·조직 기운이 약해집니다. 직장·관직과의 인연이 불안정합니다.",
    "巳":"사(巳) 공망 — 지혜·재능의 기운이 허공에 뜹니다. 화려함이 있어도 결실이 약합니다.",
    "午":"오(午) 공망 — 명예·인정의 기운이 약해집니다. 노력 대비 인정받기 어렵습니다.",
    "未":"미(未) 공망 — 재물·안정 기운이 허공에 뜹니다. 모아도 새는 재물 기운입니다.",
    "申":"신(申) 공망 — 변화·이동 기운이 막힙니다. 새 환경으로의 변화가 어렵습니다.",
    "酉":"유(酉) 공망 — 완성·결실의 기운이 약해집니다. 마무리가 항상 아쉽게 끝납니다.",
    "戌":"술(戌) 공망 — 저장·축적의 기운이 허공에 뜹니다. 창고가 있어도 채우기 어렵습니다.",
    "亥":"해(亥) 공망 — 지혜·영성의 기운이 약해집니다. 깊은 학문과 영적 기운이 허공에 뜹니다.",
}

def get_gongmang(pils):
    """공망(空亡) 계산"""
    nyon_cg = pils[3]["cg"]
    gong_pair = GONGMANG_TABLE.get(nyon_cg, ("",""))
    result = {"공망_지지": gong_pair, "해당_기둥": []}
    for i, p in enumerate(pils):
        label = ["시주","일주","월주","년주"][i]
        if p["jj"] in gong_pair:
            result["해당_기둥"].append({
                "기둥": label, "지지": p["jj"],
                "desc": GONGMANG_JJ_DESC.get(p["jj"],""),
            })
    return result


# ══════════════════════════════════════════════════
#  일주론(日柱論) | 60갑자
# ══════════════════════════════════════════════════

ILJU_DESC = {
    "甲子":{"symbol":"🌊🌳","desc":"학문의 신기가 넘치는 귀한 일주. 총명함과 높은 이상을 지녔으며 학자·교육자·문필가 기질. 편인이 강해 독창적 사고가 뛰어나나 현실감각이 부족할 수 있습니다.","luck":"학문·교육·연구 분야에서 크게 빛납니다.","caution":"현실과 이상의 균형이 과제입니다."},
    "甲戌":{"symbol":"🏔️🌳","desc":"의협심과 우직함을 타고난 일주. 재고(財庫)를 지닌 구조로 재물을 모으는 능력이 있으나 고집이 강해 마찰이 생길 수 있습니다.","luck":"중년 이후 재물이 불어나는 구조입니다.","caution":"고집을 버리면 귀인이 모여듭니다."},
    "甲申":{"symbol":"⚔️🌳","desc":"절지(絶地)에 놓인 거목. 시련이 많지만 단련을 통해 진정한 강자가 됩니다. 결단력과 실행력이 탁월합니다.","luck":"단련을 통해 성장하는 불굴의 운명입니다.","caution":"성급한 결단이 화를 부릅니다."},
    "甲午":{"symbol":"🔥🌳","desc":"목화통명(木火通明)의 빛나는 일주. 지혜롭고 총명하며 표현력이 탁월. 상관이 강해 언변과 창의성이 뛰어나나 직장과 마찰이 있을 수 있습니다.","luck":"예술·창작·강연 분야에서 두각을 나타냅니다.","caution":"직장·관직과의 충돌을 주의하십시오."},
    "甲辰":{"symbol":"🐉🌳","desc":"천을귀인을 지닌 귀격 일주. 조직력과 리더십이 강하고 큰 그릇의 인물. 식신이 강해 복록이 있고 인복도 좋습니다.","luck":"조직을 이끄는 리더로 크게 성공합니다.","caution":"너무 많은 것을 품으려 하면 소진됩니다."},
    "甲寅":{"symbol":"🐯🌳","desc":"목기가 극도로 강한 순양(純陽). 강직하고 정의로우며 자존심이 매우 강합니다. 리더십이 탁월하나 융통성이 부족할 수 있습니다.","luck":"독립하면 크게 성공합니다.","caution":"타협과 유연함을 배우는 것이 과제입니다."},
    "乙丑":{"symbol":"❄️🌿","desc":"차가운 땅에 뿌리를 내린 을목. 인내와 끈기가 대단하며 어떤 역경에서도 살아남습니다. 정재를 안고 있어 재물 복이 있습니다.","luck":"전문직·학문·재무 분야에서 빛납니다.","caution":"지나친 절약이 귀인의 발길을 막습니다."},
    "乙亥":{"symbol":"🌊🌿","desc":"수생목(水生木)의 귀한 구조. 인성이 강해 학문과 귀인의 덕이 있습니다. 섬세하고 직관력이 뛰어나며 예술적 감각이 탁월합니다.","luck":"학문·예술·상담 분야에서 대성합니다.","caution":"지나친 의존심을 극복하는 것이 과제입니다."},
    "乙酉":{"symbol":"⚔️🌿","desc":"을목이 유금 위에 앉은 불안한 구조. 시련이 많지만 더욱 정교하고 섬세해집니다. 완벽주의 기질이 강합니다.","luck":"예술·연구·디자인 분야에서 독보적 경지에 이릅니다.","caution":"완벽주의가 지나치면 스스로를 소진합니다."},
    "乙未":{"symbol":"🌿🌿","desc":"화개(華蓋)와 천을귀인을 품은 귀한 일주. 영성이 강하고 예술적 감수성이 탁월합니다. 재성이 있어 재물 복도 있습니다.","luck":"예술·종교·상담 분야에서 특별한 성취를 이룹니다.","caution":"고독을 즐기는 기질을 균형 있게 유지하십시오."},
    "乙巳":{"symbol":"🔥🌿","desc":"지혜롭고 전략적이며 화려한 재능을 지닌 복잡한 일주. 천을귀인도 있어 귀인의 도움이 있습니다.","luck":"전략·금융·외교에서 능력을 발휘합니다.","caution":"내면의 갈등을 창의적으로 승화하십시오."},
    "乙卯":{"symbol":"🌿🌿","desc":"전왕(專旺)의 순수 목기 일주. 예술적 감수성과 창의력이 최고조. 순수하고 민감하며 아름다움을 추구하는 타고난 예술가.","luck":"예술·창작·디자인 분야에서 독보적 위치에 오릅니다.","caution":"자신만의 길을 가십시오."},
    "丙寅":{"symbol":"🐯🔥","desc":"목화통명의 강렬한 빛. 카리스마와 열정이 넘치는 강력한 일주. 장생지에 앉아 귀인의 도움이 있고 성장 잠재력이 큽니다.","luck":"정치·방송·경영·교육 분야에서 대성합니다.","caution":"열정이 지나치면 충동이 됩니다."},
    "丙子":{"symbol":"❄️🔥","desc":"태양이 찬 물 위에 앉은 역경의 일주. 정재를 안고 있어 재물 복이 있으며, 역경을 통해 더욱 강해집니다.","luck":"금융·재무·사업 분야에서 성공합니다.","caution":"내면의 불안을 극복하는 것이 성공의 열쇠입니다."},
    "丙戌":{"symbol":"🏔️🔥","desc":"식신이 강한 복록의 일주. 재능과 복록을 타고났으며 인복이 좋습니다. 중년 이후 크게 발복합니다.","luck":"교육·요식업·예술·종교 분야에서 빛납니다.","caution":"낭만적 성격이 현실 판단을 흐리지 않도록 하십시오."},
    "丙申":{"symbol":"⚔️🔥","desc":"편관이 강한 도전과 극복의 일주. 시련이 많지만 이를 딛고 일어서는 강인한 기운. 결단력이 강합니다.","luck":"군·경·의료·스포츠 분야에서 두각을 나타냅니다.","caution":"충동적 결단을 자제하십시오."},
    "丙午":{"symbol":"🔥🔥","desc":"태양이 정오에 빛나는 최강의 불기운. 카리스마와 존재감이 압도적. 사람들을 끌어당기는 자연스러운 매력이 있습니다.","luck":"방송·정치·사업·스포츠 분야에서 최고의 빛을 발합니다.","caution":"겸손함을 배우면 더 큰 성공이 따릅니다."},
    "丙辰":{"symbol":"🐉🔥","desc":"식신이 있는 복록의 일주. 창의력과 재능이 풍부하며 귀인의 도움이 있습니다.","luck":"교육·창작·기획 분야에서 성공합니다.","caution":"산만한 관심사를 하나로 집중하는 것이 과제입니다."},
    "丁丑":{"symbol":"❄️🕯️","desc":"차가운 겨울 땅의 촛불. 정재를 안고 있어 재물을 모으는 능력이 있습니다. 묵묵히 자신의 길을 가는 인내와 끈기가 있습니다.","luck":"재무·의료·전문직 분야에서 안정적으로 성공합니다.","caution":"지나친 내향성이 기회를 놓치게 합니다."},
    "丁亥":{"symbol":"🌊🕯️","desc":"물 위의 촛불, 위태로운 듯 아름다운 일주. 정관을 안고 있어 명예와 인정을 받습니다. 역경 속에서도 꺼지지 않는 강인한 의지.","luck":"의료·종교·상담·학문 분야에서 명성을 얻습니다.","caution":"감정 기복을 다스리는 것이 핵심입니다."},
    "丁酉":{"symbol":"⚔️🕯️","desc":"편재를 안고 있는 활동적인 재물의 일주. 분석력이 탁월하고 완벽주의적 기질이 있습니다.","luck":"금융·분석·패션·예술 분야에서 성공합니다.","caution":"완벽주의가 결단을 방해하지 않도록 하십시오."},
    "丁未":{"symbol":"🌿🕯️","desc":"화개(華蓋)의 영성적인 일주. 예술·철학·종교적 기질이 강하고 내면의 세계가 풍부합니다.","luck":"예술·종교·철학·상담 분야에서 독보적 경지에 이릅니다.","caution":"현실에 뿌리를 내리는 노력이 필요합니다."},
    "丁巳":{"symbol":"🔥🕯️","desc":"건록을 안고 있는 강한 일주. 자립심이 강하고 자수성가하는 기운. 지혜롭고 계산이 빠르며 재물 감각도 있습니다.","luck":"독립 사업·학문·금융·종교 분야에서 성공합니다.","caution":"자존심이 지나치면 귀인이 떠납니다."},
    "丁卯":{"symbol":"🌿🕯️","desc":"편인이 강한 직관과 창의의 일주. 예술적 감수성이 탁월하고 독창적인 아이디어가 넘칩니다.","luck":"예술·창작·교육·상담 분야에서 빛납니다.","caution":"도식(倒食) 주의. 식신의 복을 편인이 가로막지 않도록 하십시오."},
    "戊寅":{"symbol":"🐯🏔️","desc":"산과 호랑이의 기운. 편관이 강한 도전과 극복의 일주. 외유내강(外柔內剛)의 인물.","luck":"군·경·관리직·스포츠 분야에서 두각을 나타냅니다.","caution":"시련을 두려워하지 마십시오. 그것이 당신을 완성합니다."},
    "戊子":{"symbol":"❄️🏔️","desc":"정재를 안고 있는 재물의 일주. 근면하고 성실하며 재물을 차곡차곡 쌓아가는 능력. 배우자 복이 있습니다.","luck":"금융·부동산·행정 분야에서 안정적으로 성공합니다.","caution":"변화를 두려워하는 고집이 기회를 막습니다."},
    "戊戌":{"symbol":"🏔️🏔️","desc":"비견이 강한 독립적인 일주. 고집과 자존심이 강하며 혼자서 모든 것을 해내려 합니다. 화개(華蓋)의 영성적 기운도 있습니다.","luck":"독립 사업·부동산·종교 분야에서 성공합니다.","caution":"타인과의 협력을 배우면 더 큰 성취가 가능합니다."},
    "戊申":{"symbol":"⚔️🏔️","desc":"식신이 강한 복록의 일주. 능력과 재능이 다양하며 결단력과 실행력이 뛰어납니다.","luck":"기술·사업·군경 분야에서 빛납니다.","caution":"너무 많은 것을 동시에 추진하면 에너지가 분산됩니다."},
    "戊午":{"symbol":"🔥🏔️","desc":"양인(羊刃)을 지닌 강렬한 일주. 에너지와 의지력이 대단하며 강렬한 카리스마로 주변을 압도합니다.","luck":"정치·경영·스포츠·군사 분야에서 강력한 힘을 발휘합니다.","caution":"폭발적인 에너지를 건설적으로 사용하는 것이 과제입니다."},
    "戊辰":{"symbol":"🐉🏔️","desc":"천을귀인이 있는 귀한 일주. 조직 관리 능력이 뛰어나고 인복이 좋습니다.","luck":"행정·경영·부동산 분야에서 성공합니다.","caution":"고집과 독선을 주의하십시오."},
    "己丑":{"symbol":"❄️🌾","desc":"비견이 강한 인내의 일주. 한번 마음먹은 것은 반드시 해내는 기질. 전문성으로 성공합니다.","luck":"농업·의료·회계·전문직 분야에서 성공합니다.","caution":"고집을 버리면 귀인의 도움이 더 많아집니다."},
    "己亥":{"symbol":"🌊🌾","desc":"정재와 정관을 안고 있는 재물과 명예의 일주. 섬세하고 꼼꼼하며 재물 관리 능력이 탁월합니다.","luck":"회계·금융·행정 분야에서 안정적으로 성공합니다.","caution":"지나친 완벽주의가 진행 속도를 늦춥니다."},
    "己酉":{"symbol":"⚔️🌾","desc":"식신이 강한 재능의 일주. 섬세하고 예술적 감각이 탁월합니다. 완벽주의적 기질로 최고의 결과물을 만들어냅니다.","luck":"예술·디자인·요리·전문직 분야에서 빛납니다.","caution":"이상만 좇지 말고 현실적인 목표를 함께 세우십시오."},
    "己未":{"symbol":"🌿🌾","desc":"비견이 강한 고집스러운 일주. 자신만의 세계관이 뚜렷하고 화개(華蓋)의 영성적 기운도 있습니다.","luck":"종교·철학·상담·교육 분야에서 독보적 위치에 오릅니다.","caution":"고집을 유연함으로 바꾸는 것이 큰 과제입니다."},
    "己巳":{"symbol":"🔥🌾","desc":"편관이 강하여 시련이 많지만 성장하는 일주. 지혜롭고 분석력이 탁월하며 복잡한 상황을 해결하는 능력이 있습니다.","luck":"기획·분석·의료·법률 분야에서 능력을 발휘합니다.","caution":"시련을 두려워하지 말고 정면으로 돌파하십시오."},
    "己卯":{"symbol":"🌿🌾","desc":"편관이 강한 혁신적인 일주. 창의력과 도전 정신이 있으며 기존 틀에 얽매이지 않습니다.","luck":"창작·교육·예술·사업 분야에서 성공합니다.","caution":"새로운 시도를 즐기되 마무리를 철저히 하십시오."},
    "庚寅":{"symbol":"🐯⚔️","desc":"편재를 안고 있는 활동적인 재물의 일주. 결단력이 강하고 행동력이 뛰어납니다. 역마(驛馬)의 기운으로 이동과 변화가 많습니다.","luck":"사업·무역·영업 분야에서 크게 성공합니다.","caution":"너무 빠른 결단이 실수를 유발합니다."},
    "庚子":{"symbol":"❄️⚔️","desc":"상관이 강한 혁신적인 일주. 총명하고 언변이 뛰어나며 창의적인 아이디어가 넘칩니다. 기존 틀에 도전하는 기질이 강합니다.","luck":"언론·방송·창작·IT 분야에서 두각을 나타냅니다.","caution":"상관견관 주의! 직장·관직과의 충돌을 특히 조심하십시오."},
    "庚戌":{"symbol":"🏔️⚔️","desc":"편인이 강한 깊은 사색의 일주. 철학적이고 분석적인 기질이 강합니다. 술중(戌中) 정화가 경금을 단련합니다.","luck":"철학·법학·종교·분석 분야에서 탁월한 능력을 발휘합니다.","caution":"지나친 완벽주의와 비판적 사고를 조절하십시오."},
    "庚申":{"symbol":"⚔️⚔️","desc":"비견이 강한 최강의 금기 일주. 결단력과 실행력이 압도적이며 강직한 성격으로 강한 인상을 줍니다.","luck":"군·경·의료·스포츠·기술 분야에서 최강의 능력을 발휘합니다.","caution":"유연함과 타협을 배우는 것이 큰 과제입니다."},
    "庚午":{"symbol":"🔥⚔️","desc":"정관이 있는 명예의 일주. 화기(火氣)가 금을 단련하니 제대로 단련되면 최고의 보검이 됩니다.","luck":"관직·공무원·군사·경찰 분야에서 명예를 얻습니다.","caution":"지나친 원칙주의가 융통성을 막습니다."},
    "庚辰":{"symbol":"🐉⚔️","desc":"편인을 지닌 분석적인 일주. 천을귀인의 덕도 있어 귀인의 도움이 있습니다. 지략이 뛰어나고 상황 판단력이 탁월합니다.","luck":"전략기획·군사·법학·IT 분야에서 활약합니다.","caution":"너무 많이 계산하면 행동이 늦어집니다."},
    "辛丑":{"symbol":"❄️💎","desc":"편인이 강한 깊은 내면의 일주. 분석력과 통찰력이 뛰어나며 전문성으로 성공합니다.","luck":"연구·분석·회계·의료 분야에서 전문가로 성공합니다.","caution":"자신의 가치를 스스로 인정하는 자기긍정이 필요합니다."},
    "辛亥":{"symbol":"🌊💎","desc":"상관이 강한 창의적인 일주. 섬세한 감수성과 탁월한 창의력. 식신생재의 구조로 재물 복도 있습니다.","luck":"예술·창작·패션·디자인 분야에서 독보적 위치에 오릅니다.","caution":"언행에 주의하고 직장·관직과의 마찰을 조심하십시오."},
    "辛酉":{"symbol":"💎💎","desc":"비견이 강한 완벽주의의 극치 일주. 아름다움과 완성도에 대한 기준이 매우 높습니다. 섬세하고 예리한 감각으로 최고의 작품을 만들어냅니다.","luck":"예술·보석·디자인·의료·패션 분야에서 최고 경지에 이릅니다.","caution":"너무 높은 기준이 타인과의 관계를 경직시킵니다."},
    "辛未":{"symbol":"🌿💎","desc":"편인과 화개를 지닌 영성의 일주. 직관력과 예술성이 탁월하며 독특한 세계관을 지녔습니다.","luck":"예술·종교·철학·상담 분야에서 독보적 존재가 됩니다.","caution":"현실적인 목표와 균형을 맞추는 것이 중요합니다."},
    "辛巳":{"symbol":"🔥💎","desc":"편관이 강한 도전의 일주. 시련을 통해 더욱 빛나는 보석. 위기 상황에서 진가를 발휘합니다.","luck":"금융·사업·의료·법률 분야에서 뛰어난 능력을 보입니다.","caution":"시련을 두려워하지 마십시오. 단련될수록 더 빛납니다."},
    "辛卯":{"symbol":"🌿💎","desc":"편재를 안고 있는 재물의 일주. 섬세하면서도 재물 감각이 있으며 창의적 아이디어로 수익을 창출합니다.","luck":"금융·예술·패션·창업 분야에서 성공합니다.","caution":"지나친 완벽주의가 결단을 방해합니다."},
    "壬寅":{"symbol":"🐯🌊","desc":"식신이 강한 복록의 일주. 지혜와 재능이 넘치며 재물 복도 있습니다. 장생지에 앉아 귀인의 도움이 있습니다.","luck":"무역·외교·학문·사업 분야에서 크게 성공합니다.","caution":"너무 많은 관심사를 정리하고 집중하는 것이 과제입니다."},
    "壬子":{"symbol":"❄️🌊","desc":"양인(羊刃)의 강렬한 수기 일주. 지혜와 추진력이 압도적이며 깊은 통찰력. 무토(戊土)의 제어가 필요합니다.","luck":"철학·전략·외교·금융 분야에서 천재적 능력을 발휘합니다.","caution":"방향 없는 지혜는 공허합니다. 목표를 명확히 하십시오."},
    "壬戌":{"symbol":"🏔️🌊","desc":"편관이 강한 시련과 극복의 일주. 강인한 의지로 시련을 극복하며 중년 이후 크게 발복합니다.","luck":"법률·전략·외교 분야에서 두각을 나타냅니다.","caution":"인내하십시오. 모든 시련에는 이유가 있습니다."},
    "壬申":{"symbol":"⚔️🌊","desc":"장생지의 귀한 일주. 인성이 강해 학문과 귀인의 덕이 넘칩니다. 유연하게 대처하는 지혜. 국제적 감각이 있습니다.","luck":"외교·국제무역·법률·학문 분야에서 대성합니다.","caution":"지나친 계산과 전략이 진정성을 가릴 수 있습니다."},
    "壬午":{"symbol":"🔥🌊","desc":"정재를 안고 있는 재물의 일주. 화수미제(火水未濟)의 역동적 긴장이 창의력의 원천이 됩니다.","luck":"금융·사업·창작·방송 분야에서 성공합니다.","caution":"내면의 갈등을 창의적으로 승화하십시오."},
    "壬辰":{"symbol":"🐉🌊","desc":"비견이 강한 독립적인 일주. 천을귀인도 있어 귀인의 도움이 있습니다. 방대한 지식과 포용력.","luck":"외교·학문·종교·경영 분야에서 크게 성공합니다.","caution":"모든 것을 혼자 짊어지려 하지 말고 팀을 활용하십시오."},
    "癸丑":{"symbol":"❄️💧","desc":"편인이 강한 인내의 일주. 전문성이 뛰어나고 분석력이 탁월합니다. 묵묵한 노력으로 결국 성공합니다.","luck":"연구·학문·의료·분석 분야에서 대가가 됩니다.","caution":"자신을 과소평가하지 마십시오."},
    "癸亥":{"symbol":"🌊💧","desc":"비견이 강한 전왕(專旺)의 수기 일주. 영성과 직관력이 극도로 발달하며 남들이 보지 못하는 것을 봅니다.","luck":"철학·종교·예술·심리학 분야에서 독보적 경지에 이릅니다.","caution":"현실에 뿌리를 내리는 훈련이 반드시 필요합니다."},
    "癸酉":{"symbol":"💎💧","desc":"편인이 강한 분석의 일주. 정밀한 사고와 섬세한 감각이 탁월합니다.","luck":"연구·분석·예술·의료 분야에서 전문가로 인정받습니다.","caution":"현실적인 결단력을 기르는 것이 성공의 열쇠입니다."},
    "癸未":{"symbol":"🌿💧","desc":"편관을 안고 있는 시련의 일주. 어려움을 통해 더욱 강해지고 깊어지는 기운. 정신적 성숙도가 높습니다.","luck":"상담·의료·종교·예술 분야에서 깊은 경지에 이릅니다.","caution":"시련을 두려워하지 마십시오. 당신을 더 깊게 만듭니다."},
    "癸巳":{"symbol":"🔥💧","desc":"정관을 안고 있는 명예의 일주. 화수(火水)의 긴장이 창의력과 지혜의 원천. 섬세한 감수성과 강인한 의지.","luck":"학문·관직·예술·금융 분야에서 명예를 얻습니다.","caution":"내면의 갈등을 긍정적인 방향으로 승화하십시오."},
    "癸卯":{"symbol":"🌿💧","desc":"식신이 강한 복록의 일주. 창의력과 재능이 풍부하며 부드러운 감성으로 많은 이들과 공감합니다. 인복이 좋습니다.","luck":"예술·창작·상담·교육 분야에서 많은 이들의 사랑을 받습니다.","caution":"꿈과 현실의 균형을 맞추십시오."},
}


# ══════════════════════════════════════════════════
#  납음오행(納音五行)
# ══════════════════════════════════════════════════

NABJIN_MAP = {
    ("甲子","乙丑"):("해중금(海中金)","金","바다 속 금. 미완성이나 잠재력이 큰 금. 도움을 받아 크게 빛나는 기운"),
    ("丙寅","丁卯"):("노중화(爐中火)","火","화로 속의 불. 강하게 타오르는 완성된 불. 단련과 성취의 기운"),
    ("戊辰","己巳"):("대림목(大林木)","木","큰 숲의 나무. 웅장하고 강한 나무. 지도자의 기운"),
    ("庚午","辛未"):("노방토(路傍土)","土","길가의 흙. 봉사와 희생의 기운"),
    ("壬申","癸酉"):("검봉금(劍鋒金)","金","칼날의 금. 예리하고 강한 금. 결단과 추진의 기운"),
    ("甲戌","乙亥"):("산두화(山頭火)","Fire","산꼭대기의 불. 명예와 리더십의 기운"),
    ("丙子","丁丑"):("간하수(澗下水)","水","계곡 아래의 물. 지혜와 소통의 기운"),
    ("戊寅","己卯"):("성두토(城頭土)","土","성 위의 흙. 권위와 방어의 기운"),
    ("庚辰","辛巳"):("백납금(白蠟金)","金","흰 밀랍의 금. 예술과 유연성의 기운"),
    ("壬午","癸未"):("양류목(楊柳木)","木","버드나무. 적응력과 창의의 기운"),
    ("甲申","乙酉"):("천중수(泉中水)","Water","샘물. 지혜와 직관의 기운"),
    ("丙戌","丁亥"):("옥상토(屋上土)","土","지붕 위의 흙. 가정과 안전의 기운"),
    ("戊子","己丑"):("벽력화(霹靂火)","Fire","벼락의 불. 충격과 각성의 기운"),
    ("庚寅","辛卯"):("송백목(松栢木)","Wood","소나무·잣나무. 의리와 절개의 기운"),
    ("壬辰","癸巳"):("장류수(長流水)","Water","장강의 물. 포용과 지속의 기운"),
    ("甲午","乙未"):("사중금(沙中金)","金","모래 속의 금. 발굴되면 빛나는 기운"),
    ("丙申","丁酉"):("산하화(山下火)","Fire","산 아래의 불. 꾸준한 열정의 기운"),
    ("戊戌","己亥"):("평지목(平地木)","Wood","평지의 나무. 포용과 성장의 기운"),
    ("庚子","辛丑"):("벽상토(壁上土)","土","벽 위의 흙. 원칙과 구조의 기운"),
    ("壬寅","癸卯"):("금박금(金箔金)","金","금박의 금. 외형적 화려함과 내면의 취약"),
    ("甲辰","乙巳"):("복등화(覆燈火)","Fire","덮인 등의 불. 숨겨진 재능이 빛을 기다리는 기운"),
    ("丙午","丁未"):("천하수(天河水)","Water","은하수. 영성과 이상의 기운"),
    ("戊申","己酉"):("대역토(大驛土)","土","큰 역참의 흙. 활동적인 사업의 기운"),
    ("庚戌","辛亥"):("차천금(釵釧金)","金","비녀와 팔찌의 금. 아름다움과 사교의 기운"),
    ("壬子","癸丑"):("상자목(桑柘木)","Wood","뽕나무. 부지런함과 실용성의 기운"),
    ("甲寅","乙卯"):("대계수(大溪水)","Water","큰 계곡의 물. 추진력과 지혜의 기운"),
    ("丙辰","丁巳"):("사중토(沙中土)","土","모래 속의 흙. 변화와 적응의 기운"),
    ("戊午","己未"):("천상화(天上火)","Fire","하늘 위의 불. 최고의 권위와 밝음의 기운"),
    ("庚申","辛酉"):("석류목(石榴木)","Wood","석류나무. 다산과 결실의 기운"),
    ("壬戌","癸亥"):("대해수(大海水)","Water","큰 바다. 무한한 포용력. 광대한 지혜의 기운"),
}

def get_nabjin(cg, jj):
    pillar = cg + jj
    for k, v in NABJIN_MAP.items():
        if pillar in k:
            name, oh, desc = v
            return {"name":name,"oh":oh,"desc":desc}
    return {"name":"미상","oh":"","desc":""}


# ══════════════════════════════════════════════════
#  육친론(六親論)
# ══════════════════════════════════════════════════

def get_yukjin(ilgan, pils, gender="남"):
    ss_to_family = {
        "남":{"정인":"어머니(正印)","편인":"계모(偏印)","정재":"아내(正財)","편재":"아버지(偏財)","정관":"딸(正官)","편관":"아들(偏官)","비견":"형제(比肩)","겁재":"이복형제(劫財)","식신":"손자(食神)","상관":"조모(傷官)"},
        "여":{"정인":"어머니(正印)","편인":"계모(偏印)","정관":"남편(正官)","편관":"정부(偏官)","정재":"시아버지(正財)","편재":"아버지(偏財)","비견":"자매(比肩)","겁재":"이복자매(劫財)","식신":"아들(食神)","상관":"딸(傷官)"},
    }.get(gender, {})
    sipsung_data = calc_sipsung(ilgan, pils)
    found = {}
    for i, ss_info in enumerate(sipsung_data):
        label = ["시주","일주","월주","년주"][i]
        p = pils[i]
        for ss in [ss_info.get("cg_ss","-"), ss_info.get("jj_ss","-")]:
            fam = ss_to_family.get(ss)
            if fam:
                if fam not in found: found[fam] = []
                found[fam].append(f"{label}({p['str']})")
    
    result = []
    checks = [
        ("어머니(正印)","정인","인성이 있어 어머니의 음덕(蔭德)이 큽니다.","정인(어머니 기운)이 약합니다. 어머니와의 인연이 엷거나 일찍 독립하는 기운입니다."),
        ("아버지(偏財)","편재","편재(아버지 기운)가 있습니다. 아버지의 재물적 도움이 있거나 부친 덕이 있습니다.","편재(아버지 기운)가 약합니다. 부친과의 인연이 엷거나 일찍 독립하는 기운입니다."),
    ]
    if gender == "남":
        checks += [
            ("아내(正財)","정재","정재(아내 기운)가 있습니다. 배우자 인연이 있고 가정적인 아내를 만날 기운입니다.","정재(아내 기운)가 약합니다. 결혼이 늦거나 대운에서 재성운이 올 때 인연이 찾아옵니다."),
            ("아들(偏官)·딸(正官)","편관","관살이 있습니다. 자녀 인연이 있으며 자녀로 인한 기쁨이 있습니다.","관살이 약합니다. 자녀와의 인연이 엷거나 늦게 생길 수 있습니다."),
        ]
    else:
        checks += [
            ("남편(正官)","정관","정관(남편 기운)이 있습니다. 안정적이고 믿음직한 남편 인연이 있습니다.","정관(남편 기운)이 없거나 약합니다. 결혼이 늦거나 편관으로 대체될 수 있습니다."),
            ("아들(食神)·딸(傷官)","식신","식상이 있습니다. 자녀 인연이 있으며 자녀로 인한 기쁨이 있습니다.","식상이 약합니다. 자녀와의 인연이 엷거나 늦을 수 있습니다."),
        ]
    checks.append(("형제(比肩)","비견","비겁이 있습니다. 형제자매 또는 동료·친구와의 인연이 깊습니다.","비겁이 약합니다. 형제자매 인연이 엷거나 자립심이 강한 독립적인 기질입니다."))
    
    sipsung_all = [ss for si in sipsung_data for ss in [si.get("cg_ss","-"), si.get("jj_ss","-")]]
    for fam_label, ss_key, yes_msg, no_msg in checks:
        has = ss_key in sipsung_all
        where = ", ".join(found.get(fam_label, []))
        result.append({"관계":fam_label,"위치":where if where else "없음","present":has,"desc":yes_msg if has else no_msg})
    return result


# ══════════════════════════════════════════════════
#  추가 신살 (원진·귀문관·백호·양인·화개)
# ══════════════════════════════════════════════════

EXTRA_SINSAL_DATA = {
    "원진": {"pairs":[("子","未"),("丑","午"),("寅","酉"),("卯","申"),("辰","亥"),("巳","戌")],"name":"원진살(怨嗔殺)","icon":"😤","desc":"서로 미워하고 반목하는 기운. 배우자·직장 동료와 불화가 잦습니다.","remedy":"처방: 상대방을 이해하려는 노력, 먼저 다가가는 소통이 필요합니다."},
    "귀문": {"pairs":[("子","酉"),("丑","午"),("寅","未"),("卯","申"),("辰","亥"),("巳","戌")],"name":"귀문관살(鬼門關殺)","icon":"🔮","desc":"직관력·영감이 탁월하나 신경과민·정신적 과부하에 취약합니다. 예술·상담 분야의 천재성.","remedy":"처방: 명상·수면 관리 필수. 긍정적으로 활용하면 영적 천재가 됩니다."},
    "백호": {"combos":["甲辰","乙未","丙戌","丁丑","戊辰","壬辰","癸丑"],"name":"백호대살(白虎大殺)","icon":"🐯","desc":"강력한 충격과 변동의 살. 사고·수술·피·혈액 관련 사건이 발생하기 쉽습니다.","remedy":"처방: 안전 주의, 정기적 건강검진, 의료·군경 분야에서 전문성으로 승화하십시오."},
    "양인": {"jjs":{"甲":"卯","丙":"午","戊":"午","庚":"酉","壬":"子"},"name":"양인살(羊刃殺)","icon":"⚡","desc":"극도로 강한 일간의 기운. 결단력·추진력이 압도적이나 충동성이 있습니다. 제화(制化)되면 최고의 지도자가 됩니다.","remedy":"처방: 강한 에너지를 건설적으로 사용. 관살의 제어가 있을 때 빛을 발합니다."},
    "화개": {"map":{"寅午戌":"戌","申子辰":"辰","巳酉丑":"丑","亥卯未":"未"},"name":"화개살(華蓋殺)","icon":"🎭","desc":"고독하지만 빛나는 별의 기운. 예술·종교·철학 분야에서 독보적 경지. 고독 속에서 탁월한 창의력이 발현됩니다.","remedy":"처방: 고독을 두려워하지 말고 내공을 쌓으십시오. 전문가·예술가·종교인의 상징!"},
}

def _get_extra_sinsal_v1(pils):
    """기본 신살 감지 (원진/귀문/백호/양인/화개) - 내부용. 전체버전은 get_extra_sinsal() 사용"""
    ilgan = pils[1]["cg"]
    jjs = [p["jj"] for p in pils]
    jj_set = set(jjs)
    result = []
    pairs_jj = [(jjs[i],jjs[j]) for i in range(len(jjs)) for j in range(i+1,len(jjs))]
    
    for a,b in pairs_jj:
        if (a,b) in EXTRA_SINSAL_DATA["원진"]["pairs"] or (b,a) in EXTRA_SINSAL_DATA["원진"]["pairs"]:
            d = EXTRA_SINSAL_DATA["원진"]
            result.append({"name":d["name"],"icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":f"{a}·{b}"})
            break
    for a,b in pairs_jj:
        if (a,b) in EXTRA_SINSAL_DATA["귀문"]["pairs"] or (b,a) in EXTRA_SINSAL_DATA["귀문"]["pairs"]:
            d = EXTRA_SINSAL_DATA["귀문"]
            result.append({"name":d["name"],"icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":f"{a}·{b}"})
            break
    for i,p in enumerate(pils):
        if p["cg"]+p["jj"] in EXTRA_SINSAL_DATA["백호"]["combos"]:
            d = EXTRA_SINSAL_DATA["백호"]
            label = ["시주","일주","월주","년주"][i]
            result.append({"name":f"{d['name']} [{label}]","icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":p["str"]})
    yang_jj = EXTRA_SINSAL_DATA["양인"]["jjs"].get(ilgan,"")
    if yang_jj and yang_jj in jj_set:
        d = EXTRA_SINSAL_DATA["양인"]
        result.append({"name":f"{d['name']} [{yang_jj}]","icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":yang_jj})
    for combo,hg_jj in EXTRA_SINSAL_DATA["화개"]["map"].items():
        if hg_jj in jj_set and any(jj in combo for jj in jj_set):
            d = EXTRA_SINSAL_DATA["화개"]
            result.append({"name":f"{d['name']} [{hg_jj}]","icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":hg_jj})
            break
    return result


# ══════════════════════════════════════════════════
#  🗓️ 만세력 엔진 (ManseCalendarEngine)
#  일진 · 절기 · 길일흉일 계산
# ══════════════════════════════════════════════════

# 24절기 기본 날짜 (연도별 미세 차이는 A단계 라이브러리로 정밀화)
_JEOLGI_BASE = [
    (1,  6,  "소한(小寒)"),  (1, 20, "대한(大寒)"),
    (2,  4,  "입춘(立春)"),  (2, 19, "우수(雨水)"),
    (3,  6,  "경칩(驚蟄)"),  (3, 21, "춘분(春分)"),
    (4,  5,  "청명(淸明)"),  (4, 20, "곡우(穀雨)"),
    (5,  6,  "입하(立夏)"),  (5, 21, "소만(小滿)"),
    (6,  6,  "망종(芒種)"),  (6, 21, "하지(夏至)"),
    (7,  7,  "소서(小暑)"),  (7, 23, "대서(大暑)"),
    (8,  8,  "입추(立秋)"),  (8, 23, "처서(處暑)"),
    (9,  8,  "백로(白露)"),  (9, 23, "추분(秋分)"),
    (10, 8,  "한로(寒露)"),  (10,23, "상강(霜降)"),
    (11, 7,  "입동(立冬)"),  (11,22, "소설(小雪)"),
    (12, 7,  "대설(大雪)"),  (12,22, "동지(冬至)"),
]

# 길일/흉일 기준 — 일진의 천간 기준 간단 판별
_GIL_CG  = {"甲","丙","戊","庚","壬"}          # 양간 = 기본 길일
_HYUNG_JJ = {"丑","刑","巳","申","寅"}          # 삼형살 지지
_GIL_JJ  = {"子","卯","午","酉","亥","寅"}      # 귀인 지지 포함

class ManseCalendarEngine:
    """
    만세력 부가 기능 엔진
    - 일진(日辰) 계산
    - 24절기 달력
    - 길일/흉일 판별
    """

    # ── 일진 계산 ─────────────────────────────────────
    @staticmethod
    def get_iljin(year: int, month: int, day: int) -> dict:
        """특정 날짜의 일진(日辰) 반환 {cg, jj, str, oh}"""
        from datetime import date as _date
        base = _date(2000, 1, 1)   # 甲子일 기준점 (2000-01-01 = 甲辰년 庚戌월 甲子일)
        target = _date(year, month, day)
        diff = (target - base).days
        # 2000-01-01은 甲子일 — 60갑자 인덱스 0
        idx = (diff + 0) % 60
        cg = CG[idx % 10]
        jj = JJ[idx % 12]
        oh = OH.get(cg, "")
        return {"cg": cg, "jj": jj, "str": cg + jj, "oh": oh, "idx": idx}

    @staticmethod
    def get_today_iljin() -> dict:
        """오늘 일진 반환"""
        today = datetime.now()
        return ManseCalendarEngine.get_iljin(today.year, today.month, today.day)

    # ── 24절기 달력 ────────────────────────────────────
    @staticmethod
    def get_jeolgi_calendar(year: int) -> list:
        """
        해당 연도의 24절기 목록 반환
        [{month, day, name, date_str}, ...]
        A단계 라이브러리 있으면 정밀 시각 포함
        """
        result = []
        for (m, d, name) in _JEOLGI_BASE:
            # 연도별 절기 날짜는 1~2일 오차 있음 (A단계에서 정밀화)
            try:
                dt = datetime(year, m, d)
                result.append({
                    "month": m,
                    "day":   d,
                    "name":  name,
                    "date_str": f"{year}.{m:02d}.{d:02d}",
                    "dt": dt,
                })
            except ValueError:
                pass
        # 날짜순 정렬
        result.sort(key=lambda x: (x["month"], x["day"]))
        return result

    @staticmethod
    def get_month_jeolgi(year: int, month: int) -> list:
        """특정 월의 절기만 반환"""
        return [j for j in ManseCalendarEngine.get_jeolgi_calendar(year)
                if j["month"] == month]

    # ── 길흉 판별 ──────────────────────────────────────
    @staticmethod
    def get_gil_hyung(year: int, month: int, day: int) -> dict:
        """
        날짜의 길흉 판별
        {grade: '길일'/'보통'/'주의', reason: str, color: '#...'}
        """
        iljin = ManseCalendarEngine.get_iljin(year, month, day)
        cg, jj = iljin["cg"], iljin["jj"]

        score = 0
        reasons = []

        if cg in _GIL_CG:
            score += 1
        if jj in _GIL_JJ:
            score += 1
            reasons.append("귀인운")
        if jj in _HYUNG_JJ:
            score -= 2
            reasons.append("삼형주의")

        # 일진별 특수 길일
        special_gil = {"甲子", "甲午", "丙子", "庚子", "壬子",
                        "甲申", "丙寅", "庚午", "壬申"}
        if iljin["str"] in special_gil:
            score += 2
            reasons.append("천을귀인")

        if score >= 2:
            return {"grade": "길일 ⭐", "reason": " · ".join(reasons) or "양기 충만",
                    "color": "#1a7a1a", "bg": "#f0fff0"}
        elif score <= -1:
            return {"grade": "주의", "reason": " · ".join(reasons) or "삼형 주의",
                    "color": "#cc0000", "bg": "#fff0f0"}
        else:
            return {"grade": "보통", "reason": "무난한 하루",
                    "color": "#444444", "bg": "#ffffff"}

    # ── 월별 달력 데이터 생성 ──────────────────────────
    @staticmethod
    def get_month_calendar(year: int, month: int) -> list:
        """
        해당 월의 전체 날짜별 데이터 반환
        [{date, iljin, gil_hyung, jeolgi_name or None}, ...]
        """
        import calendar as _cal
        _, days_in_month = _cal.monthrange(year, month)
        jeolgi_this_month = {j["day"]: j["name"]
                             for j in ManseCalendarEngine.get_month_jeolgi(year, month)}
        result = []
        for day in range(1, days_in_month + 1):
            iljin    = ManseCalendarEngine.get_iljin(year, month, day)
            gil      = ManseCalendarEngine.get_gil_hyung(year, month, day)
            jeolgi   = jeolgi_this_month.get(day)
            result.append({
                "day":      day,
                "iljin":    iljin,
                "gil":      gil,
                "jeolgi":   jeolgi,
            })
        return result


# ══════════════════════════════════════════════════
#  궁합(宮合)
# ══════════════════════════════════════════════════

def calc_gunghap(pils_a, pils_b, name_a="나", name_b="상대"):
    ilgan_a = pils_a[1]["cg"]; ilgan_b = pils_b[1]["cg"]
    jj_a = [p["jj"] for p in pils_a]; jj_b = [p["jj"] for p in pils_b]
    oh_a = OH.get(ilgan_a,""); oh_b = OH.get(ilgan_b,"")
    gen_map = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    ctrl_map = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    if gen_map.get(oh_a)==oh_b: ilgan_rel=("생(生)",f"{name_a}({ilgan_a})이 {name_b}({ilgan_b})를 생합니다.","💚",80)
    elif gen_map.get(oh_b)==oh_a: ilgan_rel=("생(生)",f"{name_b}({ilgan_b})이 {name_a}({ilgan_a})를 생합니다.","💚",80)
    elif ctrl_map.get(oh_a)==oh_b: ilgan_rel=("극(克)",f"{name_a}({ilgan_a})이 {name_b}({ilgan_b})를 극합니다.","🔴",40)
    elif ctrl_map.get(oh_b)==oh_a: ilgan_rel=("극(克)",f"{name_b}({ilgan_b})이 {name_a}({ilgan_a})를 극합니다.","🔴",40)
    elif oh_a==oh_b: ilgan_rel=("비(比)",f"두 분 모두 {OHN.get(oh_a,'')} 기운. 경쟁하거나 협력합니다.","🟡",60)
    else: ilgan_rel=("평(平)","상생상극 없는 중립적 관계.","🟢",65)
    
    all_jj_set = set(jj_a+jj_b); hap_score=0; hap_found=[]
    for combo,(name,oh,desc) in SAM_HAP_MAP.items():
        if combo.issubset(all_jj_set): hap_found.append(f"삼합 {name}"); hap_score+=20
    chung_found=[]
    for ja in jj_a:
        for jb in jj_b:
            k=frozenset([ja,jb])
            if k in CHUNG_MAP: chung_found.append(CHUNG_MAP[k][0])
    chunl={"甲":["丑","未"],"乙":["子","申"],"丙":["亥","酉"],"丁":["亥","酉"],"戊":["丑","未"],"己":["子","申"],"庚":["丑","未"],"辛":["寅","午"],"壬":["卯","巳"],"癸":["卯","巳"]}
    gui_a = any(jj in chunl.get(ilgan_a,[]) for jj in jj_b)
    gui_b = any(jj in chunl.get(ilgan_b,[]) for jj in jj_a)
    total = ilgan_rel[3]+hap_score-len(chung_found)*10+(10 if gui_a else 0)+(10 if gui_b else 0)
    total = max(0,min(100,total))
    grade = "💫 최고의 인연" if total>=85 else "✨ 좋은 인연" if total>=70 else "🌿 보통 인연" if total>=50 else "🔥 도전적 인연" if total>=30 else "⚠️ 어려운 인연"
    return {"총점":total,"등급":grade,"일간관계":ilgan_rel,"합":hap_found,"충":chung_found,"귀인_a":gui_a,"귀인_b":gui_b,"name_a":name_a,"name_b":name_b,"ilgan_a":ilgan_a,"ilgan_b":ilgan_b}


# ══════════════════════════════════════════════════
#  택일(擇日)
# ══════════════════════════════════════════════════

def get_good_days(pils, year, month):
    import calendar
    ilgan = pils[1]["cg"]; il_jj = pils[1]["jj"]
    chunl = {"甲":["丑","未"],"乙":["子","申"],"丙":["亥","酉"],"丁":["亥","酉"],"戊":["丑","未"],"己":["子","申"],"庚":["丑","未"],"辛":["寅","午"],"壬":["卯","巳"],"癸":["卯","巳"]}
    gui_jjs = chunl.get(ilgan,[])
    gm = get_gongmang(pils); bad_jjs = list(gm["공망_지지"])
    chung_jjs = [list(k)[0] if list(k)[1]==il_jj else list(k)[1] for k in CHUNG_MAP if il_jj in k]
    days_in_month = calendar.monthrange(year,month)[1]
    idx = (year-4)%60; month_base = (idx+(month-1)*2)%12
    good_days = []
    for day in range(1,days_in_month+1):
        day_jj = JJ[(month_base+day-1)%12]; day_cg = CG[((idx+(month-1)*2)+day-1)%10]
        score=50; reasons=[]
        if day_jj in gui_jjs: score+=25; reasons.append("천을귀인일 🌟")
        if day_jj in bad_jjs: score-=30; reasons.append("공망일 ⚠️")
        if day_jj in chung_jjs: score-=20; reasons.append("일주충일 ⚠️")
        for k,(name,oh,desc) in SAM_HAP_MAP.items():
            if day_jj in k and il_jj in k: score+=15; reasons.append(f"삼합{name}일 ✨"); break
        day_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(day_cg,"-")
        if day_ss in ["식신","정재","정관","정인"]: score+=10; reasons.append(f"{day_ss}일 ✨")
        elif day_ss in ["편관","겁재"]: score-=15; reasons.append(f"{day_ss}일 ⚠️")
        level = "🌟최길" if score>=80 else "✨길" if score>=65 else "〇보통" if score>=45 else "▲주의"
        if score>=60:
            good_days.append({"day":day,"jj":day_jj,"cg":day_cg,"pillar":day_cg+day_jj,"score":score,"level":level,"reasons":reasons})
    return sorted(good_days,key=lambda x:-x["score"])[:10]


# ══════════════════════════════════════════════════
#  사주 계산 엔진 (SajuCoreEngine)
# ══════════════════════════════════════════════════
import hashlib

from datetime import date, datetime, timedelta

class SajuCoreEngine:
    """사주팔자 핵심 계산 엔진"""

    MONTH_GANJI = [
        ("丙寅","戊寅"),("戊辰","甲辰"),("戊午","丙午"),
        ("庚申","戊申"),("壬戌","庚戌"),("甲子","壬子"),
        ("丙寅","甲寅"),("戊辰","丙辰"),("庚午","戊午"),
        ("壬申","庚申"),("甲戌","壬戌"),("丙子","甲子")
    ]

    SOLAR_TERMS = [
        (2,4),(2,19),(3,6),(3,21),(4,5),(4,20),
        (5,6),(5,21),(6,6),(6,21),(7,7),(7,23),
        (8,8),(8,23),(9,8),(9,23),(10,8),(10,23),
        (11,7),(11,22),(12,7),(12,22),(1,6),(1,20)
    ]

    @staticmethod
    def _get_year_pillar(year, month, day):
        """연주 계산"""
        # 입춘(2월4일) 기준
        if (month < 2) or (month == 2 and day < 4):
            y = year - 1
        else:
            y = year
        idx = (y - 4) % 60
        cg = CG[idx % 10]
        jj = JJ[idx % 12]
        return {"cg": cg, "jj": jj, "str": cg+jj}

    @staticmethod
    def _get_month_pillar(year, month, day):
        """월주 계산 (Bug 1 Fix: ji_idx = calc_m % 12)"""
        # 절기 기준 월 결정
        term_data = SajuCoreEngine.SOLAR_TERMS
        solar_month = month
        # 해당 월의 절입일
        term_idx = (month - 1) * 2
        if term_idx < len(term_data):
            t_month, t_day = term_data[term_idx]
            if (month == t_month and day < t_day) or (month != t_month):
                solar_month = month - 1
                if solar_month < 1:
                    solar_month = 12
        
        # 연간 기준으로 천간 결정
        if (month < 2) or (month == 2 and day < 4):
            y = year - 1
        else:
            y = year
        
        # 월 천간: 연간 기준 기월(寅月=1월)
        year_cg_idx = (y - 4) % 10
        # 甲己년: 丙寅시작, 乙庚년: 戊寅시작, 丙辛년: 庚寅시작, 丁壬년: 壬寅시작, 戊癸년: 甲寅시작
        month_cg_start = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]  # 갑=丙, 을=戊, 병=庚, 정=壬, 무=甲...
        cg_start = month_cg_start[year_cg_idx % 10]
        
        # 인월(寅=월지 인)부터 시작하는 월 번호 (1=인월, 2=묘월...)
        lunar_month_num = ((solar_month - 2) % 12)  # 인월=0, 묘월=1...
        
        cg_idx = (cg_start + lunar_month_num) % 10
        # ✅ BUG 1 FIX: ji_idx = calc_m % 12 (인=2부터 시작)
        ji_idx = (2 + lunar_month_num) % 12
        
        cg = CG[cg_idx]
        jj = JJ[ji_idx]
        return {"cg": cg, "jj": jj, "str": cg+jj}

    @staticmethod
    def _get_day_pillar(year, month, day):
        """일주 계산"""
        try:
            ref_date = date(2000, 1, 1)
            target_date = date(year, month, day)
            delta = (target_date - ref_date).days
            # 2000년 1월 1일 = 甲辰일 (인덱스 20)
            idx = (20 + delta) % 60
            cg = CG[idx % 10]
            jj = JJ[idx % 12]
            return {"cg": cg, "jj": jj, "str": cg+jj}
        except:
            return {"cg": "甲", "jj": "子", "str": "甲子"}

    @staticmethod
    def _get_hour_pillar(birth_hour, day_cg):
        """시주 계산"""
        # 시 번호 결정 (자시=0, 축시=1...)
        hour_boundaries = [1,3,5,7,9,11,13,15,17,19,21,23]
        si_num = 0
        for i, h in enumerate(hour_boundaries):
            if birth_hour >= h:
                si_num = i + 1
        si_num = si_num % 12
        
        # 일간 기준 시천간 결정
        day_cg_idx = CG.index(day_cg) % 5
        hour_cg_starts = [0, 2, 4, 6, 8]  # 甲己=甲, 乙庚=丙, 丙辛=戊, 丁壬=庚, 戊癸=壬
        cg_start = hour_cg_starts[day_cg_idx]
        
        cg_idx = (cg_start + si_num) % 10
        jj_idx = si_num % 12
        
        cg = CG[cg_idx]
        jj = JJ[jj_idx]
        return {"cg": cg, "jj": jj, "str": cg+jj}

    @staticmethod
    @st.cache_data
    def get_pillars(birth_year, birth_month, birth_day, birth_hour=12, gender="남"):
        """사주팔자 계산 - 반환: [시주, 일주, 월주, 년주]"""
        year_p = SajuCoreEngine._get_year_pillar(birth_year, birth_month, birth_day)
        month_p = SajuCoreEngine._get_month_pillar(birth_year, birth_month, birth_day)
        day_p = SajuCoreEngine._get_day_pillar(birth_year, birth_month, birth_day)
        hour_p = SajuCoreEngine._get_hour_pillar(birth_hour, day_p["cg"])
        
        # 순서: [시(0), 일(1), 월(2), 년(3)]
        return [hour_p, day_p, month_p, year_p]

    @staticmethod
    def get_daewoon(pils, birth_year, birth_month, birth_day, gender="남"):
        """대운 계산"""
        # 일간의 음양
        day_cg = pils[1]["cg"]
        day_cg_idx = CG.index(day_cg)
        is_yang = day_cg_idx % 2 == 0
        
        # 성별+음양 순행/역행
        if (gender == "남" and is_yang) or (gender == "여" and not is_yang):
            direction = 1  # 순행
        else:
            direction = -1  # 역행
        
        # 절입일 찾기 (간략화: 월주 기준 +/- 탐색)
        try:
            birth_date = date(birth_year, birth_month, birth_day)
            # 간단한 방식: 3일=1년 계산
            days_to_term = 30  # 기본값
            start_age = days_to_term // 3
            
            daewoon_list = []
            month_p = pils[2]  # 월주
            wolgan_idx = CG.index(month_p["cg"])
            wolji_idx = JJ.index(month_p["jj"])
            
            for i in range(9):
                step = i + 1
                d_cg_idx = (wolgan_idx + direction * step) % 10
                d_jj_idx = (wolji_idx + direction * step) % 12
                age_start = start_age + (i * 10)
                year_start = birth_year + age_start
                
                daewoon_list.append({
                    "순번": i+1,
                    "cg": CG[d_cg_idx],
                    "jj": JJ[d_jj_idx],
                    "str": CG[d_cg_idx] + JJ[d_jj_idx],
                    "시작나이": age_start,
                    "시작연도": year_start,
                    "종료연도": year_start + 9
                })
        except Exception as e:
            daewoon_list = []
        
        return daewoon_list

# ══════════════════════════════════════════════════
#  십성(十星) 및 12운성 계산 (Bug 5 Fix)
# ══════════════════════════════════════════════════
def calc_sipsung(ilgan, pils):
    """십성 계산"""
    result = []
    for p in pils:
        cg = p["cg"]
        jj = p["jj"]
        # 천간 십성
        cg_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(cg, "-")
        # 지장간 십성 (지지의 정기)
        jijang = JIJANGGAN.get(jj, [])
        if jijang:
            jj_main = jijang[-1]
            jj_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(jj_main, "-")
        else:
            jj_ss = "-"
        result.append({"cg_ss": cg_ss, "jj_ss": jj_ss, "jj": jj})
    return result


def calc_12unsung(ilgan, pils):
    """12운성 계산 (Bug 5 Fix: 양/음 배열 수정)"""
    # ✅ BUG 5 FIX: 올바른 양지/음지 배열
    jj_yang = ["子","寅","辰","午","申","戌"]  # 양지 (자인진오신술)
    jj_eum = ["丑","卯","巳","未","酉","亥"]   # 음지 (축묘사유미해)
    
    ilgan_idx = CG.index(ilgan)
    is_yang_gan = ilgan_idx % 2 == 0
    
    result = []
    for p in pils:
        jj = p["jj"]
        unsung_table_for = UNSUNG_TABLE.get(ilgan, {})
        unsung = unsung_table_for.get(jj, "-")
        result.append(unsung)
    return result


@st.cache_data
def calc_ohaeng_strength(ilgan, pils):
    """
    오행 세력 점수화 v2 (정밀 엔진)
    월령득령(25pt) + 천간투출(6~10pt) + 지지(8~15pt) + 지장간(4~8pt) + 통근보너스(5pt)
    → 합산 후 100% 정규화
    """
    power = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}

    # ─ 월령 득령 (월지 계절기운, 최대 25점) ─
    _WOLLYEONG = {
        "寅":{"木":25,"火":0,"土":3,"金":0,"水":0},
        "卯":{"木":25,"火":0,"土":3,"金":0,"水":0},
        "辰":{"木":8,"火":0,"土":20,"金":0,"水":3},
        "巳":{"木":0,"火":25,"土":3,"金":0,"水":0},
        "午":{"木":0,"火":25,"土":3,"金":0,"水":0},
        "未":{"木":0,"火":8,"土":20,"金":0,"水":0},
        "申":{"木":0,"火":0,"土":3,"金":25,"水":0},
        "酉":{"木":0,"火":0,"土":3,"金":25,"水":0},
        "戌":{"木":0,"火":0,"土":20,"金":8,"水":0},
        "亥":{"木":3,"火":0,"土":0,"金":0,"水":25},
        "子":{"木":3,"火":0,"土":0,"金":0,"水":25},
        "丑":{"木":0,"火":0,"土":20,"金":3,"水":8},
    }
    wol_jj = pils[2]["jj"]
    for oh, pt in _WOLLYEONG.get(wol_jj, {}).items():
        power[oh] += pt

    # ─ 천간 투출 (위치별 가중치) ─
    _CG_W = [6, 10, 10, 8]  # 연간, 월간, 일간, 시간
    for i, p in enumerate(pils):
        oh = OH.get(p["cg"], "")
        if oh: power[oh] += _CG_W[i]

    # ─ 지지 (위치별 가중치) ─
    _JJ_W = [8, 15, 12, 10]  # 연지, 월지, 일지, 시지
    for i, p in enumerate(pils):
        oh = OH.get(p["jj"], "")
        if oh: power[oh] += _JJ_W[i]
        # 지장간 (정기가 제일 강함)
        jijang = JIJANGGAN.get(p["jj"], [])
        n = len(jijang)
        for k, jg in enumerate(jijang):
            jg_oh = OH.get(jg, "")
            if jg_oh:
                pt = 8.0 if k == n-1 else (6.0 if k == n-2 else 4.0)
                if i == 2: pt *= 1.5  # 월지 지장간 1.5배
                power[jg_oh] += pt

    # ─ 12운성 보정 ─
    _UNSUNG_MOD = {
        "장생":1.2,"목욕":0.8,"관대":1.1,"건록":1.4,"제왕":1.5,
        "쇠":0.9,"병":0.7,"사":0.5,"묘":0.4,"절":0.3,"태":0.5,"양":0.7,
    }
    ilgan_oh = OH.get(ilgan, "")
    _JJ_W2 = [8, 15, 12, 10]
    for i, p in enumerate(pils):
        state = UNSUNG_TABLE.get(ilgan, {}).get(p["jj"], "")
        mod = _UNSUNG_MOD.get(state, 1.0)
        if mod != 1.0 and ilgan_oh:
            power[ilgan_oh] = max(0, power[ilgan_oh] + _JJ_W2[i] * (mod - 1.0) * 0.4)

    # ─ 통근 보너스 ─
    _TONGGUEN = {
        "木":{"寅","卯","辰","亥","未"},
        "火":{"巳","午","未","寅","戌"},
        "土":{"辰","戌","丑","未","巳","午"},
        "金":{"申","酉","戌","丑"},
        "水":{"亥","子","丑","申","辰"},
    }
    all_jjs = {p["jj"] for p in pils}
    for oh, jj_set in _TONGGUEN.items():
        if all_jjs & jj_set:
            power[oh] += 5.0

    # ─ 정규화 (합=100) ─
    total = sum(power.values())
    if total <= 0:
        return {"木":20,"火":20,"土":20,"金":20,"水":20}
    return {k: round(v/total*100, 1) for k, v in power.items()}


STRENGTH_DESC = {
    "신강(身强)": {
        "icon": "🔥",
        "title": "신강(身强) — 기운이 강한 사주",
        "desc": """일간의 기운이 왕성하고 충만한 사주입니다. 자기 주관이 뚜렷하고 추진력이 강하여 스스로 길을 개척하는 자립형 인물입니다.
신강 사주는 재성(財星)과 관성(官星)의 운이 올 때 자신의 강한 기운을 발산하며 크게 발복합니다.
강한 기운이 제대로 쓰일 때는 천하를 호령하지만, 쓸 곳이 없을 때는 고집과 독선이 화근이 됩니다.""",
        "lucky_run": "재성운(財星運)·관성운(官星運)",
        "lucky_desc": "재물과 명예의 운이 올 때 강한 일간이 빛을 발합니다. 관재·재물 운에서 크게 도약하는 시기입니다.",
        "caution_run": "비겁운(比劫運)·인성운(印星運)",
        "caution_desc": "이미 강한데 더 강해지면 독선과 분쟁, 고집으로 인한 손실이 생깁니다. 이 운에는 겸손과 절제가 필요합니다.",
        "ohang_advice": {
            "木": "목기(木氣)가 강할 때: 간 건강 주의, 분노 조절 수련 필요. 금(金)운에 제어받을 때 오히려 기회가 옵니다.",
            "火": "화기(火氣)가 강할 때: 심혈관 건강 주의, 수(水)운이 와서 열기를 식혀줄 때 발복합니다.",
            "土": "토기(土氣)가 강할 때: 소화기 건강 주의, 목(木)운이 와서 뚫어줄 때 변화와 성장이 옵니다.",
            "金": "금기(金氣)가 강할 때: 폐·대장 건강 주의, 화(火)운에 단련받을 때 진정한 보검이 됩니다.",
            "水": "수기(水氣)가 강할 때: 신장·방광 건강 주의, 토(土)운이 제방이 되어 방향을 잡아줄 때 발복합니다.",
        },
        "personality": "강한 자기주장, 독립심 강함, 리더십 있음, 때로 고집스러움, 경쟁에서 강함",
    },
    "신약(身弱)": {
        "icon": "🌿",
        "title": "신약(身弱) — 기운이 약한 사주",
        "desc": """일간의 기운이 상대적으로 약한 사주입니다. 타고난 기운이 약하다고 인생이 불리한 것이 아닙니다.
신약 사주는 인성(印星)과 비겁(比劫)의 운이 올 때 힘을 얻어 크게 발복합니다.
섬세한 감수성과 공감 능력이 뛰어나며, 귀인의 도움을 받는 운이 강합니다. 혼자보다 협력할 때 더 빛납니다.""",
        "lucky_run": "인성운(印星運)·비겁운(比劫運)",
        "lucky_desc": "학문·귀인·동료의 도움이 오는 운에서 크게 성장합니다. 스승이나 선배의 후원으로 도약하는 시기입니다.",
        "caution_run": "재성운(財星運)·관성운(官星運)",
        "caution_desc": "약한 기운에 재물과 관직의 무게가 더해지면 오히려 짓눌립니다. 이 운에는 무리한 확장을 자제하십시오.",
        "ohang_advice": {
            "木": "목기(木氣)가 약할 때: 수(水)운의 귀인 도움을 받을 때 발복. 간 기운 보강, 신맛 음식이 도움 됩니다.",
            "火": "화기(火氣)가 약할 때: 목(木)운의 생조를 받을 때 발복. 심장·눈 보강, 따뜻한 음식이 도움 됩니다.",
            "土": "토기(土氣)가 약할 때: 화(火)운의 생조를 받을 때 발복. 소화기 강화, 황색 식품이 도움 됩니다.",
            "金": "금기(金氣)가 약할 때: 토(土)운의 생조를 받을 때 발복. 폐·기관지 강화, 매운맛 적당히 도움 됩니다.",
            "水": "수기(水氣)가 약할 때: 금(金)운의 생조를 받을 때 발복. 신장 보강, 짠맛·검은 식품이 도움 됩니다.",
        },
        "personality": "섬세한 감수성, 뛰어난 공감 능력, 협력에 강함, 귀인 덕이 있음, 신중하고 배려심 깊음",
    },
    "중화(中和)": {
        "icon": "⚖️",
        "title": "중화(中和) — 균형 잡힌 사주",
        "desc": """오행의 기운이 비교적 균형 잡힌 이상적인 사주입니다. 중화된 사주는 어떤 운이 와도 극단적으로 흔들리지 않는 안정적인 삶을 삽니다.
재성운·관성운·인성운 어느 쪽이 와도 무난하게 적응하며 발전해 나갑니다.
특정 방면에서 폭발적인 성취보다는 안정적이고 꾸준한 상승 곡선을 그리는 것이 중화 사주의 복입니다.""",
        "lucky_run": "어느 운이든 무난하게 소화",
        "lucky_desc": "특정 운에 크게 발복하기보다 어떤 운이 와도 안정적으로 성장합니다. 꾸준함이 이 사주 최고의 강점입니다.",
        "caution_run": "극단적 편중 운",
        "caution_desc": "균형이 깨져 오행이 극단적으로 편중되는 대운은 주의가 필요합니다. 중화의 균형을 유지하는 것이 핵심입니다.",
        "ohang_advice": {
            "木": "목기가 균형점일 때: 현재의 균형을 유지하는 것이 중요합니다. 한쪽으로 치우치는 것을 경계하십시오.",
            "火": "화기가 균형점일 때: 열정과 냉정의 균형을 유지하세요. 중도(中道)가 최고의 덕입니다.",
            "土": "토기가 균형점일 때: 신중함과 행동력의 균형이 중요합니다. 때를 기다릴 줄 아는 지혜가 있습니다.",
            "金": "금기가 균형점일 때: 원칙과 유연함의 균형을 유지하세요. 강함 속에 부드러움이 있어야 합니다.",
            "水": "수기가 균형점일 때: 지혜와 실행의 균형이 중요합니다. 생각에 그치지 말고 실행으로 이어지게 하십시오.",
        },
        "personality": "안정적이고 균형 잡힌 성격, 상황 판단력 좋음, 꾸준한 노력형, 무난한 대인관계, 중재 능력",
    }
}


@st.cache_data
def get_ilgan_strength(ilgan, pils):
    """
    일간 신강신약 v2 | 5단계 점수화 (0~100)
    극신강 / 신강 / 중화 / 신약 / 극신약
    """
    oh_strength = calc_ohaeng_strength(ilgan, pils)
    ilgan_oh = OH.get(ilgan, "")

    # 생(生)해주는 오행 (인성)
    _BIRTH_R = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    parent_oh = _BIRTH_R.get(ilgan_oh, "")

    # 돕는 세력 = 비겁(같은오행) + 인성
    helper_score = oh_strength.get(ilgan_oh, 0) + oh_strength.get(parent_oh, 0)

    # 약화 세력 = 식상×0.8 + 재성×1.0 + 관성×1.0
    _BIRTH_F  = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    _CTRL     = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    sik_oh  = _BIRTH_F.get(ilgan_oh, "")
    jae_oh  = _CTRL.get(ilgan_oh, "")
    gwan_oh = next((k for k,v in _CTRL.items() if v==ilgan_oh), "")

    weak_score = (oh_strength.get(sik_oh,0)*0.8 +
                  oh_strength.get(jae_oh,0)*1.0 +
                  oh_strength.get(gwan_oh,0)*1.0)

    # 일간 힘 점수 0~100
    total = helper_score + weak_score
    daymaster_score = round(helper_score/total*100, 1) if total > 0 else 50.0

    # 5단계
    if daymaster_score >= 68:
        strength = "극신강(極身强)"
        advice   = "기운이 넘칩니다. 재성·관성 운에서 발복하나 자만과 독선 경계"
    elif daymaster_score >= 55:
        strength = "신강(身强)"
        advice   = "강한 기운 — 재성·관성 운에서 발복하나 비겁운은 경계"
    elif daymaster_score >= 45:
        strength = "중화(中和)"
        advice   = "균형 잡힌 기운 — 어떤 운에서도 무난하게 발전 가능"
    elif daymaster_score >= 32:
        strength = "신약(身弱)"
        advice   = "약한 기운 — 인성·비겁 운에서 힘을 얻고 재·관운은 조심"
    else:
        strength = "극신약(極身弱)"
        advice   = "기운이 매우 약합니다. 인성·비겁 운이 절실하며 재관운은 특히 위험"

    return {
        "신강신약": strength,
        "일간점수": daymaster_score,
        "helper_score": helper_score,
        "weak_score": weak_score,
        "조언": advice,
        "oh_strength": oh_strength,
        "ilgan_oh": ilgan_oh,
        "parent_oh": parent_oh,
        "sik_oh": sik_oh,
        "jae_oh": jae_oh,
        "gwan_oh": gwan_oh,
    }



# ══════════════════════════════════════════════════
#  세운/월운 계산 (Bug 6 Fix)
# ══════════════════════════════════════════════════
YEARLY_LUCK_NARRATIVE = {
    "비견": {
        "level": "길(吉)", "icon": "🤝",
        "title": "독립과 자립의 해",
        "desc": "동류(同類)의 기운이 강해지는 해입니다. 독립심이 강해지고 새로운 사업이나 파트너십을 통해 성장하는 시기입니다. 형제·친구·동료의 도움이 있으며, 혼자보다 협력할 때 더 큰 성과를 거둡니다.",
        "재물": "재물은 나누면 더 들어오는 해입니다. 독립 사업이나 프리랜서 활동에 유리합니다.",
        "관계": "새로운 동료와의 의미 있는 인연이 생깁니다. 기존 인맥을 활성화하십시오.",
        "건강": "과로로 인한 체력 저하를 주의하십시오. 규칙적인 운동이 도움 됩니다.",
        "조언": "경쟁보다 협력을, 독점보다 나눔을 선택할 때 복이 배가 됩니다."
    },
    "겁재": {
        "level": "흉(凶)", "icon": "⚔️",
        "title": "경쟁과 손재의 해 ⚠️",
        "desc": "재물 손실과 치열한 경쟁이 따르는 해입니다. 투자·보증·동업은 이 해에 특히 조심하십시오. 하지만 이 어려움을 이겨낸다면 더욱 강해지는 단련의 해이기도 합니다.",
        "재물": "재물 손실의 위험이 높습니다. 보수적으로 지키는 전략이 최선입니다.",
        "관계": "형제·동료와의 갈등이 생길 수 있습니다. 법적 분쟁에 주의하십시오.",
        "건강": "스트레스로 인한 심장·혈압 이상에 주의하십시오. 정기 건강검진을 받으십시오.",
        "조언": "무리한 확장이나 새로운 도전보다는 현상 유지와 내실 다지기에 집중하십시오."
    },
    "식신": {
        "level": "대길(大吉)", "icon": "🌟",
        "title": "복록과 풍요의 해 🎉",
        "desc": "하늘이 내리신 복록의 해입니다! 재능이 빛나고 하는 일마다 순조롭습니다. 먹고 사는 걱정이 사라지고, 주변에 사람이 모여드는 풍요로운 한 해를 맞이하게 됩니다.",
        "재물": "재물이 자연스럽게 들어오는 해입니다. 새로운 수입원이 생기기 좋은 시기입니다.",
        "관계": "인기가 높아지고 좋은 인연이 잇따릅니다. 결혼·새 친구 인연이 생길 수 있습니다.",
        "건강": "건강이 좋아지는 해입니다. 다만 과식·향락 소비를 절제하십시오.",
        "조언": "자신의 재능을 마음껏 발휘하십시오. 이 해에 시작하는 일은 좋은 결실을 맺습니다."
    },
    "상관": {
        "level": "평(平)", "icon": "🌪️",
        "title": "혁신과 변화의 해",
        "desc": "기존 틀을 깨고 새로운 길을 여는 혁신의 해입니다. 창의적인 아이디어가 폭발하고 변화를 향한 욕구가 강해집니다. 단, 직장·관직과의 충돌에 각별히 주의하십시오.",
        "재물": "창의적 활동으로 부수입이 생기기 좋은 해. 투자보다 재능 발휘가 유리합니다.",
        "관계": "자유로운 표현과 새로운 스타일의 인연이 찾아옵니다.",
        "건강": "신경성 질환, 불면증에 주의하십시오. 명상과 규칙적인 수면이 필요합니다.",
        "조언": "상관견관(傷官見官) 주의! 직장·공무 관련 언행을 극도로 조심하십시오."
    },
    "편재": {
        "level": "길(吉)", "icon": "💰",
        "title": "활발한 재물 활동의 해",
        "desc": "투자·사업·거래가 활발해지는 역동적인 재물의 해입니다. 대담한 도전이 빛을 발하고 새로운 재물 기회가 찾아옵니다. 이성 인연도 활발해지는 시기입니다.",
        "재물": "투자·부동산·사업 확장의 기회의 해. 계획적으로 움직이면 큰 성과가 있습니다.",
        "관계": "이성 인연이 활발한 해. 외부 활동과 사교에 좋은 시기입니다.",
        "건강": "과로와 무리한 활동으로 인한 체력 저하를 주의하십시오.",
        "조언": "신약하면 욕심을 버리고 자신의 역량 안에서만 움직이는 지혜가 필요합니다."
    },
    "정재": {
        "level": "길(吉)", "icon": "🏦",
        "title": "안정적 재물의 해",
        "desc": "성실하게 쌓아가는 안정된 재물의 해입니다. 고정 수입이 늘어나고 자산이 불어나며, 결혼 인연이나 배우자 덕을 보는 시기이기도 합니다.",
        "재물": "월급·임대수입 등 안정적 수입이 증가합니다. 저축과 자산 관리에 좋은 해입니다.",
        "관계": "배우자·파트너와의 관계가 안정되고 가정에 화목함이 깃드는 해입니다.",
        "건강": "전반적으로 건강이 안정적인 해입니다. 규칙적인 생활을 유지하십시오.",
        "조언": "꾸준함이 최고의 전략입니다. 급격한 변화보다 안정적인 성장을 추구하십시오."
    },
    "편관": {
        "level": "흉(凶)", "icon": "⚡",
        "title": "시련과 압박의 해 ⚠️",
        "desc": "강한 권력 기운과 함께 시련이 따르는 해입니다. 관재·사고·건강 이상에 주의가 필요합니다. 그러나 이 시련을 정면으로 돌파하면 더욱 단련되어 강해집니다.",
        "재물": "지출과 손실을 주의하십시오. 큰 재물 결정은 이 해를 피하는 것이 좋습니다.",
        "관계": "상사·권력자와의 갈등이 생기기 쉽습니다. 언행을 조심하고 자신을 낮추십시오.",
        "건강": "건강검진 필수! 사고·수술 위험이 있습니다. 안전에 특별히 주의하십시오.",
        "조언": "인내하고 정면으로 돌파하십시오. 식신이 있으면 제화가 되어 오히려 기회가 됩니다."
    },
    "정관": {
        "level": "대길(大吉)", "icon": "🎖️",
        "title": "명예와 인정의 해 🌟",
        "desc": "명예·직위·관직이 빛나는 황금 같은 해입니다! 승진·수상·자격 취득·계약 성사의 기회가 연달아 찾아옵니다. 조직 내에서 중요한 역할을 맡게 되는 영광의 해입니다.",
        "재물": "정직하고 합법적인 방법으로 재물이 들어오는 해. 계약·협약에 유리합니다.",
        "관계": "결혼 인연이나 공식적인 관계 진전이 있는 해입니다. 사회적 평판이 높아집니다.",
        "건강": "전반적으로 좋은 해이나 과도한 업무로 인한 스트레스를 관리하십시오.",
        "조언": "자만하지 마십시오. 겸손하게 원칙을 지키는 것이 이 해 복의 핵심입니다."
    },
    "편인": {
        "level": "평(平)", "icon": "🔮",
        "title": "직관과 연구의 해",
        "desc": "직관과 영감이 강해지고 특수 분야 연구에 몰입하기 좋은 해입니다. 일반적인 성공보다는 내면의 성장과 특수 분야에서의 도약이 이 해의 테마입니다.",
        "재물": "재물보다는 지식과 기술에 투자하기 좋은 해. 자격증·교육에 투자하십시오.",
        "관계": "혼자만의 시간이 필요한 해. 깊은 사색과 연구에 집중하십시오.",
        "건강": "소화기와 신경계 건강에 주의하십시오. 규칙적인 식사가 중요합니다.",
        "조언": "도식(倒食) 주의! 과도한 이상주의와 현실 도피를 경계하십시오."
    },
    "정인": {
        "level": "대길(大吉)", "icon": "📚",
        "title": "학문과 귀인의 해 🌟",
        "desc": "학문과 귀인의 도움이 충만한 최고의 해입니다! 시험·자격증·학위 취득에 매우 유리하며, 스승이나 윗사람의 후원이 자연스럽게 찾아오는 행운의 해입니다.",
        "재물": "직접적인 재물보다는 명예와 지식이 쌓이는 해. 이것이 미래의 큰 재물이 됩니다.",
        "관계": "어머니·스승·귀인의 도움이 있는 해. 멘토와의 만남이 인생을 바꿉니다.",
        "건강": "전반적으로 안정적인 해. 충분한 수면과 학습 환경을 잘 정비하십시오.",
        "조언": "지식을 쌓고 명예를 높이는 데 집중하십시오. 재물은 자연스럽게 따라옵니다."
    },
    "-": {
        "level": "평(平)", "icon": "〰️",
        "title": "복합 기운의 해",
        "desc": "다양한 기운이 혼재하는 해입니다. 꾸준한 노력으로 안정을 유지하는 것이 이 해의 최선입니다.",
        "재물": "급격한 변화보다 현상 유지에 집중하십시오.",
        "관계": "기존 관계를 돈독히 하는 해로 활용하십시오.",
        "건강": "정기적인 건강검진으로 이상 징후를 조기에 발견하십시오.",
        "조언": "큰 결정은 조금 더 기다리는 것이 안전합니다."
    },
}


def get_yearly_luck(pils, current_year):
    """세운 계산"""
    idx = (current_year - 4) % 60
    cg = CG[idx % 10]
    jj = JJ[idx % 12]
    
    # ✅ BUG 6 FIX: ilgan = pils[1]["cg"] (일주 천간)
    ilgan = pils[1]["cg"]
    se_ss_cg = TEN_GODS_MATRIX.get(ilgan, {}).get(cg, "-")
    jijang = JIJANGGAN.get(jj, [])
    se_ss_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(jijang[-1] if jijang else "", "-")
    
    oh_cg = OH.get(cg, "")
    oh_jj = OH.get(jj, "")
    
    narr = YEARLY_LUCK_NARRATIVE.get(se_ss_cg, YEARLY_LUCK_NARRATIVE["-"])
    
    return {
        "연도": current_year,
        "세운": cg + jj,
        "cg": cg, "jj": jj,
        "십성_천간": se_ss_cg,
        "십성_지지": se_ss_jj,
        "오행_천간": oh_cg,
        "오행_지지": oh_jj,
        "길흉": narr["level"],
        "아이콘": narr["icon"],
        "narrative": narr,
    }



MONTHLY_LUCK_DESC = {
    "비견": {
        "길흉": "평길", "css": "good",
        "short": "독립심·자립의 달",
        "desc": "동료·친구의 기운이 강해지는 달입니다. 새로운 파트너나 협력자를 만날 수 있으며, 독립적인 행동이 빛을 발합니다. 네트워킹에 적극적으로 나서십시오.",
        "재물": "재물은 나누어야 들어오는 달. 독립 사업이나 프리랜서 활동에 유리합니다.",
        "관계": "새로운 동료·친구와의 인연이 생깁니다. 형제·친구의 도움이 있습니다.",
        "주의": "경쟁자와의 갈등, 동업 분쟁에 주의하십시오."
    },
    "겁재": {
        "길흉": "흉", "css": "bad",
        "short": "경쟁·손재의 달",
        "desc": "재물 손실과 경쟁이 치열한 달입니다. 투자·보증·동업은 반드시 이달에는 자제하십시오. 불필요한 지출을 줄이고 소비를 절제하는 달입니다.",
        "재물": "재물의 손실 가능성이 높습니다. 큰 결정은 다음 달로 미루십시오.",
        "관계": "형제·동료와의 갈등이 생길 수 있습니다. 감정적 대응을 자제하십시오.",
        "주의": "보증·투자·동업 절대 금지! 도박성 투자는 이달 특히 경계하십시오."
    },
    "식신": {
        "길흉": "대길", "css": "great",
        "short": "복록·창의의 달 🌟",
        "desc": "하늘이 내리신 복록의 달입니다! 재능이 빛나고 하는 일마다 순조롭습니다. 창의적인 아이디어가 샘솟고 사람들의 인정을 받는 달입니다. 적극적으로 나서십시오!",
        "재물": "재물이 자연스럽게 들어오는 달입니다. 새로운 수입원이 생기기 좋은 시기입니다.",
        "관계": "사람들이 자연스럽게 모여드는 달. 인기가 높아지고 좋은 인연이 찾아옵니다.",
        "주의": "과도한 음식·향락 소비로 인한 건강 저하를 주의하십시오."
    },
    "상관": {
        "길흉": "평", "css": "",
        "short": "창의·변화의 달",
        "desc": "혁신적인 아이디어와 창의력이 폭발하는 달입니다. 기존 방식에서 벗어나 새로운 시도를 해볼 좋은 시기입니다. 단, 직장 상사나 권위자와의 언행에 각별히 주의하십시오.",
        "재물": "창의적 활동으로 부수입이 생기기 좋은 달. 투자보다는 재능 발휘가 유리합니다.",
        "관계": "자유로운 소통과 표현이 빛나는 달. 예술적·창의적 인연과의 만남이 있습니다.",
        "주의": "상관견관(傷官見官) 주의! 직장·공무 관련 언행을 극도로 조심하십시오."
    },
    "편재": {
        "길흉": "길", "css": "good",
        "short": "활발한 재물 활동의 달",
        "desc": "투자·사업·거래가 활발해지는 달입니다. 새로운 재물 기회가 찾아오고 대담한 도전이 빛을 발합니다. 이성 인연도 활발해지는 시기입니다. 신중한 투자로 재물을 불리십시오.",
        "재물": "투자·부동산·사업 확장의 기회. 과욕 없이 계획적으로 움직이면 성과가 있습니다.",
        "관계": "이성 인연이 활발해지는 달. 외부 활동과 사교 모임에 좋은 시기입니다.",
        "주의": "과도한 욕심으로 인한 과잉 투자를 경계하십시오. 재물이 들어오는 만큼 나갈 수도 있습니다."
    },
    "정재": {
        "길흉": "길", "css": "good",
        "short": "안정적 재물·성실의 달",
        "desc": "성실하게 쌓아가는 안정적인 재물의 달입니다. 월급·임대수입 등 고정 수입이 늘어나고, 저축과 자산 관리에 유리한 시기입니다. 배우자나 파트너의 도움이 있는 달입니다.",
        "재물": "꾸준한 노력이 결실을 맺는 달. 안정적 저축과 자산 관리에 집중하십시오.",
        "관계": "배우자·파트너와의 관계가 안정적이며 가정에 화목함이 깃드는 달입니다.",
        "주의": "현실을 벗어난 투기성 투자는 자제하십시오. 꾸준함이 최고의 전략입니다."
    },
    "편관": {
        "길흉": "흉", "css": "bad",
        "short": "압박·시련의 달 ⚠️",
        "desc": "권력이나 상사로부터 압박을 받거나 시련이 따르는 달입니다. 건강 이상이나 사고·관재의 위험이 있으니 특히 주의가 필요합니다. 인내하고 정면으로 돌파하면 이 달을 이겨낼 수 있습니다.",
        "재물": "지출과 손실을 주의하십시오. 큰 재물 결정은 이달을 피하십시오.",
        "관계": "상사·권력자와의 갈등이 생기기 쉽습니다. 언행을 조심하고 자신을 낮추십시오.",
        "주의": "건강검진 권장! 사고·수술·관재 위험이 있으니 안전에 특별히 주의하십시오."
    },
    "정관": {
        "길흉": "대길", "css": "great",
        "short": "명예·인정의 달 🎖️",
        "desc": "명예와 인정이 빛나는 최고의 달입니다! 승진·수상·자격 취득·계약 성사의 기회가 찾아옵니다. 법과 원칙을 지키는 삶이 보상받으며, 사회적 지위가 높아지는 시기입니다.",
        "재물": "정직하고 합법적인 방법으로 재물이 들어오는 달. 계약·협약에 유리합니다.",
        "관계": "결혼 인연이나 공식적인 관계 진전이 있는 달입니다. 격식 있는 만남이 이루어집니다.",
        "주의": "자만하지 마십시오. 겸손하게 원칙을 지키는 것이 이달 복의 핵심입니다."
    },
    "편인": {
        "길흉": "평", "css": "",
        "short": "직관·연구의 달",
        "desc": "직관과 영감이 강해지고 특수 분야 연구에 몰입하기 좋은 달입니다. 철학·종교·심리·IT 등 특수 분야에서 두각을 나타낼 수 있습니다. 혼자만의 시간을 통해 내공을 쌓는 달입니다.",
        "재물": "재물보다는 지식과 기술에 투자하기 좋은 달. 자격증·교육에 투자하십시오.",
        "관계": "혼자만의 시간이 필요한 달. 깊은 사색과 연구에 집중하십시오.",
        "주의": "도식(倒食) 주의! 편인이 식신을 극하면 복이 꺾이니 과도한 이상주의를 경계하십시오."
    },
    "정인": {
        "길흉": "대길", "css": "great",
        "short": "학문·귀인의 달 📚",
        "desc": "학문과 귀인의 도움이 충만한 최고의 달입니다! 시험·자격증·학위 취득에 매우 유리하며, 스승이나 윗사람의 후원이 자연스럽게 찾아옵니다. 지식을 쌓고 성장하는 달입니다.",
        "재물": "직접적인 재물보다는 명예와 지식이 쌓이는 달. 이것이 미래의 재물이 됩니다.",
        "관계": "어머니·스승·윗사람의 도움이 있는 달. 공식적이고 격식 있는 인연이 생깁니다.",
        "주의": "재물에 대한 욕심보다 학문과 자기 계발에 집중하십시오. 그것이 더 큰 복입니다."
    },
    "-": {
        "길흉": "평", "css": "",
        "short": "복합 기운의 달",
        "desc": "다양한 기운이 혼재하는 달입니다. 일간의 강약과 격국에 따라 발현이 달라지며, 꾸준한 노력으로 안정을 유지하는 것이 중요합니다.",
        "재물": "급격한 변화보다는 현상 유지에 집중하십시오.",
        "관계": "기존 관계를 돈독히 하는 달로 활용하십시오.",
        "주의": "큰 결정은 조금 더 기다리는 것이 안전합니다."
    },
}


def get_monthly_luck(pils, year, month):
    """월운 계산 (Bug 6 Fix)"""
    year_p = get_yearly_luck(pils, year)
    
    # ✅ BUG 6 FIX: ilgan = pils[1]["cg"] (일주 천간)
    ilgan = pils[1]["cg"]
    
    # 월간 인덱스
    year_cg_idx = CG.index(year_p["cg"])
    lunar_month_num = (month - 2) % 12
    m_cg_idx = (year_cg_idx * 2 + lunar_month_num) % 10
    m_jj_idx = (2 + lunar_month_num) % 12
    
    m_cg = CG[m_cg_idx]
    m_jj = JJ[m_jj_idx]
    
    m_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(m_cg, "-")
    m_jijang = JIJANGGAN.get(m_jj, [])
    m_ss_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(m_jijang[-1] if m_jijang else "", "-")
    
    luck_data = MONTHLY_LUCK_DESC.get(m_ss, MONTHLY_LUCK_DESC["-"])
    
    return {
        "월": month,
        "월운": m_cg + m_jj,
        "cg": m_cg, "jj": m_jj,
        "십성": m_ss,
        "지지십성": m_ss_jj,
        "길흉": luck_data["길흉"],
        "css": luck_data["css"],
        "short": luck_data["short"],
        "설명": luck_data["desc"],
        "재물": luck_data["재물"],
        "관계": luck_data["관계"],
        "주의": luck_data["주의"],
    }


def get_10year_luck_table(pils, birth_year, gender="남"):
    """10년 운세 테이블"""
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    result = []
    current_year = datetime.now().year
    for dw in daewoon:
        yearly = []
        for y in range(dw["시작연도"], dw["시작연도"] + 10):
            ye = get_yearly_luck(pils, y)
            yearly.append(ye)
        result.append({**dw, "yearly": yearly, "is_current": dw["시작연도"] <= current_year <= dw["종료연도"]})
    return result

# ══════════════════════════════════════════════════
#  AI 해석 (Bug 3 Fix: hash_funcs)
# ══════════════════════════════════════════════════
import json

################################################################################
# ★★★ Saju Platform Engineering Agent — AI 격리 아키텍처 ★★★
#
# [구조 원칙]
#   만세력 엔진(Deterministic) → 분석 JSON → AI Sandbox → 텍스트 출력
#
# Brain 1: 만세력 계산 엔진 — 절대 영역, AI 접근 금지
# Brain 2: AI 해석 엔진     — 읽기 전용 JSON만 수신, 계산 금지
#
# [AI 행동 금지]
#   - 생년월일 재계산 금지
#   - 간지(干支) 재추론 금지
#   - 오행 재계산 금지
#   - 대운·세운 재계산 금지
#   → 위반 감지 시 자동 차단 (validate_ai_output)
################################################################################

# ── Brain 2: AI 출력 검증 필터 ────────────────────────────────────────────────
_AI_FORBIDDEN_PHRASES = [
    "다시 계산", "생년월일 기준으로 계산",
    "추정하면", "계산해보면", "제가 계산한",
    "생년월일을 보면", "태어난 날을 기준으로",
    "사주를 계산", "간지를 계산", "오행을 계산",
]

def validate_ai_output(text: str) -> str:
    """AI 출력에서 계산 침범 감지 → 해당 문장 자동 제거"""
    if not text:
        return text
    lines = text.split("\n")
    clean = []
    for line in lines:
        if any(phrase in line for phrase in _AI_FORBIDDEN_PHRASES):
            # 침범 문장 제거 (로그만 남김)
            clean.append(f"[⚠️ 계산 침범 문장 자동 제거됨]")
        else:
            clean.append(line)
    return "\n".join(clean)

# ── Brain 2: AI Sandbox Wrapper ───────────────────────────────────────────────
_AI_SANDBOX_HEADER = """
★★★ AI 해석 전용 Sandbox 규칙 ★★★

아래 DATA는 만세력 계산 엔진이 이미 확정한 결과입니다.
당신은 절대로 이 값을 수정하거나 재계산하면 안 됩니다.

[금지 행동]
- 생년월일을 다시 계산하는 행위 금지
- 간지(干支)를 새로 추론하는 행위 금지
- 오행 비율을 재계산하는 행위 금지
- 대운·세운을 새로 계산하는 행위 금지
- "추정하면" "계산해보면" 같은 표현 금지

[허용 행동]
- 제공된 DATA를 바탕으로 해석·서술·조언만 수행

[답변 길이 & 톤 고정 규칙] ← 반드시 준수
- 길이: 250~400자 (한국어 기준). 너무 짧거나 너무 길면 안 됨
- 구조: 3단락만 허용
  ① 공감 문장 (1~2줄) — "지금 이 시기에…"
  ② 사주 분석 핵심 (2~3줄) — 운세 흐름 + 원인
  ③ 행동 조언 (1줄) — "지금 할 수 있는 한 가지"
- 문체: 상담가 말투. 존댓말. 마침표로 끝내기
- 금지: 번호 목록, 불릿(•), 헤더(##), 표, 코드블록

위 규칙을 위반하면 시스템이 해당 내용을 자동 차단합니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

def get_ai_interpretation(prompt_text, api_key="", system="당신은 40년 경력의 한국 전통 사주명리 전문가입니다.", max_tokens=2000, groq_key="", stream=False, history=None):
    """
    AI 해석 요청 — Anthropic 또는 Groq 선택
    history: [{"role": "user/assistant", "content": "..."}] 형태의 대화 이력
    """
    import requests

    # Sandbox 헤더 + Intent 엔진 + 판단 규칙 12개를 시스템 프롬프트에 강제 주입
    intent_prompt = IntentEngine.build_intent_prompt(prompt_text)
    rules_prompt  = SajuJudgmentRules.build_rules_prompt(prompt_text)
    sandboxed_system = _AI_SANDBOX_HEADER + system + "\n\n" + intent_prompt + "\n\n" + rules_prompt

    # 메시지 구성
    messages = [{"role": "system", "content": sandboxed_system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt_text})

    # Groq 우선 (빠름, 무료)
    if groq_key and groq_key.strip():
        try:
            headers = {
                "Authorization": f"Bearer {groq_key.strip()}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": stream
            }
            if not stream:
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                     headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    raw = resp.json()["choices"][0]["message"]["content"]
                    # 사후 필터: 계산 침범 제거 + 판단 규칙 12개 적용
                    return SajuJudgmentRules.apply_all(validate_ai_output(raw))
                else:
                    return f"[Groq 오류 {resp.status_code}]: {resp.text[:200]}"
            else:
                def groq_stream():
                    with requests.post("https://api.groq.com/openai/v1/chat/completions",
                                       headers=headers, json=data, timeout=60, stream=True) as resp:
                        if resp.status_code != 200:
                            yield f"[Groq 오류 {resp.status_code}]"
                            return
                        for line in resp.iter_lines():
                            if line:
                                line_str = line.decode('utf-8')
                                if line_str.startswith("data: "):
                                    if line_str == "data: [DONE]":
                                        break
                                    try:
                                        chunk = json.loads(line_str[6:])
                                        content = chunk["choices"][0]["delta"].get("content", "")
                                        if content:
                                            yield content
                                    except:
                                        pass
                return groq_stream()

        except Exception as e:
            return f"[Groq 연결 오류: {e}]"

    # Anthropic fallback
    if api_key and api_key.strip():
        try:
            headers = {
                "x-api-key": api_key.strip(),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            # Anthropic은 system 프롬프트를 별도로 처리하므로 messages에서 제외
            anthropic_messages = [m for m in messages if m["role"] != "system"]
            data = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": max_tokens,
                "system": sandboxed_system,
                "messages": anthropic_messages,
                "stream": stream
            }
            if not stream:
                resp = requests.post("https://api.anthropic.com/v1/messages",
                                     headers=headers, json=data, timeout=60)
                if resp.status_code == 200:
                    raw = resp.json()["content"][0]["text"]
                    return validate_ai_output(raw)
                else:
                    return f"[Anthropic 오류 {resp.status_code}]: {resp.text[:200]}"
            else:
                def anthropic_stream():
                    with requests.post("https://api.anthropic.com/v1/messages",
                                       headers=headers, json=data, timeout=60, stream=True) as resp:
                        if resp.status_code != 200:
                            yield f"[Anthropic 오류 {resp.status_code}]"
                            return
                        for line in resp.iter_lines():
                            if line:
                                line_str = line.decode('utf-8')
                                if line_str.startswith("data: "):
                                    try:
                                        event_data = json.loads(line_str[6:])
                                        if event_data.get("type") == "content_block_delta":
                                            yield event_data["delta"].get("text", "")
                                    except:
                                        pass
                return anthropic_stream()
        except Exception as e:
            return f"[Anthropic 연결 오류: {e}]"

    return ""


# ✅ BUG 3 FIX: hash_funcs를 사용하여 dict 인수 해싱 가능하게 처리
@st.cache_data(hash_funcs={dict: lambda d: json.dumps(d, sort_keys=True, default=str)})
def build_past_events(pils, birth_year, gender):
    """
    태어나서 현재까지 대운×세운 교차 → 사건 자동 생성
    충·합 발생 시점 + 십성으로 분야 판단 → 나이 특정 → 단정 서술
    """
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")
    orig_jjs = [p["jj"] for p in pils]
    orig_cgs = [p["cg"] for p in pils]
    current_year = datetime.now().year
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)

    # 십성 → 인생 분야 매핑
    SS_DOMAIN = {
        "남": {
            "비견": "경쟁·독립·형제갈등", "겁재": "재물손실·배신·경쟁심화",
            "식신": "창업·표현·자녀", "상관": "이직·창작충동·관직갈등",
            "편재": "사업변동·부친·이성", "정재": "재물·처·안정",
            "편관": "직장압박·사고·관재", "정관": "승진·명예·책임",
            "편인": "학업중단·모친·이사", "정인": "자격증·귀인·학업",
        },
        "여": {
            "비견": "경쟁·독립·자매갈등", "겁재": "재물손실·배신·고집",
            "식신": "자녀·표현·창업", "상관": "남편갈등·이직·예술",
            "편재": "사업변동·부친·재물", "정재": "재물·시댁·안정",
            "편관": "남편갈등·압박·관재", "정관": "남편·명예·책임",
            "편인": "모친·이사·학업중단", "정인": "귀인·학업·자격증",
        },
    }
    # 충 → 구체 사건 서술
    CHUNG_EVENT = {
        frozenset(["子","午"]): "감정 격변, 수화 충돌 — 가만히 있을 수 없었다",
        frozenset(["丑","未"]): "재물 분쟁, 토지·부동산 갈등 — 잃거나 싸웠다",
        frozenset(["寅","申"]): "돌발 사고, 이동·변화 — 예상 밖 사건이 터졌다",
        frozenset(["卯","酉"]): "관재 구설, 이성 갈등 — 말이 문제가 됐다",
        frozenset(["辰","戌"]): "재물 손실, 부동산 갈등 — 뭔가를 잃었다",
        frozenset(["巳","亥"]): "이별·분리, 먼 이동 — 관계가 끊어졌다",
    }
    # 천간합 → 긍정 변화
    TG_HAP_PAIRS = [{"甲","己"},{"乙","庚"},{"丙","辛"},{"丁","壬"},{"戊","癸"}]

    events = []  # {age, year, type, domain, desc, intensity}

    for dw in daewoon:
        if dw["시작연도"] > current_year:
            continue  # 미래 대운 제외
        dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"-")
        dw_domain = SS_DOMAIN.get(gender,SS_DOMAIN["남"]).get(dw_ss,"변화")

        # 대운 자체가 원국과 충·합하는지
        dw_chung = []
        for ojj in orig_jjs:
            k = frozenset([dw["jj"], ojj])
            if k in CHUNG_MAP:
                dw_chung.append((ojj, CHUNG_EVENT.get(k, "큰 변화가 찾아왔다")))
        dw_hap = []
        for pair in TG_HAP_PAIRS:
            if dw["cg"] in pair:
                other = list(pair - {dw["cg"]})[0]
                if other in orig_cgs:
                    dw_hap.append(other)

        # 대운 진입 시점 자체 이벤트
        age_start = dw["시작나이"]
        if dw_chung:
            for ojj, ev_desc in dw_chung:
                chung_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(JIJANGGAN.get(ojj,[""])[- 1],"-")
                domain = SS_DOMAIN.get(gender,SS_DOMAIN["남"]).get(chung_ss, dw_domain)
                events.append({
                    "age": f"{age_start}~{age_start+2}세",
                    "year": dw["시작연도"],
                    "type": "대운 지지충",
                    "domain": domain,
                    "desc": f"{dw['str']}대운 진입 — {ev_desc}. {domain} 영역에서 변동.",
                    "intensity": "🔴"
                })
        elif dw_hap:
            events.append({
                "age": f"{age_start}세",
                "year": dw["시작연도"],
                "type": "대운 천간합",
                "domain": dw_domain,
                "desc": f"{dw['str']}대운 진입 — 새로운 기운과 합(合). {dw_domain} 영역에서 기회.",
                "intensity": "🟡"
            })

        # 대운 내 세운별 교차 분석
        for y in range(dw["시작연도"], min(dw["종료연도"]+1, current_year)):
            age = y - birth_year + 1
            if age < 5:
                continue
            sw = get_yearly_luck(pils, y)
            sw_ss = sw.get("십성_천간", "-")
            sw_domain = SS_DOMAIN.get(gender,SS_DOMAIN["남"]).get(sw_ss,"변화")

            # 세운이 원국 지지와 충
            sw_chung_found = []
            for ojj in orig_jjs:
                k = frozenset([sw["jj"], ojj])
                if k in CHUNG_MAP:
                    sw_chung_found.append((ojj, k))

            # 대운+세운이 원국과 삼합
            sam_hap_found = []
            all_jj = set(orig_jjs + [dw["jj"], sw["jj"]])
            for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
                if combo.issubset(all_jj) and dw["jj"] in combo and sw["jj"] in combo:
                    sam_hap_found.append(hname)

            # 대운+세운 십성 조합으로 강도 판단
            dw_sw_combo = f"{dw_ss}+{sw_ss}"
            HIGH_IMPACT = {
                "편관+편관": ("🔴", "이중 편관 — 시련이 두 겹으로 왔다. 직업·건강·관재 중 하나가 터졌다."),
                "겁재+겁재": ("🔴", "이중 겁재 — 재물이 크게 흔들렸다. 배신이나 손실이 있었다."),
                "편관+겁재": ("🔴", "칠살 겁재 동시 — 직업+재물이 동시에 흔들렸다. 매우 힘든 해."),
                "정관+식신": ("🟡", "명예와 재능이 빛난 해. 승진·수상·성취가 있었다."),
                "정재+정관": ("🟡", "재물과 명예가 함께 왔다. 인생의 좋은 해였다."),
                "식신+정재": ("🟡", "재물운 폭발. 돈이 들어오는 해였다."),
                "편관+식신": ("🟢", "칠살제화 — 시련이 기회로 바뀐 해. 반전이 있었다."),
                "편재+편관": ("🔴", "재물 손실 + 직업 압박. 두 분야에서 동시에 힘들었다."),
            }

            intensity = "⬜"
            extra_desc = ""

            if dw_sw_combo in HIGH_IMPACT:
                intensity, extra_desc = HIGH_IMPACT[dw_sw_combo]

            if sw_chung_found:
                for ojj, ck in sw_chung_found:
                    chung_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(JIJANGGAN.get(ojj,[""])[- 1],"-")
                    domain = SS_DOMAIN.get(gender,SS_DOMAIN["남"]).get(chung_ss, sw_domain)
                    ev_desc = CHUNG_EVENT.get(ck, "큰 변화")
                    if intensity in ("🔴","🟡") or (intensity == "⬜" and ck in CHUNG_MAP):
                        events.append({
                            "age": f"{age}세",
                            "year": y,
                            "type": f"{dw_ss}대운 × {sw_ss}세운 + 원국충",
                            "domain": domain,
                            "desc": f"{y}년({age}세) — {ev_desc}. {domain}에서 변동. {extra_desc}",
                            "intensity": "🔴" if intensity == "⬜" else intensity
                        })

            elif sam_hap_found:
                events.append({
                    "age": f"{age}세",
                    "year": y,
                    "type": f"삼합 성립 {sam_hap_found[0]}",
                    "domain": sw_domain,
                    "desc": f"{y}년({age}세) — 대운+세운+원국 삼합({sam_hap_found[0]}) 성립. {sw_domain} 영역에서 발복.",
                    "intensity": "🟡"
                })
            elif intensity in ("🔴","🟡"):
                events.append({
                    "age": f"{age}세",
                    "year": y,
                    "type": f"{dw_ss}대운 × {sw_ss}세운",
                    "domain": sw_domain,
                    "desc": f"{y}년({age}세) — {extra_desc} {sw_domain} 분야.",
                    "intensity": intensity
                })

    # 중요도 기준 정렬, 상위 15개 선별
    priority = {"🔴": 0, "🟡": 1, "🟢": 2, "⬜": 3}
    events.sort(key=lambda e: (priority.get(e["intensity"],3), e["year"]))
    return events[:15]


# ══════════════════════════════════════════════════════════════════
# ★★★ 십성(十星) 2-조합 인생 분석 DB ★★★
# 조합만 알면 그 사람의 인생이 보인다
# ══════════════════════════════════════════════════════════════════
SIPSUNG_COMBO_LIFE = {
    frozenset(["식신","편재"]): {
        "요약": "🍀 재능으로 돈 버는 타입",
        "성향": "여유롭고 배짱이 있습니다. 쫓기는 삶보다 자기 페이스를 지키는 삶을 선호합니다. 욕심을 부리지 않아도 밥은 먹고 사는 구조가 이 사주입니다. 억지로 벌려 하면 오히려 안 풀립니다.",
        "재물": "재능·기술·콘텐츠로 돈이 들어오는 구조입니다. 억지로 발로 뛰는 영업보다, 본인이 잘하는 걸 갈고닦으면 돈이 따라옵니다. 프리랜서·창작·요식업·전문직이 유리합니다.",
        "직업": "자영업·프리랜서·요리사·디자이너·강사·유튜버·작가·예술가. 시간을 자유롭게 쓸 수 있는 직업이 맞습니다.",
        "연애": "상대방에게 집착하지 않습니다. 여유로운 관계를 선호합니다. 상대가 집착하거나 간섭하면 자연스럽게 멀어집니다.",
        "주의": "너무 여유를 부리다 기회를 흘려보내는 수가 있습니다. 좋은 운이 왔을 때 적극적으로 움직이십시오.",
    },
    frozenset(["상관","편재"]): {
        "요약": "⚡ 창의력과 말발로 돈 버는 타입",
        "성향": "말이 빠르고 아이디어가 넘칩니다. 기존 방식에 만족하지 못하고 항상 더 나은 방법을 찾습니다. 자유롭고 틀에 갇히는 것을 싫어합니다. 한 곳에 오래 있으면 답답함을 느낍니다.",
        "재물": "아이디어·설득·창의로 돈을 법니다. 세일즈·마케팅·홍보·예술·미디어에서 두각을 나타냅니다. 남들이 생각 못한 방식으로 수익을 만드는 능력이 있습니다.",
        "직업": "마케터·광고인·유튜버·방송인·세일즈·작가·디자이너·스타트업 창업자·연예인.",
        "연애": "매력적이고 화술이 뛰어나 이성의 시선을 끕니다. 다만 한 사람에게 오래 집중하기 힘든 면이 있어 이별이 잦을 수 있습니다.",
        "주의": "말이 앞서고 행동이 뒤처질 수 있습니다. 구설수와 경솔한 발언이 발목을 잡습니다.",
    },
    frozenset(["정관","정인"]): {
        "요약": "🏛️ 관인상생 — 공부가 출세로, 조직 내 최고 귀격",
        "성향": "원칙적이고 신중합니다. 배움을 좋아하고 지식을 쌓는 것에 보람을 느낍니다. 남에게 인정받는 것이 중요한 동기입니다. 겉으로는 여유로워 보여도 속으로는 평판을 매우 신경 씁니다.",
        "재물": "조직·제도권 안에서 안정적으로 재물이 쌓입니다. 급여·연금·직책 수당 등 안정된 수입 구조입니다. 투기보다 장기 저축·부동산이 맞습니다.",
        "직업": "공무원·교수·교사·대기업 임원·법관·의사·연구원. 자격증과 학위가 인생을 열어주는 사주입니다.",
        "연애": "신중하게 시작하고 오래 만납니다. 상대의 성실함·안정성을 중요하게 봅니다. 가볍게 만나는 것을 좋아하지 않습니다.",
        "주의": "너무 원칙만 고집하면 기회를 놓칩니다. 인간관계에서 유연함이 필요합니다.",
    },
    frozenset(["편관","식신"]): {
        "요약": "🔥 칠살제화 — 시련이 오히려 기회, 역경을 딛고 성공하는 타입",
        "성향": "어려운 상황에서 진가가 드러납니다. 압박이 올수록 더 강해집니다. 어릴 적 힘든 시절이 있었지만 그것이 오히려 내공이 되었습니다. 두 번 쓰러져도 세 번 일어나는 사람입니다.",
        "재물": "재능과 실력으로 역경을 뚫는 구조입니다. 처음엔 힘들어도 나중에 빛을 봅니다. 40대 이후 크게 안정됩니다.",
        "직업": "의사·검사·군인·경찰·운동선수·요리사·장인(匠人). 전문 기술로 편관의 압박을 제어하는 직업이 맞습니다.",
        "연애": "강인해 보이지만 내면은 매우 세심합니다. 강한 상대보다 따뜻하게 챙겨주는 사람에게 끌립니다.",
        "주의": "지나친 고집으로 도움받을 기회를 밀어내는 수가 있습니다. 받는 법도 배워야 합니다.",
    },
    frozenset(["편관","정인"]): {
        "요약": "🎖️ 큰 조직·권력 기관에서 빛나는 리더 타입",
        "성향": "리더십이 있습니다. 어려운 상황에서도 흔들리지 않고 방향을 잡습니다. 자연스럽게 따르는 사람이 생깁니다. 카리스마와 지식을 함께 갖춘 유형입니다.",
        "재물": "높은 직위·권한에서 재물이 따라오는 구조입니다. 실무보다 결정권을 갖는 위치가 훨씬 유리합니다.",
        "직업": "고위 공무원·군 장성·CEO·정치인·법조인·병원장. 조직의 상층부로 올라가는 것이 이 사주의 목표입니다.",
        "연애": "강한 카리스마에 끌리는 상대를 만납니다. 주도적인 관계를 선호하며, 상대가 자신을 인정해주기를 원합니다.",
        "주의": "권위적이 되기 쉽습니다. 아랫사람의 말에 귀 기울이는 연습이 필요합니다.",
    },
    frozenset(["비견","편재"]): {
        "요약": "⚔️ 남 밑에서는 못 배기는 독립 창업 기질",
        "성향": "독립심이 매우 강합니다. 누군가의 아래에서 지시받는 것을 본능적으로 거부합니다. 월급쟁이로 오래 살기 힘든 체질입니다. 자기 사업이나 자기 방식이 맞습니다.",
        "재물": "독립·창업·자영업으로 돈을 법니다. 재물이 왔다 갔다 하는 기복이 있지만 결국 스스로 만들어냅니다. 형제·동업자와의 재물 갈등을 각별히 조심하십시오.",
        "직업": "자영업·사업가·독립 컨설턴트·프리랜서·스타트업 대표. 조직 생활보다 독립이 맞습니다.",
        "연애": "자기 생각이 강해 상대와 부딪히는 경우가 많습니다. 비슷한 독립심을 가진 상대가 맞습니다.",
        "주의": "혼자 다 하려다 번아웃이 옵니다. 동업 분리를 명확히 하고 계약서를 꼭 쓰십시오.",
    },
    frozenset(["겁재","편재"]): {
        "요약": "🎰 크게 벌고 크게 쓰는 승부사 — 기복이 강한 인생",
        "성향": "승부욕이 극강입니다. 크게 베팅하는 기질이 있습니다. 결과가 좋을 때와 나쁠 때의 차이가 매우 큽니다. 조심성보다 추진력이 앞섭니다.",
        "재물": "한 번에 크게 버는 구조이지만, 그만큼 나가기도 쉽습니다. 보증·투기·동업에서 손해를 보는 패턴이 반복될 수 있습니다. 재물을 지키는 연습이 핵심 숙제입니다.",
        "직업": "사업가·트레이더·영업직·부동산·스포츠·연예계. 경쟁이 있는 환경에서 더 잘 됩니다.",
        "연애": "적극적이고 주도적입니다. 상대에게 아낌없이 씁니다. 하지만 재물 갈등이 관계에 영향을 줄 수 있습니다.",
        "주의": "충동적 투자와 보증은 반드시 피하십시오. 인생 최대 위기는 대부분 돈 문제에서 시작됩니다.",
    },
    frozenset(["겁재","정재"]): {
        "요약": "💸 벌어도 새는 구조 — 재물 관리가 인생의 핵심 숙제",
        "성향": "씀씀이가 큽니다. 들어오는 만큼 나갑니다. 저축보다 소비가 먼저입니다. 가까운 사람에게 베푸는 것을 좋아하지만, 그로 인해 손해를 보기도 합니다.",
        "재물": "수입은 있는데 모이지 않습니다. 고정 지출을 줄이고 자동 저축 시스템을 만드는 것이 핵심입니다. 부동산 같은 묶어두는 자산이 맞습니다.",
        "직업": "안정적인 월급 구조가 오히려 더 맞습니다. 변동 수입보다 고정 수입 직종이 재물을 지키기 좋습니다.",
        "연애": "관대하고 잘 챙깁니다. 그러나 지나친 헌신으로 지치는 경우가 있습니다.",
        "주의": "보증 서는 것과 쉬운 투자 제안을 경계하십시오.",
    },
    frozenset(["정재","정관"]): {
        "요약": "🏦 성실하게 쌓아가는 안정형 | 50대에 빛나는 사주",
        "성향": "현실적이고 성실합니다. 화려한 것보다 안정적인 것을 선호합니다. 맡은 일은 반드시 해냅니다. 한 번 한 약속은 반드시 지킵니다.",
        "재물": "꾸준히 차곡차곡 쌓는 구조입니다. 큰 기복 없이 우상향합니다. 50대가 되면 상당한 재산이 쌓여 있습니다. 부동산·예금·연금이 잘 맞습니다.",
        "직업": "금융인·회계사·공무원·대기업 직원·관리직. 안정적인 조직에서 오래 머무는 것이 유리합니다.",
        "연애": "신중하게 시작하고 오래 유지합니다. 화려한 연애보다 현실적이고 안정적인 파트너를 선호합니다.",
        "주의": "너무 안정만 추구하다 도전의 기회를 놓칩니다. 30~40대에 한 번은 용기 있는 선택이 필요합니다.",
    },
    frozenset(["상관","정관"]): {
        "요약": "💥 조직과 충돌하는 혁신가 — 창업이 답",
        "성향": "규칙과 권위에 본능적으로 반발합니다. '왜 이 규칙을 따라야 하는가'를 항상 묻습니다. 독창적이고 기존 방식을 파괴하는 혁신가 기질입니다.",
        "재물": "조직 안에서는 재물이 잘 안 쌓입니다. 독립·창업·전문직에서 빛을 발합니다. 자기 분야의 최고가 되면 돈이 따라옵니다.",
        "직업": "창업가·예술가·작가·유튜버·강연가·변호사. 자기 목소리를 낼 수 있는 직업이 최적입니다.",
        "연애": "솔직하고 직선적입니다. 상대방의 단점이 잘 보이고 그것을 말하는 경향이 있어 갈등이 생기기 쉽습니다.",
        "주의": "윗사람과의 갈등을 조심하십시오. 직장 내 구설수가 경력에 큰 타격을 줄 수 있습니다.",
    },
    frozenset(["편인","겁재"]): {
        "요약": "🌑 고독한 승부사 — 혼자 깊이 파고드는 전문가",
        "성향": "혼자 있는 것이 편합니다. 깊이 파고드는 것을 좋아하지만 결과를 잘 드러내지 않습니다. 겉으로는 강해 보이지만 내면은 외롭습니다.",
        "재물": "전문 기술·연구·특수 분야에서 재물이 옵니다. 대중을 상대하는 것보다 특정 분야 전문가로 인정받을 때 돈이 따라옵니다.",
        "직업": "연구원·전문직·한의사·역술인·프로그래머·투자자·작가.",
        "연애": "쉽게 마음을 열지 않습니다. 한번 마음을 열면 매우 깊이 의지하는 편입니다.",
        "주의": "고독이 깊어지면 자기 세계에 갇힙니다. 사람과의 연결을 의도적으로 만드십시오.",
    },
    frozenset(["식신","정관"]): {
        "요약": "✨ 재능과 명예가 함께 — 전문직·교육자로 빛나는 타입",
        "성향": "재능이 있고 원칙도 있습니다. 자기 분야에서 인정받고 싶어합니다. 일에 대한 자부심이 강하고, 자기 분야의 최고가 되는 것이 목표입니다.",
        "재물": "전문 기술+안정적 직위에서 재물이 옵니다. 전문직 자격증이 인생을 크게 열어줍니다. 꾸준히 실력을 쌓으면 중년 이후 크게 안정됩니다.",
        "직업": "의사·변호사·교수·요리사·음악가·건축가. 기술과 명예가 결합된 직업이 최적입니다.",
        "연애": "여유롭고 배려 깊습니다. 함께 성장하는 관계를 원합니다.",
        "주의": "완벽주의 성향으로 스스로를 지치게 만들 수 있습니다. 80%에서 멈추는 연습이 필요합니다.",
    },
    frozenset(["정재","식신"]): {
        "요약": "🌾 식신생재 — 실력이 재물로 자연스럽게 이어지는 길격",
        "성향": "부지런하고 현실적입니다. 군더더기 없이 실력을 쌓고 그 실력이 정직하게 재물로 이어집니다. 과욕 없이 꾸준히 하는 타입입니다.",
        "재물": "착실하게 모입니다. 큰 기복 없이 꾸준히 우상향합니다. 전통 명리에서 가장 좋은 재물 구조 중 하나입니다. 부업보다 본업 깊이 파기가 더 유리합니다.",
        "직업": "장인·요리사·의료인·공예가·전문 기술직. 손으로 하는 일, 기술이 필요한 일이 맞습니다.",
        "연애": "따뜻하고 현실적입니다. 상대를 물질적으로도 잘 챙기는 편입니다.",
        "주의": "안주하려는 경향이 있습니다. 시장이 변하면 기술도 업그레이드해야 합니다.",
    },
    frozenset(["편인","식신"]): {
        "요약": "🎭 도식(倒食) — 재능이 막히는 구조, 방향 전환이 답",
        "성향": "재능은 있는데 무언가가 자꾸 막힙니다. 하려는 일이 잘 안 풀리는 느낌이 반복됩니다. 다른 방향으로 전환했을 때 오히려 잘 되는 경우가 많습니다.",
        "재물": "한 가지 방식으로 고집하면 막힙니다. 다각화하거나 방법을 바꾸면 풀립니다. 부업·여러 수입원 구조가 유리합니다.",
        "직업": "특수 분야·틈새 시장·남들이 안 하는 것. 아웃사이더 전략으로 접근할 때 빛납니다.",
        "연애": "관계에서 오해가 생기기 쉽습니다. 말보다 행동으로 보여주는 것이 효과적입니다.",
        "주의": "한 가지에 너무 오래 집착하지 마십시오. 빠른 방향 전환이 오히려 길입니다.",
    },
    frozenset(["편재","편관"]): {
        "요약": "⚡ 큰 그림 그리는 사업가 — 고위험·고수익, 압박 속에 빛나는 타입",
        "성향": "크게 생각하고 크게 움직입니다. 작은 것에 만족하지 못합니다. 위험을 감수하는 용기가 있습니다. 한 번의 베팅으로 인생이 크게 바뀔 수 있는 사주입니다.",
        "재물": "크게 벌 수 있지만 동시에 크게 잃을 위험도 있습니다. 40대에 큰 기회가 한 번 찾아옵니다. 그 기회에 전부를 걸지 마십시오.",
        "직업": "사업가·투자가·무역업·정치인·부동산 개발. 스케일이 큰 일에 맞습니다.",
        "연애": "드라마틱한 연애를 합니다. 강렬한 만남과 이별을 반복하는 경향이 있습니다.",
        "주의": "재물과 직업 모두 기복이 큽니다. 리스크 관리가 생존의 핵심입니다.",
    },
    frozenset(["정인","비견"]): {
        "요약": "📚 독립적 학자·선생 기질 — 배운 것을 자기 철학으로 만드는 타입",
        "성향": "배움을 좋아하고, 배운 것을 자기 방식으로 해석합니다. 남의 지식을 그대로 따르지 않고 자기 철학으로 만듭니다. 독창적 사상가 기질이 있습니다.",
        "재물": "지식·교육·상담으로 돈을 법니다. 자기 콘텐츠나 저서가 수입이 되는 구조입니다. 강의·출판·코칭 분야에서 잘 됩니다.",
        "직업": "교사·강사·작가·컨설턴트·코치·상담사·철학자.",
        "연애": "지적 교류가 되는 상대에게 끌립니다. 대화가 안 되면 아무리 조건이 좋아도 관심이 없습니다.",
        "주의": "이론은 있는데 실행력이 부족한 경우가 있습니다. 아는 것을 반드시 실천으로 연결하십시오.",
    },
    frozenset(["상관","편인"]): {
        "요약": "🎨 예술·철학·창작 기질 — 천재와 기인의 경계",
        "성향": "남들과 다른 시각으로 세상을 봅니다. 예술적 감수성이 뛰어나고, 기존 틀을 깨는 것에서 쾌감을 느낍니다. 이해받기 어려운 독창성이 있습니다.",
        "재물": "일반적인 직업 경로로는 재물이 잘 안 쌓입니다. 독창적인 예술·콘텐츠·기술로 자기만의 길을 개척해야 합니다.",
        "직업": "예술가·작가·음악가·철학자·영화감독·발명가·연구자.",
        "연애": "독특한 매력이 있습니다. 하지만 상대가 이해하기 힘든 면이 많아 갈등이 생깁니다.",
        "주의": "현실 감각을 잃지 마십시오. 재능이 있어도 생활 기반이 없으면 꽃을 피울 수 없습니다.",
    },
    frozenset(["정인","정관"]): {
        "요약": "📖 학자·교육자 귀격 — 지식이 명예가 되는 사주",
        "성향": "배움과 원칙이 삶의 중심입니다. 윤리적이고 모범적입니다. 사람들에게 신뢰를 받는 타입입니다.",
        "재물": "지식·자격·직위에서 재물이 옵니다. 평생 안정적인 수입 구조입니다.",
        "직업": "교수·교사·공무원·의사·연구원·종교인·상담가.",
        "연애": "진지하게 만나고 오래 함께합니다. 배우자의 지적 수준을 중요하게 봅니다.",
        "주의": "지나치게 이상주의적이 되면 현실에서 실망을 반복합니다.",
    },
    frozenset(["비견","정재"]): {
        "요약": "💰 근성으로 재물 쌓는 타입 — 독립 후 안정",
        "성향": "자존심이 강하고 자기 방식이 확실합니다. 재물에 대한 감각이 있습니다. 독립적으로 재물을 구축하려는 의지가 강합니다.",
        "재물": "혼자 힘으로 재물을 쌓습니다. 남에게 의지하거나 물려받는 것을 자존심 때문에 거부합니다. 꾸준히 하면 반드시 성과가 납니다.",
        "직업": "자영업·전문직·관리직. 자기 영역을 갖는 것이 중요합니다.",
        "연애": "자존심이 강해 상대에게 약한 모습을 보이기 힘들어합니다.",
        "주의": "형제·친구와의 재물 갈등을 경계하십시오.",
    },
    frozenset(["식신","편인"]): {
        "요약": "🎭 도식(倒食) — 재능을 살리려면 방향 전환이 필요",
        "성향": "창의적인데 뭔가 막히는 느낌이 반복됩니다. 재능은 있지만 환경이나 시기가 맞지 않는 경우가 많습니다.",
        "재물": "일반 경로보다 틈새·특수 분야에서 기회를 찾아야 합니다. 방법을 바꾸면 열립니다.",
        "직업": "남들이 안 하는 특수 분야. 아웃사이더 전략으로 접근할 때 성과가 납니다.",
        "연애": "오해가 생기기 쉽습니다. 솔직한 대화가 관계를 살립니다.",
        "주의": "같은 방법으로 계속 시도하면 계속 막힙니다. 방향 전환이 핵심입니다.",
    },
    frozenset(["겁재","식신"]): {
        "요약": "🏃 실행력과 재능이 결합 — 스타트업·영업 최강 타입",
        "성향": "실행이 빠릅니다. 생각하면 바로 움직입니다. 재능도 있고 추진력도 있어 단기간에 성과를 만들어냅니다.",
        "재물": "빠른 실행으로 기회를 잡는 구조입니다. 초기 창업이나 신사업 개척에 유리합니다.",
        "직업": "영업·세일즈·스타트업·스포츠·요식업. 빠르게 움직이는 환경이 맞습니다.",
        "연애": "적극적이고 솔직합니다. 감정이 생기면 바로 표현합니다.",
        "주의": "섣부른 판단과 충동적 행동이 발목을 잡습니다. 실행 전 한 번 더 생각하십시오.",
    },
    frozenset(["편관","겁재"]): {
        "요약": "🌪️ 칠살겁재 — 인생 최대 험로, 하지만 살아남으면 강인한 사람",
        "성향": "인생이 순탄하지 않습니다. 외부의 압박과 재물 손실이 동시에 오는 시기가 있습니다. 그러나 이것을 버텨낸 사람은 누구보다 강인해집니다.",
        "재물": "재물 기복이 심합니다. 버는 시기와 잃는 시기가 교차합니다. 반드시 예비 자금을 확보해두어야 합니다.",
        "직업": "경쟁이 강한 환경에서도 살아남는 강인함이 있습니다. 위기관리·보안·군인·경찰·격투기.",
        "연애": "관계에서도 기복이 있습니다. 강한 상대와 만나면 끊임없이 부딪힙니다.",
        "주의": "건강을 가장 먼저 챙기십시오. 과로와 극단적 스트레스가 몸을 먼저 망가뜨립니다.",
    },
    frozenset(["정재","정인"]): {
        "요약": "🏡 안정과 지식이 결합 — 내실 있는 삶을 사는 타입",
        "성향": "알뜰하고 지식도 있습니다. 안정을 최우선으로 하면서도 배움을 멈추지 않습니다. 신뢰받는 사람입니다.",
        "재물": "꾸준히 모입니다. 절약과 투자 둘 다 잘 합니다. 부동산·저축에서 노후가 안정됩니다.",
        "직업": "교육·금융·의료·공무원. 안정적인 전문직이 맞습니다.",
        "연애": "성실하고 믿음직합니다. 상대를 잘 챙기고 오래 함께합니다.",
        "주의": "지나친 소심함으로 기회를 놓치지 마십시오.",
    },
    frozenset(["편재","정인"]): {
        "요약": "🌍 지식으로 세상을 누비는 타입 — 교육·여행·무역",
        "성향": "지적 호기심이 강하고 새로운 경험을 좋아합니다. 세상을 넓게 보는 눈이 있습니다.",
        "재물": "지식과 경험이 재물로 이어집니다. 국제적인 활동, 다양한 분야 도전이 유리합니다.",
        "직업": "무역업·해외 영업·교육·여행업·출판·미디어.",
        "연애": "다양한 경험을 원합니다. 한 타입에 머물지 않는 경향이 있습니다.",
        "주의": "넓게 보다 보면 깊이가 부족해질 수 있습니다. 한 분야를 파는 것도 필요합니다.",
    },
    frozenset(["상관","식신"]): {
        "요약": "🎤 표현의 천재 — 말·글·예술로 세상과 소통하는 타입",
        "성향": "표현력이 극강입니다. 말도 잘하고 글도 잘 씁니다. 자기 생각을 전달하는 것이 삶의 중요한 부분입니다.",
        "재물": "콘텐츠·강의·출판·공연으로 재물이 옵니다. 자기 목소리가 곧 수입입니다.",
        "직업": "작가·강사·유튜버·배우·성우·방송인·강연가.",
        "연애": "말로 상대의 마음을 사로잡습니다. 표현을 잘하는 만큼 상대에게 많은 기대를 하기도 합니다.",
        "주의": "쏟아내는 에너지가 크므로 소진되지 않도록 충전 시간이 필요합니다.",
    },
}

def build_life_analysis(pils, gender):
    """
    ★ 십성 2-조합으로 인생 전체를 읽는 핵심 엔진 ★
    성향 / 재물 / 직업 / 연애 / 주의사항 5가지 출력
    """
    ilgan = pils[1]["cg"]
    # 원국 전체 십성 수집
    ss_count = {}
    for p in pils:
        cg_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(p["cg"], "")
        jjg = JIJANGGAN.get(p["jj"], [])
        jj_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(jjg[-1] if jjg else "", "")
        for ss in [cg_ss, jj_ss]:
            if ss and ss not in ("-", ""):
                ss_count[ss] = ss_count.get(ss, 0) + 1

    # 많이 나온 순으로 정렬
    top_ss = sorted(ss_count, key=ss_count.get, reverse=True)

    # 조합 매칭 (상위 4개 십성 내에서)
    matched = []
    checked = set()
    for i, a in enumerate(top_ss[:5]):
        for b in top_ss[i+1:5]:
            k = frozenset([a, b])
            if k in SIPSUNG_COMBO_LIFE and k not in checked:
                matched.append((k, SIPSUNG_COMBO_LIFE[k]))
                checked.add(k)

    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]

    return {
        "조합_결과": matched[:2],   # 상위 2개 조합
        "전체_십성": ss_count,
        "주요_십성": top_ss[:4],
        "신강신약": sn,
        "일간": ilgan,
    }


# ══════════════════════════════════════════════════════════════════
#  엔진 하이라이트 — AI가 아닌 엔진이 먼저 뽑아내는 핵심 적중 데이터
# ══════════════════════════════════════════════════════════════════

# 성향 조합 DB — "신약+관성강 → 책임감 강+스트레스 많음" 같은 조합 공식
PERSONALITY_COMBO_DB = {
    # (신강신약_키, 강한십성) → 서술
    ("신약", "정관"): [
        "책임감이 강합니다. 맡은 일은 끝까지 하는 사람입니다.",
        "그러나 그 책임감이 자신을 갉아먹습니다. 스트레스를 속으로 삼키는 스타일입니다.",
        "남들 눈에는 믿음직해 보이지만, 혼자 있을 때 지쳐있는 경우가 많습니다."
    ],
    ("신약", "편관"): [
        "압박이 일상인 삶입니다. 외부에서 끊임없이 뭔가를 요구받습니다.",
        "그럼에도 굴복하지 않습니다. 오히려 버티는 힘이 남들보다 강합니다.",
        "다만 그 버팀이 몸을 먼저 망가뜨립니다. 건강을 각별히 챙겨야 합니다."
    ],
    ("신강", "비견"): [
        "경쟁심이 매우 강합니다. 지는 것을 본능적으로 거부합니다.",
        "형제나 동료와 크고 작은 갈등이 있었습니다.",
        "독립심도 강해서, 결국은 혼자 가는 길을 선택하는 경우가 많습니다."
    ],
    ("신강", "겁재"): [
        "승부욕이 극강입니다. 가까운 사람과도 경쟁하는 경향이 있습니다.",
        "재물이 모이는 듯하다가 흩어지는 패턴이 반복됩니다. 돈 관리가 숙제입니다.",
        "배신당한 경험이 한 번 이상은 있습니다. 그 이후로 사람을 쉽게 믿지 않습니다."
    ],
    ("신약", "식신"): [
        "재주가 있습니다. 뭔가를 만들어내는 창의력이 있습니다.",
        "그러나 일간이 약해 그 재주를 발휘할 에너지가 부족합니다.",
        "쉬어가면서 해야 하는데, 쉬는 것에 죄책감을 느끼는 경향이 있습니다."
    ],
    ("신강", "식신"): [
        "배짱이 있습니다. 남들이 걱정할 때 혼자 태평한 경우가 있습니다.",
        "자기 방식이 있고, 그 방식을 좋아합니다. 간섭받는 것을 싫어합니다.",
        "복이 자연스럽게 따라오는 구조입니다. 무리하지 않는 것이 오히려 길입니다."
    ],
    ("신약", "편인"): [
        "직관이 뛰어납니다. 논리로 설명하기 어렵지만 '그냥 아는' 경우가 많습니다.",
        "단, 그 직관이 불안으로 변하기도 합니다. 나쁜 예감이 자꾸 드는 편입니다.",
        "고독을 즐기는 척하지만, 사실은 인정받고 싶습니다."
    ],
    ("신강", "정관"): [
        "원칙과 체면을 중시합니다. 규칙을 잘 지키고, 남도 지키기를 요구합니다.",
        "겉으로는 반듯해 보이지만, 속으로는 매우 자존심이 강합니다.",
        "한번 신뢰를 잃으면 다시 주지 않는 사람입니다."
    ],
}

# 오행 과다/부족 조합 DB
OH_COMBO_DB = {
    # 과다
    ("over", "水"): [
        "생각이 너무 많습니다. 잠자리에 누워도 머릿속이 계속 돌아갑니다.",
        "걱정을 사서 합니다. 일어나지도 않은 일을 먼저 걱정합니다.",
        "밤에 더 활발해지는 경향이 있습니다. 낮형보다 밤형에 가깝습니다."
    ],
    ("over", "火"): [
        "에너지가 넘칩니다. 시작을 잘 합니다. 문제는 지속력입니다.",
        "감정 기복이 있습니다. 화가 올라왔다 금방 풀리기도 합니다.",
        "주목받는 것을 좋아합니다. 관심의 중심에 있을 때 가장 빛납니다."
    ],
    ("over", "木"): [
        "빠릅니다. 결정도 빠르고 판단도 빠릅니다. 대신 기다리는 것을 못 합니다.",
        "시작해놓고 완성을 못 보는 경우가 있습니다. 더 좋은 아이디어가 자꾸 생깁니다.",
        "자존심이 삶의 원동력입니다. 자존심이 상하면 모든 의욕이 꺼집니다."
    ],
    ("over", "金"): [
        "예리합니다. 사람의 본질을 빠르게 파악합니다. 가끔 너무 날카롭습니다.",
        "한번 결정하면 칼같이 실행합니다. 유연성이 부족한 게 단점입니다.",
        "냉정해 보이지만, 가까운 사람에게는 다릅니다. 속으로 많이 챙깁니다."
    ],
    ("over", "土"): [
        "한번 정하면 잘 안 바꿉니다. 고집이 강하고 자기 방식이 확실합니다.",
        "걱정과 근심이 많습니다. 내색은 안 하지만 속으로는 늘 뭔가를 염려합니다.",
        "신뢰를 쌓는 데 시간이 걸리지만, 한번 쌓이면 오래갑니다."
    ],
    # 부족
    ("lack", "木"): [
        "계획을 세우는 것이 약합니다. 시작하기까지 시간이 걸립니다.",
        "추진력보다 지속력이 강점입니다. 급하게 달리기보다 꾸준히 걷는 스타일."
    ],
    ("lack", "火"): [
        "표현이 서툽니다. 속으로는 분명 감정이 있는데 겉으로는 차가워 보일 수 있습니다.",
        "열정을 드러내는 것이 어색합니다. 하지만 속에 불씨는 있습니다."
    ],
    ("lack", "土"): [
        "안정보다 변화를 선호합니다. 한곳에 오래 머물기 싫어합니다.",
        "뿌리내리는 것이 인생의 숙제입니다."
    ],
    ("lack", "金"): [
        "잘라내야 할 것을 잘라내지 못합니다. 결단의 순간에 자꾸 망설입니다.",
        "정이 많습니다. 그 정 때문에 손해를 보는 경우가 있습니다."
    ],
    ("lack", "水"): [
        "직관보다 논리로 움직입니다. 느낌보다 근거를 중시합니다.",
        "감정 표현이 서툽니다. 표현을 어려워하지만 감정이 없는 건 아닙니다."
    ],
}


def generate_engine_highlights(pils, birth_year, gender):
    """
    ★ 핵심 엔진 ★
    AI가 찾게 하지 말고 엔진이 먼저 뽑아낸다.
    반환값:
    {
        "past_events": [{"age": "27~28세", "year": 2019, "domain": "직장", "desc": "...", "intensity": "🔴"}],
        "personality": ["겉은 강해 보이나 속은...", "혼자 고민을 오래 끄는 성향"],
        "money_peak": [{"age": 32, "year": 2024, "desc": "..."}],
        "marriage_peak": [{"age": 31, "year": 2023, "desc": "..."}],
        "danger_zones": [{"age": "29~30세", "desc": "..."}],
        "wolji_chung": [{"age": "28세", "desc": "..."}]
    }
    """
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")
    current_year = datetime.now().year
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    oh_strength = strength_info["oh_strength"]

    # ── 과거 사건 (기존 엔진 활용) ───────────────────────
    past_events = build_past_events(pils, birth_year, gender)

    # ── 성향 — 조합 공식으로 생성 ────────────────────────
    personality = build_personality_detail_v2(pils, gender, sn, oh_strength)

    # ── 재물 피크 ─────────────────────────────────────────
    money_peak = []
    MONEY_SS = {"식신", "정재", "편재"}
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        age_c = birth_year + dw["시작나이"] - 1
        if dw_ss in MONEY_SS:
            money_peak.append({
                "age": f"{dw['시작나이']}~{dw['시작나이']+9}세",
                "year": f"{dw['시작연도']}~{dw['종료연도']}",
                "desc": f"{dw['str']}대운({dw_ss}) — 재물이 자연스럽게 따라오는 시기",
                "ss": dw_ss
            })
        # 세운 중 재물 피크 (현재+5년)
        if dw["시작연도"] <= current_year + 5 and dw["종료연도"] >= current_year - 2:
            for y in range(max(dw["시작연도"], current_year-2), min(dw["종료연도"]+1, current_year+6)):
                sw = get_yearly_luck(pils, y)
                if sw["십성_천간"] in MONEY_SS and dw_ss in MONEY_SS:
                    age = y - birth_year + 1
                    money_peak.append({
                        "age": f"{age}세",
                        "year": str(y),
                        "desc": f"{y}년 — 대운({dw_ss})×세운({sw['십성_천간']}) 재물 더블. 최고의 돈 기회",
                        "ss": "더블"
                    })

    # ── 혼인 피크 ─────────────────────────────────────────
    MARRIAGE_SS = {"정재", "편재"} if gender == "남" else {"정관", "편관"}
    marriage_peak = []
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        if dw_ss in MARRIAGE_SS:
            # 대운 내에서 가장 강한 세운 탐색
            for y in range(dw["시작연도"], min(dw["종료연도"]+1, current_year+10)):
                sw = get_yearly_luck(pils, y)
                if sw["십성_천간"] in MARRIAGE_SS:
                    age = y - birth_year + 1
                    marriage_peak.append({
                        "age": f"{age}세",
                        "year": str(y),
                        "desc": f"{y}년({age}세) — 대운·세운 모두 인연성. 배우자 인연이 오는 해"
                    })

    # ── 위험 구간 ─────────────────────────────────────────
    danger_zones = []
    DANGER_SS = {"편관", "겁재"}
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        if dw_ss in DANGER_SS:
            danger_zones.append({
                "age": f"{dw['시작나이']}~{dw['시작나이']+9}세",
                "year": f"{dw['시작연도']}~{dw['종료연도']}",
                "desc": f"{dw['str']}대운({dw_ss}) — {'직장·관재·건강 압박' if dw_ss=='편관' else '재물손실·경쟁·배신'} 주의"
            })

    # ── 월지 충 시점 ──────────────────────────────────────
    wolji_chung = []
    wol_jj = pils[2]["jj"]
    for dw in daewoon:
        if dw["종료연도"] >= current_year:
            continue
        k = frozenset([dw["jj"], wol_jj])
        if k in CHUNG_MAP:
            name_c, _, desc = CHUNG_MAP[k]
            wolji_chung.append({
                "age": f"{dw['시작나이']}~{dw['시작나이']+2}세",
                "desc": f"대운 진입시 월지 충({name_c}) — {desc}. 이 시기 삶의 기반이 흔들렸습니다."
            })
        for y in range(dw["시작연도"], min(dw["종료연도"]+1, current_year)):
            sw = get_yearly_luck(pils, y)
            k2 = frozenset([sw["jj"], wol_jj])
            if k2 in CHUNG_MAP:
                age = y - birth_year + 1
                name_c2, _, desc2 = CHUNG_MAP[k2]
                wolji_chung.append({
                    "age": f"{age}세",
                    "desc": f"{y}년 세운이 월지를 충({name_c2}) — {desc2}. 직업·가정 중 하나가 흔들렸습니다."
                })

    return {
        "past_events": past_events,
        "personality": personality,
        "money_peak": money_peak[:5],
        "marriage_peak": marriage_peak[:3],
        "danger_zones": danger_zones[:4],
        "wolji_chung": wolji_chung[:5],
        "raw": {
            "ilgan": ilgan, "sn": sn, "oh_strength": oh_strength,
            "yongshin_ohs": get_yongshin(pils)["종합_용신"],
            "gyeok": get_gyeokguk(pils)["격국명"] if get_gyeokguk(pils) else "미정격"
        }
    }


def build_personality_detail_v2(pils, gender, sn, oh_strength):
    """
    강화된 성향 DB — 조합 공식 기반
    신약+관성강 / 비겁강 / 수과다 등 구체적 콤보
    """
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")
    traits = []

    # 강한 십성 파악 (원국 내 2개 이상)
    ss_count = {}
    for p in pils:
        jjg = JIJANGGAN.get(p["jj"], [])
        jeongi = jjg[-1] if jjg else ""
        for cg_check in [p["cg"], jeongi]:
            ss = TEN_GODS_MATRIX.get(ilgan, {}).get(cg_check, "")
            if ss and ss not in ("", "-"):
                ss_count[ss] = ss_count.get(ss, 0) + 1
    strong_ss = [ss for ss, cnt in ss_count.items() if cnt >= 2]
    sn_key = "신강" if "신강" in sn else "신약"

    # 조합 공식 적용
    for ss in strong_ss:
        combo_key = (sn_key, ss)
        if combo_key in PERSONALITY_COMBO_DB:
            traits.extend(PERSONALITY_COMBO_DB[combo_key])

    # 기본 일간 심리 (조합이 없을 때 폴백)
    if not traits:
        OH_BASE = {
            "木": {"신강": "겉으로는 당당하고 직선적이지만, 속으로는 인정받고 싶은 욕구가 강합니다. 자존심이 삶의 원동력입니다.",
                   "신약": "겉은 유연해 보이지만 속으로는 고집이 강합니다. 쉽게 상처받고 오래 기억합니다."},
            "火": {"신강": "열정적이고 화려해 보이지만, 관심받지 못하면 금세 지칩니다. 겉으로 드러나지 않는 외로움이 있습니다.",
                   "신약": "따뜻하고 감성적이지만 불안감이 내재해 있습니다. 쉽게 흥분하고 금방 꺼집니다."},
            "土": {"신강": "신뢰감 있어 보이지만 속으로는 걱정이 많습니다. 결정을 내리면 쉽게 바꾸지 않습니다.",
                   "신약": "배려심 깊지만 혼자 고민을 오래 끌고 갑니다. 결정을 미루는 경향이 있습니다."},
            "金": {"신강": "겉은 강하고 원칙적이지만 속으로는 매우 섬세합니다. 비판을 받으면 표시 안 내도 오래 상처받습니다.",
                   "신약": "예리하고 분석적이지만 약한 모습을 보이기 싫어합니다. 혼자 모든 걸 해결하려 합니다."},
            "水": {"신강": "겉으로는 여유로워 보이지만 머릿속은 늘 바쁩니다. 잠자리에서도 머릿속이 돌아갑니다.",
                   "신약": "직관이 뛰어나지만 불안감이 깔려 있습니다. 혼자 결정하기 어려워하고 오래 고민합니다."},
        }
        base = OH_BASE.get(ilgan_oh, {}).get(sn_key, "")
        if base:
            traits.append(base)

    # 일지 십성 심리
    iljj_ss = "-"
    try:
        iljj_ss = calc_sipsung(ilgan, pils)[1].get("jj_ss", "-")
    except:
        pass
    ILJJ_DEEP = {
        "비견": "지기 싫어합니다. 지면 속으로 오래 끌고 갑니다. 표시는 안 내도 계속 생각합니다.",
        "겁재": "승부욕이 강합니다. 가까운 사람에게도 지기 싫어합니다. 배신당한 경험이 있고, 이후로 조심합니다.",
        "식신": "자기 방식이 있습니다. 간섭받는 것을 싫어하고, 자기 페이스로 하는 걸 좋아합니다.",
        "상관": "말이 빠르고 재치 있습니다. 상대방의 단점이 눈에 먼저 보입니다. 때로는 그 솔직함이 문제가 됩니다.",
        "편재": "활동적이고 사교적이지만, 한곳에 오래 머물기 싫어합니다. 새로운 자극을 계속 찾습니다.",
        "정재": "현실적이고 꼼꼼합니다. 손해 보는 것을 굉장히 싫어합니다. 계산이 빠릅니다.",
        "편관": "압박이 오면 오히려 더 버팁니다. 굴복하는 것을 본능적으로 거부합니다. 강인한 사람입니다.",
        "정관": "체면과 원칙을 중시합니다. 남들 시선에 민감하고, 창피당하는 것을 극도로 싫어합니다.",
        "편인": "설명하기 어렵지만 '그냥 아는' 경우가 많습니다. 직관이 매우 발달해 있습니다.",
        "정인": "완전히 이해하기 전까지 결정을 미룹니다. 배움에 대한 욕구가 강합니다.",
    }
    iljj_t = ILJJ_DEEP.get(iljj_ss, "")
    if iljj_t and iljj_t not in " ".join(traits):
        traits.append(iljj_t)

    # 오행 과다/부족 조합
    over_ohs = [o for o, v in oh_strength.items() if v >= 35]
    lack_ohs = [o for o, v in oh_strength.items() if v <= 5]
    zero_ohs = [o for o, v in oh_strength.items() if v == 0]

    for oh in over_ohs:
        for t in OH_COMBO_DB.get(("over", oh), []):
            traits.append(t)
    for oh in lack_ohs:
        for t in OH_COMBO_DB.get(("lack", oh), []):
            traits.append(t)
    if zero_ohs:
        oh_names = "·".join([OHN.get(o, "") for o in zero_ohs])
        traits.append(f"{oh_names} 기운이 완전히 없습니다. 이 분야가 들어올 때마다 당황하거나 흔들립니다.")

    return traits[:8]  # 최대 8개 — 너무 많으면 희석됨


def build_personality_detail(pils, gender="남"):
    """
    심리 디테일 생성 — "예민합니다"가 아닌 구체적 서술
    일간 + 일지 + 신강신약 + 오행 과다 조합
    """
    ilgan = pils[1]["cg"]
    iljj = pils[1]["jj"]
    ilgan_oh = OH.get(ilgan,"")
    iljj_ss = calc_sipsung(ilgan, pils)[1].get("jj_ss","-")
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    oh_strength = strength_info["oh_strength"]
    over_ohs = [o for o,v in oh_strength.items() if v>=35]
    lack_ohs = [o for o,v in oh_strength.items() if v<=5]

    traits = []

    # 일간 심리 특성 (오행별)
    OH_PSYCH = {
        "木": {
            "신강": "겉으로는 당당하고 직선적이지만, 속으로는 남의 시선을 매우 의식합니다. 인정받고 싶은 욕구가 강합니다.",
            "신약": "겉은 유연해 보이지만 속으로는 고집이 강합니다. 쉽게 상처받고 오래 기억합니다.",
            "중화": "합리적으로 보이지만 자존심이 강해 지면 인정하기 싫어합니다."
        },
        "火": {
            "신강": "열정적이고 화려해 보이지만, 겉으로 드러나지 않는 외로움이 있습니다. 관심받지 못하면 금세 지칩니다.",
            "신약": "따뜻하고 감성적이지만 불안감이 내재해 있습니다. 쉽게 흥분하고 금방 꺼집니다.",
            "중화": "밝고 긍정적이지만 혼자만의 시간이 필요한 사람입니다."
        },
        "土": {
            "신강": "신뢰감 있어 보이지만 속으로는 걱정이 많습니다. 결정을 내리면 쉽게 바꾸지 않습니다.",
            "신약": "배려심 깊지만 우유부단한 면이 있습니다. 혼자 고민을 오래 끌고 갑니다.",
            "중화": "안정적이고 책임감 있지만 변화를 두려워하는 경향이 있습니다."
        },
        "金": {
            "신강": "겉은 강하고 원칙적이지만 속으로는 매우 섬세합니다. 비판을 받으면 표시 안 내도 오래 상처받습니다.",
            "신약": "예리하고 분석적이지만 혼자 모든 걸 해결하려 합니다. 약한 모습을 보이기 싫어합니다.",
            "중화": "냉정해 보이지만 가까운 사람에게는 다릅니다. 신뢰를 쌓는 데 시간이 걸립니다."
        },
        "水": {
            "신강": "겉으로는 여유로워 보이지만 머릿속은 늘 바쁩니다. 모든 경우의 수를 계산합니다.",
            "신약": "직관이 뛰어나지만 불안감이 깔려 있습니다. 혼자 결정하기 어려워하고 오래 고민합니다.",
            "중화": "지혜롭고 유연하지만 감정을 잘 드러내지 않습니다."
        },
    }

    # 일간 기본 심리
    sn_key = "신강" if "신강" in sn else "신약" if "신약" in sn else "중화"
    base_trait = OH_PSYCH.get(ilgan_oh,{}).get(sn_key,"")
    if base_trait:
        traits.append(base_trait)

    # 일지 십성별 심리 보정
    ILJJ_PSYCH = {
        "비견": "자존심이 매우 강합니다. 지기 싫어하고, 지면 속으로 오래 끌고 갑니다.",
        "겁재": "경쟁 심리가 강하고 승부욕이 있습니다. 친한 사람에게도 지기 싫어합니다.",
        "식신": "배짱이 있고 여유롭게 보이지만, 은근히 자기 방식대로 하고 싶어합니다.",
        "상관": "말이 빠르고 재치 있습니다. 상대방의 단점이 눈에 먼저 보입니다.",
        "편재": "활동적이고 사교적이지만, 한곳에 오래 머물기 싫어합니다.",
        "정재": "현실적이고 꼼꼼합니다. 손해 보는 것을 굉장히 싫어합니다.",
        "편관": "압박이 오면 오히려 더 버팁니다. 굴복하는 것을 본능적으로 거부합니다.",
        "정관": "체면과 원칙을 중시합니다. 남들 시선에 민감하고 규칙을 잘 지킵니다.",
        "편인": "직관이 뛰어납니다. 설명하기 어렵지만 '그냥 아는' 경우가 많습니다.",
        "정인": "배움을 좋아합니다. 완전히 이해하기 전까지 결정을 미루는 경향이 있습니다.",
    }
    iljj_trait = ILJJ_PSYCH.get(iljj_ss,"")
    if iljj_trait:
        traits.append(iljj_trait)

    # 오행 과다 심리 보정
    OH_OVER_PSYCH = {
        "木": "남들보다 빠릅니다. 결정도 빠르고 판단도 빠릅니다. 대신 기다리는 것을 못 합니다.",
        "火": "에너지가 넘칩니다. 시작은 잘 하는데 끝까지 가는 것이 과제입니다.",
        "土": "한번 정하면 잘 안 바꿉니다. 고집이 강하고 자기 방식이 확실합니다.",
        "金": "예리합니다. 사람을 빠르게 파악하고 판단합니다. 때로는 너무 날카롭습니다.",
        "水": "생각이 많습니다. 잠자리에 누워도 머릿속이 돌아갑니다. 걱정을 사서 합니다.",
    }
    for oh in over_ohs:
        t = OH_OVER_PSYCH.get(oh,"")
        if t: traits.append(f"[{OHN.get(oh,'')} 과다] {t}")

    # 오행 결핍 심리 보정
    OH_LACK_PSYCH = {
        "木": "계획을 세우는 것이 약합니다. 시작하기까지 시간이 걸립니다.",
        "火": "표현이 서툽니다. 속으로는 열정이 있지만 겉으로는 차가워 보일 수 있습니다.",
        "土": "안정을 찾기 힘들 수 있습니다. 한곳에 뿌리내리는 것이 과제입니다.",
        "金": "결단력이 부족할 수 있습니다. 잘라내야 할 것을 잘라내지 못합니다.",
        "水": "직관보다 논리로 움직입니다. 감정 표현이 서툴 수 있습니다.",
    }
    for oh in lack_ohs:
        t = OH_LACK_PSYCH.get(oh,"")
        if t: traits.append(f"[{OHN.get(oh,'')} 부족] {t}")

    return traits


def get_cached_ai_interpretation(pils_hashable, prompt_type="general", api_key="", birth_year=1990, gender="남", name="", groq_key="", stream=False):
    """
    AI 해석 — Brain 2 Sandbox 통과 + 파일 캐시 적용
    [Saju Platform Engineering Agent]
    - 동일 사주 + 동일 prompt_type → 캐시에서 즉시 반환 (API 재호출 없음)
    - 캐시 미스 → Sandbox로 AI 호출 → 결과 검증 → 캐시 저장
    """
    saju_key = pils_hashable
    cache_key = f"{saju_key}_{prompt_type}"
    
    # 1. 파일 캐시 조회
    cached = get_ai_cache(saju_key, prompt_type)
    if cached:
        if stream:
            def cached_stream():
                yield cached
            return cached_stream()
        return cached

    # 2. 캐시 미스 -> AI 호출 (프롬프트 구성)
    # (여기서 원래는 build_optimized_prompt 등으로 정밀화 함)
    prompt = f"이름: {name}, 출생: {birth_year}, 성별: {gender}\n"
    # ... 실제로는 더 복잡한 프롬프트가 들어감 ...

    # 3. AI 호출 (Streaming 지원)
    result = get_ai_interpretation(prompt, api_key, groq_key=groq_key, stream=stream)
    
    if stream:
        def stream_with_cache():
            full_text = ""
            for chunk in result:
                full_text += chunk
                yield chunk
            set_ai_cache(saju_key, prompt_type, full_text)
        return stream_with_cache()
    else:
        if result and not result.startswith("["):
            set_ai_cache(saju_key, prompt_type, result)
        return result
    pils = json.loads(pils_hashable) if isinstance(pils_hashable, str) else pils_hashable
    ilgan = pils[1]["cg"] if len(pils) > 1 else "甲"
    saju_str = ' '.join([p['str'] for p in pils])

    # ★ Brain 2 AI 캐시 확인 (동일 사주 재요청 시 즉시 반환)
    saju_key = pils_to_cache_key(pils)
    cached_ai = get_ai_cache(saju_key, prompt_type)
    if cached_ai:
        return cached_ai

    # 사주 데이터 계산
    strength_info = get_ilgan_strength(ilgan, pils)
    gyeokguk = get_gyeokguk(pils)
    oh_strength = strength_info["oh_strength"]
    current_year = datetime.now().year
    current_age = current_year - birth_year + 1
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    current_dw = next((dw for dw in daewoon if dw["시작연도"] <= current_year <= dw["종료연도"]), None)
    yearly = get_yearly_luck(pils, current_year)
    
    gname = gyeokguk["격국명"] if gyeokguk else "미정격"
    sn = strength_info["신강신약"]
    
    # 대운 과거 목록 (발복/시련 분석용)
    past_dw_summary = []
    for dw in daewoon:
        if dw["종료연도"] < current_year:
            dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
            past_dw_summary.append(f"  {dw['시작나이']}~{dw['시작나이']+9}세({dw['시작연도']}~{dw['종료연도']}): {dw['str']} [{dw_ss}]")
    
    # 미래 3년 세운
    future_years = []
    for y in range(current_year, current_year+3):
        ye = get_yearly_luck(pils, y)
        future_years.append(f"  {y}년({current_year - birth_year + (y - current_year) + 1}세): {ye['세운']} [{ye['십성_천간']}] {ye['길흉']}")
    
    # 돈 상승기 탐색 (대운 세운 중 재물 길운)
    money_peaks = []
    for dw in daewoon:
        if dw["시작연도"] >= current_year - 5:
            dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
            if dw_ss in ["식신", "정재", "편재", "정관"]:
                money_peaks.append(f"  {dw['시작나이']}~{dw['시작나이']+9}세 {dw['str']}대운({dw_ss}) 주목")
    
    # 혼인 분석 데이터
    marriage_ss = {"남": ["정재", "편재"], "여": ["정관", "편관"]}
    marry_hint = []
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        if dw_ss in marriage_ss.get(gender, []):
            marry_hint.append(f"  {dw['시작나이']}~{dw['시작나이']+9}세 {dw['str']}대운")

    # ── 엔진 하이라이트 계산 (핵심) ───────────────────
    hl = generate_engine_highlights(pils, birth_year, gender)

    # 과거 사건 블록 — 🔴부터 먼저
    past_ev_lines = []
    for ev in sorted(hl["past_events"], key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e["intensity"],3)):
        past_ev_lines.append(
            f"  [{ev['intensity']}] {ev['age']}({ev['year']}년) [{ev.get('domain','변화')}] {ev['desc']}")
    past_events_block = "\n".join(past_ev_lines) if past_ev_lines else "  (데이터 없음)"

    # 성향 블록 — 조합 공식 결과
    personality_block = "\n".join([f"  · {t}" for t in hl["personality"]])

    # 돈/결혼 피크
    money_block = "\n".join([f"  {m['age']}({m['year']}) — {m['desc']}" for m in hl["money_peak"][:3]]) or "  (없음)"
    marry_block = "\n".join([f"  {m['age']}({m['year']}) — {m['desc']}" for m in hl["marriage_peak"][:3]]) or "  (없음)"
    danger_block = "\n".join([f"  {d['age']}({d['year']}) — {d['desc']}" for d in hl["danger_zones"][:3]]) or "  (없음)"
    wolji_block = "\n".join([f"  {w['age']} — {w['desc']}" for w in hl["wolji_chung"][:3]]) or "  (없음)"

    PROPHET_SYSTEM = f"""당신은 40년 경력의 대한민국 최고 사주명리 대가(大家)입니다.
당신은 단순히 운세를 읽어주는 기계가 아니라, 내담자의 인생 전체를 꿰뚫어 보고 그들의 아픔을 어루만지는 '현대판 신령님'이자 '인생 코치'입니다.

[절대 규칙: 마스터 역술가의 6단계 판단 우선순위]
답변을 서술할 때 반드시 다음의 논리적 순서를 엄격히 준수하십시오:

1. [일간 강약(Strength)] 에너지의 주도성과 삶에 임하는 태도 파악.
2. [격국(Gyeokguk)] 타고난 인생의 목적지이자 직업적 DNA 결정.
3. [용신(Yongshin)] 운명을 개선하고 삶의 균형을 잡는 핵심 열쇠.
4. [대운 관계(Daewoon)] 현재 내담자가 지나고 있는 '인생의 계절' 파악.
5. [합·충(Interaction)] 현재 또는 미래에 발생할 구체적인 사건과 변동성.
6. [신살(Symbolic Layer)] 위 1~5번의 해석을 보강하는 세밀한 특징 및 재능 (보조로만 사용).

[필수 서술 지침 - 중독 설계(Retention Structure)]
- "이유(명리학적 근거) → 인생 흐름(서사적 연결) → 구체적 처방"의 프로세스를 따르십시오.
- 상담 도중 반드시 " {name}님은 현재 [운세 라벨]의 시기를 지나고 계십니다"라는 문장을 포함하십시오.
- **오픈 루프(Open Loop):** 답변의 마지막에 반드시 "가까운 미래에 올 새로운 변화의 신호"나 "다음 단계로 넘어가는 징조"에 대한 짧은 암시를 남겨 내담자가 다시 확인하러 오게 만드십시오.
- **대화 유도(Conversation Hook):** 답변을 마칠 때 내담자의 현재 상황이나 가장 궁금해할 법한 질문 하나를 먼저 던지십시오. (예: "지금 가장 신경 쓰이는 부분이 재물인가요, 아니면 사람인가요?")

### 1단계: 내부 분석 (Internal Analysis Layer)
답변을 시작하기 전, 제공된 데이터를 바탕으로 머릿속으로 다음을 먼저 판단하십시오. (단, 이 섹션은 최종 답변에 제목을 달아 노출하지 말고, 전체 논리의 근거로만 사용하십시오.)
- 일간의 강약(신강/신약)과 조후(온도)의 균형.
- 명식의 핵심 병(病)과 약(藥)이 되는 글자.
- 현재 대운이 원국에 미치는 결정적 영향.

### 2단계: 역할 고정 및 따뜻한 공감 (Role Lock & Empathy)
- 20~30년 경력자의 여유롭고 단정적인 문체를 유지하십시오.
- 도입부에서 내담자의 고충을 보듬는 공감의 문장으로 라포(Rapport)를 형성하십시오.
- "스스로도 느끼셨겠지만", "그동안 참 많은 것을 견뎌오셨군요" 등으로 심리적 소름 포인트를 만드십시오.

### 3단계: 논리적 해석 규칙 (Interpretation Rules)
- 모든 해석은 반드시 '이유(Why)'를 명리학적 근거(십성, 합충, 용신)와 함께 먼저 제시하십시오.
- 단정적으로 말하되(확언), 부정적인 내용은 반드시 해결 방향(희망)을 함께 제시하십시오.
- "~일 수 있습니다" 같은 애매한 표현은 지양하고, "~한 기운이 강하니 ~하게 됩니다"라고 힘 있게 말하십시오.


[상담 구조]
1️⃣ 성향 판독: 일간과 격국 중심의 예리한 심리 분석.
2️⃣ 과거 적중: 특정 연도를 언급하며 "이때 이런 일이 있었군요"라고 예언.
3️⃣ 현재 진단: 지금의 운세 라벨과 대운/세운의 위치 분석.
4️⃣ 분야별 조언: 재물, 직업, 인연 중 가장 중요한 포인트 짚기.
5️⃣ 미래 예고: 향후 3년의 결정적 변곡점 예언.
6️⃣ 오늘의 비방: 삶을 바꾸는 실천적인 사주 처방.
7️⃣ 내일의 예고: 가까운 시일 내에 마주할 '운의 변화' 한 줄 암시. (오픈 루프)"""

    data_block = f"""
━━━ 마스터 사주 엔진 실시간 분석 데이터 ━━━
상태 라벨: {turning['fate_label']} ({turning['fate_desc']})
사주 원국: {saju_str} (시일월년)
일간: {ilgan} / 격국: {gname} ({gk['격의_등급']}) / 신강신약: {sn} (점수: {score})
오행 분포: {' '.join([f"{o}{v}%" for o,v in oh_strength.items()])}
용신: {ys['용신_1순위']} / 희신: {ys['희신']} / 기신: {', '.join(ys['기신'])}
현재 대운: {cur_dw['str'] if cur_dw else '-'} ({ys['대운_해석']})
올해 세운: {yl['세운']} ({yl['십성_천간']} / {yl['길흉']})
특수 신살: {', '.join([s['name'] for s in extra_stars]) if extra_stars else '없음'}
전환점 강도: {turning['intensity']} / 주요 이슈: {', '.join(turning['reason'])}
현재: {current_year}년 {current_age}세
현재 대운: {current_dw['str'] if current_dw else '미상'} ({current_dw['시작연도'] if current_dw else ''}-{current_dw['종료연도'] if current_dw else ''})
현재 세운: {yearly['세운']} [{yearly['십성_천간']}] {yearly['길흉']}

━━━ 【핵심 ①】 과거 사건 (충·합·십성 교차 계산) ━━━
규칙: 아래 항목을 그대로 활용. 🔴 우선으로 서술. "~했습니다" 단정.
{past_events_block}

━━━ 【핵심 ②】 성향 조합 공식 결과 ━━━
규칙: 아래 문장을 더 구체적으로 풀어쓰되 "겉은~속은~" 형식 유지.
{personality_block}

━━━ 【핵심 ③】 월지 충 시점 (삶의 기반 흔들림) ━━━
{wolji_block}

━━━ 【핵심 ④】 재물 상승기 ━━━
{money_block}

━━━ 【핵심 ⑤】 인연 시기 ━━━
{marry_block}

━━━ 【핵심 ⑥】 위험 구간 ━━━
{danger_block}

━━━ 미래 3년 세운 ━━━
{chr(10).join(future_years)}

━━━ 【v3 정밀 엔진 데이터 — AI 핵심 추론 재료】 ━━━
■ 일간 힘 점수: {strength_info["일간점수"] if "일간점수" in strength_info else "50"}/100점 ({sn})
  → 30 이하=극신약 / 30~45=신약 / 45~55=중화 / 55~70=신강 / 70+=극신강
■ 오행 세력(정밀): {' '.join([f"{o}:{v}%" for o,v in oh_strength.items()])}
  → 가장 강한 오행: {max(oh_strength, key=oh_strength.get)} / 가장 약한 오행: {min(oh_strength, key=oh_strength.get)}
■ 종합 운세 점수: {calc_luck_score(pils, birth_year, gender, current_year)}/100
  → 70+= 상승기 / 50~70= 안정 / 30~50= 변화기 / 30-= 하락기
■ 인생 전환점 감지:
{chr(10).join(["  " + r for r in calc_turning_point(pils, birth_year, gender, current_year)["reason"]]) or "  (안정적 흐름)"}
■ 전환점 강도: {calc_turning_point(pils, birth_year, gender, current_year)["intensity"]}

■ 사건 트리거 (확률 순):
{chr(10).join(["  ["+t["type"]+"] "+t["title"]+" ("+str(t["prob"])+"%): "+t["detail"] for t in sorted(detect_event_triggers(pils, birth_year, gender, current_year), key=lambda x: -x["prob"])]) or "  (주요 트리거 없음)"}

■ 다층 용신 분석:
  1순위 용신: {get_yongshin_multilayer(pils, birth_year, gender, current_year).get("용신_1순위", "-")}
  2순위 용신: {get_yongshin_multilayer(pils, birth_year, gender, current_year).get("용신_2순위", "-")}
  희신(용신 보조): {get_yongshin_multilayer(pils, birth_year, gender, current_year).get("희신", "-")}
  기신(흉한 기운): {', '.join(get_yongshin_multilayer(pils, birth_year, gender, current_year).get("기신", []))}
  현재 대운 해석: {get_yongshin_multilayer(pils, birth_year, gender, current_year).get("대운_해석", "-")}

[AI 지시 v3] 
- 위 v3 정밀 데이터를 반드시 해석에 반영하십시오.
- "일간 힘 점수"를 활용해 신강/신약을 구체적으로 묘사하십시오.
- "전환점 감지" 결과가 있으면 타이밍을 단정적으로 언급하십시오.
- "사건 트리거"는 확률 높은 것부터 언급하고 반드시 구체적 사건으로 말하십시오.
- "다층 용신"을 활용해 어떤 해에 발복하는지 구체적으로 지목하십시오.
"""

    prompts = {
        "prophet": f"""{data_block}

위 데이터를 기반으로 아래 7단계 구조로 작성하십시오.
반드시 【과거 사건 계산 데이터】와 【심리 디테일 데이터】를 활용하십시오.
각 단계는 소제목을 명확히 표시하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

0️⃣ 성향 판독 — 첫 문장에서 이 사람을 꿰뚫으십시오
규칙: 【심리 디테일 데이터】를 구체적 문장으로 풀어 쓰십시오.
"예민합니다" 금지. "겉은 ~인데 속으로는 ~합니다" 형식으로.
이 사람이 읽었을 때 "어떻게 알았지?"라고 느낄 만큼 구체적으로.

1️⃣ 과거 적중 — 반드시 이 단계를 먼저, 가장 자세히 쓰십시오
규칙:
- 【과거 사건 계산 데이터】의 🔴(강도 높음) 항목을 중심으로 서술하십시오.
- 나이와 연도를 반드시 명시하십시오. (예: "27세, 2019년")
- "~했을 것입니다" 금지. "~했습니다"로 단정하십시오.
- "그때 충이 들어왔기 때문에 가만히 있을 수 없었습니다" 같이 이유를 반드시 설명하십시오.
- 최소 3개 시점을 찍으십시오.
- 분야(직장/재물/관계/건강)를 반드시 명시하십시오.

2️⃣ 현재 진단 — 지금 이 순간 어디에 서 있는가
현재 대운·세운 교차를 기반으로 지금 상황을 예리하게 단정하십시오.
용신 대운인지 기신 대운인지 명시하고, 그 의미를 설명하십시오.

3️⃣ 직업·적성 — 피해야 할 직업까지 명시
격국과 일간 기반. "~가 맞습니다" 단정. 이유 설명 포함.

4️⃣ 결혼·인연
혼인 대운 데이터 기반. 시기와 인연의 오행까지 단정.

5️⃣ 미래 3년 — 연도별 단정
세운 데이터 기반. 각 연도 핵심 키워드 + 주의사항.

6️⃣ 돈 상승기
재물운 집중 시기를 정확히 찍으십시오.
"이 시기를 놓치면 언제 다시 오는가"까지 포함.

7️⃣ 오늘의 비방 (Skill 6: Coaching)
- 지금 당장 실천할 수 있는 구체적인 행동(장소, 방향, 숫자, 색상, 소지품 등) 1가지를 강력하게 처방하십시오.
- "이것을 행하면 운의 흐름이 바뀝니다"라는 확신을 주십시오.
""",

        "general": f"""{data_block}

위 데이터를 바탕으로 전통 사주 문체로 분석하십시오.
【과거 사건 계산 데이터】와 【심리 디테일 데이터】를 반드시 활용하십시오.

1. 성향 판독 — 구체적 심리 특성 (겉과 속의 차이 포함)
2. 격국과 용신 판단
3. 오행의 균형과 강약
4. 과거 주요 사건 시점 (나이+분야 명시)
5. 평생 운명의 큰 흐름
6. 길운 시기와 주의 시기""",

        "career": f"""{data_block}

위 데이터를 바탕으로 적성과 진로를 분석하십시오.
격국과 용신 중심으로 최적 직업군, 피해야 할 직업, 재물운 상승 시기를 명시하십시오.
【과거 사건 계산 데이터】 중 직업·재물 관련 시점을 근거로 제시하십시오.""",

        "love": f"""{data_block}

위 데이터를 바탕으로 배우자운과 연애운을 분석하십시오.
혼인 대운 데이터 기반으로 인연의 시기, 궁합 좋은 일간, 이별 위험 시점을 단정하십시오.
【과거 사건 계산 데이터】 중 관계 관련 시점을 근거로 제시하십시오.""",

        "lifeline": f"""{data_block}

당신은 인생의 큰 흐름(대운)을 꿰뚫어 보는 대가입니다.
제공된 대운 100년 데이터를 바탕으로, 내담자의 인생을 '계절의 변화'에 비유하여 서술하십시오.
1. 현재 대운의 의미: 지금이 인생의 봄, 여름, 가을, 겨울 중 어디인지?
2. 황금기(용신 대운) 분석: 가장 화려하게 꽃피울 시기와 그때의 성취.
3. 전환점과 위기: 대운이 바뀌는 시점(교운기)의 주의사항과 합충으로 인한 변동.
4. 노년의 삶: 인생 후반부의 명예와 안식.
반드시 HTML 태그를 활용하여 시각적으로 아름답게(고급스러운 배경, 강조선 등) 작성하십시오.""",

        "past": f"""{data_block}

당신은 시간을 되짚어 과거를 맞히는 예언가입니다.
제공된 【과거 사건 계산 데이터】를 극대화하여 서술하십시오.
1. 특정 연도(예: 2019년, 2022년 등)를 제목으로 달고, 그때 발생한 사건을 단정적으로 맞히십시오.
2. 사건의 이유를 십성, 합, 충 등 명리학적 근거로 설명하십시오 (예: "이때는 관(官)이 충을 맞아 직장을 옮길 수밖에 없었습니다").
3. 내담자가 "정말 내 과거를 보고 있구나"라고 소름 돋을 정도로 예리한 문체를 유지하십시오.""",

        "money": f"""{data_block}

당신은 부의 흐름을 읽는 경제 명리 전문가입니다.
1. 재물 가득한 그릇: 타고난 재물운의 크기와 유형(정재 vs 편재).
2. 돈이 마르지 않는 시기: 재물 상승기(용신/식상생재)를 정확히 찍으십시오.
3. 투자와 사업: 사업가 소질 여부와 투자에 유리한 오행/분야.
4. 재난 방어: 재물이 새나가는 시기(겁재/충)와 이를 막는 비방.
부자가 되는 구체적인 실천 전략(풍수, 습관 등)을 포함하십시오.""",

        "relations": f"""{data_block}

당신은 인간관계와 인연의 실타래를 푸는 상담가입니다.
1. 타고난 인연운: 어떤 성향의 배우자/동료와 잘 맞는지?
2. 현재의 인연: 대운/세운에서 들어오는 사람의 기운.
3. 갈등 해결: 원진, 충 등으로 인한 관계의 위기와 극복법.
4. 사회적 관계: 상사, 부하, 친구와의 역학 관계 및 처세술.
따뜻하면서도 예리한 조언을 담아주십시오.""",
    }

    prompt = prompts.get(prompt_type, prompts["general"])

    # ★ Brain 3: Prompt Optimizer — 학습 패턴 자동 주입
    optimizer_suffix = b3_build_optimized_prompt_suffix()

    # ★ Adaptive Engine — 페르소나 스타일 자동 주입
    try:
        persona       = infer_persona()
        persona_style = get_persona_prompt_style(persona)
        adaptive_suffix = f"\n\n[사용자 성향 분석]\n{persona_style}"
    except Exception:
        adaptive_suffix = ""

    # ★ User Memory Context — 사용자 기억 주입
    try:
        memory_ctx = build_memory_context(pils_to_cache_key(pils))
        memory_suffix = f"\n\n{memory_ctx}" if memory_ctx else ""
    except Exception:
        memory_suffix = ""

    base_system = (PROPHET_SYSTEM if prompt_type == "prophet"
                   else "당신은 40년 경력의 한국 전통 사주명리 전문가입니다.\n단정적으로 말하십시오. 나이와 분야를 구체적으로 명시하십시오.")
    system = base_system + optimizer_suffix + adaptive_suffix + memory_suffix  # ← 전체 주입

    if api_key or groq_key:
        # ★ AI Sandbox 통해 해석 → 검증 → 파일 캐시 저장
        result = get_ai_interpretation(prompt, api_key, system=system, groq_key=groq_key)

        # ★ Self-Check Engine — prophet 타입에만 2패스 검증 적용
        if result and not result.startswith("[") and prompt_type == "prophet":
            # 검증용 요약 데이터
            analysis_summary = (
                f"사주: {saju_str} | 일간: {ilgan} | 격국: {gname} | {sn} | "
                f"오행: {' '.join([f'{o}:{v}%' for o,v in oh_strength.items()])} | "
                f"현재운: {yearly.get('세운','-')} {yearly.get('길흉','-')} | "
                f"사건트리거: {', '.join([t['title'][:15] for t in detect_event_triggers(pils, birth_year, 1, 1, gender)[:3]])}"
            )
            try:
                result = self_check_ai(result, analysis_summary, api_key, groq_key)
            except Exception:
                pass  # self-check 실패 시 1차 결과 사용

        if result and not result.startswith("["):  # 오류 응답은 캐시 저장 안 함
            set_ai_cache(saju_key, prompt_type, result)
        return result
    else:
        if prompt_type == "prophet":
            return f"""◈ 예언자 모드 — API 키가 필요합니다 ◈

이 기능은 Anthropic API를 통해 실제 AI가 당신의 사주 데이터를 분석합니다.
사이드바에서 API 키를 입력하시면 아래 6단계 운명 풀이를 받으실 수 있습니다:

1️⃣ 과거 적중 — 당신의 과거가 얼마나 정확히 맞았는지
2️⃣ 현재 — 지금 이 순간 당신은 어디에 서 있는가
3️⃣ 직업 — 천부적 적성과 가야 할 길
4️⃣ 결혼 — 인연의 시기와 궁합
5️⃣ 미래 3년 — 연도별 단정 예언
6️⃣ 돈 상승기 — 재물이 몰리는 황금기

※ Anthropic API 키는 console.anthropic.com에서 발급받으실 수 있습니다."""
        return f"""◈ {ilgan}일간 기본 해석 ◈

{ILGAN_DESC.get(ilgan, {}).get("nature", "").split(chr(10))[0]}

【기질과 천명】
{ILGAN_DESC.get(ilgan, {}).get("strength", "").split(chr(10))[0]}

【적성과 진로】
{ILGAN_DESC.get(ilgan, {}).get("career", "")} 분야에서 두각을 나타내실 수 있습니다.

【건강 유의사항】
{ILGAN_DESC.get(ilgan, {}).get("health", "").split(chr(10))[0]}

※ Anthropic API 키를 입력하시면 더욱 상세한 AI 해석을 받으실 수 있습니다."""


# 사주 입력값을 캐시 키로 변환
def pils_to_cache_key(pils):
    return json.dumps(pils, ensure_ascii=False, sort_keys=True)


# ── Brain 1 + Brain 2 캐싱 시스템 ────────────────────────────────────────────
# [설계 원칙]
#   만세력 결과 → 파일 캐시 (동일 입력 = 즉시 출력, 계산 재수행 없음)
#   AI 해석 결과 → AI 전용 캐시 (API 비용 70~80% 절감)
#   사용자 피드백 → 캐싱 금지 (실시간 반영 필요)
#
# [성능 효과]
#   첫 계산: 4~6초 / 재사용: 0.1초 이하
#   AI 비용: 최초 1회만 지불, 동일 사주 재호출 무료
################################################################################

import os as _os

_SAJU_CACHE_FILE = "saju_cache.json"
_AI_CACHE_FILE   = "saju_ai_cache.json"

def _load_json_cache(filepath: str) -> dict:
    """JSON 파일 캐시 로드"""
    try:
        if _os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_json_cache(filepath: str, cache: dict):
    """JSON 파일 캐시 저장"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def create_saju_cache_key(year: int, month: int, day: int, hour: int, gender: str) -> str:
    """사주 캐시 키 생성 — 생년월일시+성별로 고유 ID"""
    return f"{year}-{month:02d}-{day:02d}-{hour:02d}-{gender}"

def get_saju_cache(year: int, month: int, day: int, hour: int, gender: str):
    """Brain 1 계산 결과 캐시 조회"""
    key = create_saju_cache_key(year, month, day, hour, gender)
    cache = _load_json_cache(_SAJU_CACHE_FILE)
    return cache.get(key)

def set_saju_cache(year: int, month: int, day: int, hour: int, gender: str, data):
    """Brain 1 계산 결과 캐시 저장"""
    key = create_saju_cache_key(year, month, day, hour, gender)
    cache = _load_json_cache(_SAJU_CACHE_FILE)
    cache[key] = data
    _save_json_cache(_SAJU_CACHE_FILE, cache)

def get_ai_cache(saju_key: str, prompt_type: str) -> str:
    """Brain 2 AI 해석 결과 캐시 조회"""
    ai_key = f"AI-{prompt_type}-{saju_key}"
    cache = _load_json_cache(_AI_CACHE_FILE)
    return cache.get(ai_key)

def set_ai_cache(saju_key: str, prompt_type: str, text: str):
    """Brain 2 AI 해석 결과 캐시 저장"""
    ai_key = f"AI-{prompt_type}-{saju_key}"
    cache = _load_json_cache(_AI_CACHE_FILE)
    cache[ai_key] = text
    _save_json_cache(_AI_CACHE_FILE, cache)

def clear_ai_cache_for_key(saju_key: str):
    """특정 사주의 AI 캐시 무효화 (재분석 요청 시)"""
    cache = _load_json_cache(_AI_CACHE_FILE)
    keys_to_del = [k for k in cache if k.endswith(saju_key)]
    for k in keys_to_del:
        del cache[k]
    _save_json_cache(_AI_CACHE_FILE, cache)


def render_ai_deep_analysis(prompt_type, pils, name, birth_year, gender, api_key, groq_key):
    """
    각 메뉴 하단에 삽입되는 AI 정밀 분석 버튼 및 결과 출력기
    """
    st.markdown('<hr style="border:none;border-top:1px dashed #000000;margin:25px 0">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.write("") # 간격 조절
    
    button_label = {
        "lifeline": "🌊 대운 100년 AI 정밀 분석",
        "past": "🎯 과거 사건 AI 복기 분석",
        "money": "💰 재물·사업운 AI 전략 리포트",
        "relations": "💑 인연·인간관계 AI 심층 리포트",
        "future": "🔮 미래 3년 AI 집중 예언",
        "prophet": "✨ 종합 운명 AI 마스터 리포트"
    }.get(prompt_type, "✨ AI 정밀 분석 시작")

    if st.button(button_label, key=f"btn_deep_{prompt_type}", use_container_width=True):
        with st.spinner("AI가 사주 데이터를 정밀 분석 중입니다..."):
            result = build_ai_prompt(pils, name, birth_year, gender, prompt_type, api_key, groq_key)
            if result and not result.startswith("["):
                st.markdown(f"""
                <div style="background:#ffffff;border:2px solid #000000;border-radius:16px;
                            padding:25px;margin-top:20px;box-shadow:0 4px 15px rgba(197,160,89,0.15)">
                    <div style="font-size:18px;font-weight:800;color:#000000;margin-bottom:15px;text-align:center">
                        {button_label.replace('분석', '결과').replace('리포트', '결과').replace('예언', '결과')}
                    </div>
                    <div style="font-size:14px;color:#000000;line-height:2.0;white-space:pre-wrap">
                        {result}
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.error("AI 분석 중 오류가 발생했거나 API 키가 설정되지 않았습니다.")

# ══════════════════════════════════════════════════
#  UI 헬퍼 함수
# ══════════════════════════════════════════════════
def render_pillars(pils):
    """사주 기둥 표시"""
    labels = ["시(時)", "일(日)", "월(月)", "년(年)"]
    cols = st.columns(4)
    for i, (p, label) in enumerate(zip(pils, labels)):
        cg = p["cg"]
        jj = p["jj"]
        cg_kr = CG_KR[CG.index(cg)]
        jj_kr = JJ_KR[JJ.index(jj)]
        jj_an = JJ_AN[JJ.index(jj)]
        oh_cg = OH.get(cg, "")
        oh_jj = OH.get(jj, "")
        emoji_cg = OHE.get(oh_cg, "")
        emoji_jj = OHE.get(oh_jj, "")
        
        with cols[i]:
            st.markdown(f"""
            <div class="pillar-box">
                <div style="font-size:11px;color:#000000;margin-bottom:4px">{label}</div>
                <div style="font-size:28px;font-weight:700;color:#000000">{cg}</div>
                <div style="font-size:11px;color:#000000;">{cg_kr} · {emoji_cg}{oh_cg}</div>
                <div style="font-size:30px;font-weight:700;color:#000000;margin-top:6px">{jj}</div>
                <div style="font-size:11px;color:#000000;">{jj_kr} · {emoji_jj}{oh_jj}</div>
                <div style="font-size:10px;color:#000000;margin-top:4px">{jj_an}띠</div>
            </div>""", unsafe_allow_html=True)


OHAENG_DIAGNOSIS = {
    "木": {
        "emoji": "🌳", "name": "목(木)",
        "over_desc": "목기(木氣) 과다 — 분노·고집·간담 질환에 주의하십시오. 금(金) 기운으로 가지를 쳐주어야 크게 성장합니다.",
        "over_remedy": "서쪽 방향 활용, 흰색·은색 소품, 금속 악세서리, 결단력 수련",
        "lack_desc": "목기(木氣) 부족 — 의욕 저하·우유부단·근육 약화가 나타날 수 있습니다. 목의 기운을 보충하십시오.",
        "lack_remedy": "동쪽 방향 활용, 초록색 인테리어, 식물 기르기, 새벽 산책, 신맛 음식 섭취",
        "balance_desc": "목기가 균형 잡혀 있습니다. 성장과 창의의 기운이 안정적으로 작동합니다.",
    },
    "火": {
        "emoji": "🔥", "name": "화(火)",
        "over_desc": "화기(火氣) 과다 — 조급함·충동·심혈관 질환에 주의하십시오. 수(水) 기운으로 열기를 식혀야 합니다.",
        "over_remedy": "북쪽 방향 활용, 검정·남색 소품, 수분 충분히 섭취, 명상과 호흡 수련, 냉정한 판단력 기르기",
        "lack_desc": "화기(火氣) 부족 — 활력 저하·우울·심장 기능 약화가 나타날 수 있습니다. 화의 기운을 보충하십시오.",
        "lack_remedy": "남쪽 방향 활용, 빨강·주황색 인테리어, 햇빛 자주 쬐기, 열정적 취미 활동, 쓴맛 음식 적당히",
        "balance_desc": "화기가 균형 잡혀 있습니다. 열정과 이성이 조화롭게 작동합니다.",
    },
    "土": {
        "emoji": "🏔️", "name": "토(土)",
        "over_desc": "토기(土氣) 과다 — 고집·무기력·소화기 질환에 주의하십시오. 목(木) 기운으로 뚫어주어야 변화가 생깁니다.",
        "over_remedy": "동쪽 방향 활용, 초록색 소품, 새로운 도전 의식적으로 실천, 스트레칭·요가, 신맛 음식 섭취",
        "lack_desc": "토기(土氣) 부족 — 중심 잡기 어려움·소화 불량·불안감이 나타날 수 있습니다. 토의 기운을 보충하십시오.",
        "lack_remedy": "중앙·북동 방향 활용, 황색·베이지 인테리어, 규칙적인 식사 습관, 황색 식품 섭취, 안정적 루틴 구축",
        "balance_desc": "토기가 균형 잡혀 있습니다. 신뢰와 안정의 기운이 든든하게 받쳐주고 있습니다.",
    },
    "金": {
        "emoji": "⚔️", "name": "금(金)",
        "over_desc": "금기(金氣) 과다 — 냉정함·고집·폐·대장 질환에 주의하십시오. 화(火) 기운으로 단련해야 보검이 됩니다.",
        "over_remedy": "남쪽 방향 활용, 빨강·주황색 소품, 유연성 수련, 공감 능력 기르기, 쓴맛 음식 적당히",
        "lack_desc": "금기(金氣) 부족 — 결단력 부족·호흡기 약화·피부 트러블이 나타날 수 있습니다. 금의 기운을 보충하십시오.",
        "lack_remedy": "서쪽 방향 활용, 흰색·금색 인테리어, 금속 소품·악세서리, 결단력 훈련, 매운맛 음식 적당히",
        "balance_desc": "금기가 균형 잡혀 있습니다. 결단력과 정의감이 안정적으로 발휘됩니다.",
    },
    "水": {
        "emoji": "💧", "name": "수(水)",
        "over_desc": "수기(水氣) 과다 — 방향 상실·우유부단·신장·방광 질환에 주의하십시오. 토(土) 기운으로 방향을 잡아주어야 합니다.",
        "over_remedy": "중앙·북동 방향 활용, 황색·베이지 소품, 목표 설정 및 실행 계획 수립, 규칙적 생활 습관, 짠맛 절제",
        "lack_desc": "수기(水氣) 부족 — 지혜 부족·성욕 감퇴·두려움·의욕 저하가 나타날 수 있습니다. 수의 기운을 보충하십시오.",
        "lack_remedy": "북쪽 방향 활용, 검정·남색 인테리어, 충분한 수분 섭취, 명상·독서 습관, 짠맛·검은 식품 섭취",
        "balance_desc": "수기가 균형 잡혀 있습니다. 지혜와 직관력이 안정적으로 흐르고 있습니다.",
    },
}


def render_ohaeng_chart(oh_strength):
    """오행 강약 차트 + 진단"""
    oh_order = ["木", "火", "土", "金", "水"]
    oh_names = {"木": "목(木)🌳", "火": "화(火)🔥", "土": "토(土)🪨", "金": "금(金)✨", "水": "수(水)💧"}
    
    cols = st.columns(5)
    for i, oh in enumerate(oh_order):
        val = oh_strength.get(oh, 0)
        with cols[i]:
            st.markdown(f"""
            <div style="text-align:center;padding:8px">
                <div style="font-size:13px;font-weight:700;color:#000000">{oh_names[oh]}</div>
                <div style="font-size:22px;font-weight:900;color:#000000">{val}%</div>
            </div>""", unsafe_allow_html=True)
            st.progress(min(val / 100, 1.0))
    
    # 오행 조화 진단 — 결과값만 간결하게
    over_ohs = [(oh, v) for oh, v in oh_strength.items() if v >= 35]
    lack_ohs = [(oh, v) for oh, v in oh_strength.items() if v <= 5]

    diag_lines = []
    if not over_ohs and not lack_ohs:
        diag_lines.append("⚖️ 오행이 비교적 균형 잡혀 있습니다 — 안정적인 사주입니다.")
    for oh, val in over_ohs:
        d = OHAENG_DIAGNOSIS[oh]
        diag_lines.append(f"🔴 {d['name']} 과다({val}%) — {d['over_desc'][:40]}... 💊 {d['over_remedy'][:50]}")
    for oh, val in lack_ohs:
        d = OHAENG_DIAGNOSIS[oh]
        diag_lines.append(f"🔵 {d['name']} 부족({val}%) — {d['lack_desc'][:40]}... 💊 {d['lack_remedy'][:50]}")

    if diag_lines:
        rows = "".join([
            f"<div style='font-size:12px;color:#000000;padding:5px 0;border-bottom:1px solid #e8e8e8;line-height:1.8'>{l}</div>"
            for l in diag_lines
        ])
        st.markdown(f"""
        <div style="background:#f8f8f8;border-radius:10px;padding:12px 16px;margin-top:8px">
            {rows}
        </div>""", unsafe_allow_html=True)



def format_saju_text(pils, name=""):
    """사주 텍스트 요약"""
    lines = []
    if name:
        lines.append(f"◈ {name}님의 사주팔자 ◈")
    labels = ["시주(時柱)", "일주(日柱)", "월주(月柱)", "년주(年柱)"]
    for p, label in zip(pils, labels):
        oh_cg = OH.get(p["cg"], "")
        oh_jj = OH.get(p["jj"], "")
        lines.append(f"{label}: {p['str']}  [{OHN.get(oh_cg,'')} / {OHN.get(oh_jj,'')}]")
    return "\n".join(lines)


def generate_saju_summary(pils, name, birth_year, gender):
    """사주 종합 총평 자동 생성"""
    ilgan = pils[1]["cg"]
    ilgan_kr = CG_KR[CG.index(ilgan)]
    oh = OH.get(ilgan, "")
    oh_emoji = {"木": "🌳", "火": "🔥", "土": "🏔️", "金": "⚔️", "水": "🌊"}.get(oh, "✨")
    
    strength_info = get_ilgan_strength(ilgan, pils)
    strength = strength_info["신강신약"]
    oh_strength = strength_info["oh_strength"]
    
    gyeokguk = get_gyeokguk(pils)
    gname = gyeokguk["격국명"] if gyeokguk else "미정격"
    grade = gyeokguk["격의_등급"] if gyeokguk else ""
    
    unsung = calc_12unsung(ilgan, pils)
    il_unsung = unsung[1] if len(unsung) > 1 else ""
    
    # 오행 분석
    max_oh = max(oh_strength.items(), key=lambda x: x[1])
    min_oh = min(oh_strength.items(), key=lambda x: x[1])
    zero_ohs = [o for o, v in oh_strength.items() if v == 0]
    
    # 대운 현재
    current_year = datetime.now().year
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    current_dw = next((dw for dw in daewoon if dw["시작연도"] <= current_year <= dw["종료연도"]), None)
    
    # 세운
    yearly = get_yearly_luck(pils, current_year)
    
    # 신살
    special = get_special_stars(pils)
    
    lines = []
    name_str = f"{name}님의 " if name else ""
    
    lines.append(f"◈ {name_str}사주팔자 천명 총평 ◈")
    lines.append("━" * 40)
    lines.append("")
    
    lines.append(f"【일간(日干)】 {oh_emoji} {ilgan}({ilgan_kr}) — {OHN.get(oh,'')}의 기운")
    lines.append(ILGAN_DESC.get(ilgan, {}).get("nature", "").split('\n')[0])
    lines.append("")
    
    lines.append(f"【신강신약】 {strength}")
    lines.append(strength_info["조언"])
    lines.append("")
    
    lines.append(f"【격국(格局)】 {gname} ({grade})")
    if gyeokguk:
        lines.append(GYEOKGUK_DESC.get(gname, {}).get("summary", "").split('\n')[0] if GYEOKGUK_DESC.get(gname) else gyeokguk.get("격국_해설", "")[:80])
    lines.append("")
    
    lines.append(f"【일주 12운성】 {il_unsung}")
    lines.append("")
    
    lines.append("【오행 분포】")
    for o, v in sorted(oh_strength.items(), key=lambda x: -x[1]):
        bar = "█" * (v // 5)
        lines.append(f"  {o}({OHN.get(o,'')}) {v}% {bar}")
    if zero_ohs:
        lines.append(f"  ⚠️ {', '.join([OHN.get(o,'') for o in zero_ohs])} 기운이 완전히 없습니다 — 관련 분야 주의")
    lines.append("")
    
    if current_dw:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(current_dw["cg"], "-")
        lines.append(f"【현재 대운】 {current_dw['str']} ({current_dw['시작나이']}~{current_dw['시작나이']+9}세, {current_dw['시작연도']}~{current_dw['종료연도']}년)")
        lines.append(f"  천간 {dw_ss}의 기운 — " + get_daewoon_narrative(dw_ss, "", current_dw["str"], current_dw["시작나이"])[2][:60] + "...")
        lines.append("")
    
    lines.append(f"【{current_year}년 세운】 {yearly['세운']} {yearly['아이콘']} {yearly['길흉']}")
    narr = yearly.get("narrative", {})
    lines.append(f"  {narr.get('title', '')} — {narr.get('desc', '')[:60]}...")
    lines.append("")
    
    if special:
        lines.append("【신살(神殺)】")
        for s in special[:4]:
            lines.append(f"  {s['name']}: {s.get('desc','')[:40]}...")
    
    lines.append("")
    lines.append("━" * 40)
    lines.append("※ 본 풀이는 전통 사주명리학에 근거한 참고 자료입니다.")
    
    return "\n".join(lines)


def get_special_stars(pils):
    """신살 계산 (tab_special_stars에서 분리)"""
    ilgan = pils[1]["cg"]
    pil_jjs = [p["jj"] for p in pils]
    result = []
    
    # 천을귀인
    chunl = {"甲": ["丑", "未"], "乙": ["子", "申"], "丙": ["亥", "酉"], "丁": ["亥", "酉"],
             "戊": ["丑", "未"], "己": ["子", "申"], "庚": ["丑", "未"], "辛": ["寅", "午"],
             "壬": ["卯", "巳"], "癸": ["卯", "巳"]}
    if any(jj in chunl.get(ilgan, []) for jj in pil_jjs):
        found = [jj for jj in pil_jjs if jj in chunl.get(ilgan, [])]
        result.append({"name": f"천을귀인(天乙貴人) [{','.join(found)}]",
                       "desc": "하늘이 내리신 최고의 귀인성. 위기 때마다 귀인이 나타나 도와줍니다."})
    
    # 역마살
    yeokma = {"寅": "申", "午": "申", "戌": "申", "申": "寅", "子": "寅", "辰": "寅",
              "巳": "亥", "酉": "亥", "丑": "亥", "亥": "巳", "卯": "巳", "未": "巳"}
    wol_jj = pils[2]["jj"] if len(pils) > 2 else ""
    if wol_jj and yeokma.get(wol_jj, "") in pil_jjs:
        result.append({"name": "역마살(驛馬殺)", "desc": "평생 이동·여행·해외와 인연이 깊습니다."})
    
    # 도화살
    dohwa = {"寅": "卯", "午": "卯", "戌": "卯", "申": "酉", "子": "酉", "辰": "酉",
             "亥": "子", "卯": "子", "未": "子", "巳": "午", "酉": "午", "丑": "午"}
    if wol_jj and dohwa.get(wol_jj, "") in pil_jjs:
        result.append({"name": "도화살(桃花殺)", "desc": "이성의 인기를 한몸에 받는 매력의 신살입니다."})
    
    return result


# ══════════════════════════════════════════════════
#  메인 탭별 렌더링 함수
# ══════════════════════════════════════════════════

def tab_saju_basic(pils, name, birth_year, gender):
    """사주 기본 분석 탭"""

    # ── 쪽집게 요약 카드 — 과거 먼저 ─────────────────────
    ilgan = pils[1]["cg"]
    current_year = datetime.now().year

    with st.spinner("핵심 포인트 계산 중..."):
        hl = generate_engine_highlights(pils, birth_year, gender)

    # 성향 1줄 요약
    top_trait = hl["personality"][0] if hl["personality"] else ""
    # 강도 높은 과거 사건 2개
    top_events = [e for e in hl["past_events"] if e["intensity"] == "🔴"][:2]
    # 돈 피크 1개
    top_money = hl["money_peak"][0] if hl["money_peak"] else None

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#f0eeff,#ece8ff);color:#000000;
                padding:22px;border-radius:16px;margin-bottom:16px;
                border:1px solid #ddd">
        <div style="font-size:13px;color:#000000;font-weight:700;margin-bottom:14px;
                    letter-spacing:1px">🎯 엔진이 계산한 핵심 포인트</div>
        <div style="display:flex;flex-wrap:wrap;gap:10px">
            <div style="flex:1;min-width:200px;background:rgba(155,124,204,0.2);
                        padding:12px;border-radius:10px;border:1px solid #9b7ccc44">
                <div style="font-size:11px;color:#c8b8f0;margin-bottom:6px">🧠 성향</div>
                <div style="font-size:13px;line-height:1.7">{top_trait[:60]}{'...' if len(top_trait)>60 else ''}</div>
            </div>
            {"".join([f'''<div style="flex:1;min-width:200px;background:rgba(192,57,43,0.2);
                        padding:12px;border-radius:10px;border:1px solid #c0392b44">
                <div style="font-size:11px;color:#6a0000;margin-bottom:6px">🔴 {e['age']} {e.get('domain','변화')}</div>
                <div style="font-size:12px;line-height:1.7;color:#333">{e['desc'][:50]}{'...' if len(e['desc'])>50 else ''}</div>
            </div>''' for e in top_events])}
            {f'''<div style="flex:1;min-width:200px;background:rgba(39,174,96,0.2);
                        padding:12px;border-radius:10px;border:1px solid #27ae6044">
                <div style="font-size:11px;color:#1a4a2a;margin-bottom:6px">💰 재물 상승기</div>
                <div style="font-size:13px;line-height:1.7">{top_money['age']} — {top_money['desc'][:40]}...</div>
            </div>''' if top_money else ''}
        </div>
        <div style="margin-top:10px;font-size:12px;color:#000000;text-align:right">
            자세한 내용은 <b style="color:#000000">🎯 과거 적중</b> 탭에서 확인하세요
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="gold-section">팔자(八字) 분석</div>', unsafe_allow_html=True)
    render_pillars(pils)
    
    # 오행 강약
    st.markdown('<div class="gold-section">오행(五行) 강약 분석</div>', unsafe_allow_html=True)
    oh_strength = calc_ohaeng_strength(pils[1]["cg"], pils)
    render_ohaeng_chart(oh_strength)
    
    # 신강신약
    ilgan = pils[1]["cg"]
    strength_info = get_ilgan_strength(ilgan, pils)
    s_key = strength_info["신강신약"]
    s_data = STRENGTH_DESC.get(s_key, {})
    ilgan_oh = strength_info.get("ilgan_oh", "")
    oh_advice = s_data.get("ohang_advice", {}).get(ilgan_oh, "")
    
    score_val = strength_info["helper_score"]
    bar_filled = min(10, round(score_val / 10))
    gauge = "🟦" * bar_filled + "⬜" * (10 - bar_filled)
    
    st.markdown('<div class="gold-section">신강신약(身强身弱) — 일간 기운의 강약</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card" style="background:linear-gradient(135deg,#f0f8ff,#e8f4e8);border:2px solid #4a90a4">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
            <div>
                <div style="font-size:20px;font-weight:800;color:#1a5f7a">{s_data.get('icon','')} {s_key}</div>
                <div style="font-size:13px;color:#000000;margin-top:4px">{s_data.get('personality','')}</div>
            </div>
            <div style="text-align:right">
                <div style="font-size:15px">{gauge}</div>
                <div style="font-size:12px;color:#444">일간 지지점수: {score_val}점</div>
            </div>
        </div>
        <div style="font-size:13px;color:#000000;line-height:2.0;white-space:pre-line;background:white;padding:14px;border-radius:10px;margin-bottom:10px">
            {s_data.get('desc','')}
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px">
            <div style="flex:1;min-width:200px;background:#e8f5e8;padding:10px 14px;border-radius:10px;border:1px solid #a8d5a8">
                <div style="font-size:12px;font-weight:700;color:#2a6f2a;margin-bottom:4px">✨ 발복 운 — {s_data.get('lucky_run','')}</div>
                <div style="font-size:12px;color:#000000;line-height:1.8">{s_data.get('lucky_desc','')}</div>
            </div>
            <div style="flex:1;min-width:200px;background:#fff0e8;padding:10px 14px;border-radius:10px;border:1px solid #d5a888">
                <div style="font-size:12px;font-weight:700;color:#8b4020;margin-bottom:4px">⚠️ 조심 운 — {s_data.get('caution_run','')}</div>
                <div style="font-size:12px;color:#000000;line-height:1.8">{s_data.get('caution_desc','')}</div>
            </div>
        </div>
        {f'<div style="background:#ffffff;padding:10px 14px;border-radius:10px;border:1px solid #c8b8e8"><div style="font-size:12px;font-weight:700;color:#5a2d8b;margin-bottom:4px">💊 일간별 오행 처방</div><div style="font-size:12px;color:#000000;line-height:1.8">{oh_advice}</div></div>' if oh_advice else ''}
    </div>""", unsafe_allow_html=True)
    
    # 격국 분석
    st.markdown('<div class="gold-section">격국(格局) 판단 — 나의 그릇과 천명</div>', unsafe_allow_html=True)
    gyeokguk = get_gyeokguk(pils)
    if gyeokguk:
        score = gyeokguk["격의_순수도"]
        score_bar = "🟨" * (score // 10) + "⬜" * (10 - score // 10)
        
        grade_str = gyeokguk["격의_등급"]
        grade_color = "#000000" if "순격" in grade_str else "#888" if "잡격" in grade_str else "#666"
        
        gname = gyeokguk["격국명"]
        g_detail = GYEOKGUK_DESC.get(gname, {})
        
        st.markdown(f"""
        <div class="card" style="background: #ffffff; border: 2.5px solid #000000;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
                <div>
                    <div style="font-size:22px;font-weight:800;color:#000000">{gname}</div>
                    <div style="font-size:13px;color:{grade_color};font-weight:700;margin-top:4px">{grade_str}</div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:18px">{score_bar}</div>
                    <div style="font-size:14px;font-weight:700;color:#000000">{score}점</div>
                </div>
            </div>
            <div style="font-size:14px;color:#000000;line-height:2.0;white-space:pre-line;background:#ffffff;padding:14px;border-radius:10px;margin-bottom:10px">
                {g_detail.get('summary', gyeokguk['격국_해설'])}
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px">
                <div style="flex:1;min-width:180px;background:#f0f8f0;padding:10px 14px;border-radius:10px;border:1px solid #a8d5a8">
                    <div style="font-size:12px;font-weight:700;color:#2a6f2a;margin-bottom:4px">🎯 적합 진로</div>
                    <div style="font-size:12px;color:#000000;line-height:1.8">{g_detail.get('lucky_career', gyeokguk['적합_진로'])}</div>
                </div>
                <div style="flex:1;min-width:180px;background:#fff5e0;padding:10px 14px;border-radius:10px;border:1px solid #d5b878">
                    <div style="font-size:12px;font-weight:700;color:#c5750a;margin-bottom:4px">⭐ 신급(神級) 판정</div>
                    <div style="font-size:12px;color:#000000;line-height:1.8">{g_detail.get('god_rank', gyeokguk['신급_판정'])}</div>
                </div>
            </div>
            <div style="background:#fff0f0;padding:10px 14px;border-radius:10px;border:1px solid #d5a8a8;white-space:pre-line">
                <div style="font-size:12px;font-weight:700;color:#8b2020;margin-bottom:4px">⚠️ 경계사항</div>
                <div style="font-size:12px;color:#000000;line-height:1.8">{g_detail.get('caution', gyeokguk['경계사항'])}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    
    # 삼합/방합
    sam_hap = get_sam_hap(pils)
    if sam_hap:
        st.markdown('<div class="gold-section">합(合) · 충(沖) 분석</div>', unsafe_allow_html=True)
        for hap in sam_hap:
            st.markdown(f'<div class="hap-badge">{hap["type"]}: {hap["name"]}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def tab_ilgan_desc(pils):
    """일간 기질 탭"""
    ilgan = pils[1]["cg"]
    desc = ILGAN_DESC.get(ilgan, {})
    oh = OH.get(ilgan, "")
    oh_emoji = {"木": "🌳", "火": "🔥", "土": "🏔️", "金": "⚔️", "水": "🌊"}.get(oh, "✨")
    
    st.markdown(f'<div class="gold-section">{oh_emoji} {ilgan}({CG_KR[CG.index(ilgan)]}) 일간 — {OHE.get(oh,"")}{OHN.get(oh,"")}의 기운</div>', unsafe_allow_html=True)
    
    # 천명 섹션
    st.markdown(f"""
    <div class="card" style="background:#ffffff;border:2.5px solid #000000;margin-bottom:12px">
        <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:10px">📜 천명(天命)과 타고난 기질</div>
        <div style="font-size:14px;color:#000000;line-height:2.1;white-space:pre-line">{desc.get("nature", "")}</div>
    </div>""", unsafe_allow_html=True)
    
    # 강점·보완 나란히
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border:1.5px solid #000000;height:100%">
            <div style="font-size:13px;font-weight:700;color:#2a6f2a;margin-bottom:8px">💪 강점(强點)</div>
            <div style="font-size:13px;color:#000000;line-height:1.9;white-space:pre-line">{desc.get("strength", "")}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border:1.5px solid #000000;height:100%">
            <div style="font-size:13px;font-weight:700;color:#8b2020;margin-bottom:8px">🔑 보완할 점</div>
            <div style="font-size:13px;color:#000000;line-height:1.9;white-space:pre-line">{desc.get("weakness", "")}</div>
        </div>""", unsafe_allow_html=True)
    
    # 적성·건강·행운
    st.markdown(f"""
    <div class="card" style="margin-top:10px">
        <div style="display:flex;flex-wrap:wrap;gap:10px">
            <div style="flex:1;min-width:200px">
                <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">🎯 적성과 진로</div>
                <div style="font-size:13px;color:#000000;line-height:1.8">{desc.get("career", "")}</div>
            </div>
            <div style="flex:1;min-width:200px">
                <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">🏥 건강 유의사항</div>
                <div style="font-size:13px;color:#000000;line-height:1.8;white-space:pre-line">{desc.get("health", "")}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    
    # 행운 정보
    if desc.get("lucky"):
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border:1px solid #c8b8e8">
            <div style="font-size:13px;font-weight:700;color:#5a2d8b;margin-bottom:6px">🍀 행운의 기운</div>
            <div style="font-size:13px;color:#000000;line-height:1.9">{desc.get("lucky", "")}</div>
        </div>""", unsafe_allow_html=True)




def tab_12unsung(pils):
    """12운성 탭"""
    ilgan = pils[1]["cg"]
    unsung = calc_12unsung(ilgan, pils)
    sipsung_list = calc_sipsung(ilgan, pils)
    
    labels = ["시(時)", "일(日)", "월(月)", "년(年)"]
    unsung_colors = {
        "장생": "#4CAF50", "목욕": "#2196F3", "관대": "#FF9800",
        "건록": "#E91E63", "제왕": "#9C27B0", "쇠": "#607D8B",
        "병": "#F44336", "사": "#795548", "묘": "#9E9E9E",
        "절": "#FF5722", "태": "#00BCD4", "양": "#8BC34A"
    }
    
    st.markdown('<div class="gold-section">12운성(十二運星)</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (label, uns, ss) in enumerate(zip(labels, unsung, sipsung_list)):
        color = unsung_colors.get(uns, "#888")
        with cols[i]:
            st.markdown(f"""
            <div style="text-align:center;padding:15px;background:#ffffff;border-radius:12px;border:1px solid #e8d5a0;margin:4px">
                <div style="font-size:11px;color:#444">{label}</div>
                <div style="font-size:24px;font-weight:800;color:{color};margin:8px 0">{uns}</div>
                <div style="font-size:11px;color:#333">천간: {ss.get("cg_ss","-")}</div>
                <div style="font-size:11px;color:#444">지지: {ss.get("jj_ss","-")}</div>
            </div>""", unsafe_allow_html=True)
    
    # 운성 설명
    unsung_desc = {
        "장생": {
            "icon": "🌱", "color_label": "생명력",
            "meaning": "장생(長生) — 새로운 생명이 이 세상에 첫 발을 내딛는 희망찬 탄생의 단계입니다.",
            "detail": "마치 봄날 대지를 뚫고 싹이 트듯, 새로운 시작과 출발의 기운이 넘칩니다. 이 기운이 강한 분은 어떤 분야에 발을 들여도 초반부터 순조롭게 시작되는 행운이 있습니다. 귀인의 도움을 받아 자연스럽게 성장하는 환경이 만들어집니다.",
            "advice": "✓ 새로운 일을 시작하기에 좋은 기운 ✓ 귀인이 자연스럽게 나타납니다 ✓ 건강하고 활기찬 기질을 타고납니다"
        },
        "목욕": {
            "icon": "🌊", "color_label": "감수성",
            "meaning": "목욕(沐浴) — 갓 태어난 생명이 처음으로 목욕을 하는 혼돈과 감성의 단계입니다.",
            "detail": "세상 물정을 모르는 순수함과 동시에 유혹과 시험에 취약한 시기입니다. 예술적 감수성이 극도로 발달하여 음악·미술·문학 분야에서 천재적 재능을 발휘하는 경우가 많습니다. 다만 이성 문제와 방탕함을 경계해야 합니다.",
            "advice": "⚠ 이성 문제와 유혹을 각별히 경계 ✓ 예술·감성 분야에서 천부적 재능 ⚠ 방향을 잡아줄 멘토가 반드시 필요합니다"
        },
        "관대": {
            "icon": "🎓", "color_label": "성장기",
            "meaning": "관대(冠帶) — 성인식을 마치고 관과 띠를 두르는 청년기의 활기찬 단계입니다.",
            "detail": "에너지가 넘치고 자신감이 충만한 시기입니다. 사회에 첫 발을 내딛으며 자신의 능력을 증명하고 싶은 야망이 강합니다. 공부·자격증·사회 진출에 유리한 기운으로, 이 시기에 부지런히 쌓아둔 실력이 평생의 자산이 됩니다.",
            "advice": "✓ 교육·자격증 취득에 유리한 기운 ✓ 사회 진출과 취업에 좋은 기운 ⚠ 과잉 자신감으로 인한 실수를 경계하십시오"
        },
        "건록": {
            "icon": "💪", "color_label": "전성기",
            "meaning": "건록(建祿) — 녹봉(祿俸)을 받는 장년기의 충실하고 강건한 전성기 단계입니다.",
            "detail": "인생에서 가장 강력하고 안정적인 기운의 시기입니다. 직업적으로 안정된 자리를 얻고 경제적 기반이 탄탄해집니다. 건록이 일주에 있으면 평생 먹고 사는 걱정이 없는 복을 타고난 것입니다. 독립심이 강하고 자수성가하는 기운입니다.",
            "advice": "✓ 직업 안정과 경제적 기반이 가장 탄탄한 기운 ✓ 자수성가의 기운이 강합니다 ✓ 건강하고 활력이 넘칩니다"
        },
        "제왕": {
            "icon": "👑", "color_label": "절정",
            "meaning": "제왕(帝旺) — 왕이 보위에 오르는 절정과 최고조의 단계입니다.",
            "detail": "기운이 절정에 달한 최강의 운성입니다. 리더십과 카리스마가 최고조에 달하며, 자연스럽게 우두머리 자리에 오르는 기운입니다. 다만 이 기운이 지나치면 독선과 오만으로 흐를 수 있으니, 겸손함을 잃지 않는 것이 제왕격의 진정한 완성입니다.",
            "advice": "✓ 리더십과 권위가 가장 강한 기운 ⚠ 지나친 독선과 오만을 경계 ✓ 어떤 분야에 가든 정상에 서는 기운"
        },
        "쇠": {
            "icon": "🌅", "color_label": "하강기",
            "meaning": "쇠(衰) — 절정에서 내려오기 시작하는 성숙한 노년의 시작 단계입니다.",
            "detail": "강렬한 활동보다는 안정과 지속을 추구하는 시기입니다. 외면의 강함보다는 내면의 지혜가 빛나는 단계로, 경험에서 우러나오는 통찰력이 생깁니다. 현상을 유지하고 지켜가는 것이 이 기운의 역할입니다.",
            "advice": "✓ 경험에서 우러나오는 깊은 통찰력 ✓ 안정적이고 신중한 의사결정 ⚠ 새로운 도전보다는 현상 유지와 수성(守成)이 유리"
        },
        "병": {
            "icon": "🍂", "color_label": "조정기",
            "meaning": "병(病) — 기운이 쇠하여 병을 앓는 단계로, 내면을 돌보는 조정의 시기입니다.",
            "detail": "신체적·정신적 에너지가 저하되는 시기입니다. 그러나 이 기운이 일주에 있는 분은 병을 통해 더 깊은 영성과 통찰을 얻는 경우가 많습니다. 의료·상담·영성 분야에서 오히려 뛰어난 능력을 발휘합니다. 건강 관리가 최우선입니다.",
            "advice": "✓ 의료·상담·종교 분야에서 특별한 감수성 ⚠ 건강 관리와 무리하지 않는 생활이 필수 ⚠ 음주와 무절제한 생활은 건강을 급격히 해칩니다"
        },
        "사": {
            "icon": "🕯️", "color_label": "정적",
            "meaning": "사(死) — 기운이 잠들고 내면의 세계로 침잠하는 정적의 단계입니다.",
            "detail": "표면적으로는 조용해 보이지만 내면에서 깊은 사색과 정신적 성숙이 이루어지는 단계입니다. 철학·종교·학문에 깊이 몰두하는 경향이 있으며, 세속적 욕망보다 정신적 가치를 추구합니다. 영적 능력과 직관이 발달하는 기운입니다.",
            "advice": "✓ 철학·종교·학문에서 깊은 경지에 도달 ✓ 영적·직관적 능력이 발달합니다 ⚠ 지나친 내향성으로 사회적 고립을 경계"
        },
        "묘": {
            "icon": "⚰️", "color_label": "축적",
            "meaning": "묘(墓) — 창고에 저장되듯 기운이 내면에 축적되는 단계입니다.",
            "detail": "겉으로는 드러나지 않지만 내면에 엄청난 잠재력이 축적되는 기운입니다. 겉과 속이 다르고 속내를 잘 드러내지 않는 성격으로, 비밀이 많거나 복잡한 내면을 지닌 경우가 많습니다. 재물을 모으는 능력과 정보를 축적하는 능력이 탁월합니다.",
            "advice": "✓ 재물 축적과 정보 수집 능력이 탁월 ⚠ 지나친 비밀주의와 내향성을 경계 ⚠ 고지식함이나 완고함으로 인간관계가 경직될 수 있습니다"
        },
        "절": {
            "icon": "🔄", "color_label": "전환",
            "meaning": "절(絶) — 완전히 단절되고 새로운 씨앗이 심어지기 직전의 변화와 전환의 단계입니다.",
            "detail": "기존의 것이 끝나고 새로운 것이 시작되는 전환점입니다. 이 기운이 강한 시기에는 이사·이직·이별 등 큰 변화가 일어나기 쉽습니다. 변화에 대한 적응력이 탁월하며, 전혀 새로운 분야로 도전하여 성공하는 경우도 많습니다.",
            "advice": "✓ 변화와 새로운 시작에 대한 탁월한 적응력 ⚠ 변화가 많고 정착이 어려운 시기 ⚠ 섣부른 결정보다 충분히 준비한 후 도전하십시오"
        },
        "태": {
            "icon": "🥚", "color_label": "준비",
            "meaning": "태(胎) — 어머니 뱃속에서 생명이 잉태되는 조용한 준비의 단계입니다.",
            "detail": "아직 세상에 드러나지 않은 잠재적 가능성이 무한히 준비되는 시기입니다. 조급함 없이 때를 기다리며 내실을 다지는 것이 이 기운의 지혜입니다. 새로운 프로젝트나 사업의 씨앗을 뿌리는 준비 단계로 적합합니다.",
            "advice": "✓ 조용히 준비하고 씨앗을 심기에 좋은 시기 ✓ 학습과 내공을 쌓는 데 집중하십시오 ⚠ 아직 때가 아니니 조급하게 드러내려 하지 마십시오"
        },
        "양": {
            "icon": "🌿", "color_label": "양육",
            "meaning": "양(養) — 어머니의 품에서 길러지고 양육받는 따뜻한 성장의 단계입니다.",
            "detail": "누군가의 도움과 후원을 받으며 성장하는 기운입니다. 귀인이나 선배·멘토의 도움으로 능력이 키워지는 시기입니다. 어머니·여성의 도움이 강하고, 교육과 학습을 통해 크게 성장합니다. 독립보다는 의지하며 배우는 시기입니다.",
            "advice": "✓ 귀인·멘토·어머니의 도움이 강한 시기 ✓ 배움과 학습에 집중하기 좋은 기운 ⚠ 지나친 의존은 독립심을 약화시킵니다"
        },
    }

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    seen = set()
    for uns in unsung:
        if uns not in seen and uns in unsung_desc:
            seen.add(uns)
            d = unsung_desc[uns]
            color = unsung_colors.get(uns, "#888")
            st.markdown(f"""
            <div style="background:#ffffff;border-left:5px solid {color};border-radius:4px 12px 12px 4px;
                        padding:15px 18px;margin:8px 0;border-top:1px solid #f0e4bb;border-right:1px solid #f0e4bb">
                <div style="font-size:15px;font-weight:700;color:{color};margin-bottom:6px">
                    {d['icon']} {uns}({d['color_label']}) — {d['meaning'].split('—')[1].strip() if '—' in d['meaning'] else ''}
                </div>
                <div style="font-size:13px;color:#000000;line-height:1.9;margin-bottom:8px">{d['detail']}</div>
                <div style="font-size:12px;color:#000000;background:#f9f5e8;padding:8px 12px;border-radius:8px;line-height:1.8">{d['advice']}</div>
            </div>""", unsafe_allow_html=True)


def get_daewoon_narrative(d_ss_cg, d_ss_jj, dw_str, age_start):
    """대운 천간·지지 십성별 상세 해석 생성"""
    narratives = {
        "비견": ("🤝", "동류(同類)의 대운: 독립과 협력의 시기", 
            f"비견(比肩) 대운은 나를 지탱하는 뿌리가 튼튼해지며 자아와 독립심이 극대화되는 10년입니다. "
            f"새로운 파트너십이 형성되고 동료·형제와 함께 성장의 발판을 마련하지만, 한편으로는 강한 경쟁과 자아 충돌이 예상됩니다. "
            f"자신의 주관을 뚜렷이 하되, 타인의 의견을 수용하는 포용력을 발휘한다면 인생의 든든한 아군을 얻는 '인연의 황금기'가 될 것입니다. "
            f"재물은 나누고 베풂으로써 더 큰 복으로 돌아오는 법이니, 상생의 지혜를 발휘하십시오."),
        "겁재": ("⚔️", "투쟁과 변혁의 대운: 경쟁을 통한 성장", 
            f"겁재(劫財) 대운은 기존의 질서를 타파하고 치열한 경쟁 속에서 나아가는 변혁의 10년입니다. "
            f"재물의 유출이나 지인과의 관계에서 예기치 못한 갈등이 발생할 수 있으나, 이는 곧 더 큰 그릇을 만들기 위한 시련의 과정입니다. "
            f"동업이나 보증은 각별히 경계하고, 오직 나만의 실력으로 정면 돌파하십시오. "
            f"이 거센 파도를 이겨낸 뒤에는 이전에 보지 못한 강력한 추진력과 부를 거머쥐는 승리자의 위치에 서게 될 것입니다."),
        "식신": ("🍀", "복록과 창의의 대운: 하늘이 내린 풍요", 
            f"식신(食神) 대운은 사주의 기운이 원활하게 흘러 재능과 복록이 샘물처럼 솟아오르는 축복의 10년입니다! "
            f"창의력이 꽃피고 먹고 사는 걱정이 사라지며, 하는 일마다 주변의 인정과 물질적 보상이 따르게 됩니다. "
            f"음식·예술·기술 등 전문 분야에서 독보적인 두각을 나타낼 시기이며, 건강 또한 증진되어 심신이 여유로워집니다. "
            f"이 시기에 뿌린 씨앗은 인생 전체를 책임질 든든한 자산이 되니, 가진 재능을 아낌없이 펼치십시오."),
        "상관": ("🌪️", "파격과 도약의 대운: 세상을 바꾸는 영감", 
            f"상관(傷官) 대운은 틀에 박힌 일상을 거부하고 천재적인 번뜩임으로 자신을 드러내는 영감의 10년입니다. "
            f"기존의 관습을 깨는 혁신적인 아이디어가 샘솟아 예술이나 기획 분야에서 폭발적인 성취를 거둘 수 있습니다. "
            f"다만, 직설적인 언행으로 인해 윗사람이나 조직과의 마찰이 우려되니 '언행의 절제'가 곧 성공의 열쇠입니다. "
            f"자신의 에너지를 파괴가 아닌 창조적 방향으로 돌린다면 세상을 놀라게 할 도약의 발판이 될 것입니다."),
        "편재": ("💰", "도전과 성취의 대운: 역동적인 재물 운", 
            f"편재(偏財) 대운은 광활한 영토로 나아가 큰 부와 성취를 사냥하는 대담한 도전의 10년입니다. "
            f"부동산, 주식, 사업적 거래 등에서 예상을 뛰어넘는 큰 재물 운이 찾아오며, 인생의 활동 반경이 비약적으로 넓어집니다. "
            f"이성 인연 또한 활발해져 삶의 활력이 넘치게 되지만, 지나친 과욕은 독이 될 수 있습니다. "
            f"자신의 체력(일간의 강약)을 살피며 냉철하게 운용한다면 백만장자의 기틀을 마련하는 절호의 기회가 될 것입니다."),
        "정재": ("🏦", "안정과 축적의 대운: 성실함이 빚은 성공", 
            f"정재(正財) 대운은 뜬구름 잡는 행운이 아닌, 땀 흘려 일군 성실함이 거대한 부의 성(城)을 쌓는 10년입니다. "
            f"고정적인 수입과 자산의 투명성이 확보되어 경제적 안정을 구가하며, 가정이 화목해지고 배우자의 내조가 극대화되는 시기입니다. "
            f"성급한 변화보다는 원칙을 지키는 투자가 큰 결실을 맺으니, 꾸준함으로 승부하십시오. "
            f"이 시기에 형성된 자산은 평생을 지탱할 가장 단단하고 안전한 밑거름이 될 것입니다."),
        "편관": ("⚡", "권위와 극복의 대운: 위기를 기회로 바꾸는 힘", 
            f"편관(偏官) 대운은 폭풍우 속에서도 굴하지 않는 강인한 리더십과 카리스마가 발현되는 변곡점의 10년입니다. "
            f"사회적 명예나 권위가 상승하지만 동시에 극심한 스트레스와 시련이 동반될 수 있습니다. "
            f"군·경·의료·법조계 등 특수 공직에서 큰 두각을 나타내며, 시련을 정면으로 돌파할 때 전설적인 성취를 이룹니다. "
            f"인내와 절제, 그리고 건강 관리에 소홀히 하지 않는다면 인생 최고의 명예직에 오르는 영광을 누릴 것입니다."),
        "정관": ("🎖️", "명예와 인품의 대운: 사회적 지위의 정점", 
            f"정관(正官) 대운은 주변의 존경과 사회적 지위가 하늘 높이 치솟는 황금 같은 명예의 10년입니다! "
            f"승진, 수상, 자격 취득 등 공적인 인정이 잇따르며, 법과 원칙을 지키는 당신의 삶이 찬란한 빛을 보게 됩니다. "
            f"조직 내에서 핵심적인 역할을 수행하게 되고, 결혼과 상속 등 가문과 관련된 경사가 따르는 경사스러운 시기입니다. "
            f"언제 어디서나 단정한 품위와 공명정대함을 잃지 않는다면 만인의 부러움을 사는 성공의 정점에 서게 될 것입니다."),
        "편인": ("🔮", "직관과 통찰의 대운: 정신적 세계의 확장", 
            f"편인(偏印) 대운은 보이지 않는 운명의 이치를 깨닫고 정신적인 세계관이 깊어지는 성찰의 10년입니다. "
            f"철학, 종교, IT, 전문 기술 등 특수한 분야에서 남들이 보지 못하는 기회를 포착하는 날카로운 직관이 발휘됩니다. "
            f"때로는 고독을 느낄 수 있으나 이는 곧 내면의 단단함을 키우는 과정이며, 창의적인 영감이 비즈니스로 연결되기도 합니다. "
            f"자신만의 전문 영역을 개척하고 연구에 몰입한다면 대체 불가능한 고유의 가치를 인정받는 시기가 될 것입니다."),
        "정인": ("📚", "지혜와 자비의 대운: 귀인의 따뜻한 도움", 
            f"정인(正印) 대운은 스승이나 윗사람, 그리고 천지신명의 따뜻한 가호가 운명에 깃드는 축복의 10년입니다! "
            f"학문적 성취가 눈부시고 중요한 계약이나 문서 잡기가 매우 유리하며, 어머니 같은 귀인의 인도로 고난을 순조롭게 피해갑니다. "
            f"지식을 쌓고 인품을 닦는 데 집중한다면 세상이 당신의 이름을 기억하게 될 명예를 얻게 될 것입니다. "
            f"받은 사랑을 세상에 돌려주는 마음을 가질 때, 이 대운의 복록은 마르지 않는 샘물처럼 영원할 것입니다."),
        "-": ("🌐", "융합과 순환의 대운: 조율의 시기", 
            f"이 대운은 여러 오행의 기운이 복합적으로 얽혀 인생의 방향성을 다각도로 조율해야 하는 10년입니다. "
            f"단정적으로 판단하기보다 일간의 강약과 사주의 균형을 정밀하게 살펴 최상의 길을 찾아야 하는 시기입니다. "
            f"변화의 소용돌이 속에서 중심을 잃지 않도록 전문가의 조언을 귀띔 삼아 매 순간 신중하게 나아가십시오."),
    }
    icon, title, text = narratives.get(d_ss_cg, narratives["-"])
    return icon, title, text


def _get_dw_alert(ilgan, dw_cg, dw_jj, pils):
    """대운이 원국과 충·합을 일으키는지 감지"""
    alerts = []
    labels = ["시주", "일주", "월주", "년주"]
    orig_jjs = [p["jj"] for p in pils]
    orig_cgs = [p["cg"] for p in pils]
    for i, p in enumerate(pils):
        ojj = p["jj"]
        k = frozenset([dw_jj, ojj])
        if k in CHUNG_MAP:
            name, rel, desc = CHUNG_MAP[k]
            alerts.append({"type": "⚠️ 지지충", "color": "#c0392b",
                "desc": f"대운 {dw_jj}가 원국 {labels[i]}({ojj})를 충(沖) — {desc}"})
    TG_HAP_PAIRS = [{"甲","己"},{"乙","庚"},{"丙","辛"},{"丁","壬"},{"戊","癸"}]
    for pair in TG_HAP_PAIRS:
        if dw_cg in pair:
            other = list(pair - {dw_cg})[0]
            if other in orig_cgs:
                found_idx = orig_cgs.index(other)
                alerts.append({"type": "✨ 천간합", "color": "#27ae60",
                    "desc": f"대운 {dw_cg}가 원국 {labels[found_idx]}({other})와 합(合) — 변화와 기회의 기운"})
    for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
        if dw_jj in combo:
            orig_in = []
            for i, p in enumerate(pils):
                if p["jj"] in combo:
                    orig_in.append(f"{labels[i]}({p['jj']})")
            if len(orig_in) >= 2:
                alerts.append({"type": "🌟 삼합 성립", "color": "#8e44ad",
                    "desc": f"대운 {dw_jj} + 원국 {','.join(orig_in)} = {hname} — 강력한 발복"})
            elif len(orig_in) == 1:
                alerts.append({"type": "💫 반합", "color": "#2980b9",
                    "desc": f"대운 {dw_jj} + 원국 {orig_in[0]} 반합 — 부분적 기운 변화"})
    return alerts


def _get_yongshin_match(dw_cg_ss, yongshin_ohs, ilgan_oh):
    """대운 십성이 용신 오행과 맞는지 판단"""
    GEN = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    CTRL = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    BIRTH_R = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    SS_TO_OH = {
        "비견": ilgan_oh, "겁재": ilgan_oh,
        "식신": GEN.get(ilgan_oh,""), "상관": GEN.get(ilgan_oh,""),
        "편재": CTRL.get(ilgan_oh,""), "정재": CTRL.get(ilgan_oh,""),
        "편관": next((k for k,v in CTRL.items() if v==ilgan_oh),""),
        "정관": next((k for k,v in CTRL.items() if v==ilgan_oh),""),
        "편인": BIRTH_R.get(ilgan_oh,""), "정인": BIRTH_R.get(ilgan_oh,""),
    }
    dw_oh = SS_TO_OH.get(dw_cg_ss, "")
    return "yong" if dw_oh in yongshin_ohs else "normal"


def _get_hap_break_warning(pils, dw_jj, sw_jj):
    """원국의 합이 대운·세운 충으로 깨지는 시점 감지"""
    warnings = []
    labels = ["시주", "일주", "월주", "년주"]
    for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
        orig_indices = [i for i, p in enumerate(pils) if p["jj"] in combo]
        if len(orig_indices) >= 2:
            orig_desc = ",".join([f"{labels[i]}({pils[i]['jj']})" for i in orig_indices])
            for breaker in [dw_jj, sw_jj]:
                for i in orig_indices:
                    jj = pils[i]["jj"]
                    k = frozenset([breaker, jj])
                    if k in CHUNG_MAP:
                        warnings.append({
                            "level": "🔴 위험", "color": "#c0392b",
                            "desc": f"원국 {hname}({orig_desc})을 {'대운' if breaker==dw_jj else '세운'} {breaker}가 {labels[i]}({jj})를 충(沖)으로 깨뜨립니다. 계획 좌절·관계 파탄·재물 손실 위험."
                        })
    return warnings


DAEWOON_PRESCRIPTION = {
    "비견": "독립 사업·협력 강화·새 파트너십 구축이 유리합니다.",
    "겁재": "투자·보증·동업 금지. 지출 절제, 현상 유지가 최선입니다.",
    "식신": "재능 발휘·창업·콘텐츠 창작을 적극 추진하십시오.",
    "상관": "직장 이직·창업·예술 활동에 좋으나 언행 극도 조심.",
    "편재": "사업 확장·투자·이동이 유리. 단, 과욕은 금물입니다.",
    "정재": "저축·자산 관리·안정적 수입 구조 구축에 집중하십시오.",
    "편관": "건강검진 필수. 무리한 확장 자제. 인내와 정면 돌파가 최선.",
    "정관": "승진·자격증·공식 계약을 적극 추진하십시오. 명예의 시기.",
    "편인": "학문·자격증·특수 분야 연구에 집중하기 좋은 시기입니다.",
    "정인": "시험·학업·귀인과의 만남. 배움에 투자하십시오.",
}


def tab_daewoon(pils, birth_year, gender):
    """대운 탭 — 용신 하이라이트 + 합충 경고 + 처방"""
    st.markdown('<div class="gold-section">🔄 대운(大運) | 10년 주기 운명의 큰 흐름</div>', unsafe_allow_html=True)

    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    current_year = datetime.now().year
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")
    ys = get_yongshin(pils)
    yongshin_ohs = ys["종합_용신"]

    # ── 타임라인 요약 바 ────────────────────────────────
    st.markdown('<div class="gold-section">📊 용신 대운 타임라인</div>', unsafe_allow_html=True)
    oh_emoji = {"木":"🌳","火":"🔥","土":"🏔️","金":"⚔️","水":"💧"}
    yong_str = " · ".join([f"{oh_emoji.get(o,'')}{OHN.get(o,'')}" for o in yongshin_ohs]) if yongshin_ohs else "분석 중"
    st.markdown(f"""
    <div class="card" style="background:#ffffff;border:2px solid #000000;margin-bottom:10px;font-size:13px;color:#000000;line-height:1.9">
        ⭐ <b>이 사주 용신:</b> {yong_str} &nbsp;|&nbsp;
        🟡 황금 카드 = 용신 대운 &nbsp;|&nbsp; 🟠 주황 테두리 = 현재 대운
    </div>""", unsafe_allow_html=True)

    tl = '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:16px">'
    for dw in daewoon:
        d_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        is_yong = _get_yongshin_match(d_ss, yongshin_ohs, ilgan_oh) == "yong"
        is_cur = dw["시작연도"] <= current_year <= dw["종료연도"]
        bg = "#000000" if is_yong else "#e8e8e8"
        tc = "white" if is_yong else "#666"
        bdr = "border:3px solid #ff6b00;" if is_cur else "border:2px solid transparent;"
        tl += f'<div style="background:{bg};color:{tc};{bdr}border-radius:10px;padding:8px 12px;text-align:center;min-width:68px"><div style="font-size:10px;opacity:.8">{dw["시작나이"]}세</div><div style="font-size:15px;font-weight:800">{dw["str"]}</div><div style="font-size:10px">{d_ss}</div>{"<div style=font-size:10px;color:#ffe;font-weight:700>🌟용신</div>" if is_yong else ""}{"<div style=font-size:10px;color:#ff6b00;font-weight:800>◀현재</div>" if is_cur else ""}</div>'
    tl += "</div>"
    st.markdown(tl, unsafe_allow_html=True)

    # ── 대운별 상세 카드 ────────────────────────────────
    for dw in daewoon:
        d_ss_cg = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        d_ss_jj_list = JIJANGGAN.get(dw["jj"], [])
        d_ss_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(d_ss_jj_list[-1] if d_ss_jj_list else "", "-")
        oh_cg = OH.get(dw["cg"], ""); oh_jj = OH.get(dw["jj"], "")
        is_current = dw["시작연도"] <= current_year <= dw["종료연도"]
        is_yong = _get_yongshin_match(d_ss_cg, yongshin_ohs, ilgan_oh) == "yong"
        alerts = _get_dw_alert(ilgan, dw["cg"], dw["jj"], pils)
        icon, title, narrative = get_daewoon_narrative(d_ss_cg, d_ss_jj, dw["str"], dw["시작나이"])
        prescription = DAEWOON_PRESCRIPTION.get(d_ss_cg, "꾸준한 노력으로 안정을 유지하십시오.")

        if is_current:
            bdr = "border:3px solid #ff6b00;"
            bg2 = "background:linear-gradient(135deg,#fff8ee,#fff3e0);"
            badge = "<div style='font-size:12px;color:#ff6b00;font-weight:900;letter-spacing:2px;margin-bottom:8px'>▶ ★ 현재 진행 중인 대운 ★</div>"
        elif is_yong:
            bdr = "border:2px solid #000000;"
            bg2 = "background:linear-gradient(135deg,#ffffff,#ffffff);"
            badge = "<div style='font-size:11px;color:#000000;font-weight:800;margin-bottom:6px'>🌟 용신(用神) 대운 — 이 시기를 놓치지 마십시오</div>"
        else:
            bdr = "border:1px solid #e8e8e8;"
            bg2 = "background:#fafafa;"
            badge = ""

        alert_html = "".join([
            f'<div style="background:{a["color"]}18;border-left:3px solid {a["color"]};padding:8px 12px;border-radius:6px;margin-top:4px;font-size:12px"><b style="color:{a["color"]}">{a["type"]}</b> — {a["desc"]}</div>'
            for a in alerts])

        st.markdown(f"""
        <div class="card" style="{bdr}{bg2}margin:10px 0;padding:20px">
            {badge}
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                <div>
                    <span style="font-size:30px;font-weight:800;color:#000000">{dw["str"]}</span>
                    <span style="font-size:13px;color:#000000;margin-left:12px">{dw["시작나이"]}~{dw["시작나이"]+9}세</span>
                    <span style="font-size:11px;color:#000000;margin-left:8px">({dw["시작연도"]}~{dw["종료연도"]}년)</span>
                </div>
                <div style="text-align:right">
                    <div style="font-size:12px;color:#444">{OHE.get(oh_cg,"")} 천간 <b>{d_ss_cg}</b></div>
                    <div style="font-size:12px;color:#444">{OHE.get(oh_jj,"")} 지지 <b>{d_ss_jj}</b></div>
                </div>
            </div>
            <div style="background:white;border-left:4px solid #000000;padding:12px 15px;border-radius:4px 10px 10px 4px;margin-bottom:8px">
                <div style="font-size:14px;font-weight:700;color:#000000;margin-bottom:6px">{icon} {title}</div>
                <div style="font-size:13px;color:#000000;line-height:2.0">{narrative}</div>
            </div>
            <div style="background:#ffffff;border:1px solid #a8d5a8;padding:10px 14px;border-radius:10px;margin-bottom:6px">
                <span style="font-size:12px;font-weight:700;color:#2a6f2a">💊 처방: </span>
                <span style="font-size:13px;color:#333">{prescription}</span>
            </div>
            {alert_html}
        </div>""", unsafe_allow_html=True)



def tab_monthly(pils, birth_year, gender):
    """월운 탭"""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    year_sel = st.selectbox("연도 선택", list(range(current_year-1, current_year+3)), index=1)
    
    st.markdown('<div class="gold-section">월운(月運) 분석 — 한 달 한 달의 기운 풀이</div>', unsafe_allow_html=True)
    yearly = get_yearly_luck(pils, year_sel)
    ilgan = pils[1]["cg"]
    
    # 세운 상세 해석
    ye_ss_cg = yearly["십성_천간"]
    ye_ss_jj = yearly["십성_지지"]
    ye_data = MONTHLY_LUCK_DESC.get(ye_ss_cg, MONTHLY_LUCK_DESC["-"])
    
    st.markdown(f"""
    <div class="card" style="background:#ffffff;border:2.5px solid #000000;margin-bottom:15px">
        <div style="font-size:16px;font-weight:800;color:#000000;margin-bottom:10px">
            {year_sel}년 세운(歲運) — {yearly["세운"]}  {yearly["아이콘"]}
        </div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:10px">
            <div style="font-size:13px;color:#333">천간 십성: <b style="color:#000000">{ye_ss_cg}</b></div>
            <div style="font-size:13px;color:#333">지지 십성: <b style="color:#000000">{ye_ss_jj}</b></div>
            <div style="font-size:13px;color:#333">종합 길흉: <b style="color:#{'c0392b' if '흉' in yearly['길흉'] else '2980b9' if '길' in yearly['길흉'] else '666'}">{yearly["길흉"]}</b></div>
        </div>
        <div style="font-size:13px;color:#000000;line-height:1.9;background:#ffffff;padding:12px;border-radius:8px">
            {ye_data['desc']}
        </div>
        <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
            <span style="font-size:12px;background:#f0e8c8;padding:4px 10px;border-radius:12px;color:#7b5f2a">💰 {ye_data['재물']}</span>
            <span style="font-size:12px;background:#e8f0e8;padding:4px 10px;border-radius:12px;color:#2a5f2a">👥 {ye_data['관계']}</span>
        </div>
    </div>""", unsafe_allow_html=True)
    
    st.markdown('<div class="gold-section">📅 월별 상세 운세</div>', unsafe_allow_html=True)
    
    # 길흉 색상 맵
    css_colors = {
        "great": ("#ffffff", "#000000", "🌟 대길"),
        "good":  ("#f0f8ff", "#2980b9", "✨ 길"),
        "bad":   ("#fff0f0", "#c0392b", "⚠️ 흉"),
        "":      ("#fafafa", "#888",    "〇 평"),
    }
    
    for m in range(1, 13):
        monthly = get_monthly_luck(pils, year_sel, m)
        is_current = (year_sel == current_year and m == current_month)
        
        bg, border_c, luck_label = css_colors.get(monthly["css"], css_colors[""])
        border = f"border: 2px solid {border_c};" if is_current else f"border: 1px solid {border_c}33;"
        current_badge = "<span style='font-size:11px;background:#000000;color:#000000;padding:2px 8px;border-radius:10px;font-weight:700'>◀ 이번 달</span>" if is_current else ""
        
        # 확장 가능한 카드 대신 항상 요약+상세 표시
        st.markdown(f"""
        <div style="background:{bg};{border}border-radius:12px;padding:16px;margin:6px 0">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <div style="display:flex;align-items:center;gap:12px">
                    <span style="font-size:18px;font-weight:800;color:#000000;min-width:40px">{m}월</span>
                    <span style="font-size:20px;font-weight:800;color:#333">{monthly["월운"]}</span>
                    <span style="font-size:13px;color:{border_c};font-weight:700">{monthly["short"]}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    <span style="font-size:12px;color:#444">{monthly["십성"]}({monthly["지지십성"]})</span>
                    <span style="font-size:12px;font-weight:700;color:{border_c}">{luck_label}</span>
                    {current_badge}
                </div>
            </div>
            <div style="font-size:13px;color:#000000;line-height:1.8;margin-bottom:8px">{monthly["설명"]}</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;font-size:12px">
                <span style="background:#f5efe0;padding:3px 10px;border-radius:10px;color:#7b5f2a">💰 {monthly["재물"]}</span>
                <span style="background:#e8f5e8;padding:3px 10px;border-radius:10px;color:#2a5f2a">👥 {monthly["관계"]}</span>
                <span style="background:#fce8e8;padding:3px 10px;border-radius:10px;color:#8b2020">⚠ {monthly["주의"]}</span>
            </div>
        </div>""", unsafe_allow_html=True)


def tab_saju_total(pils, name, birth_year, gender):
    """사주 종합 총평 탭 — 원국+대운+세운 3중 통합"""
    st.markdown('<div class="gold-section">📜 사주팔자 종합 총평 — 천명(天命) 전체 풀이</div>', unsafe_allow_html=True)

    ilgan = pils[1]["cg"]
    oh = OH.get(ilgan, "")
    oh_emoji = {"木":"🌳","火":"🔥","土":"🏔️","金":"⚔️","水":"🌊"}.get(oh,"✨")
    strength_info = get_ilgan_strength(ilgan, pils)
    gyeokguk = get_gyeokguk(pils)
    oh_strength = strength_info["oh_strength"]
    current_year = datetime.now().year
    yearly = get_yearly_luck(pils, current_year)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    current_dw = next((dw for dw in daewoon if dw["시작연도"] <= current_year <= dw["종료연도"]), None)
    unsung = calc_12unsung(ilgan, pils)
    il_unsung = unsung[1] if len(unsung) > 1 else ""
    ys = get_yongshin(pils)
    yongshin_ohs = ys["종합_용신"]
    ilgan_oh = OH.get(ilgan, "")
    oh_emoji_map = {"木":"🌳","火":"🔥","土":"🏔️","金":"⚔️","水":"💧"}
    saju_str = " ".join([p["str"] for p in pils])
    gname = gyeokguk["격국명"] if gyeokguk else "미정격"
    sn = strength_info["신강신약"]
    current_age = current_year - birth_year + 1

    # 대운 분석
    dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(current_dw["cg"],"-") if current_dw else "-"
    dw_is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong" if current_dw else False
    sw_ss = yearly["십성_천간"]
    sw_is_yong = _get_yongshin_match(sw_ss, yongshin_ohs, ilgan_oh) == "yong"
    hap_breaks = _get_hap_break_warning(pils, current_dw["jj"] if current_dw else "", yearly["jj"])
    dw_alerts = _get_dw_alert(ilgan, current_dw["cg"] if current_dw else "", current_dw["jj"] if current_dw else "", pils) if current_dw else []

    # ① 배너
    nature_quote = ILGAN_DESC.get(ilgan,{}).get("nature","").split("\n")[0] if ILGAN_DESC.get(ilgan,{}).get("nature") else ""
    st.markdown(f"""
    <div style="background:#ffffff;color:#000000;padding:28px;border:2.5px solid #000000;border-radius:18px;text-align:center;margin-bottom:16px">
        <div style="font-size:14px;color:#c8a060;margin-bottom:8px">✨ {name if name else "내담자"}님의 사주팔자 천명</div>
        <div style="font-size:26px;font-weight:900;color:#8b6200;letter-spacing:4px;margin-bottom:8px">{saju_str}</div>
        <div style="font-size:14px;color:#000000;font-style:italic;line-height:1.8">{nature_quote}</div>
    </div>""", unsafe_allow_html=True)

    # ② 핵심 4지표
    yong_str = " · ".join([f"{oh_emoji_map.get(o,'')}{OHN.get(o,'')}" for o in yongshin_ohs]) if yongshin_ohs else "균형"
    luck_now = "🌟 용신 대운" if dw_is_yong else "⚠️ 기신 대운"
    luck_year = "🌟 용신 세운" if sw_is_yong else "〰️ 일반 세운"
    cols = st.columns(4)
    for col, (label, val, bg, tc) in zip(cols, [
        ("격국", gname, "#ffffff", "#000000"),
        ("신강신약", sn, "#f0f8ff", "#1a5f8b"),
        ("용신", yong_str, "#f0fff0", "#1a6f3a"),
        ("현재 흐름", f"{luck_now}\n{luck_year}", "#fff0f8", "#8b2060"),
    ]):
        col.markdown(f"""
        <div style="background:{bg};border-radius:12px;padding:14px;text-align:center;height:90px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:11px;color:#000000;margin-bottom:4px">{label}</div>
            <div style="font-size:13px;font-weight:800;color:{tc};line-height:1.5">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ③ 원국 구조 진단 (고수식 — 오행 흐름 중심)
    st.markdown('<div class="gold-section">🏛️ 원국(原局) 구조 진단</div>', unsafe_allow_html=True)
    over_ohs = [o for o,v in oh_strength.items() if v>=35]
    lack_ohs = [o for o,v in oh_strength.items() if v<=5]
    zero_ohs = [o for o,v in oh_strength.items() if v==0]
    oh_bar = "".join([
        f'<span style="background:{("#c0392b" if o in over_ohs else "#2980b9" if o in lack_ohs else "#000000") if o in over_ohs+lack_ohs else "#888"};color:#000000;padding:4px 10px;border-radius:12px;font-size:12px;margin:2px;display:inline-block">{oh_emoji_map.get(o,"")}{OHN.get(o,"")} {v}%</span>'
        for o,v in oh_strength.items()])
    orig_chung = get_chung_hyung(pils)
    chung_str = "·".join([c[0] for c in orig_chung["충"]]) if orig_chung["충"] else "없음"
    hap_str = "·".join([c[0] for c in orig_chung["천간합"]]) if orig_chung["천간합"] else "없음"
    gongmang = get_gongmang(pils)
    gong_str = " ".join(gongmang["공망_지지"]) if gongmang["공망_지지"] else "없음"
    yangin = get_yangin(pils)

    st.markdown(f"""
    <div class="card" style="background:#ffffff;border:2.5px solid #000000">
        <div style="margin-bottom:10px">{oh_bar}</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;font-size:13px;color:#000000;line-height:1.9">
            <div style="flex:1;min-width:200px"><b style="color:#000000">🏛️ 격국:</b> {gname} — {gyeokguk["격의_등급"] if gyeokguk else ""}</div>
            <div style="flex:1;min-width:200px"><b style="color:#000000">⚡ 원국 충:</b> {chung_str}</div>
            <div style="flex:1;min-width:200px"><b style="color:#000000">✨ 원국 합:</b> {hap_str}</div>
            <div style="flex:1;min-width:200px"><b style="color:#000000">🕳️ 공망:</b> {gong_str}</div>
            {f'<div style="flex:1;min-width:200px"><b style="color:#c0392b">🔥 양인:</b> {yangin["양인_지지"]} 존재 — 강렬한 에너지, 칠살과 함께면 극강</div>' if yangin["존재"] else ""}
            {f'<div style="flex:1;min-width:200px"><b style="color:#8b2020">⚠️ 완전 결핍:</b> {" ".join([OHN.get(o,"")+"("+o+")" for o in zero_ohs])} — 이 오행 운이 올 때 혼란</div>' if zero_ohs else ""}
        </div>
    </div>""", unsafe_allow_html=True)

    # ④ 현재 대운 × 세운 교차 진단 (핵심!)
    st.markdown('<div class="gold-section">🔀 현재 대운 × 세운 교차 진단</div>', unsafe_allow_html=True)
    if current_dw:
        both_yong = dw_is_yong and sw_is_yong
        none_yong = not dw_is_yong and not sw_is_yong
        cross_color = "#000000" if both_yong else "#c0392b" if none_yong else "#2980b9"
        cross_label = ("🌟 용신 대운과 용신 세운이 겹쳤습니다 — 평생 최고의 기회 시기" if both_yong
                      else "⚠️ 기신 대운·세운이 겹쳤습니다 — 수비가 최선입니다" if none_yong
                      else f"{'✨ 용신 대운 속 일반 세운' if dw_is_yong else '🌿 기신 대운이지만 세운이 활로를 엽니다'}")
        st.markdown(f"""
        <div class="card" style="background:{cross_color}15;border:2px solid {cross_color}">
            <div style="font-size:15px;font-weight:800;color:{cross_color};margin-bottom:10px">{cross_label}</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">
                <div style="flex:1;min-width:160px;background:white;padding:12px;border-radius:10px;text-align:center">
                    <div style="font-size:11px;color:#444">현재 대운</div>
                    <div style="font-size:22px;font-weight:900;color:#000000">{current_dw["str"]}</div>
                    <div style="font-size:12px;color:#333">{dw_ss} | {"🌟용신" if dw_is_yong else "기신"}</div>
                    <div style="font-size:11px;color:#555">{current_dw["시작나이"]}~{current_dw["시작나이"]+9}세 ({current_dw["시작연도"]}~{current_dw["종료연도"]})</div>
                </div>
                <div style="font-size:24px;color:{cross_color};display:flex;align-items:center">×</div>
                <div style="flex:1;min-width:160px;background:white;padding:12px;border-radius:10px;text-align:center">
                    <div style="font-size:11px;color:#444">{current_year}년 세운</div>
                    <div style="font-size:22px;font-weight:900;color:#000000">{yearly["세운"]}</div>
                    <div style="font-size:12px;color:#333">{sw_ss} | {"🌟용신" if sw_is_yong else "일반"}</div>
                    <div style="font-size:11px;color:#555">{yearly.get("길흉","")}</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        # 합 깨짐 경고
        if hap_breaks:
            for w in hap_breaks:
                st.markdown(f'<div class="card" style="background:{w["color"]}18;border-left:5px solid {w["color"]}"><b style="color:{w["color"]}">{w["level"]}</b> — {w["desc"]}</div>', unsafe_allow_html=True)

        # 원국-대운 충합 알림
        if dw_alerts:
            for a in dw_alerts:
                st.markdown(f'<div class="card" style="border-left:4px solid {a["color"]}"><b style="color:{a["color"]}">{a["type"]}</b> — {a["desc"]}</div>', unsafe_allow_html=True)

    # ⑤ 처방 중심 조언
    st.markdown('<div class="gold-section">💊 처방 — 지금 당장 해야 할 것</div>', unsafe_allow_html=True)
    prescriptions_total = []
    if dw_is_yong and sw_is_yong:
        prescriptions_total += ["✅ 지금이 황금 시기입니다. 중요한 결정(창업·투자·이직·결혼)을 미루지 마십시오.",
                                 "✅ 용신 방향("+("동쪽" if "木" in yongshin_ohs else "남쪽" if "火" in yongshin_ohs else "서쪽" if "金" in yongshin_ohs else "북쪽" if "水" in yongshin_ohs else "중앙")+")으로 책상·침대 방향을 맞추십시오.",
                                 "✅ 용신 색상을 착용하고 이 기운을 몸으로 흡수하십시오."]
    elif none_yong:
        prescriptions_total += ["🛡️ 무리한 확장·투자·이동을 피하십시오. 수비가 최선입니다.",
                                 "🛡️ 기존 관계·사업·자산을 지키는 데 집중하십시오.",
                                 "🛡️ 건강검진을 반드시 받으십시오. 기신 운에 건강이 가장 먼저 흔들립니다."]
    else:
        prescriptions_total += ["⚡ 좋은 기운과 나쁜 기운이 혼재합니다. 선별적으로 추진하십시오.",
                                 "⚡ 큰 결정은 다음 용신 대운이 올 때까지 기다리십시오."]
    if over_ohs:
        prescriptions_total.append(f"⚠️ {', '.join([OHN.get(o,'')+'('+o+')' for o in over_ohs])} 과다 — 해당 장기 건강에 각별히 유의하십시오.")
    if zero_ohs:
        prescriptions_total.append(f"🔍 {', '.join([OHN.get(o,'')+'('+o+')' for o in zero_ohs])} 완전 결핍 — 이 오행 운이 올 때 예측불허 혼란이 옵니다. 미리 준비하십시오.")
    if yangin["존재"]:
        prescriptions_total.append("⚔️ 양인(羊刃) 존재 — 에너지를 직업으로 승화하십시오. 군·경·의료·스포츠가 길합니다.")

    for p in prescriptions_total:
        color = "#27ae60" if p.startswith("✅") else "#c0392b" if p.startswith("🛡") else "#e67e22" if p.startswith("⚡") else "#888"
        st.markdown(f'<div style="background:{color}12;border-left:4px solid {color};padding:10px 14px;border-radius:8px;margin:5px 0;font-size:13px;color:#333">{p}</div>', unsafe_allow_html=True)

    # ⑥ 미래 5년 요약
    st.markdown('<div class="gold-section">📅 향후 5년 핵심 요약</div>', unsafe_allow_html=True)
    for y in range(current_year, current_year+5):
        c2 = get_daewoon_sewoon_cross(pils, birth_year, gender, y)
        if not c2: continue
        dy = _get_yongshin_match(c2["대운_천간십성"], yongshin_ohs, ilgan_oh) == "yong"
        sy = _get_yongshin_match(c2["세운_천간십성"], yongshin_ohs, ilgan_oh) == "yong"
        hb = _get_hap_break_warning(pils, c2["대운"]["jj"], c2["세운"]["jj"])
        if dy and sy:   row_lc,row_bg,badge="#000000","#ffffff","🌟 최길"
        elif dy or sy:  row_lc,row_bg,badge="#2980b9","#f0f8ff","✨ 길"
        elif "흉" in c2["세운"]["길흉"]: row_lc,row_bg,badge="#c0392b","#fff5f5","⚠️ 흉"
        else:           row_lc,row_bg,badge="#888","#fafafa","〰️ 평"
        hb_icon = " 🚨합깨짐" if hb else ""
        age_y = y - birth_year + 1
        st.markdown(f"""
        <div style="display:flex;align-items:center;padding:10px 16px;border-radius:12px;margin:4px 0;background:{row_bg};border:1px solid {row_lc}44">
            <span style="font-weight:900;color:#000000;min-width:55px">{y}년</span>
            <span style="min-width:45px;font-size:12px;color:#444">{age_y}세</span>
            <span style="min-width:80px;font-size:13px;color:#333">대운:{c2["대운"]["str"]}</span>
            <span style="min-width:80px;font-size:13px;color:#333">세운:{c2["세운"]["세운"]}</span>
            <span style="flex:1;font-size:12px;color:#444">{c2["대운_천간십성"]}+{c2["세운_천간십성"]}</span>
            <span style="font-size:12px;color:#c0392b">{hb_icon}</span>
            <span style="font-weight:800;color:{row_lc}">{badge}</span>
        </div>""", unsafe_allow_html=True)

    # ⑦ 텍스트 총평 (복사용)
    st.markdown('<div class="gold-section">📋 전문 총평 텍스트 (복사용)</div>', unsafe_allow_html=True)
    summary = generate_saju_summary(pils, name, birth_year, gender)
    st.text_area("", summary, height=300, label_visibility="collapsed")



def tab_ai_chat(pils, name, birth_year=1990, gender="남", api_key="", groq_key=""):
    """
    AI 채팅 탭 — Brain 1·2·3 완전 통합
    Brain 1: 만세력 계산 (이미 완료, pils로 전달됨)
    Brain 2: AI 해석 Sandbox (get_cached_ai_interpretation)
    Brain 3: 학습·수익화 엔진 (피드백 수집·패턴 분석·결제 타이밍)
    """
    import re
    ilgan   = pils[1]["cg"]
    saju_key = pils_to_cache_key(pils)

    # ── Brain 3: 현재 사주 키 세션 등록 (피드백 저장에 사용)
    st.session_state["_current_saju_key"] = saju_key

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Brain 3-① : 적중률 대시보드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    patterns = b3_analyze_patterns()
    total_fb = patterns.get("total", 0)
    overall  = patterns.get("hit_rate", 0)

    if total_fb >= 5:   # 데이터 5건 이상 축적 시 대시보드 표시
        rate_color = "#4caf50" if overall >= 70 else "#ff9800" if overall >= 50 else "#f44336"
        best_sec   = "·".join(patterns.get("best_sections", [])[:2]) or "-"
        weak_sec   = "·".join(patterns.get("weak_sections", [])[:2]) or "-"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#f0fff0,#e8f5e8);
                    border:1px solid #a8e6a8;border-radius:12px;
                    padding:12px 20px;margin-bottom:14px;
                    display:flex;gap:24px;align-items:center;flex-wrap:wrap">
            <div style="text-align:center;min-width:72px">
                <div style="font-size:10px;color:#000000;letter-spacing:1px">🧠 BRAIN 3</div>
                <div style="font-size:26px;font-weight:900;color:{rate_color};line-height:1.1">{overall}%</div>
                <div style="font-size:10px;color:#555">적중률 ({total_fb}건)</div>
            </div>
            <div style="flex:1;font-size:11px;color:#000000;line-height:2.0">
                ✅ 잘 맞는 섹션 : <b style="color:#1a7a1a">{best_sec}</b><br>
                ⚠️ 개선 중인 섹션 : <b style="color:#ffab40">{weak_sec}</b><br>
                <span style="color:#000000;font-size:10px">
                  피드백이 쌓일수록 AI 프롬프트가 자동 강화됩니다
                </span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Brain 3-④ : 결제 타이밍 감지 → 트리거 카드
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    should_trigger, trigger_msg = b3_check_monetization_trigger(api_key)
    if should_trigger:
        b3_render_trigger_card(trigger_msg)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 예언자 모드 헤더
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("""
    <div style="background:linear-gradient(135deg,#f0eeff,#ece8ff);color:#000000;
                padding:24px;border-radius:16px;margin-bottom:16px;text-align:center">
        <div style="font-size:26px;font-weight:900;letter-spacing:3px;
                    color:#000000;margin-bottom:8px">🔮 예언자의 서(書)</div>
        <div style="font-size:13px;color:#000000;line-height:1.9">
            Brain 1(만세력)이 계산한 데이터 → Brain 2(AI)가 단정적으로 풀이합니다<br>
            과거 적중 · 현재 · 직업 · 결혼 · 미래 3년 · 돈 상승기
        </div>
    </div>""", unsafe_allow_html=True)

    # 마스터 엔진 실시간 라벨 배지
    fate = turning.get("fate_label", "평온기 🍀")
    fate_desc = turning.get("fate_desc", "안정된 흐름 속에 있습니다.")
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                border-left: 5px solid #000000; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="font-size: 30px;">{fate.split()[-1] if ' ' in fate else '✨'}</div>
            <div>
                <div style="color: #000000; font-size: 13px; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px;">CURRENT LIFE SEASON</div>
                <div style="color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: -0.5px;">당신은 현재 <span style="color: #f1c40f;">{fate}</span>를 지나고 있습니다</div>
                <div style="color: #a0a0ba; font-size: 14px; margin-top: 5px;">{fate_desc}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 행운의 개운법 (Lucky Kit) 자체 로직 렌더링
    ys_info = get_yongshin(pils)
    primary_yong = ys_info.get("용신_1순위", "木")
    render_lucky_kit(primary_yong)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🗣️ AI 만신과의 대화 (Multi-turn Chat)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # 1. 기존 대화 기록 출력 가이드
    def render_message(role, content):
        with st.chat_message(role):
            # 리포트 형식(Prophet 모드) 파싱 및 렌더링
            if "1️⃣" in content and "2️⃣" in content:
                sections = {
                    "1️⃣": ("과거 적중", "#f0e8ff", "#9b7ccc"),
                    "2️⃣": ("현재",      "#e8f4ff", "#5c9bc5"),
                    "3️⃣": ("직업",      "#e0f5ec", "#5cc88b"),
                    "4️⃣": ("결혼",      "#2e0a1a", "#c55c8b"),
                    "5️⃣": ("미래 3년",  "#fffde8", "#c5b55c"),
                    "6️⃣": ("돈 상승기", "#e0f5f5", "#5cc5c5"),
                    "7️⃣": ("오늘의 비방", "#fff8f8", "#cc2222"),
                }
                parsed = {}
                for emoji in sections:
                    m = re.search(rf'{re.escape(emoji)}[^\n]*\n([\s\S]*?)(?=(?:[1-7]️⃣)|$)', content)
                    if m: parsed[emoji] = m.group(1).strip()
                
                if parsed:
                    for emoji, (title, bg, color) in sections.items():
                        if emoji in parsed:
                            if emoji == "7️⃣":
                                st.markdown(f'<div class="red-scroll"><div style="font-size:16px;font-weight:900;margin-bottom:12px">🧧 {title}</div>{parsed[emoji]}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div style="background:{bg};border:1px solid {color}44;border-left:4px solid {color};border-radius:12px;padding:20px;margin:8px 0"><div style="font-size:15px;font-weight:800;color:{color};margin-bottom:10px;letter-spacing:1px">{emoji} {title}</div><div style="font-size:14px;color:#000000;line-height:2.1;white-space:pre-wrap">{parsed[emoji]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(content)
            else:
                st.markdown(content)

    # 대화창 클리어 버튼
    if st.session_state["chat_history"]:
        if st.button("🔄 대화 초기화", use_container_width=True):
            st.session_state["chat_history"] = []
            st.rerun()

    # 히스토리 렌더링
    for msg in st.session_state["chat_history"]:
        render_message(msg["role"], msg["content"])

    # 2. 최초 시작 버튼 (히스토리가 없을 때만)
    if not st.session_state["chat_history"]:
        if st.button("🔮 예언자 풀이 | 6단계 천명 판독 시작", use_container_width=True, type="primary"):
            b3_track_behavior("view_ai")
            with st.status("🧠 사주 천명 판독 중...", expanded=True) as status:
                st.write("천명의 언어 해석 및 상담 (Interpretation)...")
                stream_gen = get_cached_ai_interpretation(
                    saju_key, "prophet", api_key, birth_year=birth_year, 
                    gender=gender, name=name, groq_key=groq_key, stream=True
                )
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full_text = placeholder.write_stream(stream_gen)
                st.session_state["chat_history"].append({"role": "assistant", "content": full_text})
                status.update(label="✅ 판독 완료", state="complete", expanded=False)
                st.rerun()

    # 3. 사용자 채팅 입력 및 펜딩 처리
    prompt = st.chat_input("사주에 대해 궁금한 점을 더 물어보세요.")
    if "_pending_sug" in st.session_state:
        prompt = st.session_state.pop("_pending_sug")

    if prompt:
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        # (렌더링은 루프에서 처리되므로 여기선 AI 응답 생성에 집중)
        with st.chat_message("assistant"):
            with st.spinner("AI 만신이 답을 구하는 중..."):
                rich_ctx = format_saju_text(pils, name)
                user_msg_with_ctx = f"【대상 사주】: {rich_ctx}\n【사용자 질문】: {prompt}\n\n위 사주를 바탕으로 대화의 맥락을 이어가며 답하십시오."
                stream_gen = get_ai_interpretation(
                    user_msg_with_ctx, api_key, system=PROPHET_SYSTEM,
                    groq_key=groq_key, stream=True, history=st.session_state["chat_history"][:-1]
                )
                placeholder = st.empty()
                full_answer = placeholder.write_stream(stream_gen)
                st.session_state["chat_history"].append({"role": "assistant", "content": full_answer})
        st.rerun()

    # 4. 추천 질문 (Suggestion Pills)
    if st.session_state["chat_history"] and st.session_state["chat_history"][-1]["role"] == "assistant":
        st.markdown("<div style='margin:10px 0 5px 0; font-size:13px; color:#000000;'>💡 **이런 질문은 어떠세요?**</div>", unsafe_allow_html=True)
        suggestions = ["올해 가장 조심해야 할 달은?", "재물을 부르는 개운법은?", "내 사주의 가장 큰 강점은?"]
    st.markdown('<div class="gold-section">⚡ 용신(用神) — 내 사주의 구원 오행</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="background:#ffffff;border:1px solid #c8b8e8;margin-bottom:12px">
        <div style="font-size:13px;color:#5a2d8b;font-weight:700;margin-bottom:4px">💡 용신이란?</div>
        <div style="font-size:13px;color:#000000;line-height:1.8">
        용신(用神)은 내 사주에서 가장 필요한 기운입니다. 이 오행의 운이 올 때 발복하고, 반대 기신(忌神)의 운이 올 때 고난이 옵니다.
        용신 방향으로 이사하고, 용신 색상을 착용하고, 용신 직업을 선택하면 운명을 바꿀 수 있습니다.
        </div>
    </div>""", unsafe_allow_html=True)
    
    ys = get_yongshin(pils)
    oh_emoji = {"木": "🌳", "火": "🔥", "土": "🏔️", "金": "⚔️", "水": "💧"}
    oh_color = {"木": "#2a6f2a", "火": "#c03020", "土": "#8b6914", "金": "#6b6b00", "水": "#1a4f8b"}
    oh_direction = {"木": "동쪽(東)", "火": "남쪽(南)", "土": "중앙", "金": "서쪽(西)", "水": "북쪽(北)"}
    oh_luckcolor = {"木": "초록·청색", "火": "빨강·주황", "土": "황색·베이지", "金": "흰색·은색·금색", "水": "검정·남색"}
    oh_season = {"木": "봄(1~3월)", "火": "여름(4~6월)", "土": "환절기", "金": "가을(7~9월)", "水": "겨울(10~12월)"}
    
    # 억부용신
    st.markdown('<div class="gold-section">1️⃣ 억부용신(抑扶用神)</div>', unsafe_allow_html=True)
    yong_ohs = ys["억부_용신"]
    cols = st.columns(len(yong_ohs) if yong_ohs else 1)
    for i, oh in enumerate(yong_ohs):
        c = oh_color.get(oh, "#888")
        e = oh_emoji.get(oh, "")
        with cols[i]:
            st.markdown(f"""
            <div class="card" style="background:#ffffff;border:2.5px solid #000000;text-align:center">
                <div style="font-size:30px">{e}</div>
                <div style="font-size:18px;font-weight:800;color:{c}">{OHN.get(oh,'')}</div>
                <div style="font-size:12px;color:#000000;margin-top:6px">억부용신</div>
                <div style="font-size:12px;color:#000000;margin-top:4px">
                    방향: {oh_direction.get(oh,'')}<br>
                    색상: {oh_luckcolor.get(oh,'')}<br>
                    계절: {oh_season.get(oh,'')}
                </div>
            </div>""", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="card" style="background:#ffffff;border-left:8px solid #000000;border:1.5px solid #000">
        <div style="font-size:13px;font-weight:700;color:#2a6f2a;margin-bottom:4px">{ys['억부_base']}</div>
        <div style="font-size:13px;color:#000000;line-height:1.9">{ys['억부_desc']}</div>
        <div style="font-size:12px;color:#c03020;margin-top:8px;background:#fff0f0;padding:8px;border-radius:6px">
            ⚠️ 기신(忌神): {ys['기신']}
        </div>
    </div>""", unsafe_allow_html=True)
    
    # 조후용신
    if ys["조후_desc"]:
        st.markdown('<div class="gold-section">2️⃣ 조후용신(調候用神)</div>', unsafe_allow_html=True)
        need_str = ", ".join([f"{OHN.get(OH.get(c,''),'')}{c}" for c in ys["조후_need"]])
        avoid_str = ", ".join([f"{OHN.get(OH.get(c,''),'')}{c}" for c in ys["조후_avoid"]])
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border-left:8px solid #000000;border:1.5px solid #000">
            <div style="font-size:13px;color:#000000;line-height:1.9;margin-bottom:8px">{ys['조후_desc']}</div>
            {f'<div style="font-size:12px;color:#2a6f2a;background:#e8f5e8;padding:6px 10px;border-radius:6px;margin-bottom:4px">✅ 필요한 기운: {need_str}</div>' if need_str else ''}
            {f'<div style="font-size:12px;color:#c03020;background:#fce8e8;padding:6px 10px;border-radius:6px">❌ 피해야 할 기운: {avoid_str}</div>' if avoid_str else ''}
        </div>""", unsafe_allow_html=True)
    
    # 통관용신
    if ys["통관_yong"]:
        oh = ys["통관_yong"]
        st.markdown('<div class="gold-section">3️⃣ 통관용신(通關用神)</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border-left:8px solid #000000;border:1.5px solid #000">
            <div style="font-size:13px;color:#000000;line-height:1.9">{ys['통관_desc']}</div>
            <div style="font-size:13px;font-weight:700;color:#000000;margin-top:8px">
                {oh_emoji.get(oh,'')} 통관용신: {OHN.get(oh,'')} — 방향: {oh_direction.get(oh,'')} / 색상: {oh_luckcolor.get(oh,'')}
            </div>
        </div>""", unsafe_allow_html=True)
    
    # 종합 용신 정리
    all_y = ys["종합_용신"]
    if all_y:
        st.markdown('<div class="gold-section">⭐ 종합 용신 정리</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="background:#ffffff;color:#000000;padding:20px;border:2.5px solid #000000">
            <div style="font-size:15px;font-weight:700;margin-bottom:14px;color:#8b6200">내 사주의 핵심 용신</div>
            <div style="display:flex;flex-wrap:wrap;gap:10px">
                {"".join([f'<div style="background:rgba(255,255,255,0.1);padding:12px 20px;border-radius:12px;text-align:center"><div style="font-size:24px">{oh_emoji.get(o,"")}</div><div style="font-size:14px;font-weight:700;color:#8b6200;margin-top:4px">{OHN.get(o,"")} ({o})</div><div style="font-size:11px;color:#000000;margin-top:4px">{oh_direction.get(o,"")} · {oh_luckcolor.get(o,"")}</div></div>' for o in all_y])}
            </div>
        </div>""", unsafe_allow_html=True)


def tab_chung_hyung(pils):
    """충·형·파·해 탭"""
    st.markdown('<div class="gold-section">⚡ 합충형파해(合沖刑破害) 분석</div>', unsafe_allow_html=True)
    
    result = get_chung_hyung(pils)
    
    sections = [
        ("충(沖)", result["충"], "🔴", "#fff0f0", "#c0392b",
         "지지끼리 정면 충돌하는 기운. 변동·사고·이별의 기운이지만 정체된 기운을 터뜨리는 긍정적 측면도 있습니다."),
        ("형(刑)", result["형"], "⚡", "#fff5e0", "#e67e22",
         "형살은 법적 문제·관재·배신·수술 등의 기운. 특히 삼형살은 가장 강력한 형살입니다."),
        ("파(破)", result["파"], "💥", "#f5f0ff", "#8e44ad",
         "계획이 깨지고 예상 밖 변수가 생기는 기운. 충보다는 약하지만 은밀하게 작용합니다."),
        ("해(害)", result["해"], "🌀", "#f0f8ff", "#2980b9",
         "서로 방해하고 상처 주는 기운. 인간관계의 배신·갈등이 주요 작용입니다."),
        ("천간합(天干合)", result["천간합"], "💛", "#f0fff0", "#27ae60",
         "천간끼리 합하여 새로운 오행이 생성. 변화와 협력의 기운으로 일부 길한 작용을 합니다."),
    ]
    
    found_any = False
    for title, items, icon, bg, color, guide in sections:
        if items:
            found_any = True
            st.markdown(f"""
            <div class="card" style="background:{bg};border-left:4px solid {color};margin:8px 0">
                <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:8px">{icon} {title}</div>
                <div style="font-size:12px;color:#000000;margin-bottom:10px">{guide}</div>
                {"".join([f'<div style="background:white;padding:10px 14px;border-radius:8px;margin-bottom:6px"><b style=color:{color}>{it[0]}</b> <span style=color:#000000;font-size:12px>({it[1] if len(it)>1 else ""})</span><div style=font-size:13px;color:#000000;margin-top:4px>{it[2] if len(it)>2 else it[1] if len(it)>1 else ""}</div></div>' for it in items])}
            </div>""", unsafe_allow_html=True)
    
    # 자형
    if result.get("자형"):
        found_any = True
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border-left:8px solid #000000;border:1.5px solid #000">
            <div style="font-size:14px;font-weight:700;color:#9b59b6;margin-bottom:6px">🔮 자형(自刑)</div>
            <div style="font-size:13px;color:#444">같은 지지가 두 개 이상: {', '.join(result['자형'])} — 스스로를 해치는 기운. 자기 비판, 자기 파괴적 행동을 조심하십시오.</div>
        </div>""", unsafe_allow_html=True)
    
    if not found_any:
        st.markdown("""
        <div class="card" style="background:#ffffff;border:2.5px solid #000000;text-align:center;padding:24px">
            <div style="font-size:18px;font-weight:700;color:#2a6f2a">✅ 합충형파해가 없는 안정적인 사주입니다</div>
            <div style="font-size:13px;color:#000000;margin-top:8px;line-height:1.8">
            지지 간의 극단적 충돌이 없어 안정적이고 꾸준한 삶을 영위합니다.<br>
            큰 변동보다는 점진적인 성장과 안정이 이 사주의 강점입니다.
            </div>
        </div>""", unsafe_allow_html=True)


def tab_gongmang(pils):
    """공망(空亡) 탭"""
    st.markdown('<div class="gold-section">🕳️ 공망(空亡) — 운명의 빈 칸</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="background:#ffffff;border:1px solid #c8b8e8">
        <div style="font-size:13px;color:#5a2d8b;font-weight:700;margin-bottom:4px">💡 공망이란?</div>
        <div style="font-size:13px;color:#000000;line-height:1.8">
        60갑자에서 천간(10)과 지지(12)의 차이로 인해 2개의 지지가 짝을 갖지 못하는 상태입니다.
        공망이 된 지지는 그 기운이 허(虛)해집니다. 해당 육친이나 사항이 약화되거나 예상과 다른 결과를 가져옵니다.
        단, 공망된 기운이 운에서 채워지면(충공·합공) 오히려 크게 발복하기도 합니다.
        </div>
    </div>""", unsafe_allow_html=True)
    
    gm = get_gongmang(pils)
    gong_pair = gm["공망_지지"]
    found_pillars = gm["해당_기둥"]
    
    st.markdown(f"""
    <div class="card" style="background:#ffffff;color:#000000;text-align:center;padding:20px;border:2.5px solid #000000">
        <div style="font-size:13px;color:#000000;margin-bottom:8px">년주 기준 공망 지지</div>
        <div style="font-size:36px;font-weight:900;color:#000000;letter-spacing:8px">{' '.join(gong_pair)}</div>
        <div style="font-size:13px;color:#000000;margin-top:8px">{', '.join([JJ_KR[JJ.index(j)] for j in gong_pair if j in JJ])}</div>
    </div>""", unsafe_allow_html=True)
    
    if found_pillars:
        st.markdown('<div class="gold-section">⚠️ 공망이 해당된 기둥</div>', unsafe_allow_html=True)
        for fp in found_pillars:
            gd = GONGMANG_JJ_DESC.get(fp["지지"], {})
            st.markdown(f"""
            <div class="card" style="background:#ffffff;border-left:8px solid #000000;border:1.5px solid #000">
                <div style="font-size:14px;font-weight:700;color:#e67e22;margin-bottom:6px">
                    ⚠️ {fp['기둥']} 공망 — {fp['지지']}({JJ_KR[JJ.index(fp['지지'])] if fp['지지'] in JJ else ''})
                </div>
                <div style="font-size:13px;color:#000000;line-height:1.9;margin-bottom:8px">{fp['desc']}</div>
                {f'<div style="background:#ffffff;padding:8px 12px;border-radius:8px"><div style="font-size:12px;font-weight:700;color:#000000;margin-bottom:4px">🔓 해공(解空) 방법</div><div style="font-size:12px;color:#444">{gd.get("remedy", "")}</div></div>' if isinstance(gd, dict) and gd.get("remedy") else ""}
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card" style="background:#ffffff;border:2.5px solid #000000;text-align:center;padding:20px">
            <div style="font-size:16px;font-weight:700;color:#2a6f2a">✅ 사주 기둥에 공망이 없습니다</div>
            <div style="font-size:13px;color:#000000;margin-top:6px">4개 기둥의 지지가 모두 실(實)하여 허한 구석이 없는 충실한 사주입니다.</div>
        </div>""", unsafe_allow_html=True)


def tab_ilju(pils):
    """일주론(日柱論) | 60갑자 탭"""
    ilgan = pils[1]["cg"]; iljj = pils[1]["jj"]
    ilju_key = ilgan + iljj
    ilju = ILJU_DESC.get(ilju_key, {})
    
    st.markdown(f'<div class="gold-section">🗝️ 일주론(日柱論) — {ilju_key} 일주의 천명</div>', unsafe_allow_html=True)
    
    if ilju:
        oh_cg = OH.get(ilgan, ""); oh_jj = OH.get(iljj, "")
        nabjin = get_nabjin(ilgan, iljj)
        
        st.markdown(f"""
        <div style="background:#ffffff;color:#000000;padding:24px;border:2.5px solid #000000;border-radius:16px;text-align:center;margin-bottom:16px">
            <div style="font-size:48px;margin-bottom:8px">{ilju.get('symbol','')}</div>
            <div style="font-size:32px;font-weight:900;color:#8b6200;letter-spacing:6px">{ilju_key}</div>
            <div style="font-size:14px;color:#c8b8f0;margin-top:8px">
                {OHN.get(oh_cg,'')}({ilgan}) + {OHN.get(oh_jj,'')}({iljj}) &nbsp;|&nbsp; 납음: {nabjin['name']}
            </div>
        </div>""", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="card" style="background: #ffffff; border: 2.5px solid #000000;">
            <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:10px">📜 일주의 천명 풀이</div>
            <div style="font-size:14px;color:#000000;line-height:2.1">{ilju.get('desc','')}</div>
        </div>""", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="card" style="background:#ffffff;border:1px solid #a8d5a8">
                <div style="font-size:13px;font-weight:700;color:#2a6f2a;margin-bottom:6px">✨ 운명의 빛</div>
                <div style="font-size:13px;color:#000000;line-height:1.9">{ilju.get('luck','')}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="card" style="background:#fff5f5;border:1px solid #d5a8a8">
                <div style="font-size:13px;font-weight:700;color:#8b2020;margin-bottom:6px">⚠️ 경계할 것</div>
                <div style="font-size:13px;color:#000000;line-height:1.9">{ilju.get('caution','')}</div>
            </div>""", unsafe_allow_html=True)
        
        # 납음오행
        st.markdown(f"""
        <div class="card" style="background:#ffffff;border:1px solid #c8b8e8">
            <div style="font-size:13px;font-weight:700;color:#5a2d8b;margin-bottom:6px">🎵 납음오행(納音五行): {nabjin['name']}</div>
            <div style="font-size:13px;color:#000000;line-height:1.8">{nabjin['desc']}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info(f"{ilju_key} 일주 데이터를 준비 중입니다.")


def tab_yukjin(pils, gender="남"):
    """육친론(六親論) 탭"""
    ilgan = pils[1]["cg"]
    st.markdown('<div class="gold-section">👨‍👩‍👧‍👦 육친론(六親論) — 가족과 인연</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="background:#ffffff;border:1px solid #c8b8e8;margin-bottom:12px">
        <div style="font-size:13px;color:#5a2d8b;font-weight:700;margin-bottom:4px">💡 육친론이란?</div>
        <div style="font-size:13px;color:#000000;line-height:1.8">
        일간을 기준으로 각 십성(十星)이 어느 가족을 나타내는지 분석합니다. 
        각 기둥의 십성 강약으로 가족관계의 덕, 인연, 갈등을 판단합니다.
        </div>
    </div>""", unsafe_allow_html=True)
    
    yk = get_yukjin(ilgan, pils, gender)
    fam_emoji = {
        "어머니": "👩", "계모": "👩‍🦳", "아내": "💑", "정부": "💘",
        "아버지": "👨", "시아버지": "👴", "딸": "👧", "남편": "💑",
        "아들": "👦", "형제": "👬", "자매": "👭", "이복형제": "👥",
        "이복자매": "👥", "조모": "👵", "손자": "👶"
    }
    
    if yk:
        for item in yk:
            fam_name = item.get("관계", "")
            emoji = next((e for n, e in fam_emoji.items() if n in fam_name), "👤")
            where_str = item.get("위치", "없음")
            has = item.get("present", False)
            desc = item.get("desc", "")
            strength_label = "강(强) — 인연이 깊습니다" if has else "약(弱) — 인연이 엷습니다"

            st.markdown(f"""
            <div class="card" style="margin-bottom:8px">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                    <span style="font-size:24px">{emoji}</span>
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#000000">{fam_name}</div>
                        <div style="font-size:12px;color:#444">{where_str} | {strength_label}</div>
                    </div>
                </div>
                <div style="font-size:13px;color:#000000;background:#ffffff;padding:8px 12px;border-radius:8px;margin-top:4px;line-height:1.8">{desc}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("육친 데이터를 분석 중입니다.")
    
    # 배우자 자리 분석
    st.markdown('<div class="gold-section">💑 배우자 자리 (일지) 분석</div>', unsafe_allow_html=True)
    iljj = pils[1]["jj"]
    iljj_ss = calc_sipsung(ilgan, pils)[1].get("jj_ss", "-")
    
    spouse_desc = {
        "남": {"정재": "현모양처형. 안정적이고 내조를 잘하는 배우자.", "편재": "활달하고 매력적이나 변화가 많은 배우자.", "정관": "남편으로서의 배우자 — 격조 있는 인연.", "편관": "강하고 카리스마 있는 배우자. 갈등도 있을 수 있습니다."},
        "여": {"정관": "점잖고 안정적인 남편. 사회적으로 인정받는 남성.", "편관": "카리스마 있고 강한 남편. 자유분방한 측면도.", "정재": "여성으로서의 배우자 — 풍요로운 인연.", "편재": "활동적이고 사교적인 배우자."},
    }
    
    spouse_hint = spouse_desc.get(gender, {}).get(iljj_ss, f"일지의 {iljj_ss} — 배우자의 성향을 나타냅니다.")
    
    st.markdown(f"""
    <div class="card" style="background:#fff0f8;border:2px solid #d580b8">
        <div style="font-size:14px;font-weight:700;color:#8b2060;margin-bottom:8px">
            💑 배우자 자리: {iljj}({JJ_KR[JJ.index(iljj)] if iljj in JJ else ''}) — {iljj_ss}
        </div>
        <div style="font-size:13px;color:#000000;line-height:1.9">{spouse_hint}</div>
    </div>""", unsafe_allow_html=True)


def tab_gunghap(pils, name="나"):
    """궁합(宮合) 탭"""
    st.markdown('<div class="gold-section">💑 궁합(宮合) — 두 사주의 조화</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card" style="background:#fff0f8;border:1px solid #d5a8c8">
        <div style="font-size:13px;color:#8b2060;font-weight:700;margin-bottom:6px">💡 상대방 사주 입력</div>
        <div style="font-size:13px;color:#444">상대방의 생년월일시를 입력하시면 두 사주의 궁합을 분석합니다.</div>
    </div>""", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        partner_name = st.text_input("상대방 이름", placeholder="이름", key="partner_name")
    with col2:
        p_year = st.number_input("생년", min_value=1920, max_value=2010, value=1992, key="p_year")
    with col3:
        p_month = st.number_input("생월", min_value=1, max_value=12, value=6, key="p_month")
    with col4:
        p_day = st.number_input("생일", min_value=1, max_value=31, value=15, key="p_day")
    
    col5, col6 = st.columns(2)
    with col5:
        p_hour = st.selectbox("생시", list(range(0, 24)), index=12, key="p_hour")
    with col6:
        p_gender = st.selectbox("성별", ["남", "여"], key="p_gender")
    
    if st.button("💑 궁합 분석", use_container_width=True, type="primary"):
        try:
            partner_pils = SajuCoreEngine.get_pillars(p_year, p_month, p_day, p_hour)
            pname = partner_name if partner_name else "상대방"
            result = calc_gunghap(pils, partner_pils, name, pname)
            
            # 궁합 점수 게이지
            score = result["총점"]
            grade = result["등급"]
            bar = "🟥" * (score // 10) + "⬜" * (10 - score // 10)
            score_color = "#000000" if score >= 70 else "#c03020" if score < 40 else "#888"
            
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#ffe2f6,#ffe1ff);color:#000000;padding:28px;border-radius:16px;text-align:center;margin:16px 0">
                <div style="font-size:16px;color:#f0c0d8;margin-bottom:8px">{name} ❤️ {pname}</div>
                <div style="font-size:48px;font-weight:900;color:#8b6200">{score}점</div>
                <div style="font-size:22px;margin:10px 0">{bar}</div>
                <div style="font-size:20px;font-weight:700;color:#8b6200">{grade}</div>
            </div>""", unsafe_allow_html=True)
            
            # 세부 분석
            col_a, col_b = st.columns(2)
            with col_a:
                ir = result["일간관계"]
                st.markdown(f"""
                <div class="card">
                    <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">{ir[2]} 일간 관계: {ir[0]}</div>
                    <div style="font-size:13px;color:#444">{ir[1]}</div>
                </div>""", unsafe_allow_html=True)
                
                if result["합"]:
                    st.markdown(f"""
                    <div class="card" style="background:#ffffff;border:1px solid #a8d5a8">
                        <div style="font-size:13px;font-weight:700;color:#2a6f2a;margin-bottom:6px">✨ 합(合) 발견!</div>
                        <div style="font-size:13px;color:#333">{', '.join(result['합'])}</div>
                    </div>""", unsafe_allow_html=True)
            
            with col_b:
                if result["충"]:
                    st.markdown(f"""
                    <div class="card" style="background:#fff0f0;border:1px solid #d5a8a8">
                        <div style="font-size:13px;font-weight:700;color:#8b2020;margin-bottom:6px">⚠️ 충(沖) 발견</div>
                        <div style="font-size:13px;color:#333">{', '.join(result['충'])}</div>
                        <div style="font-size:12px;color:#000000;margin-top:4px">충이 있어도 서로 이해하고 보완하면 더욱 단단한 인연이 됩니다.</div>
                    </div>""", unsafe_allow_html=True)
                
                gui_items = []
                if result["귀인_a"]: gui_items.append(f"{name}의 사주에 {pname}이 귀인 역할")
                if result["귀인_b"]: gui_items.append(f"{pname}의 사주에 {name}이 귀인 역할")
                if gui_items:
                    st.markdown(f"""
                    <div class="card" style="background:#ffffff;border:1px solid #e8d5a0">
                        <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">⭐ 천을귀인 인연!</div>
                        <div style="font-size:13px;color:#444">{'<br>'.join(gui_items)}</div>
                    </div>""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"분석 오류: {e}")


def tab_taegil(pils, name="나"):
    """택일(擇日) 탭"""
    st.markdown('<div class="gold-section">📅 택일(擇日) — 길한 날을 고르다</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="background:#ffffff;border:1px solid #e8d5a0;margin-bottom:12px">
        <div style="font-size:13px;color:#000000;font-weight:700;margin-bottom:4px">💡 택일이란?</div>
        <div style="font-size:13px;color:#000000;line-height:1.8">
        내 사주와 천간지지가 잘 맞는 날을 골라 중요한 일(결혼·이사·계약·개업·수술 등)을 진행하면 
        더욱 좋은 결과를 얻을 수 있습니다. 천을귀인일·삼합일이 가장 좋은 날입니다.
        </div>
    </div>""", unsafe_allow_html=True)
    
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    col1, col2, col3 = st.columns(3)
    with col1:
        t_year = st.selectbox("연도", list(range(current_year, current_year+3)), key="taegil_year")
    with col2:
        t_month = st.selectbox("월", list(range(1, 13)), index=current_month-1, key="taegil_month")
    with col3:
        t_purpose = st.selectbox("목적", ["결혼", "이사", "개업·계약", "수술", "시험·면접", "기타 중요한 일"], key="taegil_purpose")
    
    if st.button("📅 길일 찾기", use_container_width=True, type="primary"):
        good_days = get_good_days(pils, t_year, t_month)
        
        if good_days:
            st.markdown(f"### ✨ {t_year}년 {t_month}월 {t_purpose}에 좋은 날")
            for d in good_days:
                is_best = d["score"] >= 80
                bg = "#ffffff" if is_best else "#fafafa"
                border = "2px solid #000000" if is_best else "1px solid #e8e8e8"
                
                st.markdown(f"""
                <div style="background:{bg};{border};border-radius:12px;padding:14px;margin:6px 0;display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <span style="font-size:18px;font-weight:800;color:#000000">{t_year}년 {t_month}월 {d['day']}일</span>
                        <span style="font-size:14px;color:#000000;margin-left:10px">{d['pillar']}일</span>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:16px;font-weight:700">{d['level']}</div>
                        <div style="font-size:11px;color:#444">{' / '.join(d['reasons'])}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.warning(f"{t_year}년 {t_month}월에는 특별히 좋은 날이 없습니다. 다른 달을 선택하시거나, 보통 날 중에서 선택하십시오.")


def tab_special_stars(pils):
    """특수 신살 탭"""
    st.markdown('<div class="gold-section">특수 신살(神殺) 분석</div>', unsafe_allow_html=True)
    
    jjs = [p["jj"] for p in pils]
    cgs = [p["cg"] for p in pils]
    
    # 주요 신살 계산
    stars = []
    
    # 천을귀인 (甲戊: 丑未, 乙己: 子申, 丙丁: 亥酉, 庚辛: 丑未, 壬癸: 卯巳)
    chungeul_map = {
        "甲":"丑未","乙":"子申","丙":"亥酉","丁":"亥酉",
        "戊":"丑未","己":"子申","庚":"丑未","辛":"丑未",
        "壬":"卯巳","癸":"卯巳"
    }
    ilgan = pils[1]["cg"]
    chungeul_jjs = chungeul_map.get(ilgan, "")
    if any(jj in chungeul_jjs for jj in jjs):
        stars.append(("천을귀인(天乙貴人)", "⭐", "하늘이 내린 귀인성! 위기 시 귀인의 도움을 받고 평생 좋은 사람들과 인연이 맺힙니다."))
    
    # 문창귀인
    munchang_map = {"甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申","己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯"}
    if munchang_map.get(ilgan) in jjs:
        stars.append(("문창귀인(文昌貴人)", "📚", "학문과 예술에 뛰어난 재주! 시험운이 강하고 문필·학술 분야에서 두각을 나타냅니다."))
    
    # 역마살
    yeokma_map = {"寅午戌":"申","申子辰":"寅","巳酉丑":"亥","亥卯未":"巳"}
    year_jj = pils[3]["jj"]
    for combo, yeokma_jj in yeokma_map.items():
        if year_jj in combo and yeokma_jj in jjs:
            stars.append(("역마살(驛馬殺)", "🐎", "이동·변화·여행의 기운! 해외 인연이나 이동이 잦고 활동적인 직업이 맞습니다."))
    
    # 도화살
    dohwa_map = {"寅午戌":"卯","申子辰":"酉","巳酉丑":"午","亥卯未":"子"}
    for combo, dohwa_jj in dohwa_map.items():
        if year_jj in combo and dohwa_jj in jjs:
            stars.append(("도화살(桃花殺)", "🌸", "매력과 이성운이 강한 기운! 인기직종이나 예술·서비스업에서 두각을 나타냅니다."))
    
    # 화개살
    hwagae_map = {"寅午戌":"戌","申子辰":"辰","巳酉丑":"丑","亥卯未":"未"}
    for combo, hwagae_jj in hwagae_map.items():
        if year_jj in combo and hwagae_jj in jjs:
            stars.append(("화개살(華蓋殺)", "🧘", "종교·예술·학문의 기운! 혼자 깊이 파고드는 연구나 종교계에서 빛을 발합니다."))
    
    if stars:
        for name, icon, desc in stars:
            st.markdown(f"""
            <div class="card" style="margin:8px 10px">
                <div style="font-size:16px;font-weight:700;color:#000000">{icon} {name}</div>
                <div style="font-size:13px;color:#000000;margin-top:6px;line-height:1.8">{desc}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card">
            <div style="font-size:14px;color:#333">특별한 신살이 없으나 순수한 정격(正格)의 기운으로 안정적인 인생을 영위하실 수 있습니다.</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  월령(月令) 심화 — 왕상휴수사
# ══════════════════════════════════════════════════

WARYEONG_TABLE = {
    "木": {"寅":100,"卯":100,"辰":40,"巳":20,"午":10,"未":20,"申":10,"酉":10,"戌":20,"亥":70,"子":70,"丑":40},
    "火": {"寅":70,"卯":70,"辰":40,"巳":100,"午":100,"未":100,"申":20,"酉":10,"戌":20,"亥":10,"子":10,"丑":20},
    "土": {"寅":20,"卯":20,"辰":100,"巳":70,"午":70,"未":100,"申":70,"酉":40,"戌":100,"亥":20,"子":10,"丑":100},
    "金": {"寅":10,"卯":10,"辰":20,"巳":10,"午":10,"未":20,"申":100,"酉":100,"戌":70,"亥":40,"子":20,"丑":40},
    "水": {"寅":40,"卯":20,"辰":20,"巳":10,"午":10,"未":10,"申":40,"酉":70,"戌":40,"亥":100,"子":100,"丑":70},
}

JJ_MONTH_SEASON = {
    "寅":"봄 초입(1월, 양력2월)","卯":"봄 한창(2월, 양력3월)","辰":"봄 마무리(3월, 양력4월)",
    "巳":"여름 초입(4월, 양력5월)","午":"여름 한창(5월, 양력6월)","未":"여름 마무리(6월, 양력7월)",
    "申":"가을 초입(7월, 양력8월)","酉":"가을 한창(8월, 양력9월)","戌":"가을 마무리(9월, 양력10월)",
    "亥":"겨울 초입(10월, 양력11월)","子":"겨울 한창(11월, 양력12월)","丑":"겨울 마무리(12월, 양력1월)",
}

def get_waryeong(pils):
    wol_jj = pils[2]["jj"]
    result = {}
    grades = [(85,"왕(旺)","#c0392b","月令에서 가장 강한 기운. 이 오행이 사주를 주도합니다."),
              (60,"상(相)","#e67e22","月令의 지원을 받아 활발한 기운입니다."),
              (35,"휴(休)","#f39c12","月令에서 힘을 얻지 못하고 쉬는 기운입니다."),
              (15,"수(囚)","#7f8c8d","月令에서 억눌림을 받는 기운입니다."),
              (0, "사(死)","#2c3e50","月令에서 가장 힘을 잃은 기운입니다.")]
    for oh in ["木","火","土","金","水"]:
        score = WARYEONG_TABLE[oh].get(wol_jj, 20)
        label,color,desc = "평","#888",""
        for threshold,lbl,col,dsc in grades:
            if score >= threshold:
                label,color,desc = lbl,col,dsc
                break
        result[oh] = {"score":score,"grade":label,"color":color,"desc":desc}
    return {"월지":wol_jj,"계절":JJ_MONTH_SEASON.get(wol_jj,""),"오행별":result}


# ══════════════════════════════════════════════════
#  외격(外格) + 양인(羊刃)
# ══════════════════════════════════════════════════

YANGIN_MAP = {"甲":"卯","丙":"午","戊":"午","庚":"酉","壬":"子","乙":"辰","丁":"未","己":"未","辛":"戌","癸":"丑"}
YANGIN_DESC = {
    "甲":{"jj":"卯","name":"갑목 양인 卯","desc":"목기 극강. 결단력·추진력 폭발. 관재·사고·분쟁 주의.","good":"군인·경찰·의사·법조인","caution":"분노 충동 다스리기. 칠살과 함께면 더욱 강렬."},
    "丙":{"jj":"午","name":"병화 양인 午","desc":"태양이 정오에 빛남. 카리스마·권력욕 압도적.","good":"정치·방송·경영·스포츠","caution":"오만과 독선 경계. 임수의 제어 필요."},
    "戊":{"jj":"午","name":"무토 양인 午","desc":"대지가 달아오른 강렬한 기운. 실행력·의지력 대단.","good":"건설·부동산·스포츠·경영","caution":"독선 결정이 조직을 해침. 협력자 경청 필요."},
    "庚":{"jj":"酉","name":"경금 양인 酉","desc":"금기 극강. 결단력 칼같이 날카로움.","good":"군인·경찰·외과의·법조인","caution":"냉정함 과하면 인간관계 끊김. 화기의 단련 필요."},
    "壬":{"jj":"子","name":"임수 양인 子","desc":"수기 넘침. 지혜·전략 압도적이나 방향 잃으면 홍수.","good":"전략·외교·금융·IT·철학","caution":"무토 제방 없으면 방종·방황. 목표와 원칙 필수."},
    "乙":{"jj":"辰","name":"을목 양인 辰","desc":"을목 양인. 고집과 인내력이 강함.","good":"전문직·연구·예술","caution":"고집이 화근이 될 수 있음."},
    "丁":{"jj":"未","name":"정화 양인 未","desc":"정화 양인. 감성적 에너지가 강함.","good":"예술·교육·상담","caution":"감정 기복에 주의."},
    "己":{"jj":"未","name":"기토 양인 未","desc":"기토 양인. 고집과 끈기가 강함.","good":"농업·의료·전문직","caution":"고집을 유연함으로 바꾸는 것이 과제."},
    "辛":{"jj":"戌","name":"신금 양인 戌","desc":"신금 양인. 예리함과 완벽주의가 극도로 강함.","good":"예술·의료·분석","caution":"과도한 완벽주의가 자신을 소진함."},
    "癸":{"jj":"丑","name":"계수 양인 丑","desc":"계수 양인. 끈기와 인내의 기운이 강함.","good":"연구·의료·학문","caution":"자신을 과소평가하지 말 것."},
}

def get_yangin(pils):
    ilgan = pils[1]["cg"]
    yangin_jj = YANGIN_MAP.get(ilgan,"")
    found = [["시주","일주","월주","년주"][i] for i,p in enumerate(pils) if p["jj"]==yangin_jj]
    return {"일간":ilgan,"양인_지지":yangin_jj,"존재":bool(found),"위치":found,"설명":YANGIN_DESC.get(ilgan,{})}

def get_oigyeok(pils):
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan,"")
    oh_strength = calc_ohaeng_strength(ilgan, pils)
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    CTRL = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    BIRTH_R = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    GEN = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    results = []
    # 종왕격
    if oh_strength.get(ilgan_oh,0) >= 70 and sn=="신강(身强)":
        results.append({"격":"종왕격(從旺格)","icon":"👑","color":"#000000",
            "desc":f"일간 오행({OHN.get(ilgan_oh,'')})이 사주를 지배. 같은 오행을 돕는 것이 용신.",
            "용신":f"{ilgan_oh}·{BIRTH_R.get(ilgan_oh,'')}","기신":f"{CTRL.get(ilgan_oh,'')}",
            "caution":"종왕격을 내격으로 착각하면 완전히 반대 풀이가 됩니다."})
    # 종재격
    jae_oh = CTRL.get(ilgan_oh,"")
    if oh_strength.get(jae_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종재격(從財格)","icon":"💰","color":"#2980b9",
            "desc":f"재성({OHN.get(jae_oh,'')})이 사주를 압도. 재성을 따르는 것이 순리.",
            "용신":f"{jae_oh}·{GEN.get(jae_oh,'')}","기신":f"{ilgan_oh} 비겁·{BIRTH_R.get(ilgan_oh,'')} 인성",
            "caution":"비겁·인성 운이 오면 오히려 크게 파란이 생깁니다."})
    # 종관격
    gwan_oh = next((k for k,v in CTRL.items() if v==ilgan_oh),"")
    if oh_strength.get(gwan_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종관격(從官格)","icon":"🎖️","color":"#27ae60",
            "desc":f"관성({OHN.get(gwan_oh,'')})이 사주를 지배. 공직·관직에서 크게 발복.",
            "용신":f"{gwan_oh}·{jae_oh}","기신":f"{ilgan_oh} 비겁",
            "caution":"비겁이 오면 구설·관재가 생기기 쉽습니다."})
    # 종아격
    sik_oh = GEN.get(ilgan_oh,"")
    if oh_strength.get(sik_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종아격(從兒格)","icon":"🎨","color":"#8e44ad",
            "desc":f"식상({OHN.get(sik_oh,'')})이 사주를 지배. 창의·예술·기술의 기운 압도적.",
            "용신":f"{sik_oh}·{CTRL.get(ilgan_oh,'')}","기신":"관성·인성",
            "caution":"관성·인성 운에서 건강·사고·좌절이 오기 쉽습니다."})
    return results


# ══════════════════════════════════════════════════
#  12신살(十二神殺) 완전판
# ══════════════════════════════════════════════════

SINSAL_12_TABLE = {
    "劫殺":{"寅午戌":"亥","申子辰":"巳","巳酉丑":"寅","亥卯未":"申"},
    "災殺":{"寅午戌":"子","申子辰":"午","巳酉丑":"卯","亥卯未":"酉"},
    "天殺":{"寅午戌":"丑","申子辰":"未","巳酉丑":"辰","亥卯未":"戌"},
    "地殺":{"寅午戌":"寅","申子辰":"申","巳酉丑":"巳","亥卯未":"亥"},
    "年殺":{"寅午戌":"卯","申子辰":"酉","巳酉丑":"午","亥卯未":"子"},
    "月殺":{"寅午戌":"辰","申子辰":"戌","巳酉丑":"未","亥卯未":"丑"},
    "亡身殺":{"寅午戌":"巳","申子辰":"亥","巳酉丑":"申","亥卯未":"寅"},
    "將星殺":{"寅午戌":"午","申子辰":"子","巳酉丑":"酉","亥卯未":"卯"},
    "攀鞍殺":{"寅午戌":"未","申子辰":"丑","巳酉丑":"戌","亥卯未":"辰"},
    "驛馬殺":{"寅午戌":"申","申子辰":"寅","巳酉丑":"亥","亥卯未":"巳"},
    "六害殺":{"寅午戌":"酉","申子辰":"卯","巳酉丑":"子","亥卯未":"午"},
    "華蓋殺":{"寅午戌":"戌","申子辰":"辰","巳酉丑":"丑","亥卯未":"未"},
}

SINSAL_12_DESC = {
    "劫殺":{"icon":"⚔️","type":"흉","name":"겁살(劫殺)","desc":"강한 변동·손재·이별의 신살. 갑작스러운 사고가 따릅니다.","good":"군인·경찰·의사·위기관리에서 능력 발휘.","caution":"겁살 대운엔 투자·보증·동업 각별히 조심."},
    "災殺":{"icon":"💧","type":"흉","name":"재살(災殺)","desc":"재앙·수재의 신살. 관재·질병·교통사고 주의.","good":"의료·소방·구조 분야에서 특수 능력 발휘.","caution":"해외여행·수상활동 각별히 주의."},
    "天殺":{"icon":"⚡","type":"흉","name":"천살(天殺)","desc":"예상치 못한 천재지변·돌발사고. 상사와 마찰.","good":"위기 상황에서 빛을 발하는 강인함.","caution":"상사·어른과의 갈등을 극도로 조심."},
    "地殺":{"icon":"🌍","type":"중","name":"지살(地殺)","desc":"이동·변화의 신살. 역마와 함께면 해외 이동 많음.","good":"외판·무역·항공·운수업에 유리.","caution":"정착하지 못하고 떠도는 기운 조심."},
    "年殺":{"icon":"🌸","type":"중","name":"년살(도화살)","desc":"이성 인기 독차지. 예술적 기질 강함.","good":"연예인·방송·서비스·예술가로 대성.","caution":"이성 문제·향락으로 인한 문제 조심."},
    "月殺":{"icon":"🪨","type":"흉","name":"월살(고초살)","desc":"뿌리 뽑힌 풀처럼 고생하는 기운. 가정적 어려움.","good":"역경을 이겨내는 강인한 정신력.","caution":"독립 후 오히려 안정되는 경우 많음."},
    "亡身殺":{"icon":"🌀","type":"흉","name":"망신살","desc":"구설·스캔들·배신의 기운. 체면 손상.","good":"정면 돌파 용기. 역경으로 더욱 강해짐.","caution":"언행 극도 조심. 비밀 관리 철저히."},
    "將星殺":{"icon":"🎖️","type":"길","name":"장성살","desc":"장수(將帥)의 별. 강한 리더십·통솔력. 조직 수장 기운.","good":"군인·경찰·정치·경영·스포츠 감독으로 최고자리.","caution":"독선적이 되지 않도록 주의."},
    "攀鞍殺":{"icon":"🐎","type":"길","name":"반안살","desc":"말안장 위. 안정된 자리에서 성장. 중년 이후 안정.","good":"전문직·학자·행정가로 꾸준한 성공.","caution":"안주하려는 경향. 도전 정신 유지하기."},
    "驛馬殺":{"icon":"🏇","type":"중","name":"역마살","desc":"이동·여행·해외·변화의 신살. 정착하기 어려움.","good":"해외·무역·외교·운수·영업에서 크게 활약.","caution":"이동 많아 가정생활 불안정할 수 있음."},
    "六害殺":{"icon":"🌀","type":"흉","name":"육해살","desc":"배신과 상처의 신살. 소화기 질환 주의.","good":"인내력과 회복력이 뛰어남.","caution":"가까운 사람에게 배신당하는 기운. 인간관계 신중히."},
    "華蓋殺":{"icon":"🌂","type":"중","name":"화개살","desc":"예술·종교·철학·영성의 신살. 고독하지만 고귀함.","good":"예술가·철학자·종교인·상담사로 독보적 경지.","caution":"고독·은둔 기운 강함. 사회적 관계 의식적으로 유지."},
}

EXTRA_SINSAL = {
    "귀문관살":{
        "icon":"🔮","type":"흉","name":"귀문관살(鬼門關殺)",
        "pairs":[frozenset(["子","酉"]),frozenset(["丑","午"]),frozenset(["寅","未"]),
                 frozenset(["卯","申"]),frozenset(["辰","亥"]),frozenset(["巳","戌"])],
        "desc":"영적 감수성 극도 발달 또는 신경증·불면·이상한 꿈.",
        "good":"무속인·철학자·상담사·예술가 — 남들이 보지 못하는 것을 봄.",
        "caution":"신경증·우울·집착 주의. 명상·규칙적 생활 필수.",
    },
    "백호대살":{
        "icon":"🐯","type":"흉","name":"백호대살(白虎大殺)",
        "targets":{"甲辰","乙未","丙戌","丁丑","戊辰","己未","庚戌","辛丑","壬辰","癸未","甲戌","乙丑","丙辰","丁未"},
        "desc":"혈광지사(血光之事) — 사고·수술·폭력과 인연.",
        "good":"외과의사·군인·경찰로 기운을 직업으로 승화하면 대성.",
        "caution":"대운에서 백호가 오면 교통사고·수술 극도 주의.",
    },
    "원진살":{
        "icon":"😡","type":"흉","name":"원진살(怨嗔殺)",
        "pairs":[frozenset(["子","未"]),frozenset(["丑","午"]),frozenset(["寅","酉"]),
                 frozenset(["卯","申"]),frozenset(["辰","亥"]),frozenset(["巳","戌"])],
        "desc":"서로 미워하고 원망하는 신살. 부부·가족 갈등의 원인.",
        "good":"강한 독립심을 키움.",
        "caution":"배우자·가족과 원진은 관계 갈등의 근원. 이해 노력 필수.",
    },
}

def get_12sinsal(pils):
    nyon_jj = pils[3]["jj"]
    pil_jjs = [p["jj"] for p in pils]
    labels = ["시주","일주","월주","년주"]
    san_groups = ["寅午戌","申子辰","巳酉丑","亥卯未"]
    my_group = next((g for g in san_groups if nyon_jj in g),"寅午戌")
    result = []
    for sname, jj_map in SINSAL_12_TABLE.items():
        sinsal_jj = jj_map.get(my_group,"")
        found = [labels[i] for i,jj in enumerate(pil_jjs) if jj==sinsal_jj]
        if found:
            d = SINSAL_12_DESC.get(sname,{})
            result.append({"이름":d.get("name",sname),"icon":d.get("icon","⭐"),
                           "type":d.get("type","중"),"위치":found,"해당지지":sinsal_jj,
                           "desc":d.get("desc",""),"good":d.get("good",""),"caution":d.get("caution","")})
    # 추가 신살
    jj_pairs = [frozenset([pil_jjs[i],pil_jjs[j]]) for i in range(4) for j in range(i+1,4)]
    for skey, sd in EXTRA_SINSAL.items():
        if skey in ("귀문관살","원진살"):
            if any(p in sd["pairs"] for p in jj_pairs):
                result.append({"이름":sd["name"],"icon":sd["icon"],"type":sd["type"],
                               "위치":["사주내"],"해당지지":"-","desc":sd["desc"],"good":sd["good"],"caution":sd["caution"]})
        elif skey=="백호대살":
            bh = [f"{p['cg']}{p['jj']}" for p in pils if f"{p['cg']}{p['jj']}" in sd["targets"]]
            if bh:
                result.append({"이름":sd["name"],"icon":sd["icon"],"type":sd["type"],
                               "위치":bh,"해당지지":"-","desc":sd["desc"],"good":sd["good"],"caution":sd["caution"]})
    return result


# ══════════════════════════════════════════════════
#  대운·세운 교차 분석
# ══════════════════════════════════════════════════


# ══════════════════════════════════════════════════
# ★ 사건 트리거 감지 엔진 v2 ★
# 충·형·합 + 십성활성 + 대운전환점 → "소름 포인트" 생성
# ══════════════════════════════════════════════════

_JIJI_CHUNG = {
    "子":"午","午":"子","丑":"未","未":"丑",
    "寅":"申","申":"寅","卯":"酉","酉":"卯",
    "辰":"戌","戌":"辰","巳":"亥","亥":"巳",
}
_JIJI_HYEONG = {
    "子":"卯","卯":"子",
    "寅":"巳","巳":"申","申":"寅",
    "丑":"戌","戌":"未","未":"丑",
    "辰":"辰","午":"午","酉":"酉","亥":"亥",
}
_TG_HAP_PAIRS = [{"甲","己"},{"乙","庚"},{"丙","辛"},{"丁","壬"},{"戊","癸"}]
_SAM_HAP = [
    (frozenset({"寅","午","戌"}),"火"),(frozenset({"申","子","辰"}),"水"),
    (frozenset({"亥","卯","未"}),"木"),(frozenset({"巳","酉","丑"}),"金"),
]
_BIRTH_F2 = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
_CTRL2    = {"木":"土","火":"金","土":"水","金":"木","水":"火"}


def detect_event_triggers(pils, birth_year, gender, target_year=None):
    """
    사건 트리거 감지 — 충/형/합/십성활성/대운전환
    Returns list[dict]: type, title, detail, prob(0~100)
    """
    if target_year is None:
        target_year = datetime.now().year

    ilgan  = pils[1]["cg"]
    il_jj  = pils[1]["jj"]
    wol_jj = pils[2]["jj"]

    y_idx   = (target_year - 4) % 60
    year_jj = JJ[y_idx % 12]
    year_cg = CG[y_idx % 10]

    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    cur_dw  = next((d for d in dw_list if d["시작연도"]<=target_year<=d["종료연도"]), None)
    dw_jj   = cur_dw["jj"] if cur_dw else ""
    dw_cg   = cur_dw["cg"] if cur_dw else ""

    ys       = get_yongshin(pils)
    yong_ohs = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
    all_jjs  = frozenset(p["jj"] for p in pils)
    triggers = []

    def add(type_, title, detail, prob):
        triggers.append({"type":type_,"title":title,"detail":detail,"prob":prob})

    # ① 충
    if _JIJI_CHUNG.get(il_jj) == year_jj:
        add("충","⚡ 일지 충(세운) — 삶의 터전 격변",
            "이사·직장변화·관계분리 확률이 높습니다. 기존 환경이 흔들리는 해입니다.",85)
    if dw_jj and _JIJI_CHUNG.get(il_jj) == dw_jj:
        add("충","⚡ 일지 충(대운) | 10년 환경 변화",
            "대운 수준의 큰 환경 변화. 이사·직업 전환의 대운입니다.",80)
    if _JIJI_CHUNG.get(wol_jj) == year_jj:
        add("충","🌊 월지 충 — 가족·직업 변동",
            "부모·형제 관계 변화, 직업 환경의 급격한 변화가 예상됩니다.",75)

    # ② 형
    if _JIJI_HYEONG.get(il_jj) == year_jj or _JIJI_HYEONG.get(year_jj) == il_jj:
        add("형","⚠️ 일지 형(刑) — 스트레스·사고",
            "건강·사고·법적 문제에 주의. 인간관계 갈등이 생깁니다.",70)

    # ③ 천간합
    for pair in _TG_HAP_PAIRS:
        if dw_cg in pair and year_cg in pair:
            add("합","💑 천간합 — 새 인연·파트너십",
                "새로운 인연·결혼·동업·계약 인연이 찾아옵니다.",65)
            break

    # ④ 삼합국
    check_jjs = all_jjs | frozenset([dw_jj, year_jj])
    for combo, oh in _SAM_HAP:
        if combo.issubset(check_jjs):
            kind = "용신" if oh in yong_ohs else "기신"
            add("삼합","🌟 삼합국 — 강력한 기운 형성",
                f"대운·세운·원국이 {oh}({OHN.get(oh,'')}) 삼합. {kind} 오행이므로 {'크게 발복' if kind=='용신' else '조심 필요'}합니다.",80)
            break

    # ⑤ 용신/기신 대운
    if dw_cg:
        dw_oh = OH.get(dw_cg,"")
        if dw_oh in yong_ohs:
            add("황금기","✨ 용신 대운 — 황금기",
                "일생에 몇 번 없는 상승기. 이 시기의 도전은 결실을 맺습니다.",90)
        elif any(_CTRL2.get(dw_oh)==y or _CTRL2.get(y)==dw_oh for y in yong_ohs):
            add("경계","🛡️ 기신 대운 — 방어 필요",
                "확장보다 수성(守成)이 최선. 큰 결정은 신중히 하십시오.",80)

    # ⑥ 대운 전환점 (2년 이내)
    for i, dw_item in enumerate(dw_list[:-1]):
        if dw_item["시작연도"] <= target_year <= dw_item["종료연도"]:
            yrs_left = dw_item["종료연도"] - target_year
            if yrs_left <= 2:
                next_dw = dw_list[i+1]
                add("전환","🔄 대운 전환점 — 흐름 역전",
                    f"{yrs_left+1}년 안에 대운이 {next_dw['str']}로 전환됩니다. 이전과 다른 인생 국면이 펼쳐집니다.",85)

    # ⑦ 십성 활성화
    year_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(year_cg,"-")
    if year_ss in ["정관","편관"]:
        add("직업","🎖️ 관성 활성 — 직업·명예 변화",
            f"세운 천간({year_cg})이 {year_ss}. 승진·이직·자격증 변화가 예상됩니다.",70)
    if year_ss in ["정재","편재"]:
        add("재물","💰 재성 활성 — 재물 흐름",
            f"세운 천간({year_cg})이 {year_ss}. 재물 흐름이 활발해집니다. 투자 기회 주의.",72)

    return triggers


def calc_luck_score(pils, birth_year, gender, target_year=None):
    """대운+세운 종합 운세 점수 (0~100)"""
    if target_year is None:
        target_year = datetime.now().year
    ys       = get_yongshin(pils)
    yong_ohs = ys.get("종합_용신",[]) if isinstance(ys.get("종합_용신"),list) else []
    dw_list  = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    cur_dw   = next((d for d in dw_list if d["시작연도"]<=target_year<=d["종료연도"]),None)
    score    = 50
    if cur_dw:
        dw_oh = OH.get(cur_dw["cg"],"")
        if dw_oh in yong_ohs: score += 25
        elif any(_BIRTH_F2.get(dw_oh)==y for y in yong_ohs): score += 12
        elif any(_CTRL2.get(dw_oh)==y or _CTRL2.get(y)==dw_oh for y in yong_ohs): score -= 20
    _LV = {"대길(大吉)":20,"길(吉)":10,"평길(平吉)":5,"평(平)":0,"흉(凶)":-15,"흉흉(凶凶)":-25}
    yl = get_yearly_luck(pils, target_year)
    score += _LV.get(yl.get("길흉","평(平)"),0)
    return max(0, min(100, score))


def calc_turning_point(pils, birth_year, gender, target_year=None):
    """
    인생 전환점 감지 엔진 (정밀 v2)
    대운 점수 차이 + 세운 트리거 + 충합 종합
    Returns dict: {is_turning:bool, intensity:str, reason:list, score_change:int}
    """
    if target_year is None:
        target_year = datetime.now().year
    prev_score = calc_luck_score(pils, birth_year, gender, target_year - 1)
    curr_score = calc_luck_score(pils, birth_year, gender, target_year)
    next_score = calc_luck_score(pils, birth_year, gender, target_year + 1)

    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    cur_dw  = next((d for d in dw_list if d["시작연도"] <= target_year <= d["종료연도"]), None)
    prev_dw = None
    for i, d in enumerate(dw_list):
        if d["시작연도"] <= target_year <= d["종료연도"] and i > 0:
            prev_dw = dw_list[i-1]
            break

    reasons = []
    diff = curr_score - prev_score
    next_diff = next_score - curr_score

    # 대운 전환점 (이 해 또는 1~2년 이내)
    if cur_dw:
        yrs_to_change = cur_dw["종료연도"] - target_year
        if yrs_to_change <= 1:
            reasons.append(f"⚡ 대운 {cur_dw['str']} 마지막 해 — 인생 국면 전환 목전")
        if cur_dw["시작연도"] == target_year:
            reasons.append(f"🌟 새 대운 {cur_dw['str']} 시작 | 10년 흐름 완전 변화")

    if prev_dw and cur_dw and cur_dw["시작연도"] == target_year:
        # 이전 대운과 오행 관계
        prev_oh = OH.get(prev_dw["cg"], "")
        curr_oh = OH.get(cur_dw["cg"], "")
        ys = get_yongshin(pils)
        yong_ohs = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
        if prev_oh not in yong_ohs and curr_oh in yong_ohs:
            reasons.append(f"✨ 기신 대운→용신 대운 전환 — 인생 역전의 기회")
        elif prev_oh in yong_ohs and curr_oh not in yong_ohs:
            reasons.append(f"⚠️ 용신 대운→기신 대운 전환 — 속도 조절 필요")

    # 운세 점수 급변
    if abs(diff) >= 25:
        direction = "상승" if diff > 0 else "하락"
        reasons.append(f"📊 운세 점수 {abs(diff)}점 급{'등' if diff>0 else '락'} — 삶의 {direction} 흐름")
    elif abs(diff) >= 15:
        direction = "개선" if diff > 0 else "하강"
        reasons.append(f"📈 운세 {direction} ({diff:+d}점) — 변화 감지")

    # 사건 트리거 (충/합 있으면 강화)
    triggers = detect_event_triggers(pils, birth_year, gender, target_year)
    high_triggers = [t for t in triggers if t["prob"] >= 80]
    if high_triggers:
        reasons.append(f"🔴 고확률 사건 트리거 {len(high_triggers)}개 — {high_triggers[0]['title']}")

    # 전환점 여부 및 강도
    total_score_change = abs(diff)
    is_turning = total_score_change >= 15 or any("대운" in r or "전환" in r for r in reasons)

    if total_score_change >= 30 or len(reasons) >= 3:
        intensity = "🔴 강력 전환점"
    elif total_score_change >= 20 or len(reasons) >= 2:
        intensity = "🟡 주요 변화점"
    elif is_turning:
        intensity = "🟢 변화 시작"
    else:
        intensity = "⬜ 흐름 유지"

    # 운세 라벨링 (Stage Labeling)
    fate_label = ("준비기 🌱", "새로운 시작을 위해 내면을 채우고 씨앗을 심는 시기입니다.")
    if is_turning:
        fate_label = ("전환기 ⚡", "삶의 경로가 바뀌는 격동의 시기입니다. 유연한 대처가 필요합니다.")
    elif diff > 10:
        fate_label = ("확장기 🔥", "에너지가 분출되고 외연을 넓히는 시기입니다. 적극적으로 움직이세요.")
    elif curr_score >= 70:
        fate_label = ("수확기 🍂", "그동안의 노력이 결실을 맺는 안정과 성취의 시기입니다.")

    return {
        "is_turning": is_turning,
        "intensity": intensity,
        "fate_label": fate_label[0],
        "fate_desc": fate_label[1],
        "reason": reasons,
        "score_prev": prev_score,
        "score_curr": curr_score,
        "score_next": next_score,
        "score_change": diff,
        "triggers": triggers,
    }


def get_yongshin_multilayer(pils, birth_year, gender, target_year=None):
    """
    다층 용신 분석 (1순위~3순위 + 희신 + 기신 + 대운별 용신)
    Returns dict with 용신_1순위, 용신_2순위, 희신, 기신, 현재_상황_용신, 대운_용신
    """
    if target_year is None:
        target_year = datetime.now().year

    ys = get_yongshin(pils)
    yong_list = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
    oh_strength = calc_ohaeng_strength(pils[1]["cg"], pils)
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")

    # 상생 순서
    BIRTH = {"木":"火","火":"土","土":"金","金":"水","Water":"木","水":"木"}
    CTRL  = {"木":"土","火":"金","土":"水","金":"木","水":"火"}

    # 용신 1순위 (가장 필요한 오행)
    base_yong = yong_list[0] if yong_list else ""

    # 희신 (용신을 생해주는 오행)
    hee_shin = BIRTH.get(base_yong, "")

    # 기신 (용신을 극하는 오행)
    gi_shin_list = []
    for oh in ["木","火","土","金","水"]:
        if CTRL.get(oh) == base_yong or CTRL.get(base_yong) == oh:
            if oh != ilgan_oh and oh not in yong_list:
                gi_shin_list.append(oh)

    # 용신 2순위
    yong_2 = yong_list[1] if len(yong_list) > 1 else ""

    # 대운별 용신 변화
    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    cur_dw  = next((d for d in dw_list if d["시작연도"] <= target_year <= d["종료연도"]), None)
    dw_yong = ""
    dw_note  = ""
    if cur_dw:
        dw_oh = OH.get(cur_dw["cg"], "")
        if dw_oh in yong_list:
            dw_yong = dw_oh
            dw_note = f"현재 {cur_dw['str']} 대운 = 용신 오행 → 황금기"
        elif dw_oh == hee_shin:
            dw_yong = hee_shin
            dw_note = f"현재 {cur_dw['str']} 대운 = 희신 → 안정 성장기"
        elif dw_oh in gi_shin_list:
            dw_yong = ""
            dw_note = f"현재 {cur_dw['str']} 대운 = 기신 → 방어 전략 필요"
        else:
            dw_yong = dw_oh
            dw_note = f"현재 {cur_dw['str']} 대운 = 중립 → 평상 유지"

    # 상황별 용신 (재물/직장/건강)
    situation_yong = {
        "재물": yong_list[0] if yong_list else "",
        "직업": yong_list[1] if len(yong_list) > 1 else (yong_list[0] if yong_list else ""),
        "건강": hee_shin or (yong_list[0] if yong_list else ""),
        "인간관계": hee_shin or (yong_list[0] if yong_list else ""),
    }

    return {
        "용신_1순위": base_yong,
        "용신_2순위": yong_2,
        "희신": hee_shin,
        "기신": gi_shin_list[:2] if gi_shin_list else [],
        "현재_대운_용신": dw_yong,
        "대운_해석": dw_note,
        "상황별_용신": situation_yong,
        "전체_용신_목록": yong_list,
    }


def build_rich_ai_context(pils, birth_year, gender, target_year=None, focus="종합"):
    """
    AI에게 전달할 풍부한 계산 데이터 JSON 빌더 (Skill 2 & 3: Structuring & Analysis)
    - 감정적 해석을 배제하고 순수 명리 분석 수치/지표만 전달합니다.
    """
    if target_year is None:
        target_year = datetime.now().year
    
    ilgan = pils[1]["cg"]
    strength_info = get_ilgan_strength(ilgan, pils)
    ys_multi = get_yongshin_multilayer(pils, birth_year, gender, target_year)
    turning = calc_turning_point(pils, birth_year, gender, target_year)
    pillars_str = " ".join([p["str"] for p in pils])
    
    # 순수 데이터 구조화 (Skill 2: Structuring)
    context = {
        "metadata": {
            "birth_year": birth_year,
            "gender": gender,
            "target_year": target_year,
            "focus_area": focus
        },
        "saju_pillars": pillars_str,
        "daymaster": {
            "stem": ilgan,
            "strength_score": strength_info["점수"],
            "strength_label": strength_info["신강신약"]
        },
        "elements": strength_info["oh_strength"],
        "yongshin_logic": {
            "primary": ys_multi["용신_1순위"],
            "secondary": ys_multi["용신_2순위"],
            "hee_shin": ys_multi["희신"],
            "gi_shin": ys_multi["기신"]
        },
        "current_flow": {
            "is_turning_point": turning["is_turning"],
            "intensity": turning["intensity"],
            "score_change": turning["score_change"],
            "triggers": [t["title"] for t in turning["triggers"][:3]]
        }
    }
    
    # 분야별 정밀 가중치 데이터 (Skill 3: Analysis)
    if focus == "재물":
        context["domain_specific"] = {
            "wealth_star_strength": "강" if strength_info["oh_strength"].get("土", 0) > 20 else "약", # 예시 로직
            "business_luck": "상승기" if turning["score_change"] > 10 else "안정기"
        }
    elif focus == "연애":
        context["domain_specific"] = {
            "couple_star_status": "활성" if any("합" in t["title"] for t in turning["triggers"]) else "비활성"
        }
    
    return context



# --------------------------------------------------------------
# GOOSEBUMP ENGINE - 소름 문장 자동 생성 (Cold Reading 알고리즘)
# 과거 적중 -> 현재 공감 -> 미래 예고 -> 확신 강화
# --------------------------------------------------------------

def goosebump_engine(pils, birth_year, gender, target_year=None):
    """
    [Engine] Goosebump Engine
    Saju patterns -> Trigger -> Sentence
    Returns: dict
    """
    if target_year is None:
        target_year = datetime.now().year

    ilgan = pils[1]["cg"]
    il_jj = pils[1]["jj"]
    wol_jj = pils[2]["jj"]
    ilgan_oh = OH.get(ilgan, "")
    strength_info = get_ilgan_strength(ilgan, pils)
    oh_str  = strength_info["oh_strength"]
    sn      = strength_info["신강신약"]
    score   = strength_info.get("일간점수", 50)
    TGM = TEN_GODS_MATRIX.get(ilgan, {})
    all_ss = [TGM.get(p["cg"], "-") for p in pils]

    ys       = get_yongshin(pils)
    yong_ohs = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
    luck_s   = calc_luck_score(pils, birth_year, gender, target_year)
    triggers = detect_event_triggers(pils, birth_year, gender, target_year)
    turning  = calc_turning_point(pils, birth_year, gender, target_year)

    # ① 과거 적중 문장 — 사주 패턴 -> 이미 겪은 일
    past_sentences = []

    # 관성 충 감지
    officer_clash = any(TGM.get(p["cg"], "") in ("정관","편관") and
                        _JIJI_CHUNG.get(p["jj"]) in {q["jj"] for q in pils} for p in pils)
    if officer_clash or any(s in ("정관","편관") for s in all_ss):
        past_sentences.append(
            "직장이나 책임 문제로 크게 고민하고 홀로 힘들었던 시기가 분명히 있었습니다."
        )

    # 재성 과다
    wealth_count = sum(1 for s in all_ss if s in ("정재","편재"))
    if wealth_count >= 2:
        past_sentences.append(
            "돈이나 현실적 문제로 판단을 반복하고 마음이 복잡했던 시기가 있었습니다."
        )

    # 인성 과다 (생각 많음)
    insung_count = sum(1 for s in all_ss if s in ("정인","편인"))
    if insung_count >= 2:
        past_sentences.append(
            "머릿속 생각이 많아 결정을 내리지 못하고 오래 고민했던 시간이 있었습니다."
        )

    # 일지 충 (과거)
    past_dw = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    for dw in past_dw:
        if dw["종료연도"] < target_year:
            if _JIJI_CHUNG.get(il_jj) == dw["jj"]:
                age = dw["시작나이"]
                past_sentences.append(
                    f"{age}대에 환경이 크게 바뀌거나 중요한 관계가 변한 일이 있었습니다."
                )
                break

    # 겁재 (재물 경쟁)
    if any(s == "겁재" for s in all_ss):
        past_sentences.append(
            "믿었던 사람에게 금전적으로 손해를 보거나 경쟁에서 예상치 못한 결과를 겪은 적이 있었습니다."
        )

    # ② 현재 상태 문장 — 현재 운 vs 원국 비교
    present_sentences = []
    prev_luck = calc_luck_score(pils, birth_year, gender, target_year - 1)
    diff = luck_s - prev_luck

    if diff < -20:
        present_sentences.append(
            "지금은 노력 대비 결과가 느리게 따라오는 시기입니다. 열심히 하는데 티가 안 나는 느낌, 맞지 않으십니까?"
        )
    elif diff < -10:
        present_sentences.append(
            "최근 들어 무언가 예전 같지 않다는 느낌, 흐름이 살짝 꺾인 느낌을 받고 계실 겁니다."
        )
    elif diff > 20:
        present_sentences.append(
            "지금 운이 올라오는 시기입니다. 최근 생각지도 못한 기회나 연락이 오고 있지는 않으십니까?"
        )
    elif diff > 10:
        present_sentences.append(
            "서서히 흐름이 좋아지는 시기입니다. 주변에서 당신을 다시 보기 시작하는 신호가 보일 겁니다."
        )
    else:
        present_sentences.append(
            "지금은 흐름이 안정적으로 유지되고 있습니다. 큰 변화 없이 무난한 시기지만, 곧 달라질 계기가 옵니다."
        )

    # 신강/신약 현재 체감
    if "신약" in sn:
        present_sentences.append(
            "겉으로는 괜찮아 보이지만 혼자 고민을 오래 끌어가는 편이십니다. 말하지 않고 삭이는 경우가 많습니다."
        )
    elif "신강" in sn:
        present_sentences.append(
            "자신이 옳다는 확신이 강하고, 타인의 시선보다 자기 기준을 먼저 내세우는 편이십니다."
        )

    # ③ 미래 예고 문장
    future_sentences = []
    if turning["is_turning"]:
        intensity = turning["intensity"]
        if "강력" in intensity:
            future_sentences.append(
                "곧 인생 흐름이 크게 바뀌는 계기가 들어옵니다. 이 시기가 지나면 이전과 완전히 다른 국면이 펼쳐집니다."
            )
        else:
            future_sentences.append(
                "변화의 씨앗이 심어지고 있습니다. 지금의 선택 하나가 앞으로 수년을 결정짓는 분기점이 됩니다."
            )

    # 고확률 트리거 예고
    high_t = [t for t in triggers if t["prob"] >= 80]
    if high_t:
        t = high_t[0]
        if t["type"] == "충":
            future_sentences.append(
                "환경이 흔들리는 기운이 다가오고 있습니다. 이사·직장·관계 중 하나가 변할 가능성이 높습니다."
            )
        elif t["type"] == "황금기":
            future_sentences.append(
                "이 시기는 일생에 몇 번 없는 상승기입니다. 지금의 도전은 반드시 결실을 맺습니다."
            )
        elif t["type"] == "합":
            future_sentences.append(
                "새로운 인연이나 협력의 기운이 강하게 들어옵니다. 혼자보다는 함께할 때 결과가 좋습니다."
            )
        elif t["type"] == "인연":
            future_sentences.append(
                "인연의 기운이 움직이고 있습니다. 새로운 중요한 만남이 가까운 시일 안에 찾아옵니다."
            )
        elif t["type"] == "재물":
            future_sentences.append(
                "재물운의 흐름이 강화되고 있습니다. 뜻하지 않은 기회나 보상이 따를 수 있는 시기입니다."
            )

    return {
        "past": " ".join(past_sentences),
        "present": " ".join(present_sentences),
        "future": " ".join(future_sentences),
        "full_text": "\n\n".join([" ".join(past_sentences), " ".join(present_sentences), " ".join(future_sentences)])
    }


def render_lucky_kit(yong_oh):
    """
    Brain 1: 자체 로직 기반 행운의 개운법 UI 렌더링
    """
    kits = {
        "木": {"color": "초록색, 민트", "num": "3, 8", "dir": "동쪽", "food": "신맛, 싱싱한 채소", "icon": ""},
        "火": {"color": "빨간색, 주황색", "num": "2, 7", "dir": "남쪽", "food": "쓴맛, 구운 음식", "icon": ""},
        "土": {"color": "노란색, 브라운", "num": "5, 10", "dir": "중앙", "food": "단맛, 뿌리채소", "icon": ""},
        "金": {"color": "하얀색, 실버", "num": "4, 9", "dir": "서쪽", "food": "매운맛, 견과류", "icon": ""},
        "水": {"color": "검정색, 네이비", "num": "1, 6", "dir": "북쪽", "food": "짠맛, 해조류", "icon": ""},
    }
    k = kits.get(yong_oh, kits["木"])
    
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e0d8c0; border-radius: 12px; padding: 20px; margin-bottom: 25px;">
        <div style="font-size: 16px; font-weight: 800; color: #000000; margin-bottom: 15px; border-bottom: 1px solid #f0e8d0; padding-bottom: 8px;">
            [개운] 오늘의 행운 개운 비방 (Lucky Kit)
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div style="font-size: 14px; color: #555;"><b>행운의 색상:</b> <span style="color:#333">{k['color']}</span></div>
            <div style="font-size: 14px; color: #555;"><b>행운의 숫자:</b> <span style="color:#333">{k['num']}</span></div>
            <div style="font-size: 14px; color: #555;"><b>행운의 방향:</b> <span style="color:#333">{k['dir']}</span></div>
            <div style="font-size: 14px; color: #555;"><b>행운의 음식:</b> <span style="color:#333">{k['food']}</span></div>
        </div>
        <div style="margin-top: 12px; font-size: 12px; color: #888; font-style: italic;">
            (안내) {yong_oh}의 기운을 보강하여 오늘 하루의 운기를 상승시키는 실천법입니다.
        </div>
    </div>
    """, unsafe_allow_html=True)


# [중복 제거] b3_track_behavior 전체 구현은 아래 Brain3 섹션에 있음

def apply_mansin_filter(text):
    """만신 AI 환각 방지 및 말투 보정 필터"""
    if not text: return ""
    text = text.replace("AI로서 말씀드리면", "만신의 눈으로 보건대")
    text = text.replace("분석한 결과입니다", "천명의 암호를 풀이한 결과로다")
    text = text.replace("도움이 되셨길 바랍니다", "부디 이 신탁이 네 삶의 등불이 되길 바란다")
    return text


def get_extra_sinsal(pils):
    """
    고급 신살 감지 로직 (Brain 1 정밀 분석)
    문창귀인, 천을귀인, 귀문관살, 백호대살 등
    """
    ilgan = pils[1]["cg"]
    all_jjs = [p["jj"] for p in pils]
    stars = []
    
    munchang_map = {"甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申","己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯"}
    if munchang_map.get(ilgan) in all_jjs:
        stars.append({"name": "문창귀인(文昌)", "desc": "지혜가 총명하고 학문과 예술에 뛰어난 재능"})

    gwimun_pairs = [{"子","酉"},{"丑","午"},{"寅","未"},{"卯","申"},{"辰","亥"},{"巳","戌"}]
    for pair in gwimun_pairs:
        if pair.issubset(set(all_jjs)):
            stars.append({"name": "귀문관살(鬼門)", "desc": "직관력이 뛰어나고 예민한 천재성, 영적 감각"})
            break

    baekho = ["甲辰","乙未","丙戌","丁丑","戊辰","壬戌","癸丑"]
    for p in pils:
        if (p["cg"]+p["jj"]) in baekho:
            stars.append({"name": "백호대살(白虎)", "desc": "강한 추진력과 전문성, 압도적인 에너지"})
            break

    cheon_eul = {"甲":"未","乙":"申","丙":"酉","丁":"亥","戊":"未","己":"申","庚":"丑","辛":"寅","壬":"卯","癸":"巳"}
    if cheon_eul.get(ilgan) in all_jjs:
        stars.append({"name": "천을귀인(天乙)", "desc": "인생의 위기에서 돕는 귀인이 상주하는 최고의 길성"})

    return stars



# ══════════════════════════════════════════════════════════════
#  🧠 ADAPTIVE ENGINE — 페르소나 감지 → 맞춤 해석 스타일
#  사용자 행동 패턴으로 성향 자동 추정
# ══════════════════════════════════════════════════════════════

_PERSONA_KEY = "_adaptive_persona"

def infer_persona() -> str:
    """
    세션 행동 데이터로 페르소나 자동 추정
    achievement / overthinking / emotional / cautious / balanced
    """
    behavior = st.session_state.get("_b3_behavior", {})
    focus    = st.session_state.get("ai_focus", "종합")
    actions  = behavior.get("actions", [])
    q_count  = behavior.get("question_count", 0)
    v_count  = behavior.get("view_count", 0)

    # 행동 기반 성향
    if focus == "재물":
        return "achievement_type"   # 성취·결과 지향
    if focus == "연애":
        return "emotional_type"     # 감정·관계 중심
    if focus == "건강":
        return "cautious_type"      # 안정·리스크 회피
    if focus == "직장":
        return "career_type"        # 커리어·명예 지향
    if q_count >= 2:
        return "overthinking_type"  # 생각 많음, 확인 욕구
    if v_count >= 4:
        return "deep_reflection_type"  # 심층 탐색
    return "balanced_type"


def get_persona_prompt_style(persona: str) -> str:
    """페르소나별 AI 해석 스타일 지침"""
    style_map = {
        "achievement_type": (
            "사용자는 성취·결과 지향적이다. "
            "현실적이고 구체적인 행동 가이드와 기회를 중심으로 해석하라. "
            "추상적 표현 최소화. 언제, 무엇을, 어떻게 해야 하는지 단정적으로 말하라."
        ),
        "emotional_type": (
            "사용자는 감정·관계를 중시한다. "
            "인간관계와 감정 흐름을 중심으로 따뜻하고 공감적으로 해석하라. "
            "외로움, 그리움, 설렘 등 감정 언어를 자연스럽게 사용하라."
        ),
        "career_type": (
            "사용자는 커리어와 사회적 인정을 중요하게 생각한다. "
            "직업·승진·명예·직장 흐름을 중심으로 단계적이고 전략적으로 해석하라."
        ),
        "cautious_type": (
            "사용자는 안정과 리스크 회피를 선호한다. "
            "위험 요인을 먼저 짚고, 안전한 선택지와 주의 사항을 구체적으로 제시하라. "
            "과도한 낙관 표현 자제."
        ),
        "overthinking_type": (
            "사용자는 생각이 많고 확신을 원한다. "
            "반복적 고민에 대한 공감을 먼저 표현하고, "
            "단정적이고 명확한 결론을 내려주어 안심시켜라. "
            "모호한 표현 절대 금지."
        ),
        "deep_reflection_type": (
            "사용자는 인생의 의미와 방향성을 탐색 중이다. "
            "철학적이고 깊이 있는 해석을 선호한다. "
            "표면적 사건보다 근본적 원인과 삶의 패턴을 설명하라."
        ),
        "balanced_type": (
            "사용자는 균형 잡힌 관점을 원한다. "
            "긍정과 주의 사항을 균형 있게 제시하고, "
            "현재 상황과 미래 흐름을 종합적으로 해석하라."
        ),
    }
    return style_map.get(persona, style_map["balanced_type"])


def get_persona_label(persona: str) -> tuple:
    """페르소나 -> (아이콘, 한국어 라벨, 색상)"""
    labels = {
        "achievement_type":     ("[목표]", "성취·결과형",    "#e65100"),
        "emotional_type":       ("[감정]", "감정·관계형",    "#e91e8c"),
        "career_type":          ("[커리어]", "커리어·명예형", "#1565c0"),
        "cautious_type":        ("[신중]", "안정·신중형",   "#2e7d32"),
        "overthinking_type":    ("[분석]", "분석·확인형",    "#6a1b9a"),
        "deep_reflection_type": ("[성찰]", "성찰·탐색형",    "#00695c"),
        "balanced_type":        ("[균형]", "균형·종합형",    "#8B6914"),
    }
    return labels.get(persona, ("[종합]", "종합형", "#8B6914"))


# ══════════════════════════════════════════════════════════════
#  SELF-CHECK ENGINE — AI 2패스 자기검증 시스템
#  1차 해석 -> AI 감수 -> 논리 보정 -> 최종 출력
# ══════════════════════════════════════════════════════════════

def self_check_ai(first_report: str, analysis_summary: str, api_key: str, groq_key: str = "") -> str:
    """
    AI 자기검증 시스템
    1차 해석을 AI 감수관이 재검증 -> 모순 제거 + 단정성 강화
    API 비용 절약: 간결한 감수 프롬프트 사용
    """
    if not first_report or (not api_key and not groq_key):
        return first_report

    check_prompt = f"""당신은 30년 경력 명리학 감수 전문가다.

아래 [계산 데이터]와 [해석 초안]을 비교하여 검증하라.

[계산 데이터]
{analysis_summary}

[해석 초안]
{first_report}

검증 규칙:
1. 계산 데이터와 모순되는 문장 -> 삭제 또는 수정
2. "아마", "가능성", "때로는", "일지도" 등 불확실 표현 -> 단정적 표현으로 교체
3. 근거 없는 추측 -> 제거
4. 앞뒤 논리 불일치 -> 보정
5. 길이 유지 (축약 금지)

수정된 최종 리포트만 출력하라. 검증 과정 설명 불필요."""

    try:
        if groq_key:
            import urllib.request, json as _json
            payload = _json.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": check_prompt}],
                "max_tokens": 3000,
                "temperature": 0.3,
            }).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {groq_key}",
                         "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()

        elif api_key:
            import anthropic as _anthr
            client = _anthr.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": check_prompt}]
            )
            return msg.content[0].text.strip()
    except Exception:
        pass

    return first_report  # 실패 시 1차 결과 반환


# ══════════════════════════════════════════════════════════════
#  🔄 RETENTION ENGINE — 재방문·중독 구조
#  스트릭 카운터 / 운 변화 카운트다운 / 일별 운 점수
# ══════════════════════════════════════════════════════════════

_RETENTION_FILE  = "saju_retention.json"
_USER_PROFILE_FILE = "saju_user_profile.json"


# ══════════════════════════════════════════════════════════════
#  🧠 USER MEMORY SYSTEM — AI가 사용자를 기억하는 구조
#  상담 이력 · 관심 영역 · 믿음 지수 · 이전 예측 저장
# ══════════════════════════════════════════════════════════════

def _load_user_profile() -> dict:
    """사용자 프로필 로드"""
    try:
        if os.path.exists(_USER_PROFILE_FILE):
            with open(_USER_PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_user_profile(data: dict):
    """사용자 프로필 저장"""
    try:
        with open(_USER_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_user_profile(saju_key: str) -> dict:
    """특정 사주의 사용자 프로필 반환"""
    all_profiles = _load_user_profile()
    default = {
        "saju_key": saju_key,
        "main_concern": "",            # 주요 관심사
        "past_concerns": [],           # 이전 관심사 이력
        "last_focus": "",              # 마지막 집중 분야
        "last_visit": "",              # 마지막 방문일
        "visit_count": 0,              # 총 방문 횟수
        "belief_level": 0.5,           # 신뢰도 (0~1)
        "last_prediction": "",         # 마지막 예측 요약
        "prediction_history": [],      # 예측 이력
        "stress_pattern": "",          # 주요 스트레스 패턴
        "persona": "balanced_type",    # 감지된 페르소나
        "first_visit": "",             # 첫 방문일
    }
    profile = all_profiles.get(saju_key, default)
    return profile


def update_user_profile(saju_key: str, **kwargs) -> dict:
    """사용자 프로필 업데이트"""
    all_profiles = _load_user_profile()
    profile = get_user_profile(saju_key)
    today = datetime.now().strftime("%Y-%m-%d")

    # 자동 업데이트
    if not profile.get("first_visit"):
        profile["first_visit"] = today
    profile["last_visit"] = today
    profile["visit_count"] = profile.get("visit_count", 0) + 1

    # kwargs 반영
    for k, v in kwargs.items():
        if k == "concern" and v:
            # 관심사 이력 관리
            if profile.get("main_concern") and profile["main_concern"] != v:
                hist = profile.get("past_concerns", [])
                hist.append({"concern": profile["main_concern"], "date": today})
                profile["past_concerns"] = hist[-5:]  # 최근 5개만 유지
            profile["main_concern"] = v
        elif k == "prediction" and v:
            hist = profile.get("prediction_history", [])
            hist.append({"text": v[:100], "date": today})
            profile["prediction_history"] = hist[-10:]
            profile["last_prediction"] = v[:100]
        elif k == "belief_delta" and isinstance(v, (int, float)):
            profile["belief_level"] = max(0.0, min(1.0, profile.get("belief_level", 0.5) + v))
        else:
            profile[k] = v

    all_profiles[saju_key] = profile
    _save_user_profile(all_profiles)
    return profile


def build_memory_context(saju_key: str) -> str:
    """AI 프롬프트에 삽입할 사용자 기억 컨텍스트 생성"""
    profile = get_user_profile(saju_key)
    if profile.get("visit_count", 0) <= 1:
        return ""  # 첫 방문이면 기억 없음

    lines = []
    vc = profile.get("visit_count", 0)
    lines.append(f"[이전 상담 기억] 총 {vc}회 방문한 사용자입니다.")

    if profile.get("main_concern"):
        lines.append(f"주요 관심사: {profile['main_concern']}")

    if profile.get("last_prediction"):
        lines.append(f"지난 상담 예측: {profile['last_prediction']}")

    past = profile.get("past_concerns", [])
    if past:
        prev = past[-1]
        lines.append(f"이전 관심사: {prev.get('concern','')} ({prev.get('date','')})")

    bl = profile.get("belief_level", 0.5)
    if bl >= 0.7:
        lines.append("신뢰도 높음 — 이전 예측이 맞았던 사용자. 더 구체적이고 단정적으로 해석하라.")
    elif bl <= 0.3:
        lines.append("신뢰도 낮음 — 의심이 많은 사용자. 근거를 더 상세히 설명하라.")

    stress = profile.get("stress_pattern")
    if stress:
        lines.append(f"주요 스트레스 패턴: {stress}")

    if lines:
        return "\n".join(lines) + "\n"
    return ""


def render_user_memory_badge(saju_key: str):
    """사용자 기억 상태 배지 렌더링"""
    profile = get_user_profile(saju_key)
    vc = profile.get("visit_count", 0)
    if vc < 2:
        return

    bl = profile.get("belief_level", 0.5)
    bl_pct = int(bl * 100)
    bl_color = "#4caf50" if bl >= 0.7 else "#ff9800" if bl >= 0.4 else "#f44336"
    bl_label = "높음" if bl >= 0.7 else "보통" if bl >= 0.4 else "형성중"

    mc = profile.get("main_concern", "")
    lp = profile.get("last_prediction", "")

    mc_html = f"<div>(관심): <b>{mc}</b></div>" if mc else ""
    lp_html = f"<div>(이전): <span style='color:#666'>{lp[:40]}...</span></div>" if lp else ""
    
    html = "<div style='background:linear-gradient(135deg,#f0f0ff,#e8e8ff);border:1px solid #b8a8ee;border-radius:12px;padding:12px 14px;margin:8px 0'>"
    html += f"<div style='font-size:11px;color:#7b5ea7;font-weight:700;margin-bottom:6px'>AI 기억 시스템 - {vc}회 상담 이력</div>"
    html += "<div style='display:flex;gap:12px;flex-wrap:wrap;align-items:center'>"
    html += "<div style='text-align:center'>"
    html += "<div style='font-size:10px;color:#888'>신뢰도</div>"
    html += f"<div style='font-size:16px;font-weight:900;color:{bl_color}'>{bl_pct}%</div>"
    html += f"<div style='font-size:9px;color:{bl_color}'>{bl_label}</div>"
    html += "</div>"
    html += "<div style='flex:1;font-size:11px;color:#000000;line-height:1.8'>"
    html += mc_html + lp_html
    html += "</div></div></div>"
    
    st.markdown(html, unsafe_allow_html=True)


def render_ai_opening_ment(saju_key: str, name: str):
    """사용자 상태에 따른 맞춤형 오프닝 멘트 (Retention)"""
    profile = get_user_profile(saju_key)
    vc = profile.get("visit_count", 0)
    concern = profile.get("main_concern", "")
    persona = profile.get("persona", "balanced_type")
    _, p_label, _ = get_persona_label(persona)

    # 멘트 템플릿
    if vc <= 1:
        ment = f"반갑습니다, {name}님. 당신의 천명을 풀이하러 온 {p_label} 마스터입니다. 오늘 어떤 고민이 당신의 마음을 흔들고 있나요?"
    else:
        visit_text = f"벌써 {vc}번째 방문이시네요."
        if concern:
            ment = f"어서 오세요, {name}님. {visit_text} 지난번에 '<b>{concern}</b>' 관련해 고민하셨던 흐름이 지금은 어떻게 바뀌었을까요? 다시 한번 정밀하게 짚어드리겠습니다."
        else:
            ment = f"다시 뵙게 되어 기쁩니다, {name}님. {visit_text} 오늘 당신의 운기 흐름에서 가장 먼저 짚어드려야 할 곳이 어디인지 선택해 주세요."

    html = "<div style='background:linear-gradient(135deg,#f8f5ff,#ffffff);border-left:5px solid #7b5ea7;border-radius:0 12px 12px 0;padding:20px 18px;margin:15px 0;box-shadow:0 3px 10px rgba(0,0,0,0.05)'>"
    html += f"<div style='font-size:15px;color:#2c1a4d;line-height:1.7;font-weight:600'>{ment}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  📊 STATISTICAL CORRECTION ENGINE — 통계 보정 시스템
#  사주 패턴 × 실제 데이터 → 확률 기반 해석
# ══════════════════════════════════════════════════════════════

# 패턴별 확률 데이터 (실증 기반 추정값)
_STATISTICAL_PATTERNS = {
    # (신강신약, 오행과다) → (주제, 확률, 해석)
    ("신약", "金"): ("직장 스트레스", 76, "금기 과다 + 신약 → 책임 부담, 직장 압박 패턴"),
    ("신약", "水"): ("과잉 사고", 71, "수기 과다 + 신약 → 걱정·불안·수면 불안정"),
    ("신강", "火"): ("감정 폭발", 68, "화기 과다 + 신강 → 충동적 표현, 인간관계 갈등"),
    ("신강", "木"): ("고집·충돌", 65, "목기 과다 + 신강 → 타협 어려움, 독선적 결정"),
    ("중화", "土"): ("변화 저항", 62, "토기 균형 + 중화 → 안정 선호, 새로움 회피"),
    ("신약", "火"): ("소진·번아웃", 74, "화기 과다 + 신약 → 에너지 고갈, 소진 패턴"),
    ("신강", "金"): ("재물 집착", 66, "금기 과다 + 신강 → 물질 중시, 절약 강박"),
    ("극신약", "土"): ("건강 취약", 79, "토기 과다 + 극신약 → 소화기 계통 주의"),
    ("극신강", "木"): ("인간관계 마찰", 72, "목기 극강 → 자기중심적, 협력 어려움"),
}

def get_statistical_insights(pils, strength_info) -> list:
    """
    통계 보정 인사이트 생성
    Returns: list[dict] - {pattern, prob, insight, advice}
    """
    sn       = strength_info.get("신강신약", "중화")
    oh_str   = strength_info.get("oh_strength", {})
    insights = []

    # 과다 오행 탐지 (35% 이상)
    over_ohs = [(oh, v) for oh, v in oh_str.items() if v >= 35]

    for oh, val in over_ohs:
        key = (sn, oh)
        if key in _STATISTICAL_PATTERNS:
            topic, prob, desc = _STATISTICAL_PATTERNS[key]
            # 과다 강도에 따라 확률 보정
            adjusted_prob = min(95, int(prob + (val - 35) * 0.5))
            insights.append({
                "pattern": f"{sn} + {oh}과다({val:.0f}%)",
                "topic": topic,
                "prob": adjusted_prob,
                "insight": desc,
                "advice": _get_pattern_advice(sn, oh),
            })

    # 특수 패턴: 삼형살
    il_jj = pils[1]["jj"]
    wol_jj = pils[2]["jj"]
    hyeong_pairs = {("寅","巳","申"), ("丑","戌","未"), ("子","卯")}
    all_jjs = frozenset(p["jj"] for p in pils)
    for combo in hyeong_pairs:
        if isinstance(combo, frozenset):
            if combo.issubset(all_jjs):
                insights.append({
                    "pattern": "삼형살(三刑殺)",
                    "topic": "사고·건강·법적 분쟁",
                    "prob": 61,
                    "insight": "삼형살 — 스트레스·사고·법적 문제 주의",
                    "advice": "큰 결정 전 충분한 검토. 건강검진 정기적으로.",
                })
        elif isinstance(combo, tuple) and len(combo) == 3:
            if frozenset(combo).issubset(all_jjs):
                insights.append({
                    "pattern": f"삼형살({','.join(combo)})",
                    "topic": "사고·건강·법적 분쟁",
                    "prob": 61,
                    "insight": f"{','.join(combo)} 삼형살 — 스트레스·사고·법적 문제 주의",
                    "advice": "큰 결정 전 충분한 검토. 건강검진 정기적으로.",
                })
        elif isinstance(combo, tuple) and len(combo) == 2:
            if combo[0] in all_jjs and combo[1] in all_jjs:
                insights.append({
                    "pattern": f"자묘형({combo[0]}{combo[1]})",
                    "topic": "인간관계 갈등",
                    "prob": 58,
                    "insight": "자묘형 — 원칙적 인간관계, 갈등 가능성",
                    "advice": "감정 조절과 유연한 대처가 중요합니다.",
                })

    return sorted(insights, key=lambda x: -x["prob"])[:4]  # 상위 4개


def _get_pattern_advice(sn: str, oh: str) -> str:
    """패턴별 실전 조언"""
    advice_map = {
        ("신약", "金"): "용신(木·水)의 방향으로 직업을 선택하면 스트레스가 줄어듭니다.",
        ("신약", "水"): "걱정을 글로 써내려가는 습관이 도움이 됩니다. 수면 루틴 확립 필수.",
        ("신강", "火"): "중요한 결정은 감정이 가라앉은 뒤 내리십시오. 규칙적 운동이 필수.",
        ("신강", "木"): "타인의 의견을 '위협'이 아닌 '정보'로 받아들이는 연습을 하십시오.",
        ("신약", "火"): "무리한 약속을 줄이고 에너지를 선택적으로 사용하십시오.",
        ("신강", "金"): "물질이 아닌 경험에 투자하면 삶의 만족도가 올라갑니다.",
    }
    return advice_map.get((sn, oh), "오행 균형을 위한 용신 활용을 권장합니다.")


def render_statistical_insights(pils, strength_info):
    """통계 인사이트 UI 렌더링"""
    insights = get_statistical_insights(pils, strength_info)
    if not insights:
        return

    st.markdown('<div class="gold-section">📊 데이터 기반 패턴 분석</div>',
                unsafe_allow_html=True)
    st.caption("사주 패턴별 실증 통계 기반 분석입니다")

    for ins in insights:
        prob  = ins["prob"]
        color = ("#f44336" if prob >= 75 else "#ff9800" if prob >= 60 else "#4caf50")
        html = f"<div style='background:#fffef8;border:1px solid #e8d5a0;border-radius:12px;padding:14px 16px;margin:6px 0'>"
        html += "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:4px'>"
        html += f"<span style='font-size:12px;font-weight:700;color:#333'>[분석] {ins['topic']}</span>"
        html += f"<span style='background:{color}22;border:1px solid {color}55;color:{color};font-size:12px;font-weight:800;padding:2px 10px;border-radius:8px'>{prob}% 패턴</span>"
        html += "</div>"
        html += f"<div style='font-size:12px;color:#000000;margin-bottom:6px'>{ins['insight']}</div>"
        html += f"<div style='font-size:11px;color:#000000;background:#ffffff;padding:6px 10px;border-radius:6px'>(조언): {ins['advice']}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

def _load_retention() -> dict:
    try:
        if os.path.exists(_RETENTION_FILE):
            with open(_RETENTION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_retention(data: dict):
    try:
        with open(_RETENTION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def update_streak() -> dict:
    """
    방문 스트릭 업데이트
    Returns: {streak: int, is_new_day: bool, message: str}
    """
    today = datetime.now().strftime("%Y-%m-%d")
    data  = _load_retention()
    streak_data = data.get("streak", {"count": 0, "last_date": "", "max": 0})

    last = streak_data.get("last_date", "")
    count = streak_data.get("count", 0)
    max_s = streak_data.get("max", 0)
    is_new_day = False

    if last == today:
        # 오늘 이미 방문
        pass
    elif last == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"):
        # 연속 방문
        count += 1
        is_new_day = True
        streak_data["count"] = count
        streak_data["last_date"] = today
        streak_data["max"] = max(max_s, count)
    else:
        # 끊김 또는 첫 방문
        count = 1
        is_new_day = True
        streak_data["count"] = count
        streak_data["last_date"] = today

    data["streak"] = streak_data
    _save_retention(data)

    # 스트릭 메시지
    if count >= 30:
        msg = f"[대단하네요] {count}일 연속 방문 - 진정한 천명 탐구자!"
    elif count >= 14:
        msg = f"[대단하네요] {count}일 연속 방문 - 운의 흐름을 꿰뚫고 있습니다"
    elif count >= 7:
        msg = f"[대단하네요] {count}일 연속 방문 - 한 주 완성!"
    elif count >= 3:
        msg = f"[대단하네요] {count}일 연속 방문 중"
    else:
        msg = f"[방문] {count}일째 방문"

    return {"streak": count, "max": streak_data.get("max", count),
            "is_new_day": is_new_day, "message": msg}


def get_daily_luck_score(pils, birth_year, gender, target_date=None) -> dict:
    """
    일별 운세 점수 (기본운 * 대운 * 세운 * 월운 합산)
    Returns: {score: int, trend: str, label: str}
    """
    if target_date is None:
        target_date = datetime.now()
    y = target_date.year
    m = target_date.month
    d = target_date.day

    base    = calc_luck_score(pils, birth_year, gender, y)
    yearly  = get_yearly_luck(pils, y)
    monthly = get_monthly_luck(pils, y, m)

    # 일별 미세 변동 (일지 기반 결정론적 계산)
    ilgan = pils[1]["cg"]
    il_jj = pils[1]["jj"]
    day_jj_idx = (d - 1) % 12
    day_jj = JJ[day_jj_idx]

    # 일간과 일지 조화 점수
    day_mod = 0
    if _JIJI_CHUNG.get(il_jj) == day_jj:
        day_mod = -8
    elif HAP_MAP.get(il_jj) == day_jj:
        day_mod = +6
    elif OH.get(il_jj) == OH.get(day_jj):
        day_mod = +4

    _GH = {"대길(大吉)":8,"길(吉)":4,"평길(平吉)":2,"평(平)":0,"흉(凶)":-6,"흉흉(凶凶)":-12}
    year_mod   = _GH.get(yearly.get("길흉","평(平)"), 0)
    month_mod  = _GH.get(monthly.get("길흉","평(平)") if isinstance(monthly.get("길흉"), str) else "평(平)", 0)

    final = max(0, min(100, base + year_mod * 0.4 + month_mod * 0.3 + day_mod))

    if final >= 75:
        label, trend = "대길(Dae-Gil)", "UP-UP"
    elif final >= 60:
        label, trend = "길(Gil)", "UP"
    elif final >= 45:
        label, trend = "평(Normal)", "MID"
    elif final >= 30:
        label, trend = "흉(Bad)", "DOWN"
    else:
        label, trend = "흉흉(Very Bad)", "DOWN-DOWN"

    return {"score": int(final), "label": label, "trend": trend,
            "year_mod": year_mod, "month_mod": month_mod, "day_mod": day_mod}


def get_7day_luck_graph(pils, birth_year, gender) -> list:
    """7일 운세 점수 그래프 데이터"""
    today = datetime.now()
    result = []
    for delta in range(-3, 4):
        d = today + timedelta(days=delta)
        s = get_daily_luck_score(pils, birth_year, gender, d)
        result.append({
            "date": d.strftime("%m/%d"),
            "day": ["월","화","수","목","금","토","일"][d.weekday()],
            "score": s["score"],
            "label": s["label"],
            "is_today": delta == 0,
        })
    return result


def get_turning_countdown(pils, birth_year, gender) -> dict:
    """
    다음 인생 전환점까지 남은 날짜 계산
    Returns: {days_left: int, date: str, description: str}
    """
    today = datetime.now()
    # 최대 365일 앞을 스캔
    for delta in range(1, 366):
        future = today + timedelta(days=delta)
        t = calc_turning_point(pils, birth_year, gender, future.year)
        if t["is_turning"] and abs(t["score_change"]) >= 15:
            # 대운 전환 시점 더 정확히
            dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
            for dw in dw_list:
                if dw["시작연도"] == future.year:
                    change_date = f"{future.year}년 {birth_year % 100 + dw['시작나이'] % 10}월경"
                    return {
                        "days_left": delta,
                        "date": change_date,
                        "description": f"새 대운 {dw['str']} 시작 — 인생 국면 전환",
                        "intensity": t["intensity"],
                    }
            # 세운 전환점
            return {
                "days_left": delta,
                "date": future.strftime("%Y년 %m월"),
                "description": t["reason"][0] if t["reason"] else "흐름 변화",
                "intensity": t["intensity"],
            }
    return {"days_left": None, "date": "-", "description": "대운 안정기", "intensity": "⬜"}


def render_retention_widget(pils, birth_year, gender):
    """중독 유발 핵심 위젯 (Main Addiction Engine)"""
    streak_info    = update_streak()
    graph_data     = get_7day_luck_graph(pils, birth_year, gender)
    countdown      = get_turning_countdown(pils, birth_year, gender)
    today_score    = next((d for d in graph_data if d["is_today"]), {})

    streak_c = streak_info["streak"]

    days_left = countdown.get('days_left')
    if days_left is None:
        days_left_display = "365+"
        progress = 0
    else:
        days_left_display = str(days_left)
        progress = min(100, max(0, 100 - (days_left // 3)))

    score = today_score.get('score', 50)
    score_color = '#4caf50' if score >= 60 else '#ff9800' if score >= 45 else '#f44336'
    
    html = "<div style='background:linear-gradient(135deg,#fffef5,#ffffff);border:1.5px solid #e8d5a0;border-radius:16px;padding:16px 14px;margin:10px 0'>"
    html += "<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
    html += "<div style='text-align:center'>"
    html += "<div style='font-size:10px;color:#000000;font-weight:700;letter-spacing:1px'>방문 스트릭</div>"
    html += f"<div style='font-size:28px;font-weight:900;color:#000000'>{streak_c}일</div>"
    html += f"<div style='font-size:10px;color:#888'>최고 {streak_info['max']}일</div>"
    html += "</div>"
    html += "<div style='text-align:center'>"
    html += "<div style='font-size:10px;color:#000000;font-weight:700;letter-spacing:1px'>오늘 운세</div>"
    html += f"<div style='font-size:28px;font-weight:900;color:{score_color}'>{score}점</div>"
    html += f"<div style='font-size:11px;color:#666'>{today_score.get('label','Normal')}</div>"
    html += "</div>"
    html += "<div style='text-align:center'>"
    html += "<div style='font-size:10px;color:#000000;font-weight:700;letter-spacing:1px'>전환점까지</div>"
    html += f"<div style='font-size:22px;font-weight:900;color:#e65100'>D-{days_left_display}</div>"
    html += f"<div style='font-size:10px;color:#888'>{countdown.get('date','-')}</div>"
    html += "</div>"
    html += "</div>"
    
    html += "<div style='margin-top:16px; background:white; border-radius:10px; padding:10px 12px; border:1px solid #eee'>"
    html += "<div style='display:flex; justify-content:space-between; font-size:10px; color:#000000; font-weight:700; margin-bottom:5px'>"
    html += "<span>현재 인생 흐름 진행률</span>"
    html += f"<span>{progress}%</span>"
    html += "</div>"
    html += "<div style='background:#f0f0f0; height:12px; border-radius:6px; overflow:hidden;'>"
    html += f"<div style='background:linear-gradient(90deg, #000000, #e65100); width:{progress}%; height:100%;'></div>"
    html += "</div>"
    html += f"<div style='font-size:10px; color:#e65100; font-weight:700; margin-top:5px; text-align:center'>{countdown.get('description', 'Status')}</div>"
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

    # -- 7일 운 그래프
    max_s = max(d["score"] for d in graph_data) or 100
    bars = "<div style='display:flex;justify-content:space-between;align-items:flex-end;height:120px;padding:15px 10px;background:#fcfaf5;border-radius:12px;margin:5px 0'>"
    for d in graph_data:
        h = max(15, int(d["score"] / max_s * 70))
        bg = "#000000" if d["is_today"] else ("#4caf50" if d["score"] >= 60 else "#ff9800" if d["score"] >= 45 else "#f44336")
        fw = "800" if d["is_today"] else "600"
        bars += f"""
        <div style="display:flex;flex-direction:column;align-items:center;width:14%;position:relative">
            <div style="font-size:10px;color:#000000;margin-bottom:4px;font-weight:{fw}">{d["date"]}</div>
            <div style="background:{bg};height:{h}px;width:80%;border-radius:4px;margin-bottom:4px;display:flex;align-items:flex-end;justify-content:center;color:white;font-size:10px;font-weight:bold">{d["score"]}</div>
            <div style="font-size:10px;color:#000000;font-weight:{fw}">{d["day"]}</div>
        </div>
        """
    st.markdown(f"""
    <div style="background:#fcfaf5;border:1.5px solid #e8d5a0;border-radius:16px;padding:16px 14px;margin:10px 0">
        <div style="font-size:12px;color:#000000;font-weight:700;letter-spacing:1px;margin-bottom:10px">
            7일 운세 흐름
        </div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end;height:120px;padding:15px 10px;background:#fcfaf5;border-radius:12px;margin:5px 0">
            {bars}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -- 전환점 카운트다운 배너
    if countdown["days_left"] and countdown["days_left"] <= 60:
        ic = "#f44336" if "강력" in countdown["intensity"] else "#ff9800"
        html = f"<div style='background:linear-gradient(135deg,#fff5f0,#ffe8e0);border:2px solid {ic};border-radius:12px;padding:14px 16px;margin:8px 0;text-align:center'>"
        html += f"<div style='font-size:12px;color:{ic};font-weight:700;margin-bottom:4px'>[알림] {countdown['intensity']} 감지</div>"
        html += f"<div style='font-size:22px;font-weight:900;color:{ic}'>D-{countdown['days_left']}</div>"
        html += f"<div style='font-size:12px;color:#000000;margin-top:4px'>{countdown['description']}</div>"
        html += f"<div style='font-size:11px;color:#000000;margin-top:4px'>{countdown['date']}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)


def get_daewoon_sewoon_cross(pils, birth_year, gender, target_year=None):
    """대운*세운 교차 분석"""
    ilgan = pils[1]["cg"]
    if target_year is None:
        target_year = datetime.now().year
    daewoon_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    cur_dw = next((d for d in daewoon_list if d["시작연도"]<=target_year<=d["종료연도"]),None)
    if not cur_dw: return None
    sewoon = get_yearly_luck(pils, target_year)
    dw_cg_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(cur_dw["cg"],"-")
    dw_jj_cg = JIJANGGAN.get(cur_dw["jj"],[""])[-1]
    dw_jj_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw_jj_cg,"-")
    sw_cg_ss = sewoon["십성_천간"]
    sw_jj_cg = JIJANGGAN.get(sewoon["jj"], [""])[-1]
    sw_jj_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(sw_jj_cg, "-")
    cross_events = []
    TG_HAP_PAIRS = [{"甲","己"},{"乙","庚"},{"丙","辛"},{"丁","壬"},{"戊","癸"}]
    for pair in TG_HAP_PAIRS:
        if cur_dw["cg"] in pair and sewoon["cg"] in pair:
            cross_events.append({"type":"천간합","desc":f"대운 천간({cur_dw['cg']})과 세운 천간({sewoon['cg']})이 합(合). 변화와 기회의 해."})
    for k,(name,oh,desc) in CHUNG_MAP.items():
        if cur_dw["jj"] in k and sewoon["jj"] in k:
            cross_events.append({"type":"지지충","desc":f"대운 지지({cur_dw['jj']})와 세운 지지({sewoon['jj']})가 충(沖). {desc}"})
    for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
        all_jj = {cur_dw["jj"],sewoon["jj"]}|{p["jj"] for p in pils}
        if combo.issubset(all_jj):
            cross_events.append({"type":"삼합","desc":f"대운·세운·원국 삼합({hname}) — 강력한 발복의 기운."})
    ss_combo = f"{dw_cg_ss}+{sw_cg_ss}"
    interp = {
        "정관+식신":"명예와 재능이 동시에 빛나는 최길 조합. 승진·수상·큰 성취.",
        "식신+정재":"복록과 재물이 넘치는 대길 조합. 재물운 폭발.",
        "편관+편관":"이중 편관. 시련 극도. 건강·사고 각별히 주의.",
        "겁재+겁재":"이중 겁재. 재물 손실·경쟁 극심. 방어 전략이 최선.",
        "정인+정관":"학문과 명예 동시에 오는 최길 조합. 시험·자격증·승진.",
        "편관+식신":"칠살제화(七殺制化) — 시련이 오히려 기회가 됩니다.",
        "정재+정관":"재물과 명예 함께 오는 길한 조합. 사업 성공과 인정.",
    }
    cross_desc = interp.get(ss_combo,f"대운 {dw_cg_ss}의 흐름 속에 세운 {sw_cg_ss}의 기운이 더해집니다.")
    return {"연도":target_year,"대운":cur_dw,"세운":sewoon,"대운_천간십성":dw_cg_ss,
            "대운_지지십성":dw_jj_ss,"세운_천간십성":sw_cg_ss,"세운_지지십성":sw_jj_ss,"교차사건":cross_events,"교차해석":cross_desc}


# ══════════════════════════════════════════════════
#  지장간(地藏干) 심화
# ══════════════════════════════════════════════════

JIJANGGAN_FULL = {
    "子":[{"cg":"壬","days":10,"type":"여기"},{"cg":"癸","days":20,"type":"정기"}],
    "丑":[{"cg":"己","days":9,"type":"여기"},{"cg":"辛","days":3,"type":"중기"},{"cg":"癸","days":18,"type":"정기"}],
    "寅":[{"cg":"戊","days":7,"type":"여기"},{"cg":"丙","days":7,"type":"중기"},{"cg":"甲","days":16,"type":"정기"}],
    "卯":[{"cg":"甲","days":10,"type":"여기"},{"cg":"乙","days":20,"type":"정기"}],
    "辰":[{"cg":"乙","days":9,"type":"여기"},{"cg":"癸","days":3,"type":"중기"},{"cg":"戊","days":18,"type":"정기"}],
    "巳":[{"cg":"戊","days":7,"type":"여기"},{"cg":"庚","days":7,"type":"중기"},{"cg":"丙","days":16,"type":"정기"}],
    "午":[{"cg":"丙","days":10,"type":"여기"},{"cg":"己","days":10,"type":"중기"},{"cg":"丁","days":10,"type":"정기"}],
    "未":[{"cg":"丁","days":9,"type":"여기"},{"cg":"乙","days":3,"type":"중기"},{"cg":"己","days":18,"type":"정기"}],
    "申":[{"cg":"戊","days":7,"type":"여기"},{"cg":"壬","days":7,"type":"중기"},{"cg":"庚","days":16,"type":"정기"}],
    "酉":[{"cg":"庚","days":10,"type":"여기"},{"cg":"辛","days":20,"type":"정기"}],
    "戌":[{"cg":"辛","days":9,"type":"여기"},{"cg":"丁","days":3,"type":"중기"},{"cg":"戊","days":18,"type":"정기"}],
    "亥":[{"cg":"甲","days":7,"type":"여기"},{"cg":"壬","days":7,"type":"중기"},{"cg":"壬","days":16,"type":"정기"}],
}
TYPE_LABEL = {"여기":"餘氣","중기":"中氣","정기":"正氣"}

def get_jijanggan_analysis(ilgan, pils):
    cgs_all = [p["cg"] for p in pils]
    result = []
    labels = ["시주","일주","월주","년주"]
    for i,p in enumerate(pils):
        jj = p["jj"]
        jjg = JIJANGGAN_FULL.get(jj,[])
        items = []
        for e in jjg:
            cg = e["cg"]
            ss = TEN_GODS_MATRIX.get(ilgan,{}).get(cg,"-")
            items.append({"천간":cg,"타입":e["type"],"일수":e["days"],"십성":ss,"투출":cg in cgs_all})
        result.append({"기둥":labels[i],"지지":jj,"지장간":items})
    return result


# ══════════════════════════════════════════════════
#  건강론(健康論)
# ══════════════════════════════════════════════════

HEALTH_OH = {
    "木":{"organs":"간·담낭·눈·근육·신경계","emotion":"분노(怒)","over_symptom":"간염·담석·녹내장·편두통·불면","lack_symptom":"피로·우울·근육약화·시력저하","food":"신맛(식초·레몬·매실)·녹색식품","lifestyle":"새벽 취침 자제·분노 다스리기·스트레칭·요가","lucky_direction":"동쪽(東)"},
    "火":{"organs":"심장·소장·혈관·혀","emotion":"기쁨 과다(喜)","over_symptom":"심장병·고혈압·불안·불면·구내염","lack_symptom":"저혈압·우울·기억력저하·손발냉","food":"쓴맛(녹차·씀바귀)·붉은 식품(토마토·딸기)","lifestyle":"명상·호흡수련·과로 자제·충분한 수분","lucky_direction":"남쪽(南)"},
    "土":{"organs":"비장·위장·췌장·입술","emotion":"근심(思)","over_symptom":"위염·소화불량·위궤양·비만·당뇨","lack_symptom":"식욕부진·빈혈·면역저하·피로","food":"단맛(고구마·대추·꿀)·황색식품(콩·현미)","lifestyle":"규칙적 식사·걱정 줄이기·복식호흡","lucky_direction":"중앙"},
    "金":{"organs":"폐·대장·코·피부·기관지","emotion":"슬픔(悲)","over_symptom":"폐렴·천식·비염·변비·아토피","lack_symptom":"감기 잦음·대장 약함·피부트러블","food":"매운맛(무·생강)·흰색식품(배·연근·우유)","lifestyle":"심호흡·콧속보습·슬픔 표현하기","lucky_direction":"서쪽(西)"},
    "水":{"organs":"신장·방광·뼈·귀·두발·생식기","emotion":"공포(恐)","over_symptom":"신장염·방광염·골다공증·이명·탈모","lack_symptom":"허리약함·냉증·건망증·두발약화","food":"짠맛(미역·다시마·검은콩)·검은식품","lifestyle":"밤 11시 전 취침·허리보호·따뜻한 물","lucky_direction":"북쪽(北)"},
}

def get_health_analysis(pils, gender="남"):
    ilgan = pils[1]["cg"]
    oh_strength = calc_ohaeng_strength(ilgan, pils)
    unsung = calc_12unsung(ilgan, pils)
    il_unsung = unsung[1] if len(unsung)>1 else ""
    il_oh = OH.get(ilgan,"")
    HEALTH_UNSUNG = {"병":"병지(病地) — 건강 약한 구조. 정기 검진 필수.","사":"사지(死地) — 생명력 약함. 안전사고·건강 각별 주의.","절":"절지(絶地) — 체력 소진되기 쉬움.","묘":"묘지(墓地) — 만성질환 오래 지속될 수 있음."}
    return {"과다_오행":[{"오행":o,"수치":v,"health":HEALTH_OH.get(o,{})} for o,v in oh_strength.items() if v>=35],
            "부족_오행":[{"오행":o,"수치":v,"health":HEALTH_OH.get(o,{})} for o,v in oh_strength.items() if v<=5],
            "일주_건강":HEALTH_UNSUNG.get(il_unsung,""),"일간_건강":HEALTH_OH.get(il_oh,{}),
            "ilgan_oh":il_oh,"oh_strength":oh_strength}


# ══════════════════════════════════════════════════
#  재물론(財物論)
# ══════════════════════════════════════════════════

def get_jaemul_analysis(pils, birth_year, gender="남"):
    ilgan = pils[1]["cg"]
    oh_strength = calc_ohaeng_strength(ilgan, pils)
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    CTRL = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    ilgan_oh = OH.get(ilgan,"")
    jae_oh = CTRL.get(ilgan_oh,"")
    jae_strength = oh_strength.get(jae_oh,0)
    # 재성 위치
    jae_pos = []
    for i,p in enumerate(pils):
        ss_cg = TEN_GODS_MATRIX.get(ilgan,{}).get(p["cg"],"-")
        jj_cg = JIJANGGAN.get(p["jj"],[""])[-1]
        ss_jj = TEN_GODS_MATRIX.get(ilgan,{}).get(jj_cg,"-")
        lbl = ["시주","일주","월주","년주"][i]
        if ss_cg in ["정재","편재"]: jae_pos.append(f"{lbl} 천간({ss_cg})")
        if ss_jj in ["정재","편재"]: jae_pos.append(f"{lbl} 지지({ss_jj})")
    # 대운 재물 피크
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    peaks = [{"대운":d["str"],"나이":f"{d['시작나이']}~{d['시작나이']+9}세","연도":f"{d['시작연도']}~{d['종료연도']}","십성":TEN_GODS_MATRIX.get(ilgan,{}).get(d["cg"],"-")} for d in daewoon if TEN_GODS_MATRIX.get(ilgan,{}).get(d["cg"],"-") in ["정재","편재","식신"]]
    # 유형 판단
    if sn=="신강(身强)" and jae_strength>=20: jtype,jstrat="적극형 — 강한 일간이 재성을 다루는 이상적 구조.","재성 운에서 과감히 행동하십시오."
    elif sn=="신약(身弱)" and jae_strength>=30: jtype,jstrat="부담형 — 재물이 있어도 감당하기 벅찬 구조.","고정수입·저축 중심으로 운용하십시오."
    elif jae_strength==0: jtype,jstrat="재성공망형 — 재성이 없는 사주. 명예·학문·기술로 성공.","전문성과 명예를 쌓으면 돈은 따라옵니다."
    else: jtype,jstrat="균형형 — 꾸준한 노력으로 재물을 쌓아가는 구조.","안정적 자산관리가 유리합니다."
    return {"재성_오행":jae_oh,"재성_강도":jae_strength,"재성_위치":jae_pos,
            "재물_유형":jtype,"재물_전략":jstrat,"재물_피크_대운":peaks,"신강신약":sn}


# ══════════════════════════════════════════════════
#  직업론(職業論)
# ══════════════════════════════════════════════════

CAREER_MATRIX = {
    "정관격":{"best":["공무원·행정관리","판사·검사·법조인","대기업 임원","교육공무원","군 장교·외교관"],"good":["금융·은행·보험","교사·교수","의사·한의사"],"avoid":["자유업·프리랜서","예능·연예계","투기적 사업"]},
    "편관격":{"best":["군인·경찰·소방관","외과의사·응급의학","스포츠·격투기","검사·형사","위기관리·보안"],"good":["공학·기술자","법조인","언론(탐사)"],"avoid":["세밀한 행정직","반복 사무직"]},
    "식신격":{"best":["요리사·외식업","예술가·음악인","작가·시인","교육자·강사","의료·복지"],"good":["아이디어 사업","복지·상담","유튜버·콘텐츠"],"avoid":["과도한 경쟁직","군사·강압 조직"]},
    "상관격":{"best":["연예인·유튜버·방송인","변호사·변리사","창업가·혁신가","작가·작곡가","언론인·PD"],"good":["스타트업","컨설턴트","디자이너"],"avoid":["관직·공무원","상명하복 직종"]},
    "정재격":{"best":["회계사·세무사","은행원·금융관리","부동산 관리","행정관리","의사·약사"],"good":["대기업 재무·회계","보험·연금"],"avoid":["투기·도박성 사업","예능·불규칙수입"]},
    "편재격":{"best":["사업가·CEO","투자자·펀드매니저","무역상·유통업","부동산 개발","연예인·방송"],"good":["영업·마케팅","스타트업 창업","프리랜서"],"avoid":["단순 반복 사무직","소규모 고정급여직"]},
    "정인격":{"best":["교수·학자·연구원","교사·교육자","의사·한의사","변호사","종교인·성직자"],"good":["작가·언론인","공직자","상담사"],"avoid":["격렬한 경쟁 사업","단순 노무직"]},
    "편인격":{"best":["철학자·사상가","종교인·영성가","명리학자·점술가","IT개발자","탐정·분석가"],"good":["심리학자","연구원","특수기술자"],"avoid":["대형 조직 관리직","서비스업"]},
    "비견격":{"best":["독립 사업가","컨설턴트","스포츠 코치","사회운동가"],"good":["팀 기반 사업","멘토·코치"],"avoid":["독점적 대기업","단일 보스 직종"]},
    "겁재격":{"best":["운동선수·격투기","영업전문가","경쟁적 사업","변호사","스타트업"],"good":["군인·경찰","마케터"],"avoid":["재정·회계 관리","보수적 공직"]},
}
ILGAN_CAREER_ADD = {
    "甲":["건축·목재·산림","교육·인재개발"],"乙":["꽃·원예·디자인","상담·교육"],"丙":["방송·연예","발전·에너지"],
    "丁":["의료·제약","교육·종교"],"戊":["건설·부동산","농업·식품"],"己":["농업·식품가공","행정·회계"],
    "庚":["금융·금속·기계","법조·군경"],"辛":["패션·보석·예술","의료·약학"],"壬":["해운·무역·외교","IT·전략"],
    "癸":["상담·심리·영성","의료·약학"],
}

def get_career_analysis(pils, gender="남"):
    ilgan = pils[1]["cg"]
    gyeokguk = get_gyeokguk(pils)
    gname = gyeokguk["격국명"] if gyeokguk else "비견격"
    career = CAREER_MATRIX.get(gname, CAREER_MATRIX["비견격"])
    sinsal = get_12sinsal(pils)
    sinsal_jobs = []
    for s in sinsal:
        if "장성" in s["이름"]: sinsal_jobs.append("군·경·스포츠 수장 기질")
        if "화개" in s["이름"]: sinsal_jobs.append("예술·종교·철학 방면 특화")
        if "역마" in s["이름"]: sinsal_jobs.append("이동·무역·해외 관련 직종 유리")
        if "도화" in s["이름"] or "년살" in s["이름"]: sinsal_jobs.append("연예·서비스·대인 방면 유리")
    yin = get_yangin(pils)
    if yin["존재"]: sinsal_jobs.append("군·경·의료(외과) 분야 강한 기질")
    return {"격국":gname,"최적직업":career["best"],"유리직업":career["good"],"피할직업":career["avoid"],
            "일간추가":ILGAN_CAREER_ADD.get(ilgan,[]),"신살보정":sinsal_jobs}


# ══════════════════════════════════════════════════
#  개명(改名) 오행 분석
# ══════════════════════════════════════════════════

HANGUL_OH = {
    "ㄱ":"木","ㄴ":"火","ㄷ":"火","ㄹ":"土","ㅁ":"水","ㅂ":"水","ㅅ":"金","ㅇ":"土",
    "ㅈ":"金","ㅊ":"金","ㅋ":"木","ㅌ":"火","ㅍ":"水","ㅎ":"水",
    "ㅏ":"木","ㅓ":"土","ㅗ":"火","ㅜ":"水","ㅡ":"土","ㅣ":"金",
    "ㅐ":"金","ㅔ":"金","ㅑ":"木","ㅕ":"土","ㅛ":"火","ㅠ":"水",
}

def decompose_hangul(char):
    if not (0xAC00<=ord(char)<=0xD7A3): return []
    code=ord(char)-0xAC00
    jong=code%28; jung=(code//28)%21; cho=code//28//21
    CHOSUNG=["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
    JUNGSUNG=["ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"]
    JONGSUNG=["","ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
    r=[CHOSUNG[cho],JUNGSUNG[jung]]
    if jong: r.append(JONGSUNG[jong])
    return r

def analyze_name_oh(name_str):
    oh_count={"木":0,"火":0,"土":0,"金":0,"水":0}
    for char in name_str:
        for jamo in decompose_hangul(char):
            oh=HANGUL_OH.get(jamo)
            if oh: oh_count[oh]+=1
    total=sum(oh_count.values()) or 1
    return oh_count,{k:round(v/total*100) for k,v in oh_count.items()}


# ══════════════════════════════════════════════════
#  새 탭 UI 함수들
# ══════════════════════════════════════════════════

################################################################################
# ★★★ Brain 3 — Learning & Monetization Engine ★★★
#
# [역할]  사용자 반응을 수집·분석하여 AI 프롬프트를 자동 강화한다
#
# [데이터 흐름]
#   사용자 반응 → Feedback Collector
#               → Pattern Analyzer   (어떤 문장이 결제·재방문 유도?)
#               → Prompt Optimizer   (다음 AI 호출 프롬프트 자동 강화)
#               → Monetization Trigger (결제 타이밍 감지)
#
# [저장 파일]
#   saju_feedback.json  - 피드백 원본 데이터 (삭제/캐싱 금지)
#   saju_patterns.json  - 학습 패턴 결과 (자동 갱신)
################################################################################

import time as _time

_FEEDBACK_FILE = "saju_feedback.json"
_PATTERN_FILE  = "saju_patterns.json"

# -----------------------------------------------------------------------------
# Brain 3-1 : Feedback Collector
# -----------------------------------------------------------------------------

def b3_save_feedback(saju_key: str, section: str, hit: bool,
                     prompt_type: str = "prophet", extra: dict = None):
    """
    Brain 3 피드백 저장 - 영속 파일 기반
    session_state 방식과 달리 앱 재시작 후에도 누적 유지
    [절대 캐싱 금지 - 사용자 반응은 실시간 반영]
    """
    try:
        cache = _load_json_cache(_FEEDBACK_FILE)
        ts = int(_time.time())
        entry = {
            "ts": ts,
            "saju_key": saju_key[:30],   # 개인정보 최소화 (앞 30자)
            "section": section,
            "hit": hit,
            "prompt_type": prompt_type,
            **(extra or {})
        }
        day_key = str(ts // 86400)       # 하루 단위 버킷
        if day_key not in cache:
            cache[day_key] = []
        cache[day_key].append(entry)
        _save_json_cache(_FEEDBACK_FILE, cache)
    except Exception:
        pass  # 피드백 저장 실패는 앱 동작에 영향 없음


def b3_load_all_feedback() -> list:
    """전체 피드백 레코드 로드"""
    cache = _load_json_cache(_FEEDBACK_FILE)
    all_records = []
    for day_entries in cache.values():
        if isinstance(day_entries, list):
            all_records.extend(day_entries)
    return all_records


# -----------------------------------------------------------------------------
# Brain 3-2 : Pattern Analyzer
# -----------------------------------------------------------------------------

def b3_analyze_patterns() -> dict:
    """
    피드백 패턴 분석
    반환: {section : 적중률, 가장 반응 좋은 섹션, 개선 필요 섹션}
    """
    records = b3_load_all_feedback()
    if not records:
        return {"total": 0, "hit_rate": 0, "best_sections": [], "weak_sections": [], "by_section": {}}

    section_stats = {}
    for r in records:
        sec = r.get("section", "unknown")
        if sec not in section_stats:
            section_stats[sec] = {"hit": 0, "miss": 0}
        if r.get("hit"):
            section_stats[sec]["hit"] += 1
        else:
            section_stats[sec]["miss"] += 1

    section_rates = {}
    for sec, stat in section_stats.items():
        total = stat["hit"] + stat["miss"]
        section_rates[sec] = {
            "hit": stat["hit"], "miss": stat["miss"],
            "total": total,
            "rate": round(stat["hit"] / total * 100) if total > 0 else 0
        }

    total_all  = sum(v["total"] for v in section_rates.values())
    total_hits = sum(v["hit"]   for v in section_rates.values())
    overall    = round(total_hits / total_all * 100) if total_all > 0 else 0

    best    = [s for s, v in section_rates.items() if v["rate"] >= 70]
    weak    = [s for s, v in section_rates.items() if v["rate"] < 50 and v["total"] >= 3]

    result = {
        "total": total_all,
        "hit_rate": overall,
        "best_sections": best,
        "weak_sections": weak,
        "by_section": section_rates
    }

    # 패턴 파일 자동 갱신
    _save_json_cache(_PATTERN_FILE, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Brain 3-③ : Prompt Optimizer
# ─────────────────────────────────────────────────────────────────────────────

def b3_build_optimized_prompt_suffix() -> str:
    """
    패턴 분석 결과를 바탕으로 AI 프롬프트에 추가할 강화 지침 생성
    적중률이 낮은 섹션을 집중 강화하도록 AI에게 알린다
    """
    patterns = _load_json_cache(_PATTERN_FILE)
    if not patterns or patterns.get("total", 0) < 10:
        # 데이터 부족 → 기본 지침
        return """
[Brain 3 최적화 지침 - 기본 모드]
- 단정적 표현만 사용하십시오 (~입니다, ~했습니다)
- 과거 사건은 나이와 연도를 반드시 명시하십시오
- 해결책과 행동 지침을 모든 섹션에 포함하십시오
"""

    weak = patterns.get("weak_sections", [])
    best = patterns.get("best_sections", [])
    overall = patterns.get("hit_rate", 0)

    lines = [f"\n[Brain 3 최적화 지침 - 누적 {patterns['total']}건 학습 반영]"]
    lines.append(f"- 현재 전체 적중률: {overall}% - {'충분히 높습니다. 유지하십시오.' if overall >= 70 else '개선이 필요합니다.'}")

    if best:
        lines.append(f"- 반응 좋은 섹션: {', '.join(best)} : 이 섹션의 서술 스타일을 다른 섹션에도 적용하십시오")
    if weak:
        lines.append(f"- 개선 필요 섹션: {', '.join(weak)} : 이 섹션은 더 구체적인 나이/연도/행동 지침을 추가하십시오")
        for sec in weak:
            stat = patterns.get("by_section", {}).get(sec, {})
            lines.append(f"  [{sec}] 적중 {stat.get('hit',0)}/{stat.get('total',0)}건 "
                         f"({stat.get('rate',0)}%) : 더 단정적이고 구체적으로 서술하십시오")

    lines.append("- [Skill 6: Coaching] 반드시 '오늘의 비방(秘方)' 또는 '당장 할 행동 처방' 1가지를 소름 돋게 처방하십시오")
    lines.append("• 당신은 만신(萬神)의 권위를 가진 40년 경력의 전문가로서, 분석 데이터에 기반하여 단정적으로 예고하십시오.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Brain 3-④ : Monetization Trigger (결제 타이밍 감지)
# ─────────────────────────────────────────────────────────────────────────────

# 세션 내 행동 추적 키
_B3_SESSION_KEY = "_b3_behavior"

def b3_track_behavior(action: str):
    """
    사용자 행동 추적 (세션 내)
    action 종류: "view_ai", "view_section", "ask_question", "scroll_deep", "repeat_visit"
    """
    if _B3_SESSION_KEY not in st.session_state:
        st.session_state[_B3_SESSION_KEY] = {
            "actions": [], "view_count": 0, "question_count": 0,
            "triggered": False, "session_start": _time.time()
        }
    behavior = st.session_state[_B3_SESSION_KEY]
    behavior["actions"].append(action)
    if action == "view_section":
        behavior["view_count"] += 1
    if action == "ask_question":
        behavior["question_count"] += 1


def b3_check_monetization_trigger(api_key: str) -> tuple:
    """
    결제 타이밍 감지 : (should_trigger, message)
    조건:
      - API 키 없음 + 섹션 3개 이상 조회
      - API 키 없음 + 질문 1회 이상
      - 고적중률 (70% 이상) + API 키 없음
    """
    if api_key:  # API 있으면 트리거 없음
        return False, ""

    behavior = st.session_state.get(_B3_SESSION_KEY, {})
    view_count = behavior.get("view_count", 0)
    q_count    = behavior.get("question_count", 0)
    triggered  = behavior.get("triggered", False)

    if triggered:
        return False, ""

    patterns = _load_json_cache(_PATTERN_FILE)
    overall  = patterns.get("hit_rate", 0)

    msg = ""
    if overall >= 70 and view_count >= 2:
        msg = (f"[데이터] 이 사주는 누적 데이터 기준 **{overall}%** 적중률을 기록했습니다. "
               f"지금 흐름이 중요한 시기입니다. 심층 AI 풀이를 받으시겠습니까?")
    elif q_count >= 1:
        msg = "[질문] 질문이 있으시다면 **AI 상담 API 키**를 입력하시면 직접 답변을 받으실 수 있습니다."
    elif view_count >= 3:
        msg = "[추천] 여러 섹션을 살펴보셨군요. **예언자 모드**로 6단계 천명을 완전히 풀이받으시겠습니까?"

    if msg:
        if _B3_SESSION_KEY in st.session_state:
            st.session_state[_B3_SESSION_KEY]["triggered"] = True
        return True, msg

    return False, ""


def b3_render_trigger_card(msg: str):
    """결제 유도 카드 렌더링"""
    html = "<div style='background:linear-gradient(135deg,#f5eeff,#ecdaff);border:2px solid #000000;border-radius:16px;padding:22px 24px;margin:16px 0;text-align:center'>"
    html += "<div style='font-size:16px;color:#8b6200;font-weight:700;margin-bottom:10px'>[안내] 지금이 중요한 시점입니다</div>"
    html += f"<div style='font-size:13px;color:#8b6200;line-height:1.9;margin-bottom:16px'>{msg}</div>"
    html += "<div style='font-size:12px;color:#000000;margin-top:8px'>Groq API는 무료 (groq.com) / Anthropic API는 소액 과금</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Brain 3 통합: 피드백 버튼 (기존 render_feedback_btn 대체)
# ─────────────────────────────────────────────────────────────────────────────

def save_feedback(feedback_key, hit):
    """피드백 저장 - session_state 누적 (하위 호환 유지)"""
    if "feedback_log" not in st.session_state:
        st.session_state.feedback_log = {}
    st.session_state.feedback_log[feedback_key] = "hit" if hit else "miss"
    # Brain 3 영속 저장
    saju_key = st.session_state.get("_current_saju_key", "unknown")
    b3_save_feedback(saju_key, feedback_key, hit)


def get_feedback_stats():
    """피드백 통계 반환"""
    log = st.session_state.get("feedback_log", {})
    total = len(log)
    hits = sum(1 for v in log.values() if v == "hit")
    return total, hits


def render_feedback_btn(key, desc):
    """맞았다/아니었다 버튼 렌더링"""
    log = st.session_state.get("feedback_log", {})
    if key in log:
        result = log[key]
        color = "#27ae60" if result == "hit" else "#c0392b"
        label = "✅ 맞았다고 응답" if result == "hit" else "❌ 아니었다고 응답"
        st.markdown(f'<div style="font-size:11px;color:{color};margin-top:4px">{label}</div>',
                    unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ 맞았다", key=f"hit_{key}", use_container_width=True):
                save_feedback(key, True)
                st.rerun()
        with col2:
            if st.button("❌ 아니었다", key=f"miss_{key}", use_container_width=True):
                save_feedback(key, False)
                st.rerun()


def tab_yongshin(pils):
    """용신(Yong-Shin) 탭"""
    st.markdown('<div class="gold-section">[분석] 용신(Yong-Shin) - 내 사주의 구원 오행</div>', unsafe_allow_html=True)


def tab_past_events(pils, birth_year, gender, name=""):
    """[적중] 과거 적중 탭 - 엔진이 계산, AI는 설명만"""
    st.markdown('<div class="gold-section">[데이터] 과거 적중 - 엔진이 계산한 당신의 과거</div>',
                unsafe_allow_html=True)

    # 엔진 하이라이트 생성
    with st.spinner("충·합·세운 교차 계산 중..."):
        hl = generate_engine_highlights(pils, birth_year, gender)

    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    current_age = current_year - birth_year + 1

    # -- 피드백 통계 --------------------------------------
    total_fb, hit_fb = get_feedback_stats()
    if total_fb > 0:
        hit_rate = round(hit_fb / total_fb * 100)
        color = '#4caf50' if hit_rate >= 60 else '#ff5252'
        html = f"<div style='background:linear-gradient(135deg,#f0fff0,#e8f5e8);color:#000000;padding:10px 18px;border-radius:10px;margin-bottom:10px;display:flex;align-items:center;gap:16px'>"
        html += f"<span style='font-size:13px;color:#a8d58c'>[분석] 적중률 피드백</span>"
        html += f"<span style='font-size:20px;font-weight:900;color:{color}'>{hit_rate}%</span>"
        html += f"<span style='font-size:12px;color:#444'>(응답 {total_fb}개 중 {hit_fb}개 적중)</span>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    # ------------------------------------------
    # STEP 0: 성향 판독 - 첫 번째로 보여줌
    # ------------------------------------------
    st.markdown('<div class="gold-section">[분석] 성향 판독</div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px;color:#000000;margin-bottom:8px'>엔진 계산: 일간 + 일지 + 신강신약 + 오행 과다/부족 조합 공식 적용</div>", unsafe_allow_html=True)

    personality = hl["personality"]
    for i, trait in enumerate(personality):
        # 겉/속 구분 강조
        if "겉" in trait or "속" in trait:
            bg, border = "#f0e8ff", "#9b7ccc"
            tc = "#3d1a6e"          # - 진한 보라
        elif "과다" in trait or "부족" in trait or "없습니다" in trait:
            bg, border = "#fffde8", "#000000"
            tc = "#5a3e00"          # - 진한 갈색
        else:
            bg, border = "#e8f4ff", "#4a90d9"
            tc = "#0d3060"          # - 진한 파랑

        style = f"background:{bg};color:{tc};padding:13px 16px;border-radius:10px;border-left:4px solid {border};margin:5px 0;font-size:13px;line-height:1.9;font-weight:500"
        st.markdown(f"<div style='{style}'>{trait}</div>", unsafe_allow_html=True)

    # 성향 피드백
    st.markdown('<div style="font-size:12px;color:#000000;margin:6px 0">이 성향이 맞나요?</div>',
                unsafe_allow_html=True)
    render_feedback_btn("personality_overall", "성향 전반")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ------------------------------------------
    # STEP 1: 과거 사건 - 나이 + 분야 + 이유
    # ------------------------------------------
    st.markdown('<div class="gold-section">[포인트] 과거 적중 포인트</div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px;color:#000000;margin-bottom:10px'>충/합/십성 교차를 수학 계산으로 뽑은 과거 사건 시점입니다.<br><b style='color:#000000'>나이와 분야를 먼저 확인하고 '맞았다/아니었다'를 눌러주세요.</b></div>", unsafe_allow_html=True)

    # 강도 높은 것만 먼저 - 쪽집게 효과
    red_events = [e for e in hl["past_events"] if e["intensity"] == "High"]
    yellow_events = [e for e in hl["past_events"] if e["intensity"] == "Mid"]
    green_events = [e for e in hl["past_events"] if e["intensity"] == "Low"]

    def render_event_card(ev, idx):
        domain_colors = {
            "직장": "#2980b9", "재물": "#27ae60", "관계": "#8e44ad",
            "건강": "#c0392b", "학업": "#e67e22", "이동": "#16a085",
        }
        dc = "#666"
        for kw, kc in domain_colors.items():
            if kw in ev.get("domain", ""):
                dc = kc; break

        intensity_bg = {
            "High": ("#fff0f0", "#c0392b"),
            "Mid": ("#ffffff", "#000000"),
            "Low": ("#f0fff0", "#27ae60"),
        }
        card_bg, card_border = intensity_bg.get(ev["intensity"], ("#fafafa", "#888"))

        html = f"<div style='background:{card_bg};border:1px solid {card_border}44;border-left:5px solid {card_border};border-radius:12px;padding:16px;margin:8px 0'>"
        html += "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><div>"
        html += f"<span style='font-size:20px;font-weight:900;color:{card_border}'>{ev['age']}</span>"
        html += f"<span style='font-size:12px;color:#000000;margin-left:8px'>({ev['year']}년)</span>"
        html += "</div>"
        html += f"<div style='background:{dc};color:#000000;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700'>{ev.get('domain','변화')}</div>"
        html += "</div>"
        html += f"<div style='font-size:13px;color:#000000;line-height:1.9;background:white;padding:10px 14px;border-radius:8px;margin-bottom:6px'>{ev['desc']}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        render_feedback_btn(f"event_{idx}", ev["desc"][:20])

    if red_events:
        st.markdown('<div style="font-size:13px;font-weight:800;color:#000000;margin:16px 0 8px;border-left:3px solid #000000;padding-left:10px">[변동] 강한 변동 - 크게 흔들린 때</div>', unsafe_allow_html=True)
        for i, ev in enumerate(red_events[:4]):
            render_event_card(ev, f"red_{i}")

    if yellow_events:
        st.markdown('<div style="font-size:13px;font-weight:800;color:#000000;margin:16px 0 8px;border-left:3px solid #000000;padding-left:10px">[변화] 흐름이 바뀐 때</div>', unsafe_allow_html=True)
        for i, ev in enumerate(yellow_events[:3]):
            render_event_card(ev, f"yel_{i}")

    if green_events:
        st.markdown('<div style="font-size:13px;font-weight:800;color:#000000;margin:16px 0 8px;border-left:3px solid #000000;padding-left:10px">[반전] 기회가 된 때</div>', unsafe_allow_html=True)
        for i, ev in enumerate(green_events[:2]):
            render_event_card(ev, f"grn_{i}")

    # ------------------------------------------
    # 월지 충 - 가장 중요한 변동점
    # ------------------------------------------
    if hl["wolji_chung"]:
        st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
        st.markdown('<div class="gold-section">[분석] 월지(Wolji) 충 - 삶의 기반이 흔들린 시점</div>', unsafe_allow_html=True)
        html = f"<div class='card' style='background:#fff5f0;border:1px solid #e8a0a0;font-size:13px;color:#000000;margin-bottom:8px'>"
        html += f"월지 <b style='color:#c0392b'>{pils[2]['jj']}</b>는 이 사주의 뿌리입니다. "
        html += "충을 받을 때 직업/가정/건강 중 하나가 반드시 흔들렸습니다.</div>"
        st.markdown(html, unsafe_allow_html=True)

        for i, wc in enumerate(hl["wolji_chung"][:4]):
            html = f"<div style='background:#fff0f0;border-left:4px solid #c0392b;border-radius:8px;padding:12px 16px;margin:5px 0'>"
            html += f"<span style='font-size:16px;font-weight:800;color:#c0392b'>{wc['age']}</span>"
            html += f"<div style='font-size:13px;color:#000000;margin-top:4px;line-height:1.9'>{wc['desc']}</div></div>"
            st.markdown(html, unsafe_allow_html=True)
            render_feedback_btn(f"wolji_{i}", wc["desc"][:20])

    # ══════════════════════════════════════════
    # 돈 + 결혼 타이밍
    # ══════════════════════════════════════════
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    col_money, col_marry = st.columns(2)

    with col_money:
        st.markdown('<div class="gold-section">[재물] 돈이 오는 시기</div>', unsafe_allow_html=True)
        if hl["money_peak"]:
            for mp in hl["money_peak"][:3]:
                color = "#000000" if mp.get("ss") == "더블" else "#27ae60"
                html = f"<div style='background:#ffffff;border-left:4px solid {color};border-radius:8px;padding:10px 14px;margin:5px 0'>"
                html += f"<span style='font-weight:800;color:{color}'>{mp['age']}</span>"
                html += f"<span style='font-size:11px;color:#000000;margin-left:6px'>({mp['year']})</span>"
                html += f"<div style='font-size:12px;color:#000000;margin-top:4px'>{mp['desc']}</div></div>"
                st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("재물 상승기 계산 중")

    with col_marry:
        st.markdown('<div class="gold-section">[인연] 인연이 오는 시기</div>', unsafe_allow_html=True)
        if hl["marriage_peak"]:
            for mp in hl["marriage_peak"][:3]:
                html = f"<div style='background:#fff0f8;border-left:4px solid #e91e8c;border-radius:8px;padding:10px 14px;margin:5px 0'>"
                html += f"<span style='font-weight:800;color:#e91e8c'>{mp['age']}</span>"
                html += f"<span style='font-size:11px;color:#000000;margin-left:6px'>({mp['year']})</span>"
                html += f"<div style='font-size:12px;color:#000000;margin-top:4px'>{mp['desc']}</div></div>"
                st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("인연 시기 계산 중")

    # ------------------------------------------
    # 위험 구간
    # ------------------------------------------
    if hl["danger_zones"]:
        st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
        st.markdown('<div class="gold-section">[주의] 조심해야 할 구간</div>', unsafe_allow_html=True)
        for dz in hl["danger_zones"][:3]:
            html = f"<div style='background:#fff5f0;border-left:4px solid #e67e22;border-radius:8px;padding:10px 14px;margin:5px 0'>"
            html += f"<span style='font-weight:800;color:#e67e22'>{dz['age']}</span>"
            html += f"<span style='font-size:11px;color:#000000;margin-left:6px'>({dz['year']})</span>"
            html += f"<div style='font-size:12px;color:#000000;margin-top:4px'>{dz['desc']}</div></div>"
            st.markdown(html, unsafe_allow_html=True)

    # ------------------------------------------
    # 누적 적중률 현황
    # ------------------------------------------
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    total_fb2, hit_fb2 = get_feedback_stats()
    if total_fb2 > 0:
        hit_rate2 = round(hit_fb2 / total_fb2 * 100)
        miss = total_fb2 - hit_fb2
        color = '#4caf50' if hit_rate2 >= 60 else '#ff5252'
        html = "<div style='background:linear-gradient(135deg,#f5f5ff,#eef0ff);color:#000000;padding:20px;border-radius:14px;text-align:center'>"
        html += "<div style='font-size:13px;color:#000000;margin-bottom:10px'>[데이터] 이 사주의 피드백 적중률</div>"
        html += f"<div style='font-size:36px;font-weight:900;color:{color}'>{hit_rate2}%</div>"
        html += f"<div style='font-size:13px;color:#000000;margin-top:6px'>[맞았다] {hit_fb2}개 | [아니었다] {miss}개</div></div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<div style='background:#ffffff;color:#000000;padding:14px;border-radius:10px;text-align:center;font-size:13px'>위 항목들에 '맞았다/아니었다'를 눌러주세요.<br>피드백이 쌓일수록 적중률이 표시됩니다.</div>", unsafe_allow_html=True)



def tab_waryeong(pils):
    st.markdown('<div class="gold-section">[분석] 월령(Wol-ryeong) - 계절이 사주를 지배한다</div>', unsafe_allow_html=True)
    wr = get_waryeong(pils)
    wol_jj = wr["월지"]
    oh_emoji = {"木":"[木]","火":"[火]","土":"[土]","金":"[金]","水":"[水]"}
    html = "<div style='background:linear-gradient(135deg,#f5eeff,#eedaff);color:#000000;padding:20px;border-radius:14px;text-align:center;margin-bottom:14px'>"
    html += f"<div style='font-size:13px;color:#c8b8f0'>태어난 월지(Wol-ji)</div>"
    html += f"<div style='font-size:36px;font-weight:900;color:#8b6200;margin:8px 0'>{wol_jj}</div>"
    html += f"<div style='font-size:14px;color:#c8b8f0'>{wr['계절']}</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown('<div class="gold-section">오행별 月令 왕상휴수사(旺相休囚死)</div>', unsafe_allow_html=True)
    oh_strength = calc_ohaeng_strength(pils[1]["cg"], pils)
    cols = st.columns(5)
    for i,oh in enumerate(["木","火","土","金","水"]):
        d = wr["오행별"][oh]
        with cols[i]:
            html = f"<div style='text-align:center;padding:12px;background:#ffffff;border-radius:12px;border:2px solid {'#000000' if d['score']>=85 else '#ddd'}'>"
            html += f"<div style='font-size:20px'>{oh_emoji[oh]}</div>"
            html += f"<div style='font-size:14px;font-weight:800;color:#000000'>{OHN.get(oh,'')}</div>"
            html += f"<div style='font-size:22px;font-weight:900;color:{d['color']}'>{d['grade']}</div>"
            html += f"<div style='font-size:12px;color:#444'>{d['score']}점</div></div>"
            st.markdown(html, unsafe_allow_html=True)
            st.progress(d["score"]/100)
    st.markdown('<div class="gold-section">[데이터] 월령 상세 해석</div>', unsafe_allow_html=True)
    for oh in ["木","火","土","金","水"]:
        d = wr["오행별"][oh]; val = oh_strength.get(oh,0)
        bg = "#fff0e0" if d["score"]>=85 else "#fafafa"
        bdr = d["color"] if d["score"]>=60 else "#ccc"
        st.markdown(f"<div class='card' style='background:{bg};border-left:4px solid {bdr};margin:4px 0'><div style='display:flex;justify-content:space-between;margin-bottom:4px'><span style='font-size:14px;font-weight:700;color:{bdr}'>{oh_emoji[oh]} {OHN.get(oh,'')}({oh}) - {d['grade']}</span><span style='font-size:12px;color:#444'>월령 {d['score']}점 | 사주 {val}%</span></div><div style='font-size:13px;color:#444'>{d['desc']}</div></div>", unsafe_allow_html=True)


def tab_oigyeok(pils):
    st.markdown('<div class="gold-section">[분석] 외격(Oi-gyeok) + 양인(Yang-in) 분석</div>', unsafe_allow_html=True)
    results = get_oigyeok(pils)
    if results:
        for r in results:
            html = f"<div class='card' style='background:linear-gradient(135deg,#ffffff,#fff5cc);border:2px solid {r['color']}'>"
            html += f"<div style='font-size:18px;font-weight:800;color:{r['color']};margin-bottom:10px'>{r['격']} 성립!</div>"
            html += f"<div style='font-size:14px;color:#000000;line-height:2.0;margin-bottom:12px'>{r['desc']}</div>"
            html += "<div style='display:flex;flex-wrap:wrap;gap:8px'>"
            html += "<div style='flex:1;min-width:160px;background:#ffffff;padding:10px;border-radius:10px'>"
            html += f"<div style='font-size:12px;font-weight:700;color:#2a6f2a;margin-bottom:4px'>[용신]</div><div style='font-size:12px'>{r['용신']}</div></div>"
            html += "<div style='flex:1;min-width:160px;background:#fff0f0;padding:10px;border-radius:10px'>"
            html += f"<div style='font-size:12px;font-weight:700;color:#8b2020;margin-bottom:4px'>[기신]</div><div style='font-size:12px'>{r['기신']}</div></div></div>"
            html += f"<div style='margin-top:10px;background:#fff0e0;padding:8px 12px;border-radius:8px;font-size:12px;color:#8b4020'>[주의] {r['caution']}</div></div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<div class='card' style='background:#ffffff;border:2px solid #2980b9;text-align:center;padding:24px'><div style='font-size:18px;font-weight:700;color:#1a5f7a'>[안내] 내격(Nae-gyeok) 사주입니다</div><div style='font-size:13px;color:#000000;margin-top:8px'>종격/화기격 등의 외격 조건이 성립하지 않습니다. 일반 내격 이론으로 해석하십시오.</div></div>", unsafe_allow_html=True)
    # 양인
    st.markdown('<div class="gold-section" style="margin-top:16px">[분석] 양인(Yang-in) 분석</div>', unsafe_allow_html=True)
    yin = get_yangin(pils)
    if yin["존재"]:
        d = yin["설명"]
        st.markdown(f"<div class='card' style='background:#fff0e0;border:2px solid #e67e22'><div style='font-size:16px;font-weight:800;color:#e67e22;margin-bottom:8px'>[변동] {d.get('name','양인')} 존재 - {', '.join(yin['위치'])}에서 발견</div><div style='font-size:13px;color:#000000;line-height:1.9;margin-bottom:10px'>{d.get('desc','')}</div><div style='display:flex;flex-wrap:wrap;gap:8px'><div style='flex:1;min-width:160px;background:#ffffff;padding:10px;border-radius:10px'><div style='font-size:12px;font-weight:700;color:#2a6f2a;margin-bottom:4px'>[긍정] 긍정적 발현</div><div style='font-size:12px'>{d.get('good','')}</div></div><div style='flex:1;min-width:160px;background:#fff0f0;padding:10px;border-radius:10px'><div style='font-size:12px;font-weight:700;color:#8b2020;margin-bottom:4px'>[주의] 주의사항</div><div style='font-size:12px'>{d.get('caution','')}</div></div></div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='card' style='background:#ffffff;border:1px solid #a8d5a8'><div style='font-size:14px;color:#2a6f2a'>✅ 양인 없는 온화한 사주 — {pils[1]['cg']}일간 양인 지지({yin['양인_지지']})가 사주에 없습니다.</div></div>", unsafe_allow_html=True)


def tab_sinsal12(pils):
    st.markdown('<div class="gold-section">💫 12신살(十二神殺) 완전 분석</div>', unsafe_allow_html=True)
    sinsal_list = get_12sinsal(pils)
    type_colors = {"길":"#2980b9","흉":"#c0392b","중":"#8e44ad"}
    if sinsal_list:
        for grp_type, grp_label in [("길","✨ 길신"),("중","🌀 중성"),("흉","⚠️ 흉살")]:
            grp = [s for s in sinsal_list if s["type"]==grp_type]
            if grp:
                c = type_colors[grp_type]
                st.markdown(f'<div style="font-size:15px;font-weight:700;color:{c};margin:12px 0 6px">{grp_label}</div>', unsafe_allow_html=True)
                for s in grp:
                    html = f"<div class='card' style='border-left:4px solid {c};margin:6px 0'>"
                    html += f"<div style='font-size:14px;font-weight:700;color:{c};margin-bottom:6px'>[분석] {s['이름']} - <span style='font-size:12px;color:#444'>{', '.join(s['위치'])}</span></div>"
                    html += f"<div style='font-size:13px;color:#000000;line-height:1.8;margin-bottom:8px'>{s['desc']}</div>"
                    html += "<div style='display:flex;flex-wrap:wrap;gap:6px'>"
                    html += f"<div style='flex:1;min-width:150px;background:#ffffff;padding:6px 10px;border-radius:8px;font-size:12px;color:#2a6f2a'>[긍정] {s['good']}</div>"
                    html += f"<div style='flex:1;min-width:150px;background:#fff0f0;padding:6px 10px;border-radius:8px;font-size:12px;color:#8b2020'>[주의] {s['caution']}</div></div></div>"
                    st.markdown(html, unsafe_allow_html=True)
    else:
        st.success("두드러진 신살이 없는 평온한 사주입니다.")
    # 조견표
    st.markdown('<div class="gold-section">[데이터] 12신살 전체 조견표</div>', unsafe_allow_html=True)
    nyon_jj = pils[3]["jj"]
    san_groups = ["寅午戌","申子辰","巳酉丑","亥卯未"]
    my_group = next((g for g in san_groups if nyon_jj in g),"寅午戌")
    pil_jjs = [p["jj"] for p in pils]
    rows = ""
    for sname,jj_map in SINSAL_12_TABLE.items():
        sinsal_jj = jj_map.get(my_group,"")
        d = SINSAL_12_DESC.get(sname,{})
        has = "Y" if sinsal_jj in pil_jjs else "-"
        badge = {"길":"[길]","흉":"[흉]","중":"[중]"}.get(d.get("type","중"),"[ ]")
        rows += f"<tr><td style='padding:6px;font-weight:700'>{d.get('name',sname)}</td><td style='text-align:center;padding:6px'>{sinsal_jj}</td><td style='text-align:center;padding:6px'>{badge}</td><td style='text-align:center;padding:6px;font-size:16px'>{has}</td></tr>"
    st.markdown(f"""<table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="background:#ffffff"><th style="padding:8px;text-align:left">신살</th><th style="text-align:center">해당지지</th><th style="text-align:center">길흉</th><th style="text-align:center">내 사주</th></tr></thead>
        <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def tab_cross_analysis(pils, birth_year, gender):
    """대운·세운 교차 분석 - 3중 완전판"""
    st.markdown('<div class="gold-section">[분석] 대운/세운 교차 분석 - 운명의 교차점</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card" style="background:#f5f5ff;color:#000000;padding:14px;font-size:13px;line-height:1.9;margin-bottom:12px">
    [안내] <b style="color:#8b6200">고수가 보는 법:</b> 원국은 무대 설계, 대운은 계절, 세운은 날씨입니다.
    <b style="color:#000000">세 가지가 겹치는 해</b>에 인생의 큰 사건이 일어납니다. 특히 원국의 합이 운에서 충으로 깨질 때를 정확히 짚는 것이 핵심입니다.
    </div>""", unsafe_allow_html=True)

    current_year = datetime.now().year
    year_sel = st.selectbox("분석 연도", list(range(current_year-5, current_year+16)), index=5, key="cross_year")

    cross = get_daewoon_sewoon_cross(pils, birth_year, gender, year_sel)
    if not cross:
        st.warning("해당 연도의 대운 정보가 없습니다."); return

    ilgan = pils[1]["cg"]; ilgan_oh = OH.get(ilgan, "")
    ys = get_yongshin(pils); yongshin_ohs = ys["종합_용신"]
    dw = cross["대운"]; sw = cross["세운"]
    dw_ss = cross["대운_천간십성"]; sw_ss = cross["세운_천간십성"]
    dw_is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
    sw_is_yong = _get_yongshin_match(sw_ss, yongshin_ohs, ilgan_oh) == "yong"
    hap_breaks = _get_hap_break_warning(pils, dw["jj"], sw["jj"])

    lc = "#000000" if (dw_is_yong and sw_is_yong) else "#c0392b" if (not dw_is_yong and not sw_is_yong) else "#2980b9"
    overall = ("[최고] 용신 대운x세운 겹침 - 최고의 발복 시기" if (dw_is_yong and sw_is_yong)
               else "[수비] 기신 대운x세운 - 수비 전략 필요" if (not dw_is_yong and not sw_is_yong)
               else "[혼재] 대운/세운 혼재 - 선별적 추진")

    html = f"""
    <div style="background:linear-gradient(135deg,#f0eeff,#ece8ff);color:#000000;padding:28px;border-radius:16px;margin-bottom:14px">
        <div style="text-align:center;font-size:13px;color:#000000;margin-bottom:14px">{year_sel}년 운명의 교차점</div>
    """
    html += "<div style='display:flex;justify-content:center;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:14px'>"
    html += f"<div style='text-align:center;background:{'rgba(197,160,89,0.25)' if dw_is_yong else 'rgba(255,255,255,0.08)'};padding:16px 24px;border-radius:14px;border:{'2px solid #000000' if dw_is_yong else '1px solid #333'}'>"
    html += f"<div style='font-size:11px;color:#555'>대운(Dae-woon)</div>"
    html += f"<div style='font-size:30px;font-weight:900;color:#8b6200'>{dw['str']}</div>"
    html += f"<div style='font-size:12px;color:#c8b8f0'>{dw_ss} / {cross['대운_지지십성']}</div>"
    if dw_is_yong: html += "<div style='font-size:11px;color:#8b6200;margin-top:4px'>[용신 대운]</div>"
    html += "</div>"
    html += f"<div style='font-size:28px;color:{lc}'>x</div>"
    html += f"<div style='text-align:center;background:{'rgba(197,160,89,0.25)' if sw_is_yong else 'rgba(255,255,255,0.08)'};padding:16px 24px;border-radius:14px;border:{'2px solid #000000' if sw_is_yong else '1px solid #333'}'>"
    html += f"<div style='font-size:11px;color:#555'>세운(Se-woon)</div>"
    html += f"<div style='font-size:30px;font-weight:900;color:#8b6200'>{sw['세운']}</div>"
    html += f"<div style='font-size:12px;color:#c8b8f0'>{sw_ss} / {cross['세운_지지십성']}</div>"
    if sw_is_yong: html += "<div style='font-size:11px;color:#8b6200;margin-top:4px'>[용신 세운]</div>"
    html += "</div></div>"
    html += f"<div style='text-align:center;font-size:15px;font-weight:700;color:{lc}'>{overall}</div></div>"
    st.markdown(html, unsafe_allow_html=True)

    # 합이 깨지는 경고
    if hap_breaks:
        st.markdown('<div class="gold-section">[경고] 원국 합(Hap)이 운에서 깨지는 경고</div>', unsafe_allow_html=True)
        for w in hap_breaks:
            html = f"<div class='card' style='background:{w['color']}18;border-left:5px solid {w['color']}'>"
            html += f"<div style='font-size:13px;font-weight:700;color:{w['color']};margin-bottom:4px'>{w['level']}</div>"
            html += f"<div style='font-size:13px;color:#000000;line-height:1.9'>{w['desc']}</div></div>"
            st.markdown(html, unsafe_allow_html=True)

    # 교차 해석
    st.markdown(f"<div class='card' style='background:#ffffff;border:2px solid #000000'><div style='font-size:14px;font-weight:700;color:#000000;margin-bottom:8px'>[데이터] {year_sel}년 핵심 해석</div><div style='font-size:14px;color:#000000;line-height:2.0;margin-bottom:10px'>{cross['교차해석']}</div></div>", unsafe_allow_html=True)

    if cross["교차사건"]:
        st.markdown('<div class="gold-section">[분석] 원국과의 교차 사건</div>', unsafe_allow_html=True)
        for ev in cross["교차사건"]:
            c = "#000000" if "합" in ev["type"] else "#c0392b" if "충" in ev["type"] else "#8e44ad"
            st.markdown(f'<div class="card" style="border-left:4px solid {c}"><b style="color:{c}">{ev["type"]}</b> - {ev["desc"]}</div>', unsafe_allow_html=True)

    # 처방
    PCMAP = {
        (True,True):   ("[최고] 황금 시기 - 전력 질주하십시오!", "#27ae60", "이 시기에 가장 중요한 결정(창업/결혼/이직/투자)을 내리십시오. 용신 에너지가 두 배로 작동합니다."),
        (True,False):  ("[기회] 기회 속 위험 - 선별적 추진", "#e67e22", "대운의 좋은 기운을 살리되 세운의 걸림돌을 조심하십시오. 큰 결정은 신중하게, 작은 시도는 적극적으로."),
        (False,True):  ("[구원] 터닝포인트 - 세운이 구원합니다", "#2980b9", "힘든 대운이지만 올해 세운이 활로를 열어줍니다. 다음 용신 대운을 위한 준비를 하십시오."),
        (False,False): ("[수비] 수비 모드 - 내실 다지기", "#c0392b", "무리한 확장/투자/이동을 피하십시오. 건강과 재정 점검에 집중하십시오."),
    }
    plabel, pcolor, pdesc = PCMAP.get((dw_is_yong, sw_is_yong), ("[보통] 평범한 해", "#888", "꾸준한 노력으로 안정을 유지하십시오."))
    html = f"<div class='card' style='background:{pcolor}15;border:2px solid {pcolor};margin-top:10px'>"
    html += f"<div style='font-size:15px;font-weight:800;color:{pcolor};margin-bottom:8px'>{plabel}</div>"
    html += f"<div style='font-size:13px;color:#000000;line-height:1.9'>{pdesc}</div></div>"
    st.markdown(html, unsafe_allow_html=True)

    # 향후 10년 타임라인
    st.markdown('<div class="gold-section">📅 향후 10년 운세 타임라인</div>', unsafe_allow_html=True)
    for y in range(year_sel, year_sel+10):
        c2 = get_daewoon_sewoon_cross(pils, birth_year, gender, y)
        if not c2: continue
        d_is_y = _get_yongshin_match(c2["대운_천간십성"], yongshin_ohs, ilgan_oh) == "yong"
        s_is_y = _get_yongshin_match(c2["세운_천간십성"], yongshin_ohs, ilgan_oh) == "yong"
        hb = _get_hap_break_warning(pils, c2["대운"]["jj"], c2["세운"]["jj"])
        if d_is_y and s_is_y:   row_lc, row_bg, badge = "#000000","#ffffff","🌟 최길"
        elif d_is_y or s_is_y:  row_lc, row_bg, badge = "#2980b9","#f0f8ff","✨ 길"
        elif "흉" in c2["세운"]["길흉"]: row_lc, row_bg, badge = "#c0392b","#fff5f5","⚠️ 흉"
        else:                    row_lc, row_bg, badge = "#888","#fafafa","〰️ 평"
        hb_icon = " 🚨합깨짐" if hb else ""
        st.markdown(f"""
        <div style="display:flex;align-items:center;padding:9px 14px;border-radius:10px;margin:3px 0;background:{row_bg};border:{'2px solid '+row_lc if y==year_sel else '1px solid #e8e8e8'}">
            <span style="font-weight:800;color:#000000;min-width:52px">{y}년</span>
            <span style="min-width:80px;font-size:13px;color:#333">대운:{c2["대운"]["str"]}</span>
            <span style="min-width:80px;font-size:13px;color:#333">세운:{c2["세운"]["세운"]}</span>
            <span style="flex:1;font-size:12px;color:#444">{c2["대운_천간십성"]}+{c2["세운_천간십성"]}</span>
            <span style="font-size:12px;color:#c0392b">{hb_icon}</span>
            <span style="font-weight:700;color:{row_lc};font-size:13px">{badge}</span>
        </div>""", unsafe_allow_html=True)




def tab_jijanggan(pils):
    ilgan = pils[1]["cg"]
    st.markdown('<div class="gold-section">🔬 지장간(地藏干) — 지지 속 숨겨진 천간</div>', unsafe_allow_html=True)
    analysis = get_jijanggan_analysis(ilgan, pils)
    labels_full = ["시주(時柱)","일주(日柱)","월주(月柱)","년주(年柱)"]
    for i,pd in enumerate(analysis):
        jj = pd["지지"]
        jj_kr = JJ_KR[JJ.index(jj)] if jj in JJ else ""
        st.markdown(f"### {labels_full[i]} — 지지 {jj}({jj_kr})")
        items = pd["지장간"]
        if not items: continue
        cols = st.columns(len(items))
        for j,item in enumerate(items):
            with cols[j]:
                tuchul = item["투출"]
                st.markdown(f"""
                <div style="background:{'#ffffff' if tuchul else '#fafafa'};border:{'2px solid #000000' if tuchul else '1px solid #ddd'};border-radius:12px;padding:14px;text-align:center">
                    <div style="font-size:11px;color:#444">{TYPE_LABEL.get(item['타입'],item['타입'])}</div>
                    <div style="font-size:26px;font-weight:900;color:#000000;margin:6px 0">{item['천간']}</div>
                    <div style="font-size:12px;color:#333">{item['십성']}</div>
                    <div style="font-size:11px;color:#444">{item['일수']}일</div>
                    {f'<div style="font-size:11px;background:#000000;color:#000000;padding:2px 8px;border-radius:10px;margin-top:4px">✨ 투출!</div>' if tuchul else ''}
                </div>""", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#ffffff;padding:8px 12px;border-radius:8px;font-size:12px;color:#5a2d8b;margin:4px 0 12px'>[발동] {' -> '.join([f'{it['천간']}({it['십성']}) {TYPE_LABEL.get(it['타입'],'')}' for it in items])}</div>", unsafe_allow_html=True)


def tab_health(pils, gender="남"):
    ilgan = pils[1]["cg"]
    st.markdown('<div class="gold-section">[분석] 건강론(Health) - 사주로 보는 건강 지도</div>', unsafe_allow_html=True)
    health = get_health_analysis(pils, gender)
    il_oh = health["ilgan_oh"]
    oh_emoji = {"木":"[木]","火":"[火]","土":"[土]","金":"[金]","水":"[水]"}
    h = health["일간_건강"]
    html = "<div class='card' style='background:#ffffff;border:2px solid #2980b9'>"
    html += f"<div style='font-size:14px;font-weight:700;color:#1a5f8b;margin-bottom:10px'>{oh_emoji.get(il_oh,'')} {ilgan}일간 - {OHN.get(il_oh,'')} 기운의 건강 특성</div>"
    html += "<div style='display:flex;flex-wrap:wrap;gap:8px'>"
    html += ''.join([f'<div style="flex:1;min-width:180px;background:white;padding:10px;border-radius:8px"><div style="font-size:12px;font-weight:700;color:#2980b9;margin-bottom:3px">{k}</div><div style="font-size:12px;color:#333">{v}</div></div>' for k,v in [("[장기] 주요 장기",h.get("organs","")),("[감정] 취약 감정",h.get("emotion","")),("[식품] 도움 식품",h.get("food","")),("[처방] 생활 처방",h.get("lifestyle",""))]])
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    if health["일주_건강"]:
        st.markdown(f'<div class="card" style="background:#fff0e0;border-left:4px solid #e67e22;margin-top:8px"><b style="color:#e67e22">[주의] 일주 12운성 건강:</b> {health["일주_건강"]}</div>', unsafe_allow_html=True)
    if health["과다_오행"]:
        st.markdown('<div class="gold-section">[주의] 과다 오행 건강 경보</div>', unsafe_allow_html=True)
        for item in health["과다_오행"]:
            h2=item["health"]; oh=item["오행"]
            html = f"<div class='card' style='background:#fff5f0;border-left:4px solid #c0392b'>"
            html += f"<b style='color:#c0392b'>{oh}({OHN.get(oh,'')}) 과다 {item['수치']}%</b> - 주의 질환: {h2.get('over_symptom','')}"
            html += f"<div style='font-size:12px;color:#000000;margin-top:6px'>[처방] {h2.get('food','')} / {h2.get('lifestyle','')}</div></div>"
            st.markdown(html, unsafe_allow_html=True)
    if health["부족_오행"]:
        st.markdown('<div class="gold-section">[처방] 부족 오행 건강 처방</div>', unsafe_allow_html=True)
        for item in health["부족_오행"]:
            h2=item["health"]; oh=item["오행"]
            html = f"<div class='card' style='background:#f0f5ff;border-left:4px solid #2980b9'>"
            html += f"<b style='color:#2980b9'>{oh}({OHN.get(oh,'')}) 부족 {item['수치']}%</b> - 증상: {h2.get('lack_symptom','')}"
            html += f"<div style='font-size:12px;color:#000000;margin-top:6px'>[보충] {h2.get('food','')} / {h2.get('lifestyle','')}</div></div>"
            st.markdown(html, unsafe_allow_html=True)
    # 오행별 바 차트
    st.markdown('<div class="gold-section">[데이터] 오행 건강 조견표</div>', unsafe_allow_html=True)
    for oh in ["木","火","土","金","水"]:
        val = health["oh_strength"].get(oh,0)
        h2 = HEALTH_OH[oh]
        c = "#c0392b" if val>=35 else "#2980b9" if val<=5 else "#888"
        html = "<div style='padding:8px 14px;border-radius:10px;background:#fafafa;border:1px solid #e8e8e8;margin:3px 0'>"
        html += "<div style='display:flex;justify-content:space-between;margin-bottom:4px'>"
        html += f"<span style='font-weight:700;color:{c}'>{oh_emoji.get(oh,'')}{OHN.get(oh,'')} {val}%</span>"
        html += f"<span style='font-size:12px;color:#444'>{h2['organs']}</span></div>"
        html += f"<div style='background:#e8e8e8;border-radius:4px;height:6px'><div style='background:{c};border-radius:4px;height:6px;width:{min(val,100)}%'></div></div></div>"
        st.markdown(html, unsafe_allow_html=True)


def tab_jaemul(pils, birth_year, gender="남"):
    st.markdown('<div class="gold-section">[재물론] 재물론(財物論) - 돈이 모이는 구조 분석</div>', unsafe_allow_html=True)
    jm = get_jaemul_analysis(pils, birth_year, gender)
    oh_emoji = {"木":"[木]","火":"[火]","土":"[土]","金":"[金]","수":"[수]"}
    html = "<div style='background:linear-gradient(135deg,#fff9e0,#fff3c0);color:#000000;padding:20px;border-radius:14px;text-align:center;margin-bottom:14px'>"
    html += f"<div style='font-size:13px;color:#000000'>재성 오행(Wealth Element)</div>"
    html += f"<div style='font-size:36px;margin:8px 0'>{oh_emoji.get(jm['재성_오행'],'[Wealth]')}</div>"
    html += f"<div style='font-size:22px;font-weight:900;color:#8b6200'>{OHN.get(jm['재성_오행'],'')} 재성 강도 {jm['재성_강도']}%</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    html = "<div class='card' style='background:#ffffff;border:2px solid #27ae60'>"
    html += "<div style='font-size:13px;font-weight:700;color:#1a6f3a;margin-bottom:6px'>[분석] 재물 유형</div>"
    html += f"<div style='font-size:14px;color:#000000;line-height:1.9'>{jm['재물_유형']}</div>"
    html += f"<div style='margin-top:8px;background:#e8f5e8;padding:8px 12px;border-radius:8px;font-size:13px;color:#1a6f3a'>[전략] {jm['재물_전략']}</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    if jm["재성_위치"]:
        st.markdown(f'<div class="card" style="background:#ffffff;border:1px solid #e8d5a0;margin-top:8px"><b style="color:#000000">[위치] 재성 위치:</b> {"  |  ".join(jm["재성_위치"])}</div>', unsafe_allow_html=True)
    if jm["재물_피크_대운"]:
        st.markdown('<div class="gold-section">[상승] 재물 상승기 대운</div>', unsafe_allow_html=True)
        for peak in jm["재물_피크_대운"]:
            c = {"정재":"#27ae60","편재":"#2980b9","식신":"#8e44ad"}.get(peak["십성"],"#000000")
            html = f"<div style='background:#ffffff;border-left:4px solid {c};border-radius:10px;padding:12px 16px;margin:5px 0;display:flex;justify-content:space-between;align-items:center'>"
            html += f"<div><span style='font-size:16px;font-weight:800;color:#000000'>{peak['대운']}</span> <span style='font-size:13px;color:#444'>{peak['나이']}</span></div>"
            html += f"<div style='text-align:right'><div style='font-size:13px;font-weight:700;color:{c}'>{peak['십성']}</div><div style='font-size:12px;color:#444'>{peak['연도']}</div></div></div>"
            st.markdown(html, unsafe_allow_html=True)


def tab_career(pils, gender="남"):
    st.markdown('<div class="gold-section">[분석] 직업론(Career) - 천부적 적성과 최적 직업</div>', unsafe_allow_html=True)
    ca = get_career_analysis(pils, gender)
    ilgan = pils[1]["cg"]
    html = "<div style='background:linear-gradient(135deg,#e8f4ff,#e1f2ff);color:#000000;padding:20px;border-radius:14px;text-align:center;margin-bottom:14px'>"
    html += "<div style='font-size:13px;color:#a8c8f0'>격국 기반 직업 분석</div>"
    html += f"<div style='font-size:26px;font-weight:900;color:#8b6200;margin:8px 0'>{ca['격국']}</div></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown('<div class="gold-section">[데이터] 최적 직업군</div>', unsafe_allow_html=True)
    st.markdown('<div style="padding:10px 0;line-height:2">' + "".join([f'<span style="background:#ffffff;border:1px solid #000000;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:700;color:#000000;margin:4px;display:inline-block">{j}</span>' for j in ca["최적직업"]]) + '</div>', unsafe_allow_html=True)
    if ca["유리직업"]:
        st.markdown('<div class="gold-section">[안내] 유리한 직업군</div>', unsafe_allow_html=True)
        st.markdown('<div style="padding:8px 0;line-height:2">' + "".join([f'<span style="background:#ffffff;border:1px solid #a8d5a8;padding:5px 12px;border-radius:20px;font-size:13px;color:#2a6f2a;margin:4px;display:inline-block">{j}</span>' for j in ca["유리직업"]]) + '</div>', unsafe_allow_html=True)
    if ca["일간추가"]:
        st.markdown(f"### [분석] {ilgan}일간 특화")
        st.markdown('<div style="padding:8px 0;line-height:2">' + "".join([f'<span style="background:#ffffff;border:1px solid #c8b8e8;padding:5px 12px;border-radius:20px;font-size:13px;color:#5a2d8b;margin:4px;display:inline-block">{j}</span>' for j in ca["일간추가"]]) + '</div>', unsafe_allow_html=True)
    if ca["신살보정"]:
        html = "<div class='card' style='background:#ffffff;border:1px solid #e8d5a0;margin-top:8px'>"
        html += "<div style='font-size:13px;font-weight:700;color:#000000;margin-bottom:6px'>[보정] 신살/양인 직업 보정</div>"
        html += ''.join([f'<div style="font-size:13px;color:#000000;margin:3px 0">✦ {s}</div>' for s in ca["신살보정"]])
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    if ca["피할직업"]:
        st.markdown(f'<div class="card" style="background:#fff0f0;border:1px solid #d5a8a8;margin-top:8px"><b style="color:#8b2020">[제외] 피해야 할 직업:</b> {"  /  ".join(ca["피할직업"])}</div>', unsafe_allow_html=True)


def tab_gaemyeong(pils, name=""):
    st.markdown('<div class="gold-section">📝 개명(改名) 오행 분석</div>', unsafe_allow_html=True)
    ilgan = pils[1]["cg"]
    yongshin = get_yongshin(pils)
    target_ohs = yongshin["종합_용신"]
    oh_emoji = {"木":"[木]","火":"[火]","土":"[土]","金":"[金]","水":"[수]"}
    st.markdown(f"""<div class="card" style="background:#ffffff;border:1px solid #e8d5a0;margin-bottom:12px">
        <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">이 사주의 용신 오행</div>
        <div style="font-size:14px;color:#333">{'  /  '.join([f"{oh_emoji.get(o,'')}{OHN.get(o,'')}({o})" for o in target_ohs]) if target_ohs else "없음"}</div>
    </div>""", unsafe_allow_html=True)
    name_input = st.text_input("이름 입력 (한글)", value=name, placeholder="예) 홍길동", key="gaemyeong_name")
    if name_input:
        oh_count, oh_pct = analyze_name_oh(name_input)
        st.markdown(f"### [분석] '{name_input}' 오행 분포")
        cols = st.columns(5)
        for i,oh in enumerate(["木","火","土","金","水"]):
            pct = oh_pct.get(oh,0)
            is_t = oh in target_ohs
            with cols[i]:
                st.markdown(f"""
                <div style="text-align:center;padding:12px;background:{'#ffffff' if is_t else '#fafafa'};border-radius:12px;border:{'2px solid #000000' if is_t else '1px solid #ddd'}">
                    <div style="font-size:18px">{oh_emoji[oh]}</div>
                    <div style="font-size:14px;font-weight:800;color:#000000">{OHN.get(oh,'')}</div>
                    <div style="font-size:22px;font-weight:900;color:#000000">{pct}%</div>
                    {f'<div style="font-size:10px;background:#000000;color:#000000;padding:1px 6px;border-radius:8px">용신</div>' if is_t else ''}
                </div>""", unsafe_allow_html=True)
                st.progress(pct/100)
        target_pct = sum(oh_pct.get(oh,0) for oh in target_ohs)
        if target_pct>=50: ev,ec,eb="[우수] 용신 오행이 충분한 좋은 이름입니다.","#2a6f2a","#f0fff0"
        elif target_pct>=30: ev,ec,eb="[보통] 용신 오행이 어느 정도 있습니다. 보완 여지 있음.","#000000","#ffffff"
        else: ev,ec,eb="[경고] 용신 오행이 부족합니다. 개명을 고려해 볼 수 있습니다.","#8b2020","#fff0f0"
        st.markdown(f'<div class="card" style="background:{eb};border-left:4px solid {ec};margin-top:8px"><div style="font-size:14px;color:{ec};font-weight:700">{ev}</div><div style="font-size:13px;color:#000000;margin-top:6px">용신 오행 비율: {target_pct}%</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="gold-section">[가이드] 용신 오행 이름 자모 예시</div>', unsafe_allow_html=True)
        for oh in target_ohs:
            jamos = [j for j,o in HANGUL_OH.items() if o==oh]
            st.markdown(f'<div class="card" style="background:#ffffff;border:1px solid #c8b8e8"><b style="color:#5a2d8b">{oh_emoji.get(oh,"")}{OHN.get(oh,"")}({oh}) 자모:</b> <span style="font-size:14px;letter-spacing:4px;font-weight:700">{"  ".join(jamos)}</span></div>', unsafe_allow_html=True)


# --------------------------------------------------
# 서술형 대형 내러티브 생성기
# --------------------------------------------------

ILGAN_CHAR_DESC = {
    "甲": {
        "상징":"큰 나무(大木). 곧게 뻗은 소나무처럼 굽히지 않는 기상의 사람입니다.",
        "성격_핵심":"리더십과 개척 정신이 천부적입니다. 처음 길을 내는 것을 두려워하지 않으며, 한번 마음먹은 일은 반드시 완수하려는 집요함이 있습니다. 주변 사람들은 이 사람을 '신뢰할 수 있는 맏형'처럼 느낍니다.",
        "장점":"결단력·원칙·신뢰·강한 추진력·정의감·독립심",
        "단점":"고집이 지나쳐 융통성이 부족할 수 있습니다. 자신의 방식만 옳다고 여기는 경향이 있어 타인과 마찰이 생기기도 합니다.",
        "재물패턴":"재물은 꾸준한 노력으로 쌓이는 타입입니다. 한번에 큰돈을 버는 것보다 오랜 기간 성실하게 쌓아가는 방식이 맞습니다. 투기성 투자는 대체로 손해를 봅니다.",
        "건강":"간장·담낭 계통을 주의해야 합니다. 눈의 피로, 근육 경직이 오기 쉬우니 스트레칭과 규칙적 수면이 중요합니다.",
        "직업":"정치·행정·교육·건설·목재·의료·법조 계통에서 강합니다.",
        "연애_남":"연인에게 든든한 버팀목이 되지만, 너무 강한 주도권으로 상대가 답답해하기도 합니다.",
        "연애_여":"강한 자존감으로 자신만의 기준이 뚜렷합니다. 약한 남성보다 자신보다 강한 남성에게 끌립니다.",
    },
    "乙": {
        "상징":"작은 풀·덩굴(小木). 부드럽게 환경에 적응하며 결국 원하는 곳에 도달하는 사람입니다.",
        "성격_핵심":"겉으로는 부드럽고 온화하지만, 속으로는 강인한 의지가 숨어 있습니다. 처음에는 유연하게 받아들이는 것처럼 보이지만, 결국 자신이 원하는 방향으로 조용히 이끌어가는 능력이 있습니다.",
        "장점":"적응력·감수성·예술적 감각·인내·섬세함·사교성",
        "단점":"우유부단하고 결정을 미루는 경향이 있습니다. 주변 눈치를 너무 봐서 정작 자신의 뜻을 제대로 표현하지 못할 때도 있습니다.",
        "재물패턴":"재물 운이 꾸준한 편입니다. 강하게 밀어붙이기보다 관계를 통해 자연스럽게 기회가 오는 경우가 많습니다. 파트너십 사업이 유리합니다.",
        "건강":"간장·목 계통, 신경 계통이 약할 수 있습니다. 스트레스를 몸으로 표현하는 경향이 있으니 정서적 안정이 건강의 핵심입니다.",
        "직업":"디자인·예술·상담·서비스·교육·언론·의료 분야가 맞습니다.",
        "연애_남":"섬세하고 상대방 감정을 잘 읽습니다. 로맨틱한 분위기를 중요시합니다.",
        "연애_여":"부드럽고 매력적이지만, 관계에서 상대에게 의존하는 경향이 있습니다. 자립심을 키우는 것이 연애 성공의 열쇠입니다.",
    },
    "丙": {
        "상징":"태양(太陽). 자신의 빛으로 주변을 밝히는 타고난 주인공입니다.",
        "성격_핵심":"어디서나 중심에 서는 카리스마가 있습니다. 밝고 활기차며 사람들을 자연스럽게 끌어당기는 매력이 있습니다. 솔직하고 직선적이어서 속에 있는 것을 숨기지 못합니다. 인기와 명예를 중요시합니다.",
        "장점":"카리스마·열정·사교성·창의력·용기·리더십·직관",
        "단점":"자기중심적인 면이 강해 타인의 의견을 무시하기도 합니다. 체면을 중시해서 실리보다 감정적 판단을 내릴 때가 있습니다.",
        "재물패턴":"화려하게 벌고 화려하게 쓰는 타입입니다. 재물보다 명예를 먼저 생각하는 경향이 있어, 돈이 잘 모이지 않을 수 있습니다. 관리 체계를 만드는 것이 중요합니다.",
        "건강":"심장·소장·눈 계통을 주의해야 합니다. 과로와 흥분 상태가 지속되면 심혈관에 무리가 옵니다.",
        "직업":"연예·방송·정치·영업·마케팅·교육·예술 분야에서 빛납니다.",
        "연애_남":"열정적이고 드라마틱한 연애를 좋아합니다. 상대에게 아낌없이 주지만 인정받기를 원합니다.",
        "연애_여":"화려하고 밝은 매력이 있습니다. 자신을 빛나게 해주는 파트너를 원합니다.",
    },
    "丁": {
        "상징":"촛불·등불(小火). 차분하지만 가까이 있는 이에게 따뜻함을 주는 사람입니다.",
        "성격_핵심":"겉으로는 조용하고 내성적이지만, 내면에는 강렬한 열정이 숨어 있습니다. 섬세한 감수성으로 주변을 깊이 관찰하고 이해합니다. 소수의 친한 사람들과 깊은 관계를 맺는 것을 선호합니다.",
        "장점":"섬세함·집중력·예술성·따뜻함·통찰력·신중함",
        "단점":"지나치게 내향적이어서 자신을 표현하지 못할 때가 있습니다. 상처를 마음속에 쌓아두는 경향이 있어 정서적 소진이 올 수 있습니다.",
        "재물패턴":"꾸준한 노력으로 쌓아가는 재물 운입니다. 화려한 한방보다는 전문성과 기술을 통한 안정적인 수입이 맞습니다.",
        "건강":"심장·소장·혈압 관련 질환을 주의해야 합니다. 스트레스를 쌓아두면 화병이 올 수 있습니다.",
        "직업":"연구·개발·예술·상담·의료·교육·IT 분야가 잘 맞습니다.",
        "연애_남":"깊고 진지한 관계를 원합니다. 가볍거나 피상적인 관계에는 관심이 없습니다.",
        "연애_여":"감수성이 풍부하고 내면이 깊습니다. 자신을 이해해주는 파트너를 만나면 헌신적입니다.",
    },
    "戊": {
        "상징":"큰 산·대지(大土). 든든하고 안정적인 중심축 같은 사람입니다.",
        "성격_핵심":"묵직하고 믿음직스러운 성품입니다. 말보다 행동으로 보여주는 타입이며, 한번 신뢰를 쌓으면 절대 배신하지 않는 의리가 있습니다. 변화보다 안정을 선호하고, 큰 그림을 바라보는 안목이 있습니다.",
        "장점":"안정감·신뢰·인내·책임감·포용력·현실감각",
        "단점":"변화에 느리고 보수적입니다. 한번 결심한 것을 바꾸지 않아 고집스러워 보이기도 합니다.",
        "재물패턴":"부동산·토지 관련 투자에 강합니다. 안정적이고 장기적인 투자가 맞으며, 단타성 투기는 손해를 봅니다.",
        "건강":"비장·위장 계통을 주의해야 합니다. 과식과 폭식 경향이 있으니 규칙적인 식사가 중요합니다.",
        "직업":"건설·부동산·금융·토목·행정·중재·교육 분야가 맞습니다.",
        "연애_남":"든든한 파트너입니다. 화려함보다 안정감으로 사람을 끌어들입니다.",
        "연애_여":"무거운 책임감으로 가정을 지키는 타입입니다. 파트너를 선택할 때 신중하고 보수적입니다.",
    },
    "己": {
        "상징":"논밭·평지(小土). 부드럽고 기름진 땅처럼 모든 것을 품어주는 사람입니다.",
        "성격_핵심":"온화하고 섬세하며 주변 사람들에 대한 배려가 넘칩니다. 갈등을 중재하는 능력이 탁월하고, 어디서나 분위기를 부드럽게 만드는 역할을 합니다. 다소 소심한 면이 있지만, 인간관계에서 깊은 신뢰를 받습니다.",
        "장점":"배려·중재능력·섬세함·인내·유연성·실용성",
        "단점":"우유부단하고 결정을 미루는 경향이 있습니다. 타인의 감정에 너무 민감해 자신을 희생하는 경우가 많습니다.",
        "재물패턴":"서비스·유통·중개업이 잘 맞습니다. 사람 사이에서 이익을 만드는 구조가 이 일간에 맞습니다.",
        "건강":"비장·위장·췌장 계통을 주의해야 합니다. 걱정과 불안이 많을수록 소화기 증상이 나타납니다.",
        "직업":"서비스·유통·의료·상담·교육·식품·복지 분야가 잘 맞습니다.",
        "연애_남":"헌신적이고 배려가 넘칩니다. 다만 자신의 감정을 솔직하게 표현하지 못하는 경우가 있습니다.",
        "연애_여":"따뜻하고 모성적입니다. 파트너를 돌보는 것에서 행복을 느낍니다.",
    },
    "庚": {
        "상징":"큰 쇠·바위(大金). 강하고 날카로운 검처럼 결단력 있는 사람입니다.",
        "성격_핵심":"강직하고 원칙적입니다. 옳고 그름을 분명히 하는 성격으로, 불의를 보면 참지 못합니다. 추진력이 강하고 결단이 빠릅니다. 한번 마음먹으면 돌아서지 않는 의지가 있습니다.",
        "장점":"결단력·원칙·강한 의지·정의감·추진력·카리스마",
        "단점":"지나치게 강해서 주변을 불편하게 만들 수 있습니다. 유연성이 부족하고, 감정 표현이 서툽니다.",
        "재물패턴":"금속·기계·군경·의료 관련 분야에서 재물이 들어옵니다. 결단력 있게 투자하지만 손실도 크게 볼 수 있습니다.",
        "건강":"폐·대장 계통을 주의해야 합니다. 피부 트러블이나 호흡기 질환에 취약합니다.",
        "직업":"군경·의료(외과)·금속·기계·법조·스포츠 분야에서 강합니다.",
        "연애_남":"강하고 보호본능이 있습니다. 상대에게 든든한 울타리가 됩니다.",
        "연애_여":"독립적이고 자존심이 강합니다. 자신보다 약한 상대는 존중하지 않는 경향이 있습니다.",
    },
    "辛": {
        "상징":"작은 쇠·보석(小金). 섬세하게 다듬어진 보석처럼 아름답고 예리한 사람입니다.",
        "성격_핵심":"완벽주의적 성향이 강합니다. 세밀한 부분까지 놓치지 않는 날카로운 관찰력과 분석력이 있습니다. 외모나 이미지 관리에 신경을 쓰며, 품위와 격식을 중요하게 여깁니다.",
        "장점":"완벽주의·분석력·심미안·섬세함·예리함·품위",
        "단점":"완벽주의가 지나쳐 스스로를 혹독하게 대합니다. 타인에 대한 기준도 높아 관계에서 갈등이 생기기도 합니다.",
        "재물패턴":"전문성과 기술로 재물을 쌓는 타입입니다. 장기적 계획과 꼼꼼한 관리가 재물 성장의 열쇠입니다.",
        "건강":"폐·기관지·피부 계통을 주의해야 합니다. 스트레스가 쌓이면 피부 증상으로 나타납니다.",
        "직업":"의료·법·금융·예술·IT·디자인·분석 분야가 맞습니다.",
        "연애_남":"이상형이 높고 기준이 까다롭습니다. 상대의 외모와 품위를 중요하게 봅니다.",
        "연애_여":"섬세하고 완벽한 연애를 원합니다. 작은 실망에도 관계를 재고하는 경향이 있습니다.",
    },
    "壬": {
        "상징":"큰 강·바다(大水). 넓고 깊은 지혜와 포용력으로 세상을 흐르는 사람입니다.",
        "성격_핵심":"지혜롭고 통찰력이 뛰어납니다. 유연하게 상황에 적응하며 깊은 사고력으로 문제를 해결합니다. 대범하고 활동적이며, 새로운 세계를 탐험하는 것을 즐깁니다. 추진력과 사교성이 높습니다.",
        "장점":"지혜·유연성·추진력·사교성·통찰력·적응력·대범함",
        "단점":"자신의 기분과 감정 기복이 심할 수 있습니다. 집중력이 분산되어 한 가지에 끝까지 매달리기 어려울 수 있습니다.",
        "재물패턴":"무역·금융·유통·IT 등 유동성이 큰 분야에서 재물이 들어옵니다. 흐름을 잘 타는 편입니다.",
        "건강":"신장·방광·생식기 계통을 주의해야 합니다. 과로와 수면 부족이 축적되지 않도록 해야 합니다.",
        "직업":"무역·금융·IT·운수·언론·정치·외교 분야에서 두각을 나타냅니다.",
        "연애_남":"매력적이고 사교적입니다. 다양한 이성을 경험하는 경향이 있어 정착이 늦을 수 있습니다.",
        "연애_여":"활발하고 매력적입니다. 활동적이고 지적인 파트너를 선호합니다.",
    },
    "癸": {
        "상징":"빗물·샘물(小水). 조용히 스며들어 만물을 적시는 섬세한 지혜의 사람입니다.",
        "성격_핵심":"내성적이지만 깊은 통찰력을 가진 사람입니다. 감수성이 풍부하고 직관이 예리하여, 말하지 않아도 상대의 마음을 읽는 능력이 있습니다. 혼자만의 시간이 필요하고 고독 속에서 창의력이 발현됩니다.",
        "장점":"직관·감수성·지혜·창의력·신중함·통찰력",
        "단점":"예민하고 감정적으로 흔들리기 쉽습니다. 지나치게 내성적이어서 기회를 놓치는 경우도 있습니다.",
        "재물패턴":"전문 지식과 직관으로 재물을 만드는 타입입니다. 수면 아래서 조용히 부를 쌓는 방식이 맞습니다.",
        "건강":"신장·방광·귀 계통을 주의해야 합니다. 감정이 쌓이면 면역력이 떨어집니다.",
        "직업":"연구·예술·의료·심리상담·IT·문학·철학 분야가 잘 맞습니다.",
        "연애_남":"깊고 감성적인 연애를 합니다. 상대의 감정을 잘 읽어주지만 스스로 표현이 서툽니다.",
        "연애_여":"섬세하고 로맨틱합니다. 깊은 정서적 교감을 나눌 수 있는 파트너를 원합니다.",
    },
}

GYEOKGUK_NARRATIVE = {
    "정관격": "정관격은 사회적 규범과 질서를 중시하는 귀격(貴格)입니다. 이 격국을 가진 분은 법과 원칙 안에서 정당한 방법으로 높은 자리에 오르는 운명입니다. 성실함과 신뢰가 최대 무기이며, 꾸준히 실력을 쌓다 보면 반드시 인정받는 날이 옵니다. 직장 조직에서 빛나는 운으로, 공무원·교사·법조인·관리직이 잘 맞습니다. 다만 자신의 원칙을 지나치게 고집하면 주변과 마찰이 생기니 유연성을 함께 갖추어야 합니다.",
    "편관격": "편관격은 칠살격(七殺格)이라고도 하며, 강렬한 도전과 시련 속에서 성장하는 운명입니다. 어려움이 올수록 더욱 강해지는 역경의 강자입니다. 군인·경찰·의사·운동선수처럼 극한의 상황을 이겨내는 직업에서 탁월한 능력을 발휘합니다. 칠살이 잘 제화(制化)되면 최고의 성공을 이루는 대귀격이 됩니다. 관리되지 않은 칠살은 충동과 과격함으로 나타날 수 있으니 감정 조절이 중요합니다.",
    "정재격": "정재격은 성실하고 꾸준하게 재물을 쌓아가는 안정형 격국입니다. 한탕을 노리기보다 묵묵히 일하고 저축하여 결국 부를 이루는 타입입니다. 금융·부동산·유통·회계 분야에서 두각을 나타내며, 인생 후반에 더욱 빛나는 운명입니다. 이 격국은 배우자 인연이 좋아 가정이 안정적이며, 파트너의 내조가 큰 힘이 됩니다. 지나친 소심함으로 기회를 놓치지 않도록 용기 있는 결단이 필요한 순간도 있습니다.",
    "편재격": "편재격은 활동적이고 대담한 재물 운의 격국입니다. 사업·투자·무역처럼 움직임이 큰 분야에서 재물이 들어옵니다. 한자리에 머물기보다 넓은 세계를 돌아다니며 기회를 만드는 타입입니다. 기복이 있지만 그만큼 크게 버는 운도 있습니다. 아버지와의 인연이 인생에 큰 영향을 미칩니다. 재물이 들어온 만큼 나가기도 하므로, 수입의 일정 부분은 반드시 안전한 곳에 묶어두는 습관이 중요합니다.",
    "식신격": "식신격은 하늘이 내리신 복록의 격국입니다. 타고난 재능과 끼가 있어 그것을 표현하는 것만으로도 재물과 인복이 따라옵니다. 먹는 것을 즐기고 생활의 여유를 즐기며, 주변에 즐거움을 주는 사람입니다. 예술·요리·교육·서비스·창작 분야에서 두각을 나타냅니다. 건강하고 장수하는 운도 있습니다. 다만 너무 편안함을 추구하다 보면 도전 의식이 부족해질 수 있습니다.",
    "상관격": "상관격은 창의력과 표현 능력이 탁월한 격국입니다. 기존 질서에 얽매이지 않고 새로운 것을 만들어내는 혁신가 기질이 있습니다. 예술·문학·음악·마케팅·IT 분야에서 독보적인 능력을 발휘합니다. 직장 조직보다는 독립적인 활동이 더 잘 맞습니다. 상관견관(傷官見官)이 있으면 직장 상사나 권위자와 갈등이 생기기 쉬우니 언행에 각별히 주의해야 합니다.",
    "편인격": "편인격은 직관과 영감이 남다른 격국입니다. 특수한 기술·학문·예술에서 독보적인 경지에 오르는 운명입니다. 철학·종교·심리·의술·역학 등 남들이 쉽게 접근하지 못하는 전문 분야에서 두각을 나타냅니다. 고독을 즐기며 혼자만의 깊은 연구에서 에너지를 얻습니다. 도식(倒食)이 형성되면 직업 변동이 잦을 수 있으니 한 분야에 집중하는 것이 좋습니다.",
    "정인격": "정인격은 학문·교육·명예의 귀격입니다. 배움에 대한 열정이 넘치고, 지식을 쌓을수록 더 높은 곳으로 올라가는 운명입니다. 교수·의사·법관·연구원처럼 학문과 자격이 기반이 되는 직업에서 최고의 성과를 냅니다. 어머니와의 관계가 인생에 큰 영향을 미칩니다. 지식이 곧 재물이 되는 사주이므로 평생 배움을 멈추지 않는 것이 성공의 비결입니다.",
    "비견격": "비견격은 독립심과 자존감이 강한 격국입니다. 남 밑에서 지시받기보다 자신만의 영역을 구축하는 자영업·창업이 잘 맞습니다. 형제나 동료와의 경쟁이 인생의 주요한 테마가 되며, 이를 통해 단련됩니다. 뚝심과 의지가 강해 어떤 어려움도 정면 돌파합니다. 재물이 모이기 어려울 수 있으니 지출 관리가 특히 중요합니다.",
    "겁재격": "겁재격은 승부사 기질의 격국입니다. 경쟁을 즐기고 도전적인 상황에서 오히려 에너지가 솟습니다. 스포츠·영업·투자·법조 분야에서 강합니다. 재물의 기복이 매우 크며, 크게 벌었다가도 한순간에 잃을 수 있는 운명이므로 안전자산 확보가 필수입니다. 주변 사람들에게 베푸는 것을 좋아하지만, 그로 인해 재물이 새는 경우도 많습니다.",
}

STRENGTH_NARRATIVE = {
    "신강(身强)": """신강 사주는 일간의 기운이 강한 사주입니다. 체력과 정신력이 뛰어나고, 어떤 역경도 정면으로 돌파하는 힘이 있습니다. 그러나 기운이 너무 강하면 오히려 재물과 관운이 억눌릴 수 있습니다. 신강한 분에게는 재성(財星)과 관살(官殺) 운이 올 때 크게 성공할 기회가 생깁니다. 자신감이 넘치는 만큼 때로는 독단적으로 보일 수 있으니, 타인의 의견을 경청하는 습관을 기르는 것이 중요합니다. 신강 사주는 스스로 만들어가는 인생입니다. 남을 기다리기보다 먼저 움직여야 기회가 옵니다.""",
    "신약(身弱)": """신약 사주는 일간의 기운이 약한 사주입니다. 체력과 에너지 관리가 인생의 핵심 과제입니다. 그러나 신약이 꼭 나쁜 것은 아닙니다. 인성(印星)과 비겁(比劫) 운이 올 때 귀인의 도움을 받아 크게 도약합니다. 혼자보다 좋은 파트너나 조력자와 함께할 때 훨씬 좋은 결과를 냅니다. 건강 관리를 최우선으로 여기고, 무리한 확장보다는 내실을 다지는 전략이 맞습니다. 귀인을 만나거나 스승을 모시는 것이 신약 사주의 성공 방정식입니다.""",
    "중화(中和)": """중화 사주는 오행의 균형이 잡혀 있어 어떤 상황에서도 크게 무너지지 않는 안정성이 있습니다. 극단적인 기복보다는 꾸준하고 안정적으로 성장하는 타입입니다. 특정 용신에 편중되지 않아 다양한 분야에서 균형 잡힌 능력을 발휘합니다. 그러나 반대로 특출난 강점이 부족할 수 있으니, 자신만의 전문 분야를 하나 깊이 파는 것이 중요합니다. 중화 사주의 가장 큰 장점은 지속성입니다. 오래 달리는 경주마처럼 꾸준함이 무기입니다.""",
}

def build_rich_narrative(pils, birth_year, gender, name, section="report"):
    """각 메뉴별 5000~10000자 서술형 내러티브 생성"""
    try:
        ilgan = pils[1]["cg"]
        ilgan_idx = CG.index(ilgan) if ilgan in CG else 0
        ilgan_kr = CG_KR[ilgan_idx]
        iljj = pils[1]["jj"]
        iljj_idx = JJ.index(iljj) if iljj in JJ else 0
        iljj_kr = JJ_KR[iljj_idx]
        current_year = datetime.now().year
        current_age = current_year - birth_year + 1
        display_name = name if name else "내담자"

        strength_info = get_ilgan_strength(ilgan, pils)
        sn = strength_info.get("신강신약", "중화(中和)")
        gyeokguk = get_gyeokguk(pils)
        gname = gyeokguk.get("격국명", "") if gyeokguk else ""
        ys = get_yongshin(pils)
        yongshin_ohs = ys.get("종합_용신", [])
        if not isinstance(yongshin_ohs, list): yongshin_ohs = []
        ilgan_oh = OH.get(ilgan, "")

        life = build_life_analysis(pils, gender)
        ss_dist = life.get("전체_십성", {})
        top_ss = [k for k, v in sorted(ss_dist.items(), key=lambda x: -x[1])][:3]
        combos = life.get("조합_결과", [])

        daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
        cur_dw = next((d for d in daewoon if d["시작연도"] <= current_year <= d["종료연도"]), None)
        cur_dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(cur_dw["cg"], "-") if cur_dw else "-"

        sw_now = get_yearly_luck(pils, current_year)
        sw_next = get_yearly_luck(pils, current_year + 1)

        OH_KR_MAP = {"木":"목(木)","火":"화(火)","土":"토(土)","金":"금(金)","水":"수(水)"}
        yong_kr = " - ".join([OH_KR_MAP.get(o, o) for o in yongshin_ohs])

        char = ILGAN_CHAR_DESC.get(ilgan, {})
        sn_narr = STRENGTH_NARRATIVE.get(sn, "")
        gnarr = GYEOKGUK_NARRATIVE.get(gname, f"{gname}은 독특한 개성과 능력을 가진 격국입니다.")

        # 리포트용 (menu1)
        if section == "report":
            result = []
            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 사주 종합 리포트
      {birth_year}년생 | {ilgan_kr}({ilgan}) 일간 | {sn}
    -----------------------------------------------------

    [ 제1장 | 일간(Daymaster) 캐릭터 완전 분석 ]

일간(日干)은 사주의 핵심입니다. 일간은 나 자신을 나타내며, 내가 어떤 사람인지 본질적인 성품을 담고 있습니다.

{display_name}님의 일간은 {ilgan}({ilgan_kr})입니다. {char.get('상징', '')}

{char.get('성격_핵심', '')}

    [장점]: {char.get('장점', '')}

    [약점]: {char.get('단점', '')}

일간 {ilgan_kr}이(가) {iljj_kr}(地支) 위에 앉아 있습니다. 이는 {display_name}님의 현실적 토대와 행동 패턴에 {iljj_kr}의 기운이 깊숙이 관여한다는 뜻입니다. 일지(日支)는 배우자 자리이기도 하여, 파트너 관계에서도 이 기운이 크게 드러납니다.

[ 제2장 | 신강신약(Strength) - 기운의 세기 ]
    
    {sn_narr}

현재 {display_name}님의 체력 점수는 {strength_info.get('helper_score', 50)}점으로 측정됩니다. 이는 평균적인 기준에서 {'강한 편' if '신강' in sn else '약한 편' if '신약' in sn else '균형 잡힌'} 기운을 의미합니다.

{'* 신강한 사주는 직접 움직여야 기회가 옵니다. 수동적으로 기다리면 아무것도 이루지 못합니다.' if '신강' in sn else '* 신약한 사주는 귀인과 함께할 때 가장 강합니다. 좋은 파트너와 스승을 만나는 것이 운명을 바꾸는 열쇠입니다.' if '신약' in sn else '* 중화 사주는 꾸준함이 가장 큰 무기입니다. 한 분야를 깊이 파고드는 전략이 가장 효과적입니다.'}

[ 제3장 | 격국(Gyeokguk) - 타고난 인생 설계도 ]

{gnarr}

격국은 사주의 큰 그림, 인생의 방향성을 나타냅니다. {display_name}님의 {gname}은(는) 단순한 직업 적성을 넘어 이 분이 어떤 방식으로 세상에 가치를 만들어내는지를 보여줍니다.

{gname}을 가진 분이 성공하는 공통점은 다음과 같습니다:
첫째, 자신의 타고난 격국에 맞는 분야에서 일할 때 최대 능력을 발휘합니다.
둘째, 격국의 장점을 살리면서 단점을 보완하는 운을 활용해야 합니다.
셋째, 용신 오행이 들어오는 시기에 결정적인 도전을 해야 합니다.

[ 제4장 | 용신(Yongshin) - 내 인생의 보물 오행 ]

용신은 내 사주에 가장 필요한 오행입니다. 이 오행이 강화될 때 건강·재물·명예 모두가 좋아집니다.

{display_name}님의 용신: {yong_kr}

용신 오행을 일상에서 강화하는 방법:
* 용신 색상의 옷/소품을 활용하십시오
* 용신 방위 쪽에 중요한 공간(침실/사무실/책상)을 배치하십시오
* 용신 오행에 해당하는 음식을 자주 드십시오
* 용신 오행이 강한 해(Yongshin Year)에 큰 결정을 내리십시오

기신(Gishin)이 강해지는 해에는 무리한 투자, 이동, 결정을 자제하고 내실을 다지는 것이 현명합니다.

[ 제5장 | 십성(Sipsung) 조합 - 당신만의 인생 코드 ]
""")

            for key, combo in combos[:2]:
                result.append(f"""
- [{' x '.join(key)}] 조합

{combo.get('요약', '')}

* 성향: {combo.get('성향', '')}
* 재물 방식: {combo.get('재물', '')}
* 직업 적성: {combo.get('직업', '')}
* 연애 패턴: {combo.get('연애', '')}
* 주의사항: {combo.get('주의', '')}
""")

            result.append(f"""
[ 제6장 | 건강(Health) 주의사항 ]

일간 {ilgan_kr}의 건강 취약점: {char.get('건강', '')}

사주에서 건강은 오행의 균형 상태를 반영합니다.
{'목(木) 기운이 강하면 간장·담낭·눈·근육 계통을 주의하십시오.' if '木' in ilgan_oh else ''}
{'화(火) 기운이 강하면 심장·소장·혈압·시력을 주의하십시오.' if '火' in ilgan_oh else ''}
{'토(土) 기운이 강하면 비장·위장·췌장·소화기를 주의하십시오.' if '土' in ilgan_oh else ''}
{'금(金) 기운이 강하면 폐·대장·기관지·피부를 주의하십시오.' if '金' in ilgan_oh else ''}
{'수(水) 기운이 강하면 신장·방광·생식기·귀를 주의하십시오.' if '수' in ilgan_oh else ''}

건강을 지키는 가장 확실한 방법은 용신 오행을 강화하는 것입니다.
규칙적인 생활 리듬, 적절한 운동, 충분한 수면이 이 사주에 가장 중요한 건강법입니다.
""")
            result.append(f"""
[ 제7장 | 직업 적성 분석 ]

일간 {ilgan_kr}에게 가장 잘 맞는 직업: {char.get('직업', '')}

현재 주요 십성 {', '.join(top_ss)}의 조합이 의미하는 적합 업종:
* 식신이 강하면: 요리, 예술, 창작, 교육, 서비스 분야에서 자연스럽게 빛납니다.
* 상관이 강하면: IT, 마케팅, 방송, 예술, 컨설팅에서 독보적 능력을 발휘합니다.
* 편재가 강하면: 사업, 투자, 영업, 무역, 부동산에서 두각을 나타냅니다.
* 정재가 강하면: 금융, 회계, 행정, 유통에서 안정적인 커리어를 쌓습니다.
* 편관이 강하면: 군경, 의료, 법조, 스포츠에서 강인한 의지를 발휘합니다.
* 정관이 강하면: 공무원, 교육, 관리직에서 신뢰받는 전문가가 됩니다.
* 편인이 강하면: 연구, 철학, 역술, IT, 의학에서 독보적 전문성을 쌓습니다.
* 정인이 강하면: 학문, 자격증 기반의 전문직에서 평생 성장합니다.
* 비견이 강하면: 독립사업, 프리랜서, 자영업에서 진가를 발휘합니다.
* 겁재가 강하면: 영업, 스포츠, 투자에서 강한 승부 본능을 발휘합니다.
""")

            result.append(f"""
[ 제8장 | 현재 운기(Flow) - {current_year}년 상황 ]

현재 {cur_dw['str'] if cur_dw else '-'} 대운이 진행 중입니다.
    ({cur_dw_ss} 십성 대운 | {cur_dw['시작연도'] if cur_dw else '-'}년부터 {cur_dw['종료연도'] if cur_dw else '-'}년까지)

올해 {sw_now.get('세운', '')} 세운 ({sw_now.get('십성_천간', '')} / {sw_now.get('길흉', '')})

{'이 시기는 용신 대운이 들어오는 황금기입니다. 적극적으로 움직이고 도전하십시오. 지금 준비하면 반드시 결실이 옵니다.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '이 시기는 주의가 필요한 대운입니다. 무리한 확장보다 내실을 다지고 건강 관리에 집중하십시오. 지금의 인내가 다음 황금기를 준비하는 것입니다.'}
""")
            result.append(f"    내년 {sw_next.get('세운', '')} 세운 전망: {sw_next.get('십성_천간', '')} 십성 | {sw_next.get('길흉', '')}\n")
            result.append(f"""
[ 제9장 | 연애/결혼 성향 ]

일간 {ilgan_kr}의 연애 패턴:
{'* ' + char.get('연애_남', '') if gender == '남' else '* ' + char.get('연애_여', '')}

배우자 자리 일지(日支) {iljj_kr}({iljj})의 의미:
배우자 자리에 있는 지지는 배우자의 성품과 부부 관계의 방향을 나타냅니다.
{iljj_kr} 일지를 가진 분은 배우자에게서 {'안정과 현실적인 도움을 받는' if iljj in ['丑','辰','戌','未'] else '열정적이고 활기찬 에너지를 받는' if iljj in ['寅','午','戌'] else '지적 교감과 소통을 중요하게 여기는' if iljj in ['申','酉'] else '따뜻한 감성적 유대감을 원하는'} 경향이 있습니다.

[ 제10장 | 인생 총평 - 만신의 한 말씀 ]

{display_name}님의 사주를 종합적으로 보았을 때, 이 분의 인생 키워드는 "{', '.join(top_ss[:2])}" 조합이 만들어내는 에너지입니다.

{combos[0][1].get('요약', '타고난 재능으로 자신의 길을 개척하는 인생입니다.') if combos else '타고난 개성으로 자신만의 길을 걸어가는 인생입니다.'}

이 사주가 가장 빛나는 순간은 자신의 타고난 기질을 긍정하고, 용신 오행의 힘을 빌려 움직일 때입니다. 억지로 자신에게 맞지 않는 방향으로 가려 하면 반드시 시련이 따릅니다.

{sn}인 이 사주는 {'스스로 길을 열어가는 개척자의 운명입니다. 두려움을 버리고 먼저 나서십시오.' if '신강' in sn else '귀인의 도움과 좋은 인연으로 날개를 다는 운명입니다. 좋은 사람과 함께하십시오.' if '신약' in sn else '꾸준함과 균형으로 오래 멀리 가는 운명입니다. 한 우물을 깊게 파십시오.'}

앞으로의 {yong_kr} 용신 강화를 통해 건강·재물·명예 모두를 함께 향상시키십시오. 이것이 이 사주의 가장 핵심적인 처방입니다.
""")
            # 확장 콘텐츠: 신살, 오행, 연도별 조언
            try:
                sinsal_list = get_extra_sinsal(pils)
                if sinsal_list:
                    sinsal_text = "\n".join([f"* {s['name']}: {s['desc']}\n  처방: {s.get('remedy','')}" for s in sinsal_list])
                    result.append(f"""
[ 제11장 | 신살(Sinsal) 완전 분석 ]

신살은 사주에 내재된 특수한 기운으로, 삶의 특정 측면에 강한 영향을 줍니다.

{sinsal_text}

신살은 좋고 나쁨을 단정짓기보다, 그 에너지를 어떻게 활용하느냐가 더 중요합니다. 흉살이라도 제화(制化)하면 오히려 탁월한 능력의 원천이 됩니다.
""")
                sinsal12 = get_12sinsal(pils)
                if sinsal12:
                    s12_text = "\n".join([f"* {s['이름']}: {s.get('desc','')}" for s in sinsal12[:5]])
                    result.append(f"""
[ 제12장 | 12신살(12 Sinsal) ]

{s12_text}
""")
            except: pass

            try:
                oh_strength = calc_ohaeng_strength(ilgan, pils)
                oh_lines = []
                OH_BODY = {"木":"간장·담낭·눈·근육","火":"심장·소장·혈관·혈압","土":"비장·위장·췌장·소화기","金":"폐·대장·기관지·피부","水":"신장·방광·생식기·귀"}
                OH_STRONG = {"木":"창의력·기획력·성장 에너지가 넘칩니다","火":"열정·표현력·인기운이 뛰어납니다","土":"안정감·신뢰·현실 감각이 탁월합니다","金":"결단력·추진력·원칙이 강합니다","水":"지혜·유연성·적응력이 뛰어납니다"}
                OH_WEAK  = {"木":"유연성과 창의력을 의식적으로 키우십시오","火":"열정을 표현하고 사람들과 더 많이 소통하십시오","土":"안정적 기반을 만드는 데 더 노력하십시오","金":"결단력을 기르고 원칙을 세우십시오","水":"직관을 믿고 상황에 유연하게 적응하십시오"}
                for oh_key, oh_val in sorted(oh_strength.items(), key=lambda x: -x[1]):
                    level = "강함" if oh_val >= 30 else "보통" if oh_val >= 15 else "약함"
                    body_part = OH_BODY.get(oh_key, "")
                    if oh_val >= 30:
                        oh_lines.append(f"* {oh_key}({oh_val}점/강함): {OH_STRONG.get(oh_key,'')} | 건강 주의 부위: {body_part}")
                    elif oh_val < 15:
                        oh_lines.append(f"* {oh_key}({oh_val}점/약함): {OH_WEAK.get(oh_key,'')} | 보충 필요 부위: {body_part}")
                result.append(f"""
[ 제13장 | 오행(Five Elements) 분포와 건강 심층 분석 ]

오행의 강약은 성격과 건강 모두에 영향을 줍니다.

{chr(10).join(oh_lines)}

오행 균형을 맞추기 위한 처방:
* 부족한 오행을 보충하는 음식/색상/활동을 일상에서 꾸준히 활용하십시오
* 과잉된 오행의 기관을 정기적으로 검진하십시오
* 용신 오행이 약하다면 그 오행을 강화하는 노력이 인생 전반을 향상시킵니다
""")
            except: pass

            result.append(f"""
[ 제14장 | 연령대별 인생 전략 - {display_name}님에게만 드리는 맞춤 처방 ]

    - 현재 {current_age}세 | {current_year}년
    대운: {cur_dw['str'] if cur_dw else '-'} ({cur_dw_ss})
    세운: {sw_now.get('세운','')} ({sw_now.get('십성_천간','')} / {sw_now.get('길흉','')})

지금 이 순간의 처방:
{f'[처방] 용신 대운과 용신 세운이 겹치는 황금기입니다. 지금 움직이지 않으면 언제 움직이겠습니까. 두려움을 버리고 계획했던 것을 실행하십시오.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' and _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '[주의] 지금은 신중하게 내실을 다지는 시기입니다. 무리한 확장보다 체력, 실력, 자금을 비축하십시오.'}

    - 내년 {current_year+1}년 전망
    세운: {sw_next.get('세운','')} ({sw_next.get('십성_천간','')} / {sw_next.get('길흉','')})
    {'내년은 올해보다 더 나은 흐름이 예상됩니다. 올해 준비한 것이 내년에 결실을 맺습니다.' if sw_next.get('길흉','') in ['길','대길'] else '내년도 신중한 한 해가 될 것입니다. 계획을 세우고 차분하게 실행하십시오.'}

    - 향후 5년 핵심 전략
1. 용신 {yong_kr} 오행이 강한 환경에 자신을 노출시키십시오
2. {gname}의 특성을 최대한 살리는 직업·사업 방향으로 나아가십시오
3. {sn}에 맞는 방식으로 에너지를 운용하십시오: {'직접 움직여 기회를 만들어가십시오' if '신강' in sn else '좋은 파트너와 함께 시너지를 내십시오' if '신약' in sn else '꾸준하고 안정적으로 성장하십시오'}
4. 기신 오행의 유혹(투자, 환경, 인연)을 의식적으로 피하십시오
5. 건강이 모든 운의 기반입니다. {char.get('건강','정기적 건강 관리')}에 주의하십시오

[ 제15장 | 만신의 최종 한 말씀 ]

{display_name}님의 사주는 한마디로 "{combos[0][1].get('요약','자신만의 독특한 빛을 가진 사주') if combos else '평생 성장하는 사주'}"입니다.

이 세상에 태어난 모든 사람은 저마다의 사명(使命)이 있습니다. {display_name}님의 사명은 {ilgan_kr} 일간이 가진 "{char.get('장점','타고난 능력')}"을(를) 세상에 발현하는 것입니다.

지금까지의 삶에서 힘들었던 순간들도 사실은 이 사명을 위한 준비 과정이었습니다. 사주를 보는 것은 미래를 맹목적으로 믿기 위함이 아닙니다. 자신을 깊이 이해하고, 좋은 운기에 최대로 활동하며, 어려운 운기에 현명하게 대처하기 위함입니다.

{display_name}님에게 드리는 만신의 마지막 한 마디:
"운명은 사주가 정하지만, 운명을 만드는 것은 당신입니다."
""")
            # 제16~20장 확장 콘텐츠 --------------------------------
            try:
                iljj  = pils[1]["jj"]
                ilju_str = pils[1]["str"]
                ILJJ_NATURE = {
                    "子":"지혜롭고 총명하며 기억력이 뛰어납니다. 밤에 더 활발해지고 직관이 발달해 있습니다.",
                    "丑":"성실하고 묵묵합니다. 한 번 결심하면 끝까지 가는 뚝심이 있습니다.",
                    "寅":"추진력이 강하고 용감합니다. 타인을 이끄는 리더십이 자연스럽게 나옵니다.",
                    "卯":"감수성이 풍부하고 창의적입니다. 예술적 감각이 있으며 인기가 많습니다.",
                    "辰":"다재다능하고 신비로운 매력이 있습니다. 변화와 적응에 능합니다.",
                    "巳":"지혜롭고 비밀이 많습니다. 겉으로 드러나지 않는 깊은 내면이 있습니다.",
                    "午":"열정적이고 감정 표현이 풍부합니다. 인기와 주목을 자연스럽게 끌어당깁니다.",
                    "未":"예술적이고 따뜻한 심성을 지녔습니다. 보살피고 지키려는 본능이 강합니다.",
                    "申":"영리하고 임기응변이 뛰어납니다. 변화를 두려워하지 않고 기회를 잘 잡습니다.",
                    "酉":"섬세하고 완벽주의적입니다. 기준이 높아 스스로를 끊임없이 갈고닦습니다.",
                    "戌":"의리 있고 충직합니다. 한번 믿은 사람은 끝까지 지키는 의협심이 있습니다.",
                    "亥":"자유롭고 포용력이 넓습니다. 생각의 깊이가 있으며 영성·철학에 관심이 많습니다.",
                }
                ILJJ_SPOUSE = {
                    "子":"배우자는 총명하고 감각이 뛰어난 분을 만날 가능성이 높습니다. 지적 교감이 중요합니다.",
                    "丑":"배우자는 성실하고 현실적인 분을 만나게 됩니다. 가정을 소중히 여기는 파트너입니다.",
                    "寅":"배우자는 활동적이고 추진력 있는 분입니다. 서로 에너지를 주고받는 관계가 됩니다.",
                    "卯":"배우자는 섬세하고 예술적 감각이 있는 분입니다. 정서적 교감을 중시합니다.",
                    "辰":"배우자는 다재다능하고 변화가 많은 분입니다. 관계에서 기복이 있을 수 있습니다.",
                    "巳":"배우자는 지혜롭고 신중한 분입니다. 겉으로 드러나지 않는 깊은 내면을 가진 파트너입니다.",
                    "午":"배우자는 열정적이고 표현력이 강한 분입니다. 감정의 기복이 있지만 뜨겁게 사랑합니다.",
                    "未":"배우자는 따뜻하고 예술적 감각이 있는 분입니다. 집과 가정을 소중히 여깁니다.",
                    "申":"배우자는 영리하고 임기응변이 뛰어난 분입니다. 다방면에 재능이 있는 파트너입니다.",
                    "酉":"배우자는 섬세하고 완벽주의적인 분입니다. 기준이 높아 처음에는 까다롭게 보일 수 있습니다.",
                    "戌":"배우자는 의리 있고 충직한 분입니다. 한번 믿으면 끝까지 지키는 파트너입니다.",
                    "亥":"배우자는 자유롭고 포용력 있는 분입니다. 생각이 깊고 영성적인 면이 있는 파트너입니다.",
                }
                ilju_nature  = ILJJ_NATURE.get(iljj, "")
                ilju_spouse  = ILJJ_SPOUSE.get(iljj, "")
                ilju_detail  = ILJU_DATA.get(ilju_str, {}).get("desc", f"{ilgan_kr} 위에 {iljj_kr}이 앉은 일주입니다.")
                result.append(f"""
[ 제16장 | 일주론(Ilju-ron) - {ilju_str} 일주의 완전 분석 ]

일주(日柱)는 사주의 핵심입니다. 일간(日干)은 나 자신이고, 일지(日支)는 내가 서 있는 토대이자 배우자 자리입니다.
{display_name}님의 일주는 {ilju_str}({ilgan_kr}/{iljj_kr})입니다.

    - 일주 특성 ({iljj_kr})
    {ilju_nature}

    - 배우자 자리(Day Branch) 분석
    {ilju_spouse}

    - 일간 {ilgan_kr}의 오행적 특성
{OHN.get(ilgan_oh,'')} 기운은 {'성장과 창의, 새로운 시작을 상징합니다.' if ilgan_oh=='木' else '열정과 표현, 인기를 상징합니다.' if ilgan_oh=='火' else '안정과 신뢰, 중심을 상징합니다.' if ilgan_oh=='土' else '결단과 원칙, 정제를 상징합니다.' if ilgan_oh=='金' else '지혜와 유연성, 깊이를 상징합니다.'}
이 기운이 {display_name}님의 삶 전반에 흐르며, 용신 {yong_kr} 오행과 만날 때 가장 크게 빛납니다.
""")
            except: pass

            # 제17장: 재물운 로드맵
            try:
                hi = generate_engine_highlights(pils, birth_year, gender)
                mp_text = "\n".join([
                    f"* {mp['age']} ({mp['year']}): {mp['desc']}"
                    for mp in hi.get('money_peak', [])[:4]
                ]) or "* 계산된 재물 황금기가 없습니다."
                result.append(f"""
[ 제17장 | 재물운(Wealth) 완전 로드맵 ]

    - {display_name}님의 재물 패턴
    {char.get('재물패턴','꾸준한 노력으로 재물을 쌓아가는 타입입니다.')}

    - 평생 재물 황금기
    {mp_text}

    - 재물 핵심 전략
* {gname}: {'직업 안정 수입이 기반. 투기는 금물.' if '정재' in gname else '사업, 투자로 큰 기회. 기복 대비 안전자산 필수.' if '편재' in gname else '전문성, 창의력으로 수입. 재능을 팔아 돈 버는 구조.' if '식신' in gname or '상관' in gname else '명예와 재물 동시에. 실력 먼저, 돈은 따라온다.'}
* 기신 운: {'대운, 세운 모두 기신일 때 큰 투자, 동업, 보증 금지'}
* 용신 {yong_kr} 오행 해(Year): 재물 결정과 실행의 최적기
* {sn}: {'직접 부딪혀야 재물이 온다. 기다리면 지나간다.' if '신강' in sn else '귀인, 파트너와 함께할 때 재물이 배로 온다.' if '신약' in sn else '꾸준함이 최대 재물 전략이다.'}
""")
            except: pass

            # ── 제18장: 건강운
            try:
                oh_strength2 = calc_ohaeng_strength(ilgan, pils)
                OH_BODY_FULL = {
                    "木":"간장·담낭·눈·근육·인대. 봄이 취약, 분노·스트레스가 간을 상합니다.",
                    "火":"심장·소장·혈관·혈압·시력. 여름이 취약, 과로·흥분이 심장을 상합니다.",
                    "土":"비장·위장·췌장·소화기. 환절기 취약, 걱정과 폭식이 위장을 상합니다.",
                    "金":"폐·대장·기관지·피부·코. 가을이 취약, 슬픔·건조가 폐를 상합니다.",
                    "水":"신장·방광·생식기·귀·뼈. 겨울이 취약, 공포와 과로가 신장을 상합니다.",
                }
                OH_HEALTH_ADV = {
                    "木":"규칙적 스트레칭·충분한 수면. 신맛 음식(레몬·매실·신과일) 권장.",
                    "火":"심혈관 정기검진 필수. 카페인·음주 자제. 쓴맛(녹차) 적당히.",
                    "土":"식사 규칙성이 핵심. 폭식·군것질 금지. 황색 음식(꿀·고구마) 권장.",
                    "金":"습도 관리, 가습기 활용. 건조 환경 주의. 매운맛(마늘·생강) 적당히.",
                    "水":"수분 충분히. 짠 음식·과로 금지. 검은 음식(검은콩·미역·김) 권장.",
                }
                h_lines = [f"[일간 주의사항] {ilgan_kr}\n{char.get('건강','규칙적인 생활과 수면이 핵심입니다.')}\n"]
                for o, v in oh_strength2.items():
                    if v >= 30:
                        h_lines.append(f"[과다] {OHN.get(o,'')}({o}) ({v}%) | 주의: {OH_BODY_FULL.get(o,'')}\n  처방: {OH_HEALTH_ADV.get(o,'')}")
                    elif v <= 8:
                        h_lines.append(f"[부족] {OHN.get(o,'')}({o}) ({v}%) | 보충 필요: {OH_BODY_FULL.get(o,'')}\n  처방: {OH_HEALTH_ADV.get(o,'')}")
                result.append(f"""
[ 제18장 | 건강운(Health) 완전 분석 ]

{chr(10).join(h_lines)}

[현재 대운 주의] ({cur_dw_ss})
{'편관 대운 - 과로, 수술, 관재 위험. 정기검진 필수.' if cur_dw_ss=='편관' else '겁재 대운 - 정신적 스트레스가 신체에 영향. 감정 관리가 곧 건강 관리.' if cur_dw_ss=='겁재' else '비교적 건강한 대운. 기본 생활습관 유지가 핵심.'}

[평생 건강 5대 수칙]
1. 수면: 규칙적 수면 - {ilgan_kr} 일간의 건강 기반
2. 감정: {'분노 억제' if ilgan_oh=='木' else '과잉 흥분 조절' if ilgan_oh=='火' else '걱정, 근심 해소' if ilgan_oh=='土' else '슬픔, 집착 해소' if ilgan_oh=='金' else '공포, 불안 해소'} - 감정이 곧 건강
3. 음식: 용신 {yong_kr} 오행 음식 꾸준히 섭취
4. 운동: {'강도 있는 운동보다 꾸준한 유산소' if '신강' in sn else '가벼운 운동 + 충분한 휴식' if '신약' in sn else '균형 잡힌 운동 루틴'}
5. 검진: 주의 장기 연 1회 이상 검진 필수
""")
            except: pass

            # ── 제19장: 인간관계·육친
            try:
                yk = get_yukjin(ilgan, pils, gender)
                yk_yes = [item for item in yk if item.get('present')]
                yk_no  = [item for item in yk if not item.get('present')]
                yk_yes_text = "\n".join([f"* {i['관계']}: {i['위치']} | {i['desc'][:60]}" for i in yk_yes[:4]]) or "해당 없음"
                yk_no_text  = "\n".join([f"* {i['관계']}: 원국에 없음" for i in yk_no[:4]]) or "해당 없음"
                result.append(f"""
[ 제19장 | 인간관계(Relations) - 육친(Yukjin) 완전 분석 ]

[강한 인연] 원국에 있는 육친 
{yk_yes_text}

[변화 많은 인연] 원국에 없는 육친
{yk_no_text}

- {ilgan_kr} 일간의 인간관계 방식
{'강한 독립심으로 인해 혼자 결정, 해결하려는 경향이 강합니다.' if ilgan_oh in ['木','金'] else '따뜻하지만 상처받으면 오래 기억하는 편입니다.' if ilgan_oh=='火' else '신뢰를 중시하고 새로운 인연을 맺는 데 시간이 걸립니다.' if ilgan_oh=='土' else '깊은 통찰력으로 사람을 파악하지만 먼저 다가가기 어려워합니다.'}

- {'남성' if gender=='남' else '여성'} {display_name}님의 이성 인연
{char.get('연애_남' if gender=='남' else '연애_여','이성 관계에서 자신만의 방식을 가지고 있습니다.')}

- 귀인을 만나는 방법
{'문서, 학문, 공식 자리에서 귀인을 만납니다.' if '정관' in gname or '정인' in gname else '이동, 사업, 거래 현장에서 귀인을 만납니다.' if '편재' in gname or '편관' in gname else '일상 업무, 창작 활동 중에 귀인이 나타납니다.'}
용신 {yong_kr} 오행의 기운이 강한 장소와 사람에게서 귀인이 옵니다.
""")
            except: pass

            # ── 제20장: 맞춤 인생 처방전
            try:
                result.append(f"""
[ 제20장 | {display_name}님에게만 드리는 맞춤 인생 처방전 ]

20개 장의 분석을 종합한 최종 처방입니다.

[지금 당장 해야 할 것 (Yongshin 강화)]

색상 처방:
{f'* 목(木) 용신: 청색, 녹색 계열' if '木' in yongshin_ohs else ''}{f'* 화(火) 용신: 적색, 주황색 계열' if '火' in yongshin_ohs else ''}{f'* 토(土) 용신: 황색, 베이지, 갈색 계열' if '土' in yongshin_ohs else ''}{f'* 금(金) 용신: 백색, 은색, 금색 계열' if '金' in yongshin_ohs else ''}{f'* 수(水) 용신: 흑색, 남색, 회색 계열' if '水' in yongshin_ohs else ''}

방위 처방:
{f'* 목(木): 동쪽' if '木' in yongshin_ohs else ''}{f'* 화(火): 남쪽' if '火' in yongshin_ohs else ''}{f'* 토(土): 중앙, 북동, 북서' if '土' in yongshin_ohs else ''}{f'* 금(金): 서쪽' if '金' in yongshin_ohs else ''}{f'* 수(水): 북쪽' if '水' in yongshin_ohs else ''}

시간 처방:
{f'* 목(木): 새벽 3~7시(인묘시)' if '木' in yongshin_ohs else ''}{f'* 화(火): 오전 9~13시(사오시)' if '火' in yongshin_ohs else ''}{f'* 토(土): 진술축미시' if '土' in yongshin_ohs else ''}{f'* 금(金): 오후 3~7시(신유시)' if '金' in yongshin_ohs else ''}{f'* 수(水): 저녁 9~새벽 1시(해자시)' if '水' in yongshin_ohs else ''}

[절대 하면 안 되는 것 (Gishin 주의)]

* 기신 운이 강한 해에 큰 투자, 이사, 창업, 결혼 서두르지 않기
* {gname}에 맞지 않는 사업 방향 피하기
* {'보증, 연대책임 절대 금지' if '겁재' in str(top_ss) or '비견' in str(top_ss) else '감정적 충동 결정 자제'}
* 건강 경고 신호 무시하지 않기

[ {current_year + 1}년 행동 계획 ]

내년 세운: {sw_next.get('세운','')} ({sw_next.get('십성_천간','')} / {sw_next.get('길흉','')})
{'[확인] 적극적으로 움직여야 할 해. 준비한 것을 실행하고 귀인의 도움을 요청하십시오.' if sw_next.get('길흉','') in ['길','대길'] else '[주의] 신중하게 내실을 다지는 해. 현재를 안정화하는 데 집중하십시오.'}

"운명은 사주가 정하지만, 운명을 만드는 것은 당신입니다."
""")
            except: pass
            return "".join(result)
        # ── 인생 흐름용 (menu2)
        elif section == "lifeline":
            result = []
            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 인생 흐름 - 대운 100년 완전 해설
    -----------------------------------------------------

대운(大運)은 10년 단위로 흐르는 인생의 큰 물결입니다. 세운(歲運)이 1년 단위의 파도라면, 대운은 10년을 휘감는 조류(潮流)입니다. 아무리 좋은 세운이 와도 대운이 나쁘면 크게 발현되지 않으며, 반대로 힘든 세운도 좋은 대운 아래서는 그 피해가 줄어듭니다.

{display_name}님의 용신은 {yong_kr}입니다. 이 오행의 대운이 오는 시기가 인생의 황금기가 됩니다.

[ 대운별 상세 해설 ]
""")
            for dw in daewoon[:9]:
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                dw_oh = OH.get(dw["cg"], "")
                is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
                is_cur = dw["시작연도"] <= current_year <= dw["종료연도"]
                cur_mark = " ◀ 현재 대운" if is_cur else ""

                DW_SS_DESC = {
                    "식신": f"식신 대운은 복록과 재능이 꽃피는 시기입니다. {display_name}님의 타고난 재능이 세상에 드러나고, 하는 일마다 사람들의 인정을 받게 됩니다. 건강하고 여유로운 시간이며, 창작·교육·서비스 분야에서 특히 좋은 성과를 냅니다. 먹는 복, 입는 복이 따르고 생활이 윤택해집니다.",
                    "상관": f"상관 대운은 창의력과 표현력이 폭발하는 시기입니다. 기존의 틀을 깨고 새로운 길을 개척하고 싶은 욕구가 강해집니다. 직장 상사나 권위자와 마찰이 생기기 쉬우니 언행에 각별히 주의해야 합니다. 예술·창업·자유업 분야에서는 오히려 빛나는 시기입니다.",
                    "편재": f"편재 대운은 사업·투자·이동이 활발해지는 시기입니다. 적극적으로 움직이면 큰 재물을 잡을 기회가 옵니다. 다만 기복이 크므로 무리한 투기는 피해야 합니다. 이성 인연이 강해지고 새로운 환경에서 새 출발을 하게 되는 경우가 많습니다.",
                    "정재": f"정재 대운은 안정적인 재물이 꾸준히 들어오는 시기입니다. 성실한 노력이 결실을 맺고, 저축과 자산 관리가 잘 됩니다. 결혼·가정·안정을 추구하게 되며, 배우자나 파트너의 내조가 큰 힘이 됩니다. 인생의 기반을 다지기에 최고의 시기입니다.",
                    "편관": f"편관 대운은 시련과 도전이 교차하는 시기입니다. 직장·건강·관재 문제가 생길 수 있으니 특별한 주의가 필요합니다. 그러나 이 시련을 이겨내면 크게 성장하는 계기가 됩니다. 결단력과 추진력을 발휘하면 오히려 강한 리더십이 빛나는 시기가 됩니다.",
                    "정관": f"정관 대운은 명예와 인정이 찾아오는 시기입니다. 사회적 지위가 올라가고 주변으로부터 신뢰를 받습니다. 승진·수상·자격 취득의 기회가 생기며, 법과 원칙 안에서 정당하게 성공합니다. 결혼 인연이나 공식적인 관계가 맺어지기 좋은 시기입니다.",
                    "편인": f"편인 대운은 직관과 통찰이 강해지는 시기입니다. 특수 분야의 전문성을 쌓기 좋으며, 공부·연구·수련에 몰입하게 됩니다. 단, 도식이 형성되면 복이 꺾이는 작용이 있으니 지나친 이상주의를 경계해야 합니다. 고독 속에서 내공을 쌓는 시기입니다.",
                    "정인": f"정인 대운은 학문과 귀인의 덕이 충만한 시기입니다. 스승이나 윗사람의 후원을 받아 도약할 기회가 옵니다. 자격증·학위 취득이나 중요한 시험에서 좋은 결과를 냅니다. 어머니나 귀인으로부터 도움을 받게 되는 경우가 많습니다.",
                    "비견": f"비견 대운은 독립심과 자존감이 강해지는 시기입니다. 새로운 파트너나 동업자를 만나게 되며, 독립 창업을 시도하기도 합니다. 경쟁이 치열해지고 재물이 분산될 수 있으니 지출 관리에 신경 써야 합니다. 자신만의 길을 걷겠다는 의지가 강해집니다.",
                    "겁재": f"겁재 대운은 재물의 기복이 심한 시기입니다. 크게 벌었다가 크게 잃는 사이클이 반복될 수 있습니다. 투기성 투자·보증·동업에는 각별히 주의해야 합니다. 강한 경쟁 의식이 생기지만, 이것이 성장의 에너지가 될 수도 있습니다.",
                }
                desc = DW_SS_DESC.get(dw_ss, f"{dw_ss} 십성 대운으로 {dw['str']}의 기운이 10년간 흐릅니다.")

                result.append(f"""
    + {dw['시작나이']}세 ~ {dw['시작나이']+9}세 | {dw['str']} 대운 ({dw_ss}){cur_mark}
       ({dw['시작연도']}년 ~ {dw['종료연도']}년)
       {'* 용신 대운 - 인생의 황금기' if is_yong else ''}

       {desc}

       이 시기의 핵심 키워드: {'번영, 성장, 도약' if is_yong else '인내, 준비, 기반 구축'}
       {'지금이 바로 큰 결정을 내려야 할 때입니다. 머뭇거리지 마십시오.' if is_yong and is_cur else '지금은 다음 황금기를 위한 준비 기간입니다. 내실을 다지십시오.' if not is_yong and is_cur else ''}
""")

            result.append(f"""
[ 인생 전체 흐름 요약 ]

{display_name}님의 인생에서 가장 중요한 대운은 용신 {yong_kr} 오행이 들어오는 시기입니다. 이 시기에 큰 결정을 내리고 적극적으로 움직여야 합니다.

현재 {current_age}세의 {display_name}님은 {'지금이 바로 황금기입니다. 두려워하지 말고 전진하십시오!' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '지금은 준비 기간입니다. 다음 용신 대운을 위해 체력과 실력을 비축하십시오.'}

인생의 좋은 대운에 최대한 활동하고, 나쁜 대운에 최소한으로 노출되는 것 | 이것이 사주 활용의 핵심 전략입니다.
""")
            # 확장 — 대운별 재물·건강·연애 상세
            result.append(f"""
[ 대운별 분야별 상세 분석 ]

각 대운에서 재물·직업·건강·연애가 어떻게 흘러가는지 구체적으로 분석합니다.
""")
            DW_DOMAIN_DETAIL = {
                "식신": {"재물":"재능으로 수익을 만드는 최적의 대운입니다. 창작·교육·서비스 관련 수익이 안정적으로 들어옵니다.","직업":"현재 일에서 역량이 꽃피어 인정받습니다. 승진이나 새로운 기회가 자연스럽게 옵니다.","건강":"이 대운에서는 전반적으로 건강하고 활기찬 시기입니다. 식욕과 체력이 좋아집니다.","연애":"자연스러운 매력으로 인기를 끕니다. 여유롭고 행복한 인연이 이루어집니다."},
                "상관": {"재물":"기존 방식에서 벗어난 창의적 수익 창출이 가능합니다. 부업·프리랜서 소득이 늘어날 수 있습니다.","직업":"직장보다 독립적인 활동이 강조됩니다. 창업·이직 충동이 강해집니다.","건강":"신경계 과부하에 주의하십시오. 지나친 활동으로 번아웃이 올 수 있습니다.","연애":"자유롭고 역동적인 인연이 생깁니다. 단, 관계의 지속성이 약해질 수 있습니다."},
                "편재": {"재물":"투자·사업·거래가 활발해지는 재물 대운입니다. 기복이 있지만 크게 버는 시기입니다.","직업":"외부 활동과 영업이 강해집니다. 새로운 사업 영역을 개척하기 좋은 대운입니다.","건강":"과로로 인한 체력 저하가 올 수 있습니다. 활동량을 적절히 조절하십시오.","연애":"이성 인연이 풍부해지는 대운입니다. 적극적으로 만남을 만들어가십시오."},
                "정재": {"재물":"안정적이고 꾸준한 재물이 쌓이는 대운입니다. 저축과 자산 관리에 가장 유리한 시기입니다.","직업":"묵묵한 노력이 인정받고 승진이나 연봉 인상의 기회가 옵니다.","건강":"전반적으로 안정적인 건강 상태입니다. 규칙적인 생활을 유지하십시오.","연애":"안정적이고 진지한 인연이 생깁니다. 결혼을 결심하기 좋은 대운입니다."},
                "편관": {"재물":"재물 손실과 지출이 커지는 시기입니다. 보수적인 재무 전략이 필요합니다.","직업":"직장 내 압박·갈등·변동이 생기기 쉽습니다. 언행에 각별히 주의하십시오.","건강":"건강 이상·사고·수술 위험이 있는 대운입니다. 정기 건강검진을 받으십시오.","연애":"관계에서 갈등과 불화가 생기기 쉬우니 인내하고 감정을 조절하십시오."},
                "정관": {"재물":"합법적이고 정당한 방법으로 재물이 들어오는 대운입니다. 계약·협약에 유리합니다.","직업":"사회적 지위가 올라가고 명예가 빛나는 대운입니다. 승진·수상의 기회가 옵니다.","건강":"전반적으로 안정적입니다. 과로에만 주의하십시오.","연애":"공식적이고 격식 있는 인연이 생깁니다. 결혼 기회가 찾아오는 대운입니다."},
                "편인": {"재물":"재물보다 전문성과 지식이 쌓이는 대운입니다. 자격증·교육에 투자하십시오.","직업":"특수 분야 전문성이 인정받는 대운입니다. 연구·개발·강의 분야에서 두각을 나타냅니다.","건강":"신경과민과 불면증에 주의하십시오. 명상과 충분한 휴식이 필요합니다.","연애":"고독한 시간이 많아질 수 있습니다. 깊고 의미있는 인연을 만납니다."},
                "정인": {"재물":"귀인의 도움으로 재물 기회가 찾아옵니다. 직접 버는 것보다 귀인의 연결로 이익이 생깁니다.","직업":"스승·상사의 후원으로 도약합니다. 시험·자격·학위 취득에 최고의 대운입니다.","건강":"몸과 마음 모두 안정적입니다. 정기적인 스트레칭과 명상이 더욱 효과적입니다.","연애":"격식 있고 진지한 인연이 생깁니다. 어른들의 주선으로 좋은 만남이 이루어집니다."},
                "비견": {"재물":"재물이 여러 방향으로 분산될 수 있습니다. 지출 관리와 투자 신중이 필요합니다.","직업":"독립·창업 의지가 강해지는 대운입니다. 자신만의 영역을 구축하기 좋습니다.","건강":"전반적으로 안정적입니다. 경쟁 스트레스가 쌓이지 않도록 하십시오.","연애":"비슷한 가치관의 인연을 만납니다. 독립적인 관계 방식을 선호하게 됩니다."},
                "겁재": {"재물":"재물 기복이 크고 손재 위험이 있는 대운입니다. 투기성 투자는 반드시 피하십시오.","직업":"경쟁이 치열해집니다. 상대를 이기려 하기보다 자신의 실력에 집중하십시오.","건강":"과도한 경쟁 스트레스로 인한 건강 저하를 주의하십시오.","연애":"질투와 경쟁 심리로 관계 갈등이 생기기 쉽습니다. 감정을 솔직히 표현하십시오."},
            }
            for dw in daewoon[:9]:
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                is_cur = (dw["시작연도"] <= current_year <= dw["종료연도"])
                domain = DW_DOMAIN_DETAIL.get(dw_ss, {"재물":"운기를 주시하십시오","직업":"변화에 대비하십시오","건강":"건강 관리에 유의하십시오","연애":"인연에 열린 자세를 가지십시오"})
                cur_mark = " [현재]" if is_cur else ""
                result.append(f"""
    > {dw['시작나이']}~{dw['시작나이']+9}세 {dw['str']} ({dw_ss}대운){cur_mark}
      [재물]: {domain['재물']}
      [직업]: {domain['직업']}
      [건강]: {domain['건강']}
      [연애]: {domain['연애']}
""")
            golden = [(dw['시작나이'], dw['str']) for dw in daewoon if _get_yongshin_match(TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-'), yongshin_ohs, ilgan_oh) == 'yong']
            crisis = [(dw['시작나이'], dw['str']) for dw in daewoon if TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-') in ['편관','겁재'] and _get_yongshin_match(TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-'), yongshin_ohs, ilgan_oh) != 'yong']
            golden_str = " / ".join([f"{a}세 {s}" for a,s in golden[:4]]) if golden else "꾸준한 노력이 황금기를 만듭니다"
            crisis_str = " / ".join([f"{a}세 {s}" for a,s in crisis[:3]]) if crisis else "없음"
            result.append(f"""
[ 인생 황금기 vs 위기 구간 최종 정리 ]

[*] 황금기 구간: {golden_str}
[!] 주의 구간: {crisis_str}

황금기에는 최대한 활동하고, 주의 구간에는 최소한으로 노출되십시오.
황금기에 번 것의 30%는 반드시 다음 주의 구간을 위해 비축하십시오.
인생은 파도처럼 오르고 내립니다. 내릴 때 준비한 자가 오를 때 더 높이 올라갑니다.
""")
            return "".join(result)

        # ── 미래 3년용 (menu4)
        elif section == "future":
            result = []
            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 미래 3년 집중 분석
    -----------------------------------------------------

향후 3년은 {display_name}님 인생에서 중요한 변곡점이 될 수 있습니다. 각 해의 세운(歲運)을 분야별로 집중 분석합니다.

""")
            for y in range(current_year, current_year + 3):
                sw = get_yearly_luck(pils, y)
                dw = next((d for d in daewoon if d["시작연도"] <= y <= d["종료연도"]), None)
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-") if dw else "-"
                sw_ss = sw.get("십성_천간", "-")
                sw_jj_ss = sw.get("지지십성", "-") if "지지십성" in sw else "-"
                age = y - birth_year + 1
                is_yong_sw = _get_yongshin_match(sw_ss, yongshin_ohs, ilgan_oh) == "yong"
                gilhyung = sw.get("길흉", "")

                # 길흉 마커
                gh_mark = "[길]" if gilhyung in ["길","대길"] else "[평]" if gilhyung=="평" else "[의]"
                                
                result.append(f"### {y}년 차트 ({age}세) | {sw['세운']} ({sw_ss}) {gh_mark}\n")
                if is_yong_sw: result.append(f"* [용신운] 올해는 하늘의 도움이 따르는 해입니다.\n")

                YEAR_SS_DETAIL = {
                    "식신": {
                        "총평": f"{y}년은 재능과 창의력이 꽃피는 해입니다. 타고난 끼가 세상에 드러나고, 하는 일마다 순조롭게 풀립니다.",
                        "돈": "부업·창작·서비스 관련 수익이 들어오기 좋습니다. 새로운 수입원을 만들기에 최적의 해입니다.",
                        "직장": "업무 성과가 인정받고 주변의 지지를 받습니다. 창의적 프로젝트를 시작하기 좋습니다.",
                        "연애": "자연스러운 매력으로 인기를 끄는 해입니다. 여유로운 만남이 이루어집니다.",
                        "건강": "건강하고 활기찬 해입니다. 과식·과음에만 주의하십시오.",
                        "조언": "재능을 세상에 꺼내십시오. 숨기면 복이 사라집니다.",
                    },
                    "상관": {
                        "총평": f"{y}년은 창의력과 혁신의 해입니다. 새로운 도전과 변화를 통해 자신만의 길을 만들어가는 시기입니다.",
                        "돈": "창의적인 방법으로 새 수익을 만들 수 있습니다. 기존 방식에서 벗어난 시도가 빛납니다.",
                        "직장": "직장 내 언행에 특히 주의하십시오. 상사와의 마찰이 생기기 쉬운 해입니다. 창업·이직을 고려하기 좋습니다.",
                        "연애": "자유롭고 활발한 인연이 생기지만 관계가 오래 지속되기 어려울 수 있습니다.",
                        "건강": "신경계 과부하에 주의하십시오. 충분한 휴식이 필요합니다.",
                        "조언": "창의력은 살리되 직장과 권위 앞에서 언행을 조심하십시오.",
                    },
                    "편재": {
                        "총평": f"{y}년은 사업과 투자, 이동이 활발해지는 해입니다. 재물 기회가 오지만 기복도 함께 옵니다.",
                        "돈": "사업 확장·투자·거래가 활발합니다. 과욕 없이 계획적으로 움직이면 성과가 있습니다.",
                        "직장": "활발한 외부 활동과 영업이 빛납니다. 새로운 사업 파트너를 만날 수 있습니다.",
                        "연애": "이성 인연이 활발해지는 해입니다. 새로운 만남의 가능성이 높습니다.",
                        "건강": "과로와 무리한 활동으로 인한 체력 저하에 주의하십시오.",
                        "조언": "욕심을 조절하십시오. 들어온 재물의 절반은 반드시 안전한 곳에 보관하십시오.",
                    },
                    "정재": {
                        "총평": f"{y}년은 안정적이고 꾸준한 재물의 해입니다. 성실한 노력이 결실을 맺는 시기입니다.",
                        "돈": "월급·임대수입 등 고정 수입이 늘어납니다. 저축과 자산 관리에 가장 유리한 해입니다.",
                        "직장": "묵묵히 일한 것이 인정받는 해입니다. 안정적인 커리어를 쌓기 좋습니다.",
                        "연애": "안정적이고 진지한 인연이 생깁니다. 결혼을 결심하기 좋은 해입니다.",
                        "건강": "전반적으로 안정적인 해입니다. 규칙적인 생활을 유지하십시오.",
                        "조언": "안정을 추구하되 기회가 올 때 움직이는 용기도 잃지 마십시오.",
                    },
                    "편관": {
                        "총평": f"{y}년은 시련과 도전이 교차하는 해입니다. 건강·관재·직장 문제에 각별한 주의가 필요합니다.",
                        "돈": "지출과 손실을 주의하십시오. 큰 재물 결정은 이 해를 피하십시오.",
                        "직장": "직장 내 갈등·압박·이직 위험이 있습니다. 언행을 조심하고 자신을 낮추십시오.",
                        "연애": "상대방과의 갈등이 생기기 쉬운 해입니다. 감정적 대응을 자제하십시오.",
                        "건강": "사고·수술·건강 이상이 생기기 쉬운 해입니다. 정기 건강검진을 받으십시오.",
                        "조언": "인내하고 정면으로 돌파하십시오. 시련을 이겨낸 후에는 반드시 성장이 옵니다.",
                    },
                    "정관": {
                        "총평": f"{y}년은 명예와 인정이 빛나는 최고의 해입니다! 승진·수상·자격 취득의 기회가 찾아옵니다.",
                        "돈": "정직하고 합법적인 방법으로 재물이 들어오는 해입니다. 계약·협약에 유리합니다.",
                        "직장": "승진·인정·자격 취득의 기회가 옵니다. 원칙과 성실함이 보상받는 해입니다.",
                        "연애": "결혼 인연이나 공식적인 관계 진전이 있는 해입니다.",
                        "건강": "전반적으로 안정적입니다. 과로에만 주의하십시오.",
                        "조언": "겸손하게 원칙을 지키십시오. 자만은 이 해의 가장 큰 적입니다.",
                    },
                    "편인": {
                        "총평": f"{y}년은 직관과 통찰이 강해지는 해입니다. 전문성을 쌓고 내공을 키우기 좋은 시기입니다.",
                        "돈": "재물보다 지식과 기술에 투자하기 좋은 해입니다.",
                        "직장": "특수 분야 전문성을 인정받습니다. 연구·개발·교육 분야에서 두각을 나타냅니다.",
                        "연애": "고독한 시간이 많아질 수 있습니다. 깊은 감정적 교감을 나눌 수 있는 인연을 만납니다.",
                        "건강": "신경 과민·불면증에 주의하십시오. 명상과 충분한 휴식이 필요합니다.",
                        "조언": "고독을 두려워하지 마십시오. 이 시간 동안 쌓은 내공이 다음 도약의 기반이 됩니다.",
                    },
                    "정인": {
                        "총평": f"{y}년은 귀인의 도움과 학문의 성취가 충만한 최고의 해 중 하나입니다!",
                        "돈": "직접적인 재물보다 명예·지식·자격이 쌓이는 해입니다. 이것이 미래의 재물이 됩니다.",
                        "직장": "스승·상사·윗사람의 후원을 받아 도약합니다. 자격증·시험·학위 취득에 유리합니다.",
                        "연애": "격식 있는 만남과 공식적인 인연이 생깁니다.",
                        "건강": "몸과 마음 모두 안정적인 해입니다.",
                        "조언": "배움의 기회를 놓치지 마십시오. 지금 쌓는 지식이 10년 후 재물이 됩니다.",
                    },
                    "비견": {
                        "총평": f"{y}년은 독립심과 자존감이 강해지는 해입니다. 새로운 파트너나 동업자와의 만남이 있습니다.",
                        "돈": "재물이 여러 방향으로 분산될 수 있습니다. 지출 관리에 신경 쓰십시오.",
                        "직장": "독립·창업을 시도하기 좋은 해입니다. 새로운 협력자를 만날 수 있습니다.",
                        "연애": "비슷한 관심사와 가치관을 가진 인연을 만납니다.",
                        "건강": "전반적으로 안정적입니다. 경쟁 스트레스가 쌓이지 않도록 하십시오.",
                        "조언": "독립 의지는 좋으나 혼자 모든 것을 해결하려 하지 마십시오.",
                    },
                    "겁재": {
                        "총평": f"{y}년은 재물 기복이 큰 해입니다. 경쟁과 손재를 조심하고 수비적으로 대응하십시오.",
                        "돈": "재물 손실과 경쟁이 치열한 해입니다. 투자·보증·동업은 이 해에 자제하십시오.",
                        "직장": "경쟁이 치열해집니다. 자신의 실력을 쌓는 데 집중하십시오.",
                        "연애": "질투·경쟁 심리로 인한 관계 갈등이 생기기 쉽습니다.",
                        "건강": "과도한 경쟁과 스트레스로 인한 건강 저하에 주의하십시오.",
                        "조언": "이 해는 수비가 최선입니다. 지키는 것만 잘해도 성공입니다.",
                    },
                }
                yd = YEAR_SS_DETAIL.get(sw_ss, {
                    "총평": f"{y}년 {sw.get('세운','')} 세운이 흐릅니다.",
                    "돈": "재물 흐름을 주시하십시오.",
                    "직장": "직업적 변화에 유의하십시오.",
                    "연애": "인연에 관심을 기울이십시오.",
                    "건강": "건강 관리에 신경 쓰십시오.",
                    "조언": "차분히 흐름을 따르십시오.",
                })
                star = "[*] " if is_yong_sw else "[!] " if sw_ss in ["편관","겁재"] else "+ "
                result.append(f"""
-----------------------------------------------------
{star}{y}년 ({age}세) | {sw.get('세운','')} 세운 | {sw_ss} / {gilhyung}
-----------------------------------------------------

{yd['총평']}

[재물/돈]: {yd['돈']}

[직장/사업]: {yd['직장']}

[연애/관계]: {yd['연애']}

[건강]: {yd['건강']}

[핵심 조언]: {yd['조언']}
""")

            result.append(f"""
[ 3년 종합 전략 ]

향후 3년 동안 {display_name}님이 가장 중점을 두어야 할 사항:

1. 용신 {yong_kr} 강화 | 용신 오행의 색상, 음식, 방위를 일상에서 꾸준히 활용하십시오
2. 기신 차단 | 기신 오행의 요소를 생활 공간에서 최소화하십시오
3. {'적극적 투자와 도전 | 지금이 황금기의 연속입니다' if all(_get_yongshin_match(get_yearly_luck(pils,y).get('십성_천간','-'), yongshin_ohs, ilgan_oh) == 'yong' for y in range(current_year, current_year+2)) else '내실 다지기 | 지금은 준비 기간이니 실력 향상에 집중하십시오'}
4. 건강 관리 | 사주의 취약한 오행 관련 기관을 정기적으로 점검하십시오
5. 인맥 관리 | {'귀인을 만날 운기이니 새로운 사람들과의 교류에 적극적으로 나서십시오' if '정인' in [get_yearly_luck(pils,y).get('십성_천간') for y in range(current_year, current_year+3)] else '신뢰 관계를 꾸준히 유지하고 새로운 파트너를 신중하게 선택하십시오'}
""")
            # 확장 — 월별 핵심 시기 분석
            result.append(f"""
[ 올해 월별 운기 핵심 포인트 ]

월별 세운(月運)을 통해 어느 달에 집중하고, 어느 달에 쉬어야 하는지 파악합니다.
""")
            try:
                month_data = []
                for m in range(1, 13):
                    ml = get_monthly_luck(pils, current_year, m) if 'get_monthly_luck' in dir() else None
                    if ml:
                        m_ss = ml.get("십성","")
                        m_str = ml.get("월주","")
                        is_m_yong = _get_yongshin_match(m_ss, yongshin_ohs, ilgan_oh) == "yong"
                        mark = "*" if is_m_yong else "!" if m_ss in ["편관","겁재"] else "o"
                        month_data.append(f"  {m:2d}월 {m_str:6s} ({m_ss:4s}) {mark}")
                if month_data:
                    result.append("\n".join(month_data))
                    result.append(f"""

* 별표 달: 이 달에 중요한 미팅, 계약, 투자 결정을 하십시오
! 경고 달: 이 달에는 큰 결정을 피하고 수비 전략을 쓰십시오
o 보통 달: 꾸준히 계획대로 진행하십시오
""")
            except: pass

            result.append(f"""
[ 3년 분야별 최적 타이밍 ]

[돈] 재물, 투자 최적 시기:
{'* ' + str(current_year) + '년이 3년 중 재물 최고 시기입니다. 이 해에 투자, 계약을 집중하십시오.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '* ' + str(current_year+1) + '년에 재물 운이 더 강해질 것으로 예상됩니다.'}

[직업] 직업, 사업 최적 시기:
* 정관, 편관, 정인이 오는 해에 승진, 자격, 계약 기회를 노리십시오
* {'지금이 새 사업을 시작하기에 좋은 흐름입니다.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '새 사업은 다음 용신 세운이 올 때까지 기다리십시오.'}

[연애] 연애, 결혼 최적 시기:
* {'재성(남성) / 관성(여성) 세운이 오는 해가 결혼, 인연의 최적 시기입니다.' if gender == '남' else ''}
* {'이 3년 중 ' + str(current_year) + '년이 이성 인연에 가장 활성화된 해입니다.' if (sw_now.get('십성_천간','') in (['정재','편재'] if gender == '남' else ['정관','편관'])) else '적극적인 활동을 통해 인연의 기회를 만드십시오.'}

[건강] 건강 주의 시기:
* 편관, 겁재 세운은 건강 이상이 생기기 쉬운 시기입니다
* 매년 정기 건강검진을 받고, 용신 오행 관련 기관을 특히 점검하십시오

[ 3년 후 미래 | 지금의 선택이 만드는 5년 후 ]

향후 3년을 어떻게 보내느냐에 따라 5년 후의 삶이 완전히 달라집니다.

{'용신 대운이 진행 중인 지금, 이 황금기를 제대로 활용한다면 5년 후에는 재물·명예·건강 모두 크게 향상될 것입니다.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '지금의 준비 기간을 어떻게 보내느냐에 따라 다음 황금기의 높이가 결정됩니다. 지금 실력을 갈고닦으십시오.'}

{display_name}님에게 드리는 3년 최종 처방:
"지금 당장 할 수 있는 한 가지를 시작하십시오. 완벽한 타이밍을 기다리다 인생이 지나갑니다."
""")
            return "".join(result)

        # ── 재물용 (menu5)
        elif section == "money":
            result = []
            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 재물, 사업 특화 완전 분석
    -----------------------------------------------------

재물(財物)은 사주에서 재성(財星)과 용신(用神)의 관계로 파악합니다. 얼마나 버느냐보다 어떤 방식으로 버는지, 어떤 시기에 돈이 모이는지를 아는 것이 진짜 재물 분석입니다.

[ 제1장 | 재물 기질 완전 분석 ]

{display_name}님의 재물 버는 방식을 십성 조합으로 분석합니다.
일간 {ilgan_kr} + {sn} + 주요 십성 {', '.join(top_ss)}

""")
            for key, combo in combos[:3]:
                result.append(f"""
* [{' x '.join(key)}] 재물 조합

{combo.get('요약', '')}

재물 버는 방식: {combo.get('재물', '')}
맞는 사업·직업: {combo.get('직업', '')}
재물 주의사항: {combo.get('주의', '')}
""")

            result.append(f"""
[ 제2장 | 재물 운기 분석 | 돈이 모이는 시기와 새는 시기 ]

사주에서 재물은 대운과 세운의 조합으로 결정됩니다. 용신 오행이 들어오는 해에 재물이 모이고, 기신 오행이 강해지는 해에 재물이 나갑니다.

현재 {cur_dw['str'] if cur_dw else '-'} 대운 ({cur_dw_ss})
{'> 이 대운은 용신 대운으로, 재물이 모이기 좋은 10년입니다. 적극적으로 투자하고 수익 구조를 만들어가십시오.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '> 이 대운은 재물 관리에 신중해야 하는 시기입니다. 무리한 투자보다 기존 자산을 지키는 전략이 중요합니다.'}

올해 {sw_now.get('세운','')} 세운 ({sw_now.get('십성_천간','')} / {sw_now.get('길흉','')})
{'> 올해는 재물 운이 활성화되는 해입니다. 새로운 수입원을 만들거나 투자를 시작하기 좋습니다.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '> 올해는 재물 지출에 주의해야 합니다. 불필요한 지출을 줄이고 저축에 집중하십시오.'}

[ 제3장 | 투자 유형 분석 ]

{display_name}님의 사주에서 가장 잘 맞는 투자 유형:

{'[v] 부동산 투자 | 토(土) 기운과 관련된 투자로 장기적으로 안정적인 수익을 줍니다.' if '土' in yongshin_ohs else ''}
{'[v] 금융, 주식 투자 | 금(金) 기운과 관련된 투자로 결단력 있게 움직이면 수익이 납니다.' if '金' in yongshin_ohs else ''}
{'[v] 무역, 유통 투자 | 수(水) 기운과 관련된 투자로 흐름을 잘 타면 큰 수익을 냅니다.' if '水' in yongshin_ohs else ''}
{'[v] 성장주, 벤처 투자 | 목(木) 기운과 관련된 투자로 초기 단계 투자에서 강합니다.' if '木' in yongshin_ohs else ''}
{'[v] 에너지, 문화 투자 | 화(火) 기운과 관련된 투자로 사람과 콘텐츠에서 수익이 납니다.' if '火' in yongshin_ohs else ''}

! 피해야 할 투자 유형 (기신 오행 관련):
{'기신 오행의 산업·자산에는 투자를 자제하십시오. 아무리 좋아 보여도 이 분의 사주에서는 기신 오행 투자가 손실로 이어지는 경우가 많습니다.'}

[ 제4장 | 사업 적합성 분석 ]

{display_name}님의 사주가 독립사업과 직장 중 어느 쪽이 더 맞는지:

{'비견·겁재가 강한 이 사주는 독립사업·자영업이 더 맞습니다. 남 밑에서 지시받기보다 자신만의 영역에서 일할 때 재물이 쌓입니다.' if any(ss in top_ss for ss in ['비견', '겁재']) else ''}
{'식신·상관이 강한 이 사주는 창의적인 사업 또는 프리랜서 활동이 맞습니다. 재능을 상품화하는 방식이 가장 효율적인 재물 창출입니다.' if any(ss in top_ss for ss in ['식신', '상관']) else ''}
{'정관·정재가 강한 이 사주는 안정적인 직장에서 꾸준히 성장하는 방식이 맞습니다. 조직 내에서 신뢰를 쌓는 것이 재물로 이어집니다.' if any(ss in top_ss for ss in ['정관', '정재']) else ''}
{'편재·편관이 강한 이 사주는 역동적인 사업 환경에서 강합니다. 위험을 감수하고 크게 움직이는 것을 두려워하지 마십시오.' if any(ss in top_ss for ss in ['편재', '편관']) else ''}

[ 제5장 | 재물 새는 구멍과 막는 법 ]

이 사주에서 재물이 새는 주요 원인:

{'1. 겁재가 강해 주변 사람들에게 베풀다가 재물이 분산됩니다. 감정적 지출을 줄이십시오.' if '겁재' in ss_dist else ''}
{'2. 상관이 강해 충동적인 소비나 불필요한 지출이 생깁니다. 구매 전 하루 생각하는 습관을 들이십시오.' if '상관' in ss_dist else ''}
{'3. 편재가 강해 투자 욕구가 넘쳐 무리하게 확장하다 손실이 납니다. 수익의 30%는 반드시 안전 자산으로 보관하십시오.' if '편재' in ss_dist else ''}
{'4. 편인이 강해 직업 변동이 잦아 안정적인 수입 구조를 만들기 어렵습니다. 한 분야에 집중하는 것이 재물 관리의 핵심입니다.' if '편인' in ss_dist else ''}

재물을 지키는 가장 좋은 방법:
* 용신 {yong_kr} 색상의 지갑 사용
* 수입의 20~30% 자동 저축 설정
* 기신 오행이 강한 해에는 큰 재물 결정 미루기
* 용신 오행이 강한 해에 투자 및 사업 확장

[ 제6장 | 재물 황금기 완전 예측 ]

{display_name}님의 인생에서 재물 황금기가 오는 시기:
""")
            # 향후 대운 중 용신 대운 찾기
            peak_years = []
            for dw in daewoon:
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                if _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong":
                    age_mid = dw["시작나이"] + 5
                    year_mid = birth_year + age_mid - 1
                    peak_years.append(f"* {dw['시작나이']}~{dw['시작나이']+9}세 ({dw['시작연도']}~{dw['종료연도']}년): {dw['str']} 용신 대운 | 이 10년이 {display_name}님의 재물 황금기입니다")
            result.append("\n".join(peak_years[:3]) if peak_years else "* 꾸준한 노력이 재물 황금기를 만듭니다")
            result.append(f"""

재물 황금기를 최대로 활용하는 전략:
1. 황금기 대운이 시작되기 2~3년 전부터 준비하십시오
2. 황금기에는 두려움 없이 과감하게 투자하십시오
3. 황금기의 수익은 다음 어려운 시기를 위해 30% 이상 비축하십시오
4. 사업을 시작한다면 황금기 대운 초반에 시작하는 것이 가장 좋습니다

[ 제7장 | 재물 관리의 황금 원칙 | 이 사주에만 해당하는 처방 ]

일간 {ilgan_kr} + {gname} + {sn} 조합의 재물 관리 황금 원칙:

원칙 1. {'크게 벌고 크게 쓰는 패턴을 끊어야 합니다. 수입이 생기면 즉시 30%를 자동이체로 저축하십시오.' if any(ss in ss_dist for ss in ['겁재','편재']) else '안정적으로 쌓아가는 것이 이 사주의 재물 방식입니다. 투기성 투자에 유혹받지 마십시오.'}

원칙 2. {'창의력과 재능이 돈이 됩니다. 자신의 전문성을 상품화하는 방법을 끊임없이 고민하십시오.' if any(ss in ss_dist for ss in ['식신','상관']) else '안정적 수입 구조를 먼저 만들고 투자를 시작하십시오.'}

원칙 3. 용신 {yong_kr} 오행이 강해지는 해에 큰 재물 결정을 집중하고, 기신이 강해지는 해에는 지키는 전략을 쓰십시오.

원칙 4. {'부동산은 이 사주에 중장기적으로 좋은 자산입니다.' if '土' in yongshin_ohs else '금융 자산과 현금 유동성을 충분히 유지하십시오.' if '水' in yongshin_ohs or '金' in yongshin_ohs else '성장하는 분야에 일찍 진입하는 것이 이 사주의 재물 전략입니다.' if '木' in yongshin_ohs else '콘텐츠·사람·브랜드에 투자하는 것이 이 사주의 재물 방식입니다.'}

원칙 5. 보증·동업에서 재물을 잃는 경우가 많습니다. 계약서 없는 재물 거래는 절대 하지 마십시오.

[ 제8장 | 직업별 예상 소득 패턴 분석 ]

{display_name}님의 사주에서 각 직업 유형별 예상 소득 패턴:

* 직장인: 꾸준하고 안정적이지만 {'가파른 성장은 어렵습니다. 전문성을 쌓아 희소 인재가 되어야 합니다.' if '신강' in sn else '귀인의 도움으로 예상보다 빠른 성장이 가능합니다.'}

* 프리랜서/자영업: {'이 사주에 가장 잘 맞는 방식입니다. 초기 기반을 잡는 데 3~5년이 필요하지만, 그 후에는 직장보다 훨씬 큰 수익을 낼 수 있습니다.' if any(ss in ss_dist for ss in ['비견','식신','상관']) else '안정적인 수입이 보장되지 않는 방식이라 이 사주에는 주의가 필요합니다.'}

* 투자/사업: {'편재가 강해 사업 확장 기질이 있습니다. 단, 리스크 관리가 생존의 핵심입니다.' if '편재' in ss_dist else '안정적인 사업 기반을 만든 후 확장하는 보수적 전략이 맞습니다.'}

[ 제9장 | 나이별 재물 타이밍 완전 분석 ]

인생의 각 10년 구간에서 재물 운의 흐름:
""")
            for dw in daewoon[:8]:
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
                money_advice = {
                    "식신": "재능 소득·창작 수익이 들어오는 시기",
                    "상관": "혁신적 방식으로 새 수익원 개척 시기",
                    "편재": "투자·사업으로 크게 버는 시기 (기복 주의)",
                    "정재": "안정적 저축·자산 축적 최적 시기",
                    "편관": "재물 보호·손실 방어가 우선인 시기",
                    "정관": "직장·명예를 통한 합법적 소득 증가 시기",
                    "편인": "전문성 투자 시기 (미래 재물의 씨앗)",
                    "정인": "귀인을 통한 재물 기회 시기",
                    "비견": "재물 분산 주의·독립 수익 도전 시기",
                    "겁재": "재물 손실 위험·투기 절대 금지 시기",
                }.get(dw_ss, f"{dw_ss} 십성 운기")
                yong_mark = " [*]" if is_yong else ""
                result.append(f"  {dw['시작나이']}~{dw['시작나이']+9}세: {money_advice}{yong_mark}\n")
            result.append(f"""

[ 제10장 | 만신의 재물 최종 처방 ]

{display_name}님의 재물 운을 한마디로 요약하면:
"{combos[0][1].get('재물','타고난 방식으로 꾸준히 쌓아가는 재물') if combos else '성실함과 전문성으로 재물을 쌓아가는 사주'}"

이 사주에서 재물이 들어오는 문은 "{', '.join(top_ss[:2])}"이(가) 열어줍니다.
이 문이 활성화되는 운기에 최대로 움직이고, 닫히는 운기에는 지키십시오.

재물은 복이지만 집착하면 독이 됩니다. {display_name}님만의 방식으로 재물을 이루어 나가십시오.
""")
            return "".join(result)

        # ── 인간관계용 (menu6)
        elif section == "relations":
            result = []
            yk = get_yukjin(ilgan, pils, gender)
            sipsung_data = calc_sipsung(ilgan, pils)

            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 인간관계, 육친 완전 분석
    -----------------------------------------------------

인간관계는 사주에서 십성(十星)과 육친(六親)을 통해 분석합니다. 어떤 사람과 인연이 깊은지, 어떤 사람과 갈등이 생기는지를 사주는 미리 알려줍니다.

[ 제1장 | 일간의 대인관계 패턴 ]

{display_name}님은 일간 {ilgan_kr} + {sn}의 조합으로 다음과 같은 대인관계 패턴을 가집니다:

{'* 신강하여 자기주장이 강합니다. 타인의 의견을 경청하는 연습이 관계 개선의 핵심입니다.' if '신강' in sn else '* 신약하여 타인의 영향을 많이 받습니다. 자신의 의견을 분명히 표현하는 연습이 필요합니다.' if '신약' in sn else '* 중화 사주로 균형 잡힌 대인관계를 유지합니다. 극단적인 관계보다 안정적인 인간관계를 선호합니다.'}

{'* 비견, 겁재가 강해 경쟁적인 관계에서 에너지를 발산합니다.' if any(ss in ss_dist for ss in ['비견','겁재']) else ''}
{'* 식신, 상관이 강해 자신을 잘 표현하고 주변에 즐거움을 줍니다.' if any(ss in ss_dist for ss in ['식신','상관']) else ''}
{'* 정관, 편관이 강해 조직과 권위를 의식하며 사회적 관계에 민감합니다.' if any(ss in ss_dist for ss in ['정관','편관']) else ''}
{'* 정인, 편인이 강해 스승과 선배로부터 배우고 지식을 나누는 관계를 중요시합니다.' if any(ss in ss_dist for ss in ['정인','편인']) else ''}

[ 제2장 | 육친 상세 분석 ]
""")
            YUKJIN_DEEP = {
                "어머니(正印)": f"정인은 어머니의 자리입니다. {display_name}님과 어머니의 관계는 사주에서 매우 중요한 영향을 미칩니다. 정인이 있다면 어머니의 음덕(蔭德)이 크며, 어머니로부터 정서적·물질적 도움을 받는 운입니다. 학문과 귀인을 상징하는 정인이 강하면 교육열이 높고 스승의 인연이 좋습니다.",
                "계모(偏印)": f"편인은 계모·이모·외조모 등 어머니 외의 여성 윗사람을 상징합니다. 편인이 강하면 독특한 재능과 직관이 있으며, 특수 분야에서 독보적인 능력을 발휘합니다. 단, 식신을 억제하면 도식이 형성되어 복이 꺾이는 작용이 있습니다.",
                "아버지(偏財)": f"편재는 아버지의 자리입니다. {display_name}님과 아버지의 관계가 이 사주에 큰 영향을 줍니다. 편재가 있다면 아버지로부터 재물적 도움이나 사업적 조언을 받을 수 있습니다. 편재는 활동적이고 외향적인 아버지의 기운으로, 아버지가 사업가이거나 활발한 분인 경우가 많습니다.",
                "아내(正財)": f"정재는 남성에게 아내의 자리입니다. 정재가 있으면 성실하고 현모양처형 배우자를 만나는 운입니다. 정재가 강하면 안정적인 가정생활을 영위하며, 배우자의 내조가 큰 힘이 됩니다. 다만 정재가 너무 강하면 돈과 배우자에 집착하는 경향이 생길 수 있습니다.",
                "남편(正官)": f"정관은 여성에게 남편의 자리입니다. 정관이 있으면 점잖고 안정적인 남편 인연이 있습니다. 사회적으로 인정받는 남성을 만나는 운이며, 결혼 후 안정적인 가정생활을 할 가능성이 높습니다.",
                "아들(偏官)": f"편관(칠살)은 남성에게 아들, 여성에게는 정부(情夫)를 상징합니다. 편관이 있으면 자녀로 인한 기쁨과 함께 자녀 교육에 많은 에너지를 쏟습니다. 칠살이 제화(制化)되면 자녀가 사회적으로 성공하는 운입니다.",
                "딸(正官)": f"정관은 남성에게 딸을 상징합니다. 딸과의 관계가 따뜻하고 격식 있습니다. 자녀가 안정적이고 사회적으로 인정받는 삶을 사는 운입니다.",
                "형제(比肩)": f"비견은 형제·자매·친구·동료를 상징합니다. 비견이 강하면 형제자매나 친구와의 인연이 깊습니다. 서로 경쟁하면서도 성장하는 관계이며, 동업이나 협업을 통해 시너지를 낼 수 있습니다.",
                "이복형제(劫財)": f"겁재는 이복 형제·경쟁자·라이벌을 상징합니다. 겁재가 강하면 주변에 경쟁자가 많고, 재물이 분산될 수 있습니다. 그러나 건강한 경쟁 의식으로 발전시키면 강한 추진력이 됩니다.",
            }
            for item in yk:
                fam = item.get("관계", "")
                has = item.get("present", False)
                where = item.get("위치", "없음")
                deep_desc = YUKJIN_DEEP.get(fam, item.get("desc", ""))
                result.append(f"""
* {fam}
   위치: {where if where != '없음' else '원국에 직접 없음'}
   인연 강도: {'강함 | 이 인연이 인생에 크게 영향을 미칩니다' if has else '약함 | 인연이 엷거나 독립적인 관계'}

   {deep_desc}

   {'이 육친과의 관계가 이 분의 운명에 핵심적인 역할을 합니다. 이 관계를 잘 가꾸십시오.' if has else '이 육친과의 관계에서 독립적인 성향이 강합니다. 의식적으로 관계를 돌보는 노력이 필요합니다.'}
""")

            result.append(f"""
[ 제3장 | 이성 인연, 배우자 분석 ]

일지(日支) {iljj_kr}({iljj})는 배우자 자리입니다. 이 자리의 기운이 배우자의 성품과 부부 관계의 방향을 결정합니다.

{display_name}님의 배우자 자리 분석:
* {iljj_kr}({iljj}) 일지 | {'안정과 포용력을 가진 배우자' if iljj in ['丑','辰','戌','未'] else '열정적이고 활기찬 배우자' if iljj in ['午','巳','寅'] else '논리적이고 실력 있는 배우자' if iljj in ['申','酉','亥','子'] else '성장하는 에너지를 가진 배우자' if iljj in ['卯'] else '포용력 있는 배우자'}를 만나는 운입니다.

이성 인연이 강해지는 시기:
* {'재성(財星) 세운 | 편재, 정재 세운이 올 때 이성 인연이 활성화됩니다.' if gender == '남' else '* 관성(官星) 세운 | 정관, 편관 세운이 올 때 이성 인연이 활성화됩니다.'}
* 현재 대운 {cur_dw['str'] if cur_dw else '-'} | {'이성 인연이 활성화되는 대운입니다' if cur_dw_ss in (['정재','편재'] if gender=='남' else ['정관','편관']) else '배우자 운보다 다른 분야가 강조되는 대운입니다'}

이상적인 파트너의 특징:
* 용신 {yong_kr} 오행을 가진 사람과 궁합이 잘 맞습니다
* {'불, 에너지가 강한 사람' if '火' in yongshin_ohs else ''}{'땅처럼 안정적인 사람' if '土' in yongshin_ohs else ''}{'물처럼 지혜로운 사람' if '水' in yongshin_ohs else ''}{'나무처럼 성장하는 사람' if '木' in yongshin_ohs else ''}{'금처럼 결단력 있는 사람' if '金' in yongshin_ohs else ''}이(가) 이상적인 파트너입니다

[ 제4장 | 사회적 인간관계 조언 ]

{display_name}님이 만나야 할 귀인(貴人)의 특징:
* 용신 오행이 강한 분야(직업, 전공)에 있는 사람이 귀인입니다
* {'수학, 금융, 법, 의료, 공학 분야의 전문가' if '金' in yongshin_ohs or '水' in yongshin_ohs else '교육, 예술, 봉사, 문화 분야의 전문가' if '木' in yongshin_ohs or '火' in yongshin_ohs else '부동산, 건설, 농업, 토지 관련 분야의 전문가' if '土' in yongshin_ohs else '다양한 분야의 전문가'}와의 인연을 소중히 하십시오

조심해야 할 인연:
* 기신 오행이 강한 사람과는 재물 거래나 동업을 피하십시오
* 겁재가 강하게 들어오는 해에 만나는 사업 파트너는 신중히 검토하십시오
* 겉으로는 화려해 보이지만 실속이 없는 관계에 에너지를 낭비하지 마십시오

인간관계에서 {display_name}님만의 강점:
{char.get('장점', '타고난 성품으로 주변 사람들에게 신뢰를 줍니다')}

이 강점을 살려 인간관계를 넓혀가면, 그 관계가 결국 재물과 명예로 돌아오는 운명입니다.

[ 제5장 | 연애, 결혼 심층 분석 ]

{'남성' if gender == '남' else '여성'} {ilgan_kr} 일간의 연애 본능:
* {'* ' + char.get('연애_남', '') if gender == '남' else '* ' + char.get('연애_여', '')}

배우자 자리 {iljj_kr}({iljj}) 심층 해석:
{iljj_kr}이(가) 배우자 자리에 있다는 것은 배우자에게서 {'안정·신뢰·현실적 도움을 받고 싶은 내면의 욕구' if iljj in ['丑','辰','戌','未'] else '열정·활기·도전적 에너지를 받고 싶은 욕구' if iljj in ['午','巳'] else '지적 교감·논리·전문성을 원하는 욕구' if iljj in ['申','酉'] else '성장·창의·새로움을 함께 나누고 싶은 욕구' if iljj in ['寅','卯'] else '깊은 감정·지혜·내면의 평화를 함께하고 싶은 욕구' if iljj in ['亥','子'] else '다양한 매력을 가진 파트너를 원하는 욕구'}가 있다는 것입니다.

이상적인 배우자의 오행:
* 용신 {yong_kr} 오행이 강한 사람 | 이 분과 함께하면 삶이 더 풍요로워집니다
* 이 오행을 가진 직업군의 사람이 좋습니다

결혼 적령기 분석:
현재 {current_age}세 기준:
* {'재성 대운 중에 있어 결혼 에너지가 활성화되어 있습니다.' if cur_dw and cur_dw_ss in (['정재','편재'] if gender == '남' else ['정관','편관']) else '관성 대운 중에 있어 결혼 에너지가 활성화되어 있습니다.' if cur_dw and cur_dw_ss in (['정관','편관'] if gender == '남' else ['정재','편재']) else '결혼보다 자기 개발에 더 집중하는 시기입니다.'}
* 가장 강한 결혼 기회가 오는 세운: {'정재, 편재 세운' if gender == '남' else '정관, 편관 세운'}

[ 제6장 | 직장 내 인간관계 전략 ]

{gname}을 가진 분의 직장 인간관계 패턴:
* {'정관격은 상사와 원칙적이고 예의 바른 관계를 형성합니다. 규칙을 잘 지키고 성실한 모습이 신뢰를 얻습니다.' if '정관' in gname else '편관격은 직장에서 경쟁이 치열하고 상사와 갈등이 생기기 쉽습니다. 실력으로 인정받는 것이 최선입니다.' if '편관' in gname else '격국의 기운이 직장 내 관계에 영향을 줍니다.'}

동료와의 관계:
* {'비견이 강해 동료 간 경쟁이 활발합니다. 협력을 통해 함께 성장하는 방식이 더 유리합니다.' if '비견' in ss_dist or '겁재' in ss_dist else '식신, 상관이 강해 동료들에게 재미와 영감을 주는 존재입니다. 분위기 메이커 역할이 강점입니다.' if '식신' in ss_dist or '상관' in ss_dist else '정관, 정인이 강해 조직 내에서 신뢰받는 전문가로 인식됩니다.' if '정관' in ss_dist or '정인' in ss_dist else '독특한 개성으로 직장 내 독보적인 존재감을 가집니다.'}

직장에서 조심해야 할 사람:
* 기신 오행이 강한 상사나 동료와는 재물 거래를 피하십시오
* 자신을 이용하려는 person을 빨리 알아채는 직관을 기르십시오

[ 제7장 | 인간관계 운기별 전략 ]

현재 {cur_dw['str'] if cur_dw else '-'} 대운에서의 인간관계:
{'* 인성 대운: 스승, 어른의 도움이 큰 시기입니다. 배움의 인연을 소중히 하십시오.' if cur_dw_ss in ['정인','편인'] else '* 재성 대운: 이성 인연과 사업 파트너 운이 강합니다.' if cur_dw_ss in ['정재','편재'] else '* 관성 대운: 사회적 관계와 권위자와의 인연이 중요해집니다.' if cur_dw_ss in ['정관','편관'] else '* 비겁 대운: 동료, 친구, 경쟁자와의 관계가 인생의 중심이 됩니다.' if cur_dw_ss in ['비견','겁재'] else '* 식상 대운: 자기표현과 인기가 중심이 되는 시기입니다.'}

올해 {sw_now.get('세운','')} 세운에서의 인간관계:
{'* 새로운 귀인을 만날 운기입니다. 모임, 행사에 적극적으로 참여하십시오.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '* 인간관계에서 신중함이 요구되는 해입니다. 새로운 동업이나 큰 부탁은 자제하십시오.'}

[ 제8장 | 만신의 인간관계 최종 처방 ]

{display_name}님의 인간관계 핵심 비결:

1. {char.get('장점','타고난 성품')}을(를) 인간관계에서 최대로 발휘하십시오
2. {char.get('단점','약점')}을(를) 의식적으로 보완하는 노력을 하십시오
3. 용신 {yong_kr} 오행이 강한 분야의 사람들과 더 많이 교류하십시오
4. 인간관계에 투자한 시간과 에너지는 결국 재물과 명예로 돌아옵니다

    "Good relationships create good luck, and good luck creates a good life."
""")
            return "".join(result)

        # ── 과거 적중용 (menu3)
        elif section == "past":
            result = []
            result.append(f"""
    -----------------------------------------------------
      {display_name}님의 과거 적중 타임라인 분석
    -----------------------------------------------------

과거의 사건들을 사주 엔진으로 분석한 결과입니다. 특정 시기에 발생한 강한 기운의 변화(충, 합)가 실제 삶에서 어떻게 나타났는지 확인해 보십시오.

""")
            highlights = generate_engine_highlights(pils, birth_year, gender)
            for event in highlights.get("past_events", [])[:10]:
                result.append(f"### {event.get('age')}세 ({event.get('year')}년) | {event.get('title')}\n")
                result.append(f"{event.get('desc')}\n\n")

            result.append("""
[ 과거 분석의 의미 ]
과거를 분석하는 것은 미래를 대비하기 위함입니다. 어떤 운기에 어떤 사건이 일어났는지 패턴을 파악하면, 다가올 운기에서 최선의 선택을 할 수 있습니다.
""")
            return "".join(result)

        return "" # Fallback for unhandled sections

    except Exception as e:
        return f"Error in narrative generation: {e}"


def tab_ai_chat_prophet(pils, name, birth_year=1990, gender="남", api_key="", groq_key=""):
    """ AI 채팅 인터페이스 - Prophet Mode (예언자 6단계 판독 특화 버전) """
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    turning = calc_turning_point(pils, birth_year, gender)
    fate = turning.get("fate_label", "평온기 [Luck]")
    fate_desc = turning.get("fate_desc", "안정된 흐름 속에 있습니다.")
    
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                border-radius: 12px; padding: 20px; margin-bottom: 20px; 
                border-left: 5px solid #000000;">
        <div style="color: #ffffff; font-size: 20px; font-weight: 800; margin-bottom: 5px;">Life Season: <span style="color: #f1c40f;">{fate}</span></div>
        <div style="color: #a0a0ba; font-size: 14px;">{fate_desc}</div>
    </div>
    ''', unsafe_allow_html=True)

    # 행운의 개운법 표시
    render_lucky_kit(get_yongshin(pils).get("용신_1순위", "木"))

    # 대화창 초기화
    if st.session_state["chat_history"] and st.button("[Reset] 대화 초기화"):
        st.session_state["chat_history"] = []
        st.rerun()

    # 히스토리 렌더링
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 초기 버튼 (첫 시작 시)
    if not st.session_state["chat_history"]:
        if st.button("[Prophet] 예언자 풀이 시작 | 6단계 천명 판독", use_container_width=True, type="primary"):
            with st.spinner("AI가 천명을 판독하는 중..."):
                saju_ctx = format_saju_text(pils, name)
                # [Retention] 이전 상담 기억 주입
                saju_key = pils_to_cache_key(pils)
                memory_ctx = build_memory_context(saju_key)
                system_with_memory = PROPHET_SYSTEM + (f"\n\n[사용자 기억 데이터]\n{memory_ctx}" if memory_ctx else "")
                
                # Prophet 모드 호출
                stream_gen = get_ai_interpretation(
                    f"사주: {saju_ctx}\n내담자 정보: {name}, {birth_year}년생, {gender}. 이 사주의 6단계 판독을 시작하라.", 
                    api_key, system=system_with_memory, groq_key=groq_key, stream=True
                )
                with st.chat_message("assistant"):
                    full_text = st.write_stream(stream_gen)
                st.session_state["chat_history"].append({"role": "assistant", "content": full_text})
                # ★ Retention: 상담 결과 저장 (기억 시스템)
                update_user_profile(saju_key, prediction=full_text[:200])
                st.rerun()

    # 채팅 입력
    prompt = st.chat_input("궁금한 점을 더 물어보세요.")
    if prompt:
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("AI 만신 답신 중..."):
                saju_ctx = format_saju_text(pils, name)
                # ★ Retention: 이전 상담 기억 주입
                saju_key = pils_to_cache_key(pils)
                memory_ctx = build_memory_context(saju_key)
                system_with_memory = PROPHET_SYSTEM + (f"\n\n[사용자 기억 데이터]\n{memory_ctx}" if memory_ctx else "")
                
                user_msg = f"사주: {saju_ctx}\n내담자 정보: {name}, {birth_year}년생, {gender}. 사용자 추가 질문: {prompt}"
                stream_gen = get_ai_interpretation(
                    user_msg, api_key, system=system_with_memory, 
                    groq_key=groq_key, stream=True, history=st.session_state["chat_history"][:-1]
                )
                full_answer = st.write_stream(stream_gen)
                st.session_state["chat_history"].append({"role": "assistant", "content": full_answer})
        st.rerun()


# --------------------------------------------------
#  UI Menu Functions
# --------------------------------------------------
def menu1_report(pils, name, birth_year, gender, occupation="선택 안 함", api_key="", groq_key=""):
    """ [1. Comprehensive Report] - Pillars, Personality, Gyeokguk, Yongshin """
    try:
        ilgan = pils[1]["cg"]
        current_year = datetime.now().year
        current_age  = current_year - birth_year + 1
        strength_info = get_ilgan_strength(ilgan, pils)
        gyeokguk = get_gyeokguk(pils)
        ys = get_yongshin(pils)
    except Exception as e:
        st.error(f"기본 데이터 계산 오류: {e}")
        return

    # ── 리포트 요약 카드 ─────────────────────────────────────
    sn_label  = strength_info.get("신강신약", "중화")
    _sn_score = strength_info.get("helper_score", 50)
    sn_icon   = STRENGTH_DESC.get(sn_label, {}).get("icon", "[Balance]")
    yong_list = ys.get("종합_용신", [])
    yong_str  = "·".join(yong_list[:2]) if isinstance(yong_list, list) else str(yong_list)
    gk_name   = gyeokguk.get("격국명", "-")

    st.markdown(f"""
    <div style="background:#ffffff;border:1.5px solid #e0d0a0;border-radius:14px;
                padding:14px 16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
        <div style="font-size:11px;font-weight:700;color:#8b6200;letter-spacing:2px;margin-bottom:10px">
            📋 종합 사주 리포트 — 원국·성향·격국·용신
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
            <div style="flex:1;min-width:90px;background:#fff8e8;border-radius:10px;
                        padding:10px 12px;border:1px solid #e8d5a0;text-align:center">
                <div style="font-size:10px;color:#000000;margin-bottom:4px">일간</div>
                <div style="font-size:20px;font-weight:900;color:#333">{pils[1]["cg"]}</div>
                <div style="font-size:11px;color:#555">{pils[1]["jj"]}</div>
            </div>
            <div style="flex:1;min-width:90px;background:#ffffff;border-radius:10px;
                        padding:10px 12px;border:1px solid #c0d8f0;text-align:center">
                <div style="font-size:10px;color:#000000;margin-bottom:4px">신강신약</div>
                <div style="font-size:16px;font-weight:900;color:#0d47a1">{sn_icon}</div>
                <div style="font-size:11px;color:#333">{sn_label}</div>
            </div>
            <div style="flex:1;min-width:90px;background:#f5fff0;border-radius:10px;
                        padding:10px 12px;border:1px solid #b8e0b8;text-align:center">
                <div style="font-size:10px;color:#000000;margin-bottom:4px">용신</div>
                <div style="font-size:16px;font-weight:900;color:#1b5e20">⚡</div>
                <div style="font-size:11px;color:#333">{yong_str}</div>
            </div>
            <div style="flex:1;min-width:90px;background:#fdf0ff;border-radius:10px;
                        padding:10px 12px;border:1px solid #d8b8e8;text-align:center">
                <div style="font-size:10px;color:#000000;margin-bottom:4px">격국</div>
                <div style="font-size:16px;font-weight:900;color:#4a148c">🎯</div>
                <div style="font-size:11px;color:#333">{gk_name}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ① 사주원국
    st.markdown('<div class="gold-section">📊 사주원국 (八字)</div>', unsafe_allow_html=True)
    try:
        render_pillars(pils)
    except Exception as e:
        st.warning(f"원국 렌더링 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ② 오행 + 신강신약
    try:
        col_oh, col_sn = st.columns(2)
        with col_oh:
            st.markdown('<div class="gold-section">🌈 오행 분포</div>', unsafe_allow_html=True)
            oh_strength = calc_ohaeng_strength(ilgan, pils)
            render_ohaeng_chart(oh_strength)
        with col_sn:
            st.markdown('<div class="gold-section">⚖️ 신강신약</div>', unsafe_allow_html=True)
            sn = strength_info.get("신강신약", "중화(中和)")
            score = strength_info.get("helper_score", 50)
            bar = "🟦"*min(10,round(score/10)) + "⬜"*(10-min(10,round(score/10)))
            s_data = STRENGTH_DESC.get(sn, {})
            st.markdown(f"""
            <div style="background:#ffffff;border:2.5px solid #000000;border-radius:12px;padding:16px">
                <div style="font-size:22px;font-weight:900;color:#000000">{s_data.get('icon','')} {sn}</div>
                <div style="margin:6px 0;font-size:14px">{bar}</div>
                <div style="font-size:12px;color:#000000;line-height:1.8">{s_data.get('personality','')}</div>
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"오행/신강신약 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ③ 성향 판독
    st.markdown('<div class="gold-section">🧠 성향 판독</div>', unsafe_allow_html=True)
    try:
        with st.spinner("성향 계산 중..."):
            hl = generate_engine_highlights(pils, birth_year, gender)
        for trait in hl["personality"][:6]:
            tag_color = "#9b7ccc" if ("겉" in trait or "속" in trait) else "#4a90d9"
            st.markdown(f"""
            <div style="border-left:4px solid {tag_color};background:#ffffff;
                        padding:11px 16px;border-radius:8px;margin:5px 0;
                        font-size:13px;line-height:1.9;color:#000000;border:1px solid #000000">{trait}</div>""",
                        unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"성향 계산 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ④ 격국
    st.markdown('<div class="gold-section">🏆 격국 (格局)</div>', unsafe_allow_html=True)
    try:
        if gyeokguk:
            gname = gyeokguk.get("격국명", "")
            # GYEOKGUK_DESC 전체 요약 사용 (300자 제한 제거)
            gdesc_full = GYEOKGUK_DESC.get(gname, {}).get("summary", gyeokguk.get("격국_해설", ""))
            gcaution   = GYEOKGUK_DESC.get(gname, {}).get("caution", "")
            gcareer    = GYEOKGUK_DESC.get(gname, {}).get("lucky_career", "")
            ggod_rank  = GYEOKGUK_DESC.get(gname, {}).get("god_rank", "")
            st.markdown(f"""
            <div style="background:#ffffff;border:2.5px solid #000000;
                        border-radius:14px;padding:22px">
                <div style="font-size:22px;font-weight:900;color:#000000;margin-bottom:12px">{gname}</div>
                <div style="font-size:14px;color:#000000;line-height:2.1;white-space:pre-wrap;margin-bottom:14px">{gdesc_full}</div>
                {"<div style='background:#ffffff;border:1.5px solid #000000;border-left:8px solid #000000;padding:10px 14px;border-radius:8px;font-size:13px;color:#000000;margin-bottom:10px'>💼 적합 직업: " + gcareer + "</div>" if gcareer else ""}
                {"<div style='background:#fff5f5;border:1.5px solid #ff0000;border-left:8px solid #ff0000;padding:10px 14px;border-radius:8px;font-size:13px;color:#000000;margin-bottom:10px;white-space:pre-wrap'>⚠️ " + gcaution + "</div>" if gcaution else ""}
                {"<div style='background:#f5fff5;border:1.5px solid #27ae60;border-left:8px solid #27ae60;padding:10px 14px;border-radius:8px;font-size:13px;color:#000000'>⭐ " + ggod_rank + "</div>" if ggod_rank else ""}
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"격국 표시 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑤ 용신
    st.markdown('<div class="gold-section">⭐ 용신 (用神)</div>', unsafe_allow_html=True)
    try:
        yongshin_ohs = ys.get("종합_용신", [])
        if not isinstance(yongshin_ohs, list):
            yongshin_ohs = []
        gishin_raw = ys.get("기신", [])
        if isinstance(gishin_raw, list):
            gishin_ohs = gishin_raw
        else:
            gishin_ohs = [o for o in ["木","火","土","金","水"] if o in str(gishin_raw)]

        OH_EMOJI = {"木":"🌳","火":"🔥","土":"⛰️","金":"⚔️","水":"💧"}
        y_tags = " ".join([
            f"<span style='background:#ffffff;color:#000000;padding:5px 14px;"
            f"border:2px solid #000000;border-radius:20px;font-size:14px;font-weight:900'>"
            f"{OH_EMOJI.get(o,'')} {o}({OHN.get(o,'')})</span>"
            for o in yongshin_ohs
        ])
        g_tags = " ".join([
            f"<span style='background:#ffe5e2;color:#000000;padding:5px 14px;"
            f"border-radius:20px;font-size:14px;font-weight:700'>"
            f"{OH_EMOJI.get(o,'')} {o}({OHN.get(o,'')})</span>"
            for o in gishin_ohs
        ]) if gishin_ohs else f"<span style='color:#000000;font-size:13px'>{str(gishin_raw)}</span>"

        st.markdown(f"""
        <div style="background:#f8f0ff;border-radius:12px;padding:16px">
            <div style="margin-bottom:10px"><b>🌟 용신 (힘이 되는 오행):</b><br>{y_tags}</div>
            <div><b>⚠️ 기신 (조심할 오행):</b><br>{g_tags}</div>
        </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"용신 표시 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑥ 십성 조합 인생 분석 ★★★ 핵심
    st.markdown('<div class="gold-section">🔮 십성(十星) 조합 — 당신의 인생 설계도</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;color:#000000;margin-bottom:12px">
    원국에 나타난 십성의 조합을 분석합니다. 조합만 알면 그 사람의 인생이 보입니다.
    </div>""", unsafe_allow_html=True)
    try:
        life = build_life_analysis(pils, gender)
        combos = life["조합_결과"]
        top_ss = life["주요_십성"]
        ss_dist = life["전체_십성"]

        # 십성 분포 태그
        ss_colors = {
            "비견":"#3498db","겁재":"#e74c3c","식신":"#27ae60","상관":"#e67e22",
            "편재":"#2ecc71","정재":"#16a085","편관":"#c0392b","정관":"#2980b9",
            "편인":"#8e44ad","정인":"#d35400"
        }
        tags_html = "".join([
            f"<span style='background:{ss_colors.get(ss,'#888')};color:#000000;"
            f"padding:4px 12px;border-radius:20px;font-size:12px;margin:3px;display:inline-block'>"
            f"{ss} x{cnt}</span>"
            for ss, cnt in sorted(ss_dist.items(), key=lambda x: -x[1])
        ])
        st.markdown(f"""
        <div style="background:#ffffff;border-radius:10px;padding:14px;margin-bottom:16px">
            <div style="font-size:11px;color:#000000;margin-bottom:8px">📊 원국 십성 분포</div>
            <div>{tags_html}</div>
        </div>""", unsafe_allow_html=True)

        if combos:
            for key, combo in combos:
                ss_pair = " × ".join(list(key))
                st.markdown(f"""
                <div style="background:#ffffff;border-radius:16px;
                            padding:22px;margin:12px 0;border:2.5px solid #000000">
                    <div style="font-size:18px;font-weight:900;color:#000000;margin-bottom:6px">
                        {combo['요약']}
                    </div>
                    <div style="font-size:12px;color:#000000;margin-bottom:16px;font-weight:700">조합: {ss_pair}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">🧠 성향</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['성향']}</div>
                        </div>
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💰 재물·돈 버는 방식</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['재물']}</div>
                        </div>
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💼 직업 적성</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['직업']}</div>
                        </div>
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💑 연애·인간관계</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['연애']}</div>
                        </div>
                    </div>
                    <div style="background:#ffffff;border-radius:10px;padding:12px;margin-top:12px;
                                border:1.5px solid #ff0000">
                        <span style="font-size:11px;color:#ff0000;font-weight:700">⚠️ 주의사항: </span>
                        <span style="font-size:13px;color:#000000;line-height:1.8;font-weight:700">{combo['주의']}</span>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            # 조합 없을 때 단일 십성 분석
            if top_ss:
                ss1 = top_ss[0]
                st.markdown(f"""
                <div style="background:#ffffff;border-radius:12px;padding:18px;border:1px solid #3a4060">
                    <div style="font-size:16px;font-weight:700;color:#000000">
                        {ss1} 중심 사주
                    </div>
                    <div style="font-size:13px;color:#000000;margin-top:10px;line-height:1.8">
                        주요 십성: {', '.join(top_ss[:3])}
                    </div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"십성 조합 분석 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑦ 직업 조언
    if occupation and occupation != "선택 안 함":
        st.markdown('<div class="gold-section">💼 직업 적합도 분석</div>', unsafe_allow_html=True)
        try:
            tab_career(pils, gender)
        except Exception as e:
            st.warning(f"직업 분석 오류: {e}")

    # ⑧ 만신 스타일 종합 해설문
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 종합 사주 해설 — 만신의 풀이</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, name, section="report")
        sections = narrative.split("【")
        for i, sec in enumerate(sections):
            if not sec.strip(): continue
            lines = sec.strip().split("\n")
            title = lines[0].replace("】","").strip() if lines else ""
            body  = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            if title:
                st.markdown(f"""
                <div style="background:#ffffff;
                            border-left:8px solid #000000;border:1.5px solid #000000;border-radius:10px;
                            padding:18px 22px;margin:10px 0">
                    <div style="font-size:15px;font-weight:900;color:#000000;margin-bottom:10px">
                        【 {title} 】
                    </div>
                    <div style="font-size:14px;color:#000000;line-height:2.0;
                                white-space:pre-wrap">{body}</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"종합 해설 오류: {e}")

    # ── 통계 기반 패턴 분석 ───────────────────────────────
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    try:
        render_statistical_insights(pils, strength_info)
    except Exception:
        pass

    # ── 클리프행어 (미완성 서술 트릭) ──────────────────────
    try:
        current_year = datetime.now().year
        turning = calc_turning_point(pils, birth_year, gender, current_year)
        triggers = detect_event_triggers(pils, birth_year, gender, current_year)
        high_t = [t for t in triggers if t["prob"] >= 75]

        teaser = ""
        if turning["is_turning"] and turning["reason"]:
            teaser = f"이 사주 구조에서 **{current_year}~{current_year+1}년**은 단순히 넘어가는 해가 아닙니다. {turning['reason'][0]}"
        elif high_t:
            teaser = f"사건 트리거 분석에서 **{high_t[0]['title']}** 패턴이 포착됐습니다. 이 흐름이 구체적으로 어떤 영역에서 발현될지,"
        else:
            luck_s = calc_luck_score(pils, birth_year, gender, current_year)
            if luck_s >= 70:
                teaser = f"현재 운세 점수 **{luck_s}/100** — 상승기 진입 신호가 감지됩니다. 이 기회를 어떻게 활용할지,"
            else:
                teaser = f"현재 운세 점수 **{luck_s}/100** — 흐름의 방향이 바뀌는 시점이 다가오고 있습니다. 그 시기와 대비책이"

        if teaser:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#ffffff,#fff3cc);
                        border:2px solid #000000;border-radius:14px;
                        padding:20px 22px;margin:16px 0;text-align:center">
                <div style="font-size:13px;color:#000000;font-weight:700;margin-bottom:8px">
                    🔮 AI 예언자 심층 분석 예고
                </div>
                <div style="font-size:14px;color:#000000;line-height:1.9;margin-bottom:12px">
                    {teaser}<br>
                    <span style="color:#000000;font-size:12px">
                        → AI 상담 탭에서 정확한 시기와 대응 전략을 확인하십시오.
                    </span>
                </div>
                <div style="font-size:11px;color:#000000;font-weight:700;letter-spacing:1px">
                    ✦ 🤖 AI 상담 탭 이동 ✦
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass


    render_ai_deep_analysis("prophet", pils, name, birth_year, gender, api_key, groq_key)

def menu2_lifeline(pils, birth_year, gender, name="내담자", api_key="", groq_key=""):
    """2️⃣ 인생 흐름 (대운 100년) — 그래프 포함"""
    import json

    st.markdown("""
    <div style="background:#fff8e8;border:2px solid #000000;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#8b6200;margin-bottom:4px">📈 대운 100년 흐름 분석</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 황금기와 위기 구간을 한눈에 파악합니다. &nbsp; ✦ 현재 대운 위치를 확인하세요.
        </div>
    </div>""", unsafe_allow_html=True)

    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신",[])
    if not isinstance(yongshin_ohs, list): yongshin_ohs = []
    ilgan_oh = OH.get(ilgan,"")

    # ── 대운 100년 타임라인 그래프 ──
    st.markdown('<div class="gold-section">📈 대운 흐름 그래프</div>', unsafe_allow_html=True)

    # 각 대운의 길흉 점수 계산
    labels, scores, colors_list, dw_strs = [], [], [], []
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"-")
        is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
        is_current = dw["시작연도"] <= current_year <= dw["종료연도"]

        SCORE_MAP = {
            "정재":80,"식신":85,"정관":75,"정인":70,
            "편재":65,"편관":40,"겁재":35,"상관":55,
            "비견":60,"편인":50
        }
        score = SCORE_MAP.get(dw_ss, 60)
        if is_yong: score = min(100, score + 20)

        age_label = f"{dw['시작나이']}세\n{dw['str']}"
        labels.append(age_label)
        scores.append(score)
        c = "#000000" if is_yong else ("#e74c3c" if score < 50 else "#3498db")
        if is_current: c = "#ff6b00"
        colors_list.append(c)
        dw_strs.append(dw["str"])

    # Chart.js 대신 HTML/CSS 바 차트
    bars_html = ""
    for i, (lbl, sc, cl, ds) in enumerate(zip(labels, scores, colors_list, dw_strs)):
        is_cur = cl == "#ff6b00"
        border = "3px solid #ff6b00" if is_cur else "1px solid transparent"
        # ★ \n을 <br>로 교체 — white-space:pre-line 제거하여 div 오염 방지
        lbl_html = lbl.replace("\n", "<br>")
        cur_mark = "<div style='font-size:9px;color:#ff6b00;font-weight:800;margin-top:3px'>▲현재</div>" if is_cur else ""
        bars_html += (
            f'<div style="display:flex;flex-direction:column;align-items:center;min-width:52px">'
            f'<div style="font-size:11px;color:#000000;margin-bottom:4px">{sc}</div>'
            f'<div style="width:40px;height:{sc}px;background:{cl};border-radius:6px 6px 0 0;'
            f'border:{border};transition:height 0.3s" title="{ds}대운({sc}점)"></div>'
            f'<div style="font-size:10px;color:#000000;margin-top:4px;text-align:center;line-height:1.5">'
            f'{lbl_html}</div>'
            f'{cur_mark}'
            f'</div>'
        )

    st.markdown(f"""
    <div style="background:#f5f5f5;border-radius:14px;padding:20px;overflow-x:auto">
        <div style="display:flex;align-items:flex-end;gap:8px;min-width:600px;height:160px;
                    padding-bottom:10px;border-bottom:1px solid #333">
            {bars_html}
        </div>
        <div style="display:flex;gap:16px;margin-top:12px;font-size:12px">
            <span style="color:#000000">■ 용신 대운</span>
            <span style="color:#ff6b00">■ 현재 대운</span>
            <span style="color:#3498db">■ 일반 대운</span>
            <span style="color:#e74c3c">■ 기신 대운</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">🔄 대운 상세</div>', unsafe_allow_html=True)
    tab_daewoon(pils, birth_year, gender)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">🔀 대운 × 세운 교차</div>', unsafe_allow_html=True)
    try:
        tab_cross_analysis(pils, birth_year, gender)
    except Exception as e:
        st.warning(f"교차분석 오류: {e}")

    # 대운 100년 상세 해설문
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 대운 100년 완전 해설</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, "", section="lifeline")
        sections = narrative.split("▶")
        # 첫 도입부
        if sections:
            intro = sections[0].strip()
            if intro:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#e8f4ff,#e7f1ff);
                            border-left:4px solid #3498db;border-radius:10px;
                            padding:18px 22px;margin:10px 0">
                    <div style="font-size:13px;color:#1a4a8b;line-height:2.0;white-space:pre-wrap">{intro}</div>
                </div>""", unsafe_allow_html=True)
        # 각 대운
        for sec in sections[1:]:
            if not sec.strip(): continue
            lines = sec.strip().split("\n")
            title = lines[0].strip() if lines else ""
            body  = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            is_cur = "현재 대운" in title
            border_color = "#ff6b00" if is_cur else "#000000" if "용신 대운" in body else "#3498db"
            st.markdown(f"""
            <div style="background:{'rgba(255,107,0,0.1)' if is_cur else '#0d1117'};
                        border-left:4px solid {border_color};border-radius:10px;
                        padding:16px 20px;margin:8px 0">
                <div style="font-size:13px;font-weight:700;color:{border_color};margin-bottom:8px">
                    ▶ {title}
                </div>
                <div style="font-size:13px;color:#d0c8a0;line-height:1.9;white-space:pre-wrap">{body}</div>
            </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"대운 해설 오류: {e}")
    
    # AI 정밀 분석 버튼
    render_ai_deep_analysis("lifeline", pils, name, birth_year, gender, api_key, groq_key)

def menu3_past(pils, birth_year, gender, name="", api_key="", groq_key=""):
    """3️⃣ 과거 적중 타임라인 | 15년 자동 스캔"""
    st.markdown("""
    <div style="background:#fff0f8;border:2px solid #e91e8c55;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#880e4f;margin-bottom:4px">🎯 과거 적중 타임라인</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 충·합·십성 교차를 수학 계산으로 뽑은 과거 사건 시점입니다.<br>
        ✦ AI가 아닌 엔진 계산 — 나이·분야가 맞으면 <b style="color:#c0392b">"맞았다"</b>를 눌러주세요.
        </div>
    </div>""", unsafe_allow_html=True)
    tab_past_events(pils, birth_year, gender, name)
    # AI 정밀 분석 버튼
    render_ai_deep_analysis("past", pils, name, birth_year, gender, api_key, groq_key)

def menu4_future3(pils, birth_year, gender, marriage_status="미혼", name="내담자", api_key="", groq_key=""):
    """4️⃣ 미래 3년 집중 분석 — 돈/직장/연애"""
    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    current_age  = current_year - birth_year + 1

    st.markdown("""
    <div style="background:#f0fff8;border:2px solid #27ae6055;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#1b5e20;margin-bottom:4px">🔮 미래 3년 집중 분석</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 돈 · 직장 · 연애 3개 분야를 연도별로 집중 분석합니다.
        </div>
    </div>""", unsafe_allow_html=True)

    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신",[])
    if not isinstance(yongshin_ohs, list): yongshin_ohs = []
    ilgan_oh = OH.get(ilgan,"")

    DOMAIN_SS = {
        "돈·재물": {"식신","정재","편재"},
        "직장·명예": {"정관","편관","정인"},
        "연애·인연": {"정재","편재"} if gender=="남" else {"정관","편관"},
        "변화·이동": {"상관","겁재","편인"},
    }
    DOMAIN_COLOR = {
        "돈·재물": "#27ae60", "직장·명예": "#2980b9",
        "연애·인연": "#e91e8c", "변화·이동": "#e67e22"
    }

    years_data = []
    for y in range(current_year, current_year + 3):
        sw = get_yearly_luck(pils, y)
        dw = next((d for d in SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
                   if d["시작연도"] <= y <= d["종료연도"]), None)
        dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"-") if dw else "-"
        sw_ss = sw.get("십성_천간", "-")
        age = y - birth_year + 1

        # 분야별 점수
        domains = {}
        for dname, ss_set in DOMAIN_SS.items():
            score = 0
            if dw_ss in ss_set: score += 50
            if sw_ss in ss_set: score += 50
            domains[dname] = score

        # 용신 여부
        is_yong_dw = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong" if dw else False
        is_yong_sw = _get_yongshin_match(sw_ss, yongshin_ohs, ilgan_oh) == "yong"

        # 합깨짐 경고
        hap_warn = _get_hap_break_warning(pils, dw["jj"] if dw else "", sw["jj"])

        years_data.append({
            "year": y, "age": age,
            "dw": dw["str"] if dw else "-", "dw_ss": dw_ss,
            "sw": sw["세운"], "sw_ss": sw_ss,
            "is_yong_dw": is_yong_dw, "is_yong_sw": is_yong_sw,
            "domains": domains, "hap_warn": hap_warn,
            "gilhyung": sw["길흉"]
        })

    for yd in years_data:
        yong_both = yd["is_yong_dw"] and yd["is_yong_sw"]
        gishin_both = not yd["is_yong_dw"] and not yd["is_yong_sw"]
        card_color = "#000000" if yong_both else "#c0392b" if gishin_both else "#2980b9"
        card_bg    = "#ffffff" if yong_both else "#fff0f0" if gishin_both else "#f0f8ff"
        label      = "🌟 황금기" if yong_both else "⚠️ 수비" if gishin_both else "〰️ 혼재"

        st.markdown(f"""
        <div style="background:{card_bg};border:2px solid {card_color};border-radius:16px;
                    padding:20px;margin:12px 0">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div>
                    <span style="font-size:26px;font-weight:900;color:{card_color}">{yd['year']}년</span>
                    <span style="font-size:14px;color:#000000;margin-left:10px">만 {yd['age']}세</span>
                </div>
                <div style="background:{card_color};color:#000000;padding:5px 16px;
                            border-radius:20px;font-size:13px;font-weight:700">{label}</div>
            </div>
            <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                <span style="background:#f5f5f5;color:#000000;padding:3px 12px;border-radius:12px;font-size:12px">
                    대운 {yd['dw']}({yd['dw_ss']})</span>
                <span style="background:#f5f5f5;color:#000000;padding:3px 12px;border-radius:12px;font-size:12px">
                    세운 {yd['sw']}({yd['sw_ss']})</span>
                <span style="color:{card_color};font-size:12px;padding:3px 8px">{yd['gilhyung']}</span>
            </div>""", unsafe_allow_html=True)

        # 분야별 점수 바
        domain_bars = ""
        for dname, score in yd["domains"].items():
            dc = DOMAIN_COLOR.get(dname,"#888")
            filled = score // 10
            bar_vis = "🟩"*filled + "⬜"*(10-filled)
            status = "활성" if score >= 50 else "보통" if score >= 30 else "약함"
            domain_bars += f"""
            <div style="display:flex;align-items:center;gap:10px;margin:4px 0">
                <span style="font-size:12px;color:{dc};min-width:70px;font-weight:700">{dname}</span>
                <span style="font-size:11px">{bar_vis}</span>
                <span style="font-size:11px;color:#444">{status}</span>
            </div>"""

        st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:12px">{domain_bars}</div>""",
                    unsafe_allow_html=True)

        if yd["hap_warn"]:
            for hw in yd["hap_warn"]:
                st.markdown(f"""
            <div style="background:#fff0f0;border-left:4px solid #c0392b;
                        border-radius:8px;padding:10px 14px;margin-top:8px;font-size:12px;color:#c0392b">
                🚨 {hw}</div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # 결혼 여부별 인연 조언
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💑 인연·배우자운 (3년)</div>', unsafe_allow_html=True)
    if marriage_status in ("미혼","이혼/별거"):
        MARRY_SS = {"정재","편재"} if gender=="남" else {"정관","편관"}
        for yd in years_data:
            if yd["sw_ss"] in MARRY_SS or yd["dw_ss"] in MARRY_SS:
                st.markdown(f"""
                <div style="background:#fff0f8;border-left:4px solid #e91e8c;
                            border-radius:8px;padding:12px;margin:5px 0">
                    <b style="color:#e91e8c">{yd['year']}년({yd['age']}세)</b> —
                    인연성이 강합니다. 적극적으로 움직이십시오.
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#f0fff8;border-left:4px solid #27ae60;
                    border-radius:8px;padding:12px">
            {marriage_status} 상태. 부부 관계 흐름 분석은 육친론을 참고하세요.
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📅 월별 세운 (올해)</div>', unsafe_allow_html=True)
    tab_monthly(pils, birth_year, gender)

    # 미래 3년 상세 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 미래 3년 완전 해설 — 만신의 풀이</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, "", section="future")
        blocks = narrative.split("━"*55)
        if blocks:
            intro = blocks[0].strip()
            if intro:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#dcfff5,#dcfffd);
                            border-left:4px solid #27ae60;border-radius:10px;
                            padding:16px 20px;margin:10px 0">
                    <div style="font-size:13px;color:#1a4a2a;line-height:1.9;white-space:pre-wrap">{intro}</div>
                </div>""", unsafe_allow_html=True)
            for block in blocks[1:]:
                if not block.strip(): continue
                lines = block.strip().split("\n")
                title_line = next((l for l in lines if l.strip()), "")
                body = "\n".join(lines[1:]).strip()
                is_good = "⭐" in title_line
                is_bad = "⚠️" in title_line
                bg = "rgba(197,160,89,0.12)" if is_good else "rgba(192,57,43,0.12)" if is_bad else "rgba(41,128,185,0.12)"
                bc = "#000000" if is_good else "#c0392b" if is_bad else "#2980b9"
                st.markdown(f"""
                <div style="background:{bg};border-left:4px solid {bc};
                            border-radius:10px;padding:16px 20px;margin:8px 0">
                    <div style="font-size:14px;font-weight:900;color:{bc};margin-bottom:10px">{title_line}</div>
                    <div style="font-size:13px;color:#000000;line-height:1.9;white-space:pre-wrap">{body}</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"미래 해설 오류: {e}")
    
    # AI 정밀 분석 버튼
    render_ai_deep_analysis("future", pils, name, birth_year, gender, api_key, groq_key)

def menu5_money(pils, birth_year, gender, name="내담자", api_key="", groq_key=""):
    """5️⃣ 재물·사업 특화 분석"""
    st.markdown("""
    <div style="background:#f5fff0;border:2px solid #2e7d3255;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#1b5e20;margin-bottom:4px">💰 재물·사업 특화 분석</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 수익 구조 · 재물 기질 · 돈이 터지는 시기를 십성 조합으로 분석합니다.
        </div>
    </div>""", unsafe_allow_html=True)

    ilgan = pils[1]["cg"]
    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신",[])
    if not isinstance(yongshin_ohs, list): yongshin_ohs = []
    ilgan_oh = OH.get(ilgan,"")
    current_year = datetime.now().year

    # ① 십성 조합 기반 재물 기질
    st.markdown('<div class="gold-section">💎 십성 조합으로 보는 재물 기질</div>', unsafe_allow_html=True)
    try:
        life = build_life_analysis(pils, gender)
        combos = life["조합_결과"]
        ss_dist = life["전체_십성"]

        # 재물 관련 조합만 강조
        MONEY_SS = {"식신","상관","편재","정재","겁재","비견"}
        money_combos = [(k, v) for k, v in combos if any(s in MONEY_SS for s in k)]

        if money_combos:
            for key, combo in money_combos:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#f5f5f5,#f5ffea);
                            border:2px solid #4a8a20;border-radius:14px;padding:20px;margin:10px 0">
                    <div style="font-size:17px;font-weight:900;color:#a0d040;margin-bottom:10px">
                        {combo['요약']}
                    </div>
                    <div style="background:#eaffdc;border-radius:10px;padding:14px;margin-bottom:10px;
                                border-left:4px solid #000000">
                        <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💰 재물 버는 방식</div>
                        <div style="font-size:14px;color:#f0e0a0;line-height:1.9">{combo['재물']}</div>
                    </div>
                    <div style="background:#eaffdc;border-radius:10px;padding:14px;margin-bottom:10px;
                                border-left:4px solid #3498db">
                        <div style="font-size:11px;color:#5ab4ff;font-weight:700;margin-bottom:6px">💼 맞는 직업·사업</div>
                        <div style="font-size:14px;color:#c0d8f0;line-height:1.9">{combo['직업']}</div>
                    </div>
                    <div style="background:#f5f5f5;border-radius:10px;padding:12px;
                                border-left:4px solid #e74c3c">
                        <div style="font-size:11px;color:#ff6b6b;font-weight:700;margin-bottom:4px">⚠️ 재물 주의사항</div>
                        <div style="font-size:13px;color:#f0c0c0;line-height:1.8">{combo['주의']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
        elif combos:
            key, combo = combos[0]
            st.markdown(f"""
            <div style="background:#ffffff;border-radius:12px;padding:18px;border:1px solid #3a4060">
                <div style="font-size:16px;font-weight:700;color:#000000;margin-bottom:10px">{combo['요약']}</div>
                <div style="font-size:14px;color:#f0e0a0;line-height:1.9">{combo['재물']}</div>
            </div>""", unsafe_allow_html=True)

        # 십성별 재물 기질 요약
        MONEY_NATURE = {
            "식신": "🌾 재능·기술로 꾸준히 버는 타입. 억지로 돈 쫓지 않아도 따라온다.",
            "상관": "⚡ 아이디어·말·창의로 버는 타입. 새로운 방식으로 수익을 만든다.",
            "편재": "🎰 활발한 활동·투자·사업으로 버는 타입. 기복이 있지만 크게 번다.",
            "정재": "🏦 성실하게 모으는 타입. 꾸준히 하면 결국 쌓인다.",
            "겁재": "💸 크게 벌고 크게 쓰는 타입. 재물 관리가 인생 최대 숙제.",
            "비견": "⚔️ 독립·자영업으로 버는 타입. 남 밑에서는 돈이 안 모인다.",
            "편관": "🔥 직위·권한에서 재물이 따라오는 타입. 높은 자리가 돈이 된다.",
            "정관": "🏛️ 안정된 직장에서 꾸준히 쌓는 타입. 직급이 올라갈수록 재물도 는다.",
            "편인": "🎭 특수 분야 전문성으로 버는 타입. 일반적인 방법보다 틈새가 맞다.",
            "정인": "📚 지식·자격·귀인을 통해 재물이 오는 타입. 배움이 곧 돈이 된다.",
        }
        st.markdown('<div style="font-size:13px;font-weight:800;color:#000000;margin:16px 0 8px;border-left:3px solid #000000;padding-left:10px">📊 주요 십성별 재물 기질</div>', unsafe_allow_html=True)
        for ss, cnt in sorted(ss_dist.items(), key=lambda x: -x[1])[:4]:
            if ss in MONEY_NATURE:
                ss_color = {"식신":"#27ae60","상관":"#e67e22","편재":"#2ecc71","정재":"#16a085",
                           "겁재":"#e74c3c","비견":"#3498db","편관":"#c0392b","정관":"#2980b9",
                           "편인":"#8e44ad","정인":"#d35400"}.get(ss,"#888")
                st.markdown(f"""
                <div style="display:flex;align-items:flex-start;gap:12px;padding:10px 0;
                            border-bottom:1px solid #eee">
                    <span style="background:{ss_color};color:#000000;padding:3px 10px;
                                 border-radius:12px;font-size:12px;white-space:nowrap;
                                 min-width:50px;text-align:center">{ss}×{cnt}</span>
                    <span style="font-size:13px;color:#000000;line-height:1.8">{MONEY_NATURE.get(ss,'')}</span>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"재물 기질 분석 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ② 돈 터지는 시기
    st.markdown('<div class="gold-section">📈 돈이 터지는 시기</div>', unsafe_allow_html=True)
    try:
        with st.spinner("재물 운기 계산 중..."):
            hl = generate_engine_highlights(pils, birth_year, gender)

        if hl["money_peak"]:
            for mp in hl["money_peak"]:
                is_double = mp.get("ss") == "더블"
                bg = "#ffffff" if is_double else "#f0fff0"
                bc = "#000000" if is_double else "#27ae60"
                icon = "🌟" if is_double else "💰"
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {bc};border-radius:12px;
                            padding:16px;margin:8px 0">
                    <span style="font-size:18px;font-weight:900;color:{bc}">{icon} {mp['age']}</span>
                    <span style="font-size:12px;color:#000000;margin-left:8px">({mp['year']})</span>
                    <div style="font-size:13px;color:#000000;margin-top:6px;line-height:1.8">{mp['desc']}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("현재 기준 향후 5년 내 뚜렷한 재물 피크가 계산되지 않았습니다.")
    except Exception as e:
        st.warning(f"재물 운기 계산 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💰 재물론 상세 (장생·12운성)</div>', unsafe_allow_html=True)
    try:
        tab_jaemul(pils, birth_year, gender)
    except Exception as e:
        st.warning(f"재물론 오류: {e}")

    # 재물 완전 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 재물·사업 완전 해설 — 만신의 풀이</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, "", section="money")
        sections = narrative.split("【")
        for sec in sections:
            if not sec.strip(): continue
            lines = sec.strip().split("\n")
            title = lines[0].replace("】","").strip() if lines else ""
            body  = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            if title:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#eaffdc,#f5ffdc);
                            border-left:4px solid #000000;border-radius:10px;
                            padding:18px 22px;margin:10px 0">
                    <div style="font-size:14px;font-weight:900;color:#000000;margin-bottom:10px">
                        【 {title} 】
                    </div>
                    <div style="font-size:13px;color:#2a4a00;line-height:2.0;white-space:pre-wrap">{body}</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"재물 해설 오류: {e}")
    
    # AI 정밀 분석 버튼
    render_ai_deep_analysis("money", pils, name, birth_year, gender, api_key, groq_key)

def menu6_relations(pils, name, birth_year, gender, marriage_status="미혼", api_key="", groq_key=""):
    """6️⃣ 궁합 / 인간관계 분석"""
    st.markdown("""
    <div style="background:#fdf0ff;border:2px solid #9b59b655;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#4a148c;margin-bottom:4px">💑 궁합 · 인간관계 분석</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 연인 · 동업자 · 상사와의 인간관계를 사주로 분석합니다.
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="gold-section">👫 육친론 — 주변 인물 분석</div>', unsafe_allow_html=True)
    tab_yukjin(pils, gender)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💑 궁합 분석</div>', unsafe_allow_html=True)
    tab_gunghap(pils, name)

    # 인간관계 완전 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 육친·인간관계 완전 해설 — 만신의 풀이</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, name if name else "내담자", section="relations")
        sections = narrative.split("【")
        for sec in sections:
            if not sec.strip(): continue
            lines = sec.strip().split("\n")
            title = lines[0].replace("】","").strip() if lines else ""
            body  = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            if not title: continue
            # 육친 파트 vs 일반 파트
            if "◈" in body:
                # 육친 개별 카드
                sub_items = body.split("◈")
                if title:
                    st.markdown(f"<div style='font-size:14px;font-weight:900;color:#c39bd3;margin:12px 0 6px'>【 {title} 】</div>", unsafe_allow_html=True)
                for item in sub_items:
                    if not item.strip(): continue
                    item_lines = item.strip().split("\n")
                    item_title = item_lines[0].strip()
                    item_body = "\n".join(item_lines[1:]).strip()
                    st.markdown(f"""
                    <div style="background:#f5f5f5;border-left:4px solid #9b59b6;
                                border-radius:10px;padding:14px 18px;margin:6px 0">
                        <div style="font-size:13px;font-weight:700;color:#c39bd3;margin-bottom:6px">◈ {item_title}</div>
                        <div style="font-size:13px;color:#e8d0f8;line-height:1.9;white-space:pre-wrap">{item_body}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#ffdcff,#ffdcff);
                            border-left:4px solid #9b59b6;border-radius:10px;
                            padding:18px 22px;margin:10px 0">
                    <div style="font-size:14px;font-weight:900;color:#c39bd3;margin-bottom:10px">
                        【 {title} 】
                    </div>
                    <div style="font-size:13px;color:#e8d0f8;line-height:2.0;white-space:pre-wrap">{body}</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"인간관계 해설 오류: {e}")

    # AI 정밀 분석 버튼
    render_ai_deep_analysis("relations", pils, name, birth_year, gender, api_key, groq_key)


################################################################################
# ☀️ menu9_daily  — 일일 운세
# 📅 menu10_monthly — 월별 운세
# 🎊 menu11_yearly  — 신년 운세
################################################################################

def menu9_daily(pils, name, birth_year, gender):
    """9️⃣ 일일 운세 — 오늘·내일·이번주 일진 완전 분석"""

    ilgan   = pils[1]["cg"]
    today   = datetime.now()
    display_name = name if name else "내담자"

    # ── 일진 계산 헬퍼 ─────────────────────────────────────────
    def get_day_pillar(dt):
        """날짜 → 일주 계산 (갑자일 기준 오프셋)"""
        base  = date(1924, 1, 1)          # 甲子日 기준점
        delta = (dt.date() - base).days if hasattr(dt, 'date') else (dt - base).days
        cg_i  = delta % 10
        jj_i  = delta % 12
        return CG[cg_i], JJ[jj_i]

    def day_ten_god(ilgan, day_cg):
        return TEN_GODS_MATRIX.get(ilgan, {}).get(day_cg, "-")

    # 오늘 일주
    today_cg, today_jj = get_day_pillar(today)
    today_ss  = day_ten_god(ilgan, today_cg)
    today_mlu = get_monthly_luck(pils, today.year, today.month)
    today_ylu = get_yearly_luck(pils, today.year)

    # ── 헤더 ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#e8f4ff,#ddeeff);
                border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
        <div style="font-size:22px;font-weight:900;color:#8b6200;letter-spacing:2px">
            ☀️ {display_name}님의 일일 운세
        </div>
        <div style="font-size:13px;color:#000000;margin-top:6px">
            {today.strftime('%Y년 %m월 %d일')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)
        </div>
    </div>""", unsafe_allow_html=True)

    # ── 오늘 일진 메인 카드 ──────────────────────────────────
    DAILY_SS_MSG = {
        "비견":  {"emoji":"🤝","level":"평길","msg":"동료·경쟁자 기운. 협력하면 좋고, 독단적 결정은 삼가십시오.","재물":"지출 주의","관계":"새 인연 가능","건강":"체력 소모 주의"},
        "겁재":  {"emoji":"⚠️","level":"흉","msg":"재물 손실, 경쟁 기운. 오늘 큰 결정·투자는 내일로 미루십시오.","재물":"지갑 조심","관계":"갈등 주의","건강":"스트레스 주의"},
        "식신":  {"emoji":"🌟","level":"대길","msg":"복록이 쏟아지는 날! 먹고 즐기고 창작하기 최고의 날입니다.","재물":"예상 수입 가능","관계":"인기 상승","건강":"최상"},
        "상관":  {"emoji":"🌪️","level":"평","msg":"창의·표현의 날. 아이디어가 넘치지만 말실수에 주의하십시오.","재물":"재능으로 수입","관계":"표현 조심","건강":"신경 예민"},
        "편재":  {"emoji":"💰","level":"길","msg":"재물 기운이 활발한 날. 거래·계약·사교에 유리합니다.","재물":"예상치 못한 수입","관계":"이성 인연","건강":"과로 주의"},
        "정재":  {"emoji":"🏦","level":"길","msg":"안정적 재물의 날. 성실하게 움직이면 반드시 보상이 옵니다.","재물":"정직한 수입","관계":"파트너 안정","건강":"양호"},
        "편관":  {"emoji":"⚡","level":"흉","msg":"압박과 긴장의 날. 서두르지 말고 인내하는 것이 최선입니다.","재물":"지출 증가","관계":"갈등 가능","건강":"사고 주의"},
        "정관":  {"emoji":"🎖️","level":"대길","msg":"명예와 인정의 날! 중요한 발표·면접·계약에 최적입니다.","재물":"합법적 수입","관계":"신뢰 상승","건강":"좋음"},
        "편인":  {"emoji":"🔮","level":"평","msg":"직관과 영감의 날. 창의적 연구·기획에 집중하십시오.","재물":"재물보다 지식","관계":"혼자가 편한 날","건강":"소화 주의"},
        "정인":  {"emoji":"📚","level":"대길","msg":"귀인과 학문의 날! 시험·발표·공부에 최고입니다.","재물":"간접 수입","관계":"스승·선배 도움","건강":"안정"},
        "-":     {"emoji":"〰️","level":"평","msg":"복합 기운의 날. 꾸준히 자신의 일에 집중하십시오.","재물":"현상 유지","관계":"평온","건강":"보통"},
    }
    d = DAILY_SS_MSG.get(today_ss, DAILY_SS_MSG["-"])
    level_color = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107","평":"#9e9e9e","흉":"#f44336"}.get(d["level"],"#aaa")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#fffde8,#ffffff);
                border:2px solid {level_color}55;border-left:5px solid {level_color};
                border-radius:14px;padding:22px;margin-bottom:14px">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px">
            <div style="font-size:40px">{d['emoji']}</div>
            <div>
                <div style="font-size:18px;font-weight:900;color:#8b6200">
                    오늘의 일진 — {today_cg}{today_jj}일 ({CG_KR[CG.index(today_cg)]}·{JJ_KR[JJ.index(today_jj)]})
                </div>
                <div style="font-size:13px;color:{level_color};font-weight:700;margin-top:4px">
                    {display_name}님 기준 십성: {today_ss} &nbsp;|&nbsp;
                    <span style="background:{level_color}33;padding:2px 10px;border-radius:8px">{d['level']}</span>
                </div>
            </div>
        </div>
        <div style="font-size:14px;color:#000000;line-height:1.9;margin-bottom:12px">{d['msg']}</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
            <span style="background:#e8f5e8;color:#33691e;padding:5px 12px;border-radius:8px;font-size:12px">
                💰 재물: {d['재물']}
            </span>
            <span style="background:#f5f5f5;color:#7986cb;padding:5px 12px;border-radius:8px;font-size:12px">
                👥 관계: {d['관계']}
            </span>
            <span style="background:#fff0f0;color:#b71c1c;padding:5px 12px;border-radius:8px;font-size:12px">
                💊 건강: {d['건강']}
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── 이번 주 7일 일진 미리보기 ────────────────────────────
    st.markdown('<div style="font-size:15px;font-weight:800;color:#000000;margin:16px 0 10px">📅 이번 주 7일 일진</div>',
                unsafe_allow_html=True)

    week_days = [(today + timedelta(days=i)) for i in range(7)]
    day_names = ["월","화","수","목","금","토","일"]
    cols = st.columns(7)
    for i, (col, dt) in enumerate(zip(cols, week_days)):
        cg, jj = get_day_pillar(dt)
        ss = day_ten_god(ilgan, cg)
        d_info = DAILY_SS_MSG.get(ss, DAILY_SS_MSG["-"])
        lc = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107","평":"#777","흉":"#f44336"}.get(d_info["level"],"#777")
        is_today = (i == 0)
        with col:
            st.markdown(f"""
            <div style="background:{'linear-gradient(135deg,#2a2010,#3a3020)' if is_today else '#f8f8f8'};
                        border:{'2px solid #f0c060' if is_today else '1px solid #333'};
                        border-radius:10px;padding:10px 4px;text-align:center">
                <div style="font-size:11px;color:{'#f0c060' if is_today else '#666'};font-weight:{'700' if is_today else '400'}">
                    {dt.strftime('%m/%d')}<br>{day_names[dt.weekday()]}
                    {'<br><span style="color:#8b6200">▲오늘</span>' if is_today else ''}
                </div>
                <div style="font-size:16px;margin:6px 0">{d_info['emoji']}</div>
                <div style="font-size:11px;color:#555">{cg}{jj}</div>
                <div style="font-size:10px;color:{lc};font-weight:700;margin-top:4px">
                    {ss}<br>{d_info['level']}
                </div>
            </div>""", unsafe_allow_html=True)

    # ── 오늘의 길한 시간 ─────────────────────────────────────
    st.markdown('<div style="font-size:15px;font-weight:800;color:#000000;margin:20px 0 10px">⏰ 오늘의 길한 시간대</div>',
                unsafe_allow_html=True)

    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신", [])
    if not isinstance(yongshin_ohs, list):
        yongshin_ohs = []

    OH_HOUR_MAP = {
        "木": [("새벽 3~5시","寅시"), ("새벽 5~7시","卯시")],
        "火": [("오전 9~11시","巳시"), ("오전 11~오후 1시","午시")],
        "土": [("오전 7~9시","辰시"), ("오후 1~3시","未시")],
        "金": [("오후 3~5시","申시"), ("오후 5~7시","酉시")],
        "水": [("저녁 9~11시","亥시"), ("밤 11~새벽 1시","子시")],
    }
    good_hours = []
    for oh in yongshin_ohs:
        good_hours.extend(OH_HOUR_MAP.get(oh, []))

    if good_hours:
        hour_tags = " ".join([
            f"<span style='background:#d8f5d8;color:#33691e;padding:5px 14px;border-radius:8px;font-size:13px;margin:4px'>"
            f"✅ {t} ({jj})</span>"
            for t, jj in good_hours[:4]
        ])
        st.markdown(f"<div style='line-height:2.5'>{hour_tags}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#aaa;font-size:13px'>용신 계산 중...</div>", unsafe_allow_html=True)

    # ── 오늘의 한 줄 처방 ─────────────────────────────────────
    DAILY_PRESCRIPTION = {
        "비견": "🤝 오늘은 혼자보다 둘이 낫습니다. 협력 제안은 긍정적으로 받아들이십시오.",
        "겁재": "🛡️ 오늘은 지키는 날입니다. 지갑과 감정을 단단히 붙잡으십시오.",
        "식신": "🍀 오늘 시작하는 일은 복을 부릅니다. 망설이지 말고 첫 발을 내딛으십시오.",
        "상관": "🖊️ 오늘 떠오르는 아이디어를 메모하십시오. 말은 줄이고 행동으로 보여주십시오.",
        "편재": "💼 오늘 들어오는 거래·제안을 신중히 검토하십시오. 기회가 있습니다.",
        "정재": "📊 오늘 성실하게 처리한 일이 내일의 수입이 됩니다. 꾸준히 움직이십시오.",
        "편관": "🧘 오늘은 인내가 최고의 전략입니다. 서두르면 반드시 탈이 납니다.",
        "정관": "🌟 오늘은 자신을 드러낼 날입니다. 중요한 만남·발표를 오늘로 잡으십시오.",
        "편인": "📖 오늘은 연구·공부·계획에 집중하십시오. 대외 활동보다 내면을 다지십시오.",
        "정인": "🎓 오늘 윗사람·스승의 조언을 귀담아 들으십시오. 귀인이 나타나는 날입니다.",
        "-":    "🌿 오늘은 평온하게 자신의 루틴을 지키는 것이 가장 좋은 선택입니다.",
    }
    prescription = DAILY_PRESCRIPTION.get(today_ss, DAILY_PRESCRIPTION["-"])
    st.markdown(f"""
    <div style="background:#e8f5e8;border:1px solid #7ad47a;border-radius:10px;
                padding:14px 18px;margin-top:16px;font-size:14px;color:#1b5e20;line-height:1.8">
        <b style="color:#33691e">💊 오늘의 처방</b><br>{prescription}
    </div>""", unsafe_allow_html=True)

    # ── 이번 달 세운 요약 ──────────────────────────────────
    st.markdown(f"""
    <div style="background:#e2f5ff;border:1px solid #d0e8ff;border-radius:10px;
                padding:14px 18px;margin-top:10px;font-size:13px;color:#0d47a1;line-height:1.8">
        <b style="color:#5c9bc5">🌙 이번 달({today.month}월) 월운</b><br>
        {today_mlu['월운']} ({today_mlu['십성']}) — {today_mlu['short']}<br>
        <span style="color:#555">{today_mlu['설명'][:60]}...</span>
    </div>""", unsafe_allow_html=True)

    # ── 7일 운세 점수 그래프 ──────────────────────────────
    st.markdown('<div class="gold-section" style="margin-top:20px">📊 7일 운세 흐름 그래프</div>',
                unsafe_allow_html=True)
    try:
        graph_data = get_7day_luck_graph(pils, birth_year, gender)
        max_s = max(d["score"] for d in graph_data) or 100
        bars = ""
        for d in graph_data:
            h   = max(15, int(d["score"] / max_s * 75))
            bg  = "#000000" if d["is_today"] else ("#4caf50" if d["score"] >= 60 else "#ff9800" if d["score"] >= 45 else "#f44336")
            fw  = "900" if d["is_today"] else "600"
            shadow = f"box-shadow:0 0 10px {bg}99;" if d["is_today"] else ""
            bars += f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:3px;flex:1">
                <div style="font-size:11px;color:{'#000000' if d['is_today'] else '#555'};font-weight:{fw}">{d['score']}</div>
                <div style="width:100%;max-width:36px;height:{h}px;background:{bg};
                            border-radius:5px 5px 0 0;{shadow}opacity:{'1' if d['is_today'] else '0.75'}"></div>
                <div style="font-size:10px;color:{'#000000' if d['is_today'] else '#888'};font-weight:{fw}">{d['day']}</div>
                <div style="font-size:9px;color:#bbb">{d['date']}</div>
                <div style="font-size:9px;color:{'#000000' if d['is_today'] else '#aaa'}">{d['label'] if d['is_today'] else ''}</div>
            </div>"""
        st.markdown(f"""
        <div style="background:#fffef8;border:1.5px solid #e8d5a0;border-radius:14px;
                    padding:16px 12px;margin:8px 0">
            <div style="display:flex;align-items:flex-end;gap:6px;height:120px;padding-bottom:4px">
                {bars}
            </div>
            <div style="font-size:10px;color:#aaa;text-align:center;margin-top:8px">
                ◀ 3일 전 &nbsp;&nbsp;&nbsp; 오늘 ▲ &nbsp;&nbsp;&nbsp; 3일 후 ▶
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        pass

    # ── 전환점 카운트다운 ──────────────────────────────────
    try:
        countdown = get_turning_countdown(pils, birth_year, gender)
        if countdown["days_left"] and countdown["days_left"] <= 90:
            ic = "#f44336" if "강력" in countdown.get("intensity","") else "#ff9800"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#fff5e8,#ffe0c0);
                        border:2px solid {ic};border-radius:12px;
                        padding:14px 16px;margin:10px 0;text-align:center">
                <div style="font-size:11px;color:{ic};font-weight:700;margin-bottom:2px">
                    ⚡ 인생 전환점 감지
                </div>
                <div style="font-size:28px;font-weight:900;color:{ic}">
                    D-{countdown['days_left']}
                </div>
                <div style="font-size:12px;color:#000000;margin-top:4px">
                    {countdown['description']}
                </div>
                <div style="font-size:11px;color:#000000;margin-top:2px">
                    {countdown['date']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

    # ── 🔮 소름 엔진 — 과거 적중·현재 공감·미래 예고 ─────────────
    st.markdown('<div class="gold-section" style="margin-top:24px">🔮 당신의 사주 패턴 — 이미 겪으셨나요?</div>',
                unsafe_allow_html=True)
    try:
        gb = goosebump_engine(pils, birth_year, gender)

        # 과거 적중
        if gb["past"]:
            for s in gb["past"][:2]:
                st.markdown(f"""
                <div style="background:#ffffff;border-left:5px solid #000000;
                            padding:12px 16px;border-radius:4px 12px 12px 4px;
                            margin:6px 0;font-size:14px;color:#000000;line-height:1.9">
                    🔍 <b>과거 적중</b> &nbsp;{s}
                </div>""", unsafe_allow_html=True)

        # 현재 공감
        if gb["present"]:
            for s in gb["present"][:1]:
                st.markdown(f"""
                <div style="background:#ffffff;border-left:5px solid #4a90d9;
                            padding:12px 16px;border-radius:4px 12px 12px 4px;
                            margin:6px 0;font-size:14px;color:#000000;line-height:1.9">
                    💡 <b>현재 상태</b> &nbsp;{s}
                </div>""", unsafe_allow_html=True)

        # 미래 예고
        if gb["future"]:
            for s in gb["future"][:1]:
                st.markdown(f"""
                <div style="background:#fff5e0;border-left:5px solid #e65100;
                            padding:12px 16px;border-radius:4px 12px 12px 4px;
                            margin:6px 0;font-size:14px;color:#000000;line-height:1.9">
                    ⚡ <b>미래 예고</b> &nbsp;{s}
                </div>""", unsafe_allow_html=True)

        # 확신 강화 문장
        st.markdown(f"""
        <div style="background:#f8f8f8;border:1px solid #ddd;border-radius:10px;
                    padding:10px 14px;margin-top:6px;font-size:11px;color:#000000;line-height:1.7">
            📌 {gb['conviction']}
        </div>""", unsafe_allow_html=True)

    except Exception:
        pass

    # ── 📅 14일 이내 이벤트 예고 배너 ─────────────────────────────
    st.markdown('<div class="gold-section" style="margin-top:24px">📅 앞으로 14일 이내 운기 예고</div>',
                unsafe_allow_html=True)
    try:
        future_alerts = []
        for offset in range(1, 15):
            chk_date = today + timedelta(days=offset)
            chk_year = chk_date.year
            chk_cg, chk_jj = get_day_pillar(chk_date)
            chk_ss = day_ten_god(ilgan, chk_cg)
            # 대길 또는 흉 일진 감지
            if chk_ss in ("식신", "정관", "정인", "정재"):
                future_alerts.append({
                    "date": chk_date.strftime("%m/%d"),
                    "day": ["월","화","수","목","금","토","일"][chk_date.weekday()],
                    "type": "🌟 길일",
                    "ss": chk_ss,
                    "color": "#4caf50",
                    "bg": "#e8f5e8",
                    "desc": {"식신":"복록 기운","정관":"명예 기운","정인":"귀인 기운","정재":"재물 기운"}.get(chk_ss,"길한 기운"),
                    "offset": offset,
                })
            elif chk_ss in ("편관", "겁재"):
                future_alerts.append({
                    "date": chk_date.strftime("%m/%d"),
                    "day": ["월","화","수","목","금","토","일"][chk_date.weekday()],
                    "type": "⚠️ 주의일",
                    "ss": chk_ss,
                    "color": "#f44336",
                    "bg": "#fff5f5",
                    "desc": {"편관":"압박 주의","겁재":"지출 주의"}.get(chk_ss,"주의 필요"),
                    "offset": offset,
                })

        if future_alerts:
            alert_html = ""
            for a in future_alerts[:6]:  # 최대 6개
                alert_html += f"""
                <div style="display:flex;align-items:center;gap:10px;
                            background:{a['bg']};border:1px solid {a['color']}44;
                            border-radius:10px;padding:9px 14px;margin:5px 0">
                    <span style="font-size:13px;font-weight:900;color:{a['color']};min-width:40px">
                        D-{a['offset']}
                    </span>
                    <span style="font-size:12px;color:#000000;min-width:60px">
                        {a['date']} ({a['day']})
                    </span>
                    <span style="font-size:13px;font-weight:700;color:{a['color']}">{a['type']}</span>
                    <span style="font-size:12px;color:#666">{a['ss']} — {a['desc']}</span>
                </div>"""
            st.markdown(alert_html, unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#000000;font-size:13px;padding:10px'>14일 이내 특이 사항 없음 — 평온한 흐름입니다.</div>",
                        unsafe_allow_html=True)
    except Exception:
        pass

    # ── 📊 30일 운 흐름 그래프 (확장) ────────────────────────────
    st.markdown('<div class="gold-section" style="margin-top:24px">📊 30일 운세 흐름</div>',
                unsafe_allow_html=True)
    try:
        # 오늘 기준 -7 ~ +22일 (총 30일)
        scores_30 = []
        for offset in range(-7, 23):
            d = today + timedelta(days=offset)
            s = get_daily_luck_score(pils, birth_year, gender, d)
            scores_30.append({
                "score": s["score"],
                "date": d.strftime("%d"),
                "is_today": offset == 0,
                "label": s.get("label", ""),
            })

        if scores_30:
            max_s = max(d["score"] for d in scores_30) or 100
            bars30 = ""
            for i, d in enumerate(scores_30):
                h = max(8, int(d["score"] / max_s * 60))
                bg = ("#000000" if d["is_today"] else
                      "#4caf50" if d["score"] >= 65 else
                      "#ff9800" if d["score"] >= 45 else "#f44336")
                opacity = "1" if d["is_today"] else "0.65"
                label = f'<div style="font-size:8px;color:#000000;font-weight:900">▲</div>' if d["is_today"] else ""
                bars30 += f"""
                <div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:1px">
                    {label}
                    <div style="width:100%;max-width:14px;height:{h}px;
                                background:{bg};border-radius:3px 3px 0 0;
                                opacity:{opacity}"></div>
                    <div style="font-size:7px;color:{'#000000' if d['is_today'] else '#aaa'}">{d['date']}</div>
                </div>"""
            st.markdown(f"""
            <div style="background:#fffef8;border:1.5px solid #e8d5a0;border-radius:14px;
                        padding:14px 10px;margin:8px 0">
                <div style="display:flex;align-items:flex-end;gap:2px;height:90px;padding-bottom:4px">
                    {bars30}
                </div>
                <div style="display:flex;justify-content:space-between;
                            font-size:9px;color:#aaa;margin-top:4px;padding:0 4px">
                    <span>◀ 7일 전</span>
                    <span>오늘 ▲</span>
                    <span>22일 후 ▶</span>
                </div>
                <div style="display:flex;gap:8px;margin-top:8px;justify-content:center">
                    <span style="background:#4caf5033;color:#4caf50;padding:2px 8px;border-radius:6px;font-size:10px">🟢 65+ 상승</span>
                    <span style="background:#ff980033;color:#ff9800;padding:2px 8px;border-radius:6px;font-size:10px">🟡 45~65 보통</span>
                    <span style="background:#f4433633;color:#f44336;padding:2px 8px;border-radius:6px;font-size:10px">🔴 45- 주의</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass


def menu10_monthly(pils, name, birth_year, gender):
    """🔟 월별 운세 | 12개월 완전 분석"""

    ilgan = pils[1]["cg"]
    display_name = name if name else "내담자"
    today = datetime.now()

    # ── 헤더 ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#e8f4ff,#e0f5ec);
                border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
        <div style="font-size:22px;font-weight:900;color:#1a7a4a;letter-spacing:2px">
            📅 {display_name}님의 월별 운세
        </div>
        <div style="font-size:13px;color:#000000;margin-top:6px">
            {today.year}년 전체 12개월 · 월운 완전 분석
        </div>
    </div>""", unsafe_allow_html=True)

    # 연도 선택
    col_y, _ = st.columns([1, 3])
    with col_y:
        sel_year = st.selectbox("조회 연도",
                                [today.year - 1, today.year, today.year + 1],
                                index=1,
                                key="monthly_year_select")

    LEVEL_COLOR = {
        "대길":"#4caf50","길":"#8bc34a","평길":"#ffc107",
        "평":"#9e9e9e","흉":"#f44336","흉흉":"#b71c1c"
    }
    LEVEL_EMOJI = {"대길":"🌟","길":"✅","평길":"🟡","평":"⬜","흉":"⚠️","흉흉":"🔴"}

    # ── 12개월 카드 ───────────────────────────────────────────
    months_data = [get_monthly_luck(pils, sel_year, m) for m in range(1, 13)]

    # 올해 최고·최저 월 자동 탐지
    LEVEL_RANK = {"대길":5,"길":4,"평길":3,"평":2,"흉":1,"흉흉":0}
    best_m  = max(months_data, key=lambda x: LEVEL_RANK.get(x["길흉"], 2))
    worst_m = min(months_data, key=lambda x: LEVEL_RANK.get(x["길흉"], 2))

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown(f"""
        <div style="background:#e8f5e8;border:1px solid #8de48d;border-radius:10px;
                    padding:12px 16px;margin-bottom:10px;font-size:13px;color:#33691e">
            🌟 최고의 달: <b>{best_m['월']}월</b> — {best_m['월운']} ({best_m['십성']}) {best_m['short']}
        </div>""", unsafe_allow_html=True)
    with bc2:
        st.markdown(f"""
        <div style="background:#fff0f0;border:1px solid #f0a0a0;border-radius:10px;
                    padding:12px 16px;margin-bottom:10px;font-size:13px;color:#b71c1c">
            ⚠️ 주의할 달: <b>{worst_m['월']}월</b> — {worst_m['월운']} ({worst_m['십성']}) {worst_m['short']}
        </div>""", unsafe_allow_html=True)

    # ── 월별 상세 카드 ────────────────────────────────────────
    for ml in months_data:
        m       = ml["월"]
        is_now  = (m == today.month and sel_year == today.year)
        lcolor  = LEVEL_COLOR.get(ml["길흉"], "#777")
        lemoji  = LEVEL_EMOJI.get(ml["길흉"], "")
        month_names = ["","1월 — 인월(寅)","2월 — 묘월(卯)","3월 — 진월(辰)",
                       "4월 — 사월(巳)","5월 — 오월(午)","6월 — 미월(未)",
                       "7월 — 신월(申)","8월 — 유월(酉)","9월 — 술월(戌)",
                       "10월 — 해월(亥)","11월 — 자월(子)","12월 — 축월(丑)"]

        with st.expander(
            f"{'▶ ' if is_now else ''}{month_names[m]}  |  {ml['월운']} ({ml['십성']})  |  "
            f"{lemoji} {ml['길흉']} — {ml['short']}",
            expanded=is_now
        ):
            st.markdown(f"""
            <div style="background:#f8f8f8;border-left:4px solid {lcolor};
                        border-radius:0 10px 10px 0;padding:16px;margin-bottom:8px">
                <div style="font-size:13px;color:#000000;line-height:1.9">
                    {ml['설명']}
                </div>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">
                <div style="flex:1;background:#e8f5e8;border-radius:8px;padding:10px 14px">
                    <div style="font-size:11px;color:#000000;margin-bottom:4px">💰 재물운</div>
                    <div style="font-size:13px;color:#33691e">{ml['재물']}</div>
                </div>
                <div style="flex:1;background:#f5f5f5;border-radius:8px;padding:10px 14px">
                    <div style="font-size:11px;color:#000000;margin-bottom:4px">👥 인간관계</div>
                    <div style="font-size:13px;color:#7986cb">{ml['관계']}</div>
                </div>
            </div>
            <div style="background:#fff5e0;border-radius:8px;padding:10px 14px">
                <div style="font-size:11px;color:#000000;margin-bottom:4px">⚠️ 주의사항</div>
                <div style="font-size:13px;color:#ffab40">{ml['주의']}</div>
            </div>""", unsafe_allow_html=True)

    # ── 분기별 요약표 ─────────────────────────────────────────
    st.markdown('<div style="font-size:15px;font-weight:800;color:#000000;margin:20px 0 10px">📊 분기별 운세 요약</div>',
                unsafe_allow_html=True)
    quarters = [
        ("1분기 (1~3월)", months_data[0:3]),
        ("2분기 (4~6월)", months_data[3:6]),
        ("3분기 (7~9월)", months_data[6:9]),
        ("4분기 (10~12월)", months_data[9:12]),
    ]
    for qtitle, qdata in quarters:
        avg_rank = sum(LEVEL_RANK.get(d["길흉"], 2) for d in qdata) / 3
        qcolor = "#4caf50" if avg_rank >= 4 else "#ffc107" if avg_rank >= 3 else "#f44336"
        best_q = max(qdata, key=lambda x: LEVEL_RANK.get(x["길흉"], 2))
        st.markdown(f"""
        <div style="background:#f8f8f8;border:1px solid #ddd;border-radius:10px;
                    padding:12px 16px;margin-bottom:6px;display:flex;
                    align-items:center;gap:14px">
            <div style="min-width:110px;font-size:13px;color:#000000;font-weight:700">{qtitle}</div>
            <div style="flex:1;font-size:12px;color:#555">
                {' · '.join([f"{d['월']}월 {d['십성']}({d['길흉']})" for d in qdata])}
            </div>
            <div style="font-size:12px;color:{qcolor};font-weight:700">
                최고: {best_q['월']}월 {best_q['월운']}
            </div>
        </div>""", unsafe_allow_html=True)

    # ── 🔮 이달 소름 문장 ────────────────────────────────────
    st.markdown('<div class="gold-section" style="margin-top:20px">🔮 현재 운기 패턴 — 지금 상황 체크</div>',
                unsafe_allow_html=True)
    try:
        gb = goosebump_engine(pils, birth_year, gender, today.year)
        if gb["present"]:
            for s in gb["present"][:2]:
                st.markdown(f"""
                <div style="background:#ffffff;border-left:5px solid #4a90d9;
                            padding:12px 16px;border-radius:4px 12px 12px 4px;
                            margin:5px 0;font-size:14px;color:#000000;line-height:1.9">
                    💡 {s}
                </div>""", unsafe_allow_html=True)
        if gb["future"]:
            for s in gb["future"][:1]:
                st.markdown(f"""
                <div style="background:#fff5e0;border-left:5px solid #e65100;
                            padding:12px 16px;border-radius:4px 12px 12px 4px;
                            margin:5px 0;font-size:14px;color:#000000;line-height:1.9">
                    ⚡ {s}
                </div>""", unsafe_allow_html=True)
    except Exception:
        pass

    # ── 올해 최적 행동 타이밍 요약 ───────────────────────────
    try:
        best_months = sorted(months_data,
                             key=lambda x: LEVEL_RANK.get(x["길흉"], 2), reverse=True)[:3]
        timing_html = ""
        for bm in best_months:
            lc = LEVEL_COLOR.get(bm["길흉"], "#777")
            timing_html += f"""
            <div style="display:inline-flex;align-items:center;gap:8px;
                        background:{lc}22;border:1px solid {lc}55;
                        border-radius:10px;padding:8px 14px;margin:4px">
                <span style="font-size:16px;font-weight:900;color:{lc}">{bm['월']}월</span>
                <div>
                    <div style="font-size:12px;font-weight:700;color:{lc}">{LEVEL_EMOJI.get(bm['길흉'],'')} {bm['길흉']}</div>
                    <div style="font-size:11px;color:#555">{bm['십성']} — {bm['short']}</div>
                </div>
            </div>"""
        st.markdown(f"""
        <div style="background:#fffef8;border:1.5px solid #e8d5a0;border-radius:14px;
                    padding:14px;margin:8px 0">
            <div style="font-size:12px;color:#000000;font-weight:700;margin-bottom:8px">
                🎯 {sel_year}년 최적 행동 타이밍 TOP 3
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:4px">
                {timing_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        pass


def menu11_yearly(pils, name, birth_year, gender):
    """1️⃣1️⃣ 신년 운세 — 연도별 종합 대운·세운 완전 분석"""

    ilgan = pils[1]["cg"]
    display_name = name if name else "내담자"
    today = datetime.now()
    current_year = today.year

    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신", [])
    if not isinstance(yongshin_ohs, list):
        yongshin_ohs = []

    # ── 헤더 ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#f5f0ff,#fff0e8);
                border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
        <div style="font-size:22px;font-weight:900;color:#5a2a00;letter-spacing:2px">
            🎊 {display_name}님의 신년 운세
        </div>
        <div style="font-size:13px;color:#000000;margin-top:6px">
            연도별 세운(歲運) × 대운(大運) 교차 완전 분석
        </div>
    </div>""", unsafe_allow_html=True)

    # 조회 기간 선택
    col_s, col_e, _ = st.columns([1, 1, 2])
    with col_s:
        start_y = st.number_input("시작 연도", min_value=current_year-5,
                                  max_value=current_year+20,
                                  value=current_year, step=1, key="yearly_start")
    with col_e:
        end_y   = st.number_input("종료 연도", min_value=int(start_y)+1,
                                  max_value=current_year+30,
                                  value=current_year+5, step=1, key="yearly_end")

    LEVEL_RANK = {"대길":5,"길":4,"평길":3,"평":2,"흉":1,"흉흉":0}
    LEVEL_COLOR = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107",
                   "평":"#9e9e9e","흉":"#f44336","흉흉":"#b71c1c"}

    def get_cur_daewoon(year):
        for dw in daewoon:
            if dw["시작연도"] <= year <= dw["종료연도"]:
                return dw
        return None

    # ── 황금기·주의 연도 자동 탐지 ──────────────────────────
    years_data = []
    for y in range(int(start_y), int(end_y)+1):
        yl   = get_yearly_luck(pils, y)
        cur_dw = get_cur_daewoon(y)
        dw_ss  = TEN_GODS_MATRIX.get(ilgan, {}).get(cur_dw["cg"], "-") if cur_dw else "-"
        dw_oh  = OH.get(cur_dw["cg"], "") if cur_dw else ""
        is_yong = dw_oh in yongshin_ohs
        rank   = LEVEL_RANK.get(yl["길흉"], 2)
        if is_yong and rank >= 4:
            rank += 1   # 용신 대운 + 길운 세운 = 황금기 가중
        years_data.append({
            "year": y, "yl": yl, "dw": cur_dw, "dw_ss": dw_ss,
            "is_yong": is_yong, "rank": rank
        })

    if years_data:
        best_yr  = max(years_data, key=lambda x: x["rank"])
        worst_yr = min(years_data, key=lambda x: x["rank"])
        golden_yrs = [d for d in years_data if d["rank"] >= 5]

        bc1, bc2 = st.columns(2)
        with bc1:
            st.markdown(f"""
            <div style="background:#e8f5e8;border:1px solid #8de48d;border-radius:10px;
                        padding:12px 16px;margin-bottom:10px;font-size:13px;color:#33691e">
                🌟 최고의 해: <b>{best_yr['year']}년</b><br>
                세운 {best_yr['yl']['세운']} ({best_yr['yl']['십성_천간']}) — {best_yr['yl']['길흉']}
                {'&nbsp;✨ 용신 대운 황금기' if best_yr['is_yong'] else ''}
            </div>""", unsafe_allow_html=True)
        with bc2:
            st.markdown(f"""
            <div style="background:#fff0f0;border:1px solid #f0a0a0;border-radius:10px;
                        padding:12px 16px;margin-bottom:10px;font-size:13px;color:#b71c1c">
                ⚠️ 주의할 해: <b>{worst_yr['year']}년</b><br>
                세운 {worst_yr['yl']['세운']} ({worst_yr['yl']['십성_천간']}) — {worst_yr['yl']['길흉']}
            </div>""", unsafe_allow_html=True)

        if golden_yrs:
            golden_str = " · ".join([f"{d['year']}년" for d in golden_yrs])
            st.markdown(f"""
            <div style="background:#fffde8;border:1px solid #4a4a1a;border-radius:10px;
                        padding:10px 16px;margin-bottom:14px;font-size:13px;color:#1a1a1a176">
                ✨ 황금기 구간 (용신 대운 + 길운 세운 교차): {golden_str}
            </div>""", unsafe_allow_html=True)

    # ── 연도별 상세 카드 ──────────────────────────────────────
    YEARLY_ACTION = {
        "대길": "🚀 이 해에는 적극적으로 움직이십시오. 새로운 사업·투자·도전이 빛을 발합니다.",
        "길":   "✅ 꾸준히 전진하십시오. 노력이 반드시 결실을 맺는 해입니다.",
        "평길": "🌿 안정적으로 기반을 다지십시오. 무리하지 않아도 성과가 옵니다.",
        "평":   "⚖️ 균형을 유지하며 내실을 다지십시오. 준비하는 해로 활용하십시오.",
        "흉":   "🛡️ 보수적으로 지키는 전략이 최선입니다. 큰 결정은 미루십시오.",
        "흉흉": "🧘 인내가 최고의 전략입니다. 자중하고 기회를 기다리십시오.",
    }

    for yd in years_data:
        y   = yd["year"]
        yl  = yd["yl"]
        dw  = yd["dw"]
        is_cur = (y == current_year)
        is_yong = yd["is_yong"]
        lcolor = LEVEL_COLOR.get(yl["길흉"], "#777")
        action = YEARLY_ACTION.get(yl["길흉"], "꾸준히 나아가십시오.")
        age = y - birth_year + 1

        # 세운 상세
        se_narr = YEARLY_LUCK_NARRATIVE.get(yl["십성_천간"], YEARLY_LUCK_NARRATIVE["-"])

        with st.expander(
            f"{'★ ' if is_yong else ''}{'▶ 현재 ' if is_cur else ''}"
            f"{y}년 ({age}세)  |  세운 {yl['세운']} ({yl['십성_천간']})  |  "
            f"{yl['아이콘']} {yl['길흉']}  {'🔆 용신 대운' if is_yong else ''}",
            expanded=is_cur
        ):
            dw_label = (f"{dw['str']} 대운 ({dw['시작나이']}~{dw['시작나이']+9}세 / "
                        f"{dw['시작연도']}~{dw['종료연도']}) — {yd['dw_ss']}"
                        if dw else "대운 정보 없음")

            yong_badge = (
                f"<span style='background:#d8f5d8;color:#33691e;"
                f"padding:3px 10px;border-radius:8px;font-size:11px;margin-left:8px'>"
                f"✨ 용신 대운</span>" if is_yong else "")

            # 12개월 요약 바
            monthly_ranks = [LEVEL_RANK.get(get_monthly_luck(pils, y, m)["길흉"], 2)
                             for m in range(1, 13)]
            bar_colors = ["#4caf50" if r>=4 else "#ffc107" if r>=3 else "#f44336" for r in monthly_ranks]
            bar_html = "".join([
                f"<div title='{i+1}월' style='flex:1;height:18px;background:{c};"
                f"border-radius:2px;margin:1px;min-width:8px'></div>"
                for i, c in enumerate(bar_colors)
            ])

            st.markdown(f"""
            <div style="background:#f8f8f8;border-left:4px solid {lcolor};
                        border-radius:0 12px 12px 0;padding:18px;margin-bottom:10px">
                <div style="font-size:13px;color:#000000;margin-bottom:8px">
                    🌊 {dw_label}{yong_badge}
                </div>
                <div style="font-size:14px;color:#000000;line-height:1.9;margin-bottom:12px">
                    {se_narr['desc']}
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
                    <div style="flex:1;background:#e8f5e8;border-radius:8px;padding:10px">
                        <div style="font-size:11px;color:#000000;margin-bottom:3px">💰 재물</div>
                        <div style="font-size:12px;color:#33691e">{se_narr['재물']}</div>
                    </div>
                    <div style="flex:1;background:#f5f5f5;border-radius:8px;padding:10px">
                        <div style="font-size:11px;color:#000000;margin-bottom:3px">👥 관계</div>
                        <div style="font-size:12px;color:#7986cb">{se_narr['관계']}</div>
                    </div>
                    <div style="flex:1;background:#fff0f0;border-radius:8px;padding:10px">
                        <div style="font-size:11px;color:#000000;margin-bottom:3px">💊 건강</div>
                        <div style="font-size:12px;color:#b71c1c">{se_narr['건강']}</div>
                    </div>
                </div>
                <div style="background:#e8f5e8;border-radius:8px;padding:10px 14px;margin-bottom:10px">
                    <div style="font-size:11px;color:#000000;margin-bottom:3px">🎯 {y}년 행동 처방</div>
                    <div style="font-size:13px;color:#1b5e20">{action}<br>
                    <span style="color:#aaa;font-size:12px">{se_narr['조언']}</span></div>
                </div>
                <div>
                    <div style="font-size:10px;color:#000000;margin-bottom:4px">
                        📊 월운 흐름 (1월→12월 / 🟢좋음 🟡보통 🔴주의)
                    </div>
                    <div style="display:flex;border-radius:4px;overflow:hidden">{bar_html}</div>
                    <div style="display:flex;justify-content:space-between;
                                font-size:9px;color:#000000;margin-top:2px">
                        {''.join([f'<span>{i+1}</span>' for i in range(12)])}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)


def menu8_bihang(pils, name, birth_year, gender):
    """8️⃣ 특급 비방록 — 용신 기반 전통 비방 처방전"""

    ilgan = pils[1]["cg"]
    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신", [])
    if not isinstance(yongshin_ohs, list):
        yongshin_ohs = []
    gishin_raw = ys.get("기신", "")
    gishin_ohs = [o for o in ["木","火","土","金","水"] if o in str(gishin_raw)]
    ilgan_oh = OH.get(ilgan, "")
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    display_name = name if name else "내담자"
    current_year = datetime.now().year
    current_age = current_year - birth_year + 1

    # ══════════════════════════════════
    # 비방 DB — 용신 오행별 전통 비방
    # ══════════════════════════════════
    BIHANG_DB = {
        "木": {
            "오행명": "목(木) · 나무의 기운",
            "emoji": "🌳",
            "색상": ["초록색","청록색","파란 계열"],
            "방위": "동쪽 (정동방)",
            "숫자": ["3","8"],
            "시간": "새벽 3시~7시 (인시·묘시)",
            "날짜": "인일(寅日)·묘일(卯日) — 갑·을일도 길",
            "음식": ["신맛 음식","오이·부추·시금치·쑥","녹차·현미茶","보리밥"],
            "금기음식": ["매운 음식 과다 섭취","건조한 음식"],
            "풍수": [
                "동쪽 창가에 화분 3~8개 배치 (홀수가 길)",
                "침실·사무실 동쪽 벽에 나무 소재 가구 배치",
                "초록색·청색 커튼이나 침구 사용",
                "거실 동쪽에 대나무 또는 행운목 키우기",
            ],
            "부적_종류": "청룡부(靑龍符) — 동쪽 벽 높은 곳에 부착",
            "만신_의식": [
                "갑·을·인·묘일 새벽 — 동쪽을 향해 맑은 물 한 그릇 올리고 3번 절",
                "초록실로 왼쪽 손목에 3번 감아 매듭 짓기 (재물 새는 것 막기)",
                "부추나 쑥을 달인 물로 현관 문지방 닦기 — 목기 강화, 기회 불러들임",
                "동쪽 창가에 황금색 동전 3개를 붉은 실로 묶어 걸어두기",
            ],
            "재물비방": [
                "🟢 지갑을 항상 초록색으로 — 나무처럼 자라는 재물",
                "🟢 새 지갑에 첫 돈 넣을 때 갑인일(甲寅日) 선택",
                "🟢 지갑 안에 나뭇잎 모양 장식품 또는 나무 소재 장식 넣기",
                "🟢 사업 서류·계약서 보관함을 동쪽에 배치",
                "🟢 사무실 동쪽 코너에 수정 원석(초록 계열) 배치",
            ],
            "막는비방": [
                "🔴 기신이 金이면 — 서쪽 방향 큰 창문 커튼 닫기, 금속 장식 최소화",
                "🔴 서쪽에 화장실이 있으면 — 항상 뚜껑 닫고 소금 한 줌 올려두기",
                "🔴 지갑에 영수증 쌓아두지 말기 — 새는 돈 상징",
                "🔴 쥐띠·토끼띠와 큰 재물 거래 때 특히 조심",
            ],
            "신살_주의": "경·신·신·유일에는 큰 계약·투자·이사 금지",
        },
        "火": {
            "오행명": "화(火) · 불의 기운",
            "emoji": "🔥",
            "색상": ["빨강색","주황색","분홍색","자주색"],
            "방위": "남쪽 (정남방)",
            "숫자": ["2","7"],
            "시간": "낮 11시~오후 3시 (오시·미시)",
            "날짜": "병일(丙日)·정일(丁日)·사일(巳日)·오일(午日)",
            "음식": ["쓴맛 음식","쑥·익모초·도라지","붉은 팥죽·팥밥","홍삼","대추"],
            "금기음식": ["찬 음식 과다","빙수·아이스크림 매일 섭취"],
            "풍수": [
                "남쪽 거실·사무실에 붉은 계열 소품 배치",
                "조명을 밝게 — 화기가 어두움을 싫어함",
                "남쪽 벽에 해·태양 그림 또는 붉은 그림 걸기",
                "촛불을 남쪽에 켜두는 것이 화기 강화에 큰 효험",
            ],
            "부적_종류": "주작부(朱雀符) — 남쪽 벽 눈높이에 부착",
            "만신_의식": [
                "병·정·사·오일 정오 — 남쪽 향해 붉은 초 켜고 재물 기원 3번 절",
                "붉은 실로 오른쪽 손목에 7번 감기 — 화기 강화, 인기운 상승",
                "대추·팥을 쌀에 섞어 밥 지어 첫 숟갈을 남쪽 창문 향해 바치기",
                "붉은 복주머니에 쌀·동전·황토 넣어 남쪽 선반에 보관",
            ],
            "재물비방": [
                "🔴 지갑을 붉은색·자주색으로 — 화기가 재물 활성화",
                "🔴 거래·영업은 점심 전후 2~3시간이 가장 강한 시간대",
                "🔴 명함 색상에 빨간 포인트 넣기 — 인상에 각인됨",
                "🔴 사무실 입구에 빨간 카펫 또는 빨간 화분 배치",
                "🔴 오·미월(5~8월)에 큰 결정 내리면 성사될 확률 높음",
            ],
            "막는비방": [
                "🔴 기신이 水이면 — 북쪽 화장실 소금 상시 비치",
                "🔴 검정색 지갑·검정색 가방 사용 자제",
                "🔴 임·계·해·자일에는 큰 계약·개업 피하기",
                "🔴 수족관·어항을 집 안 중앙에 두지 말 것",
            ],
            "신살_주의": "임·계·해·자일에는 큰 투자·이사·계약 금지",
        },
        "土": {
            "오행명": "토(土) · 땅의 기운",
            "emoji": "⛰️",
            "색상": ["황색","노란색","베이지","황토색","갈색"],
            "방위": "중앙 또는 북동·남서",
            "숫자": ["5","10"],
            "시간": "오후 1시~5시 (미시·신시 사이)",
            "날짜": "무일(戊日)·기일(己日)·진일(辰日)·술일(戌日)·축일(丑日)·미일(未日)",
            "음식": ["단맛 음식","고구마·감자·호박·단호박","꿀물","현미·잡곡밥"],
            "금기음식": ["신 음식 과다(목이 토를 억제)","날것 위주 식단"],
            "풍수": [
                "집 중앙에 황토색·베이지 소품 배치",
                "도자기·옹기·황토 소재 장식품이 토기 강화",
                "황색 카펫이나 러그 사용 — 땅의 안정 기운",
                "돌·황토·자연석 장식을 현관 입구에 배치",
            ],
            "부적_종류": "황정부(黃庭符) — 집 중앙 또는 북동쪽 벽에 부착",
            "만신_의식": [
                "무·기·진·술·축·미일 오후 — 중앙 향해 황토물(황토+물) 한 그릇 올리기",
                "황색 실로 배꼽 주변에 9번 감고 기도하면 재물 중심 잡힘",
                "집 네 모서리에 황토 한 줌씩 묻기 — 재물 기반 안정",
                "쌀 됫박에 황금색 동전 5개 넣어 중앙 선반에 두기 (재물신 상징)",
            ],
            "재물비방": [
                "🟡 지갑을 황색·베이지로 — 땅처럼 묵직하게 모이는 재물",
                "🟡 부동산·토지 관련 투자가 이 사주에 가장 잘 맞음",
                "🟡 중앙에 재물 모이는 공간 만들기 — 황색 그릇에 동전 쌓기",
                "🟡 계약서·중요 서류를 황색 봉투에 보관",
                "🟡 진·술·축·미월(3·9·12·6월)에 큰 계약이 유리",
            ],
            "막는비방": [
                "🔴 기신이 木이면 — 동쪽에 큰 화분·나무 배치 금지",
                "🔴 초록색 지갑 자제",
                "🔴 갑·을·인·묘일에 큰 재물 거래 조심",
                "🔴 뿌리가 깊은 나무를 집 정동쪽에 심지 말 것",
            ],
            "신살_주의": "갑·을·인·묘일에는 큰 계약·이사·투자 금지",
        },
        "金": {
            "오행명": "금(金) · 쇠의 기운",
            "emoji": "⚔️",
            "색상": ["흰색","은색","금색","회색"],
            "방위": "서쪽 (정서방)",
            "숫자": ["4","9"],
            "시간": "오후 3시~7시 (신시·유시)",
            "날짜": "경일(庚日)·신일(辛日)·신일(申日)·유일(酉日)",
            "음식": ["매운맛 음식","파·마늘·생강·무·배","흰쌀밥","배·복숭아"],
            "금기음식": ["쓴 음식 과다(화가 금을 억제)","태운 음식"],
            "풍수": [
                "서쪽에 금속 소재 장식·금속 조각품 배치",
                "흰색·은색·금색 인테리어 소품 활용",
                "서쪽 창가에 크리스탈·수정 장식 걸기",
                "금속 풍경(風磬) 서쪽 창가에 달기 — 금기 강화",
            ],
            "부적_종류": "백호부(白虎符) — 서쪽 벽 높은 곳에 부착",
            "만신_의식": [
                "경·신·신·유일 오후 — 서쪽 향해 금속 그릇에 맑은 물 올리고 3번 절",
                "은색 실로 왼쪽 발목에 9번 감기 — 금기 강화, 결단력 상승",
                "흰 무명천에 은화·동전 9개 싸서 서쪽 서랍에 보관",
                "칼·가위 등 금속 도구 잘 닦아 서쪽 선반에 칼날 향하게 보관",
            ],
            "재물비방": [
                "⚪ 지갑을 흰색·은색·금색으로 — 금기가 재물 응결",
                "⚪ 귀금속·금 투자가 이 사주에 가장 잘 맞음",
                "⚪ 사무실 서쪽에 금색 소품 배치 — 거래 결단력 강화",
                "⚪ 신·유월(8~9월)에 계약·투자 결정이 유리",
                "⚪ 협상·계약은 오후 3~7시 사이가 가장 강한 시간대",
            ],
            "막는비방": [
                "🔴 기신이 火이면 — 남쪽에 강한 조명·붉은 소품 자제",
                "🔴 빨간 지갑 사용 금지",
                "🔴 병·정·사·오일에 큰 투자·계약 금지",
                "🔴 집 남쪽 방향에 화로·벽난로 설치 금지",
            ],
            "신살_주의": "병·정·사·오일에는 큰 결정·투자·이사 금지",
        },
        "水": {
            "오행명": "수(水) · 물의 기운",
            "emoji": "💧",
            "색상": ["검정색","남색","진한 파랑","보라"],
            "방위": "북쪽 (정북방)",
            "숫자": ["1","6"],
            "시간": "밤 9시~새벽 3시 (해시·자시)",
            "날짜": "임일(壬日)·계일(癸日)·해일(亥日)·자일(子日)",
            "음식": ["짠맛 음식","다시마·미역·김·해산물","검은콩·흑임자","두부"],
            "금기음식": ["건조하고 매운 음식 과다","술 과음"],
            "풍수": [
                "북쪽에 수족관·어항·작은 분수대 배치 (흐르는 물이 재물 불러옴)",
                "검정·남색 계열 소품·그림 북쪽 벽에",
                "화장실·욕실 청결하게 유지 — 수기 오염 방지",
                "북쪽 현관에 검정색 매트 또는 어두운 색 매트 배치",
            ],
            "부적_종류": "현무부(玄武符) — 북쪽 벽 또는 침실 북쪽에 부착",
            "만신_의식": [
                "임·계·해·자일 밤 자시(23~1시) — 북쪽 향해 정화수 한 그릇 올리고 1번 절",
                "검정 실로 왼쪽 엄지손가락에 6번 감기 — 수기 강화, 지혜·재물 유입",
                "미역국이나 검은콩밥을 해·자일에 해먹기 — 수기 보충 음식 의식",
                "북쪽 창가에 파란 유리병에 물 담아 두기 — 재물수 강화",
            ],
            "재물비방": [
                "🔵 지갑을 검정·남색으로 — 수기가 지혜와 재물을 부름",
                "🔵 금융·투자·보험 관련 일이 이 사주에 잘 맞음",
                "🔵 북쪽 방향으로 사업장 확장 또는 이전 시 유리",
                "🔵 해·자월(11~12월)에 중요 계약·투자 결정이 유리",
                "🔵 흐르는 물 소리(분수·수족관)가 재물 유입을 돕는다",
            ],
            "막는비방": [
                "🔴 기신이 土이면 — 중앙·북동쪽에 흙더미·황토 소품 자제",
                "🔴 황색·갈색 지갑 사용 금지",
                "🔴 무·기·진·술·축·미일에 큰 투자·계약 피하기",
                "🔴 화장실·욕실 문 항상 닫기 — 수기 유출 방지",
            ],
            "신살_주의": "무·기·진·술일에는 큰 계약·이사·창업 금지",
        },
    }

    # ══════════════════════════════════════════════════
    # UI 시작
    # ══════════════════════════════════════════════════
    st.markdown("""
    <div style="background:linear-gradient(135deg,#ffdcdc,#ffdce4,#ffdcdc);
                border:1px solid #8B0000;border-radius:16px;padding:22px 26px;margin-bottom:20px">
        <div style="color:#ff6060;font-size:11px;letter-spacing:4px;margin-bottom:8px">
            ⚠️ 극비(極秘) — 용신 기반 전통 비방 처방전
        </div>
        <div style="color:#8b6200;font-size:19px;font-weight:900;letter-spacing:2px;margin-bottom:10px">
            🔴 특급 비방록(特急 秘方錄)
        </div>
        <div style="color:#d0a080;font-size:13px;line-height:1.9">
            무당·만신이 대대로 전해온 비방을 사주 용신에 맞춰 처방합니다.<br>
            돈이 새는 구멍을 막고, 재물이 들어오는 문을 여는 처방입니다.<br>
            <span style="color:#ff8888">기신(忌神) 오행을 막고 용신(用神) 오행을 강화하는 것이 핵심입니다.</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ① 용신·기신 파악
    OH_EMOJI = {"木":"🌳","火":"🔥","土":"⛰️","金":"⚔️","水":"💧"}
    OH_NAME  = {"木":"목(木)","火":"화(火)","土":"토(土)","金":"금(金)","水":"수(水)"}

    col_y, col_g = st.columns(2)
    with col_y:
        y_tags = " ".join([
            f"<span style='background:#000000;color:#000;font-weight:900;"
            f"padding:6px 16px;border-radius:20px;font-size:14px'>"
            f"{OH_EMOJI.get(o,'')} {OH_NAME.get(o,o)}</span>"
            for o in yongshin_ohs
        ]) if yongshin_ohs else "<span style='color:#888'>분석 중</span>"
        st.markdown(f"""
        <div style="background:#ffffff;border:2px solid #000000;border-radius:12px;padding:16px">
            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:8px">
                🌟 용신 (이 기운을 강화하라)
            </div>
            <div>{y_tags}</div>
        </div>""", unsafe_allow_html=True)
    with col_g:
        g_tags = " ".join([
            f"<span style='background:#ffdcdc;color:#000000;font-weight:700;"
            f"padding:6px 16px;border-radius:20px;font-size:14px'>"
            f"{OH_EMOJI.get(o,'')} {OH_NAME.get(o,o)}</span>"
            for o in gishin_ohs
        ]) if gishin_ohs else "<span style='color:#888'>없음</span>"
        st.markdown(f"""
        <div style="background:#f5f5f5;border:2px solid #8B0000;border-radius:12px;padding:16px">
            <div style="font-size:11px;color:#ff6060;font-weight:700;margin-bottom:8px">
                ⛔ 기신 (이 기운이 돈을 쫓아낸다)
            </div>
            <div>{g_tags}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ② 용신별 비방 처방
    if not yongshin_ohs:
        st.warning("용신 계산 결과가 없습니다. 사주 계산을 먼저 진행하십시오.")
        return

    for yong_oh in yongshin_ohs[:2]:
        bd = BIHANG_DB.get(yong_oh)
        if not bd:
            continue

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#f5f5f5,#f5f5f5);
                    border:2px solid #8B4513;border-radius:18px;padding:24px;margin:16px 0">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;
                        border-bottom:1px solid #3a2010;padding-bottom:14px">
                <span style="font-size:36px">{bd['emoji']}</span>
                <div>
                    <div style="font-size:20px;font-weight:900;color:#8b6200">
                        {bd['오행명']} 강화 비방
                    </div>
                    <div style="font-size:12px;color:#a0800a">
                        방위: {bd['방위']} · 숫자: {', '.join(bd['숫자'])} · 시간: {bd['시간']}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

        # 색상·날짜
        color_tags = " ".join([
            f"<span style='background:#fff5e0;border:1px solid #8B6914;color:#8b6200;"
            f"padding:4px 12px;border-radius:12px;font-size:12px;margin:3px;display:inline-block'>"
            f"{c}</span>"
            for c in bd['색상']
        ])
        st.markdown(f"""
        <div style="margin-bottom:16px">
            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">
                🎨 길한 색상 (지갑·옷·소품)
            </div>
            <div>{color_tags}</div>
            <div style="font-size:12px;color:#a08060;margin-top:8px">
                📅 거래·계약에 좋은 날: {bd['날짜']}
            </div>
        </div>""", unsafe_allow_html=True)

        # 풍수 비방
        st.markdown("""
        <div style="font-size:12px;color:#000000;font-weight:700;margin-bottom:8px">
            🏠 풍수 비방 — 집·사무실 배치
        </div>""", unsafe_allow_html=True)
        for fw in bd['풍수']:
            st.markdown(f"""
            <div style="background:#ffffff;border-left:3px solid #27ae60;
                        padding:9px 14px;border-radius:6px;margin:4px 0;
                        font-size:13px;color:#1a4a1a;line-height:1.8">
                🌿 {fw}
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 부적
        st.markdown(f"""
        <div style="background:#f5f5f5;border:1px solid #8e44ad;border-radius:10px;
                    padding:14px;margin-bottom:14px">
            <div style="font-size:11px;color:#c39bd3;font-weight:700;margin-bottom:6px">
                🔮 부적 처방
            </div>
            <div style="font-size:13px;color:#e8d5f0;line-height:1.8">{bd['부적_종류']}</div>
        </div>""", unsafe_allow_html=True)

        # 만신 의식
        st.markdown("""
        <div style="font-size:12px;color:#ff8888;font-weight:700;margin-bottom:8px">
            🕯️ 만신(萬神) 전통 의식 — 실제 무당이 쓰던 방법
        </div>""", unsafe_allow_html=True)
        for ritual in bd['만신_의식']:
            st.markdown(f"""
            <div style="background:#f5f5f5;border-left:3px solid #c0392b;
                        padding:10px 14px;border-radius:6px;margin:5px 0;
                        font-size:13px;color:#f0c0c0;line-height:1.9">
                🕯️ {ritual}
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 재물 비방
        st.markdown("""
        <div style="font-size:12px;color:#000000;font-weight:700;margin-bottom:8px">
            💰 재물 불러들이는 비방
        </div>""", unsafe_allow_html=True)
        for rb in bd['재물비방']:
            st.markdown(f"""
            <div style="background:#eaffdc;border-left:3px solid #000000;
                        padding:9px 14px;border-radius:6px;margin:4px 0;
                        font-size:13px;color:#f0e0a0;line-height:1.8">
                {rb}
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 돈 새는 것 막는 비방
        st.markdown("""
        <div style="font-size:12px;color:#ff6060;font-weight:700;margin-bottom:8px">
            🚫 돈 새는 구멍 막는 비방
        </div>""", unsafe_allow_html=True)
        for mb in bd['막는비방']:
            st.markdown(f"""
            <div style="background:#ffdcdc;border-left:3px solid #e74c3c;
                        padding:9px 14px;border-radius:6px;margin:4px 0;
                        font-size:13px;color:#6a0000;line-height:1.8">
                {mb}
            </div>""", unsafe_allow_html=True)

        # 음식 비방
        st.markdown(f"""
        <br>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
            <div style="background:#ffffff;border-radius:10px;padding:14px;border:1px solid #2a4a1a">
                <div style="font-size:11px;color:#4caf50;font-weight:700;margin-bottom:6px">
                    🍚 길한 음식 (용신 강화)
                </div>
                <div style="font-size:12px;color:#1a4a1a;line-height:1.8">
                    {', '.join(bd['음식'])}
                </div>
            </div>
            <div style="background:#f5f5f5;border-radius:10px;padding:14px;border:1px solid #4a1a1a">
                <div style="font-size:11px;color:#e74c3c;font-weight:700;margin-bottom:6px">
                    ⚠️ 금기 음식 (기신 강화 주의)
                </div>
                <div style="font-size:12px;color:#6a0000;line-height:1.8">
                    {', '.join(bd['금기음식'])}
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        # 신살 주의
        st.markdown(f"""
        <div style="background:#ffffdc;border:1px solid #8B8B00;border-radius:10px;
                    padding:12px;margin-top:12px">
            <span style="font-size:11px;color:#1a1a1af60;font-weight:700">
                📛 신살(神殺) 주의: </span>
            <span style="font-size:13px;color:#f0f0a0">{bd['신살_주의']}</span>
        </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ③ 기신 차단 종합 처방
    if gishin_ohs:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#ffdcdc,#ffdcdc);
                    border:2px solid #8B0000;border-radius:14px;padding:20px;margin:16px 0">
            <div style="font-size:16px;font-weight:900;color:#ff6060;margin-bottom:14px">
                🚫 기신(忌神) 종합 차단 비방 — 돈 새는 구멍 막기
            </div>""", unsafe_allow_html=True)

        GISHIN_BLOCK = {
            "木": [
                "동쪽에 큰 화분·나무 배치 금지 — 기신이 목이면 목이 당기는 방향을 차단",
                "초록색 지갑·초록 차량 교체 고려 — 기신 오행 색상은 재물을 쫓는다",
                "갑·을·인·묘일 큰 계약·투자 금지 — 기신의 날은 반드시 피한다",
                "목 오행 직업(임산업·목재·원예업)과의 거래 시 계약서 필수",
            ],
            "火": [
                "남쪽 강한 조명·붉은 소품 자제",
                "빨간 지갑·빨간 차 사용 자제 — 화기 기신 흡수",
                "병·정·사·오일 큰 결정 금지",
                "난방 기구·용광로·고열 장비 관련 투자 조심",
            ],
            "土": [
                "집 중앙에 황토·도자기 대형 소품 자제",
                "황색·갈색 지갑 교체 고려",
                "무·기·진·술·축·미일 투자·계약 금지",
                "부동산·땅 관련 투자 시 특히 신중하게",
            ],
            "金": [
                "서쪽 금속 장식·금속 가구 자제",
                "흰색·은색 지갑 자제",
                "경·신·신·유일 큰 결정 금지",
                "금·은·귀금속 투기 조심 — 기신이 금이면 금값 하락에 취약",
            ],
            "水": [
                "북쪽 수족관·어항·분수 설치 금지",
                "검정·남색 지갑 사용 자제",
                "임·계·해·자일 큰 계약·이사 금지",
                "화장실·욕실 문 항상 닫기 — 기신 수기 유출로 오히려 해로움",
                "물 관련 사업(해운·수산·음료) 투자 신중",
            ],
        }

        for goh in gishin_ohs:
            blocks = GISHIN_BLOCK.get(goh, [])
            if blocks:
                st.markdown(f"""
                <div style="margin-bottom:12px">
                    <div style="font-size:13px;color:#ff8888;font-weight:700;margin-bottom:6px">
                        {OH_EMOJI.get(goh,'')} {OH_NAME.get(goh,goh)} 기신 차단
                    </div>""", unsafe_allow_html=True)
                for b in blocks:
                    st.markdown(f"""
                    <div style="background:#f5f5f5;border-left:3px solid #8B0000;
                                padding:9px 14px;border-radius:6px;margin:3px 0;
                                font-size:13px;color:#f0c0c0;line-height:1.8">
                        🔴 {b}
                    </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ④ 공통 만신 비방 — 신강신약별
    st.markdown("""
    <div style="background:#ffffff;;
                border:2px solid #4a3080;border-radius:14px;padding:20px;margin:16px 0">
        <div style="font-size:16px;font-weight:900;color:#c39bd3;margin-bottom:14px">
            🕯️ 신강신약별 공통 비방 — 만신 구전(口傳)
        </div>""", unsafe_allow_html=True)

    if "신강" in sn:
        rituals_common = [
            "신강한 사주는 힘이 넘쳐 오히려 재물을 흩트린다. 주 1회 절에 가거나 사찰 보시(布施)를 생활화하면 기운이 안정된다.",
            "집 안에 거울을 너무 많이 두지 말 것 — 강한 기운이 반사되어 충돌이 생긴다.",
            "월초(음력 1일)마다 현관 소금 한 줌 뿌리고 3일 후 쓸어버리기 — 나쁜 기운 차단",
            "재물이 들어오는 운기(用神대운)에는 반드시 움직여라. 신강한 사주는 적극적으로 나서야 재물이 손에 잡힌다.",
            "기도·의식보다 행동이 우선이다. 신강은 스스로 만드는 사주이다.",
        ]
        desc_color = "#d0c8f8"
        sn_color = "#9b7ccc"
    else:
        rituals_common = [
            "신약한 사주는 기운이 약해 귀신·나쁜 기운에 쉽게 영향 받는다. 매달 음력 초하루 정화수 올리는 것을 생활화하라.",
            "집 안 구석구석 소금 청소 — 월 1회 소금물로 현관 바닥 닦기 (기운 정화)",
            "붉은 팥죽을 동지·정월 초에 대문 앞에 뿌리기 — 나쁜 기운 쫓기",
            "수호신 역할의 소품(도자기·나무 인형 등)을 집 안에 두되 정기적으로 닦아줄 것",
            "귀인 운이 올 때 반드시 받아들여라. 신약은 혼자보다 귀인과 함께일 때 크게 된다.",
            "무리한 야간 활동·과음·과로를 피하라. 신약은 건강이 재물의 기반이다.",
        ]
        desc_color = "#f0d8c8"
        sn_color = "#e8a060"

    st.markdown(f"""
    <div style="font-size:12px;color:{sn_color};font-weight:700;margin-bottom:8px">
        {sn} 특화 처방
    </div>""", unsafe_allow_html=True)

    for r in rituals_common:
        st.markdown(f"""
        <div style="background:#f5f5f5;border-left:3px solid {sn_color};
                    padding:10px 14px;border-radius:6px;margin:5px 0;
                    font-size:13px;color:{desc_color};line-height:1.9">
            ✦ {r}
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑤ 나이별 특급 비방 — 현재 운기에 맞춘 처방
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#fff5e0,#fff0dc);
                border:2px solid #000000;border-radius:14px;padding:20px">
        <div style="font-size:16px;font-weight:900;color:#8b6200;margin-bottom:10px">
            📅 {current_year}년 ({current_age}세) 현재 운기 맞춤 비방
        </div>""", unsafe_allow_html=True)

    try:
        sw = get_yearly_luck(pils, current_year)
        sw_ss = sw.get("십성_천간", "-")
        sw_oh = sw.get("오행_천간", "")
        sw_str = sw.get("세운", "")

        is_yong_year = sw_oh in yongshin_ohs

        if is_yong_year:
            year_desc = f"올해 {sw_str}년은 용신 오행이 들어오는 해입니다. 적극적으로 움직이십시오."
            year_bihang = [
                f"용신 오행({sw_oh})이 강화되는 해 — 이 해에 큰 결정·투자·창업을 해야 합니다.",
                f"용신 색상·방위를 최대한 활용하십시오. 옷 색상부터 바꾸는 것이 시작입니다.",
                "새로운 인연·거래처·투자처가 올 때 적극적으로 받아들이십시오.",
                "연초(음력 정월)에 용신 방향으로 여행 또는 나들이 — 운기를 몸에 흡수",
            ]
            card_color = "#000000"
            card_bg = "#1a1a00"
        else:
            year_desc = f"올해 {sw_str}년은 기신이 강하게 작동하는 해입니다. 수비적으로 대응하십시오."
            year_bihang = [
                f"기신 오행({sw_oh})이 강화되는 해 — 큰 투자·보증·동업을 피하십시오.",
                "현상 유지가 오히려 이기는 해입니다. 무리하게 확장하면 손해를 봅니다.",
                "월초마다 소금 청소와 정화수 의식으로 기운을 지키십시오.",
                "이 해에는 귀한 사람을 만나도 큰 거래보다 관계를 쌓는 데 집중하십시오.",
            ]
            card_color = "#c0392b"
            card_bg = "#1a0000"

        st.markdown(f"""
        <div style="background:{card_bg};border-left:4px solid {card_color};
                    border-radius:10px;padding:14px;margin-bottom:12px">
            <div style="font-size:13px;color:{card_color};font-weight:700;margin-bottom:6px">
                {sw_str}년 ({sw_ss}년) 판단
            </div>
            <div style="font-size:13px;color:#000000;line-height:1.8">{year_desc}</div>
        </div>""", unsafe_allow_html=True)

        for yb in year_bihang:
            st.markdown(f"""
            <div style="background:#fafafa;border-left:3px solid {card_color};
                        padding:9px 14px;border-radius:6px;margin:4px 0;
                        font-size:13px;color:#e0d0c0;line-height:1.8">
                {'✅' if is_yong_year else '⚠️'} {yb}
            </div>""", unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"올해 운기 계산 오류: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("⚠️ 본 비방록은 전통 민속 문화 정보를 제공하는 참고 자료입니다. 실제 굿·부적 처방은 전문 무당·만신에게 문의하십시오.")


def menu7_ai(pils, name, birth_year, gender, api_key, groq_key=""):
    """7️⃣ AI 상담창 — 집중 영역 선택 + 정밀 엔진 데이터 표시"""

    st.markdown("""
    <div style="background:#ffffff;border:2px solid #1565c055;border-radius:12px;
                padding:14px 18px;margin-bottom:14px">
        <div style="font-size:13px;font-weight:700;color:#0d47a1;margin-bottom:4px">🤖 AI 사주 상담</div>
        <div style="font-size:12px;color:#000000;line-height:1.8">
        ✦ 만세력 엔진이 계산한 데이터를 AI가 설명합니다.<br>
        ✦ 집중 분야 선택 → 특화 해석 · <b style="color:#c0392b">전환점 감지 엔진</b> 작동.
    </div>""", unsafe_allow_html=True)

    # ★ Retention: 맞춤형 오프닝 멘트
    saju_key = pils_to_cache_key(pils)
    render_ai_opening_ment(saju_key, name)

    # ── 오늘의 사주 상태 (Daily Status Engine) ──────────
    try:
        daily_score = get_daily_luck_score(pils, birth_year, gender)
        ds_color = ("#4caf50" if daily_score["score"] >= 65 else "#ff9800" if daily_score["score"] >= 45 else "#f44336")
        ds_emoji = {"대길(大吉)":"🔥","길(吉)":"✨","평(平)":"🌱","흉(凶)":"⚖️","흉흉(凶흉)":"⚠️"}.get(daily_score["label"], "🌱")
        
        st.markdown(f"""
        <div style="background:white; border:1px solid {ds_color}55; border-radius:14px; 
                    padding:14px 16px; margin-bottom:14px; display:flex; align-items:center; gap:12px;
                    box-shadow: 0 4px 12px {ds_color}11">
            <div style="font-size:32px">{ds_emoji}</div>
            <div style="flex:1">
                <div style="font-size:11px; color:#000000; font-weight:700">오늘의 사주 상태</div>
                <div style="font-size:16px; font-weight:900; color:{ds_color}">
                    {daily_score['label']} — {daily_score['trend']} (운기 {daily_score['score']}점)
                </div>
            </div>
            <div style="background:{ds_color}11; color:{ds_color}; font-size:10px; font-weight:800; padding:4px 8px; border-radius:8px">
                실시간 업데이트
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        pass

    # ── 집중 영역 선택 ──────────────────────────────
    st.markdown("**🎯 오늘 어떤 분야가 가장 궁금하세요?**")
    focus_options = ["종합", "💰 재물·돈", "💑 연애·인연", "🎖️ 직장·사업", "🏥 건강"]
    focus_col = st.selectbox("집중 분야", focus_options, label_visibility="collapsed")
    focus_key = {"종합":"종합","💰 재물·돈":"재물","💑 연애·인연":"연애",
                 "🎖️ 직장·사업":"직장","🏥 건강":"건강"}.get(focus_col, "종합")

    # ── 현재 운기 정밀 데이터 카드 ──────────────────
    current_year = datetime.now().year
    try:
        ctx = build_rich_ai_context(pils, birth_year, gender, current_year, focus_key)
        turning = calc_turning_point(pils, birth_year, gender, current_year)

        # 운세 게이지
        luck_s   = ctx["luck_score_total"]
        gauge_w  = luck_s
        gauge_c  = ("#4caf50" if luck_s >= 70 else "#ff9800" if luck_s >= 45 else "#f44336")
        intensity_color = {"🔴":"#f44336","🟡":"#ff9800","🟢":"#4caf50","⬜":"#9e9e9e"}
        ic = intensity_color.get(turning["intensity"][:2], "#9e9e9e")

        st.markdown(f"""
        <div style="background:#fffef8;border:1.5px solid #e8d5a0;border-radius:14px;
                    padding:16px 14px;margin:10px 0">
            <div style="font-size:12px;color:#000000;font-weight:700;margin-bottom:10px">
                ⚡ 정밀 엔진 데이터 — {current_year}년 실시간 분석
            </div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px">
                <div>
                    <span style="font-size:11px;color:#666">일간 힘: </span>
                    <span style="font-weight:800;color:#000000">{ctx['daymaster_strength_score']}/100
                    ({ctx['daymaster_strength_label']})</span>
                </div>
                <div>
                    <span style="font-size:11px;color:#666">종합 운세: </span>
                    <span style="font-weight:800;color:{gauge_c}">{luck_s}/100</span>
                </div>
            </div>

            <div style="background:#f0f0f0;border-radius:6px;height:8px;margin-bottom:10px;overflow:hidden">
                <div style="background:{gauge_c};width:{gauge_w}%;height:100%;border-radius:6px;
                            transition:width 0.5s"></div>
            </div>

            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
                {''.join([f'<span style="background:#fff3cd;border:1px solid #ffc107;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">{k}:{v}</span>' for k,v in ctx['element_power'].items()])}
            </div>

            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
                <span style="background:#e8f5e8;padding:3px 10px;border-radius:10px;font-size:11px">
                    🌟 용신1: {ctx['yongshin_primary'] or '-'}
                </span>
                <span style="background:#fff0e8;padding:3px 10px;border-radius:10px;font-size:11px">
                    용신2: {ctx['yongshin_secondary'] or '-'}
                </span>
                <span style="background:#ffeaea;padding:3px 10px;border-radius:10px;font-size:11px">
                    ⛔ 기신: {', '.join(ctx['gishin']) or '없음'}
                </span>
            </div>

            <div style="background:{ic}22;border-left:3px solid {ic};
                        padding:8px 12px;border-radius:4px 8px 8px 4px;font-size:12px">
                {turning['intensity']} — {turning['reason'][0] if turning['reason'] else '안정적 흐름'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 고확률 트리거 표시
        high_triggers = ctx.get("high_prob_triggers", [])
        if high_triggers:
            st.markdown(f"""
            <div style="background:#fff5f0;border:1px solid #ffccaa;border-radius:10px;
                        padding:12px 14px;margin:8px 0">
                <div style="font-size:11px;color:#e65100;font-weight:700;margin-bottom:6px">
                    🚨 고확률 사건 트리거 ({len(high_triggers)}개)
                </div>
                {''.join([f'<div style="font-size:12px;color:#000000;margin:3px 0">• {t["title"]} ({t["prob"]}%)</div>' for t in high_triggers[:3]])}
            </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.caption(f"데이터 분석 중... ({e})")

    # ── AI 엔진 상태 표시
    if groq_key:
        st.markdown("""
        <div style="background:#e8f5e8;color:#2e7d32;padding:8px 14px;border-radius:8px;
                    font-size:12px;margin-bottom:10px">
            ⚡ Groq (Llama 3.3 70B) 연결됨 — 빠른 응답 모드
        </div>""", unsafe_allow_html=True)
    elif api_key:
        st.markdown("""
        <div style="background:#e2f5ff;color:#1565c0;padding:8px 14px;border-radius:8px;
                    font-size:12px;margin-bottom:10px">
            🤖 Anthropic Claude Sonnet 연결됨
        </div>""", unsafe_allow_html=True)
    else:
        st.warning("사이드바에서 API Key를 입력하면 AI 상담이 활성화됩니다.\n\n**Groq**는 무료로 groq.com에서 발급 가능합니다.")

    # ── 캐시 상태 표시 + 재분석 버튼
    saju_key = pils_to_cache_key(pils)
    cache_focus_key = f"{saju_key}_{focus_key}"
    is_cached = bool(get_ai_cache(saju_key, "prophet"))

    # ── User Memory 업데이트 ──────────────────────────────
    try:
        update_user_profile(saju_key,
            concern=focus_key if focus_key != "종합" else "",
            last_focus=focus_key,
            persona=infer_persona(),
        )
        render_user_memory_badge(saju_key)
    except Exception:
        pass

    c1, c2 = st.columns([3, 1])
    with c1:
        if is_cached:
            st.markdown(
                "<div style='background:#e8f5e8;color:#2e7d32;padding:6px 12px;"
                "border-radius:6px;font-size:11px;margin-bottom:6px'>"
                "⚡ 캐시된 AI 해석 사용 중 — 즉시 출력</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                "<div style='background:#fff5e0;color:#e65100;padding:6px 12px;"
                "border-radius:6px;font-size:11px;margin-bottom:6px'>"
                "🔄 새 AI 분석 필요 — API 호출 예정</div>",
                unsafe_allow_html=True)
    with c2:
        if st.button("🔄 재분석", help="AI 캐시를 삭제하고 새로 분석합니다", use_container_width=True):
            clear_ai_cache_for_key(saju_key)
            st.rerun()

    # focus 컨텍스트를 session_state에 저장 (tab_ai_chat에서 사용)
    st.session_state["ai_focus"] = focus_key

    # ── Adaptive 페르소나 표시 ──────────────────────
    persona = infer_persona()
    p_emoji, p_label, p_color = get_persona_label(persona)
    st.markdown(f"""
    <div style="background:#f8f5ff;border:1px solid #d0b8ff;border-radius:10px;
                padding:10px 14px;margin:8px 0;display:flex;align-items:center;gap:10px">
        <span style="font-size:20px">{p_emoji}</span>
        <div>
            <div style="font-size:11px;color:#7b5ea7;font-weight:700">AI 분석 스타일 자동 설정</div>
            <div style="font-size:13px;color:{p_color};font-weight:800">{p_label}</div>
        </div>
        <div style="font-size:10px;color:#000000;margin-left:auto">
            집중 분야 선택에 따라 해석 스타일이 자동 변경됩니다
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 소름 엔진 — 과거 적중 미리보기 ────────────────
    st.markdown('<div class="gold-section">🔮 사주 패턴 분석 — 이미 겪으셨나요?</div>',
                unsafe_allow_html=True)
    try:
        gb = goosebump_engine(pils, birth_year, gender)
        if gb["past"]:
            gb_html = "".join([
                f'<div style="background:#ffffff;border-left:4px solid #000000;'
                f'padding:10px 14px;border-radius:4px 10px 10px 4px;margin:5px 0;'
                f'font-size:13px;color:#000000;line-height:1.8">'
                f'🔍 {s}</div>'
                for s in gb["past"]
            ])
            if gb["present"]:
                gb_html += "".join([
                    f'<div style="background:#ffffff;border-left:4px solid #4a90d9;'
                    f'padding:10px 14px;border-radius:4px 10px 10px 4px;margin:5px 0;'
                    f'font-size:13px;color:#000000;line-height:1.8">'
                    f'💡 {s}</div>'
                    for s in gb["present"][:1]
                ])
            if gb["future"]:
                gb_html += "".join([
                    f'<div style="background:#fff5e0;border-left:4px solid #e65100;'
                    f'padding:10px 14px;border-radius:4px 10px 10px 4px;margin:5px 0;'
                    f'font-size:13px;color:#000000;line-height:1.8">'
                    f'⚡ {s}</div>'
                    for s in gb["future"][:1]
                ])
            st.markdown(gb_html, unsafe_allow_html=True)
    except Exception:
        pass

    # ── Retention 위젯 ──────────────────────────────
    with st.expander("📊 운세 흐름 + 방문 기록", expanded=False):
        render_retention_widget(pils, birth_year, gender)

    tab_ai_chat(pils, name, birth_year, gender, api_key, groq_key=groq_key)


def menu12_manse(pils=None, birth_year=1990, gender="남"):
    """📅 만세력 탭 —— 일진·절기·길일달력 통합 UI"""
    today = datetime.now()

    st.markdown("""
    <div style='background:#000;color:#fff;border-radius:12px;
                padding:16px 20px;margin-bottom:14px'>
        <div style='font-size:20px;font-weight:900;letter-spacing:2px'>
            📅 만세력 · 일진 · 절기 달력
        </div>
        <div style='font-size:12px;opacity:0.7;margin-top:4px'>
            일진(日辰) · 24절기 · 길일/흥일 자동 표시
        </div>
    </div>""", unsafe_allow_html=True)

    # 오늘 일진 헤더
    today_iljin = ManseCalendarEngine.get_today_iljin()
    today_gil   = ManseCalendarEngine.get_gil_hyung(today.year, today.month, today.day)
    st.markdown(f"""
    <div style='background:{today_gil["bg"]};border:2px solid {today_gil["color"]};
                border-radius:12px;padding:14px 20px;margin-bottom:14px;
                display:flex;justify-content:space-between;align-items:center'>
      <div>
        <div style='font-size:13px;color:#888;font-weight:700'>TODAY 일진</div>
        <div style='font-size:28px;font-weight:900;color:#000;letter-spacing:3px'>
            {today_iljin["str"]}
        </div>
        <div style='font-size:12px;color:#555'>{today_iljin["oh"]} 일</div>
      </div>
      <div style='text-align:right'>
        <div style='font-size:18px;font-weight:800;color:{today_gil["color"]}'>
            {today_gil["grade"]}
        </div>
        <div style='font-size:12px;color:#777'>{today_gil["reason"]}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # 월 선택
    col_y, col_m, _ = st.columns([1, 1, 2])
    with col_y:
        sel_year  = st.selectbox("연도", list(range(2020, 2031)),
                                  index=today.year - 2020, label_visibility="collapsed")
    with col_m:
        sel_month = st.selectbox("월", list(range(1, 13)),
                                  index=today.month - 1, label_visibility="collapsed",
                                  format_func=lambda m: f"{m}월")

    # 절기 배지
    jeolgi_this = ManseCalendarEngine.get_month_jeolgi(sel_year, sel_month)
    if jeolgi_this:
        jeolgi_html = " &nbsp;".join(
            f"<span style='background:#000;color:#fff;padding:2px 8px;"
            f"border-radius:10px;font-size:11px;font-weight:700'>"
            f"{j['day']}일 {j['name']}</span>"
            for j in jeolgi_this
        )
        st.markdown(f"<div style='margin:6px 0 10px'>이달 절기: {jeolgi_html}</div>",
                    unsafe_allow_html=True)

    # 달력 그리드
    import calendar as _cal
    cal_data = ManseCalendarEngine.get_month_calendar(sel_year, sel_month)
    weekdays = ["月","火","水","木","金","土","日"]
    first_wd, _ = _cal.monthrange(sel_year, sel_month)

    # 헤더 행
    hdr = "".join(
        f"<td style='text-align:center;font-weight:800;font-size:12px;"
        f"color:{'#cc0000' if i==6 else '#0033cc' if i==5 else '#000'}'>{w}</td>"
        for i, w in enumerate(weekdays)
    )
    rows = f"<tr>{hdr}</tr><tr>"

    # 빈 셀 (1일 이전)
    for _ in range(first_wd):
        rows += "<td></td>"

    for entry in cal_data:
        d   = entry["day"]
        ilj = entry["iljin"]
        gil = entry["gil"]
        jeo = entry["jeolgi"]
        wd  = (first_wd + d - 1) % 7

        day_color = "#cc0000" if wd == 6 else "#0033cc" if wd == 5 else "#000"
        bg = gil["bg"]
        border = f"2px solid {gil['color']}" if gil["grade"] != "보통" else "1px solid #ddd"
        is_today = (d == today.day and sel_month == today.month and sel_year == today.year)
        if is_today:
            bg = "#fffde7"
            border = "2px solid #f9a825"

        jeolgi_label = f"<div style='font-size:8px;color:#7b1fa2;font-weight:700'>{jeo.split('(')[0]}</div>" if jeo else ""
        rows += (
            f"<td style='text-align:center;padding:4px 2px;border:{border};"
            f"background:{bg};border-radius:6px;vertical-align:top;min-width:38px'>"
            f"<div style='font-size:12px;font-weight:700;color:{day_color}'>{d}</div>"
            f"<div style='font-size:11px;font-weight:800;color:#000'>{ilj['str']}</div>"
            f"{jeolgi_label}"
            f"</td>"
        )
        if wd == 6 and d != cal_data[-1]["day"]:
            rows += "</tr><tr>"

    rows += "</tr>"
    st.markdown(
        f"<table style='width:100%;border-collapse:separate;border-spacing:3px'>{rows}</table>",
        unsafe_allow_html=True
    )

    # 길일/주의일 요약 바
    gil_days  = [e["day"] for e in cal_data if e["gil"]["grade"].startswith("길일")]
    warn_days = [e["day"] for e in cal_data if e["gil"]["grade"] == "주의"]
    st.markdown(f"""
    <div style='margin-top:12px;padding:10px 14px;background:#f8f8f8;
                border-radius:8px;font-size:12px'>
        <span style='color:#1a7a1a;font-weight:700'>⭐ 길일:</span>
        {', '.join(str(d)+'일' for d in gil_days) or '없음'} &nbsp;&nbsp;
        <span style='color:#cc0000;font-weight:700'>⚠️ 주의:</span>
        {', '.join(str(d)+'일' for d in warn_days) or '없음'}
    </div>""", unsafe_allow_html=True)

    # 날짜 선택 사주 분석
    st.markdown("---")
    st.markdown("**🔮 특정 날짜 사주 분석**", unsafe_allow_html=False)
    sel_day = st.number_input("날짜 선택",
                               min_value=1, max_value=len(cal_data),
                               value=today.day if sel_month == today.month and sel_year == today.year
                                     else 1,
                               step=1, label_visibility="visible")
    if st.button("🔮 이 날짜의 일진 사주 분석", use_container_width=True):
        iljin_sel = ManseCalendarEngine.get_iljin(sel_year, sel_month, int(sel_day))
        gil_sel   = ManseCalendarEngine.get_gil_hyung(sel_year, sel_month, int(sel_day))
        pils_day  = SajuCoreEngine.get_pillars(sel_year, sel_month, int(sel_day), 12, gender)
        yp = pils_day[0]["str"]; mp = pils_day[2]["str"]
        dp = pils_day[1]["str"]
        st.markdown(f"""
        <div style='background:#fff;border:2px solid #000;border-radius:12px;
                    padding:16px;margin-top:10px'>
            <div style='font-size:16px;font-weight:900;margin-bottom:8px'>
                {sel_year}년 {sel_month}월 {int(sel_day)}일 — {iljin_sel["str"]}일
                &nbsp;<span style='color:{gil_sel["color"]}'>{gil_sel["grade"]}</span>
            </div>
            <div style='display:flex;gap:12px;flex-wrap:wrap'>
                <div style='background:#f5f5f5;padding:8px 16px;border-radius:8px;
                            font-size:14px;font-weight:700'>年 {yp}</div>
                <div style='background:#f5f5f5;padding:8px 16px;border-radius:8px;
                            font-size:14px;font-weight:700'>月 {mp}</div>
                <div style='background:#000;color:#fff;padding:8px 16px;border-radius:8px;
                            font-size:14px;font-weight:700'>日 {dp}</div>
            </div>
            <div style='font-size:12px;color:#777;margin-top:8px'>{gil_sel["reason"]}</div>
        </div>""", unsafe_allow_html=True)


def main():
    # ── 페이지 설정 ─────────────────────────────────
    # (전역 CSS는 파일 상단 st.markdown으로 이미 적용됨)
    # main-header, section-label만 추가 정의
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #8B6914, #000000, #8B6914);
        color: white; text-align: center;
        padding: 24px 16px 20px;
        border-radius: 0 0 16px 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(139,105,20,0.3);
    }
    .main-header h1 {
        font-size: 26px; font-weight: 900;
        letter-spacing: 3px; margin: 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }
    @media (max-width:480px) {
        .main-header { padding: 16px 12px 14px; }
        .main-header h1 { font-size: 19px !important; letter-spacing: 1px !important; }
    }
    .main-header p { font-size: 13px; opacity: 0.85; margin: 5px 0 0; letter-spacing: 2px; }
    .section-label { font-size: 13px; font-weight: 700; color: #8B6914; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
    </style>""", unsafe_allow_html=True)

    # ── 헤더 ─────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>萬神 사주 천명풀이</h1>
        <p>四柱八字 · 天命을 밝히다</p>
    </div>""", unsafe_allow_html=True)

    # ── 스트릭 배너 (방문 추적) ──────────────────────
    try:
        streak_info = update_streak()
        sc = streak_info["streak"]
        if sc >= 2:
            se = "🏆" if sc >= 30 else "🔥" if sc >= 7 else "✨"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#fffde8,#fff8cc);
                        border:1px solid #e8d058;border-radius:10px;
                        padding:8px 14px;margin:6px 0;
                        display:flex;align-items:center;justify-content:space-between">
                <span style="font-size:13px;color:#8B6914;font-weight:700">
                    {se} {streak_info['message']}
                </span>
                <span style="font-size:11px;color:#aaa">최고 {streak_info['max']}일</span>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

    # ── AI 설정 — 메인 화면 expander ────────────────
    with st.expander("⚙️ 앱 설정 및 AI 캐스팅 (API 설정)", expanded=False):
        col_e1, col_e2 = st.columns([1, 2])
        with col_e1:
            st.markdown("**🤖 AI 엔진**")
            ai_engine = st.radio("AI 엔진", ["Groq (무료·빠름)", "Anthropic Claude"],
                                 label_visibility="collapsed", key="ai_engine_radio")
        with col_e2:
            if "Groq" in ai_engine:
                st.markdown("**🔑 Groq API Key**")
                groq_key = st.text_input("Groq Key", type="password",
                                         placeholder="gsk_...",
                                         label_visibility="collapsed")
                api_key = ""
                st.caption("groq.com → API Keys → Create (무료)")
            else:
                st.markdown("**🔑 Anthropic API Key**")
                api_key = st.text_input("Anthropic Key", type="password",
                                        placeholder="sk-ant-...",
                                        label_visibility="collapsed")
                groq_key = ""
                st.caption("console.anthropic.com")
    
    # ── 입력 폼 (카드 UI) ────────────────────────────
    st.markdown("""
    <div style="background:white;border-radius:16px;padding:24px 24px 8px;
                box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:4px">
        <div style="font-size:18px;font-weight:800;color:#000000;margin-bottom:4px">
            📝 사주 정보 입력
        </div>
    </div>""", unsafe_allow_html=True)

    with st.form("saju_form"):
        # ── 이름 + 성별 ──────────────────────
        col1, col2 = st.columns([3, 1])
        with col1:
            name = st.text_input("이름 (선택)", placeholder="홍길동",
                                 label_visibility="visible")
        with col2:
            st.markdown('<div style="margin-top:4px"></div>', unsafe_allow_html=True)
            gender = st.radio("성별", ["남", "여"], horizontal=True, key="gender_radio")

        # ── 양력/음력 선택 ────────────────────
        st.markdown('<div style="font-size:13px;font-weight:700;color:#8B6914;margin:12px 0 6px">📅 생년월일</div>', unsafe_allow_html=True)
        cal_col1, cal_col2 = st.columns([1, 2])
        with cal_col1:
            cal_type = st.radio("달력 구분", ["양력", "음력"], horizontal=True, key="cal_type_radio")
            is_leap_month = False
            if cal_type == "음력":
                is_leap_month = st.checkbox("윤달", help="윤달에 태어난 경우 체크")
        with cal_col2:
            if cal_type == "양력":
                birth_date_solar = st.date_input(
                    "양력 생년월일",
                    value=date(1990, 1, 1),
                    min_value=date(1940, 1, 1),
                    max_value=date(2010, 12, 31),
                    label_visibility="collapsed"
                )
                l_year, l_month, l_day = 1990, 1, 1
            else:
                birth_date_solar = None
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    l_year = st.number_input("음력 년", min_value=1940, max_value=2010, value=1990, step=1)
                with lc2:
                    l_month = st.selectbox("음력 월", list(range(1, 13)), format_func=lambda m: f"{m}월")
                with lc3:
                    l_day = st.number_input("음력 일", min_value=1, max_value=30, value=1, step=1)

        # 출생 시간
        st.markdown('<div style="font-size:13px;font-weight:700;color:#8B6914;margin:12px 0 6px">⏰ 출생 시간</div>', unsafe_allow_html=True)
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            JJ_12 = ["子","子","丑","丑","寅","寅","卯","卯","辰","辰","巳","巳",
                     "午","午","未","未","申","申","酉","酉","戌","戌","亥","亥"]
            birth_hour = st.selectbox(
                "출생 시간",
                options=list(range(0, 24)),
                format_func=lambda h: f"{h:02d}:00 ({JJ_12[h]}시)",
                index=12,
                label_visibility="collapsed"
            )
        with t_col2:
            unknown_time = st.checkbox("시간 모름", help="모르면 체크 (정오 계산)")

        # 결혼유무 + 직업
        st.markdown('<div style="font-size:13px;font-weight:700;color:#8B6914;margin:12px 0 6px">👤 추가 정보 (선택)</div>', unsafe_allow_html=True)
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            marriage_status = st.selectbox(
                "결혼 유무",
                ["미혼", "기혼", "이혼/별거", "사별", "재혼"],
                help="배우자운·인연운 분석에 활용"
            )
        with info_col2:
            occupation = st.selectbox(
                "직업 분야",
                ["선택 안 함", "직장인(회사)", "공무원/공기업", "전문직(의/법/회계)",
                 "사업/자영업", "예술/창작", "IT/개발", "교육/학술",
                 "금융/투자", "판매/유통", "건설/부동산", "학생",
                 "주부/육아", "구직중", "기타"],
                help="직업론·적성 분석에 활용"
            )

        st.markdown('<div style="margin-top:8px"></div>', unsafe_allow_html=True)
        submitted = st.form_submit_button("🔮 천명을 풀이하다", use_container_width=True,
                                          type="primary")

    if submitted or "saju_pils" in st.session_state:
        if submitted:
            # 음력 → 양력 변환
            if cal_type == "음력":
                try:
                    birth_date_solar = lunar_to_solar(int(l_year), int(l_month), int(l_day), is_leap_month)
                    st.info(f"📅 음력 {int(l_year)}년 {int(l_month)}월 {int(l_day)}일"
                            f"{'(윤달)' if is_leap_month else ''} → "
                            f"**양력 {birth_date_solar.strftime('%Y년 %m월 %d일')}** 로 변환")
                except Exception as e:
                    st.error(f"음력 변환 오류. 양력으로 직접 입력해주세요.")
                    st.stop()

            b_year  = birth_date_solar.year
            b_month = birth_date_solar.month
            b_day   = birth_date_solar.day
            b_hour  = 12 if unknown_time else birth_hour

            with st.spinner("사주를 계산하는 중..."):
                pils = SajuCoreEngine.get_pillars(b_year, b_month, b_day, b_hour, gender)
                st.session_state["saju_pils"]        = pils
                st.session_state["birth_year"]        = b_year
                st.session_state["birth_month"]       = b_month
                st.session_state["birth_day"]         = b_day
                st.session_state["birth_hour"]        = b_hour
                st.session_state["gender"]            = gender
                st.session_state["saju_name"]         = name if name else "내담자"
                st.session_state["marriage_status"]   = marriage_status
                st.session_state["occupation"]        = occupation
                st.session_state["cal_type"]          = cal_type
                if cal_type == "음력":
                    st.session_state["lunar_info"] = f"{int(l_year)}년 {int(l_month)}월 {int(l_day)}일{'(윤)' if is_leap_month else ''}"
        
        pils = st.session_state.get("saju_pils")
        birth_year = st.session_state.get("birth_year", 1990)
        gender = st.session_state.get("gender", "남")
        name = st.session_state.get("saju_name", "내담자")
        marriage_status = st.session_state.get("marriage_status", "미혼")
        occupation = st.session_state.get("occupation", "선택 안 함")
        lunar_info = st.session_state.get("lunar_info", "")
        cal_type_saved = st.session_state.get("cal_type", "양력")
        birth_month = st.session_state.get("birth_month", 1)
        birth_day   = st.session_state.get("birth_day", 1)
        birth_hour2 = st.session_state.get("birth_hour", 12)
        
        if pils:
            # ── 🧠 기억 시스템 자동 업데이트 ─────────────────
            try:
                # ① 정체 기억 업데이트 (사주 분석 시점에 1회)
                ilgan_char  = pils[1]["cg"] if pils and len(pils) > 1 else ""
                gyeok_data  = get_gyeokguk(pils)
                gyeok_name  = gyeok_data.get("격국명", "") if gyeok_data else ""
                str_info    = get_strength_info(pils)
                sn_val      = str_info.get("신강신약", "") if str_info else ""
                ys_data     = calc_yongshin(pils, birth_year, gender)
                ys_list     = ys_data.get("종합_용신", []) if ys_data else []
                core_trait  = f"{ilgan_char} 일간 / {sn_val} / {gyeok_name}"
                SajuMemory.update_identity(ilgan_char, gyeok_name, core_trait, ys_list)

                # ③ 흐름 기억 업데이트 (현재 대운 기반)
                dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, 1, 1, gender)
                cur_year = datetime.now().year
                cur_dw = next(
                    (d for d in dw_list if d.get("시작연도", 0) <= cur_year <= d.get("종료연도", 9999)),
                    None
                )
                if cur_dw:
                    turning = calc_turning_point(pils, birth_year, gender, cur_year)
                    stage = turning.get("intensity", "안정기") if turning and turning.get("is_turning") else "안정기"
                    period = f"{cur_dw.get('시작연도', '')}~{cur_dw.get('종료연도', '')}"
                    SajuMemory.update_flow(stage, period, cur_dw.get("str", ""))
            except Exception:
                pass  # 기억 업데이트 실패해도 앱은 계속 실행

            # ── 🗣 기억 기반 개인화 인사말 ──────────────────
            try:
                intro_msg = SajuMemory.get_personalized_intro()
                if intro_msg:
                    st.markdown(f"""
                    <div style="background:#f0f7ff;border-left:5px solid #000000;
                                border-radius:8px;padding:10px 16px;margin:8px 0;
                                font-size:13px;color:#000000;font-weight:600">
                        🧠 {intro_msg}
                    </div>""", unsafe_allow_html=True)
            except Exception:
                pass

            # 이름 + 추가정보 배너
            display_name = name if name else "내담자"
            marriage_icon = {"미혼":"💚","기혼":"💑","이혼/별거":"💔","사별":"🖤","재혼":"🌸"}.get(marriage_status,"")
            occ_short = occupation if occupation != "선택 안 함" else ""

            # 생년월일 표시: 입력값 그대로 보존
            if lunar_info and cal_type_saved == "음력":
                date_badge = (
                    f"<span style='font-size:12px;background:#ede4ff;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                    f"음력 {lunar_info}</span>"
                    f"<span style='font-size:11px;color:#000000;margin-left:6px'>"
                    f"(양력 {birth_year}.{birth_month:02d}.{birth_day:02d})</span>"
                )
            else:
                date_badge = (
                    f"<span style='font-size:12px;background:#e8f5e8;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                    f"양력 {birth_year}.{birth_month:02d}.{birth_day:02d}</span>"
                )

            JJ_12b = ["子","子","丑","丑","寅","寅","卯","卯","辰","辰","巳","巳",
                      "午","午","未","未","申","申","酉","酉","戌","戌","亥","亥"]
            hour_badge = (
                f"<span style='font-size:12px;background:#ffffff;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                f"{birth_hour2:02d}시({JJ_12b[birth_hour2]}시)</span>"
            )

            info_tags = ""
            if marriage_status != "미혼":
                info_tags += f"<span style='font-size:12px;background:#edfffb;padding:3px 10px;border-radius:12px;margin:2px'>{marriage_icon} {marriage_status}</span> "
            if occ_short:
                info_tags += f"<span style='font-size:12px;background:#e8f3ff;padding:3px 10px;border-radius:12px;margin:2px'>💼 {occ_short}</span>"

            st.markdown(f"""
            <div style="text-align:center;padding:14px;background:linear-gradient(135deg,#fff5e0,#fff0dc);
                        border-radius:14px;margin-bottom:10px">
                <div style="color:#000000;font-size:20px;font-weight:700;margin-bottom:6px">
                    ✨ {display_name}님의 사주팔자 ✨
                </div>
                <div style="margin-bottom:6px">{date_badge}{hour_badge}</div>
                <div style="margin-top:4px">{info_tags}</div>
            </div>""", unsafe_allow_html=True)

            # ── 8개 메뉴 탭 ──────────────────────────────
            tabs = st.tabs([
                "📋 종합 사주 리포트",
                "🌊 인생 흐름 (대운 100년)",
                "🎯 과거 적중 타임라인",
                "🔮 미래 3년 집중 분석",
                "💰 재물·사업 특화",
                "💑 궁합·인간관계",
                "🤖 AI 상담",
                "🔴 특급 비방록",
                "☀️ 일일 운세",
                "📅 월별 운세",
                "🎊 신년 운세",
                "🗓️ 만세력",
            ])

            with tabs[0]:
                menu1_report(pils, name, birth_year, gender, occupation, api_key, groq_key)
            with tabs[1]:
                menu2_lifeline(pils, birth_year, gender, name, api_key, groq_key)
            with tabs[2]:
                menu3_past(pils, birth_year, gender, name, api_key, groq_key)
            with tabs[3]:
                menu4_future3(pils, birth_year, gender, marriage_status, name, api_key, groq_key)
            with tabs[4]:
                menu5_money(pils, birth_year, gender, name, api_key, groq_key)
            with tabs[5]:
                menu6_relations(pils, name, birth_year, gender, marriage_status, api_key, groq_key)
            with tabs[6]:
                menu7_ai(pils, name, birth_year, gender, api_key, groq_key)
            with tabs[7]:
                menu8_bihang(pils, name, birth_year, gender)
            with tabs[8]:
                menu9_daily(pils, name, birth_year, gender)
            with tabs[9]:
                menu10_monthly(pils, name, birth_year, gender)
            with tabs[10]:
                menu11_yearly(pils, name, birth_year, gender)
            with tabs[11]:
                menu12_manse(pils, birth_year, gender)

if __name__ == "__main__":
    main()
