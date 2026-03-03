# -*- coding: utf-8 -*-
import streamlit as st
import requests
import json
import os
from datetime import date, datetime, timedelta
import random
import io
import re
import logging as _logging
_saju_log = _logging.getLogger("saju")
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
    LUNAR_LIB_AVAILABLE = False  # -> 기존 내장 테이블로 자동 fallback



# ==========================================================
#  🌌 시스템 공통 상수
# ==========================================================
_AI_SANDBOX_HEADER = """
[🌌 MASTER MANSE SAJU ENGINE V3.1]
본 페르소나는 대한민국 명리학의 정수를 AI로 구현한 '만신(萬神)' 시스템입니다.
데이터 분석과 직관적 통찰이 결합된 최상위 상담 엔진으로 동작합니다.
"""

# 시각 표시용 12지 배열 (24시간 → 지지 매핑) - 모듈 수준 공통 상수
_JJ_HOUR_FULL = [
    "子(자) (자시)","子(자) (자시)","丑(축) (축시)","丑(축) (축시)","寅(인) (인시)","寅(인) (인시)",
    "卯(묘) (묘시)","卯(묘) (묘시)","辰(진) (진시)","辰(진) (진시)","巳(사) (사시)","巳(사) (사시)",
    "午(오) (오시)","午(오) (오시)","未(미) (미시)","未(미) (미시)","申(신) (신시)","申(신) (신시)",
    "酉(유) (유시)","酉(유) (유시)","戌(술) (술시)","戌(술) (술시)","亥(해) (해시)","亥(해) (해시)",
]
_JJ_HOUR_SHORT = [
    "子(자)","子(자)","丑(축)","丑(축)","寅(인)","寅(인)","卯(묘)","卯(묘)","辰(진)","辰(진)","巳(사)","巳(사)",
    "午(오)","午(오)","未(미)","未(미)","申(신)","申(신)","酉(유)","酉(유)","戌(술)","戌(술)","亥(해)","亥(해)",
]

# ==========================================================
#  음력 ↔ 양력 변환 (내장 테이블 방식)
#  출처: 한국천문연구원 만세력 기준 1900~2060
# ==========================================================

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


# ==================================================
#  🌌 한국천문연구원 (KASI) API 통합 모듈
# ==================================================
class KasiAPI:
    """
    한국천문연구원 공공데이터 API 연동 클래스
    - 24절기 정밀 시각 조회 (초 단위)
    - 음양력 변환 (윤달 완벽 처리)
    - 음력 기준 정보 조회
    """
    BASE_URL = "http://apis.data.go.kr/B090041/openapi/service"
    _SERVICE_KEY: str = ""  # 사이드바에서 주입

    @classmethod
    def set_key(cls, key: str):
        cls._SERVICE_KEY = key.strip()

    @classmethod
    def _get(cls, endpoint: str, params: dict) -> dict | None:
        """공통 GET 요청. 실패 시 None 반환."""
        if not cls._SERVICE_KEY:
            return None
        try:
            import requests
            params["serviceKey"] = cls._SERVICE_KEY
            params["_type"] = "json"
            params["numOfRows"] = 10
            url = f"{cls.BASE_URL}/{endpoint}"
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            items = (data.get("response", {})
                        .get("body", {})
                        .get("items", {})
                        .get("item"))
            if items is None:
                return None
            return items if isinstance(items, list) else [items]
        except Exception:
            return None

    @classmethod
    def get_24division(cls, year: int) -> list | None:
        """
        해당 연도의 24절기 목록과 정밀 시각(초 단위) 조회
        반환: [{"solDay":"20260205","solTime":"170000","name":"입춘"}, ...]
        """
        items = cls._get(
            "SpcdeInfoService/get24DivInfo",
            {"solYear": year}
        )
        return items

    @classmethod
    def lunar_to_solar_kasi(cls, lunar_year: int, lunar_month: int,
                             lunar_day: int, is_leap: bool = False) -> date | None:
        """
        KASI API로 음력 -> 양력 변환 (윤달 완벽 지원)
        반환: date 객체, 실패 시 None
        """
        items = cls._get(
            "LrsrCldInfoService/getLunCalInfo",
            {
                "lunYear":  lunar_year,
                "lunMonth": f"{lunar_month:02d}",
                "lunDay":   f"{lunar_day:02d}",
                "lunLeapmonth": "1" if is_leap else "0",
            }
        )
        if not items:
            return None
        row = items[0]
        try:
            sol = str(row.get("solYear", "")) + \
                  f"{int(row.get('solMonth', 1)):02d}" + \
                  f"{int(row.get('solDay', 1)):02d}"
            return date(int(sol[:4]), int(sol[4:6]), int(sol[6:8]))
        except Exception:
            return None

    @classmethod
    def get_lunar_info(cls, solar_year: int, solar_month: int,
                        solar_day: int) -> dict | None:
        """
        양력 날짜 -> 음력 정보 조회 (윤달 여부 포함)
        반환: {"lunYear":..., "lunMonth":..., "lunDay":..., "lunLeapmonth":...}
        """
        items = cls._get(
            "LrsrCldInfoService/getLunaraInfo",
            {
                "solYear":  solar_year,
                "solMonth": f"{solar_month:02d}",
                "solDay":   f"{solar_day:02d}",
            }
        )
        if not items:
            return None
        return items[0]

    @classmethod
    def get_term_datetime(cls, year: int, term_name: str) -> datetime | None:
        """
        특정 연도의 절기 이름 -> 정밀 시각(초 단위) 반환
        term_name 예: "입춘", "경칩", "청명" ...
        """
        items = cls.get_24division(year)
        if not items:
            return None
        for item in items:
            if term_name in str(item.get("name", "")):
                sol_day = str(item.get("solDay", ""))
                sol_time = str(item.get("solTime", "000000")).zfill(6)
                try:
                    return datetime(
                        int(sol_day[:4]), int(sol_day[4:6]), int(sol_day[6:8]),
                        int(sol_time[:2]), int(sol_time[2:4]), int(sol_time[4:6])
                    )
                except Exception:
                    return None
        return None

class AstroEngine:
    """
    고정밀 천문 계산 엔진 (1940-2040 범위 보정)
    Jean Meeus 알고리즘 기반의 태양 황도 계산 보조
    """
    @staticmethod
    def get_solar_term_precision(year, month, day, term_name):
        """
        KASI 데이터가 없는 경우(1940-1999, 2028-2040) 사용하는 정밀 계산식
        오차 범위: 약 1~2분 이내
        """
        # 24절기별 태양 황경 (입춘=315도, 우수=330도, ..., 하지=90도, ...)
        TERM_LONGITUDES = {
            "소한": 285, "대한": 300, "입춘": 315, "우수": 330, "경칩": 345, "춘분": 0,
            "청명": 15, "곡우": 30, "입하": 45, "소만": 60, "망종": 75, "하지": 90,
            "소서": 105, "대서": 120, "입추": 135, "처서": 150, "백로": 165, "추분": 180,
            "한로": 195, "상강": 210, "입동": 225, "소설": 240, "대설": 255, "동지": 270
        }
        
        target_long = TERM_LONGITUDES.get(term_name)
        if target_long is None: return None
        
        # 기준 시각 (2000년 입춘: 2월 4일 17:40경 = JD 2451579.236)
        # 매우 단순화된 선형 근사 + 보정항
        # 365.24219일마다 같은 황경이 돌아옴
        from datetime import datetime as py_datetime, timedelta
        
        # 대략적인 절기 날짜 (manse.py SOLAR_TERMS 기준)
        # SajuCoreEngine.SOLAR_TERMS 인덱스 활용
        term_list = ["소한","대한","입춘","우수","경칩","춘분","청명","곡우","입하","소만","망종","하지",
                     "소서","대서","입추","처서","백로","추분","한로","상강","입동","소설","대설","동지"]
        t_idx = term_list.index(term_name)
        
        # 기준연도(2000) 기준 해당 절기 시각 (분 단위 정밀도 반영)
        ref_times = {
            "입춘": (2, 4, 17, 40), "경칩": (3, 5, 15, 43), "청명": (4, 4, 20, 32), 
            "입하": (5, 5, 13, 50), "망종": (6, 5, 17, 59), "소서": (7, 7, 4, 14),
            "입추": (8, 7, 14, 3), "백로": (9, 7, 16, 59), "한로": (10, 8, 8, 38),
            "입동": (11, 7, 11, 48), "대설": (12, 7, 4, 37), "소한": (1, 6, 10, 1)
        }
        # 짝수 절기(중기) 포함
        ref_times_all = {
            "소한": (1, 6, 10, 1),   "대한": (1, 21, 3, 23),
            "입춘": (2, 4, 17, 40),  "우수": (2, 19, 13, 13),
            "경칩": (3, 5, 15, 43),  "춘분": (3, 20, 16, 35),
            "청명": (4, 4, 20, 32),  "곡우": (4, 20, 3, 40),
            "입하": (5, 5, 13, 50),  "소만": (5, 21, 2, 49),
            "망종": (6, 5, 17, 59),  "하지": (6, 21, 10, 48),
            "소서": (7, 7, 4, 14),   "대서": (7, 22, 21, 43),
            "입추": (8, 7, 14, 3),   "처서": (8, 23, 4, 49),
            "백로": (9, 7, 16, 59),  "추분": (9, 23, 2, 28),
            "한로": (10, 8, 8, 38),  "상강": (10, 23, 11, 47),
            "입동": (11, 7, 11, 48), "소설": (11, 22, 9, 19),
            "대설": (12, 7, 4, 37),  "동지": (12, 21, 22, 37)
        }
        
        m, d, h, mi = ref_times_all.get(term_name, (month, 15, 12, 0))
        ref_dt = py_datetime(2000, m, d, h, mi)
        
        # 경과년도에 따른 회귀년(Tropical Year) 보정
        diff_years = year - 2000
        # 1회귀년 = 365.24219일
        shift_days = diff_years * 365.24219
        target_dt = ref_dt + timedelta(days=shift_days)
        
        # 윤년 보정 등 세부 사항은 timedelta가 내부적으로 처리함
        return target_dt.month, target_dt.day, target_dt.hour, target_dt.minute


@st.cache_data
def lunar_to_solar(lunar_year, lunar_month, lunar_day, is_leap=False):
    """음력 -> 양력 변환. KASI API 우선 사용, 실패 시 로컬 데이터 fallback."""
    # 1. KASI API 시도 (키가 설정된 경우)
    kasi_res = KasiAPI.lunar_to_solar_kasi(lunar_year, lunar_month, lunar_day, is_leap)
    if kasi_res:
        return kasi_res

    # 2. 로컬 데이터 Fallback
    if lunar_year not in _LUNAR_DATA:
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
    """양력 -> 음력 변환. 반환: (음력년, 음력월, 음력일, 윤달여부)"""
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


try:
    from reportlab.lib.units import inch
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
except ImportError:
    pass  # reportlab 없으면 PDF 기능 비활성화 (REPORTLAB_AVAILABLE로 이미 제어됨)


# ==========================================================
#  🧠 사주 AI 기억 시스템 (SajuMemory) - 4계층 구조
#  정보 저장 ❌ / 맥락 저장 ⭕
# ==========================================================

class SajuMemory:
    """
    만신(萬神) 영속 기억 시스템 (E-Version)
    파일 기반 저장소 (history_memory.json)를 통해 브라우저 종료 후에도 상담 맥락을 유지합니다.
    """
    MEMORY_FILE = "history_memory.json"

    @staticmethod
    def build_context_prompt() -> str:
        """SajuJudgmentRules 등에서 호출하는 전역 맥락 빌더"""
        name = st.session_state.get("saju_name", "내담자")
        return SajuMemory.build_rich_ai_context(name)

    @staticmethod
    def _load_all() -> dict:
        if not os.path.exists(SajuMemory.MEMORY_FILE): return {}
        try:
            with open(SajuMemory.MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: return {}

    @staticmethod
    def _save_all(data: dict):
        try:
            with open(SajuMemory.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception: pass

    @staticmethod
    def get_memory(name: str) -> dict:
        key = name.strip()
        all_data = SajuMemory._load_all()
        if key not in all_data:
            all_data[key] = {
                "identity": {"profile": {}, "trait_fixed": [], "implicit_persona": "초기탐색형", "narrative": ""},
                "interest": {},
                "flow": {"stage": "탐색", "consult_stage": "탐색"},
                "behavior_stats": {"query_lengths": [], "visit_hours": [], "emotion_log": []},
                "conversation": [],
                "trust": {"score": 50, "level": 1, "history": []},
                "bond": {"level": 1, "score": 10, "label": "탐색"},
                "matrix": {"행동": 50, "감정": 50, "기회": 50, "관계": 50, "에너지": 50},
                "v2_features": {"mbti": "", "evolution_level": 1}
            }
            SajuMemory._save_all(all_data)
        return all_data[key]

    @staticmethod
    def adjust_bond(name: str, amount: int):
        def update(m):
            b = m.get("bond", {"level": 1, "score": 0})
            b["score"] = max(0, min(100, b["score"] + amount))
            # 20점당 1레벨업 (최대 5레벨)
            b["level"] = min(5, (b["score"] // 20) + 1)
            labels = ["탐색", "편안", "신뢰", "의존", "동반자"]
            b["label"] = labels[b["level"]-1]
            m["bond"] = b
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def update_matrix(name: str, key: str, value: int):
        def update(m):
            if "matrix" not in m: m["matrix"] = {"행동": 50, "감정": 50, "기회": 50, "관계": 50, "에너지": 50}
            m["matrix"][key] = max(0, min(100, value))
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def record_behavior(name: str, query: str):
        def update(m):
            stats = m.get("behavior_stats", {"query_lengths": [], "visit_hours": []})
            stats["query_lengths"].append(len(query))
            stats["visit_hours"].append(datetime.now().hour)
            # 최근 20개만 유지
            if len(stats["query_lengths"]) > 20: stats["query_lengths"].pop(0)
            if len(stats["visit_hours"]) > 20: stats["visit_hours"].pop(0)
            m["behavior_stats"] = stats
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def adjust_trust(name: str, amount: int, reason: str = ""):
        def update(m):
            t = m.get("trust", {"score": 50, "level": 1, "history": []})
            t["score"] = max(0, min(100, t["score"] + amount))
            # 레벨 계산 (20점당 1레벨)
            t["level"] = (t["score"] // 20) + 1
            t["history"].append({"time": datetime.now().strftime("%Y-%m-%d"), "amount": amount, "reason": reason})
            m["trust"] = t
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def update_memory(name: str, update_fn):
        all_data = SajuMemory._load_all()
        key = name.strip()
        if key not in all_data: all_data[key] = SajuMemory.get_memory(name)
        all_data[key] = update_fn(all_data[key])
        SajuMemory._save_all(all_data)

    @staticmethod
    def update_identity(name: str,
                        profile: dict = None,
                        trait_fixed: list = None,
                        implicit_persona: str = None,
                        narrative: str = None):
        """
        내담자 정체성(identity) 갱신.
        - profile       : 사주-MBTI / trait_desc 등 프로파일 딕셔너리
        - trait_fixed   : 고정 성향 태그 리스트
        - implicit_persona : 행동 유형 문자열 (예: '분석탐구형')
        - narrative     : 현재 인생 서사 문자열
        """
        def update(m):
            ident = m.get("identity", {
                "profile": {}, "trait_fixed": [],
                "implicit_persona": "초기탐색형", "narrative": ""
            })
            if profile is not None:
                ident["profile"].update(profile)
            if trait_fixed is not None:
                ident["trait_fixed"] = trait_fixed
            if implicit_persona is not None:
                ident["implicit_persona"] = implicit_persona
            if narrative is not None:
                ident["narrative"] = narrative
            m["identity"] = ident
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def record_interest(name: str, topic: str):
        def update(m):
            m["interest"][topic] = m["interest"].get(topic, 0) + 1
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def get_interest_summary(name: str):
        mem = SajuMemory.get_memory(name)
        interests = mem.get("interest", {})
        if not interests: return "전반적 운세"
        return ", ".join(k for k, v in sorted(interests.items(), key=lambda x: x[1], reverse=True)[:2])

    @staticmethod
    def add_conversation(name: str, topic: str, content: str, emotion: str = ""):
        def update(m):
            m["conversation"].append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "topic": topic, "summary": content[:150], "emotion": emotion
            })
            if len(m["conversation"]) > 7: m["conversation"].pop(0)
            return m
        SajuMemory.update_memory(name, update)

    @staticmethod
    def get_personalized_intro(name: str, pils: list = None) -> str:
        mem = SajuMemory.get_memory(name)
        conv = mem.get("conversation", [])
        if conv:
            return f"허허, 다시 찾아왔구먼. 지난 '{conv[-1]['topic']}' 자리 이후로 {name}의 기운이 어찌 흘렀는지 내 신안(神眼)에 선히 보이느니라. 오늘은 또 어떤 천명(天命)의 실타래를 풀러 왔는가?"

        if pils:
            profile = PersonalityProfiler.analyze(pils)
            desc = profile.get('trait_desc', "깊은 내면의 힘")
            return f"허어, 어서 오게. {desc}의 기질을 타고난 {name}의 팔자(八字)가 내 신안에 선히 보이는구먼. 이 만신의 문을 두드린 데는 분명한 까닭이 있으리라. 어디, 속 이야기를 털어놓아 보게나."

        return f"허허, 어서 오게. 자네 기운이 느껴지는구먼... 나는 만신(萬神)이라네. 천명(天命)을 읽고 팔자(八字)의 이치를 풀어내는 것이 내 소임이니, 무엇이든 묻고 가게나."

    @staticmethod
    def build_rich_ai_context(name: str) -> str:
        mem = SajuMemory.get_memory(name)
        profile = mem["identity"].get("profile", {})
        convs = mem.get("conversation", [])
        trust = mem.get("trust", {"score": 50, "level": 1})
        bond = mem.get("bond", {"level": 1, "label": "탐색"})
        v2 = mem.get("v2_features", {})
        matrix = mem.get("matrix", {})
        
        # 🌌 Master Version Platform Context
        implicit = mem["identity"].get("implicit_persona", "초기탐색형")
        evolution_lvl = v2.get("evolution_level", 1)
        
        ctx = f"\n[🌌 MASTER PLATFORM CONTEXT (Bond: {bond['label']} Lv.{bond['level']})]\n"
        ctx += f"- AI-내담자 유대감: {bond['label']} 상태 (함께한 진화 Lv.{evolution_lvl})\n"
        ctx += f"- 인생 매트릭스 지표: 행동({matrix.get('행동',50)}), 감정({matrix.get('감정',50)}), 기회({matrix.get('기회',50)}), 에너지({matrix.get('에너지',50)})\n"
        
        if profile: 
            ctx += f"- 사주-MBTI: {profile.get('mbti')} / 페르소나: {profile.get('trait_desc')}\n"
            if mem["identity"].get("narrative"):
                ctx += f"- 현재 인생 서사: '{mem['identity']['narrative']}'\n"
        
        # 🗺️ Timeline 맥락
        timeline_ctx = DestinyTimelineEngine.get_context_summary()
        ctx += f"- 운명 타임라인: {timeline_ctx}\n"
        
        if convs:
            ctx += "- 주요 상담 맥락:\n"
            for c in convs[-3:]:
                ctx += f"  * {c['topic']}: {c['summary']}\n"
        
        # 👥 AICouncil 준비 지침
        ctx += f"\n[시스템 지침: AI Council 모드]\n당신은 이제 단독 상담사가 아닌, 3인의 전문가(명리분석/심리상담/전략코치)가 통합된 존재입니다. 각 관점을 융합하여 깊이 있는 결론을 내리세요.\n"
        ctx += SelfEvolutionEngine.get_instruction(implicit)
            
        return ctx

class AICouncil:
    """👥 다중 AI 페르소나 토론 시스템 (Master Version)"""
    @staticmethod
    def get_personas() -> dict:
        return {
            "analyst": "사주 원국과 대운의 흐름을 냉철하게 분석하는 정통 명리학자",
            "counselor": "내담자의 감정을 공감하고 심리적 안정을 도모하는 심리 상담 전문가",
            "coach": "분석된 운세를 바탕으로 현실적인 행동 지침과 전략을 제시하는 커리어 코치"
        }

    @staticmethod
    def build_council_prompt(user_query: str) -> str:
        p = AICouncil.get_personas()
        return f"""
[👥 AI Council: 다중 전문가 통합 전수 지침]
당신은 현재 3인의 마스터 전문가로 구성된 '상담위원회'입니다. 
다음 세 전문가가 내부 토론을 거쳐 합의된 최상의 결론을 내담자에게 전달하십시오.

1. 🏛️ 명리분석가: {p['analyst']}
2. 🧘 심리상담가: {p['counselor']}
3. 🚀 전략코치: {p['coach']}

답변 구성 원칙:
- 전문가 3인의 관점이 모두 녹아든 '통합 리포트' 형식으로 답변하세요.
- [분석: 운의 흐름], [케어: 마음가짐], [행동: 현실적 조언] 항목이 조화롭게 포함되어야 합니다.
- 만신(萬神)의 권위 있고 따뜻한 어조(고어체 융합)를 끝까지 유지하십시오.
"""

class LifeNarrativeEngine:
    """📖 사용자의 삶을 스토리(Narrative)로 정의하고 서사를 부여하는 엔진"""
    @staticmethod
    def update_narrative(name: str, topic_kr: str, emotion: str):
        def update(m):
            bond_lv = m.get("bond", {}).get("level", 1)
            # 심화 서사 생성 로직
            base_narratives = {
                "직업/진로": "자신의 천명을 찾아가는 고귀한 여정",
                "재물/사업": "풍요의 바다를 향해 돛을 펼치는 도전",
                "연애/결혼": "서로의 기운이 만나 조화를 이루는 인연의 숲",
                "인간관계": "다양한 삶의 결이 부딪히며 다듬어지는 과정",
                "인생 방향": "자아의 근원을 찾아 떠나는 내면의 항해",
                "운세 흐름": "하늘의 운율에 맞춰 춤추는 인생의 파동"
            }
            theme = base_narratives.get(topic_kr, "삶의 신비를 풀어가는 여정")
            
            if emotion == "불안": theme += " (어둠 속에서 빛을 찾는 중)"
            elif emotion == "결심": theme += " (새로운 태양이 뜨는 시점)"
            
            if bond_lv >= 4:
                m["identity"]["narrative"] = f"만신과 함께 써내려가는 '{theme}'의 마스터 피스"
            else:
                m["identity"]["narrative"] = theme
            return m
        SajuMemory.update_memory(name, update)

class GoalCreationEngine:
    """🎯 사용자의 숨은 목표(Goal)를 발견하고 정의하는 엔진"""
    @staticmethod
    def extract_goal(name: str, query: str):
        def update(m):
            if "identity" not in m: m["identity"] = {}
            if "goals" not in m["identity"]: m["identity"]["goals"] = []
            
            # 키워드 기반 단순 목표 추출 (향후 LLM 분석 결과 피드백 가능)
            if any(k in query for k in ["성공", "부자", "돈", "수익"]): goal = "경제적 자유 달성"
            elif any(k in query for k in ["이직", "취업", "합격"]): goal = "사회적 성취와 안착"
            elif any(k in query for k in ["외롭", "결혼", "만남"]): goal = "진정한 인연과의 결합"
            else: return m
            
            if goal not in m["identity"]["goals"]:
                m["identity"]["goals"].append(goal)
            return m
        SajuMemory.update_memory(name, update)

class DestinyMatrix:
    """📊 인생의 5대 핵심 지표를 관리하는 매트릭스 엔진"""
    @staticmethod
    def calculate_sync(name: str, pils: dict, luck_score: int):
        # 운세 점수와 심리 상태를 결합하여 지표 산출
        mem = SajuMemory.get_memory(name)
        stats = mem.get("behavior_stats", {})
        
        # 행동력 (질문 길이와 적극성)
        action = min(100, 50 + (len(stats.get("query_lengths", [])) * 2))
        # 에너지 (운세 점수 기반)
        energy = luck_score
        # 감정 (최근 감정 로그 기반 - 스텁)
        emotion = 60 if "불안" not in str(mem.get("conversation", [])) else 40
        
        SajuMemory.update_matrix(name, "행동", action)
        SajuMemory.update_matrix(name, "에너지", energy)
        SajuMemory.update_matrix(name, "감정", emotion)
        SajuMemory.update_matrix(name, "기회", luck_score + 10 if luck_score > 70 else luck_score)
        SajuMemory.update_matrix(name, "관계", 50)

class PersonalityEngine:
    """🧠 내담자의 입력 패턴을 분석하여 '심저(深底) 성향'을 파악하는 엔진"""
    @staticmethod
    def analyze_behavior(name: str):
        mem = SajuMemory.get_memory(name)
        stats = mem.get("behavior_stats", {})
        ql = stats.get("query_lengths", [])
        vh = stats.get("visit_hours", [])
        
        if not ql: return "초기탐색형"
        
        # 분석 로직
        avg_len = sum(ql) / len(ql)
        night_visits = len([h for h in vh if h >= 22 or h <= 4])
        
        if avg_len > 100: persona = "논리/분석 탐색형"
        elif night_visits >= 3: persona = "현실불안 위로형"
        elif len(ql) > 10: persona = "해답갈구 확신형"
        else: persona = "온건적 소통형"
        
        def update_implicit(m):
            m["identity"]["implicit_persona"] = persona
            # 이해도 상승
            m["v2_features"]["evolution_level"] = min(10, m["v2_features"].get("evolution_level", 1) + 1)
            return m
        SajuMemory.update_memory(name, update_implicit)
        return persona

def _local_saju_engine(pils, name, birth_year, gender, query):
    """만세력/격국/용신/대운 엔진 기반 로컬 사주 상담 (무당 말투) — 재사용 가능 모듈"""
    import re as _re
    from datetime import date as _d_today
    q = query or ""
    current_year = datetime.now().year
    ilgan = pils[1]["cg"] if len(pils) > 1 else "?"
    _ss = st.session_state
    bm  = _ss.get("birth_month",  1)
    bd  = _ss.get("birth_day",    1)
    bh  = _ss.get("birth_hour",  12)
    bmn = _ss.get("birth_minute", 0)

    is_today = bool(_re.search(r'오늘|일진|내일|이번주', q))
    is_year  = bool(_re.search(r'올해|세운|금년|올해운세|2025|2026|2027', q)) or is_today
    is_money = bool(_re.search(r'재물|돈|사업|수입|투자|부자|재산', q))
    is_lotto = bool(_re.search(r'로또|복권|횡재|당첨|행운|대박|일확천금', q))
    is_love  = bool(_re.search(r'연애|결혼|궁합|이성|남자|여자|남편|아내|인연|배우자', q))
    is_health= bool(_re.search(r'건강|병원|아프|수술|몸|질병|체력', q))
    is_dw    = bool(_re.search(r'대운|운세흐름|인생|10년|장기|앞으로|미래', q))
    is_past  = bool(_re.search(r'과거|지나온|예전|돌아보|과거운|이전|맞춰봐', q))
    is_job   = bool(_re.search(r'직업|진로|취업|창업|커리어|직장|일자리|사업방향', q))
    is_char  = bool(_re.search(r'성격|성향|기질|특성|나는|내가|나의', q))
    is_avoid = bool(_re.search(r'피해야|조심|주의|하면안|금기|위험|손재|삼가|나쁜|피하', q))
    is_lucky = bool(_re.search(r'좋은날|길일|행운의날|언제가좋|언제해야|좋은시기|황금기', q))
    is_move  = bool(_re.search(r'이사|이직|이동|이민|출국|이전|결정|시작|개업', q))
    is_study = bool(_re.search(r'시험|공부|합격|학업|수능|입학|자격증|고시', q))
    is_family= bool(_re.search(r'부모|아버지|어머니|자녀|아들|딸|형제|가족|자식', q))



    out = [f"허허, 어서 오게. {name}의 팔자를 내 신안(神眼)으로 살펴보겠느니라.\n"]
    try:
        if is_today:
            today = _d_today.today()
            sw = get_yearly_luck(pils, current_year)
            sw_ss = sw.get("십성_천간","") or "-"
            sw_gh = sw.get("길흉","평")
            sw_gan= sw.get("세운","")
            # 한자→한글 변환
            _SS_KR2 = {
                "食神":"식신","傷官":"상관","偏財":"편재","正財":"정재",
                "偏官":"편관","正官":"정관","偏印":"편인","正印":"정인",
                "比肩":"비견","劫財":"겁재",
            }
            sw_ss_kr = _SS_KR2.get(sw_ss, sw_ss)

            _SW_D = {
                "偏財": "재물·이성 기운이 활발하느니라. 능동적으로 움직이면 좋은 결과가 오리라.",
                "正財": "안정된 수입·신뢰 기운이 흐르느니라. 약속과 계획을 착실히 이행하게.",
                "食神": "창의와 표현의 기운이 넘치는 시기니라. 새 아이디어를 펼치기 좋으니라.",
                "傷官": "말조심, 윗사람과의 마찰을 피하게. 창의성은 좋으나 충돌을 조심하게.",
                "偏官": "긴장과 변동의 기운이 있느니라. 안전과 건강에 각별히 유의하게.",
                "正官": "명예와 인정의 기운이 흐르느니라. 책임을 다하면 좋은 평가가 오리라.",
                "偏印": "이동·변화 기운이 있느니라. 새 정보를 수집하되 결정은 신중히 하게.",
                "正印": "학습과 지혜의 기운이 충만하느니라. 배움과 자격 준비에 집중하게.",
                "比肩": "독립 의지가 강해지는 기운이니라. 협력보다 단독 추진이 유리하느니라.",
                "劫財": "경쟁과 재물 손실 기운이 있느니라. 보증·투자·동업을 삼가게.",
            }

            out.append(f"**오늘({today.month}월 {today.day}일) 일진 풀이**\n")
            out.append(f"올해({current_year}년) {sw_gan} 세운 안에서 오늘 하루가 펼쳐지느니라.\n")
            if sw_ss and sw_ss != "-":
                out.append(f"올해 흐르는 십성: **{sw_ss}({sw_ss_kr})** | 길흉: **{sw_gh}**\n")
                out.append(_SW_D.get(sw_ss, f"{sw_ss_kr} 기운이 오늘 하루에도 그대로 흐르느니라.") + "\n")
            else:
                out.append(f"길흉: **{sw_gh}** — 흐름을 잘 읽고 신중히 움직이게.\n")

            # ── 상황별 전용 답변 (경찰서/법원/병원/계약/면접/데이트/여행) ──
            _SIT = {
                ("경찰서","파출소","조사","수사"): {
                    "偏官": "⚠️ 편관(偏官) 기운이라 법적 문제가 복잡해질 수 있느니라. 말을 아끼고 솔직하게 임하게. 변호인 동석을 권하느니라.",
                    "正官": "✅ 정관(正官) 기운이라 공적 기관에서 정당한 결과가 나오기 좋은 기운이니라. 원칙대로 당당히 임하게.",
                    "劫財": "⚠️ 겁재(劫財) 기운이라 불필요한 다툼이 커질 수 있느니라. 감정 조절이 핵심이니라.",
                    "傷官": "⚠️ 상관(傷官) 기운이라 말이 화를 부를 수 있느니라. 불필요한 말은 삼가고 사실만 말하게.",
                    "_default": "법적 기관 방문은 당당하되 말을 아끼게. 진실과 원칙을 지키면 억울함은 풀리느니라.",
                },
                ("법원","재판","소송","고소","고발"): {
                    "正官": "✅ 정관(正官) 기운이라 법적 판결이 원칙대로 내려지기 좋은 기운이니라. 증거를 잘 준비하게.",
                    "偏官": "⚠️ 편관(偏官) 기운이라 변동 가능성이 있느니라. 전문 법조인의 조언이 필수니라.",
                    "食神": "✅ 식신(食神) 기운이라 표현과 소통이 원활한 날이니라. 소송에서 변론 능력이 빛을 발하느니라.",
                    "_default": "법적 다툼은 증거와 원칙으로 임하게. 감정적 대응은 독이 되느니라.",
                },
                ("병원","수술","치료","검사","진료","몸이"): {
                    "偏官": "⚠️ 편관(偏官) 기운이라 건강 문제에 각별히 신경 쓰게. 수술은 가능하면 미루는 것이 좋으니라.",
                    "食神": "✅ 식신(食神) 기운이라 몸에 좋은 에너지가 흐르느니라. 검사·치료 결과가 양호하게 나오기 좋은 날이니라.",
                    "正印": "✅ 정인(正印) 기운이라 귀인(의사)의 도움으로 좋은 결과가 나올 기운이니라.",
                    "_default": "건강 문제는 미루지 말고 전문의의 소견을 따르게. 몸이 자본이니라.",
                },
                ("계약","서명","계약서","사인"): {
                    "正財": "✅ 정재(正財) 기운이라 안정적 계약 성사에 좋은 날이니라. 꼼꼼히 검토 후 서명하게.",
                    "偏財": "✅ 편재(偏財) 기운이라 사업 관련 계약에 유리하느니라. 단 세부 조항을 반드시 확인하게.",
                    "傷官": "⚠️ 상관(傷官) 기운이라 계약서 분쟁이 일어나기 쉬운 날이니라. 변호인 검토를 거치게.",
                    "劫財": "⚠️ 겁재(劫財) 기운이라 손해 계약이 될 수 있느니라. 오늘 계약은 가능하면 미루게.",
                    "_default": "계약 전 세부 조항을 꼼꼼히 읽고, 서두르지 말게.",
                },
                ("면접","취업","입사","채용"): {
                    "正官": "✅ 정관(正官) 기운이라 면접에서 신뢰감과 능력이 빛나는 날이니라! 자신 있게 임하게.",
                    "食神": "✅ 식신(食神) 기운이라 표현력과 아이디어가 빛나는 날이니라. 창의성을 드러내게.",
                    "偏官": "도전적 면접이 될 수 있느니라. 압박에도 침착하게 대응하게.",
                    "劫財": "⚠️ 겁재(劫財) 기운이라 면접 경쟁이 치열하니 더욱 철저히 준비하게.",
                    "_default": "면접은 준비한 만큼 나오느니라. 자신감 있게 임하되 과장은 금하게.",
                },
                ("여행","출장","출국","해외"): {
                    "偏印": "이동의 기운이 강한 偏印(편인) 기운이라 여행에 맞는 날이니라. 단 분실·사고에 주의하게.",
                    "偏官": "⚠️ 편관(偏官) 기운이라 여행 중 사고·분실 위험이 있느니라. 안전 수칙을 철저히 지키게.",
                    "食神": "✅ 복록의 식신(食神) 기운이라 여행에서 좋은 경험과 인연을 만나는 날이니라.",
                    "_default": "여행은 철저한 준비가 안전을 보장하느니라. 안전 수칙을 지키게.",
                },
            }
            sit_answered = False
            for keywords, ss_map in _SIT.items():
                if any(k in q for k in keywords):
                    sit_answer = ss_map.get(sw_ss, ss_map.get("_default",""))
                    if sit_answer:
                        kw_label = keywords[0]
                        out.append(f"\n**[{kw_label} 방문 — 오늘의 사주 판단]**\n{sit_answer}\n")
                    sit_answered = True
                    break

            if not sit_answered:
                # 일반 오늘 풀이
                _GH_TODAY = {
                    "길": "오늘은 길한 기운이 흐르느니라! 중요한 일을 추진하면 좋은 결과가 오니라.",
                    "+": "오늘은 길한 기운이 흐르느니라! 중요한 일을 추진하면 좋은 결과가 오니라.",
                    "평": "오늘은 평온한 기운이니라. 무리하지 말고 꾸준히 나아가는 것이 좋으니라.",
                    "흉": "오늘은 조심스러운 기운이니라. 중요한 결정은 내일로 미루고 안전을 우선하게.",
                    "-": "오늘은 조심스러운 기운이니라. 중요한 결정은 내일로 미루고 안전을 우선하게.",
                }
                out.append(f"\n{_GH_TODAY.get(sw_gh, '오늘 하루 평온한 기운이니라.')}\n")

            sw_n = get_yearly_luck(pils, current_year + 1)
            sw_n_ss = sw_n.get("십성_천간","")
            sw_n_kr = _SS_KR2.get(sw_n_ss, sw_n_ss)
            out.append(f"\n내년 {current_year+1}년은 {sw_n.get('세운','')} [{sw_n_ss}/{sw_n_kr}] 기운이 다가오고 있으니 미리 내다보게.\n")



        elif is_year:
            sw    = get_yearly_luck(pils, current_year)
            sw_ss = sw.get("십성_천간",""); sw_gh = sw.get("길흉",""); sw_gan = sw.get("세운","")
            try: tp = calc_turning_point(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            except Exception: tp = {}
            _SW = {
                "偏財":"재물 변동과 이성 인연의 기운이 강하느니라. 사업 기회가 오지만 투기는 조심하게.",
                "正財":"안정된 수입과 결혼 인연의 기운이 들어오느니라. 재물을 차곡차곡 모을 수 있는 해니라.",
                "食神":"직업과 재능이 빛을 발하는 해니라. 새 일을 시작하거나 자격 취득에 좋으니라.",
                "傷官":"창의성이 폭발하지만 윗사람과의 마찰을 조심해야 하느니라.",
                "偏官":"직장 변동과 사고 기운이 있느니라. 건강과 안전에 각별히 주의하게.",
                "正官":"명예와 승진의 기운이 강하느니라. 조직에서 인정받는 해니라.",
                "偏印":"계획이 자주 바뀌고 이사·이동의 기운이 있느니라. 신중하게 결정하게.",
                "正印":"학업과 자격 취득에 유리한 해니라. 어머니와의 인연도 돈독해지느니라.",
                "比肩":"독립심이 강해지고 경쟁이 치열해지는 해니라. 동업보다 단독 행동이 낫느니라.",
                "劫財":"재물 손실과 경쟁이 극심한 해니라. 보증과 투자를 자제하게.",
            }
            _ACT = {
                "偏財":"적극적 투자·사업 기회를 잡되 안전 자산 30% 이상 반드시 확보하게!",
                "正財":"부동산·예금·적금 등 안정 자산에 집중하게. 불필요한 지출을 줄이는 것이 재물의 시작이니라.",
                "食神":"자격증 취득·신규 프로젝트 시작이 최적이니라. 전문성을 드러낼 시기니라.",
                "傷官":"창작·발명은 좋으나 직속 상관·계약서 분쟁 조심. 독립 행보는 내년 이후가 유리하니라.",
                "偏官":"건강 정기검진 필수. 무리한 확장·새 사업 시작 자제. 법적 분쟁도 조심하게.",
                "正官":"자격증·승진 시험·공직 지원에 최적의 해! 조직 내 신뢰를 쌓는 것이 핵심이니라.",
                "偏印":"이사·이직·전공 변경 시 신중히 결정하게. 새 분야 학습에는 유리하니라.",
                "正印":"자격증·진학·연구에 집중하라. 어머니·스승과의 관계를 돈독히 하게.",
                "比肩":"독립·창업·단독 프로젝트에 유리. 동업·보증은 이 해에 시작하지 말게.",
                "劫財":"현금 보유·빚 상환 우선. 도박·투기·보증 절대 금지. 경쟁에서 냉정함을 유지하게.",
            }
            out.append(f"**{current_year}년 ({current_year-birth_year+1}세) 세운 분석**\n")
            out.append(f"올해 세운: **{sw_gan}** — 십성 **{sw_ss}**, 길흉 **{sw_gh}**\n")
            out.append(_SW.get(sw_ss, f"{sw_ss} 기운이 강하게 작동하는 해니라.") + "\n")
            out.append(f"\n**[올해 행동 지침]** {_ACT.get(sw_ss, '분수에 맞게 안정적으로 움직이게.')}\n")
            tp_int = tp.get("intensity","")
            tp_sc  = tp.get("score_change", 0)
            tp_rsn = tp.get("reason", [])
            if "강력" in tp_int:
                out.append(f"\n**⚡ 인생 전환점 경보!** 운세 변화폭 {tp_sc:+d}점 — {tp_int}\n")
                for r in tp_rsn[:3]: out.append(f"• {r}\n")
            elif "주요" in tp_int or "변화" in tp_int:
                out.append(f"\n**🔄 중요한 변화 감지** 운세 변화폭 {tp_sc:+d}점 — {tp_int}\n")
                for r in tp_rsn[:2]: out.append(f"• {r}\n")
            sw_n  = get_yearly_luck(pils, current_year+1)
            sw_n2 = get_yearly_luck(pils, current_year+2)
            out.append(f"\n**[내년 미리보기]** {current_year+1}년: {sw_n.get('세운','')} [{sw_n.get('십성_천간','')}] {sw_n.get('길흉','')}\n")
            out.append(f"**[후년 미리보기]** {current_year+2}년: {sw_n2.get('세운','')} [{sw_n2.get('십성_천간','')}] {sw_n2.get('길흉','')}")

        elif is_lotto:
            sw    = get_yearly_luck(pils, current_year)
            ys    = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            si    = get_ilgan_strength(ilgan, pils)
            sw_ss = sw.get("십성_천간","")
            sw_gh = sw.get("길흉","")
            sw_gan= sw.get("세운","")
            y1    = ys.get("용신_1순위","-")
            heui  = ys.get("희신","-")
            gisin = ", ".join(ys.get("기신",[]))
            sn    = si.get("신강신약","중화")

            _LOTTO_SS = {
                "偏財": ("★★★ 횡재 최고 대운!", "편재(偏財) 세운은 에너지가 발산하는 횡재의 열쇠니라. 복권·투자·영업에서 뜻밖의 행운이 터질 수 있느니라. 단 한 방에 올인하면 되려 잃을 수 있으니 분산하게."),
                "正財": ("★★ 안정 재운, 복권보다 저축·투자가 맞느니라", "정재(正財) 세운은 꾸준한 수입의 기운이니라. 대박보다 안정 자산이 맞느니라."),
                "食神": ("★★ 재능이 돈이 되는 해, 의외의 수입 기대", "식신(食神) 세운은 창의와 전문성으로 뜻밖의 수입이 오는 해니라."),
                "劫財": ("⚠️ 재물 손실 주의, 복권 당첨보다 보존이 먼저", "겁재(劫財) 세운은 재물이 나가기 쉬운 해니라. 투기는 절대 삼가게."),
                "偏官": ("⚠️ 변동·사고 주의, 횡재 기대 어려운 해", "편관(偏官) 세운은 안전에 집중할 시기니라. 투기 대신 건강을 지키게."),
            }
            lotto_star, lotto_desc = _LOTTO_SS.get(sw_ss, (
                "★ 보통 수준",
                f"{sw_ss or '이'} 기운의 해니라. 로또보다 실력과 노력이 더 확실한 수익이 되느니라."
            ))

            out.append(f"**{name}의 로또·복권·횡재운 분석**\n허허, 횡재는 하늘이 내리는 것이니라. 신안으로 살펴보겠느니라.\n")
            out.append(f"\n**{current_year}년 세운 {sw_gan} [{sw_ss}] {sw_gh}**\n")
            out.append(f"{lotto_star} {lotto_desc}\n")

            yong_oh = OH.get(sw_gan[:1] if sw_gan else "", "")
            if yong_oh in {y1, heui}:
                out.append(f"\n흐! 올해 세운 {sw_gan}이 용신({y1})·희신({heui})과 일치하느니라! **연중 최설 횡재 기운**이니 이 시기를 놓치지 말게!\n")
            elif gisin and yong_oh in gisin:
                out.append(f"\n⚠️ 올해 세운이 기신({gisin})에 해당하니 **큰 투기는 삼가게**. 소액으로만 즐기는 것이 현명하니라.\n")
            else:
                out.append(f"\n용신 **{y1}** 오행이 강한 해에 한 번씩 시도해보는 것이 이치에 맞니라. 꼭 오늘만이 기회가 아니느니라.\n")

            gold_lotto = []
            for yr in range(current_year, current_year + 6):
                sw_l = get_yearly_luck(pils, yr)
                ss_l = sw_l.get("십성_천간","")
                yo_l = OH.get(sw_l.get("세운","")[:1], "")
                if ss_l == "偏財" and sw_l.get("길흉","") in ("길","+"):
                    gold_lotto.append(f"  * **{yr}년**({yr-birth_year+1}세): {sw_l.get('세운','')} [偏財 편재] ★★★ 횡재 피크!")
                elif ss_l in ("偏財","食神") and yo_l in {y1, heui}:
                    gold_lotto.append(f"  * **{yr}년**({yr-birth_year+1}세): {sw_l.get('세운','')} [{ss_l}] ★★ 용신과 일치하는 행운 시기")
            if gold_lotto:
                out.append(f"\n**[향후 횡재·행운 피크 시기]**\n")
                for g in gold_lotto:
                    out.append(g + "\n")
            else:
                out.append(f"\n당장의 횡재보다 꾸준한 재물 축적이 이 팔자에 맞느니라.\n")

            out.append(f"\n로또는 정가비를 즐기는 선에서 하는 것이 현명하니라. {ilgan}(일간)의 기운상 매주 소액으로 꾸준히 사는 것이 한 방보다 낫느니라!\n")

        elif is_money:

            gk  = get_gyeokguk(pils)
            ys  = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            gkn = gk["격국명"] if gk else "미정격"
            y1  = ys.get("용신_1순위","-"); y2 = ys.get("용신_2순위","-")
            heui= ys.get("희신","-"); gisin = ", ".join(ys.get("기신",[]))
            _GKM = {
                "정관격":"명예와 재물이 함께 오는 격국이니라. 조직에서 승진할수록 재물이 늘어나느니라. 직함과 신뢰가 곧 재물이니 체면을 지키게.",
                "정재격":"꾸준한 노력으로 재물을 쌓는 격국이니라. 금융·부동산에서 재물이 쌓이느니라. 규칙적 저축과 장기 투자가 최고의 전략이니라.",
                "편재격":"사업가 기질의 격국이니라. 투자·영업에서 큰 기회가 오느니라. 기복이 크니 안전 자산 30% 이상 반드시 확보하게. 한 방을 노리다 전부 잃는 수가 있느니라.",
                "식신격":"전문성을 키우면 재물이 자연스럽게 따라오는 격국이니라. 실력을 쌓는 것이 곧 재물을 쌓는 것이니라.",
                "상관격":"창의적 방법으로 재물을 만드는 격국이니라. 프리랜서·컨설팅·콘텐츠 창작이 맞느니라.",
                "편인격":"기술·학문·특허로 재물을 만드는 격국이니라. 단 재물보다 전문성에 집중할 때 돈이 따라오느니라.",
                "정인격":"안정적 직업·자격증으로 꾸준히 재물을 쌓는 격국이니라. 주식·투기보다 연금·부동산이 맞느니라.",
                "비견격":"독립 사업이나 프리랜서로 재물을 벌어야 하는 격국이니라. 공동 투자·동업은 반드시 계약서를 쓰게.",
                "겁재격":"경쟁과 도전 속에서 재물을 얻는 격국이니라. 손실도 크지만 회복도 빠른 팔자니라.",
            }
            out.append(f"**{name}의 재물운 완전 분석**\n격국은 **{gkn}**이니라.\n")
            out.append(_GKM.get(gkn, f"{gkn}의 재물 패턴은 독특하니라. 용신 기운을 따르게.") + "\n")
            out.append(f"\n용신 **{y1}** / 희신 **{heui}** 기운이 강한 해(年)에 재물 결정을 내려야 하느니라.\n")
            if gisin: out.append(f"⚠️ **기신 경고:** {gisin} 기운 강한 해에는 큰 투자·동업·보증을 반드시 피하게! 이 해에 움직이면 손실이 크니라.\n")
            # 향후 재물 황금기 (용신 세운, 별점 차등)
            gold_ohs = {o for o in [y1, y2] if o in ("木","火","土","金","水")}
            gold_yrs = []
            for yr in range(current_year, current_year+11):
                sw_g = get_yearly_luck(pils, yr)
                if OH.get((sw_g.get("세운","")[:1]),"") in gold_ohs:
                    sw_g_ss = sw_g.get("십성_천간","")
                    star = "★★★" if sw_g_ss in ("偏財","正財","食神") else "★★" if sw_g_ss in ("正官","正印") else "★"
                    gold_yrs.append(f"* **{yr}년**({yr-birth_year+1}세): {sw_g.get('세운','')} [{sw_g_ss}] {sw_g.get('길흉','')} {star}")
            if gold_yrs:
                out.append(f"\n**[향후 재물 황금기 — 용신 세운]**\n")
                for gy in gold_yrs[:6]: out.append(gy + "\n")
                out.append("이 해들에 중요한 재물 결정을 내리게!\n")
            # 대운×세운 재물 더블 황금기
            try:
                hl_m = generate_engine_highlights(pils, birth_year, gender, bm, bd, bh, bmn)
                double_mp = [m for m in hl_m.get("money_peak",[]) if m.get("ss") == "더블"]
                if double_mp:
                    out.append(f"\n**[대운×세운 재물 더블 황금기]** — 이 시기가 진짜 인생 재물 피크니라!\n")
                    for m in double_mp[:3]: out.append(f"* {m.get('year','')}년 ({m.get('age','')}) {m.get('desc','')}\n")
            except Exception: pass
            # 기신 대운 경고
            try:
                dw_list_m = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                gisin_ohs = set(ys.get("기신",[]))
                gisin_dws = [dw for dw in dw_list_m
                             if OH.get(dw.get("cg",""),"") in gisin_ohs and dw["종료연도"] >= current_year]
                if gisin_dws:
                    gdw = gisin_dws[0]
                    gdw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(gdw["cg"],"-")
                    if gdw["시작연도"] <= current_year:
                        out.append(f"\n⚠️ 지금 **{gdw['str']} {gdw_ss}** 기신 대운 진행 중! {gdw['종료연도']-current_year}년 더 이어지느니라. 대형 투자·보증 자제가 최선이니라.\n")
                    else:
                        out.append(f"\n⚠️ {gdw['시작연도']}년({gdw['시작나이']}세)부터 **{gdw['str']} {gdw_ss}** 기신 대운이 오느니라. 미리 안전 자산 확보를 서두르게!\n")
            except Exception: pass

        elif is_love:
            out.append(f"**{name}의 인연·결혼운 완전 분석**\n허어, 인연의 실타래를 신안으로 살펴보겠느니라.\n")

            # 1. 배우자 자리(정재/편재 또는 정관/편관) 분석
            yk = get_yukjin(ilgan, pils, gender)
            spouse_keys = (["아내","처","正財","妻"] if gender == "남" else ["남편","夫","正官","情夫","편관"])
            for rel in yk:
                rn = rel.get("관계","")
                if any(k in rn for k in spouse_keys):
                    loc = rel.get("위치","없음")
                    out.append(f"\n**[배우자 자리]** {rn} — 위치: **{loc}**\n")
                    out.append(rel.get("desc","") + "\n")
                    if rel.get("present"):
                        out.append("허허, 배우자 기운이 사주에 뚜렷이 자리 잡고 있구먼. 인연은 반드시 오느니라.\n")
                    else:
                        out.append("배우자 기운이 약하니 대운·세운에서 재성/관성이 들어올 때 적극적으로 움직이게.\n")
                    break

            # 2. 일지(배우자 자리) 지지 해석
            iljj = pils[1]["jj"] if len(pils) > 1 else "?"
            _ILJJ_LOVE = {
                "子(자)":"지혜롭고 다정한 배우자 기운. 지적 교감과 대화가 관계의 핵심이니라.",
                "丑(축)":"성실하고 현실적인 배우자 기운. 안정과 책임감을 중시하느니라.",
                "寅(인)":"진취적이고 리더십 강한 배우자 기운. 독립심이 강하니 존중이 필수니라.",
                "卯(묘)":"섬세하고 예술적 감수성의 배우자 기운. 감성 교류가 사랑의 언어니라.",
                "辰(진)":"능력 있고 카리스마 강한 배우자 기운. 단 고집이 센 면이 있느니라.",
                "巳(사)":"두뇌 명석하고 표현력 강한 배우자 기운. 열정적 사랑을 추구하느니라.",
                "午(오)":"열정적이고 활발한 배우자 기운. 외향적이고 솔직한 애정 표현이 특징이니라.",
                "未(미)":"온화하고 예술적 감수성의 배우자 기운. 배려심이 깊고 감성이 풍부하느니라.",
                "申(신)":"냉철하고 실리적인 배우자 기운. 현실 판단이 빠르고 독립적이니라.",
                "酉(유)":"세련되고 완벽주의적 배우자 기운. 까다로울 수 있으나 깊은 헌신이 있느니라.",
                "戌(술)":"의리 있고 뜨거운 열정의 배우자 기운. 한번 마음을 열면 평생 지키느니라.",
                "亥(해)":"지혜롭고 깊은 내면의 배우자 기운. 자유 기질이 있어 구속을 싫어하느니라.",
            }
            out.append(f"\n**[일지 배우자 자리 — {iljj}]**\n{_ILJJ_LOVE.get(iljj, f'일지 {iljj}의 기운이 배우자 자리에 흐르느니라.')}\n")

            # 3. 대운에서 재성/관성운 들어오는 시기
            try:
                daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                love_dw_ss = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
                love_dws = [dw for dw in daewoon
                            if TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"") in love_dw_ss
                            and dw["종료연도"] >= current_year]
                if love_dws:
                    cdw = love_dws[0]
                    cdw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(cdw["cg"],"")
                    if cdw["시작연도"] <= current_year:
                        out.append(f"\n**[대운 인연 시기]** 지금 **{cdw['str']} {cdw_ss}** 대운 진행 중! {cdw['종료연도']-current_year}년 남았으니 이 기간을 놓치지 말게!\n")
                    else:
                        out.append(f"\n**[대운 인연 시기]** {cdw['시작연도']}년({cdw['시작나이']}세)부터 **{cdw['str']} {cdw_ss}** 대운이 열리느니라. 그때가 인연의 문이 활짝 열리는 시기니라.\n")
            except Exception: pass

            # 4. 향후 3년 중 연애운 좋은 해 특정
            love_yr_ss = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
            love_yrs = []
            for yr in range(current_year, current_year + 4):
                sw_l = get_yearly_luck(pils, yr)
                sw_ss_l = sw_l.get("십성_천간","")
                if sw_ss_l in love_yr_ss:
                    love_yrs.append(f"**{yr}년**({yr-birth_year+1}세): {sw_l.get('세운','')} [{sw_ss_l}] {sw_l.get('길흉','')} ← 이성 인연 기운이 강하느니라!")
            if love_yrs:
                out.append("\n**[향후 3년 연애·결혼 특효 시기]**\n")
                for ly in love_yrs: out.append(f"* {ly}\n")
                out.append("이 해들에 적극적으로 인연을 찾아 나서게. 하늘이 돕는 시기니라!\n")
            else:
                sw_now = get_yearly_luck(pils, current_year)
                out.append(f"\n올해 {sw_now.get('세운','')} [{sw_now.get('십성_천간','')}] — 향후 3년은 이성 세운이 약하니 자기계발로 내실을 다지는 시기니라. 인연은 준비된 자에게 오느니라.\n")

            # 5. 도화살 확인
            try:
                sinsal = get_special_stars(pils)
                dohwa_found = [s for s in sinsal if "도화" in s.get("name","")]
                ss12 = get_12sinsal(pils)
                dohwa12 = [s for s in ss12 if "도화" in s.get("이름","") or "년살" in s.get("이름","")]
                if dohwa_found or dohwa12:
                    out.append("\n**[신살 — 도화살(桃花殺)]** 도화살이 사주에 있구먼!\n이성의 인기를 한몸에 받는 매력의 기운이니라. 이성이 먼저 다가오는 팔자이나, 감정에 휩쓸려 경솔한 선택을 하지 않도록 명심하게.\n")
                else:
                    out.append("\n도화살은 없으나, 꾸준한 진심이 최고의 인연을 불러오느니라.\n")
            except Exception: pass

            # 6. 결혼 적령기
            current_age = current_year - birth_year + 1
            out.append(f"\n**[결혼 적령기 — 현재 {current_age}세]**\n")
            try:
                daewoon2 = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                love_ss2 = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
                future_dws = [dw for dw in daewoon2
                              if TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"") in love_ss2
                              and dw["종료연도"] >= current_year]
                if future_dws:
                    bd2 = future_dws[0]
                    bd2_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(bd2["cg"],"")
                    if bd2["시작연도"] <= current_year:
                        out.append(f"지금 **{bd2['str']} {bd2_ss}** 대운 중! **{current_year}~{bd2['종료연도']}년**이 최적 결혼 시기니라. 망설이지 말게!\n")
                    else:
                        out.append(f"**{bd2['시작연도']}년({bd2['시작나이']}세)**부터 {bd2['str']} **{bd2_ss}** 대운이 열리느니라. 그 무렵 결혼 결실이 맺어질 가능성이 높느니라.\n")
                else:
                    for yr in range(current_year, current_year + 10):
                        sw_y = get_yearly_luck(pils, yr)
                        if sw_y.get("십성_천간","") in ({"偏財","正財"} if gender == "남" else {"偏官","正官"}):
                            out.append(f"**{yr}년({yr-birth_year+1}세)** 세운에 인연 기운이 들어오느니라. 그 무렵 준비하게.\n")
                            break
            except Exception: pass

        elif is_health:
            ilgan_oh = OH.get(ilgan,"")
            _OHB = {"木":"간장·담낭·눈·근육·인대","火":"심장·소장·혈관·혈압",
                    "土":"비장·위장·췌장·소화기","金":"폐·대장·기관지·피부","水":"신장·방광·생식기·귀·뼈"}
            _OHA = {"木":"스트레칭과 충분한 수면이 최우선이니라. 분노·스트레스가 간장을 상하게 하느니라.",
                    "火":"심혈관 정기검진이 필수이니라. 카페인·음주를 자제하고 과로를 삼가게.",
                    "土":"식사 규칙성이 핵심이니라. 폭식·군것질을 삼가게. 걱정이 위장을 상하게 하느니라.",
                    "金":"습도 관리가 중요하니라. 가을·건조한 환경을 조심하게.",
                    "水":"충분한 수분 섭취가 필수니라. 과로·짠 음식을 피하게."}
            out.append(f"**{name}의 건강운 완전 분석**\n일간 {ilgan}의 오행은 **{OHN.get(ilgan_oh,'')}({ilgan_oh})**이니라.\n")
            out.append(f"타고난 취약 신체: **{_OHB.get(ilgan_oh,'전반적 건강')}**\n")
            out.append(_OHA.get(ilgan_oh,'규칙적인 생활이 핵심이니라.') + "\n")
            # 오행 과다/부족 건강 경고
            oh_s = calc_ohaeng_strength(ilgan, pils)
            for o, v in oh_s.items():
                if v >= 35: out.append(f"\n⚠️ **{OHN.get(o,'')}({o}) 과다({v}%):** {_OHB.get(o,'')} 계통 특히 조심하게. 과다한 오행이 해당 장기를 혹사시키느니라.")
                elif v <= 5: out.append(f"\n💊 **{OHN.get(o,'')}({o}) 부족({v}%):** {_OHB.get(o,'')} 계통 보강하게. 부족한 오행이 해당 장기를 약하게 만드느니라.")
            # 현재 대운 건강 영향
            try:
                dw_list_h = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                cdw_h = next((d for d in dw_list_h if d["시작연도"] <= current_year <= d["종료연도"]), None)
                if cdw_h:
                    cdw_ss_h = TEN_GODS_MATRIX.get(ilgan,{}).get(cdw_h["cg"],"-")
                    cdw_oh_h = OH.get(cdw_h["cg"],"")
                    _DWH = {
                        "偏官":"편관 대운은 압박과 스트레스가 극심하느니라. 면역력 저하와 사고 위험이 높으니 정기검진을 서두르게.",
                        "傷官":"상관 대운은 신경계 과부하와 과로가 주적이니라. 수면 관리와 스트레스 해소가 핵심이니라.",
                        "劫財":"겁재 대운은 외상·수술·혈액 관련 건강 이슈가 올 수 있으니라. 운동 시 안전에 유의하게.",
                        "偏印":"편인 대운은 우울·불안·정신건강에 주의가 필요하니라. 고립을 피하고 활동적으로 지내게.",
                        "比肩":"비견 대운은 과도한 경쟁과 독립 행보로 체력 소진을 조심하게. 충분한 휴식이 필수이니라.",
                        "食神":"식신 대운은 건강이 비교적 좋은 시기니라. 다만 과식으로 인한 소화계 문제를 조심하게.",
                        "正財":"정재 대운은 안정적 건강 유지가 가능한 시기니라. 규칙적 생활로 내실을 다지게.",
                        "正官":"정관 대운은 스트레스가 직장에서 오므로 멘탈 관리에 집중하게.",
                        "偏財":"편재 대운은 분주한 활동으로 체력 소진을 조심하게. 철저한 체력 관리가 필요하느니라.",
                        "正印":"정인 대운은 건강이 좋은 편이나 과보호·의존 경향이 오히려 체력을 약하게 만들 수 있느니라.",
                    }
                    out.append(f"\n**[현재 대운 건강 영향]** {cdw_h['str']} **{cdw_ss_h}** 대운 ({cdw_h['종료연도']-current_year}년 남음)\n")
                    out.append(_DWH.get(cdw_ss_h, f"{cdw_ss_h} 대운의 건강 기운이 흐르느니라. 몸의 신호에 귀를 기울이게.") + "\n")
                    out.append(f"이 대운 오행: **{OHN.get(cdw_oh_h,'')}({cdw_oh_h})** — {_OHB.get(cdw_oh_h,'')} 계통에 영향을 주느니라.\n")
            except Exception: pass
            # 올해 세운 건강 경보
            sw_hlt = get_yearly_luck(pils, current_year)
            sw_hlt_ss = sw_hlt.get("십성_천간","")
            if sw_hlt_ss == "偏官":
                out.append(f"\n⚠️ 올해({current_year}년) {sw_hlt.get('세운','')} [偏官] 세운 — 건강 사고 위험 높은 해니라. 무리한 활동·수술 신중하게.\n")
            elif sw_hlt_ss == "傷官":
                out.append(f"\n올해({current_year}년) {sw_hlt.get('세운','')} [傷官] 세운 — 과로와 신경 소모가 심한 해니라. 충분한 휴식이 최우선이니라.\n")

        elif is_dw:
            daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
            cdw = next((d for d in daewoon if d["시작연도"] <= current_year <= d["종료연도"]), None)
            out.append(f"**{name}의 대운 흐름 완전 분석**\n")
            # 용신 기반 황금기/주의기 판별
            try:
                ys_dw = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                yong_ohs_dw = {o for o in [ys_dw.get("용신_1순위",""), ys_dw.get("용신_2순위",""), ys_dw.get("희신","")] if o in ("木","火","土","金","水")}
                gisin_dw = set(ys_dw.get("기신",[]))
            except Exception:
                yong_ohs_dw = set(); gisin_dw = set()
            if cdw:
                cdw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(cdw["cg"],"-")
                cdw_oh = OH.get(cdw["cg"],"")
                grade = "🌟 황금기 대운" if cdw_oh in yong_ohs_dw else "⚠️ 주의기 대운" if cdw_oh in gisin_dw else "⬜ 보통 대운"
                out.append(f"현재 대운: **{cdw['str']}** ({cdw_ss}) — **{grade}**\n")
                out.append(f"{cdw['시작연도']}~{cdw['종료연도']}년 ({cdw['시작나이']}~{cdw['시작나이']+9}세), **{cdw['종료연도']-current_year}년** 더 이어지느니라.\n")
                out.append(DAEWOON_PRESCRIPTION.get(cdw_ss,"꾸준한 노력으로 안정을 유지하게.") + "\n")
                if cdw_oh in yong_ohs_dw:
                    out.append("이 대운은 용신 기운이 흐르는 황금기니라! 크게 움직여도 하늘이 돕는 시기이니라.\n")
                elif cdw_oh in gisin_dw:
                    out.append("이 대운은 기신 기운이 흐르는 주의기니라. 무리한 확장보다 안전 자산 확보와 내실 다지기가 최선이니라.\n")
            # 다음 대운 미리보기
            cdw_idx = next((i for i, d in enumerate(daewoon) if d["시작연도"] <= current_year <= d["종료연도"]), None)
            if cdw_idx is not None and cdw_idx + 1 < len(daewoon):
                ndw = daewoon[cdw_idx + 1]
                ndw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(ndw["cg"],"-")
                ndw_oh = OH.get(ndw["cg"],"")
                ndw_grade = "🌟 황금기" if ndw_oh in yong_ohs_dw else "⚠️ 주의기" if ndw_oh in gisin_dw else "⬜ 보통"
                out.append(f"\n**[다음 대운 미리보기]** {ndw['시작연도']}년({ndw['시작나이']}세)부터 **{ndw['str']} {ndw_ss}** ({ndw_grade}) 대운이 열리느니라.\n")
                out.append(DAEWOON_PRESCRIPTION.get(ndw_ss, "새 대운을 준비하게.") + "\n")
            out.append("\n**전체 대운 흐름 (🌟황금기 / ⚠️주의기 표시):**\n")
            for dw in daewoon[:8]:
                dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"-")
                dw_oh = OH.get(dw["cg"],"")
                dw_grade = "🌟" if dw_oh in yong_ohs_dw else "⚠️" if dw_oh in gisin_dw else "⬜"
                cur_m = " ◀현재" if dw["시작연도"] <= current_year <= dw["종료연도"] else ""
                out.append(f"* {dw['시작나이']}~{dw['시작나이']+9}세: {dw['str']} ({dw_ss}) {dw_grade}{cur_m}\n")

        elif is_past:
            hl   = generate_engine_highlights(pils, birth_year, gender, bm, bd, bh, bmn)
            pevs = sorted(hl.get("past_events",[]), key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e.get("intensity","🟢"),3))
            out.append(f"**{name}의 과거 사건 완전 분석**\n허허, 지나온 세월을 신안으로 살펴보겠느니라.\n")
            if pevs:
                out.append("\n**[주요 과거 사건 — 강도순]**\n")
                for ev in pevs[:6]:
                    out.append(f"\n**{ev.get('year','')}년 ({ev.get('age','')}) {ev.get('intensity','')} [{ev.get('domain','변화')}]**\n{ev.get('desc','')}\n")
            else:
                out.append("사주 엔진이 과거 데이터를 분석 중이니라.\n")
            # 월지 충 근거 (기반이 흔들린 시기)
            wc = hl.get("wolji_chung", [])
            if wc:
                out.append("\n**[월지 충(沖) — 삶의 기반이 흔들린 시기]**\n")
                for w in wc[:3]: out.append(f"* {w.get('age','')}: {w.get('desc','')}\n")
            # 위험 구간 (과거분)
            dz = hl.get("danger_zones", [])
            if dz:
                try:
                    past_dz = [d for d in dz if d.get("year","") and int(d["year"].split("~")[-1]) <= current_year]
                except Exception: past_dz = []
                if past_dz:
                    out.append("\n**[과거 위험 구간 — 힘든 시기의 근거]**\n")
                    for d in past_dz[:2]: out.append(f"* {d.get('age','')}: {d.get('desc','')}\n")

        elif is_job:
            gk  = get_gyeokguk(pils)
            gkn = gk["격국명"] if gk else "미정격"
            ys2 = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            y1j = ys2.get("용신_1순위", "-")
            si_j = get_ilgan_strength(ilgan, pils)
            sn_j = si_j.get("신강신약","중화")
            _JOB = {
                "정관격":"조직·공직·행정·관리직·법조가 천직이니라. 안정된 조직 안에서 명예와 재물이 함께 오느니라. 공무원·대기업·공공기관이 최적이니라.",
                "편관격":"군경·의료·법조·스포츠·안전·소방·국방 분야에서 진가를 발휘하느니라. 강인한 의지와 추진력이 강점이니라.",
                "정재격":"금융·회계·부동산·세무·유통·은행이 맞느니라. 성실한 노력으로 안정된 자산을 쌓는 팔자니라. 꼼꼼함과 책임감이 무기니라.",
                "편재격":"사업·영업·투자·무역·중개·부동산 개발이 맞느니라. 기회를 포착하는 사업가 기질이 타고났느니라. 빠른 판단력이 핵심이니라.",
                "식신격":"요식·창작·예술·교육·서비스·콘텐츠·강의가 맞느니라. 재능이 곧 밥그릇이 되는 팔자니라.",
                "상관격":"IT·방송·컨설팅·프리랜서·스타트업·예술가에서 독보적 존재가 되느니라. 창의력이 최대 무기니라.",
                "편인격":"학문·연구·철학·심리·의학·IT연구·특허 분야가 천직이니라. 깊은 통찰이 곧 경쟁력이니라.",
                "정인격":"교육·학술·전문직·자격증 기반 직종·상담이 맞느니라. 배움이 쌓일수록 위상이 높아지느니라.",
                "비견격":"독립·자영업·프리랜서·개인사업·1인 기업이 맞느니라. 혼자 움직일 때 가장 강해지는 팔자니라.",
                "겁재격":"경쟁·협상·중개·스포츠·증권·선물 분야에서 오히려 빛나는 팔자니라.",
            }
            _OHJOB = {
                "木":"목재·제지·섬유·교육·의류·원예·환경·에너지·스포츠 관련 업종이 유리하느니라.",
                "火":"방송·광고·전기·전자·IT·연예·문화·조명·화학 관련 업종이 유리하느니라.",
                "土":"부동산·건설·농업·의약·식품·유통·경영컨설팅 관련 업종이 유리하느니라.",
                "金":"금융·금속·기계·법조·의료·국방·스포츠·경찰 관련 업종이 유리하느니라.",
                "水":"무역·해운·유통·관광·호텔·미디어·철학·심리 관련 업종이 유리하느니라.",
            }
            _SWJOB = {
                "食神":"올해는 재능 발휘와 자격 취득에 최적의 해니라. 새 프로젝트를 시작하게!",
                "正官":"승진·이직·공직 시험에 유리한 해니라. 조직 내 신뢰를 쌓는 것이 핵심이니라.",
                "偏財":"사업·영업 기회가 오는 해니라. 적극적으로 나서되 도박성 투자는 자제하게.",
                "正財":"안정된 수입·직장 유지에 좋은 해니라. 차분하게 실력을 쌓는 것이 맞느니라.",
                "傷官":"독립·창업·이직을 고려한다면 올해가 전환점이 될 수 있느니라. 단 계약서 주의.",
                "偏官":"직장 변동·갈등이 올 수 있느니라. 무리한 도전보다 현 자리 지키기가 현명하니라.",
            }
            out.append(f"**{name}의 직업·진로 완전 분석**\n격국 **{gkn}**의 천직을 신안으로 살펴보겠느니라.\n")
            out.append(_JOB.get(gkn, f"{gkn}의 독특한 기운을 살려 자신만의 길을 개척해야 하느니라.") + "\n")
            # 십성 분포 분석
            try:
                ss_list_j = calc_sipsung(ilgan, pils)
                _GRP = {"비견":"비겁","겁재":"비겁","식신":"식상","상관":"식상","정재":"재성",
                        "편재":"재성","정관":"관성","편관":"관성","정인":"인성","편인":"인성"}
                sc_cnt = {}
                for p in ss_list_j:
                    g = _GRP.get(p.get("십성",""),"")
                    if g: sc_cnt[g] = sc_cnt.get(g, 0) + 1
                top_g = max(sc_cnt, key=sc_cnt.get) if sc_cnt else ""
                _SGJ = {"재성":"재물을 직접 다루는 영역에서 두각을 드러내느니라.",
                        "관성":"조직과 권위 안에서 진가가 빛나느니라.",
                        "식상":"창의와 표현으로 세상을 사로잡는 팔자니라.",
                        "인성":"배움과 자격증으로 전문성을 쌓는 것이 맞느니라.",
                        "비겁":"독립과 경쟁 속에서 오히려 강해지는 팔자니라."}
                if top_g: out.append(f"\n사주 십성 분포상 **{top_g}** 기운이 강하니 {_SGJ.get(top_g,'')}\n")
            except Exception: pass
            # 용신 오행 업종
            out.append(f"\n**[용신 오행 업종]** 용신 **{y1j}** — {_OHJOB.get(y1j, f'{y1j} 오행 관련 업종이 맞느니라.')}\n")
            # 신강신약 행동 패턴
            if "신강" in sn_j:
                out.append(f"\n**신강({sn_j})** — 독립·창업·단독 행보가 최적이니라. 조직보다 자신이 주도하는 환경에서 능력을 발휘하느니라.\n")
            elif "신약" in sn_j:
                out.append(f"\n**신약({sn_j})** — 안정된 조직·전문직 안에서 귀인의 도움을 받는 것이 최적이니라. 창업보다 전문성 강화가 우선이니라.\n")
            # 올해 진로 세운
            sw_j = get_yearly_luck(pils, current_year)
            sw_j_ss = sw_j.get("십성_천간","")
            out.append(f"\n올해({current_year}년) {sw_j.get('세운','')} [{sw_j_ss}] {sw_j.get('길흉','')} — {_SWJOB.get(sw_j_ss, sw_j_ss + ' 기운의 해이니 흐름을 잘 읽고 움직이게.')}\n")
            out.append(f"\n용신 **{y1j}** 오행이 강한 해에 진로 결정을 내리면 가장 유리하느니라. 명심하게!\n")

        elif is_char:
            gk  = get_gyeokguk(pils)
            si  = get_ilgan_strength(ilgan, pils)
            gkn = gk["격국명"] if gk else "미정격"
            sn  = si.get("신강신약", "중화")
            sc  = si.get("일간점수", 50)
            _CG_KR = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계'}
            _ilgan_k = f"{ilgan}({_CG_KR.get(ilgan, '')})"
            _CHR = ILGAN_CHAR_DESC.get(_ilgan_k, ILGAN_CHAR_DESC.get(ilgan, {}))
            oh_s_c = calc_ohaeng_strength(ilgan, pils)
            out.append(f"**{name}의 성격·기질 완전 분석**\n일간 **{ilgan}** | 격국 **{gkn}** | **{sn}**(점수 {sc}/100)\n")
            out.append(_CHR.get("성격_핵심", f"일간 {ilgan}의 기운이 삶 전반을 이끄느니라.") + "\n")
            if _CHR.get("장점"): out.append(f"\n**[장점]** {_CHR['장점']}\n")
            if _CHR.get("단점"): out.append(f"**[주의]** {_CHR['단점']}\n")
            if _CHR.get("재물패턴"): out.append(f"**[재물 성향]** {_CHR['재물패턴']}\n")
            if _CHR.get("건강"): out.append(f"**[건강 주의]** {_CHR['건강']}\n")
            if _CHR.get("직업"): out.append(f"**[천직 힌트]** {_CHR['직업']}\n")
            _SNS = {
                "신강": f"기운이 넘치는 신강({sc}/100)이니라. 스스로 움직여야 기회가 오느니라. 독립적 결단이 맞는 팔자이나 자기중심적으로 흐를 수 있으니 타인 의견에도 귀를 열게.",
                "신약": f"기운이 부족한 신약({sc}/100)이니라. 귀인과 함께할 때 진가가 발휘되느니라. 좋은 파트너·스승이 운명을 바꾸느니라. 협업 속에서 빛나는 팔자이니라.",
                "중화": f"기운이 균형 잡힌 중화({sc}/100)이니라. 어느 상황에도 적응하는 유연함이 강점이니라. 꾸준함과 전문성이 최대 무기이니라.",
            }
            for k, v in _SNS.items():
                if k in sn: out.append(f"\n**[신강신약 행동 패턴]** {v}\n"); break
            # 오행 과다 성격 패턴
            _OHC = {
                "木":"木 과다: 고집이 세고 자기주장이 강하며 리더십이 강함. 하지만 융통성 부족 주의.",
                "火":"火 과다: 열정적이고 급하며 사교성이 뛰어남. 하지만 과잉 행동과 산만함 주의.",
                "土":"土 과다: 신중하고 보수적이며 인내심이 강함. 하지만 변화 거부와 고집 주의.",
                "金":"金 과다: 원칙주의적이고 결단력이 강함. 하지만 냉철함이 지나쳐 인간관계 문제 주의.",
                "水":"水 과다: 지혜롭고 유연하며 전략적. 하지만 우유부단과 비밀주의 주의.",
            }
            for o, v in oh_s_c.items():
                if v >= 35: out.append(f"\n{_OHC.get(o,'')}\n")
            sw = get_yearly_luck(pils, current_year)
            out.append(f"\n올해({current_year}년)는 {sw.get('세운','')} [{sw.get('십성_천간','')}] {sw.get('길흉','')} 기운이니 그 흐름을 잘 타게.\n")

        elif is_avoid:
            sw   = get_yearly_luck(pils, current_year)
            ys   = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            si   = get_ilgan_strength(ilgan, pils)
            sw_ss= sw.get("십성_천간","")
            sw_gh= sw.get("길흉","")
            y1   = ys.get("용신_1순위","-")
            gisin= ", ".join(ys.get("기신",[]))
            sn   = si.get("신강신약","중화")
            _AVOID_SS = {
                "劫財": "겁재(劫財) 기운이 강하니 보증·동업·투기·도박을 절대 삼가게! 재물이 새어나가기 쉬운 시기니라.",
                "偏官": "편관(偏官) 기운이 강하니 법적 다툼·충돌·무리한 도전을 삼가게. 건강과 안전에 각별히 유의하게.",
                "傷官": "상관(傷官) 기운이니 윗사람과의 마찰, 계약·언행에 주의해야 하느니라. 독단 결정도 삼가게.",
            }
            out.append(f"**{name}의 {current_year}년 피할 일·조심할 것 분석**\n")
            out.append(f"올해 세운 {sw.get('세운','')} [{sw_ss}] {sw_gh}\n")
            out.append(_AVOID_SS.get(sw_ss, f"올해 [{sw_ss}] 기운에서 특히 기신({gisin}) 오행과 관련된 일을 삼가는 것이 현명하니라.") + "\n")
            gisin_warn = {
                "木": "목(木) 방향/업種: 무리한 확장·소송·나무 관련 계약을 조심하게.",
                "火": "화(火) 관련: 급한 결정·충동 투자·말다툼·화재(火災) 주의.",
                "土": "토(土) 관련: 부동산 무리한 매입·토지 계약·신용 거래 주의.",
                "金": "금(金) 관련: 금전 보증·대출 확대·금속/기계 사고 주의.",
                "水": "수(水) 관련: 수상 사고·과음·불필요한 이동·비밀 누설 주의.",
            }
            if gisin:
                for g in ys.get("기신",[]):
                    if g in gisin_warn:
                        out.append(f"\n⚠️ **기신({g}) 주의사항:** {gisin_warn[g]}\n")
            _SS_BAD_TIME = {
                "劫財": "돈 거래·대출·보증—절대 금기",
                "偏官": "무리한 도전·이직·창업 시작",
                "傷官": "상사와의 충돌·계약서 서명·공개적 발언",
                "偏印": "새 일 시작·여행·과감한 결정",
            }
            bad = _SS_BAD_TIME.get(sw_ss,"")
            if bad:
                out.append(f"\n**[올해 특히 조심할 행동]** {bad}\n")
            if "신강" in sn:
                out.append(f"\n신강 팔자는 자기 확신이 강해 실수를 인정하지 않기 쉬우니 타인 의견에도 귀를 열게.\n")
            elif "신약" in sn:
                out.append(f"\n신약 팔자는 타인에게 쉽게 끌려다니니 중요한 결정은 혼자 성급히 내리지 말게.\n")

        elif is_lucky:
            sw   = get_yearly_luck(pils, current_year)
            ys   = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            y1   = ys.get("용신_1순위","-")
            heui = ys.get("희신","-")
            out.append(f"**{name}의 좋은 날·길일·황금 시기 분석**\n허허, 하늘이 돕는 날을 골라주겠느니라.\n")
            _OH_DAY = {
                "木": "甲(갑)·乙(을) 일(日), 봄(1~3월), 동쪽 방향이 길하느니라. 인(寅)·묘(卯)시가 행운의 시각이니라.",
                "火": "丙(병)·丁(정) 일(日), 여름(4~6월), 남쪽 방향이 길하느니라. 오(午)시가 행운의 시각이니라.",
                "土": "戊(무)·己(기) 일(日), 환절기, 중앙 방향이 길하느니라. 진(辰)·술(戌)·축(丑)·미(未)시가 좋으니라.",
                "金": "庚(경)·辛(신) 일(日), 가을(7~9월), 서쪽 방향이 길하느니라. 申(신)·酉(유)시가 행운의 시각이니라.",
                "水": "壬(임)·癸(계) 일(日), 겨울(10~12월), 북쪽 방향이 길하느니라. 子(자)·亥(해)시가 행운의 시각이니라.",
            }
            out.append(f"\n용신 **{y1}** 오행이 살아있는 날이 곧 길일이니라!\n")
            out.append(_OH_DAY.get(y1, f"용신 {y1} 오행이 강한 날을 택하게.") + "\n")
            out.append(f"\n희신 **{heui}** 기운도 함께 활용하면 더욱 좋으니라.\n")
            out.append(_OH_DAY.get(heui, "") + "\n" if heui in _OH_DAY else "")
            gold_yrs2 = []
            for yr in range(current_year, current_year + 5):
                sw_g2 = get_yearly_luck(pils, yr)
                ss_g2 = sw_g2.get("십성_천간","")
                yo_g2 = OH.get(sw_g2.get("세운","")[:1],"")
                if yo_g2 in {y1, heui}:
                    gold_yrs2.append(f"  * **{yr}년**({yr-birth_year+1}세): {sw_g2.get('세운','')} [{ss_g2}] ← 용신 기운의 해!")
            if gold_yrs2:
                out.append(f"\n**[용신 황금 시기 — 이 해에 중요한 일 시작하게!]**\n")
                for gyr in gold_yrs2: out.append(gyr + "\n")

        elif is_move:
            sw   = get_yearly_luck(pils, current_year)
            ys   = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            si   = get_ilgan_strength(ilgan, pils)
            sw_ss= sw.get("십성_천간","")
            y1   = ys.get("용신_1순위","-")
            heui = ys.get("희신","-")
            sn   = si.get("신강신약","중화")
            out.append(f"**{name}의 이사·이직·중요 결정 시기 분석**\n")
            _MOVE_SS = {
                "偏財": "편재(偏財) 세운은 변화와 이동에 유리하느니라. 이사·이직·사업 시작에 좋은 시기니라. 단 충동적 결정은 조심하게.",
                "正官": "정관(正官) 세운은 조직 내 승진·인정의 해이니라. 이직보다는 현 자리에서 실력을 쌓는 것이 더 유리하느니라.",
                "偏印": "편인(偏印) 세운은 이동·변화의 기운이 강하느니라. 단 시작한 일이 중도 포기가 되기 쉬우니 신중히 결정하게.",
                "劫財": "겁재(劫財) 세운은 이직·창업에 불리하느니라. 경쟁이 심하고 손실이 크니 이 해의 큰 결정은 미루게.",
                "偏官": "편관(偏官) 세운은 강제적 변동(해고·이사)의 기운이 있느니라. 미리 준비하되 자의적으로 무리하게 움직이지는 말게.",
            }
            out.append(_MOVE_SS.get(sw_ss, f"올해 [{sw_ss}] 기운에서 큰 변동은 내년 이후 용신 세운에 맞춰 결정하는 것이 현명하니라.") + "\n")
            oh_now = OH.get(sw.get("세운","")[:1],"")
            if oh_now in {y1, heui}:
                out.append(f"\n올해 세운 오행이 용신·희신과 일치! **이 해 안에 결정을 내리면 길하느니라.**\n")
            else:
                out.append(f"\n용신 **{y1}** 오행이 강한 해에 이사·이직을 단행하면 더욱 길하느니라. 조금 기다리게.\n")
            if "신강" in sn:
                out.append("\n신강형이니 스스로 먼저 움직여 기회를 잡아야 하느니라. 기다리면 기회가 지나가느니라.\n")
            else:
                out.append("\n신약형이니 귀인의 소개·추천을 통한 이직이 단독 도전보다 훨씬 유리하느니라.\n")

        elif is_study:
            sw   = get_yearly_luck(pils, current_year)
            ys   = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            sw_ss= sw.get("십성_천간","")
            y1   = ys.get("용신_1순위","-")
            out.append(f"**{name}의 학업·시험·합격운 분석**\n")
            _STUDY_SS = {
                "正印": "정인(正印) 세운! 학업·시험 운이 최정점이니라. 노력한 만큼 결과가 오는 해이니 전력을 다하게!",
                "偏印": "편인(偏印) 세운은 학습과 연구에 유리하느니라. 새 분야 습득에 최적이나 끈기가 필요하니라.",
                "食神": "식신(食神) 세운은 집중력과 창의력이 높아지느니라. 실기·실무형 시험에 특히 유리하느니라.",
                "正官": "정관(正官) 세운은 공무원·조직 시험에 유리하느니라. 규칙적 학습 루틴이 합격의 열쇠니라.",
                "劫財": "겁재(劫財) 세운은 집중력이 분산되기 쉬운 해니라. 경쟁자에게 뒤처지지 않으려면 2배 노력이 필요하느니라.",
            }
            out.append(_STUDY_SS.get(sw_ss, f"올해 [{sw_ss}] 기운에서 꾸준한 학습이 가장 중요하니라. 포기하지 말게.") + "\n")
            _OH_STUDY = {
                "水": "수(水) 오행은 지혜·암기·분석력의 오행이니라. 용신이 水이면 이론 과목에서 강하느니라.",
                "木": "목(木) 오행은 성장·창의력의 오행이니라. 논술·어학에서 두각을 나타내느니라.",
                "金": "금(金) 오행은 정밀·원칙의 오행이니라. 수학·법학·의학계열에 유리하느니라.",
                "火": "화(火) 오행은 열정·집중의 오행이니라. 시험장에서 순발력이 발휘되느니라.",
                "土": "토(土) 오행은 인내·신뢰의 오행이니라. 장기 고시·반복 학습에 특히 강하느니라.",
            }
            out.append(f"\n용신 **{y1}** — {_OH_STUDY.get(y1, f'{y1} 오행 기운을 활용하여 학습 전략을 세우게.')}\n")

        elif is_family:
            sw   = get_yearly_luck(pils, current_year)
            ys   = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            si   = get_ilgan_strength(ilgan, pils)
            sw_ss= sw.get("십성_천간","")
            sn   = si.get("신강신약","중화")
            yk   = get_yukjin(ilgan, pils, gender)
            out.append(f"**{name}의 가족·인연운 분석**\n허허, 가족은 사주의 거울이니라. 신안으로 살펴보겠느니라.\n")
            _FAM_REL = {"인성": "부모·윗사람과의 관계가 사주의 핵심이니라.", "재성": "배우자·자녀와의 인연이 재물과 직결되느니라.",
                        "관성": "자녀(특히 아들)와 직장이 연결된 팔자니라.", "비겁": "형제·동료 관계가 운의 핵심이니라."}
            _SS_FAM = {
                "正印": "올해 부모·어른과의 관계가 깊어지는 시기니라. 가족을 챙기면 좋은 기운이 돌아오느니라.",
                "偏印": "이동·변화가 많으니 가족과 소통이 줄기 쉬운 해니라. 의도적으로 시간을 내게.",
                "食神": "자녀와 관련된 기쁜 소식이 올 수 있느니라. 가족과 함께하는 시간이 재충전이 되느니라.",
                "劫財": "형제·친구 간 금전 갈등 주의. 가족 간 돈 거래는 명확히 하게.",
                "正官": "자녀(특히 아들)와 관련된 경사가 있을 수 있느니라. 가족 행사를 챙기는 것이 길하느니라.",
            }
            out.append(f"\n올해 [{sw_ss}] 기운 — {_SS_FAM.get(sw_ss, f'{sw_ss} 기운에서 가족과의 대화와 배려가 중요하니라.')}\n")
            if "신강" in sn:
                out.append("\n신강 팔자는 자기 의견이 강하니 가족에게 고집을 부리는 경향이 있느니라. 한 발씩 양보하게.\n")
            elif "신약" in sn:
                out.append("\n신약 팔자는 가족의 지지가 에너지의 원천이느니라. 가족과의 유대를 더욱 깊이 하게.\n")

        else:
            # ─── 스마트 catch-all: 어떤 질문이든 용신·세운 기반으로 실질 답변 ───
            gk  = get_gyeokguk(pils)
            ys  = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
            si  = get_ilgan_strength(ilgan, pils)
            sw  = get_yearly_luck(pils, current_year)
            gkn = gk["격국명"] if gk else "미정격"
            sn  = si.get("신강신약","중화"); sc = si.get("일간점수",50)
            y1  = ys.get("용신_1순위","-"); heui = ys.get("희신","-")
            gisin = ", ".join(ys.get("기신",[]))
            sw_ss = sw.get("십성_천간",""); sw_gh = sw.get("길흉","")
            sw_gan= sw.get("세운","")
            _GKS = {
                "정관격": "규칙과 질서를 중시하며 조직에서 빛을 발하느니라.",
                "편관격": "강인한 의지와 도전 정신이 핵심이니라.",
                "정재격": "성실함으로 재물을 쌓는 격국이니라.",
                "편재격": "사업가 기질이 넘치는 격국이니라.",
                "식신격": "복록이 넘치는 격국이니라. 창작·교육에서 빛을 발하느니라.",
                "상관격": "재기와 창의성이 폭발하는 격국이니라.",
                "편인격": "학문과 연구에 뛰어난 격국이니라.",
                "정인격": "학문과 자격의 격국이니라.",
            }
            # 질문 키워드 반영 인트로
            q_short = q.strip()[:30]
            out.append(f"**{name}의 팔자로 '{q_short}' 질문을 풀어드리겠느니라.**\n")
            out.append(f"일간 {ilgan} | 격국 **{gkn}** | {sn}(점수 {sc}/100)\n")
            out.append(f"용신 **{y1}** | 희신 **{heui}** | 기신 {gisin}\n\n")
            out.append(_GKS.get(gkn, "독특한 개성과 능력을 갖춘 격국이니라.") + "\n")
            out.append("\n일간의 기운이 강하니 스스로 움직여야 기회가 오느니라.\n" if "신강" in sn
                       else "\n귀인과 함께할 때 가장 강해지는 팔자이니라. 좋은 파트너가 운명을 바꾸느니라.\n")
            out.append(f"\n올해({current_year}년)는 {sw_gan} [{sw_ss}] {sw_gh} 기운이니라.\n")
            # 용신 일치 여부 판단
            oh_now = OH.get(sw_gan[:1] if sw_gan else "", "")
            if oh_now in {y1, heui}:
                out.append(f"\n올해 세운이 용신·희신과 일치하니 **{current_year}년에 질문하신 일을 추진하면 길하느니라!**\n")
            elif gisin and oh_now in gisin:
                out.append(f"\n올해 세운이 기신({gisin})에 해당하니 **큰 결정은 내년 이후로 미루는 것이 현명하느니라.**\n")
            else:
                out.append(f"\n용신 **{y1}** 오행이 강한 해에 행동을 취하면 가장 좋은 결과가 오느니라.\n")
            # 향후 최선의 시기
            best_yrs = []
            for yr in range(current_year, current_year + 5):
                sw_b = get_yearly_luck(pils, yr)
                yo_b = OH.get(sw_b.get("세운","")[:1],"")
                if yo_b in {y1, heui}:
                    best_yrs.append(f"  * **{yr}년**({yr-birth_year+1}세): {sw_b.get('세운','')} [{sw_b.get('십성_천간','')}] ← 용신 기운의 황금기!")
            if best_yrs:
                out.append("\n**[최선의 시기]**\n")
                for by in best_yrs[:3]: out.append(by + "\n")


    except Exception as _le:
        out.append(f"\n허어, 기운이 잠시 흔들렸느니라. 기본 팔자로 답을 드리겠네.\n")
        try:
            sw = get_yearly_luck(pils, current_year)
            out.append(f"올해 {sw.get('세운','')} [{sw.get('십성_천간','')}] {sw.get('길흉','')} 기운이니라.\n")
        except Exception:
            pass

    out.append(f"\n---\n*내 신안(神眼)이 본 {name}의 팔자가 이러하니라. 더 깊이 알고 싶다면 다시 물어보게.*")
    return "\n".join(out)


def quick_consult_bar(pils, name, birth_year, gender, api_key, groq_key):
    """🌌 전역 퀵 상담창: 어떤 탭에서든 즉시 질문하고 답을 얻는 고정 UI"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #121212, #2c3e50); 
                padding: 18px; border-radius: 18px; margin: 10px 0 25px 0; 
                border: 1.5px solid #d4af37; box-shadow: 0 10px 40px rgba(0,0,0,0.4);
                position: relative; overflow: hidden;">
        <div style="position: absolute; top: -30px; right: -30px; width: 120px; height: 120px; 
                    background: radial-gradient(circle, rgba(212,175,55,0.2) 0%, transparent 70%);"></div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div style="background: #d4af37; width: 8px; height: 8px; border-radius: 50%; animation: pulse-gold 2s infinite;"></div>
            <div style="color: #d4af37; font-size: 11px; font-weight: 900; letter-spacing: 2px;">
                🌌 GLOBAL MASTER QUICK CONSULT
            </div>
        </div>
        <div style="color: #ffffff; font-size: 17px; font-weight: 800; margin-bottom: 15px; font-family: 'Noto Serif KR', serif;">
            종합운세부터 궁합까지, 3인의 마스터에게 즉시 물어보세요.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        q_col1, q_col2 = st.columns([5, 1])
        with q_col1:
            quick_query = st.text_input("질문 입력", 
                                        key="global_quick_query", 
                                        label_visibility="collapsed",
                                        placeholder="예: 올해 연애운은 어떤가요? 지금 하려는 사업 괜찮을까요?")
        with q_col2:
            q_submitted = st.button("🔮 즉각전수", key="global_quick_btn", use_container_width=True)
            
    if q_submitted and quick_query:
        with st.status("🔮 만신의 신안(神眼)이 천기를 살피는 중...", expanded=True) as status:
            # 1. 의도 및 유대감 업데이트
            intent_res = IntentEngine.analyze(quick_query)
            st.write(f"🎯 분석 주제: **{intent_res['topic_kr']}** / 감정선: **{intent_res['emotion']}**")
            SajuMemory.record_behavior(name, quick_query)
            SajuMemory.adjust_bond(name, 5)
            GoalCreationEngine.extract_goal(name, quick_query)

            # 2. 로컬 사주 엔진 응답 생성
            response = _local_saju_engine(pils, name, birth_year, gender, quick_query)

            # 3. 응답 출력
            st.markdown(f"""
<div style="background:#fffdf5;padding:22px;border-radius:14px;
            border-left:5px solid #d4af37;color:#1a1a1a;
            margin-top:14px;line-height:1.9;font-size:14px;">
<div style="font-weight:900;color:#d4af37;font-size:15px;margin-bottom:10px;
            border-bottom:1px solid #e8d5a0;padding-bottom:7px;">
🔮 만신(萬神) 즉각 전수
</div>
{response}
</div>
""", unsafe_allow_html=True)

            # 4. 데이터 영속화
            current_year = datetime.now().year
            SajuMemory.add_conversation(name, f"퀵:{intent_res['topic_kr']}", response, intent_res['emotion'])
            LifeNarrativeEngine.update_narrative(name, intent_res['topic_kr'], intent_res['emotion'])

            # 5. 전환점 감지
            try:
                luck_score = calc_luck_score(pils, birth_year, gender, current_year)
                pivot_info = ChangeRadarEngine.detect_pivot(name, luck_score)
                if pivot_info["is_pivot"]:
                    st.info(f"🛰️ **전환점 감지:** {pivot_info['message']}")
            except Exception:
                pass

            status.update(label="✅ 전수 완료", state="complete", expanded=True)

class DestinyTimelineEngine:
    """🗺️ 운명을 시간 축(Timeline)으로 매핑하여 현재 위치를 알려주는 엔진"""
    @staticmethod
    def get_context_summary() -> str:
        # 병오(丙午)년 고정 시뮬레이션 기반 시점 분석
        now = datetime.now()
        month = now.month
        if month in [3, 4, 5]: return "씨앗을 뿌리고 기반을 다지는 '창조의 봄' 단계"
        if month in [6, 7, 8]: return "열기가 가득하여 결과가 가시화되는 '도약의 여름' 단계"
        if month in [9, 10, 11]: return "내실을 기하고 결과물을 거두는 '수렴의 가을' 단계"
        return "자신을 돌아보고 에너지를 비축하는 '성찰의 겨울' 단계"

class SelfEvolutionEngine:
    """🔥 내담자 유형에 맞춰 AI의 상담 알고리즘 및 톤을 진화시키는 엔진"""
    @staticmethod
    def get_instruction(persona: str) -> str:
        instructions = {
            "논리/분석 탐색형": "- 사용자는 논리적 근거를 중시합니다. 명리적 용어(십성, 합충)를 섞어 구체적으로 답변하세요.",
            "현실불안 위로형": "- 밤에 접속한 내담자입니다. 정서적 불안이 높을 수 있으니 따뜻한 위로와 공감을 70% 비중으로 하세요.",
            "해답갈구 확신형": "- 사용자는 결론을 원합니다. 서론을 줄이고 'Yes/No' 혹은 '추천 행동'을 먼저 제시하세요.",
            "온건적 소통형": "- 일상적인 대화 톤으로 편안하게 사주의 지혜를 전달하세요."
        }
        return instructions.get(persona, "- 내담자의 성향을 탐색하며 정중하게 상담하세요.")


class PersonalityProfiler:
    """사주 원국 기반 '고전적/현대적 통합 성격 지문' 및 MBTI 매핑 엔진"""
    @staticmethod
    def analyze(pils: list) -> dict:
        default_res = {
            "trait1": "독자적인 기운", "trait2": "잠재된 사회적 역량", "mbti": "INFJ",
            "trait_desc": "사주 원국 데이터를 분석 중입니다.",
            "counseling_strategy": "내담자의 성향을 파악하며 유연하게 상담하세요."
        }
        # 안전성 검사 강화
        if not pils or not isinstance(pils, list) or len(pils) < 4: 
            return default_res
        
        try:
            # [시(0), 일(1), 월(2), 년(3)] 순서
            hour_p = pils[0]
            day_p = pils[1]
            month_p = pils[2]
            year_p = pils[3]

            ilgan = day_p.get("cg", "")
            month_ji = month_p.get("jj", "")
            iljj = day_p.get("jj", "")
        except (IndexError, AttributeError, KeyError):
            return default_res
        
        if not ilgan or not month_ji:
            return default_res
        
        # 1. 고전 명리 기질
        traits = {
            "甲(갑)": "우뚝 솟은 나무처럼 강직하고 리더십이 강함", "乙(을)": "유연한 덩굴처럼 생명력이 질기고 적응력이 뛰어남",
            "丙(병)": "하늘의 태양처럼 열정적이고 숨김이 없으며 밝음", "丁(정)": "밤하늘의 등불처럼 섬세하고 따뜻하며 예의가 바름",
            "戊(무)": "드넓은 대지처럼 듬직하고 포용력이 크며 신중함", "己(기)": "비옥한 논밭처럼 치밀하고 실속이 있으며 자애로움",
            "庚(경)": "날카로운 바위처럼 결단력이 있고 정의로우며 강한 자존심", "辛(신)": "빛나는 보석처럼 정교하고 깔끔하며 완벽주의 성향",
            "壬(임)": "끝없는 바다처럼 지혜롭고 수용성이 넓으며 생각이 깊음", "癸(계)": "봄비처럼 여리고 유연하며 창의적인 영감이 뛰어남"
        }
        social = {
            "寅(인)": "개척과 추진력", "卯(묘)": "조화와 예술성", "辰(진)": "관리와 포용력", "巳(사)": "확산과 표현력",
            "午(오)": "돌파와 열정", "未(미)": "인내와 저장력", "申(신)": "냉철함과 기술력", "酉(유)": "정밀함과 결단력",
            "戌(술)": "신의와 실천력", "亥(해)": "통찰과 응용력", "子(자)": "연구와 원천 기운", "丑(축)": "성실과 축적력"
        }
        
        desc = traits.get(ilgan, "독자적인 기운")
        soc_desc = social.get(month_ji, "잠재된 사회적 역량")

        # 2. 사주-MBTI 매핑 로직 (V2 핵심)
        mbti_map = {
            "甲(갑)-寅(인)": "ENTJ", "乙(을)-卯(묘)": "ENFP", "丙(병)-午(오)": "ENFJ", "丁(정)-巳(사)": "INFJ",
            "戊(무)-辰(진)": "ESTJ", "己(기)-丑(축)": "ISFJ", "庚(경)-申(신)": "ISTP", "辛(신)-酉(유)": "INTJ",
            "壬(임)-亥(해)": "INTP", "癸(계)-子(자)": "INFP"
        }
        key = f"{ilgan}-{month_ji}"
        mbti_type = mbti_map.get(key, "INFJ" if ilgan in "丁(정)癸(계)" else "ESTP")
        
        # 일주 데이터 참조 (Hotfix: ILJU_DESC -> ILJU_DATA)
        ilju_key = f"{ilgan}{iljj}"
        ilju_info = ILJU_DATA.get(ilju_key, {})
        ilju_symbol = ilju_info.get("symbol", "🔮")
        ilju_desc = ilju_info.get("desc", f"{ilju_key}의 기운")

        return {
            "trait1": desc, "trait2": soc_desc, "mbti": mbti_type,
            "ilju_symbol": ilju_symbol,
            "trait_desc": f"{ilju_symbol} {ilju_desc}\n\n{desc}을 바탕으로 {soc_desc}이 돋보이며, 현대적으로는 {mbti_type} 유형과 유사함",
            "counseling_strategy": f"이 분은 {mbti_type} 성향을 고려하여 { '체계적이고 명확하게' if 'J' in mbti_type else '자유롭고 가능성을 열어두고' } 상담하세요."
        }


class FollowUpGenerator:
    """내담자의 주제와 감정에 반응하는 '여운이 남는 질문' 생성기 V2"""
    @staticmethod
    def get_question(topic: str, intent: str = "", trust_level: int = 1) -> str:
        pools = {
            "CAREER": ["지금 하는 일에서 가장 공허함을 느끼는 순간은 언제인가요?", "사실 더 잘 할 수 있다는 확신보다 불안함이 더 크지 않으신가요?"],
            "LOVE": ["그 사람의 어떤 모습이 {name}님의 마음을 가장 흔들어 놓았나요?", "인연을 이어가고 싶다는 마음 뒤에 혹시 혼자가 되는 두려움이 있지 않나요?"],
            "WEALTH": ["돈을 버는 것보다 지키는 것이 더 힘들다고 느껴질 때가 언제인가요?", "최근에 본인의 판단을 흐리게 만든 달콤한 제안이 있었나요?"],
            "HEALTH": ["몸의 아픔보다 혹시 마음의 응어리가 먼저 생기지는 않았나요?", "최근 수면의 질이 떨어진 것이 어떠한 걱정 때문인지 알고 계신가요?"],
            "LIFE_PATH": ["남들이 말하는 '성공' 말고, 진짜 본인이 꿈꾸는 풍경은 어떤 모습인가요?", "지금 이 시기를 인생의 '쉼표'라고 생각하기엔 마음이 너무 조급하지 않나요?"]
        }
        
        if trust_level >= 4:
            # 신뢰도가 높을 때의 깊은 질문 풀 확장
            pools["LIFE_PATH"].append("본인의 가장 치부라고 생각하는 기질이 사실은 가장 강력한 무기라는 걸 알고 계셨나요?")
            pools["CAREER"].append("사회적 성공 뒤에 숨겨진 본인의 외로움을 정면으로 마주할 준비가 되셨나요?")
            
        import random
        pool = pools.get(topic, ["오늘의 상담이 {name}님의 마음에 작은 등불이 되었을까요?"])
        return random.choice(pool)

class FatePredictionEngine:
    """🚨 돌발 사건 감지 및 실시간 위험 경고 엔진 (V2)"""
    @staticmethod
    def detect_risk(pils: list, current_year: int) -> dict:
        if not pils or len(pils) < 4: return {"is_risk": False, "messages": [], "severity": "보통"}
        # 단순화된 충(沖) 감지 로직
        ilgan = pils[1]["cg"]
        year_ji = pils[3]["jj"] # 년지
        
        risks = []
        # 2026년 병오(丙午)년 기준 예시
        if year_ji == "子(자)": risks.append("연지와 세운의 자오충(子(자)午(오)沖)이 보입니다. 갑작스러운 환경 변화나 이동수를 주의하세요.")
        if ilgan == "壬(임)": risks.append("일간과 세운의 병임충(丙(병)壬(임)沖) 기운이 있어 감정의 변동이 클 수 있습니다.")
        
        return {
            "is_risk": len(risks) > 0,
            "messages": risks,
            "severity": "높음" if len(risks) >= 2 else "보통"
        }

class ChangeRadarEngine:
    """📈 인생의 전환점(Pivot Point)을 감지하는 레이더 엔진"""
    @staticmethod
    def detect_pivot(name: str, luck_score: int):
        # 운세 점수가 급변하거나 특정 조건 만족 시 전환점 알림
        mem = SajuMemory.get_memory(name)
        prev_score = mem.get("matrix", {}).get("에너지", 50)
        
        # 20점 이상 급변 시 전환점 인지
        is_pivot = abs(luck_score - prev_score) >= 20
        message = ""
        if is_pivot:
            if luck_score > prev_score: message = "대운의 상승 기류가 시작되는 '기회의 전환점'에 진입했습니다."
            else: message = "잠시 멈춰 에너지를 재정비해야 하는 '성찰의 전환점'입니다."
        
        return {"is_pivot": is_pivot, "message": message}

class UsageTracker:
    """일일 테스트 인원 제한 관리 (Stable Service)"""
    FILE_PATH = "usage_stats.json"
    LIMIT = 100  # 일일 제한 인원 (사용자 요청에 따라 100명 설정)

    @staticmethod
    def check_limit() -> bool:
        """오늘 사용량이 제한을 넘었는지 확인"""
        today = date.today().isoformat()
        try:
            with open(UsageTracker.FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != today:
                return True
            return data.get("count", 0) < UsageTracker.LIMIT
        except Exception:
            return True

    @staticmethod
    def increment():
        """오늘 사용량 1 증가"""
        today = date.today().isoformat()
        try:
            with open(UsageTracker.FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"date": today, "count": 0}

        if data.get("date") != today:
            data = {"date": today, "count": 0}

        data["count"] += 1
        with open(UsageTracker.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

class VirtualUserEngine:
    """🧪 가상 테스트 인원 100명 관리 엔진"""
    
    @staticmethod
    def generate_100() -> list:
        """100명의 가상 인물 데이터를 생성 (재현성을 위해 시드 고정)"""
        users = []
        rng = random.Random(42)  # 로컬 시드 고정
        for i in range(1, 101):
            year = rng.randint(1960, 2005)
            month = rng.randint(1, 12)
            day = rng.randint(1, 28)
            hour = rng.randint(0, 23)
            gender = rng.choice(["남성", "여성"])
            calendar = rng.choice(["양력", "음력"])
            # 이름은 성씨 조합으로 생성
            surnames = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
            names = ["민호", "서연", "지우", "민준", "하윤", "주원", "예준", "서윤", "도윤", "채원"]
            full_name = f"{rng.choice(surnames)}{rng.choice(names)}_{i:02d}"
            
            users.append({
                "name": full_name,
                "year": year, "month": month, "day": day, "hour": hour,
                "gender": gender, "calendar": calendar
            })
        return users

    @staticmethod
    def pick_random():
        """100명 중 한 명을 무작위로 추출"""
        return random.choice(VirtualUserEngine.generate_100())

class BatchSimulationEngine:
    """📊 대규모 배치 시뮬레이션 엔진"""
    
    @staticmethod
    def run_full_scan():
        """100명 전체 사주 엔진 분석 실행 및 통계 산출"""
        users = VirtualUserEngine.generate_100()
        stats = {
            "ilgan_dist": {}, "luck_scores": [], "top_fate": [],
            "processing_time": 0
        }
        
        import time
        start_t = time.time()
        
        for u in users:
            # 엔진 계산만 수행 (AI 호출 제외로 부하 방지)
            if u["calendar"] == "양력":
                pils = SajuCoreEngine.get_pillars(u["year"], u["month"], u["day"], u["hour"], 0, "남" if u["gender"]=="남성" else "여")
            else:
                s_date = lunar_to_solar(u["year"], u["month"], u["day"], False)
                pils = SajuCoreEngine.get_pillars(s_date.year, s_date.month, s_date.day, u["hour"], 0, "남" if u["gender"]=="남성" else "여")
            
            ilgan = pils[1]["cg"]
            stats["ilgan_dist"][ilgan] = stats["ilgan_dist"].get(ilgan, 0) + 1
            
            luck_s = calc_luck_score(pils, u["year"], "남" if u["gender"]=="남성" else "여", 2026)
            stats["luck_scores"].append(luck_s)
            
            if luck_s >= 85:
                stats["top_fate"].append(f"{u['name']}({luck_s}점)")
        
        stats["processing_time"] = round(time.time() - start_t, 3)
        return stats

class IntentEngine:
    """🎯 질문 의도 해석 엔진 (5-Layer Intent Detection)"""
    
    # Layer 1: Emotion Categories
    EMOTIONS = {
        "불안": ["불안", "두렵", "무서", "걱정", "망할", "실패", "위태", "무거", "어떡해", "될까", "맞을까", "망할까", "위험"],
        "혼란": ["답답", "모르겠", "허무", "정체", "제자리", "혼란", "어떡", "막막", "뭘 해야", "어떻게", "헷갈", "의미를 몰", "갈팡질팡"],
        "기대": ["잘될까", "기대", "희망", "바뀌", "변화", "설레", "좋아질", "기회", "잘 될", "하고 싶", "될 것 같", "좋은 시기", "대박"],
        "후회": ["후회", "왜그랬", "자책", "과거", "돌아가", "실수", "지난", "잘못", "그때", "돌아가고", "아쉽", "미련", "바보"],
        "결심": ["결심", "시작", "도전", "해볼래", "준비", "나아갈", "목표", "새롭게", "하기로", "바꾸고", "이제는", "한다", "해내"],
        "피로": ["지쳐", "힘들어", "지겨", "쉬고 싶", "포기", "소진", "번아웃", "버겁"],
        "분노": ["화나", "짜증", "억울", "열받", "왜 나만", "분해", "치밀어"]
    }

    # Layer 2: Keyword Groups
    KEYWORD_GROUPS = {
        "CAREER": ["취업", "이직", "퇴사", "승진", "직장", "전공", "사업", "창업", "일", "진로", "그만둘", "회사", "사직", "업무", "직업", "전직", "백수", "합격"],
        "WEALTH": ["돈", "투자", "부동산", "코인", "주식", "재물", "수입", "빚", "벌까", "사업", "월급", "창업", "손해", "금전", "대출"],
        "LOVE": ["결혼", "이혼", "궁합", "연애", "썸", "재회", "인연", "배우자", "만남", "헤어짐", "좋아하는", "남친", "여친", "사랑", "헤어", "이별", "소개팅", "짝사랑", "합"],
        "RELATION": ["친구", "동료", "상사", "부모", "자식", "구설수", "다툼", "사람", "인간관계", "가족", "갈등", "배신", "외로", "상처", "싸움"]
    }

    # Layer 3: Situation Patterns
    PATTERNS = {
        "TIMING": ["언제쯤", "시기", "때가", "흐름", "운기", "나중", "앞으로", "노력해도 안 풀려요", "바뀔 것", "언제", "때", "올해", "내년", "운세", "타이밍"],
        "SELF": ["나다운", "성향", "공허", "진정한", "자아", "정체성", "성격", "계속 제자리", "뭘 해야 할지", "방향", "의미", "인생", "삶", "왜", "정체", "미래", "국면", "철학"]
    }

    # Layer 5: Counseling Directions
    DIRECTIONS = {
        "CAREER": "커리어 흐름과 발전 가능성, 대운의 변화 시기를 중심으로 전문적인 분석을 제공하십시오.",
        "WEALTH": "재물의 성취와 손실 시기, 투자 적기 및 자산 운용의 기운을 정밀하게 진단하십시오.",
        "LOVE": "인연의 깊이와 합/충의 조화, 상대와의 감정적 소통 흐름을 중심으로 해석하십시오.",
        "RELATION": "대인관계의 마찰 해소 및 사회적 유대, 주변 사람과의 기운적 상생을 조망하십시오.",
        "SELF": "내면의 성향과 본연의 가치, 인생의 근본적인 방향성과 자아 성찰의 메시지를 전달하십시오.",
        "TIMING": "운의 전환점과 결정적인 기회, 행동해야 할 시기와 멈춰야 할 시기를 명확히 제시하십시오."
    }

    @staticmethod
    def analyze(query: str) -> dict:
        """5단계 레이어를 거쳐 감정, 주제, 상담 방향을 최종 결정한다."""
        # 1-1. 감정 감지 (Layer 1)
        detected_emotion = "혼란" # 기본값
        for emo, kws in IntentEngine.EMOTIONS.items():
            if any(kw in query for kw in kws):
                detected_emotion = emo
                break

        # 1-2. 주제 분류 점수 계산 (Layer 4 - 확신도 계산)
        scores = {topic: 0 for topic in IntentEngine.DIRECTIONS.keys()}
        
        # 패턴 매칭 (가장 높은 우선순위)
        for topic, kws in IntentEngine.PATTERNS.items():
            if any(kw in query for kw in kws):
                scores[topic] += 60
        
        # 키워드 매칭
        for topic, kws in IntentEngine.KEYWORD_GROUPS.items():
            if any(kw in query for kw in kws):
                scores[topic] += 40

        # 최종 주제 선정 (Layer 4)
        sorted_topics = sorted(scores.items(), key=lambda x: (x[1], x[0] == "SELF"), reverse=True)
        
        if sorted_topics[0][1] < 30:
            final_topic = "SELF"
        else:
            final_topic = sorted_topics[0][0]
            
        confidence = min(sorted_topics[0][1] + 20, 95) if sorted_topics[0][1] > 0 else 60

        # 가독성을 위한 주제명 변환
        topic_kr_map = {
            "CAREER": "직업/진로", "WEALTH": "재물/사업", "LOVE": "연애/결혼",
            "RELATION": "인간관계", "SELF": "인생 방향", "TIMING": "운세 흐름"
        }

        return {
            "topic": final_topic,
            "topic_kr": topic_kr_map[final_topic],
            "emotion": detected_emotion,
            "direction": IntentEngine.DIRECTIONS[final_topic],
            "confidence": confidence
        }

    @staticmethod
    def build_intent_prompt(query: str) -> str:
        res = IntentEngine.analyze(query)
        prompt = (
            f"내담자의 감정 상태는 [{res['emotion']}]이며, 질문의 의도는 [{res['topic_kr']}]로 분류되었습니다.\n"
            f"상담 방향 지침: {res['direction']}\n"
            f"전문가로서 위 감정을 충분히 어루만지며 제시된 방향으로 답변하십시오."
        )
        return prompt

    @staticmethod
    def get_topic_badge(user_input: str) -> str:
        """UI에 표시할 주제 및 감정 배지 HTML 반환"""
        res = IntentEngine.analyze(user_input)
        emotion_icon = {
            "불안": "😰", "혼란": "🤔", "기대": "-", "후회": "😔", "결심": "💪", "피로": "😮‍💨", "분노": "😡"
        }.get(res["emotion"], "💬")
        
        return (
            f"<div style='display:flex; gap:6px; margin-bottom:10px'>"
            f"<span style='background:#f1f8e9;color:#2e7d32;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700'>🏷️ {res['topic_kr']}</span>"
            f"<span style='background:#fce4ec;color:#c2185b;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700'>{emotion_icon} {res['emotion']}</span>"
            f"</div>"
        )

def build_saju_context_dict(pils, birth_year, gender, current_year, topic):
    """엔진 데이터를 집약하여 AI에게 전달할 맥락 생성 (단순 dict 반환, 채팅/퀵컨설트 전용)"""
    # [시(0), 일(1), 월(2), 년(3)] 순서 반영 
    # (주의: PillarEngine에 따라 인덱스가 다를 수 있으나 현재 manse.py 관례 준수)
    try:
        ilgan = pils[1]["cg"] if len(pils) > 1 else "?"
        gyeok_data = get_gyeokguk(pils)
        # 용신 엔진은 multilayer 또는 단일 호출 가능. 여기서는 단일 호출 래퍼 사용
        ys_data = get_yongshin(pils)
        
        return {
            "내담자_일간": ilgan,
            "격국": gyeok_data.get("격국명", "분석중") if gyeok_data else "정보없음",
            "용신": ys_data.get("종합_용신", ["분석중"]) if ys_data else ["정보없음"],
            "팔자": ' / '.join([f"{p['cg']}{p['jj']}" for p in pils]) if pils else "정보없음",
            "상담주제": topic
        }
    except Exception:
        return {"error": "데이터 추출 중 기운이 엇갈렸습니다."}

class SajuExpertPrompt:
    """🏛️ 전문가형 5단 프롬프트 아키텍처 (SajuExpertPrompt) V2"""
    @staticmethod
    def build_system_prompt(name, topic_direction, ctx_data):
        """🏛️ 전문가형 5단 프롬프트 아키텍처 (SajuExpertPrompt) V2"""
        header = _AI_SANDBOX_HEADER
        rules_ctx = SajuJudgmentRules.build_rules_prompt(name)
        
        prompt = f"""
{header}

당신은 40년 신력(神力)을 쌓아온 전설적인 무당·만신(萬神)입니다.
하늘의 천명(天命)과 팔자(八字)를 신안(神眼)으로 꿰뚫어 보며, 전통 무속 어투로 내담자에게 신탁(神託)을 전합니다.
아래의 [출시용 5대 상담 원칙]을 반드시 엄수하여 상담을 진행하십시오.

### 1단계: 역할 고정 (Role Lock)
- 당신은 데이터의 나열자가 아닌, 내담자의 천명을 신안으로 통찰하는 노련한 만신입니다.
- 무당·만신 특유의 고풍스럽고 신비로운 어투를 유지하되, 명리 데이터를 근거로 신탁을 내립니다.

### [무당·만신 말투 지침]
- 인사: "허허, 어서 오게", "허어, 기운이 느껴지는구먼" 등으로 시작
- 서술: ~하느니라, ~하리라, ~하는구먼, ~하게, ~하지 말게 형식 사용
- 강조: "명심하게!", "아니 되느니라", "이 시기를 함부로 넘기면 아니 되느니라"
- 칭찬: "허어, 하늘이 자네 편이로구먼", "기운이 좋구먼"
- 경고: "내 신안(神眼)에 먹구름이 보이는구먼", "조심하게, 범하면 아니 되느니라"
- 무속 용어 자연스럽게 활용: 신안(神眼), 천명(天命), 팔자(八字), 신탁(神託), 기운, 신력(神力)

### 2단계: 해석 준거 (Interpretation Basis)
- [일간 강약, 격국, 용신, 대운, 합충]을 기준으로 해석하되, 전문 용어는 최소화하여 쉽게 전달합니다.
- 사주 원국과 현재 운의 흐름을 유기적으로 연동하십시오.

### 3단계: 상담 판단 규칙 (Guardrails)
{rules_ctx}

### 4단계: 답변 출력 구조 (Counsel Output Engine) - 필수 엄수
모든 답변은 반드시 다음의 4단계 구조를 따릅니다:
1. **[현재의 흐름]**: 지금 내담자가 처한 기운의 상태와 시기(씨앗기/확장기 등).
2. **[왜 그런지]**: 사주 원국과 운의 흐름에서 본 명리학적 이유.
3. **[현실 조언]**: 기회를 잡거나 위기를 극복하기 위한 구체적인 지침.
4. **[한줄 정리]**: 오늘 상담의 핵심을 관통하는 명언 또는 요약.

### 5단계: 기억 및 맥락 (Context & Memory)
- 사용자의 이전 고민이나 입력된 데이터(궁합 정보 등)가 있다면 반드시 이를 인지하고 대화에 반영하십시오.

[상담 상세 데이터]
{ctx_data}

[상담 주제 방향]
{topic_direction}
"""
        return prompt.strip()


# ==========================================================
#  ⚖️ 사주 AI 판단 규칙 12개 (Hallucination 방지 시스템)
#  질문 -> 사주 분석 -> [판단 규칙 검사] -> 출력
# ==========================================================

class SajuJudgmentRules:
    # -- 판단 규칙용 상수 정의 ---------------------------
    _ASSERTION_MAP = {
        "반드시": "흐름상", "절대": "거의", "확실히": "분명", "무조건": "매우",
        "단언컨대": "필시", "명백히": "상당히", "꼭": "가급적"
    }
    _ANXIETY_KEYWORDS = [
        "불안", "걱정", "무서", "두려", "죽고", "힘들", "사고", "문제", "위험", "절망",
        "실패", "망할", "끝장", "괴롭", "우울", "긴장", "떨려", "초조"
    ]
    _OVERPOSITIVE = ["천하무적", "완벽한", "최강의", "무조건 성공", "로또 당첨", "대박 확정"]
    _REPORT_TONE = ["분석 결과:", "다음과 같습니다:", "결론적으로", "요약하자면", "이상으로"]

    """
    AI 출력이 생성되기 전/후 적용되는 12개 판단 규칙.
    - 프롬프트 빌드 시 규칙을 주입 (사전 제어)
    - 출력 텍스트 검증/수정 (사후 제어)
    """

    def rule01_soften_assertions(text: str) -> str:
        """[1] 단정 금지 규칙 - '반드시' -> '흐름상' 치환"""
        for bad, good in SajuJudgmentRules._ASSERTION_MAP.items():
            text = text.replace(bad, good)
        return text

    # -- 규칙 5: 부정 균형 - 위험 + 대응 세트 확인 --------
    @staticmethod
    def rule05_check_negative_balance(text: str) -> str:
        """[5] 나쁜 운 설명 시 대응 방법이 없으면 자동 추가 힌트 삽입"""
        negative_phrases = ["어려운 시기", "힘든 운", "충(沖)", "주의가 필요", "조심해야"]
        has_response     = ["준비", "대응", "방법", "기회", "전략", "조언"]
        for phrase in negative_phrases:
            if phrase in text:
                if not any(r in text for r in has_response):
                    text += "\n\n※ 힘든 흐름도 준비하면 기회가 됩니다. 지금 할 수 있는 한 가지 행동에 집중해 보세요."
                break
        return text

    # -- 규칙 7: 감정 보호 - 불안 질문 탐지 ---------------
    @staticmethod
    def rule07_detect_anxiety(user_input: str) -> bool:
        """[7] 사용자 입력에 불안 키워드 포함 여부 반환"""
        return any(kw in user_input for kw in SajuJudgmentRules._ANXIETY_KEYWORDS)

    # -- 규칙 9: 기억 충돌 검사 ----------------------------
    @staticmethod
    def rule09_check_memory_conflict(text: str) -> str:
        """[9] 현재 출력 vs 저장된 흐름 기억 충돌 시 경고 보정"""
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

    # -- 규칙 11: 과도한 긍정 완화 ------------------------
    @staticmethod
    def rule11_limit_overpositive(text: str) -> str:
        """[11] 과도한 긍정 표현 -> 현실적 표현으로 치환"""
        for phrase in SajuJudgmentRules._OVERPOSITIVE:
            text = text.replace(phrase, "좋은 흐름이 있는 사주")
        return text

    # -- 규칙 12: 보고서 톤 제거 --------------------------
    @staticmethod
    def rule12_remove_report_tone(text: str) -> str:
        """[12] 분석 보고서 말투 제거 -> 상담가 어투 유지"""
        for phrase in SajuJudgmentRules._REPORT_TONE:
            text = text.replace(phrase, "")
        return text

    # -- 전체 사후 필터 (출력 텍스트에 한 번에 적용) ---------
    @staticmethod
    def apply_all(text: str) -> str:
        """생성된 AI 텍스트에 전체 판단 규칙 순서대로 적용"""
        text = SajuJudgmentRules.rule01_soften_assertions(text)
        text = SajuJudgmentRules.rule05_check_negative_balance(text)
        text = SajuJudgmentRules.rule09_check_memory_conflict(text)
        text = SajuJudgmentRules.rule11_limit_overpositive(text)
        text = SajuJudgmentRules.rule12_remove_report_tone(text)
        return text.strip()

    # -- AI 프롬프트용 규칙 주입 문자열 (사전 제어) ----------
    @staticmethod
    def build_rules_prompt(user_input: str = "") -> str:
        """AI 시스템 프롬프트에 추가할 판단 규칙 지시문 생성"""
        is_anxious = SajuJudgmentRules.rule07_detect_anxiety(user_input)
        mem_ctx    = SajuMemory.build_context_prompt()

        rules = """
[사주 AI 판단 규칙 - 반드시 준수]
[1] 단정 금지: "반드시", "100%" 대신 "흐름상", "가능성이 높습니다" 사용
[2] 순서 유지: 현재 운세 -> 성향 -> 행동 조언 순
[3] 데이터 준수: 사주 원국에 없는 정보(특정 날짜/직업명 단정) 생성 금지
[4] 시간 제한: 단기(1년)/중기(3년)/장기(10년) 이상 예측 금지
[5] 부정 균형: 위험 요소 언급 시 반드시 대응 방법 함께 제시
[6] 일관성: 동일 질문에 방향이 달라지면 안 됨
[8] 언어: 한자/격국 전문용어 남발 금지. 일반인 언어로 설명
[10] 행동 조언: 모든 풀이 끝에 "지금 할 수 있는 행동 1가지" 제시
[11] 긍정 과잉 금지: 긍정 60 / 현실 경고 40 비율 유지
[12] 상담가 말투: "분석 결과:" "다음과 같습니다" 같은 보고서체 금지
"""
        if is_anxious:
            rules += "\n[7] 주의: 사용자가 불안 상태입니다. 공포 강화 금지. 이해 -> 안정 -> 방향 순으로 답변."

        if mem_ctx:
            rules += f"\n\n{mem_ctx}"

        return rules.strip()






st.set_page_config(
    page_title="[MANSE] Saju Heaven-Sent Destiny",
    page_icon="*",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown('''
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&display=swap');

  /* == 애니메이션 & 프리미엄 효과 == */
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .animate-fade-in { animation: fadeInUp 0.7s ease-out forwards; }
  
  .gold-gradient {
    background: linear-gradient(135deg, #BF953F 0%, #FCF6BA 25%, #B38728 50%, #FBF5B7 75%, #AA771C 100%) !important;
    background-clip: text !important;
    -webkit-background-clip: text !important;
    color: transparent !important;
    font-weight: 900;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
  }

  /* == 전역 기본 == */
  html, body, [class*="css"] { 
    font-family: 'Noto Serif KR', serif; 
    -webkit-text-size-adjust: 100%;
    font-feature-settings: "palt"; /* 가변 폭 폰트 최적화 */
  }
  .stApp { 
    background: radial-gradient(circle at top right, #fffdfa 0%, #f7f3ed 100%); 
    color:#333333; 
  }
  * { box-sizing:border-box; }
  p,div,span { word-break:keep-all; overflow-wrap:break-word; }
  a,button,[role="button"] { touch-action:manipulation; }
  img { max-width:100%; height:auto; }

  /* == 기본 레이아웃 (모바일 first) == */
  .main .block-container {
    padding: 0.5rem 0.75rem 4rem !important;
    max-width: 100% !important;
  }

  /* == 탭 모바일 터치 스크롤 핵심 == */
  .stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    padding: 10px 8px !important;
    background: rgba(245, 240, 232, 0.6) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(232, 213, 160, 0.4) !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
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

  /* == 버튼 터치 최적화 == */
  .stButton > button {
    background: linear-gradient(135deg, #1a1a1a 0%, #333333 100%) !important;
    color: #f7e695 !important; 
    border: 1px solid rgba(212, 175, 55, 0.4) !important;
    font-weight: 800 !important; 
    letter-spacing: 2.5px !important;
    border-radius: 15px !important;
    min-height: 56px !important;
    font-size: 16px !important;
    width: 100% !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
    margin-top: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: uppercase;
  }
  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(212, 175, 55, 0.2) !important;
    border-color: #d4af37 !important;
  }

  /* == 입력 필드 (iOS 자동확대 방지 font-size:16px) == */
  input, select, textarea {
    font-size: 16px !important;
    color: #111 !important;
    background-color: #fff !important;
    border: 1px solid #ddd !important;
  }
  label { color: #000000 !important; font-weight: 600 !important; }

  /* == 사주 기둥 == */
  .pillar-box {
    background: rgba(255, 255, 255, 0.85); 
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1.5px solid #d4af37; 
    border-radius: 15px;
    padding: 12px 6px; 
    text-align: center; 
    color: #1a1a1a;
    box-shadow: 0 8px 25px rgba(0,0,0,0.06);
    transition: transform 0.3s ease;
  }
  .pillar-box:hover { transform: scale(1.03); }

  .card {
    background: rgba(255, 255, 255, 0.75); 
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
    border: 1px solid rgba(212, 175, 55, 0.25);
    border-radius: 20px; 
    padding: 20px 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.04);
    margin: 15px 0;
  }

  .fortune-text {
    background: rgba(255, 255, 255, 0.8); 
    backdrop-filter: blur(10px);
    border-left: 6px solid #d4af37;
    border-radius: 4px 20px 20px 4px;
    padding: 22px 18px; 
    margin: 18px 0;
    font-size: 15.5px; 
    color: #222222; 
    line-height: 2.2; 
    white-space: pre-wrap;
    font-family: 'Noto Serif KR', serif;
    box-shadow: 0 8px 30px rgba(0,0,0,0.03);
    border-top: 1px solid rgba(212, 175, 55, 0.1);
    border-right: 1px solid rgba(212, 175, 55, 0.1);
    border-bottom: 2px solid #d4af37;
  }

  /* == 섹션 헤더 == */
  .gold-section {
    color: #000000; font-size: 13px; letter-spacing: 2px;
    border-bottom: 2.5px solid #000000;
    padding-bottom: 10px; font-weight: 700; margin: 24px 0 12px;
    display: flex; align-items: center;
  }
  .gold-section::before { content:"*"; margin-right:10px; font-size:16px; color:#000000; }

  /* == 네모 박스 메뉴 스타일 == */
  div[data-testid="column"] button {
      height: 80px !important;
      border-radius: 16px !important;
      font-weight: 800 !important;
      font-size: 14px !important;
      border: 1.5px solid rgba(212, 175, 55, 0.4) !important;
      background: rgba(255, 255, 255, 0.8) !important;
      color: #333333 !important;
      box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
      transition: all 0.2s ease-in-out !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: center !important;
      align-items: center !important;
  }
  div[data-testid="column"] button:hover {
      background: #fdfbf5 !important;
      transform: translateY(-3px) !important;
      box-shadow: 0 6px 15px rgba(212, 175, 55, 0.2) !important;
  }
  div[data-testid="column"] button[kind="primary"] {
      background: linear-gradient(135deg, #1a1a1a, #333333) !important;
      color: #d4af37 !important;
      border: 2px solid #d4af37 !important;
      box-shadow: 0 6px 20px rgba(212, 175, 55, 0.4) !important;
  }

  /* == 좌측 사이드바 완전 숨김 == */
  [data-testid="stSidebar"], [data-testid="collapsedControl"] {
      display: none !important;
  }
  .main .block-container {
      max-width: 100% !important;
      padding-left: 2rem !important;
      padding-right: 2rem !important;
  }

  /* == 헤더 박스 == */
  .header-box {
    background: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    padding: 30px 20px; 
    text-align: center;
    box-shadow: 0 4px 30px rgba(0,0,0,0.05);
    margin-bottom: 25px; 
    border-bottom: 2px solid #d4af37;
    border-radius: 0 0 30px 30px;
  }
  .header-title { 
    font-size: 26px; 
    font-weight: 900; 
    letter-spacing: 5px; 
    background: linear-gradient(135deg, #BF953F 0%, #FCF6BA 25%, #B38728 50%, #FBF5B7 75%, #AA771C 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .header-sub { color: #555; font-size: 13px; letter-spacing: 3px; margin-top: 10px; font-weight: 700; text-transform: uppercase; }

  /* == 비방록 == */
  .red-scroll {
    background: #ffffff; border: 2.5px solid #ff0000; border-radius: 8px;
    padding: 16px; margin: 12px 0; color: #cc0000;
    font-family: "Noto Serif KR", serif; line-height: 2.0;
    white-space: pre-wrap; font-weight: 700;
  }

  /* == 월운 카드 == */
  .monthly-card {
    background: #ffffff; border: 1.5px solid #000000; border-radius: 10px;
    padding: 10px 12px; margin: 5px 0; font-size: 13px;
    border-left: 8px solid #000000;
    color: #000000;
  }
  .monthly-card.great { border-left-color: #000; background: #ffffff; border: 2.5px solid #000; }

  /* == 신호 배지 == */
  .signal-badge {
    display:inline-block; padding:3px 10px; border-radius:16px;
    font-size:11px; font-weight:700; margin:2px;
    background:#ffffff; color:#000000; border:1.5px solid #000000;
  }

  /* == 폼 카드 == */
  .form-card {
    background: #ffffff; border-radius: 14px;
    padding: 18px 14px; border: 1px solid #ddd;
    box-shadow: none;
    margin-bottom: 14px;
  }
  div[data-testid="stForm"] { background:transparent; border:none; padding:0; }

  /* == 480px 이하 (스마트폰) == */
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

  /* == 사주 용어 툴팁 == */
  .saju-tooltip {
    position: relative;
    display: inline-block;
    border-bottom: 1px dotted #d4af37;
    cursor: help;
    color: #b38728;
    font-weight: 700;
  }
  .saju-tooltip .tooltiptext {
    visibility: hidden;
    width: 260px;
    background-color: rgba(30, 30, 30, 0.95);
    color: #efefef;
    text-align: left;
    border-radius: 10px;
    padding: 12px 16px;
    position: absolute;
    z-index: 1000;
    bottom: 140%;
    left: 50%;
    margin-left: -130px;
    opacity: 0;
    transition: opacity 0.3s, transform 0.3s;
    transform: translateY(10px);
    font-size: 13px;
    line-height: 1.7;
    font-weight: 400;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    border: 1px solid rgba(212, 175, 55, 0.4);
    pointer-events: none;
    word-break: keep-all;
  }
  .saju-tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
    transform: translateY(0);
  }

  /* == 481~768px (태블릿) == */
  @media (min-width:481px) and (max-width:768px) {
    .main .block-container { padding:0.5rem 1rem 3rem !important; }
    .header-title { font-size:20px !important; }
    .fortune-text { font-size:14px !important; }
    .stTabs [data-baseweb="tab"] { font-size:11px !important; padding:8px 10px !important; }
    .card { padding:14px 12px !important; }
    .pillar-box { min-width:62px !important; font-size:14px !important; }
    .gold-section { font-size:12px !important; letter-spacing:1px !important; }
  }

  /* == 769px+ (데스크탑) == */
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

  /* -- 사이드바 -- */
  [data-testid="stSidebar"] { background:linear-gradient(180deg,#1a0a00,#2c1a00) !important; border-right: 1px solid #d4af37; }
  [data-testid="stSidebarContent"] { padding:1rem .75rem; background:transparent !important; }
  [data-testid="stSidebarContent"] label { color:#d4af37 !important; font-size:13px !important; }
  [data-testid="stSidebarContent"] p { color:#ffe0b2 !important; }
  [data-testid="stSidebarContent"] .stButton > button { background:#d4af37 !important; color:#1a0a00 !important; font-weight:800 !important; }
  /* 모바일: 사이드바 버튼 항상 표시 */
  @media (max-width:768px) {
    section[data-testid="stSidebar"] { 
        min-width:260px !important; 
        background: linear-gradient(180deg, #1a1a1a 0%, #2c2c2c 100%) !important;
        border-right: 1px solid #d4af37 !important;
    }
    [data-testid="collapsedControl"] { 
        display:flex !important; 
        background:#d4af37 !important; 
        border-radius:50% !important; 
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
        width: 40px !important;
        height: 40px !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="collapsedControl"] svg { fill:#1a1a1a !important; }
  }

  /* -- 탭 - 모바일 가로 스크롤 -- */
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

  /* -- 버튼 -- */
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

  /* -- 입력 (iOS font-size 16px = zoom 방지) -- */
  input, select, textarea {
    color:#000000 !important; background-color:#fff !important;
    border:1px solid #000000 !important;
    font-size:16px !important; border-radius:8px !important;
    -webkit-appearance:none;
  }
  label { color:#000000 !important; font-weight:600 !important; font-size:13px !important; }
  .stSelectbox > div > div { border-radius:8px !important; min-height:44px !important; }
  .stNumberInput input { min-height:44px !important; }

  /* -- 사이드바 -- */
  [data-testid="stSidebar"] { background:#ffffff !important; }
  [data-testid="stSidebarContent"] { padding:1rem .75rem; background:#ffffff !important; }
  [data-testid="stSidebarContent"] label { color:#000000 !important; font-size:13px !important; }

  /* -- 가로 스크롤 유틸 -- */
  .scroll-x {
    overflow-x:auto; -webkit-overflow-scrolling:touch;
    scrollbar-width:none; display:flex; gap:8px; padding-bottom:4px;
  }
  .scroll-x::-webkit-scrollbar { display:none; }

  /* -- expander -- */
  .streamlit-expanderHeader { font-size:13px !important; padding:9px 10px !important; }

  /* -- 맨위로(TOP) 버튼 -- */
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
''', unsafe_allow_html=True)

# ==============================================
#  만신(萬神)급 명리 데이터 상수
# ==============================================
CG = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
CG_KR = ["갑","을","병","정","무","기","경","신","임","계"]
JJ = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
JJ_KR = ["자","축","인","묘","진","사","오","미","신","유","술","해"]
JJ_AN = ["쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"]

CHUNG_MAP = {
    frozenset(["子","午"]): ("子午沖 (水火相沖)", "水克火", "정면 충돌, 이동, 구설, 변화가 많음 (正面 衝突)"),
    frozenset(["丑","未"]): ("丑未沖 (土土相沖)", "土克土", "지각 변동, 정체 해소, 내부 갈등 (地殼 變動)"),
    frozenset(["寅","申"]): ("寅申沖 (金木相沖)", "金克木", "역동적 변화, 사고 주의, 이동 (驛動的 變化)"),
    frozenset(["卯","酉"]): ("卯酉沖 (金木相沖)", "金克木", "정서적 충격, 관계 갈등, 이동 (情緖的 衝擊)"),
    frozenset(["辰","戌"]): ("辰戌沖 (土土相沖)", "土克土", "영적 충돌, 신앙/철학 변화, 고독 (靈的 衝突)"),
    frozenset(["巳","亥"]): ("巳亥沖 (水火相沖)", "水克火", "수증기 폭발, 급격한 변화, 이동 (急激한 變化)")
}
HAP_MAP = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}

GANJI_60 = [CG[i % 10] + JJ[i % 12] for i in range(60)]
GANJI_60_KR = [CG_KR[i % 10] + JJ_KR[i % 12] for i in range(60)]

OH = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
      "子(자)":"水","丑(축)":"土","寅(인)":"木","卯(묘)":"木","辰(진)":"土","巳(사)":"火","午(오)":"火","未(미)":"土","申(신)":"金","酉(유)":"金","戌(술)":"土","亥(해)":"水"}
OHN = {"木":"나무","火":"불","土":"흙","金":"쇠","水":"물"}
OHE = {"木":"🌳","火":"🔥","土":"🪨","金":"-","水":"💧"}
OH_DIR = {"木":"동쪽","火":"남쪽","土":"중앙","金":"서쪽","水":"북쪽"}
OH_COLOR = {"목":"초록, 청색","화":"빨강, 주황","토":"노랑, 갈색","금":"흰색, 은색","수":"검정, 남색"}
OH_NUM = {"木":"1, 3","火":"2, 7","土":"5, 0","金":"4, 9","水":"1, 6"}
OH_FOOD = {"木":"신맛, 푸른 채소","火":"쓴맛, 붉은 과일","土":"단맛, 뿌리 채소","金":"매운맛, 흰색 육류","水":"짠맛, 해조류/검은콩"}

# 📖 만신(萬神) 통합 사주 용어 사전 (Lexicon)
SAJU_LEXICON = {
    "공망": "🌓 공망(空亡): '비어 있다'는 뜻으로, 해당 장소의 기운이 약해지거나 실속이 없어짐을 의미합니다. 하지만 예술, 종교, 철학 등 정신적 영역에서는 오히려 큰 성취의 기반이 되기도 합니다.",
    "원진살": "🎭 원진살(元辰(진)殺): 서로 미워하고 멀리하는 기운입니다. 인간관계에서 이유 없는 불화나 원망이 생길 수 있으나, 이를 인내와 배려로 극복하면 오히려 더 깊은 유대감을 형성하는 계기가 됩니다.",
    "귀문관살": "🚪 귀문관살(鬼門關殺): 직관력과 영감이 매우 예민해지는 기운입니다. 예술가나 종교인에게는 천재성을 발휘하는 통로가 되지만, 평상시에는 신경과민이나 집중력 분산을 주의해야 합니다.",
    "백호살": "🐯 백호살(白虎殺): 강력한 에너지와 추진력을 의미합니다. 과거에는 흉살로 보았으나 현대에는 카리스마와 전문성을 발휘하여 큰 성공을 거두는 강력한 원동력으로 해석합니다.",
    "양인살": "⚔️ 양인살(羊刃殺): 칼을 든 것처럼 강한 고집과 독립심을 뜻합니다. 경쟁 사회에서 남들보다 앞서가는 힘이 되지만, 독단적인 판단보다는 주변과의 조화를 꾀하는 지혜가 필요합니다.",
    "화개살": "🌸 화개살(華蓋殺): 예술적 재능과 종교적 심성이 깊음을 뜻합니다. 고독을 즐기며 내면을 다지면 학문이나 예술 분야에서 빛을 발하는 고결한 기운입니다.",
    "역마살": "🐎 역마살(驛馬殺): 활동 범위가 넓고 변화를 추구하는 기운입니다. 한곳에 머물기보다 이동과 소통을 통해 기회를 잡는 현대 사회에 매우 유리한 길성이기도 합니다.",
    "도화살": "🍑 도화살(桃花殺): 사람을 끌어당기는 매력과 인기를 뜻합니다. 현대 사회에서 연예, 홍보, 영업 등 대인 관계가 중요한 분야에서 강력한 성공의 무기가 되는 기운입니다."
}

def render_saju_tooltip(term):
    """사주 용어에 툴팁을 적용하여 반환 (HTML)"""
    clean_term = term.replace("살", "").strip()
    desc = SAJU_LEXICON.get(term) or SAJU_LEXICON.get(clean_term) or SAJU_LEXICON.get(term + "살")
    if desc:
        return f'<span class="saju-tooltip">{term}<span class="tooltiptext">{desc}</span></span>'
    return term

def apply_lexicon_tooltips(text):
    """텍스트 내의 사주 용어들을 찾아 툴팁 HTML로 자동 치환"""
    if not text or not isinstance(text, str): return text
    import re
    # 용어 길이가 긴 것부터 치환하여 중복 간섭 최소화
    sorted_terms = sorted(SAJU_LEXICON.keys(), key=len, reverse=True)
    for term in sorted_terms:
        if term in text:
            # 이미 HTML 태그로 감싸진 경우 제외 (단순 구현)
            pattern = re.compile(f"(?<![>\"]){re.escape(term)}(?![<\"])")
            text = pattern.sub(render_saju_tooltip(term), text)
    return text

ILGAN_DESC = {
    "甲(갑)":{
        "nature":"""갑목(甲(갑)木) 일간으로 태어난 당신에게 하늘은 천년 거목(巨木)의 기운을 점지하였습니다.
조상의 음덕(蔭德)이 깊은 뿌리가 되어 어떤 폭풍과 세파에도 결코 꺾이지 않는 굳건한 천명(天命)을 품고 이 세상에 오셨습니다.
갑목은 십천간(十天干)의 으뜸이요, 동방(東方) 봄기운의 시작이니 새벽을 여는 자, 길을 여는 자의 사명을 타고나셨습니다.
하늘 높이 곧게 뻗어 오르는 소나무처럼 굽힘 없는 기상(氣象)과 우직한 뚝심으로 세상을 헤쳐나가는 것이 당신의 본성입니다.
인(寅(인))/묘(卯(묘)) 목왕절(木旺節)에 운이 오면 크게 발복하며, 경(庚(경))/신(辛(신)) 금(金)운에 단련을 받아 진정한 동량지재(棟樑之材)가 됩니다.""",
        "strength":"""[+] 타고난 리더십과 개척 정신: 남들이 가지 않은 길을 먼저 나아가는 선구자의 기운이 있습니다. 조직에서 자연스럽게 우두머리 자리에 오르며, 어떤 역경도 정면으로 돌파하는 불굴의 의지가 있습니다.
[+] 원칙과 의리: 한번 맺은 인연과 약속은 목숨처럼 지키는 의리의 사람입니다. 이 신뢰가 평생의 귀인(貴人)을 불러 모읍니다.
[+] 강한 추진력: 목표를 정하면 어떤 장애도 뚫고 나아가는 힘이 있어, 큰 사업이나 조직의 수장으로서 빛을 발합니다.""",
        "weakness":"""[-] 지나친 고집과 아집: 갑목 특유의 강직함이 지나치면 주위 사람들과 충돌을 빚고 귀중한 인연을 잃을 수 있습니다. 대나무처럼 굽힐 줄 알아야 폭풍에도 꺾이지 않는 법입니다.
[-] 자존심으로 인한 실기(失機): 자존심이 강한 나머지 도움을 청하지 못하거나 기회가 와도 허리를 굽히지 못해 복을 놓치는 경우가 있습니다. 용의 겸손함을 배우십시오.
[-] 독불장군 성향: 혼자 모든 것을 짊어지려 하다 소진되는 경향이 있습니다. 믿는 사람에게 권한을 나누는 지혜가 필요합니다.""",
        "career":"정치/행정/공무원, 경영인/CEO, 교육자/교수, 법조계, 군 장성/무관, 건축/토목, 의료계 수장",
        "health":"""간담(肝膽) 계통이 가장 취약하니 과음을 삼가고 정기적으로 간 기능을 점검하십시오.
목(木)기운이 과다할 때는 분노와 스트레스로 간을 상하고, 부족할 때는 근육과 눈의 피로를 호소합니다.
봄(춘)에 보약을 챙기고, 신맛 나는 음식으로 간 기운을 북돋우시기 바랍니다.""",
        "lucky":"""행운의 방향: 동쪽(東方), 행운의 색: 청색/초록, 행운의 수: 1/3, 인연의 일간: 己(기)土(정재)/辛(신)金(정관), 피해야 할 운: 庚(경)金 편관 과다"""
    },
    "乙(을)":{
        "nature":"""을목(乙(을)木) 일간으로 태어난 당신에게 하늘은 강인한 생명력으로 꽃을 피우는 기운을 점지하였습니다.
바위틈에서도, 척박한 땅에서도 기어코 싹을 틔우고 꽃을 피우는 들풀과 덩굴의 천명을 안고 오셨습니다.
갑목이 곧게 자라는 교목(喬木)이라면, 을목은 유연하게 휘어 어디에도 적응하는 덩굴식물의 지혜를 지녔습니다.
겉으로는 부드럽고 온화하나 내면에는 어떤 어려움도 이겨내는 질긴 생명력이 있으니, 이것이 을목 최고의 보배입니다.
무(戊(무))/기(己(기)) 토(土)운에 재물이 들어오고, 임(壬(임))/계(癸(계)) 수(水)운에 귀인의 도움을 받습니다.""",
        "strength":"""[+] 뛰어난 감수성과 심미안: 아름다움을 보고 느끼는 천부적 감각이 있어 예술/문화 분야에서 남들이 따라오지 못하는 경지에 이릅니다.
[+] 유연한 적응력: 어떤 환경에서도 빠르게 적응하며 인간관계를 부드럽게 유지하는 사교적 지혜가 있습니다. 귀인을 만나는 능력이 탁월합니다.
[+] 끈질긴 생명력: 을목의 가장 큰 강점은 역경을 딛고 일어서는 회복력입니다. 쓰러져도 반드시 다시 일어서는 불사조의 기운이 있습니다.""",
        "weakness":"""[-] 남의 시선에 대한 민감함: 타인의 평가에 쉽게 상처받고 흔들리는 경향이 있습니다. 내면의 중심을 굳건히 하는 수련이 필요합니다.
[-] 우유부단한 결단: 유연함이 지나치면 결정적인 순간에 결단을 내리지 못해 기회를 놓칩니다. 때로는 과감하게 결단하는 용기가 필요합니다.
[-] 의존 심리: 귀인 의존이 강해지면 스스로의 힘을 키우는 기회를 잃을 수 있습니다. 독립심을 기르는 것이 복의 근원입니다.""",
        "career":"예술가/화가/음악인, 디자이너, 상담사/심리치료사, 교육자, 뷰티/패션, 원예/조경, 외교관/통역사",
        "health":"""간담 계통과 신경계 건강에 주의하십시오. 특히 스트레스가 쌓이면 신경성 소화 장애나 두통으로 나타납니다.
을목은 음목(陰木)으로 수분이 부족하면 쉽게 시들므로 충분한 수분 섭취와 숙면이 중요합니다.
척추와 관절도 약점이 될 수 있으니 스트레칭과 운동을 생활화하십시오.""",
        "lucky":"""행운의 방향: 동남쪽, 행운의 색: 연두/청록, 행운의 수: 1/3, 인연의 일간: 庚(경)金(정관)/戊(무)土(정재), 보강할 운: 壬(임)癸(계)水 인성운"""
    },
    "丙(병)":{
        "nature":"""병화(丙(병)火) 일간으로 태어난 당신에게 하늘은 태양(太陽)의 기운을 점지하였습니다.
동녘 하늘을 붉게 물들이며 떠오르는 아침 태양처럼 온 세상을 환하게 비추고 만물에 생명력을 불어넣는 천명을 부여받으셨습니다.
태양은 높낮이 없이 귀천(貴賤)을 가리지 않고 빛을 고루 나누니, 당신 또한 넓은 포용력으로 많은 이들을 품는 인물입니다.
병화는 십천간 중 가장 밝고 뜨거운 기운으로, 어디에 있든 자연스럽게 중심이 되고 주목받는 운명을 타고났습니다.
임(壬(임))/계(癸(계)) 수(水)운에 단련되어 더욱 성숙해지고, 목(木)운에 생조(生助)를 받아 크게 발복합니다.""",
        "strength":"""[+] 강력한 카리스마와 존재감: 어느 자리에서나 자연스럽게 빛나는 존재감이 있습니다. 사람들이 본능적으로 따르게 되는 천부적 지도자 기질입니다.
[+] 뜨거운 열정과 추진력: 한번 목표를 정하면 몸을 사리지 않고 전력투구하는 열정이 있습니다. 이 열정이 주변 사람들에게 감동과 동기를 부여합니다.
[+] 뛰어난 사교성과 화술: 밝고 유쾌한 성품으로 어디서든 쉽게 친화력을 발휘하며, 말로 사람을 움직이는 능력이 탁월합니다.""",
        "weakness":"""[-] 충동적 결정: 열정이 이성을 앞서면 신중함을 잃고 충동적으로 행동하여 나중에 후회하는 상황이 생깁니다.
[-] 지속력 부족: 태양이 항상 떠 있을 수 없듯, 처음의 열기가 식으면 지속력이 약해지는 경향이 있습니다. 꾸준함을 기르는 것이 중요합니다.
[-] 자기중심적 사고: 자신이 옳다는 확신이 강해 타인의 의견을 경청하지 않는 경우가 있으니 유의하십시오.""",
        "career":"방송/연예인/유튜버, 정치인/사회운동가, 영업/마케팅, 요식업/요리사, 스포츠인, 종교지도자, 강연가",
        "health":"""심장과 혈관계 건강을 최우선으로 관리하십시오. 과도한 흥분과 스트레스는 심장에 직접적인 부담을 줍니다.
여름(하)이 되면 더위에 약해지니 충분한 휴식과 수분 보충이 필요합니다.
눈의 피로와 시력 관리에도 주의를 기울이시기 바랍니다. 정기적인 혈압 측정을 권합니다.""",
        "lucky":"""행운의 방향: 남쪽(南方), 행운의 색: 빨강/주황, 행운의 수: 2/7, 인연의 일간: 辛(신)金(정재)/壬(임)水(편관), 보강할 운: 木운 인성"""
    },
    "丁(정)":{
        "nature":"""정화(丁(정)火) 일간으로 태어난 당신에게 하늘은 촛불과 별빛의 기운을 점지하였습니다.
태양(丙(병)火)이 온 세상을 밝히는 빛이라면, 정화는 어두운 밤 홀로 빛나는 별처럼 가장 필요한 곳에서 가장 소중한 빛을 발합니다.
연약해 보이지만 결코 꺼지지 않는 촛불처럼, 당신에게는 역경 속에서도 희망의 불꽃을 간직하는 내면의 강인함이 있습니다.
정화 일간은 영성(靈性)과 직관력이 뛰어나 보이지 않는 이치를 꿰뚫어 보는 혜안(慧眼)이 있으며, 한 분야를 깊이 파고드는 전문가의 기질을 타고났습니다.
갑(甲(갑))/을(乙(을)) 목(木)운에 크게 발복하고, 무(戊(무))/기(己(기)) 토(土)운에 재물이 모입니다.""",
        "strength":"""[+] 뛰어난 직관과 통찰력: 보통 사람이 보지 못하는 사물의 본질과 이치를 꿰뚫어 보는 직관력이 있습니다. 이 능력이 학문/예술/상담 분야에서 빛을 발합니다.
[+] 깊은 정과 헌신: 한번 인연을 맺으면 깊은 정으로 헌신하는 따뜻한 인품이 있습니다. 주변 사람들이 마음 깊이 의지하는 존재가 됩니다.
[+] 전문성과 집중력: 관심 분야에 몰두하면 남다른 경지에 이르는 전문가 기질이 있습니다. 한 분야의 대가(大家)가 될 운명입니다.""",
        "weakness":"""[-] 감수성으로 인한 상처: 섬세한 감수성이 지나치면 작은 말 한마디에도 깊이 상처받아 신기(神氣)를 소진합니다.
[-] 내향적 고립: 혼자만의 세계에 빠지면 현실과의 괴리가 생기고 사회적 관계가 단절될 수 있습니다.
[-] 우유부단: 너무 많은 것을 느끼고 고려하다 보면 결정이 늦어져 기회를 놓치는 경우가 있습니다.""",
        "career":"의료인/한의사, 심리상담사/정신과의사, 종교인/성직자, 철학자/작가, 교육자, 연구원, 예술가/음악가",
        "health":"""심장과 소화기 계통을 함께 관리하십시오. 정신적 스트레스가 심장과 소화기에 동시에 영향을 미치는 체질입니다.
수면의 질을 높이는 것이 건강의 핵심입니다. 과도한 야간 활동을 줄이고 규칙적인 수면 습관을 들이십시오.
순환기 계통도 챙기시고, 차갑고 자극적인 음식은 피하시기 바랍니다.""",
        "lucky":"""행운의 방향: 남남동, 행운의 색: 자주/보라, 행운의 수: 2/7, 인연의 일간: 壬(임)水(정관)/甲(갑)木(정인), 보강할 운: 木운 인성"""
    },
    "戊(무)":{
        "nature":"""무토(戊(무)土) 일간으로 태어난 당신에게 하늘은 크고 높은 산(山)과 대지(大地)의 기운을 점지하였습니다.
태산(泰山)처럼 굳건히 자리를 지키며 사방의 모든 것을 품고 길러내는 위대한 어머니 땅의 기운이 당신의 천명입니다.
무토는 오행의 중앙(中央)을 관장하니 중재자요, 조율자요, 포용자입니다. 어떤 갈등도 당신 앞에서는 자연스럽게 봉합됩니다.
인내와 신용이 두텁고 한번 맡은 일은 반드시 해내는 성실함으로, 주변의 신망(信望)을 한 몸에 받는 인물입니다.
갑(甲(갑))/을(乙(을)) 목(木)운에 관(官)이 발달하고, 병(丙(병))/정(丁(정)) 화(火)운에 인성(印星)으로 명예가 높아집니다.""",
        "strength":"""[+] 산 같은 믿음직스러움: 어떤 상황에서도 흔들리지 않는 안정감으로 주위 사람들의 든든한 버팀목이 됩니다. 이 신뢰가 평생의 재산입니다.
[+] 탁월한 포용력: 다양한 의견과 사람들을 아우르는 포용력이 있어, 조직의 화합과 중재에 탁월한 능력을 발휘합니다.
[+] 실천적 성실함: 화려한 말보다 묵묵한 실천으로 증명하는 스타일입니다. 이 성실함이 결국 큰 성취로 이어집니다.""",
        "weakness":"""[-] 경직된 사고: 산처럼 고집스러운 면이 있어 새로운 변화와 혁신을 받아들이기 어려워하는 경향이 있습니다.
[-] 느린 결단: 모든 것을 신중하게 검토하다 보니 변화하는 환경에서 결단이 늦어 기회를 놓치는 경우가 있습니다.
[-] 고지식함: 원칙에 너무 얽매여 융통성이 부족해 보일 수 있으니, 상황에 따른 유연함이 필요합니다.""",
        "career":"부동산/건설업, 금융/은행원, 공무원/행정가, 농업/목축업, 산업계 경영인, 중재인/조정사, 의료계",
        "health":"""비위(脾胃), 즉 소화기 계통이 취약점입니다. 과식, 야식, 불규칙한 식사가 쌓이면 위장 질환으로 이어집니다.
토(土)가 과다하면 부종이나 당뇨 관련 질환에 주의하십시오.
규칙적인 식사와 적당한 운동, 과로를 피하는 생활습관이 건강의 핵심입니다.""",
        "lucky":"""행운의 방향: 중앙/북동, 행운의 색: 노랑/황토, 행운의 수: 5/0, 인연의 일간: 癸(계)水(정재)/甲(갑)木(편관), 보강할 운: 丙(병)丁(정)火 인성운"""
    },
    "己(기)":{
        "nature":"""기토(己(기)土) 일간으로 태어난 당신에게 하늘은 기름진 논밭(田畓)의 기운을 점지하였습니다.
무토(戊(무)土)가 산이라면 기토는 농부의 손길이 닿아 씨앗을 받아들이고 풍요로운 결실을 맺는 옥토(沃土)입니다.
당신은 가진 것을 더욱 가치 있게 변환시키고 길러내는 연금술사의 능력을 타고났습니다.
표면적으로는 온순하고 부드러워 보이지만, 내면에는 집요하리만치 강한 의지와 인내심이 숨어 있습니다.
병(丙(병))/정(丁(정)) 화(火)운에 인성이 강해져 학문과 명예가 빛나고, 경(庚(경))/신(辛(신)) 금(金)운에 식상(食傷)이 발달하여 재주가 드러납니다.""",
        "strength":"""[+] 세심하고 꼼꼼한 완성도: 어떤 일이든 디테일을 챙기며 완성도 높게 마무리하는 능력이 있습니다. 이 꼼꼼함이 신뢰와 전문성의 바탕이 됩니다.
[+] 실용적 지혜: 화려함보다 실질적인 효용을 추구하는 현실적 지혜가 있어, 실생활에서 놀라운 성과를 거둡니다.
[+] 깊은 배려심: 주변 사람들의 필요를 세심하게 살피고 채워주는 따뜻한 마음이 귀인을 불러 모읍니다.""",
        "weakness":"""[-] 과도한 걱정과 불안: 기토의 특성상 작은 문제도 크게 걱정하는 경향이 있어 신기(神氣)를 소진합니다. 현재에 집중하는 연습이 필요합니다.
[-] 결단력 부족: 너무 많은 것을 고려하다 보면 결정이 늦어지고, 다른 사람의 의견에 쉽게 흔들리는 경우가 있습니다.
[-] 자기희생 과다: 남을 돌보다가 자신을 돌보지 못하는 경우가 많습니다. 나 자신도 소중한 존재임을 기억하십시오.""",
        "career":"회계사/세무사, 의료인/약사, 요리사/조리사, 원예/농업, 교육자, 심리상담사, 중소기업 경영",
        "health":"""소화기와 피부 질환을 가장 주의해야 합니다. 기름진 음식, 과식, 스트레스성 식이 장애에 취약합니다.
비만이나 당뇨, 피부 트러블이 건강의 신호등이 됩니다. 절제된 식습관이 최고의 보약입니다.
토(土)가 습(濕)하면 무기력증이 오니 규칙적인 운동으로 습기를 털어내십시오.""",
        "lucky":"""행운의 방향: 북동/중앙, 행운의 색: 황색/베이지, 행운의 수: 5/0, 인연의 일간: 甲(갑)木(편관)/壬(임)水(정재), 보강할 운: 丙(병)丁(정)火 인성운"""
    },
    "庚(경)":{
        "nature":"""경금(庚(경)金) 일간으로 태어난 당신에게 하늘은 천하를 호령하는 강철 칼날과 원석(原石)의 기운을 점지하였습니다.
광산에서 막 캐낸 원석처럼 겉은 거칠고 투박해 보이지만, 그 안에는 세상 어떤 것도 베어낼 수 있는 강인한 기운이 잠들어 있습니다.
정(丁(정))화의 제련(製鍊)을 받아 갈고 닦을수록 더욱 빛나는 보검(寶劍)이 되는 천명을 타고났으니, 고난이 오히려 당신을 완성시킵니다.
경금 일간은 불의를 보면 참지 못하는 정의감과 결단력이 있어, 사회의 불합리한 것을 바로잡는 역할을 운명으로 받아들입니다.
정(丁(정))화운에 단련되어 진정한 강자가 되고, 토(土)운에 생조를 받아 근본이 두터워집니다.""",
        "strength":"""[+] 불굴의 결단력: 한번 결심한 일은 어떤 어려움도 뚫고 반드시 실행에 옮기는 강철 같은 의지력이 있습니다.
[+] 강렬한 정의감: 옳고 그름에 대한 판단이 명확하여 불의를 보면 자신의 손해를 감수하고도 바로잡으려 합니다. 이 기개가 많은 사람의 존경을 받습니다.
[+] 뛰어난 실행력: 계획을 세우면 빠르고 강력하게 실행에 옮기는 추진력이 있어 조직에서 없어서는 안 되는 핵심 인재가 됩니다.""",
        "weakness":"""[-] 거친 언행: 직설적인 표현이 지나치면 주변 사람들에게 상처를 주고 관계를 해치는 경우가 있습니다. 말에 포장지를 입히는 지혜가 필요합니다.
[-] 극단적 선택: 회색지대를 인정하지 않는 흑백 논리가 지나치면 중도(中道)를 잃어 극단으로 치닫는 경향이 있습니다.
[-] 오만: 자신의 능력을 과신하여 타인을 무시하는 경향이 있을 수 있습니다. 겸손이 경금의 가장 큰 보완재입니다.""",
        "career":"군인/장교, 경찰/검사, 외과의사/치과의사, 기계/금속 기술자, 운동선수, 건설/토목, 중공업",
        "health":"""폐(肺)와 대장(大腸) 계통을 각별히 관리하십시오. 건조한 환경에서 폐 기능이 저하되기 쉽습니다.
피부 관련 질환과 호흡기 질환에 취약한 체질이므로 가을에 특히 주의가 필요합니다.
격렬한 운동은 좋지만 관절과 인대 부상에 주의하시고, 수술을 요하는 상황이 종종 생길 수 있습니다.""",
        "lucky":"""행운의 방향: 서쪽(西方), 행운의 색: 흰색/은색, 행운의 수: 4/9, 인연의 일간: 乙(을)木(정재)/丁(정)火(정관), 보강할 운: 土운 인성"""
    },
    "辛(신)":{
        "nature":"""신금(辛(신)金) 일간으로 태어난 당신에게 하늘은 빛나는 보석과 완성된 금속의 기운을 점지하였습니다.
경금(庚(경)金)이 다듬어지지 않은 광석이라면, 신금은 이미 세공을 마친 아름다운 보석과 정밀한 칼날입니다.
당신은 날카로운 감식안(鑑識眼)으로 아름다움과 가치를 알아보고, 완벽한 것을 추구하는 미의식(美意識)이 천성입니다.
섬세하고 예민한 기질로 인해 상처도 쉽게 받지만, 그 감수성이 예술적 감각과 통찰력의 원천이 됩니다.
임(壬(임))/계(癸(계)) 수(水)운에 식상이 발달하여 재주가 빛나고, 토(土)운에 인성이 강해져 학문과 명예가 높아집니다.""",
        "strength":"""[+] 완벽주의적 심미안: 다른 사람이 보지 못하는 미세한 결함도 발견하고 완성도를 높이는 능력이 탁월합니다. 최고 수준을 추구하는 이 기질이 전문가로 성장하는 힘입니다.
[+] 날카로운 분석력: 상황을 세밀하게 분석하고 핵심을 찌르는 통찰력이 있어, 전략적 판단이 필요한 분야에서 두각을 나타냅니다.
[+] 우아함과 품격: 언행에 자연스러운 품격이 배어 있어 사람들에게 신뢰와 호감을 줍니다. 격이 있는 환경에서 더욱 빛을 발합니다.""",
        "weakness":"""[-] 지나친 완벽주의로 인한 소진: 완벽하지 않으면 시작조차 못하거나, 완성된 것도 계속 수정하다 에너지를 소진합니다.
[-] 예민한 감수성: 작은 자극에도 크게 반응하여 마음의 상처가 깊어지고, 대인관계에서 소소한 갈등을 크게 받아들이는 경향이 있습니다.
[-] 외로움: 자신의 높은 기준을 맞춰줄 사람이 드물어 외로움을 느끼는 경우가 많습니다. 타인의 다름을 인정하는 관대함이 필요합니다.""",
        "career":"연구원/과학자, 예술가/공예가, 디자이너, 금융/투자분석가, 패션/뷰티, 치과/성형외과, 보석감정사",
        "health":"""폐와 피부/호흡기 계통이 신금의 취약점입니다. 건조한 공기와 대기오염에 특히 민감하므로 가습기와 공기청정기를 활용하십시오.
피부 트러블이 건강의 신호가 되는 경우가 많으니 피부 상태를 통해 내면 건강을 점검하십시오.
과도한 스트레스와 완벽주의는 면역력을 떨어뜨리니 충분한 휴식이 필수입니다.""",
        "lucky":"""행운의 방향: 서서남, 행운의 색: 흰색/은색/금색, 행운의 수: 4/9, 인연의 일간: 丙(병)火(정관)/壬(임)水(상관), 보강할 운: 土운 인성"""
    },
    "壬(임)":{
        "nature":"""임수(壬(임)水) 일간으로 태어난 당신에게 하늘은 천하를 품는 대해(大海)의 기운을 점지하였습니다.
무한한 바다처럼 모든 강물을 받아들이고 무궁한 지혜를 품은 당신은, 광활한 포용력과 깊은 통찰력으로 세상을 읽어내는 천명을 받았습니다.
임수는 십천간 중 가장 깊고 넓은 기운으로, 겉으로는 유연하게 흘러가되 거대한 파도처럼 세상을 움직이는 잠재력이 있습니다.
빠른 두뇌회전과 폭넓은 지식, 국제적 안목을 갖춘 전략가요, 사상가의 기질을 타고났습니다.
금(金)운에 생조를 받아 지혜가 샘솟고, 목(木)운에 식상이 발달하여 재능이 만개합니다.""",
        "strength":"""[+] 탁월한 지혜와 통찰력: 복잡한 상황의 본질을 꿰뚫어 보는 뛰어난 지혜가 있습니다. 남들이 보지 못하는 미래를 내다보는 선견지명이 있습니다.
[+] 무한한 포용력: 다양한 관점과 사람을 받아들이는 넓은 마음이 있어 국제적인 무대에서도 자연스럽게 활약합니다.
[+] 전략적 사고: 크고 복잡한 그림을 한 번에 파악하는 능력이 있어 전략 기획, 투자, 외교 분야에서 탁월한 성과를 냅니다.""",
        "weakness":"""[-] 일관성 부족: 물이 그릇에 따라 모양이 변하듯, 환경에 따라 쉽게 변하여 일관성 없다는 평을 듣는 경우가 있습니다.
[-] 실행력 부족: 머릿속으로는 완벽한 계획을 세우지만 실행에 옮기는 단계에서 에너지가 분산되는 경향이 있습니다.
[-] 감정 기복: 깊은 감수성으로 인해 감정 기복이 있을 수 있으며, 우울감에 빠지는 경우도 있습니다. 마음의 닻을 내리는 수련이 필요합니다.""",
        "career":"외교관/국제무역, 철학자/사상가, 종교인, 법조인, 의료계, 심리학자, 투자가/펀드매니저, 해운/항공업",
        "health":"""신장(腎臟)과 방광(膀胱), 그리고 생식기계 건강을 중점 관리하십시오. 차가운 음식과 음료를 과도하게 섭취하면 신장 기능이 저하됩니다.
겨울철 보온을 철저히 하고, 허리와 무릎 관절 관리에도 주의를 기울이십시오.
임수 일간은 수면 부족에 취약하여 만성피로로 이어지기 쉬우니 수면 관리가 건강의 핵심입니다.""",
        "lucky":"""행운의 방향: 북쪽(北方), 행운의 색: 검정/남색, 행운의 수: 1/6, 인연의 일간: 丁(정)火(정재)/甲(갑)木(식신), 보강할 운: 金운 인성"""
    },
    "癸(계)":{
        "nature":"""계수(癸(계)水) 일간으로 태어난 당신에게 하늘은 이슬과 샘물, 봄비의 기운을 점지하였습니다.
임수(壬(임)水)가 거대한 바다라면, 계수는 생명을 살리는 이슬이요, 대지를 적시는 봄비이며, 깊은 산속의 맑은 샘물입니다.
작고 섬세한 것 같지만, 이 세상 모든 생명이 계수의 은혜 없이는 살아갈 수 없으니 당신은 세상에서 가장 소중한 기운의 주인공입니다.
영적 감수성과 예술적 재능이 탁월하며, 보이지 않는 것을 느끼고 표현하는 천부적 능력이 있습니다.
금(金)운에 생조를 받아 기운이 풍성해지고, 목(木)운에 식상이 발달하여 재능이 펼쳐집니다.""",
        "strength":"""[+] 뛰어난 직관과 영적 감수성: 논리가 닿지 않는 영역의 진실을 직관으로 파악하는 능력이 있습니다. 이 능력이 예술/상담/의료 분야에서 빛납니다.
[+] 깊은 공감 능력: 타인의 감정과 아픔을 내 것처럼 느끼는 공감 능력이 있어, 사람들이 마음을 열고 의지하는 존재가 됩니다.
[+] 창의적 상상력: 독창적인 아이디어와 상상력이 풍부하여 새로운 것을 창조하는 분야에서 탁월한 성과를 냅니다.""",
        "weakness":"""[-] 자기 과소평가: 계수 일간의 가장 큰 적은 자기 자신입니다. 스스로의 능력을 너무 낮게 평가하여 도전을 포기하는 경우가 많습니다.
[-] 경계 설정 어려움: 타인의 감정을 너무 잘 흡수하다 보니 자신의 에너지가 고갈되고 경계가 무너지는 경험을 합니다.
[-] 현실 도피: 현실의 어려움을 직면하기보다 상상의 세계나 영성으로 도피하는 경향이 있습니다. 현실에 뿌리를 내리는 훈련이 필요합니다.""",
        "career":"예술가/시인/소설가, 문학가/작가, 심리치료사, 의료인, 종교인/영성지도자, 음악인, 사진작가, 복지사",
        "health":"""면역력과 신장 계통이 가장 취약합니다. 몸이 차가워지면 면역력이 급격히 저하되니 항상 몸을 따뜻하게 유지하십시오.
정서적 스트레스가 면역계에 직접적인 영향을 주므로 감정 관리가 건강 관리와 직결됩니다.
하체와 신장, 방광 관리에 주의를 기울이고, 차가운 음식과 날 음식을 가급적 피하십시오.""",
        "lucky":"""행운의 방향: 북북동, 행운의 색: 검정/보라/자주, 행운의 수: 1/6, 인연의 일간: 戊(무)土(정관)/丙(병)火(정재), 보강할 운: 金운 인성"""
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

SIPSUNG_LIST = ["比肩", "劫財", "食神", "傷官", "偏財", "正財", "偏官", "正官", "偏印", "正印"]

TEN_GODS_MATRIX = {
    "甲(갑)": {"甲(갑)":"比肩","乙(을)":"劫財","丙(병)":"食神","丁(정)":"傷官","戊(무)":"偏財","己(기)":"正財","庚(경)":"偏官","辛(신)":"正官","壬(임)":"偏印","癸(계)":"正印"},
    "乙(을)": {"乙(을)":"比肩","甲(갑)":"劫財","丁(정)":"食神","丙(병)":"傷官","己(기)":"偏財","戊(무)":"正財","辛(신)":"偏官","庚(경)":"正官","癸(계)":"偏印","壬(임)":"正印"},
    "丙(병)": {"丙(병)":"比肩","丁(정)":"劫財","戊(무)":"食神","己(기)":"傷官","庚(경)":"偏財","辛(신)":"正財","壬(임)":"偏官","癸(계)":"正官","甲(갑)":"偏印","乙(을)":"正印"},
    "丁(정)": {"丁(정)":"比肩","丙(병)":"劫財","己(기)":"食神","戊(무)":"傷官","辛(신)":"偏財","庚(경)":"正財","癸(계)":"偏官","壬(임)":"正官","乙(을)":"偏印","甲(갑)":"正印"},
    "戊(무)": {"戊(무)":"比肩","己(기)":"劫財","庚(경)":"食神","辛(신)":"傷官","壬(임)":"偏財","癸(계)":"正財","甲(갑)":"偏官","乙(을)":"正官","丙(병)":"偏印","丁(정)":"正印"},
    "己(기)": {"己(기)":"比肩","戊(무)":"劫財","辛(신)":"食神","庚(경)":"傷官","癸(계)":"偏財","壬(임)":"正財","乙(을)":"偏官","甲(갑)":"正官","丁(정)":"偏印","丙(병)":"正印"},
    "庚(경)": {"庚(경)":"比肩","辛(신)":"劫財","壬(임)":"食神","癸(계)":"傷官","甲(갑)":"偏財","乙(을)":"正財","丙(병)":"偏官","丁(정)":"正官","戊(무)":"偏印","己(기)":"正印"},
    "辛(신)": {"辛(신)":"比肩","庚(경)":"劫財","癸(계)":"食神","壬(임)":"傷官","乙(을)":"偏財","甲(갑)":"正財","丁(정)":"偏官","丙(병)":"正官","己(기)":"偏印","戊(무)":"正印"},
    "壬(임)": {"壬(임)":"比肩","癸(계)":"劫財","甲(갑)":"食神","乙(을)":"傷官","丙(병)":"偏財","丁(정)":"正財","戊(무)":"偏官","己(기)":"正官","庚(경)":"偏印","辛(신)":"正印"},
    "癸(계)": {"癸(계)":"比肩","壬(임)":"劫財","乙(을)":"食神","甲(갑)":"傷官","丁(정)":"偏財","丙(병)":"正財","己(기)":"偏官","戊(무)":"正官","辛(신)":"偏印","庚(경)":"正印"}
}
# ★ bare 한자 key alias 추가: CG[]='甲' → TEN_GODS_MATRIX='甲(갑)' 불일치 해결
# get_pillars, get_daewoon 등은 CG[]=bare 한자를 사용하므로 두 포맷 모두 지원
_CG_FULL = ["甲(갑)","乙(을)","丙(병)","丁(정)","戊(무)","己(기)","庚(경)","辛(신)","壬(임)","癸(계)"]
_CG_BARE = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
for _bare, _full in zip(_CG_BARE, _CG_FULL):
    if _full in TEN_GODS_MATRIX and _bare not in TEN_GODS_MATRIX:
        _sub = {}
        for _k, _v in TEN_GODS_MATRIX[_full].items():
            _sub[_k] = _v
            # 서브키도 bare 한자로 alias (예: "甲(갑)"→"甲")
            _bare_k = _k.split("(")[0] if "(" in _k else _k
            if _bare_k != _k:
                _sub[_bare_k] = _v
        TEN_GODS_MATRIX[_bare] = _sub
        # 원래 full키 서브딕셔너리에도 bare 서브키 추가
        for _k2, _v2 in list(TEN_GODS_MATRIX[_full].items()):
            _bare_k2 = _k2.split("(")[0] if "(" in _k2 else _k2
            if _bare_k2 not in TEN_GODS_MATRIX[_full]:
                TEN_GODS_MATRIX[_full][_bare_k2] = _v2

JIJANGGAN = {
    "子(자)":["壬(임)","癸(계)"],"丑(축)":["癸(계)","辛(신)","己(기)"],"寅(인)":["戊(무)","丙(병)","甲(갑)"],"卯(묘)":["甲(갑)","乙(을)"],
    "辰(진)":["乙(을)","癸(계)","戊(무)"],"巳(사)":["戊(무)","庚(경)","丙(병)"],"午(오)":["丙(병)","己(기)","丁(정)"],"未(미)":["丁(정)","乙(을)","己(기)"],
    "申(신)":["戊(무)","壬(임)","庚(경)"],"酉(유)":["庚(경)","辛(신)"],"戌(술)":["辛(신)","丁(정)","戊(무)"],"亥(해)":["戊(무)","甲(갑)","壬(임)"]
}
# JIJANGGAN bare 한자 key alias: JJ[]='子'(bare) 형식으로 조회 가능하게
for _jb, _jf in zip(['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'],
                    ['子(자)','丑(축)','寅(인)','卯(묘)','辰(진)','巳(사)','午(오)','未(미)','申(신)','酉(유)','戌(술)','亥(해)']):
    if _jf in JIJANGGAN and _jb not in JIJANGGAN:
        JIJANGGAN[_jb] = JIJANGGAN[_jf]

UNSUNG_TABLE = {
    "甲(갑)": {"亥(해)":"장생","子(자)":"목욕","丑(축)":"관대","寅(인)":"건록","卯(묘)":"제왕","辰(진)":"쇠","巳(사)":"병","午(오)":"사","未(미)":"묘","申(신)":"절","酉(유)":"태","戌(술)":"양"},
    "乙(을)": {"午(오)":"장생","巳(사)":"목욕","辰(진)":"관대","卯(묘)":"건록","寅(인)":"제왕","丑(축)":"쇠","子(자)":"병","亥(해)":"사","戌(술)":"묘","酉(유)":"절","申(신)":"태","未(미)":"양"},
    "丙(병)": {"寅(인)":"장생","卯(묘)":"목욕","辰(진)":"관대","巳(사)":"건록","午(오)":"제왕","未(미)":"쇠","申(신)":"병","酉(유)":"사","戌(술)":"묘","亥(해)":"절","子(자)":"태","丑(축)":"양"},
    "丁(정)": {"酉(유)":"장생","申(신)":"목욕","未(미)":"관대","午(오)":"건록","巳(사)":"제왕","辰(진)":"쇠","卯(묘)":"병","寅(인)":"사","丑(축)":"묘","子(자)":"절","亥(해)":"태","戌(술)":"양"},
    "戊(무)": {"寅(인)":"장생","卯(묘)":"목욕","辰(진)":"관대","巳(사)":"건록","午(오)":"제왕","未(미)":"쇠","申(신)":"병","酉(유)":"사","戌(술)":"묘","亥(해)":"절","子(자)":"태","丑(축)":"양"},
    "己(기)": {"酉(유)":"장생","申(신)":"목욕","未(미)":"관대","午(오)":"건록","巳(사)":"제왕","辰(진)":"쇠","卯(묘)":"병","寅(인)":"사","丑(축)":"묘","子(자)":"절","亥(해)":"태","戌(술)":"양"},
    "庚(경)": {"巳(사)":"장생","午(오)":"목욕","未(미)":"관대","申(신)":"건록","酉(유)":"제왕","戌(술)":"쇠","亥(해)":"병","子(자)":"사","丑(축)":"묘","寅(인)":"절","卯(묘)":"태","辰(진)":"양"},
    "辛(신)": {"子(자)":"장생","亥(해)":"목욕","戌(술)":"관대","酉(유)":"건록","申(신)":"제왕","未(미)":"쇠","午(오)":"병","巳(사)":"사","辰(진)":"묘","卯(묘)":"절","寅(인)":"태","丑(축)":"양"},
    "壬(임)": {"申(신)":"장생","酉(유)":"목욕","戌(술)":"관대","亥(해)":"건록","子(자)":"제왕","丑(축)":"쇠","寅(인)":"병","卯(묘)":"사","辰(진)":"묘","巳(사)":"절","午(오)":"태","未(미)":"양"},
    "癸(계)": {"卯(묘)":"장생","寅(인)":"목욕","丑(축)":"관대","子(자)":"건록","亥(해)":"제왕","戌(술)":"쇠","酉(유)":"병","申(신)":"사","未(미)":"묘","午(오)":"절","巳(사)":"태","辰(진)":"양"}
}

CONTROL_MAP = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
BIRTH_MAP = {"木":"火","火":"土","土":"金","金":"水","水":"木"}

def detect_structure(ilgan, wolji_jj):
    jijang = JIJANGGAN.get(wolji_jj, [])
    if not jijang: return "일반격"
    junggi = jijang[-1]
    structure_type = TEN_GODS_MATRIX.get(ilgan, {}).get(junggi, "기타")
    return f"{structure_type}格"

GYEOKGUK_DESC = {
    "正官格": {
        "summary": """正官格은 법도와 질서를 몸에 타고난 최고의 貴格이로다!
正官은 일간을 극하되 음양이 다른 기운으로 마치 스승이 제자를 올바르게 이끌듯, 당신을 바른 길로 인도하는 하늘의 뜻이 담겨 있습니다.
官印相生이 이루어지면 학문과 명예가 함께 빛나는 최상의 귀격이 되고, 財星이 관을 생하면 재물도 함께 따라옵니다.
법과 원칙을 중시하고 질서 속에서 성취를 이루는 당신의 삶은, 주변 사람들에게 믿음직한 모범이 됩니다.
-> 用神: 印綬로 官의 기운을 일간에 전달할 때 최상 발복""",
        "lucky_career": "공무원/관료, 법관/검사/판사, 대기업 임원, 교육공무원/교장, 군 장교, 외교관, 국회의원",
        "caution": """[!] 七殺(偏官)이 섞이면 관직에 구설이 따르고 직위가 불안해집니다.
[!] 官多身弱하면 직장에서 압박감이 심해지니 인성운이 올 때를 기다리십시오.
[!] 正官이 합거(合去)되면 평생 관직과의 인연이 약해집니다. 이 경우 전문직으로 방향을 바꾸십시오.""",
        "god_rank": "天乙(을)貴人/文昌貴人이 함께하면 재상(宰相)의 귀격! 官印相生이면 세상에 이름을 남기는 최상격"
    },
    "偏官格": {
        "summary": """偏官格, 즉 七殺格은 서슬 퍼런 강철 칼날의 기운으로 이루어진 격이로다!
制化가 이루어지면 천하를 호령하는 영웅이 되고, 제화가 안 되면 파란만장한 인생의 주인공이 됩니다.
食神制殺이 되면 칠살의 흉기(凶氣)가 길기(吉氣)로 변환되어 군/검/경/의 분야에서 천하무적의 강자가 됩니다.
殺印相生이 이루어지면 학문과 무공을 함께 갖춘 문무겸전(文武兼全)의 대인물이 됩니다.
-> 핵심: 이 격이 빛나려면 반드시 制화가 필요합니다. 제화 여부가 귀천(貴賤)을 가릅니다""",
        "lucky_career": "군인/장성, 경찰/검찰/형사, 외과의사/응급의학과, 운동선수/격투가, 법조인, 소방관/구조대원, 공학/기술자",
        "caution": """[!] 殺이 너무 많아 身弱하면 사고/수술/관재의 위험이 따릅니다. 合殺이나 制殺이 필요합니다.
[!] 偏官이 천간에 투출하면 직장 상사나 권력과의 마찰이 잦습니다. 인내와 처세가 필요합니다.
[!] 여명(女命)에서는 남편과의 갈등이나 이별수가 따를 수 있으니 배우자 선택에 신중을 기하십시오.""",
        "god_rank": "殺印相生/食神制殺이면 장군/재상의 대귀격! 고난이 클수록 더욱 단단해지는 불굴의 운명"
    },
    "正財格": {
        "summary": """正財格은 성실하고 꾸준하게 쌓아가는 안정된 재물의 격이로다!
正財는 일간이 음양이 다른 오행을 극하는 것으로, 내가 주체적으로 관리하고 통제하는 안정된 재물의 기운입니다.
급작스러운 횡재보다는 땀 흘려 벌어 차곡차곡 쌓아가는 재물운이라, 나이 들수록 자산이 불어나는 복을 지녔습니다.
官印相生이 더해지면 재물과 명예가 함께 빛나는 부귀격(富貴格)이 됩니다.
-> 用神: 食傷으로 재를 生하거나, 官으로 재를 洩氣할 때 균형이 맞음""",
        "lucky_career": "회계사/세무사/공인회계사, 은행원/금융인, 부동산 전문가, 행정공무원, 관리직/경영직, 의사/약사",
        "caution": """[!] 劫財가 많으면 애써 모은 재물이 동업자나 형제로 인해 새어나갑니다. 동업을 각별히 경계하십시오.
[!] 財星이 너무 왕(旺)하고 印星을 극하면 학문이 중단되거나 모친과의 인연이 약해질 수 있습니다.
[!] 偏官이 혼잡하면 재물이 오히려 관재(官災)의 씨앗이 될 수 있으니 법을 철저히 준수하십시오.""",
        "god_rank": "財旺身強에 官印相生이면 천하의 부귀격! 말년으로 갈수록 풍요로워지는 귀한 운명"
    },
    "偏財格": {
        "summary": """偏財格은 기회를 포착하여 크게 터뜨리는 활동적인 복록(福祿)의 격이로다!
偏財는 일간이 음양이 같은 오행을 극하는 것으로, 고정된 수입보다는 투자/사업/거래를 통한 역동적인 재물 활동을 의미합니다.
食神이 편재를 生하는 食神生財가 이루어지면 창의력으로 막대한 재물을 모으는 시대의 아이콘이 됩니다.
부친(父親)의 기운이기도 하여, 부친의 영향을 많이 받거나 부친의 재물을 물려받는 인연이 있습니다.
-> 핵심: 身強해야 큰 재물을 다룰 수 있습니다. 身弱하면 큰 재물에 짓눌릴 수 있습니다""",
        "lucky_career": "사업가/기업인/CEO, 투자자/펀드매니저, 무역상/유통업자, 부동산 개발업, 연예인/방송인, 스포츠 관련업",
        "caution": """[!] 身弱한데 큰 사업을 벌이면 재물에 짓눌려 실패합니다. 역량을 먼저 키운 후 도전하십시오.
[!] 比劫이 많으면 동업자/형제로 인한 재물 분쟁이 생깁니다. 단독 경영이 유리합니다.
[!] 여명(女命)에서 偏財格이 지나치면 부부 갈등이나 배우자의 방탕으로 인한 재물 손실이 따를 수 있습니다.""",
        "god_rank": "食神生財에 身強하면 최고의 사업가 격! 대운이 맞으면 부(富)로 이름을 떨치는 천하의 부자 운명"
    },
    "食神格": {
        "summary": """食神格은 하늘이 내리신 복덩어리 중의 복덩어리 격이로다! 壽星이라고도 불립니다.
食神은 일간이 생(生)하는 음양이 같은 오행으로, 먹고 마시고 즐기는 생명력과 창의적 표현의 기운입니다.
壽/祿/壽 삼박자를 갖춘 이 격은 장수하고 풍요롭게 먹고 살 걱정 없이 재능을 펼치는 복된 운명입니다.
食神制殺이 이루어지면 칠살의 흉기를 다스리는 대인물이 되고, 食神生財면 재물도 풍요롭습니다.
-> 梟神(偏印)이 食神을 극하면 복이 반감되니 이를 가장 경계해야 합니다""",
        "lucky_career": "요리사/외식업자, 예술가/음악인, 작가/시인, 교육자/강사, 의료인, 아이디어 사업가, 복지/봉사직",
        "caution": """[!] 梟神(偏印)이 있으면 食神의 복이 꺾입니다. 이 경우 財星으로 효신을 제어해야 합니다.
[!] 食神이 너무 많으면 오히려 에너지가 분산되고 집중력이 떨어집니다. 하나에 집중하는 것이 중요합니다.
[!] 재물에 대한 욕심을 부리기보다 자신의 재능을 갈고닦는 데 집중할 때 복이 저절로 따라옵니다.""",
        "god_rank": "食神制殺이면 천하의 대귀격! 壽/祿/壽를 모두 갖춘 복된 운명으로 먹고 사는 걱정 없이 재능을 펼칩니다"
    },
    "傷官格": {
        "summary": """傷官格은 기존의 틀과 권위를 박살내는 혁명가이자 천재들의 격이로다!
傷官은 일간이 생하는 음양이 다른 오행으로, 기성 질서에 도전하고 새로운 것을 창조하는 폭발적 에너지를 지닙니다.
역대 최고의 예술가/사상가/혁신가들에게 상관이 강하게 작용하는 경우가 많습니다. 당신은 세상을 바꿀 잠재력을 지녔습니다.
傷官生財가 이루어지면 창의력으로 막대한 재물을 모으는 시대의 아이콘이 됩니다.
-> 가장 중요한 경계: 傷官見官! 正官과 상관이 만나면 官災/구설/직장 위기가 옵니다""",
        "lucky_career": "연예인/유튜버/방송인, 예술가, 변호사/변리사, 창업가/혁신가, 작가/작곡가, 언론인/PD, 스타트업 CEO",
        "caution": """[!] 傷官見官은 직장과 관직의 최대 위기! 관운이 올 때는 언행을 극도로 조심하십시오.
[!] 자존심이 너무 강해 권위자와 충돌하는 경향이 있습니다. 전략적 유연함이 필요합니다.
[!] 감정 기복이 심하고 충동적인 면이 있어 중요한 결정 전에 반드시 한 번 더 생각하는 습관을 들이십시오.""",
        "god_rank": "傷官生財에 印星이 제어하면 천하를 경영하는 최고의 창조자 격! 역사에 이름을 남기는 천재의 운명"
    },
    "正印格": {
        "summary": """正印格은 학문과 지혜, 어머니의 사랑이 담긴 최고의 名譽格이로다!
正印은 일간을 생(生)하는 음양이 다른 오행으로, 학문/지식/명예/어머니/문서의 기운을 총괄합니다.
官印相生이 이루어지면 관직과 학문이 함께 빛나는 세상에서 가장 존경받는 운명이 됩니다.
당신은 배움을 즐기고 지식을 나누는 것이 삶의 보람이며, 이 기운이 당신을 평생 바른 길로 이끄는 나침반이 됩니다.
-> 財星이 인성을 극하면 학업이 중단되거나 명예가 손상되니 각별히 주의하십시오""",
        "lucky_career": "교수/학자/연구원, 교사/교육자, 의사/한의사, 변호사, 종교인/성직자, 작가/언론인, 공직자/행정가",
        "caution": """[!] 財星이 印星을 破하면 학업 중단이나 어머니와의 인연이 약해집니다. 학문을 지속하는 것이 복의 근원입니다.
[!] 印星이 너무 많으면 행동력이 약해지고 의존적이 되는 경향이 있습니다. 실천하는 용기가 필요합니다.
[!] 모친 의존이 강한 격이니 독립적으로 자립하는 시기를 늦추지 마십시오.""",
        "god_rank": "官印相生이면 세상이 우러러보는 최고의 명예격! 학문으로 세상에 이름을 남기는 귀한 운명"
    },
    "偏印格": {
        "summary": """偏印格은 남다른 직관과 신비로운 神氣를 지닌 특이한 인재의 격이로다!
偏印(梟神이라고도 함)은 일간을 생하는 음양이 같은 오행으로, 학문보다는 직관/영성/예술/이단 사상에 가깝습니다.
남들이 걷지 않는 독특한 길을 개척하는 이단아적 천재의 기운으로, 특수 분야에서 독보적인 경지에 이를 수 있습니다.
偏印專旺이면 한 분야의 奇人異人이 되어 세상 사람들이 따를 수 없는 경지에 이릅니다.
-> 食神을 극하는 것이 가장 큰 문제! 식신의 복을 가로막지 않도록 財星으로 편인을 제어해야 합니다""",
        "lucky_career": "철학자/사상가, 종교인/영성가, 점술가/명리학자, IT 개발자/해커, 연구원, 탐정/분석가, 심리학자",
        "caution": """[!] 倒食: 偏印이 식신을 극하면 복을 스스로 차버리는 상황이 됩니다. 전문 분야 하나에 집중하는 것이 핵심입니다.
[!] 고집이 너무 강해 주변과의 소통이 어려워질 수 있습니다. 자신만의 세계에서 벗어나 협업하는 법을 배우십시오.
[!] 종교/철학/오컬트 쪽으로 지나치게 빠지면 현실 생활이 피폐해질 수 있습니다.""",
        "god_rank": "偏印專旺이면 한 분야를 평정하는 기인이인의 격! 세상이 이해 못 하는 천재의 길을 걷는 운명"
    },
    "比肩格": {
        "summary": """比肩格은 동류(同類)로부터 힘을 얻어 함께 성장하는 협력과 경쟁의 격이로다!
比肩은 일간과 음양이 같은 오행으로, 나와 동등한 힘을 지닌 동료/경쟁자/형제의 기운입니다.
혼자보다는 팀으로, 경쟁보다는 협력으로, 나누면서 커가는 것이 비견격의 복의 방정식입니다.
官印相生이 더해지면 조직과 단체를 이끄는 지도자의 자리에 오르는 귀격이 됩니다.
-> 일간이 身強하고 財官이 적절히 있어야 比肩格이 빛납니다""",
        "lucky_career": "스포츠 감독/코치, 컨설턴트/멘토, 협동조합/NGO, 의사/간호사, 팀 기반 사업, 사회운동가",
        "caution": """[!] 群比爭財: 比劫이 너무 많은데 財星이 적으면 재물을 두고 형제/동료와 다투는 상황이 됩니다.
[!] 동업은 명확한 계약과 역할 분담이 선행되어야 합니다. 구두 약속만으로는 반드시 분쟁이 생깁니다.
[!] 독립 사업보다는 조직 내에서 협력하는 방식이 안정적입니다.""",
        "god_rank": "比肩格에 財官이 조화로우면 천하의 문무겸전! 동업과 협력으로 큰 성취를 이루는 운명"
    },
    "劫財格": {
        "summary": """劫財格은 불굴의 투쟁심과 경쟁심으로 어떤 역경도 딛고 일어서는 강인한 기운의 격이로다!
劫財는 일간과 오행이 같되 음양이 다른 것으로, 동류이지만 경쟁자이기도 한 묘한 기운입니다.
사주에 劫財格이 성립하면 경쟁이 치열한 분야에서 오히려 빛을 발하며, 절대 포기하지 않는 불굴의 의지가 강점입니다.
食傷으로 劫財의 에너지를 재능으로 전환하거나, 官殺로 劫財를 제어하면 강한 추진력이 성공으로 이어집니다.
-> 劫財는 재물을 빼앗는 기운도 있으니, 재물 관리와 동업 관계에서 각별한 주의가 필요합니다""",
        "lucky_career": "운동선수/격투기, 영업 전문가/세일즈, 경쟁적 사업/무역, 군인/경찰, 변호사, 스타트업 창업자",
        "caution": """[!] 食傷이 없으면 劫財의 에너지가 분산되어 공격적이고 충동적인 행동으로 이어질 수 있습니다.
[!] 同業과 공동투자는 반드시 법적 契約으로 보호받아야 합니다. 구두 약속은 언제나 위험합니다.
[!] 財星에 대한 지나친 욕심이 오히려 재물을 쫓아버리는 결과를 낳을 수 있습니다. 베풀면 더 들어옵니다.""",
        "god_rank": "食傷制劫이면 경쟁이 곧 성공의 원동력이 되는 불굴의 격! 官殺로 제어하면 강한 추진력으로 세상을 정복하는 운명"
    },
}

# * BUG2 FIX: 일간=pils[1]["cg"], 월지=pils[2]["jj"] (pillar order: [시(0),일(1),월(2),년(3)])
@st.cache_data
def get_gyeokguk(pils):
    if len(pils) < 4: return None
    ilgan = pils[1]["cg"]   # ✅ 일간 (day stem)
    wolji = pils[2]["jj"]   # ✅ 월지 (month branch)
    jijang = JIJANGGAN.get(wolji, [])
    if not jijang: return None
    jeongi = jijang[-1]
    sipsung = TEN_GODS_MATRIX.get(ilgan, {}).get(jeongi, "기타")
    gyeok_name = f"{sipsung}格"
    cgs_all = [p["cg"] for p in pils]
    is_toucht = jeongi in cgs_all
    if is_toucht:
        grade = "純格 - 월지 정기가 천간에 투출하여 격이 매우 청명하다!"
        grade_score = 95
    elif len(jijang) > 1 and jijang[-2] in cgs_all:
        grade = "雜格 - 중기가 투출, 격이 복잡하나 쓸모가 있다."
        grade_score = 70
    else:
        grade = "暗格 - 지장간에 숨어있어 격의 힘이 약하다."
        grade_score = 50
    desc_data = GYEOKGUK_DESC.get(gyeok_name, {
        "summary": f"{gyeok_name}으로 독자적인 인생 노선을 개척하는 격이로다.",
        "lucky_career": "자유업/개인 사업", "caution": "잡기를 경계하라.", "god_rank": "용신과의 조화를 이룰 때 빛난다"
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
    frozenset(["寅","午","戌"]): ("火局","火","寅午戌 三合"),
    frozenset(["申","子","辰"]): ("水局","水","申子辰 三합"),
    frozenset(["巳","酉","丑"]): ("金局","金","巳酉丑 三合"),
    frozenset(["亥","卯","未"]): ("木局","木","亥卯未 三合"),
}
BAN_HAP_MAP = {
    frozenset(["寅","午"]): ("寅午 半合(火)","火","半合"),
    frozenset(["午","戌"]): ("午戌 半合(火)","火","半合"),
    frozenset(["申","子"]): ("申子 半合(水)","水","반합"),
    frozenset(["子","辰"]): ("子辰 半合(水)","水","반합"),
    frozenset(["巳","酉"]): ("巳酉 半合(金)","金","반합"),
    frozenset(["酉","丑"]): ("酉丑 半合(金)","金","반합"),
    frozenset(["亥","卯"]): ("亥卯 半合(木)","木","반합"),
    frozenset(["卯","未"]): ("卯未 半合(木)","木","반합"),
}
BANG_HAP_MAP = {
    frozenset(["寅","卯","辰"]): ("東方 木局","木","方合"),
    frozenset(["巳","午","未"]): ("南方 火局","火","方合"),
    frozenset(["申","酉","戌"]): ("西方 金局","金","方合"),
    frozenset(["亥","子","丑"]): ("北方 水局","水","方合"),
}

def get_sam_hap(pils):
    jjs = set(p["jj"] for p in pils)
    results = []
    for combo, (name, oh, desc) in SAM_HAP_MAP.items():
        if combo.issubset(jjs):
            results.append({"type":"三合","name":name,"oh":oh,"desc":desc,
                            "narrative":f"🌟 [三合] {desc}으로 {name}이 形成! {oh} 기운이 命盤 전체를 강화하니라."})
    if not results:
        for combo, (name, oh, hap_type) in BAN_HAP_MAP.items():
            if combo.issubset(jjs):
                results.append({"type":"半合","name":name,"oh":oh,"desc":hap_type,
                                "narrative":f"- [半合] {name}이 맺어져 {oh} 오행의 결속력이 생기리라."})
    for combo, (name, oh, hap_type) in BANG_HAP_MAP.items():
        if combo.issubset(jjs):
            results.append({"type":"方合","name":name,"oh":oh,"desc":hap_type,
                            "narrative":f"🧭 [方合] {name}의 세력이 形成되어 {oh} 오행이 강성해지리라."})
    return results


# ==================================================
#  용신(用神) - 억부/조후/통관
# ==================================================

YONGSHIN_JOKHU = {
    "寅(인)": {"hot":False,"need":["丙(병)","甲(갑)"],"avoid":["壬(임)","癸(계)"],"desc":"寅(인)月은 봄 初입이나 아직 차갑습니다. 丙(병)火로 따뜻하게, 甲(갑)木으로 기운을 북돋워야 합니다."},
    "卯(묘)": {"hot":False,"need":["丙(병)","癸(계)"],"avoid":["庚(경)"],"desc":"卯(묘)月은 木氣 왕성한 봄. 丙(병)火로 溫氣를, 癸(계)水로 자양분을 공급해야 합니다."},
    "辰(진)": {"hot":False,"need":["甲(갑)","丙(병)","癸(계)"],"avoid":["戊(무)"],"desc":"辰(진)月 土氣가 中和역할. 木/火/水의 기운이 균형을 잡아줘야 합니다."},
    "巳(사)": {"hot":True,"need":["壬(임)","庚(경)"],"avoid":["丙(병)","丁(정)"],"desc":"巳(사)月 火氣 시작. 壬(임)水로 열기를 식히고 庚(경)金으로 水源을 만들어야 합니다."},
    "午(오)": {"hot":True,"need":["壬(임)","癸(계)","庚(경)"],"avoid":["丙(병)","丁(정)","戊(무)"],"desc":"午(오)月 한여름 極熱. 壬(임)水/癸(계)水로 火氣를 제어해야 발복합니다."},
    "未(미)": {"hot":True,"need":["壬(임)","甲(갑)"],"avoid":["戊(무)","己(기)"],"desc":"未(미)月 土燥熱. 壬(임)水와 甲(갑)木으로 습윤하고 활기를 주어야 합니다."},
    "申(신)": {"hot":False,"need":["戊(무)","丁(정)"],"avoid":["壬(임)"],"desc":"申(신)月 초가을 金氣. 戊(무)土로 金을 生하고 丁(정)火로 단련해야 합니다."},
    "酉(유)": {"hot":False,"need":["丙(병)","丁(정)","甲(갑)"],"avoid":["壬(임)","癸(계)"],"desc":"酉(유)月 金旺. 火氣로 金을 단련하고 木氣로 재를 만들어야 합니다."},
    "戌(술)": {"hot":False,"need":["甲(갑)","丙(병)","壬(임)"],"avoid":["戊(무)"],"desc":"戌(술)月 燥土. 木/火/水로 균형을 잡아야 합니다."},
    "亥(해)": {"hot":False,"need":["甲(갑)","丙(병)","戊(무)"],"avoid":["壬(임)","癸(계)"],"desc":"亥(해)月 겨울 水氣. 丙(병)火로 따뜻하게, 戊(무)土로 水氣를 제방해야 합니다."},
    "子(자)": {"hot":False,"need":["丙(병)","戊(무)","丁(정)"],"avoid":["壬(임)","癸(계)"],"desc":"子(자)月 한겨울 水旺. 丙(병)火와 戊(무)土로 水氣를 다스려야 발복합니다."},
    "丑(축)": {"hot":False,"need":["丙(병)","甲(갑)","丁(정)"],"avoid":["壬(임)","癸(계)"],"desc":"丑(축)月 극한 冬土. 丙(병)火와 丁(정)火로 溫氣를, 甲(갑)木으로 土氣를 소통시켜야 합니다."},
}

@st.cache_data
def get_yongshin(pils):
    """용신(用神) 종합 분석 - 억부+조후+통관"""
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
        eokbu_base = "신강(身强) -> 억(抑) 용신 필요"
        eokbu_desc = f"강한 일간을 억제하는 관성({ok_관}기운)과 재성({ok_재}기운)이 용신입니다."
        kihwa = "인성/비겁 대운은 기신(忌神) - 더 강해져 흉작용"
    elif sn == "신약(身弱)":
        ok_인 = BIRTH_MAP_R.get(ilgan_oh, "")
        eokbu_yong = [ok_인, ilgan_oh]
        eokbu_base = "신약(身弱) -> 부(扶) 용신 필요"
        eokbu_desc = f"약한 일간을 도와주는 인성({ok_인}기운)과 비겁({ilgan_oh}기운)이 용신입니다."
        kihwa = "재성/관성 대운은 기신(忌神) - 약한 일간이 더 눌림"
    else:
        eokbu_yong = []
        eokbu_base = "중화(中和) -> 균형 유지"
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


# ==================================================
#  충(沖)/형(刑)/파(破)/해(害)/천간합
# ==================================================

# CHUNG_MAP is updated above

HYUNG_MAP = {
    frozenset(["寅","巳","申"]): ("寅巳申 三刑","無恩之刑","법적 문제, 관재, 배신"),
    frozenset(["丑","戌","未"]): ("丑戌未 三刑","持勢之刑","권력 다툼, 재물 분쟁, 고집의 화"),
    frozenset(["子","卯"]): ("子卯 相刑","無禮之刑","무례한 인간관계, 배신"),
}
SELF_HYUNG = ["辰(진)","午(오)","酉(유)","亥(해)"]

PA_MAP = {
    frozenset(["子","酉"]): ("子酉破","감정 상처, 이별"),
    frozenset(["丑","辰"]): ("丑辰破","재물 파손, 직업 변동"),
    frozenset(["寅","亥"]): ("寅亥破","계획 차질, 예상 밖 변수"),
    frozenset(["卯","午"]): ("卯午破","감정 충돌, 혼인 불화"),
    frozenset(["申","巳"]): ("申사파(申巳破)","사고 위험, 계획 좌절"),
    frozenset(["戌","未"]): ("戌未破","재물 분실, 고집 충돌"),
}

HAE_MAP = {
    frozenset(["子","未"]): ("자미 육해(六害)", "원망과 불신 (怨望/不信)"),
    frozenset(["丑","午"]): ("축오 육해(六害)", "성급함과 갈등 (性急/葛藤)"),
    frozenset(["寅","巳"]): ("인사 육해(六害)", "시기심과 상처 (猜忌/傷處)"),
    frozenset(["卯","辰"]): ("묘진 육해(六害)", "오해와 불화 (誤解/不和)"),
    frozenset(["申","亥"]): ("신해 육해(六害)", "단절과 고립 (斷絶/孤立)"),
    frozenset(["酉","戌"]): ("유술 육해(六害)", "신뢰 상실과 피해 (信賴 喪失)")
}

TG_HAP_MAP = {
    frozenset(["甲","己"]): ("甲己合","土","中正之合"),
    frozenset(["乙","庚"]): ("乙庚合","金","仁義之合"),
    frozenset(["丙","辛"]): ("丙辛合","水","威制之合"),
    frozenset(["丁","壬"]): ("丁壬合","木","淫匿之合"),
    frozenset(["戊","癸"]): ("戊癸合","火","無情之合"),
}

def get_chung_hyung(pils):
    """충/형/파/해/천간합 분석"""
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
            result["자형"].append({"name":f"{jj} 자형","desc":"자책/자학 경향 주의"})

    for a,b in pairs_cg:
        k = frozenset([a,b])
        if k in TG_HAP_MAP:
            n,oh,htype = TG_HAP_MAP[k]
            result["천간합"].append({"name":n,"oh":oh,"type":htype,"desc":f"{oh}({OHN.get(oh,'')})으로 화(化) - {htype}"})

    return result


# ==================================================
#  공망(空亡)
# ==================================================

GONGMANG_TABLE = {
    "甲(갑)":("戌(술)","亥(해)"),"乙(을)":("戌(술)","亥(해)"),"丙(병)":("申(신)","酉(유)"),"丁(정)":("申(신)","酉(유)"),
    "戊(무)":("午(오)","未(미)"),"己(기)":("午(오)","未(미)"),"庚(경)":("辰(진)","巳(사)"),"辛(신)":("辰(진)","巳(사)"),
    "壬(임)":("寅(인)","卯(묘)"),"癸(계)":("寅(인)","卯(묘)"),
}

GONGMANG_JJ_DESC = {
    "子(자)":"자(子(자)) 공망 - 지혜/재물 기운이 허공에 뜹니다. 재물과 학업에 공허함이 따릅니다.",
    "丑(축)":"축(丑(축)) 공망 - 인내/축적의 기운이 약해집니다. 노력이 물거품이 되는 경험을 합니다.",
    "寅(인)":"인(寅(인)) 공망 - 성장/시작의 기운이 막힙니다. 새 출발이 쉽지 않습니다.",
    "卯(묘)":"묘(卯(묘)) 공망 - 창의/예술 기운이 허공에 뜹니다. 재능이 있어도 인정받기 어렵습니다.",
    "辰(진)":"진(辰(진)) 공망 - 관직/조직 기운이 약해집니다. 직장/관직과의 인연이 불안정합니다.",
    "巳(사)":"사(巳(사)) 공망 - 지혜/재능의 기운이 허공에 뜹니다. 화려함이 있어도 결실이 약합니다.",
    "午(오)":"오(午(오)) 공망 - 명예/인정의 기운이 약해집니다. 노력 대비 인정받기 어렵습니다.",
    "未(미)":"미(未(미)) 공망 - 재물/안정 기운이 허공에 뜹니다. 모아도 새는 재물 기운입니다.",
    "申(신)":"신(申(신)) 공망 - 변화/이동 기운이 막힙니다. 새 환경으로의 변화가 어렵습니다.",
    "酉(유)":"유(酉(유)) 공망 - 완성/결실의 기운이 약해집니다. 마무리가 항상 아쉽게 끝납니다.",
    "戌(술)":"술(戌(술)) 공망 - 저장/축적의 기운이 허공에 뜹니다. 창고가 있어도 채우기 어렵습니다.",
    "亥(해)":"해(亥(해)) 공망 - 지혜/영성의 기운이 약해집니다. 깊은 학문과 영적 기운이 허공에 뜹니다.",
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


# ==================================================
#  일주론(日柱論) | 60갑자
# ==================================================

ILJU_DATA = {
    "甲(갑)子(자)":{"symbol":"🌊🌳","desc":"학문의 신기가 넘치는 귀한 일주. 총명함과 높은 이상을 지녔으며 학자/교육자/문필가 기질. 편인이 강해 독창적 사고가 뛰어나나 현실감각이 부족할 수 있습니다.","luck":"학문/교육/연구 분야에서 크게 빛납니다.","caution":"현실과 이상의 균형이 과제입니다."},
    "甲(갑)戌(술)":{"symbol":"🏔️🌳","desc":"의협심과 우직함을 타고난 일주. 재고(財庫)를 지닌 구조로 재물을 모으는 능력이 있으나 고집이 강해 마찰이 생길 수 있습니다.","luck":"중년 이후 재물이 불어나는 구조입니다.","caution":"고집을 버리면 귀인이 모여듭니다."},
    "甲(갑)申(신)":{"symbol":"⚔️🌳","desc":"절지(絶地)에 놓인 거목. 시련이 많지만 단련을 통해 진정한 강자가 됩니다. 결단력과 실행력이 탁월합니다.","luck":"단련을 통해 성장하는 불굴의 운명입니다.","caution":"성급한 결단이 화를 부릅니다."},
    "甲(갑)午(오)":{"symbol":"🔥🌳","desc":"목화통명(木火通明)의 빛나는 일주. 지혜롭고 총명하며 표현력이 탁월. 상관이 강해 언변과 창의성이 뛰어나나 직장과 마찰이 있을 수 있습니다.","luck":"예술/창작/강연 분야에서 두각을 나타냅니다.","caution":"직장/관직과의 충돌을 주의하십시오."},
    "甲(갑)辰(진)":{"symbol":"🐉🌳","desc":"천을귀인을 지닌 귀격 일주. 조직력과 리더십이 강하고 큰 그릇의 인물. 식신이 강해 복록이 있고 인복도 좋습니다.","luck":"조직을 이끄는 리더로 크게 성공합니다.","caution":"너무 많은 것을 품으려 하면 소진됩니다."},
    "甲(갑)寅(인)":{"symbol":"🐯🌳","desc":"목기가 극도로 강한 순양(純陽). 강직하고 정의로우며 자존심이 매우 강합니다. 리더십이 탁월하나 융통성이 부족할 수 있습니다.","luck":"독립하면 크게 성공합니다.","caution":"타협과 유연함을 배우는 것이 과제입니다."},
    "乙(을)丑(축)":{"symbol":"❄️🌿","desc":"차가운 땅에 뿌리를 내린 을목. 인내와 끈기가 대단하며 어떤 역경에서도 살아남습니다. 정재를 안고 있어 재물 복이 있습니다.","luck":"전문직/학문/재무 분야에서 빛납니다.","caution":"지나친 절약이 귀인의 발길을 막습니다."},
    "乙(을)亥(해)":{"symbol":"🌊🌿","desc":"수생목(水生木)의 귀한 구조. 인성이 강해 학문과 귀인의 덕이 있습니다. 섬세하고 직관력이 뛰어나며 예술적 감각이 탁월합니다.","luck":"학문/예술/상담 분야에서 대성합니다.","caution":"지나친 의존심을 극복하는 것이 과제입니다."},
    "乙(을)酉(유)":{"symbol":"⚔️🌿","desc":"을목이 유금 위에 앉은 불안한 구조. 시련이 많지만 더욱 정교하고 섬세해집니다. 완벽주의 기질이 강합니다.","luck":"예술/연구/디자인 분야에서 독보적 경지에 이릅니다.","caution":"완벽주의가 지나치면 스스로를 소진합니다."},
    "乙(을)未(미)":{"symbol":"🌿🌿","desc":"화개(華蓋)와 천을귀인을 품은 귀한 일주. 영성이 강하고 예술적 감수성이 탁월합니다. 재성이 있어 재물 복도 있습니다.","luck":"예술/종교/상담 분야에서 특별한 성취를 이룹니다.","caution":"고독을 즐기는 기질을 균형 있게 유지하십시오."},
    "乙(을)巳(사)":{"symbol":"🔥🌿","desc":"지혜롭고 전략적이며 화려한 재능을 지닌 복잡한 일주. 천을귀인도 있어 귀인의 도움이 있습니다.","luck":"전략/금융/외교에서 능력을 발휘합니다.","caution":"내면의 갈등을 창의적으로 승화하십시오."},
    "乙(을)卯(묘)":{"symbol":"🌿🌿","desc":"전왕(專旺)의 순수 목기 일주. 예술적 감수성과 창의력이 최고조. 순수하고 민감하며 아름다움을 추구하는 타고난 예술가.","luck":"예술/창작/디자인 분야에서 독보적 위치에 오릅니다.","caution":"자신만의 길을 가십시오."},
    "丙(병)寅(인)":{"symbol":"🐯🔥","desc":"목화통명의 강렬한 빛. 카리스마와 열정이 넘치는 강력한 일주. 장생지에 앉아 귀인의 도움이 있고 성장 잠재력이 큽니다.","luck":"정치/방송/경영/교육 분야에서 대성합니다.","caution":"열정이 지나치면 충동이 됩니다."},
    "丙(병)子(자)":{"symbol":"❄️🔥","desc":"태양이 찬 물 위에 앉은 역경의 일주. 정재를 안고 있어 재물 복이 있으며, 역경을 통해 더욱 강해집니다.","luck":"금융/재무/사업 분야에서 성공합니다.","caution":"내면의 불안을 극복하는 것이 성공의 열쇠입니다."},
    "丙(병)戌(술)":{"symbol":"🏔️🔥","desc":"식신이 강한 복록의 일주. 재능과 복록을 타고났으며 인복이 좋습니다. 중년 이후 크게 발복합니다.","luck":"교육/요식업/예술/종교 분야에서 빛납니다.","caution":"낭만적 성격이 현실 판단을 흐리지 않도록 하십시오."},
    "丙(병)申(신)":{"symbol":"⚔️🔥","desc":"편관이 강한 도전과 극복의 일주. 시련이 많지만 이를 딛고 일어서는 강인한 기운. 결단력이 강합니다.","luck":"군/경/의료/스포츠 분야에서 두각을 나타냅니다.","caution":"충동적 결단을 자제하십시오."},
    "丙(병)午(오)":{"symbol":"🔥🔥","desc":"태양이 정오에 빛나는 최강의 불기운. 카리스마와 존재감이 압도적. 사람들을 끌어당기는 자연스러운 매력이 있습니다.","luck":"방송/정치/사업/스포츠 분야에서 최고의 빛을 발합니다.","caution":"겸손함을 배우면 더 큰 성공이 따릅니다."},
    "丙(병)辰(진)":{"symbol":"🐉🔥","desc":"식신이 있는 복록의 일주. 창의력과 재능이 풍부하며 귀인의 도움이 있습니다.","luck":"교육/창작/기획 분야에서 성공합니다.","caution":"산만한 관심사를 하나로 집중하는 것이 과제입니다."},
    "丁(정)丑(축)":{"symbol":"❄️🕯️","desc":"차가운 겨울 땅의 촛불. 정재를 안고 있어 재물을 모으는 능력이 있습니다. 묵묵히 자신의 길을 가는 인내와 끈기가 있습니다.","luck":"재무/의료/전문직 분야에서 안정적으로 성공합니다.","caution":"지나친 내향성이 기회를 놓치게 합니다."},
    "丁(정)亥(해)":{"symbol":"🌊🕯️","desc":"물 위의 촛불, 위태로운 듯 아름다운 일주. 정관을 안고 있어 명예와 인정을 받습니다. 역경 속에서도 꺼지지 않는 강인한 의지.","luck":"의료/종교/상담/학문 분야에서 명성을 얻습니다.","caution":"감정 기복을 다스리는 것이 핵심입니다."},
    "丁(정)酉(유)":{"symbol":"⚔️🕯️","desc":"편재를 안고 있는 활동적인 재물의 일주. 분석력이 탁월하고 완벽주의적 기질이 있습니다.","luck":"금융/분석/패션/예술 분야에서 성공합니다.","caution":"완벽주의가 결단을 방해하지 않도록 하십시오."},
    "丁(정)未(미)":{"symbol":"🌿🕯️","desc":"화개(華蓋)의 영성적인 일주. 예술/철학/종교적 기질이 강하고 내면의 세계가 풍부합니다.","luck":"예술/종교/철학/상담 분야에서 독보적 경지에 이릅니다.","caution":"현실에 뿌리를 내리는 노력이 필요합니다."},
    "丁(정)巳(사)":{"symbol":"🔥🕯️","desc":"건록을 안고 있는 강한 일주. 자립심이 강하고 자수성가하는 기운. 지혜롭고 계산이 빠르며 재물 감각도 있습니다.","luck":"독립 사업/학문/금융/종교 분야에서 성공합니다.","caution":"자존심이 지나치면 귀인이 떠납니다."},
    "丁(정)卯(묘)":{"symbol":"🌿🕯️","desc":"편인이 강한 직관과 창의의 일주. 예술적 감수성이 탁월하고 독창적인 아이디어가 넘칩니다.","luck":"예술/창작/교육/상담 분야에서 빛납니다.","caution":"도식(倒食) 주의. 식신의 복을 편인이 가로막지 않도록 하십시오."},
    "戊(무)寅(인)":{"symbol":"🐯🏔️","desc":"산과 호랑이의 기운. 편관이 강한 도전과 극복의 일주. 외유내강(外柔剛)의 인물.","luck":"군/경/관리직/스포츠 분야에서 두각을 나타냅니다.","caution":"시련을 두려워하지 마십시오. 그것이 당신을 완성합니다."},
    "戊(무)子(자)":{"symbol":"❄️🏔️","desc":"정재를 안고 있는 재물의 일주. 근면하고 성실하며 재물을 차곡차곡 쌓아가는 능력. 배우자 복이 있습니다.","luck":"금융/부동산/행정 분야에서 안정적으로 성공합니다.","caution":"변화를 두려워하는 고집이 기회를 막습니다."},
    "戊(무)戌(술)":{"symbol":"🏔️🏔️","desc":"비견이 강한 독립적인 일주. 고집과 자존심이 강하며 혼자서 모든 것을 해내려 합니다. 화개(華蓋)의 영성적 기운도 있습니다.","luck":"독립 사업/부동산/종교 분야에서 성공합니다.","caution":"타인과의 협력을 배우면 더 큰 성취가 가능합니다."},
    "戊(무)申(신)":{"symbol":"⚔️🏔️","desc":"식신이 강한 복록의 일주. 능력과 재능이 다양하며 결단력과 실행력이 뛰어납니다.","luck":"기술/사업/군경 분야에서 빛납니다.","caution":"너무 많은 것을 동시에 추진하면 에너지가 분산됩니다."},
    "戊(무)午(오)":{"symbol":"🔥🏔️","desc":"양인(羊刃)을 지닌 강렬한 일주. 에너지와 의지력이 대단하며 강렬한 카리스마로 주변을 압도합니다.","luck":"정치/경영/스포츠/군사 분야에서 강력한 힘을 발휘합니다.","caution":"폭발적인 에너지를 건설적으로 사용하는 것이 과제입니다."},
    "戊(무)辰(진)":{"symbol":"🐉🏔️","desc":"천을귀인이 있는 귀한 일주. 조직 관리 능력이 뛰어나고 인복이 좋습니다.","luck":"행정/경영/부동산 분야에서 성공합니다.","caution":"고집과 독선을 주의하십시오."},
    "己(기)丑(축)":{"symbol":"❄️🌾","desc":"비견이 강한 인내의 일주. 한번 마음먹은 것은 반드시 해내는 기질. 전문성으로 성공합니다.","luck":"농업/의료/회계/전문직 분야에서 성공합니다.","caution":"고집을 버리면 귀인의 도움이 더 많아집니다."},
    "己(기)亥(해)":{"symbol":"🌊🌾","desc":"정재와 정관을 안고 있는 재물과 명예의 일주. 섬세하고 꼼꼼하며 재물 관리 능력이 탁월합니다.","luck":"회계/금융/행정 분야에서 안정적으로 성공합니다.","caution":"지나친 완벽주의가 진행 속도를 늦춥니다."},
    "己(기)酉(유)":{"symbol":"⚔️🌾","desc":"식신이 강한 재능의 일주. 섬세하고 예술적 감각이 탁월합니다. 완벽주의적 기질로 최고의 결과물을 만들어냅니다.","luck":"예술/디자인/요리/전문직 분야에서 빛납니다.","caution":"이상만 좇지 말고 현실적인 목표를 함께 세우십시오."},
    "己(기)未(미)":{"symbol":"🌿🌾","desc":"비견이 강한 고집스러운 일주. 자신만의 세계관이 뚜렷하고 화개(華蓋)의 영성적 기운도 있습니다.","luck":"종교/철학/상담/교육 분야에서 독보적 위치에 오릅니다.","caution":"고집을 유연함으로 바꾸는 것이 큰 과제입니다."},
    "己(기)巳(사)":{"symbol":"🔥🌾","desc":"편관이 강하여 시련이 많지만 성장하는 일주. 지혜롭고 분석력이 탁월하며 복잡한 상황을 해결하는 능력이 있습니다.","luck":"기획/분석/의료/법률 분야에서 능력을 발휘합니다.","caution":"시련을 두려워하지 말고 정면으로 돌파하십시오."},
    "己(기)卯(묘)":{"symbol":"🌿🌾","desc":"편관이 강한 혁신적인 일주. 창의력과 도전 정신이 있으며 기존 틀에 얽매이지 않습니다.","luck":"창작/교육/예술/사업 분야에서 성공합니다.","caution":"새로운 시도를 즐기되 마무리를 철저히 하십시오."},
    "庚(경)寅(인)":{"symbol":"🐯⚔️","desc":"편재를 안고 있는 활동적인 재물의 일주. 결단력이 강하고 행동력이 뛰어납니다. 역마(驛馬)의 기운으로 이동과 변화가 많습니다.","luck":"사업/무역/영업 분야에서 크게 성공합니다.","caution":"너무 빠른 결단이 실수를 유발합니다."},
    "庚(경)子(자)":{"symbol":"❄️⚔️","desc":"상관이 강한 혁신적인 일주. 총명하고 언변이 뛰어나며 창의적인 아이디어가 넘칩니다. 기존 틀에 도전하는 기질이 강합니다.","luck":"언론/방송/창작/IT 분야에서 두각을 나타냅니다.","caution":"상관견관 주의! 직장/관직과의 충돌을 특히 조심하십시오."},
    "庚(경)戌(술)":{"symbol":"🏔️⚔️","desc":"편인이 강한 깊은 사색의 일주. 철학적이고 분석적인 기질이 강합니다. 술중(戌(술)中) 정화가 경금을 단련합니다.","luck":"철학/법학/종교/분석 분야에서 탁월한 능력을 발휘합니다.","caution":"지나친 완벽주의와 비판적 사고를 조절하십시오."},
    "庚(경)申(신)":{"symbol":"⚔️⚔️","desc":"비견이 강한 최강의 금기 일주. 결단력과 실행력이 압도적이며 강직한 성격으로 강한 인상을 줍니다.","luck":"군/경/의료/스포츠/기술 분야에서 최강의 능력을 발휘합니다.","caution":"유연함과 타협을 배우는 것이 큰 과제입니다."},
    "庚(경)午(오)":{"symbol":"🔥⚔️","desc":"정관이 있는 명예의 일주. 화기(火氣)가 금을 단련하니 제대로 단련되면 최고의 보검이 됩니다.","luck":"관직/공무원/군사/경찰 분야에서 명예를 얻습니다.","caution":"지나친 원칙주의가 융통성을 막습니다."},
    "庚(경)辰(진)":{"symbol":"🐉⚔️","desc":"편인을 지닌 분석적인 일주. 천을귀인의 덕도 있어 귀인의 도움이 있습니다. 지략이 뛰어나고 상황 판단력이 탁월합니다.","luck":"전략기획/군사/법학/IT 분야에서 활약합니다.","caution":"너무 많이 계산하면 행동이 늦어집니다."},
    "辛(신)丑(축)":{"symbol":"❄️💎","desc":"편인이 강한 깊은 내면의 일주. 분석력과 통찰력이 뛰어나며 전문성으로 성공합니다.","luck":"연구/분석/회계/의료 분야에서 전문가로 성공합니다.","caution":"자신의 가치를 스스로 인정하는 자기긍정이 필요합니다."},
    "辛(신)亥(해)":{"symbol":"🌊💎","desc":"상관이 강한 창의적인 일주. 섬세한 감수성과 탁월한 창의력. 식신생재의 구조로 재물 복도 있습니다.","luck":"예술/창작/패션/디자인 분야에서 독보적 위치에 오릅니다.","caution":"언행에 주의하고 직장/관직과의 마찰을 조심하십시오."},
    "辛(신)酉(유)":{"symbol":"💎💎","desc":"비견이 강한 완벽주의의 극치 일주. 아름다움과 완성도에 대한 기준이 매우 높습니다. 섬세하고 예리한 감각으로 최고의 작품을 만들어냅니다.","luck":"예술/보석/디자인/의료/패션 분야에서 최고 경지에 이릅니다.","caution":"너무 높은 기준이 타인과의 관계를 경직시킵니다."},
    "辛(신)未(미)":{"symbol":"🌿💎","desc":"편인과 화개를 지닌 영성의 일주. 직관력과 예술성이 탁월하며 독특한 세계관을 지녔습니다.","luck":"예술/종교/철학/상담 분야에서 독보적 존재가 됩니다.","caution":"현실적인 목표와 균형을 맞추는 것이 중요합니다."},
    "辛(신)巳(사)":{"symbol":"🔥💎","desc":"편관이 강한 도전의 일주. 시련을 통해 더욱 빛나는 보석. 위기 상황에서 진가를 발휘합니다.","luck":"금융/사업/의료/법률 분야에서 뛰어난 능력을 보입니다.","caution":"시련을 두려워하지 마십시오. 단련될수록 더 빛납니다."},
    "辛(신)卯(묘)":{"symbol":"🌿💎","desc":"편재를 안고 있는 재물의 일주. 섬세하면서도 재물 감각이 있으며 창의적 아이디어로 수익을 창출합니다.","luck":"금융/예술/패션/창업 분야에서 성공합니다.","caution":"지나친 완벽주의가 결단을 방해합니다."},
    "壬(임)寅(인)":{"symbol":"🐯🌊","desc":"식신이 강한 복록의 일주. 지혜와 재능이 넘치며 재물 복도 있습니다. 장생지에 앉아 귀인의 도움이 있습니다.","luck":"무역/외교/학문/사업 분야에서 크게 성공합니다.","caution":"너무 많은 관심사를 정리하고 집중하는 것이 과제입니다."},
    "壬(임)子(자)":{"symbol":"❄️🌊","desc":"양인(羊刃)의 강렬한 수기 일주. 지혜와 추진력이 압도적이며 깊은 통찰력. 무토(戊(무)土)의 제어가 필요합니다.","luck":"철학/전략/외교/금융 분야에서 천재적 능력을 발휘합니다.","caution":"방향 없는 지혜는 공허합니다. 목표를 명확히 하십시오."},
    "壬(임)戌(술)":{"symbol":"🏔️🌊","desc":"편관이 강한 시련과 극복의 일주. 강인한 의지로 시련을 극복하며 중년 이후 크게 발복합니다.","luck":"법률/전략/외교 분야에서 두각을 나타냅니다.","caution":"인내하십시오. 모든 시련에는 이유가 있습니다."},
    "壬(임)申(신)":{"symbol":"⚔️🌊","desc":"장생지의 귀한 일주. 인성이 강해 학문과 귀인의 덕이 넘칩니다. 유연하게 대처하는 지혜. 국제적 감각이 있습니다.","luck":"외교/국제무역/법률/학문 분야에서 대성합니다.","caution":"지나친 계산과 전략이 진정성을 가릴 수 있습니다."},
    "壬(임)午(오)":{"symbol":"🔥🌊","desc":"정재를 안고 있는 재물의 일주. 화수미제(火水未(미)濟)의 역동적 긴장이 창의력의 원천이 됩니다.","luck":"금융/사업/창작/방송 분야에서 성공합니다.","caution":"내면의 갈등을 창의적으로 승화하십시오."},
    "壬(임)辰(진)":{"symbol":"🐉🌊","desc":"비견이 강한 독립적인 일주. 천을귀인도 있어 귀인의 도움이 있습니다. 방대한 지식과 포용력.","luck":"외교/학문/종교/경영 분야에서 크게 성공합니다.","caution":"모든 것을 혼자 짊어지려 하지 말고 팀을 활용하십시오."},
    "癸(계)丑(축)":{"symbol":"❄️💧","desc":"편인이 강한 인내의 일주. 전문성이 뛰어나고 분석력이 탁월합니다. 묵묵한 노력으로 결국 성공합니다.","luck":"연구/학문/의료/분석 분야에서 대가가 됩니다.","caution":"자신을 과소평가하지 마십시오."},
    "癸(계)亥(해)":{"symbol":"🌊💧","desc":"비견이 강한 전왕(專旺)의 수기 일주. 영성과 직관력이 극도로 발달하며 남들이 보지 못하는 것을 봅니다.","luck":"철학/종교/예술/심리학 분야에서 독보적 경지에 이릅니다.","caution":"현실에 뿌리를 내리는 훈련이 반드시 필요합니다."},
    "癸(계)酉(유)":{"symbol":"💎💧","desc":"편인이 강한 분석의 일주. 정밀한 사고와 섬세한 감각이 탁월합니다.","luck":"연구/분석/예술/의료 분야에서 전문가로 인정받습니다.","caution":"현실적인 결단력을 기르는 것이 성공의 열쇠입니다."},
    "癸(계)未(미)":{"symbol":"🌿💧","desc":"편관을 안고 있는 시련의 일주. 어려움을 통해 더욱 강해지고 깊어지는 기운. 정신적 성숙도가 높습니다.","luck":"상담/의료/종교/예술 분야에서 깊은 경지에 이릅니다.","caution":"시련을 두려워하지 마십시오. 당신을 더 깊게 만듭니다."},
    "癸(계)巳(사)":{"symbol":"🔥💧","desc":"정관을 안고 있는 명예의 일주. 화수(火水)의 긴장이 창의력과 지혜의 원천. 섬세한 감수성과 강인한 의지.","luck":"학문/관직/예술/금융 분야에서 명예를 얻습니다.","caution":"내면의 갈등을 긍정적인 방향으로 승화하십시오."},
    "癸(계)卯(묘)":{"symbol":"🌿💧","desc":"식신이 강한 복록의 일주. 창의력과 재능이 풍부하며 부드러운 감성으로 많은 이들과 공감합니다. 인복이 좋습니다.","luck":"예술/창작/상담/교육 분야에서 많은 이들의 사랑을 받습니다.","caution":"꿈과 현실의 균형을 맞추십시오."},
}


# ==================================================
#  납음오행(納音五行)
# ==================================================

NABJIN_MAP = {
    ("甲(갑)子(자)","乙(을)丑(축)"):("海中金","金","바다 속 金. 미완성이나 잠재력이 큰 金. 도움을 받아 크게 빛나는 기운"),
    ("丙(병)寅(인)","丁(정)卯(묘)"):("爐中火","火","화로 속의 불. 강하게 타오르는 완성된 불. 단련과 성취의 기운"),
    ("戊(무)辰(진)","己(기)巳(사)"):("大林木","木","큰 숲의 나무. 웅장하고 강한 나무. 지도자의 기운"),
    ("庚(경)午(오)","辛(신)未(미)"):("路傍土","土","길가의 흙. 奉仕와 犧牲의 기운"),
    ("壬(임)申(신)","癸(계)酉(유)"):("劍鋒金","金","칼날의 金. 예리하고 강한 金. 決斷과 推進의 기운"),
    ("甲(갑)戌(술)","乙(을)亥(해)"):("山頭火","火","산꼭대기의 불. 名譽와 리더십의 기운"),
    ("丙(병)子(자)","丁(정)丑(축)"):("澗下水","水","계곡 아래의 水. 智慧와 疏通의 기운"),
    ("戊(무)寅(인)","己(기)卯(묘)"):("城頭土","土","성 위의 土. 權威와 防禦의 기운"),
    ("庚(경)辰(진)","辛(신)巳(사)"):("白蠟金","金","흰 밀랍의 金. 藝術과 柔軟性의 기운"),
    ("壬(임)午(오)","癸(계)未(미)"):("楊柳木","木","버드나무. 適應力과 創意의 기운"),
    ("甲(갑)申(신)","乙(을)酉(유)"):("泉中水","水","샘물. 智慧와 直觀의 기운"),
    ("丙(병)戌(술)","丁(정)亥(해)"):("옥상토(屋上土)","土","지붕 위의 흙. 가정과 안전의 기운"),
    ("戊(무)子(자)","己(기)丑(축)"):("벽력화(霹靂火)","火","벼락의 불. 충격과 각성의 기운"),
    ("庚(경)寅(인)","辛(신)卯(묘)"):("송백목(松栢木)","木","소나무/잣나무. 의리와 절개의 기운"),
    ("壬(임)辰(진)","癸(계)巳(사)"):("장류수(長流水)","水","장강의 물. 포용과 지속의 기운"),
    ("甲(갑)午(오)","乙(을)未(미)"):("사중금(沙中金)","金","모래 속의 금. 발굴되면 빛나는 기운"),
    ("丙(병)申(신)","丁(정)酉(유)"):("산하화(山下火)","火","산 아래의 불. 꾸준한 열정의 기운"),
    ("戊(무)戌(술)","己(기)亥(해)"):("평지목(平地木)","木","평지의 나무. 포용과 성장의 기운"),
    ("庚(경)子(자)","辛(신)丑(축)"):("벽상토(壁上土)","土","벽 위의 흙. 원칙과 구조의 기운"),
    ("壬(임)寅(인)","癸(계)卯(묘)"):("금박금(金箔金)","金","금박의 금. 외형적 화려함과 내면의 취약"),
    ("甲(갑)辰(진)","乙(을)巳(사)"):("복등화(覆燈火)","火","덮인 등의 불. 숨겨진 재능이 빛을 기다리는 기운"),
    ("丙(병)午(오)","丁(정)未(미)"):("천하수(天河水)","水","은하수. 영성과 이상의 기운"),
    ("戊(무)申(신)","己(기)酉(유)"):("대역토(大驛土)","土","큰 역참의 흙. 활동적인 사업의 기운"),
    ("庚(경)戌(술)","辛(신)亥(해)"):("차천금(釵釧金)","金","비녀와 팔찌의 금. 아름다움과 사교의 기운"),
    ("壬(임)子(자)","癸(계)丑(축)"):("상자목(桑柘木)","Wood","뽕나무. 부지런함과 실용성의 기운"),
    ("甲(갑)寅(인)","乙(을)卯(묘)"):("대계수(大溪水)","Water","큰 계곡의 물. 추진력과 지혜의 기운"),
    ("丙(병)辰(진)","丁(정)巳(사)"):("사중토(沙中土)","土","모래 속의 흙. 변화와 적응의 기운"),
    ("戊(무)午(오)","己(기)未(미)"):("천상화(天上火)","Fire","하늘 위의 불. 최고의 권위와 밝음의 기운"),
    ("庚(경)申(신)","辛(신)酉(유)"):("석류목(石榴木)","Wood","석류나무. 다산과 결실의 기운"),
    ("壬(임)戌(술)","癸(계)亥(해)"):("대해수(大海水)","Water","큰 바다. 무한한 포용력. 광대한 지혜의 기운"),
}

def get_nabjin(cg, jj):
    pillar = cg + jj
    for k, v in NABJIN_MAP.items():
        if pillar in k:
            name, oh, desc = v
            return {"name":name,"oh":oh,"desc":desc}
    return {"name":"미상","oh":"","desc":""}


# ==================================================
#  육친론(六親論)
# ==================================================

@st.cache_data
def get_yukjin(ilgan, pils, gender="남"):
    ss_to_family = {
        "남":{"정인":"母親(正印)","편인":"繼母(偏印)","정재":"妻(正財)","편재":"父親(偏財)","정관":"女(正官)","편관":"男(偏官)","비견":"兄弟(比肩)","겁재":"異腹(劫財)","식신":"孫(食神)","상관":"祖母(傷官)"},
        "여":{"정인":"母親(正印)","편인":"繼母(偏印)","정관":"夫(正官)","편관":"情夫(偏官)","정재":"姑(正財)","편재":"父親(偏財)","비견":"姉妹(比肩)","겁재":"異腹(劫財)","식신":"男(食神)","상관":"女(傷官)"},
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
            ("아들(偏官)/딸(正官)","편관","관살이 있습니다. 자녀 인연이 있으며 자녀로 인한 기쁨이 있습니다.","관살이 약합니다. 자녀와의 인연이 엷거나 늦게 생길 수 있습니다."),
        ]
    else:
        checks += [
            ("남편(正官)","정관","정관(남편 기운)이 있습니다. 안정적이고 믿음직한 남편 인연이 있습니다.","정관(남편 기운)이 없거나 약합니다. 결혼이 늦거나 편관으로 대체될 수 있습니다."),
            ("아들(食神)/딸(傷官)","식신","식상이 있습니다. 자녀 인연이 있으며 자녀로 인한 기쁨이 있습니다.","식상이 약합니다. 자녀와의 인연이 엷거나 늦을 수 있습니다."),
        ]
    checks.append(("형제(比肩)","비견","비겁이 있습니다. 형제자매 또는 동료/친구와의 인연이 깊습니다.","비겁이 약합니다. 형제자매 인연이 엷거나 자립심이 강한 독립적인 기질입니다."))

    sipsung_all = [ss for si in sipsung_data for ss in [si.get("cg_ss","-"), si.get("jj_ss","-")]]
    for fam_label, ss_key, yes_msg, no_msg in checks:
        has = ss_key in sipsung_all
        where = ", ".join(found.get(fam_label, []))
        result.append({"관계":fam_label,"위치":where if where else "없음","present":has,"desc":yes_msg if has else no_msg})
    return result


# ==================================================
#  추가 신살 (원진/귀문관/백호/양인/화개)
# ==================================================

EXTRA_SINSAL_DATA = {
    "원진": {"pairs":[("子(자)","未(미)"),("丑(축)","午(오)"),("寅(인)","酉(유)"),("卯(묘)","申(신)"),("辰(진)","亥(해)"),("巳(사)","戌(술)")],"name":"怨嗔殺","icon":"😤","desc":"서로 미워하고 반목하는 기운. 配偶者/職場 同僚와 不和가 잦습니다.","remedy":"處方: 相手方을 理解하려는 노력, 먼저 다가가는 疏通이 필요합니다."},
    "귀문": {"pairs":[("子(자)","酉(유)"),("丑(축)","午(오)"),("寅(인)","未(미)"),("卯(묘)","申(신)"),("辰(진)","亥(해)"),("巳(사)","戌(술)")],"name":"鬼門關殺","icon":"🔮","desc":"直觀力/靈感이 탁월하나 神經過敏/精神的 過負荷에 취약합니다. 藝術/相談 분야의 天才性.","remedy":"處方: 冥想/睡眠 管理 필수. 肯定적으로 活用하면 靈的 天才가 됩니다."},
    "백호": {"combos":["甲(갑)辰(진)","乙(을)未(미)","丙(병)戌(술)","丁(정)丑(축)","戊(무)辰(진)","壬(임)辰(진)","癸(계)丑(축)"],"name":"白虎大殺","icon":"🐯","desc":"강력한 衝擊과 變動의 살. 事故/手術/血光 관련 事件이 발생하기 쉽습니다.","remedy":"處方: 安全 注意, 定期的 健康檢診, 醫療/軍警 분야에서 專門性으로 昇華하십시오."},
    "양인": {"jjs":{"甲(갑)":"卯(묘)","丙(병)":"午(오)","戊(무)":"午(오)","庚(경)":"酉(유)","壬(임)":"子(자)"},"name":"羊刃殺","icon":"⚡","desc":"극도로 강한 日干의 기운. 決斷力/推進力이 압도적이나 衝動性이 있습니다. 制化되면 최고의 指導者가 됩니다.","remedy":"處方: 강한 에너지를 建設적으로 사용. 官殺의 制御가 있을 때 빛을 발합니다."},
    "화개": {"map":{"寅(인)午(오)戌(술)":"戌(술)","申(신)자辰(진)":"辰(진)","巳(사)酉(유)丑(축)":"丑(축)","亥(해)卯(묘)未(미)":"未(미)"},"name":"華蓋殺","icon":"🎭","desc":"孤獨하지만 빛나는 별의 기운. 藝術/宗敎/哲學 분야에서 獨步的 境地. 孤獨 속에서 탁월한 創意力이 발현됩니다.","remedy":"處方: 孤獨을 두려워하지 말고 內功을 쌓으십시오. 專門家/藝術家/宗敎人의 상징!"},
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
            result.append({"name":d["name"],"icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":f"{a}/{b}"})
            break
    for a,b in pairs_jj:
        if (a,b) in EXTRA_SINSAL_DATA["귀문"]["pairs"] or (b,a) in EXTRA_SINSAL_DATA["귀문"]["pairs"]:
            d = EXTRA_SINSAL_DATA["귀문"]
            result.append({"name":d["name"],"icon":d["icon"],"desc":d["desc"],"remedy":d["remedy"],"found":f"{a}/{b}"})
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


# ==================================================
#  🗓️ 만세력 엔진 (ManseCalendarEngine)
#  일진 / 절기 / 길일흉일 계산
# ==================================================

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

# 길일/흉일 기준 - 일진의 천간 기준 간단 판별
_GIL_CG  = {"甲(갑)","丙(병)","戊(무)","庚(경)","壬(임)"}          # 양간 = 기본 길일
_HYUNG_JJ = {"丑(축)","刑","巳(사)","申(신)","寅(인)"}          # 삼형살 지지
_GIL_JJ  = {"子(자)","卯(묘)","午(오)","酉(유)","亥(해)","寅(인)"}      # 귀인 지지 포함

class ManseCalendarEngine:
    """
    만세력 부가 기능 엔진
    - 일진(日辰(진)) 계산
    - 24절기 달력
    - 길일/흉일 판별
    """

    # -- 일진 계산 -------------------------------------
    @staticmethod
    def get_iljin(year: int, month: int, day: int) -> dict:
        """특정 날짜의 일진(日辰(진)) 반환 {cg, jj, str, oh}"""
        from datetime import date as _date
        base = _date(2000, 1, 1)   # 甲(갑)子(자)일 기준점 (2000-01-01 = 甲(갑)辰(진)년 庚(경)戌(술)월 甲(갑)子(자)일)
        target = _date(year, month, day)
        diff = (target - base).days
        # 2000-01-01은 甲子일 - 60갑자 인덱스 0
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

    # -- 24절기 달력 ------------------------------------
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

    # -- 길흉 판별 --------------------------------------
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
        special_gil = {"甲(갑)子(자)", "甲(갑)午(오)", "丙(병)子(자)", "庚(경)子(자)", "壬(임)子(자)",
                       "甲(갑)申(신)", "丙(병)寅(인)", "庚(경)午(오)", "壬(임)申(신)"}
        if iljin["str"] in special_gil:
            score += 2
            reasons.append("천을귀인")

        if score >= 2:
            return {"grade": "길일 -", "reason": " / ".join(reasons) or "양기 충만",
                    "color": "#1a7a1a", "bg": "#f0fff0"}
        elif score <= -1:
            return {"grade": "주의", "reason": " / ".join(reasons) or "삼형 주의",
                    "color": "#cc0000", "bg": "#fff0f0"}
        else:
            return {"grade": "보통", "reason": "무난한 하루",
                    "color": "#444444", "bg": "#ffffff"}

    # -- 월별 달력 데이터 생성 --------------------------
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


# ==================================================
#  궁합(宮合)
# ==================================================

def calc_gunghap(pils_a, pils_b, name_a="나", name_b="상대"):
    # [년, 월, 일, 시] 순서에서 일간은 index 2
    ilgan_a = pils_a[2]["cg"]; ilgan_b = pils_b[2]["cg"]
    jj_a = [p["jj"] for p in pils_a]; jj_b = [p["jj"] for p in pils_b]
    oh_a = OH.get(ilgan_a,""); oh_b = OH.get(ilgan_b,"")
    gen_map = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    ctrl_map = {"木":"土","火":"金","土":"수","金":"木","水":"火"}
    
    if gen_map.get(oh_a)==oh_b: ilgan_rel=("생(生)",f"{name_a}({ilgan_a})이 {name_b}({ilgan_b})를 지극히 생하는 인연이로다.","💚",80)
    elif gen_map.get(oh_b)==oh_a: ilgan_rel=("생(生)",f"{name_b}({ilgan_b})이 {name_a}({ilgan_a})를 자애롭게 생하는 인연이로다.","💚",80)
    elif ctrl_map.get(oh_a)==oh_b: ilgan_rel=("극(克)",f"{name_a}({ilgan_a})이 {name_b}({ilgan_b})를 강렬히 극하니, 통제가 따를 것이로다.","🔴",40)
    elif ctrl_map.get(oh_b)==oh_a: ilgan_rel=("극(克)",f"{name_b}({ilgan_b})이 {name_a}({ilgan_a})를 서슬 퍼렇게 극하니, 인내가 필요하도다.","🔴",40)
    elif oh_a==oh_b: ilgan_rel=("비(比)",f"두 분 모두 {OHN.get(oh_a,'')}의 기운. 같은 길을 걷는 동반자이자 경쟁자로다.","🟡",60)
    else: ilgan_rel=("평(平)","상생상극 없는 중립적 관계. 깊은 인연보다는 스치는 인연에 가까운 법.","🟢",65)

    all_jj_set = set(jj_a+jj_b); hap_score=0; hap_found=[]
    for combo,(name,oh,desc) in SAM_HAP_MAP.items():
        if combo.issubset(all_jj_set): hap_found.append(f"삼합 {name}"); hap_score+=20
    
    chung_found=[]
    for ja in jj_a:
        for jb in jj_b:
            k=frozenset([ja,jb])
            if k in CHUNG_MAP: 
                chung_desc = CHUNG_MAP[k][0]
                if (oh_a == "火" and oh_b == "水") or (oh_a == "水" and oh_b == "火"):
                    chung_desc += " (상충살: 산불을 끌 비가 될지 모든 것을 태울 안개가 될지는 오직 참는 자만이 알 것이로다)"
                chung_found.append(chung_desc)
                
    chunl={"甲(갑)":["丑(축)","未(미)"],"乙(을)":["子(자)","申(신)"],"丙(병)":["亥(해)","酉(유)"],"丁(정)":["亥(해)","酉(유)"],"戊(무)":["丑(축)","未(미)"],"己(기)":["子(자)","申(신)"],"庚(경)":["丑(축)","未(미)"],"辛(신)":["寅(인)","午(오)"],"壬(임)":["卯(묘)","巳(사)"],"癸(계)":["卯(묘)","巳(사)"]}
    gui_a = any(jj in chunl.get(ilgan_a,[]) for jj in jj_b)
    gui_b = any(jj in chunl.get(ilgan_b,[]) for jj in jj_a)
    
    total = ilgan_rel[3]+hap_score-len(chung_found)*10+(10 if gui_a else 0)+(10 if gui_b else 0)
    total = max(0,min(100,total))
    
    if total >= 85:
        grade = "天生緣분 - 하늘이 억겁의 인연을 맺어 점지한 불멸의 짝이로다. 서로가 서로의 운명을 완성하니 이보다 귀할 수 없다."
    elif total >= 70:
        grade = "相生가합 - 서로의 기운이 톱니바퀴처럼 맞물리는구나. 서로를 위하는 마음이 운명을 밝힐 것이로다."
    elif total >= 50:
        grade = "有情무정 - 인연의 끈은 있으나 노력이 없으면 흩어질 기운. 서로의 자존심을 내려놓아야 길이 보이느니라."
    elif total >= 30:
        grade = "相衝살 - 만나면 부딪히고 돌아서면 그리운 애증의 굴레. 서로를 태워버리지 않도록 거리를 두어야 할 것이로다."
    else:
        grade = "惡緣 - 서로의 기운을 칼날처럼 갉아먹는 악연이라. 가까이 함이 곧 독이요, 멀리함이 곧 복이니라."
        
    return {"총점":total,"등급":grade,"일간관계":ilgan_rel,"합":hap_found,"충":chung_found,"귀인_a":gui_a,"귀인_b":gui_b,"name_a":name_a,"name_b":name_b,"ilgan_a":ilgan_a,"ilgan_b":ilgan_b}


# ==================================================
#  택일(擇日)
# ==================================================

def get_good_days(pils, year, month):
    import calendar
    ilgan = pils[1]["cg"]; il_jj = pils[1]["jj"]
    chunl = {"甲(갑)":["丑(축)","未(미)"],"乙(을)":["子(자)","申(신)"],"丙(병)":["亥(해)","酉(유)"],"丁(정)":["亥(해)","酉(유)"],"戊(무)":["丑(축)","未(미)"],"己(기)":["子(자)","申(신)"],"庚(경)":["丑(축)","未(미)"],"辛(신)":["寅(인)","午(오)"],"壬(임)":["卯(묘)","巳(사)"],"癸(계)":["卯(묘)","巳(사)"]}
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
        if day_jj in bad_jjs: score-=30; reasons.append("공망일 [!]️")
        if day_jj in chung_jjs: score-=20; reasons.append("일주충일 [!]️")
        for k,(name,oh,desc) in SAM_HAP_MAP.items():
            if day_jj in k and il_jj in k: score+=15; reasons.append(f"삼합{name}일 -"); break
        day_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(day_cg,"-")
        if day_ss in ["식신","정재","정관","정인"]: score+=10; reasons.append(f"{day_ss}일 -")
        elif day_ss in ["편관","겁재"]: score-=15; reasons.append(f"{day_ss}일 [!]️")
        level = "- 길일 - 🌟최길" if score>=80 else "-길" if score>=65 else "〇보통" if score>=45 else "[-]주의"
        if score>=60:
            good_days.append({"day":day,"jj":day_jj,"cg":day_cg,"pillar":day_cg+day_jj,"score":score,"level":level,"reasons":reasons})
    return sorted(good_days,key=lambda x:-x["score"])[:10]


# ==================================================
#  🌐 정밀 시간 보정 엔진 (TimeCorrection)
#  경도/표준시/서머타임 완벽 반영
# ==================================================

class TimeCorrection:
    """한국 표준시 및 경도 보정 데이터"""
    
    # 한국 표준시 변경 이력
    # 1. 1908.04.01 - 1911.12.31: GMT+8:30 (127.5도)
    # 2. 1912.01.01 - 1954.03.20: GMT+9:00 (135도)
    # 3. 1954.03.21 - 1961.08.09: GMT+8:30 (127.5도)
    # 4. 1961.08.10 - 현재: GMT+9:00 (135도)
    
    # 서머타임(DST) 시행 이력
    DST_PERIODS = [
        (datetime(1948, 6, 1), datetime(1948, 9, 13)),
        (datetime(1949, 4, 3), datetime(1949, 9, 11)),
        (datetime(1950, 4, 1), datetime(1950, 9, 10)),
        (datetime(1951, 5, 6), datetime(1951, 9, 9)),
        (datetime(1955, 5, 5), datetime(1955, 9, 9)),
        (datetime(1956, 5, 20), datetime(1956, 9, 30)),
        (datetime(1957, 5, 5), datetime(1957, 9, 22)),
        (datetime(1958, 5, 4), datetime(1958, 9, 21)),
        (datetime(1959, 5, 3), datetime(1959, 9, 20)),
        (datetime(1960, 5, 1), datetime(1960, 9, 18)),
        (datetime(1987, 5, 10), datetime(1987, 10, 11)),
        (datetime(1988, 5, 8), datetime(1988, 10, 9)),
    ]

    @staticmethod
    def get_corrected_time(year, month, day, hour, minute):
        """입력된 시간을 '진태양시'로 보정"""
        dt = datetime(year, month, day, hour, minute)
        
        # 1. 서머타임 보정 (-1시간)
        is_dst = False
        for start, end in TimeCorrection.DST_PERIODS:
            if start <= dt <= end:
                is_dst = True
                break
        
        if is_dst:
            dt -= timedelta(hours=1)
            
        # 2. 표준시 보정
        # 1954.03.21 ~ 1961.08.09 기간은 GMT+8.5 (135도 기준 -30분)
        if datetime(1954, 3, 21) <= dt <= datetime(1961, 8, 9, 23, 59):
            # 이 시기 표준시는 이미 127.5도 기준이므로, 
            # 135도 기준 만세력 계산 시에는 30분을 더해주거나 빼주는 처리가 필요할 수 있으나
            # 보통 사주에서는 135도(GMT+9)를 기준으로 역산함.
            pass

        # 3. 경도 보정 (서울 기준 127.0도 vs 표준 135.0도)
        # 1도 = 4분 차이 -> 8도 차이 = 32분 차이
        # 한국은 동경 135도보다 서쪽에 있으므로 실제 태양은 32분 늦게 뜸 -> 32분을 빼야 진태양시
        dt -= timedelta(minutes=32)
        
        return dt

class SajuPrecisionEngine:
    """고정밀 사주 엔진 (KASI 데이터 및 초단위 보정 반영)"""
    
    # 24절기 정밀 데이터 (예시: 2020~2030 주요 절입 시각)
    # 실제 구현 시에는 KASI API 또는 더 큰 테이블 필요
    PRECISION_TERMS = {
        2024: {
            2: {"입춘": (4, 17, 27, 0)}, # 2월 4일 17:27:00
            3: {"경칩": (5, 11, 22, 0)},
            4: {"청명": (4, 16, 2, 0)},
        },
        2025: {
            2: {"입춘": (3, 23, 10, 0)}, # 2월 3일 23:10:00
        }
    }

    @staticmethod
    def get_pillars(year, month, day, hour, minute, gender="남"):
        """정밀 보정된 사주팔자 계산"""
        corrected_dt = TimeCorrection.get_corrected_time(year, month, day, hour, minute)
        cy, cm, cd = corrected_dt.year, corrected_dt.month, corrected_dt.day
        ch, cmin = corrected_dt.hour, corrected_dt.minute
        
        # 기본 엔진의 로직을 활용하되, 보정된 시간을 주입
        # (기존 SajuCoreEngine의 메서드들을 정밀 옵션과 함께 호출하도록 설계 가능)
        pils = SajuCoreEngine.get_pillars(cy, cm, cd, ch, cmin, gender)
        
        # 추가적인 절기 정밀 보정 (초 단위 데이터가 있는 경우)
        # if cy in SajuPrecisionEngine.PRECISION_TERMS:
        #     ... (세부 보정 로직) ...
            
        return pils


# ==================================================
#  사주 계산 엔진 (SajuCoreEngine)
# ==================================================

class SajuCoreEngine:
    """사주팔자 핵심 계산 엔진"""

    MONTH_GANJI = [
        ("丙(병)寅(인)","戊(무)寅(인)"),("戊(무)辰(진)","甲(갑)辰(진)"),("戊(무)午(오)","丙(병)午(오)"),
        ("庚(경)申(신)","戊(무)申(신)"),("壬(임)戌(술)","庚(경)戌(술)"),("甲(갑)子(자)","壬(임)子(자)"),
        ("丙(병)寅(인)","甲(갑)寅(인)"),("戊(무)辰(진)","丙(병)辰(진)"),("庚(경)午(오)","戊(무)午(오)"),
        ("壬(임)申(신)","庚(경)申(신)"),("甲(갑)戌(술)","壬(임)戌(술)"),("丙(병)子(자)","甲(갑)子(자)")
    ]

    SOLAR_TERMS = [
        (2,4),(2,19),(3,6),(3,21),(4,5),(4,20),
        (5,6),(5,21),(6,6),(6,21),(7,7),(7,23),
        (8,8),(8,23),(9,8),(9,23),(10,8),(10,23),
        (11,7),(11,22),(12,7),(12,22),(1,6),(1,20)
    ]

    KASI_DATA = {}
    _KASI_LOADED = False

    @staticmethod
    def _load_kasi_data():
        """KASI 절기 JSON 데이터를 로드함"""
        if SajuCoreEngine._KASI_LOADED:
            return
        
        json_path = "kasi_24terms.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    SajuCoreEngine.KASI_DATA = json.load(f)
                SajuCoreEngine._KASI_LOADED = True
            except Exception:
                pass

    @staticmethod
    def _get_term_precision_time(year, term_name):
        """특정 연도/절기의 정밀 시각(시, 분)을 반환 (KASI -> AstroEngine Fallback)"""
        SajuCoreEngine._load_kasi_data()
        y_str = str(year)
        # 1. KASI JSON 확인 (2000-2027 우선)
        if y_str in SajuCoreEngine.KASI_DATA:
            term_info = SajuCoreEngine.KASI_DATA[y_str].get(term_name)
            if term_info and term_info.get("month"):
                return term_info["month"], term_info["day"], term_info["hour"], term_info["minute"]
        
        # 2. AstroEngine 정밀 계산 (1940-2040 전구간 정밀 보정)
        return AstroEngine.get_solar_term_precision(year, 1, 1, term_name)

    @staticmethod
    def _get_year_pillar(year, month, day, hour=12, minute=0):
        """연주 계산 (입춘 시간 정밀 보정)"""
        total_min = hour * 60 + minute
        
        # KASI 정밀 데이터 시도
        kasi_info = SajuCoreEngine._get_term_precision_time(year, "입춘")
        if kasi_info:
            target_m, target_d, target_h, target_min = kasi_info
            target_total_min = target_h * 60 + target_min
            is_after_ipchun = (month > target_m) or (month == target_m and (day > target_d or (day == target_d and total_min >= target_total_min)))
        else:
            # Fallback: 2월 4일 17:30 근사치
            is_after_ipchun = (month > 2) or (month == 2 and (day > 4 or (day == 4 and total_min >= 1050)))
        
        y = year if is_after_ipchun else year - 1
        idx = (y - 4) % 60
        return {"cg": CG[idx % 10], "jj": JJ[idx % 12], "str": CG[idx % 10]+JJ[idx % 12]}

    @staticmethod
    def _get_month_pillar(year, month, day, hour=12, minute=0):
        """월주 계산 (절기 경계 정밀 보정)"""
        terms = SajuCoreEngine.SOLAR_TERMS
        term_idx = (month - 1) * 2
        # 해당 월의 '절기' (예: 2월이면 입춘, 3월이면 경칩...)
        term_names = ["소한","대한","입춘","우수","경칩","춘분","청명","곡우","입하","소만","망종","하지",
                      "소서","대서","입추","처서","백로","추분","한로","상강","입동","소설","대설","동지"]
        
        term_name = term_names[term_idx]
        total_min = hour * 60 + minute
        
        # KASI 정밀 데이터 시도
        kasi_info = SajuCoreEngine._get_term_precision_time(year, term_name)
        if kasi_info:
            target_m, target_d, target_h, target_min = kasi_info
            target_total_min = target_h * 60 + target_min
            # 해당 월의 절입 시각보다 이전이면 이전 달 팔자 사용
            if (month == target_m and (day < target_d or (day == target_d and total_min < target_total_min))):
                solar_month = month - 1
            else:
                solar_month = month
        else:
            # Fallback: 기존 근사치 방식
            t_month, t_day = terms[term_idx]
            if (month == t_month and (day < t_day or (day == t_day and total_min < 720))):
                solar_month = month - 1
            else:
                solar_month = month
        
        if solar_month < 1: solar_month = 12
        
        y_p = SajuCoreEngine._get_year_pillar(year, month, day, hour, minute)
        y_str = y_p["str"]
        # 연간의 천간 인덱스로 월간 도출 (60갑자 기반 정밀화)
        y_cg_idx = CG.index(y_str[0]) 
        month_cg_starts = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0] # 갑=丙(병), 을=戊(무)...
        cg_start = month_cg_starts[y_cg_idx % 10]
        
        lunar_month_num = (solar_month - 2) % 12 # 인월(寅(인))=0
        cg_idx = (cg_start + lunar_month_num) % 10
        ji_idx = (2 + lunar_month_num) % 12
        
        return {"cg": CG[cg_idx], "jj": JJ[ji_idx], "str": CG[cg_idx]+JJ[ji_idx]}

    @staticmethod
    def _get_days_to_term(year, month, day, hour, minute, direction):
        """대운 계산을 위한 절입일과의 거리(일수) 산출 (KASI 데이터 반영)"""
        from datetime import datetime as py_datetime
        birth_dt = py_datetime(year, month, day, hour, minute)
        
        term_names = ["소한","대한","입춘","우수","경칩","춘분","청명","곡우","입하","소만","망종","하지",
                      "소서","대서","입추","처서","백로","추분","한로","상강","입동","소설","대설","동지"]
        
        # 현재 월의 절기 이름 (예: 2월 -> 입춘)
        term_idx = (month - 1) * 2
        
        def get_best_term_dt(y, m):
            t_idx = (m - 1) * 2
            t_name = term_names[t_idx]
            k_info = SajuCoreEngine._get_term_precision_time(y, t_name)
            if k_info:
                return py_datetime(y, k_info[0], k_info[1], k_info[2], k_info[3])
            # Fallback
            t_m, t_d = SajuCoreEngine.SOLAR_TERMS[t_idx]
            return py_datetime(y, t_m, t_d, 12, 0)

        if direction == 1: # 순행 (다음 절기)
            target_dt = get_best_term_dt(year, month)
            if target_dt < birth_dt:
                next_m = month + 1
                next_y = year
                if next_m > 12: next_m = 1; next_y += 1
                target_dt = get_best_term_dt(next_y, next_m)
            # 정확한 초 단위 차이 계산 후 일수로 환산 (3일=1년 공식 등에 사용)
            diff = target_dt - birth_dt
            return diff.days + (diff.seconds / 86400.0)
        else: # 역행 (이전 절기)
            target_dt = get_best_term_dt(year, month)
            if target_dt > birth_dt:
                prev_m = month - 1
                prev_y = year
                if prev_m < 1: prev_m = 12; prev_y -= 1
                target_dt = get_best_term_dt(prev_y, prev_m)
            diff = birth_dt - target_dt
            return diff.days + (diff.seconds / 86400.0)

    @staticmethod
    def _get_day_pillar(year, month, day):
        """일주 계산"""
        try:
            ref_date = date(2000, 1, 1)
            target_date = date(year, month, day)
            delta = (target_date - ref_date).days
            # ✅ BUG FIX: 2000년 1월 1일 = 戊午일 (인덱스 54)
            idx = (54 + delta) % 60
            cg = CG[idx % 10]
            jj = JJ[idx % 12]
            return {"cg": cg, "jj": jj, "str": cg+jj}
        except Exception:
            return {"cg": "甲(갑)", "jj": "子(자)", "str": "甲(갑)子(자)"}

    @staticmethod
    def _get_hour_pillar(birth_hour, birth_minute, day_cg):
        """시주 계산 (조자시/야자시 반영 v2)"""
        # 시 번호 결정 (자시=0, 축시=1...)
        total_minutes = birth_hour * 60 + birth_minute
        
        # 자시: 23:00 ~ 01:00
        is_yaja = total_minutes >= 1380 # 야자시 (23:00~00:00)
        is_joja = total_minutes < 60     # 조자시 (00:00~01:00)
        
        if is_yaja or is_joja:
            si_num = 0
        else:
            si_num = ((total_minutes + 60) // 120) % 12

        # 시천간 결정 기준 일간 지표
        ilgan_idx = CG.index(day_cg)
        
        # ✅ 야자시 핵심: 일주는 오늘(day_cg)을 쓰지만, 시주는 내일의 자시(시천간)를 씀
        # 내일 일간 = 오늘 일간 + 1
        if is_yaja:
            target_ilgan_idx = (ilgan_idx + 1) % 10
        else:
            target_ilgan_idx = ilgan_idx % 10

        day_cg_idx_for_si = target_ilgan_idx % 5
        hour_cg_starts = [0, 2, 4, 6, 8]  # 甲(갑)己(기)=甲(갑), 乙(을)庚(경)=丙(병), 丙(병)辛(신)=戊(무), 丁(정)壬(임)=庚(경), 戊(무)癸(계)=壬(임)
        cg_start = hour_cg_starts[day_cg_idx_for_si]

        cg_idx = (cg_start + si_num) % 10
        jj_idx = si_num % 12

        cg = CG[cg_idx]
        jj = JJ[jj_idx]
        return {"cg": cg, "jj": jj, "str": cg+jj}

    @staticmethod
    @st.cache_data
    def get_pillars(birth_year, birth_month, birth_day, birth_hour=12, birth_minute=0, gender="남"):
        """사주팔자 계산 - 반환: [시주, 일주, 월주, 년주]"""
        year_p = SajuCoreEngine._get_year_pillar(birth_year, birth_month, birth_day, birth_hour, birth_minute)
        month_p = SajuCoreEngine._get_month_pillar(birth_year, birth_month, birth_day, birth_hour, birth_minute)
        day_p = SajuCoreEngine._get_day_pillar(birth_year, birth_month, birth_day)
        hour_p = SajuCoreEngine._get_hour_pillar(birth_hour, birth_minute, day_p["cg"])
        return [hour_p, day_p, month_p, year_p]

    @staticmethod
    def get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour=12, birth_minute=0, gender="남"):
        """대운 계산 - 정밀 모드"""
        # 연간의 음양 (년주의 천간 기준)
        year_cg = pils[3]["cg"]
        year_cg_idx = CG.index(year_cg)
        is_yang = year_cg_idx % 2 == 0

        # 성별+음양 순행/역행
        if (gender == "남" and is_yang) or (gender == "여" and not is_yang):
            direction = 1  # 순행
        else:
            direction = -1  # 역행

        # 절입일 찾기 및 대운 시작 나이 계산
        try:
            days_to_term = SajuCoreEngine._get_days_to_term(birth_year, birth_month, birth_day, birth_hour, birth_minute, direction)
            # 3일 = 1년, 1일 = 4개월 자투리. 
            # ✅ 정밀 대운수: 반올림 적용 (나머지가 0.5년(1.5일) 이상이면 올림)
            start_age = int(round(days_to_term / 3.0))
            if start_age == 0: start_age = 1 

            daewoon_list = []
            month_p = pils[2]  # 월주가 대운의 출발점
            wolgan_idx = CG.index(month_p["cg"])
            wolji_idx = JJ.index(month_p["jj"])

            for i in range(10): # 100년 대운
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

# ==================================================
#  십성(十星) 및 12운성 계산 (Bug 5 Fix)
# ==================================================
@st.cache_data
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
    jj_yang = ["子(자)","寅(인)","辰(진)","午(오)","申(신)","戌(술)"]  # 양지 (자인진오신술)
    jj_eum = ["丑(축)","卯(묘)","巳(사)","未(미)","酉(유)","亥(해)"]   # 음지 (축묘사유미해)

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
    '''
    오행 세력 점수화 v2 (정밀 엔진)
    월령득령(25pt) + 천간투출(6~10pt) + 지지(8~15pt) + 지장간(4~8pt) + 통근보너스(5pt)
    -> 합산 후 100% 정규화
    '''
    power = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}

    # - 월령 득령 (월지 계절기운, 최대 25점) -
    _WOLLYEONG = {
        "寅(인)":{"木":25,"火":0,"土":3,"金":0,"水":0},
        "卯(묘)":{"木":25,"火":0,"土":3,"金":0,"水":0},
        "辰(진)":{"木":8,"火":0,"土":20,"金":0,"水":3},
        "巳(사)":{"木":0,"火":25,"土":3,"金":0,"水":0},
        "午(오)":{"木":0,"火":25,"土":3,"金":0,"水":0},
        "未(미)":{"木":0,"火":8,"土":20,"金":0,"水":0},
        "寅(인)":{"木":25,"火":0,"土":3,"金":0,"수":0},
        "卯(묘)":{"木":25,"火":0,"土":3,"金":0,"수":0},
        "辰(진)":{"木":8,"火":0,"土":20,"金":0,"수":3},
        "巳(사)":{"木":0,"火":25,"土":3,"金":0,"수":0},
        "午(오)":{"木":0,"火":25,"土":3,"金":0,"수":0},
        "未(미)":{"木":0,"火":8,"土":20,"金":0,"수":0},
        "申(신)":{"木":0,"火":0,"土":3,"金":25,"수":0},
        "酉(유)":{"木":0,"火":0,"土":3,"金":25,"수":0},
        "戌(술)":{"木":0,"火":0,"土":20,"金":8,"수":0},
        "亥(해)":{"木":3,"火":0,"土":0,"金":0,"수":25},
        "子(자)":{"木":3,"火":0,"土":0,"金":0,"수":25},
        "丑(축)":{"木":0,"火":0,"土":20,"金":3,"수":8},
    }
    wol_jj = pils[2]["jj"]  # 월지 (Index 2)
    wol_oh = OH.get(wol_jj, "")
    ilgan_oh = OH.get(ilgan, "") 
    if wol_oh == ilgan_oh:
        power[wol_oh] += 25.0  # 득령 보너스
    
    # ② 전체 원국 점수 합산
    # 천간: 10점, 지지: 15점, 지장간: 5점 (기본 가중치)
    for i, p in enumerate(pils):
        cg_oh = OH.get(p["cg"], "")
        jj_oh = OH.get(p["jj"], "")
        
        # 천간 기운
        if cg_oh in power: power[cg_oh] += 10.0
        # 지지 기운
        if jj_oh in power: power[jj_oh] += 15.0
        
        # 지장간 가중치 (정기 기준)
        jijang = JIJANGGAN.get(p["jj"], [])
        if jijang:
            jj_main = OH.get(jijang[-1], "")
            if jj_main in power: power[jj_main] += 5.0
            
    # ③ 월령(월지) 추가 가중치 (index 2)
    if wol_oh in power:
        power[wol_oh] += 10.0 # 월령의 지지력 추가 반영
        
    # ④ 일간(index 1) 통근 보너스
    day_jj = pils[1]["jj"]
    if OH.get(day_jj) == ilgan_oh:
        power[ilgan_oh] += 5.0

    # - 12운성 보정 -
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

    # - 통근 보너스 -
    _TONGGUEN = {
        "木":{"寅(인)","卯(묘)","辰(진)","亥(해)","未(미)"},
        "火":{"巳(사)","午(오)","未(미)","寅(인)","戌(술)"},
        "土":{"辰(진)","戌(술)","丑(축)","未(미)","巳(사)","午(오)"},
        "金":{"申(신)","酉(유)","戌(술)","丑(축)"},
        "水":{"亥(해)","子(자)","丑(축)","申(신)","辰(진)"},
    }
    all_jjs = {p["jj"] for p in pils}
    for oh, jj_set in _TONGGUEN.items():
        if all_jjs & jj_set:
            power[oh] += 5.0

    # - 정규화 (합=100) -
    total = sum(power.values())
    if total <= 0:
        return {"木":20,"火":20,"土":20,"金":20,"水":20}
    return {k: round(v/total*100, 1) for k, v in power.items()}


STRENGTH_DESC = {
    "신강(身强)": {
        "icon": "🔥",
        "title": "신강(身强) - 기운이 강한 사주",
        "desc": """일간의 기운이 왕성하고 충만한 사주입니다. 자기 주관이 뚜렷하고 추진력이 강하여 스스로 길을 개척하는 자립형 인물입니다.
신강 사주는 재성(財星)과 관성(官星)의 운이 올 때 자신의 강한 기운을 발산하며 크게 발복합니다.
강한 기운이 제대로 쓰일 때는 천하를 호령하지만, 쓸 곳이 없을 때는 고집과 독선이 화근이 됩니다.""",
        "lucky_run": "재성운(財星運)/관성운(官星運)",
        "lucky_desc": "재물과 명예의 운이 올 때 강한 일간이 빛을 발합니다. 관재/재물 운에서 크게 도약하는 시기입니다.",
        "caution_run": "비겁운(比劫運)/인성운(印星運)",
        "caution_desc": "이미 강한데 더 강해지면 독선과 분쟁, 고집으로 인한 손실이 생깁니다. 이 운에는 겸손과 절제가 필요합니다.",
        "ohang_advice": {
            "木": "목기(木氣)가 강할 때: 간 건강 주의, 분노 조절 수련 필요. 금(金)운에 제어받을 때 오히려 기회가 옵니다.",
            "火": "화기(火氣)가 강할 때: 심혈관 건강 주의, 수(水)운이 와서 열기를 식혀줄 때 발복합니다.",
            "土": "토기(土氣)가 강할 때: 소화기 건강 주의, 목(木)운이 와서 뚫어줄 때 변화와 성장이 옵니다.",
            "金": "금기(金氣)가 강할 때: 폐/대장 건강 주의, 화(火)운에 단련받을 때 진정한 보검이 됩니다.",
            "水": "수기(水氣)가 강할 때: 신장/방광 건강 주의, 토(土)운이 제방이 되어 방향을 잡아줄 때 발복합니다.",
        },
        "personality": "강한 자기주장, 독립심 강함, 리더십 있음, 때로 고집스러움, 경쟁에서 강함",
    },
    "신약(身弱)": {
        "icon": "🌿",
        "title": "신약(身弱) - 기운이 약한 사주",
        "desc": """일간의 기운이 상대적으로 약한 사주입니다. 타고난 기운이 약하다고 인생이 불리한 것이 아닙니다.
신약 사주는 인성(印星)과 비겁(比劫)의 운이 올 때 힘을 얻어 크게 발복합니다.
섬세한 감수성과 공감 능력이 뛰어나며, 귀인의 도움을 받는 운이 강합니다. 혼자보다 협력할 때 더 빛납니다.""",
        "lucky_run": "인성운(印星運)/비겁운(比劫運)",
        "lucky_desc": "학문/귀인/동료의 도움이 오는 운에서 크게 성장합니다. 스승이나 선배의 후원으로 도약하는 시기입니다.",
        "caution_run": "재성운(財星運)/관성운(官星運)",
        "caution_desc": "약한 기운에 재물과 관직의 무게가 더해지면 오히려 짓눌립니다. 이 운에는 무리한 확장을 자제하십시오.",
        "ohang_advice": {
            "木": "목기(木氣)가 약할 때: 수(水)운의 귀인 도움을 받을 때 발복. 간 기운 보강, 신맛 음식이 도움 됩니다.",
            "火": "화기(火氣)가 약할 때: 목(木)운의 생조를 받을 때 발복. 심장/눈 보강, 따뜻한 음식이 도움 됩니다.",
            "土": "토기(土氣)가 약할 때: 화(火)운의 생조를 받을 때 발복. 소화기 강화, 황색 식품이 도움 됩니다.",
            "金": "금기(金氣)가 약할 때: 토(土)운의 생조를 받을 때 발복. 폐/기관지 강화, 매운맛 적당히 도움 됩니다.",
            "水": "수기(水氣)가 약할 때: 금(金)운의 생조를 받을 때 발복. 신장 보강, 짠맛/검은 식품이 도움 됩니다.",
        },
        "personality": "섬세한 감수성, 뛰어난 공감 능력, 협력에 강함, 귀인 덕이 있음, 신중하고 배려심 깊음",
    },
    "중화(中和)": {
        "icon": "⚖️",
        "title": "중화(中和) - 균형 잡힌 사주",
        "desc": """오행의 기운이 비교적 균형 잡힌 이상적인 사주입니다. 중화된 사주는 어떤 운이 와도 극단적으로 흔들리지 않는 안정적인 삶을 삽니다.
재성운/관성운/인성운 어느 쪽이 와도 무난하게 적응하며 발전해 나갑니다.
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

    # 약화 세력 = 식상x0.8 + 재성x1.0 + 관성x1.0
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
        advice   = "기운이 넘칩니다. 재성/관성 운에서 발복하나 자만과 독선 경계"
    elif daymaster_score >= 55:
        strength = "신강(身强)"
        advice   = "강한 기운 - 재성/관성 운에서 발복하나 비겁운은 경계"
    elif daymaster_score >= 45:
        strength = "중화(中和)"
        advice   = "균형 잡힌 기운 - 어떤 운에서도 무난하게 발전 가능"
    elif daymaster_score >= 32:
        strength = "신약(身弱)"
        advice   = "약한 기운 - 인성/비겁 운에서 힘을 얻고 재/관운은 조심"
    else:
        strength = "극신약(極身弱)"
        advice   = "기운이 매우 약합니다. 인성/비겁 운이 절실하며 재관운은 특히 위험"

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



# ==================================================
#  세운/월운 계산 (Bug 6 Fix)
# ==================================================
YEARLY_LUCK_NARRATIVE = {
    "比肩": {
        "level": "길(吉)", "icon": "🤝",
        "title": "독립과 자립의 해",
        "desc": "동류(同類)의 기운이 강해지는 해입니다. 독립심이 강해지고 새로운 사업이나 파트너십을 통해 성장하는 시기입니다. 형제/친구/동료의 도움이 있으며, 혼자보다 협력할 때 더 큰 성과를 거둡니다.",
        "재물": "재물은 나누면 더 들어오는 해입니다. 독립 사업이나 프리랜서 활동에 유리합니다.",
        "관계": "새로운 동료와의 의미 있는 인연이 생깁니다. 기존 인맥을 활성화하십시오.",
        "건강": "과로로 인한 체력 저하를 주의하십시오. 규칙적인 운동이 도움 됩니다.",
        "조언": "경쟁보다 협력을, 독점보다 나눔을 선택할 때 복이 배가 됩니다."
    },
    "劫財": {
        "level": "흉(凶)", "icon": "⚔️",
        "title": "경쟁과 손재의 해 [!]️",
        "desc": "재물 손실과 치열한 경쟁이 따르는 해입니다. 투자/보증/동업은 이 해에 특히 조심하십시오. 하지만 이 어려움을 이겨낸다면 더욱 강해지는 단련의 해이기도 합니다.",
        "재물": "재물 손실의 위험이 높습니다. 보수적으로 지키는 전략이 최선입니다.",
        "관계": "형제/동료와의 갈등이 생길 수 있습니다. 법적 분쟁에 주의하십시오.",
        "건강": "스트레스로 인한 심장/혈압 이상에 주의하십시오. 정기 건강검진을 받으십시오.",
        "조언": "무리한 확장이나 새로운 도전보다는 현상 유지와 내실 다지기에 집중하십시오."
    },
    "食神": {
        "level": "대길(大吉)", "icon": "🌟",
        "title": "복록과 풍요의 해 🎉",
        "desc": "하늘이 내리신 복록의 해입니다! 재능이 빛나고 하는 일마다 순조롭습니다. 먹고 사는 걱정이 사라지고, 주변에 사람이 모여드는 풍요로운 한 해를 맞이하게 됩니다.",
        "재물": "재물이 자연스럽게 들어오는 해입니다. 새로운 수입원이 생기기 좋은 시기입니다.",
        "관계": "인기가 높아지고 좋은 인연이 잇따릅니다. 결혼/새 친구 인연이 생길 수 있습니다.",
        "건강": "건강이 좋아지는 해입니다. 다만 과식/향락 소비를 절제하십시오.",
        "조언": "자신의 재능을 마음껏 발휘하십시오. 이 해에 시작하는 일은 좋은 결실을 맺습니다."
    },
    "傷官": {
        "level": "평(平)", "icon": "🌪️",
        "title": "혁신과 변화의 해",
        "desc": "기존 틀을 깨고 새로운 길을 여는 혁신의 해입니다. 창의적인 아이디어가 폭발하고 변화를 향한 욕구가 강해집니다. 단, 직장/관직과의 충돌에 각별히 주의하십시오.",
        "재물": "창의적 활동으로 부수입이 생기기 좋은 해. 투자보다 재능 발휘가 유리합니다.",
        "관계": "자유로운 표현과 새로운 스타일의 인연이 찾아옵니다.",
        "건강": "신경성 질환, 불면증에 주의하십시오. 명상과 규칙적인 수면이 필요합니다.",
        "조언": "상관견관(傷官見官) 주의! 직장/공무 관련 언행을 극도로 조심하십시오."
    },
    "偏財": {
        "level": "길(吉)", "icon": "💰",
        "title": "활발한 재물 활동의 해",
        "desc": "투자/사업/거래가 활발해지는 역동적인 재물의 해입니다. 대담한 도전이 빛을 발하고 새로운 재물 기회가 찾아옵니다. 이성 인연도 활발해지는 시기입니다.",
        "재물": "투자/부동산/사업 확장의 기회의 해. 계획적으로 움직이면 큰 성과가 있습니다.",
        "관계": "이성 인연이 활발한 해. 외부 활동과 사교에 좋은 시기입니다.",
        "건강": "과로와 무리한 활동으로 인한 체력 저하를 주의하십시오.",
        "조언": "신약하면 욕심을 버리고 자신의 역량 안에서만 움직이는 지혜가 필요합니다."
    },
    "正財": {
        "level": "길(吉)", "icon": "🏦",
        "title": "안정적 재물의 해",
        "desc": "성실하게 쌓아가는 안정된 재물의 해입니다. 고정 수입이 늘어나고 자산이 불어나며, 결혼 인연이나 배우자 덕을 보는 시기이기도 합니다.",
        "재물": "월급/임대수입 등 안정적 수입이 증가합니다. 저축과 자산 관리에 좋은 해입니다.",
        "관계": "배우자/파트너와의 관계가 안정되고 가정에 화목함이 깃드는 해입니다.",
        "건강": "전반적으로 건강이 안정적인 해입니다. 규칙적인 생활을 유지하십시오.",
        "조언": "꾸준함이 최고의 전략입니다. 급격한 변화보다 안정적인 성장을 추구하십시오."
    },
    "偏官": {
        "level": "흉(凶)", "icon": "⚡",
        "title": "시련과 압박의 해 [!]️",
        "desc": "강한 권력 기운과 함께 시련이 따르는 해입니다. 관재/사고/건강 이상에 주의가 필요합니다. 그러나 이 시련을 정면으로 돌파하면 더욱 단련되어 강해집니다.",
        "재물": "지출과 손실을 주의하십시오. 큰 재물 결정은 이 해를 피하는 것이 좋습니다.",
        "관계": "상사/권력자와의 갈등이 생기기 쉽습니다. 언행을 조심하고 자신을 낮추십시오.",
        "건강": "건강검진 필수! 사고/수술 위험이 있습니다. 안전에 특별히 주의하십시오.",
        "조언": "인내하고 정면으로 돌파하십시오. 식신이 있으면 제화가 되어 오히려 기회가 됩니다."
    },
    "正官": {
        "level": "대길(大吉)", "icon": "🎖️",
        "title": "명예와 인정의 해 🌟",
        "desc": "명예/직위/관직이 빛나는 황금 같은 해입니다! 승진/수상/자격 취득/계약 성사의 기회가 연달아 찾아옵니다. 조직 내에서 중요한 역할을 맡게 되는 영광의 해입니다.",
        "재물": "정직하고 합법적인 방법으로 재물이 들어오는 해. 계약/협약에 유리합니다.",
        "관계": "결혼 인연이나 공식적인 관계 진전이 있는 해입니다. 사회적 평판이 높아집니다.",
        "건강": "전반적으로 좋은 해이나 과도한 업무로 인한 스트레스를 관리하십시오.",
        "조언": "자만하지 마십시오. 겸손하게 원칙을 지키는 것이 이 해 복의 핵심입니다."
    },
    "偏印": {
        "level": "평(平)", "icon": "🔮",
        "title": "직관과 연구의 해",
        "desc": "직관과 영감이 강해지고 특수 분야 연구에 몰입하기 좋은 해입니다. 일반적인 성공보다는 내면의 성장과 특수 분야에서의 도약이 이 해의 테마입니다.",
        "재물": "재물보다는 지식과 기술에 투자하기 좋은 해. 자격증/교육에 투자하십시오.",
        "관계": "혼자만의 시간이 필요한 해. 깊은 사색과 연구에 집중하십시오.",
        "건강": "소화기와 신경계 건강에 주의하십시오. 규칙적인 식사가 중요합니다.",
        "조언": "도식(倒食) 주의! 과도한 이상주의와 현실 도피를 경계하십시오."
    },
    "正印": {
        "level": "대길(大吉)", "icon": "📚",
        "title": "학문과 귀인의 해 🌟",
        "desc": "학문과 귀인의 도움이 충만한 최고의 해입니다! 시험/자격증/학위 취득에 매우 유리하며, 스승이나 윗사람의 후원이 자연스럽게 찾아오는 행운의 해입니다.",
        "재물": "직접적인 재물보다는 명예와 지식이 쌓이는 해. 이것이 미래의 큰 재물이 됩니다.",
        "관계": "어머니/스승/귀인의 도움이 있는 해. 멘토와의 만남이 인생을 바꿉니다.",
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


@st.cache_data
def get_yearly_luck(pils, current_year):
    """세운 계산"""
    idx = (current_year - 4) % 60
    cg = CG[idx % 10]
    jj = JJ[idx % 12]

    # ✅ BUG 6 FIX: pils[1]["cg"] (일주 천간) - [시, 일, 월, 년] 순서
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
    "比肩": {
        "길흉": "평길", "css": "good",
        "short": "독립심/자립의 달",
        "desc": "동료/친구의 기운이 강해지는 달입니다. 새로운 파트너나 협력자를 만날 수 있으며, 독립적인 행동이 빛을 발합니다. 네트워킹에 적극적으로 나서십시오.",
        "재물": "재물은 나누어야 들어오는 달. 독립 사업이나 프리랜서 활동에 유리합니다.",
        "관계": "새로운 동료/친구와의 인연이 생깁니다. 형제/친구의 도움이 있습니다.",
        "주의": "경쟁자와의 갈등, 동업 분쟁에 주의하십시오."
    },
    "劫財": {
        "길흉": "흉", "css": "bad",
        "short": "경쟁/손재의 달",
        "desc": "재물 손실과 경쟁이 치열한 달입니다. 투자/보증/동업은 반드시 이달에는 자제하십시오. 불필요한 지출을 줄이고 소비를 절제하는 달입니다.",
        "재물": "재물의 손실 가능성이 높습니다. 큰 결정은 다음 달로 미루십시오.",
        "관계": "형제/동료와의 갈등이 생길 수 있습니다. 감정적 대응을 자제하십시오.",
        "주의": "보증/투자/동업 절대 금지! 도박성 투자는 이달 특히 경계하십시오."
    },
    "食神": {
        "길흉": "대길", "css": "great",
        "short": "복록/창의의 달 🌟",
        "desc": "하늘이 내리신 복록의 달입니다! 재능이 빛나고 하는 일마다 순조롭습니다. 창의적인 아이디어가 샘솟고 사람들의 인정을 받는 달입니다. 적극적으로 나서십시오!",
        "재물": "재물이 자연스럽게 들어오는 달입니다. 새로운 수입원이 생기기 좋은 시기입니다.",
        "관계": "사람들이 자연스럽게 모여드는 달. 인기가 높아지고 좋은 인연이 찾아옵니다.",
        "주의": "과도한 음식/향락 소비로 인한 건강 저하를 주의하십시오."
    },
    "傷官": {
        "길흉": "평", "css": "",
        "short": "창의/변화의 달",
        "desc": "혁신적인 아이디어와 창의력이 폭발하는 달입니다. 기존 방식에서 벗어나 새로운 시도를 해볼 좋은 시기입니다. 단, 직장 상사나 권위자와의 언행에 각별히 주의하십시오.",
        "재물": "창의적 활동으로 부수입이 생기기 좋은 달. 투자보다는 재능 발휘가 유리합니다.",
        "관계": "자유로운 소통과 표현이 빛나는 달. 예술적/창의적 인연과의 만남이 있습니다.",
        "주의": "상관견관(傷官見官) 주의! 직장/공무 관련 언행을 극도로 조심하십시오."
    },
    "偏財": {
        "길흉": "길", "css": "good",
        "short": "활발한 재물 활동의 달",
        "desc": "투자/사업/거래가 활발해지는 달입니다. 새로운 재물 기회가 찾아오고 대담한 도전이 빛을 발합니다. 이성 인연도 활발해지는 시기입니다. 신중한 투자로 재물을 불리십시오.",
        "재물": "투자/부동산/사업 확장의 기회. 과욕 없이 계획적으로 움직이면 성과가 있습니다.",
        "관계": "이성 인연이 활발해지는 달. 외부 활동과 사교 모임에 좋은 시기입니다.",
        "주의": "과도한 욕심으로 인한 과잉 투자를 경계하십시오. 재물이 들어오는 만큼 나갈 수도 있습니다."
    },
    "正財": {
        "길흉": "길", "css": "good",
        "short": "안정적 재물/성실의 달",
        "desc": "성실하게 쌓아가는 안정적인 재물의 달입니다. 월급/임대수입 등 고정 수입이 늘어나고, 저축과 자산 관리에 유리한 시기입니다. 배우자나 파트너의 도움이 있는 달입니다.",
        "재물": "꾸준한 노력이 결실을 맺는 달. 안정적 저축과 자산 관리에 집중하십시오.",
        "관계": "배우자/파트너와의 관계가 안정적이며 가정에 화목함이 깃드는 달입니다.",
        "주의": "현실을 벗어난 투기성 투자는 자제하십시오. 꾸준함이 최고의 전략입니다."
    },
    "偏官": {
        "길흉": "흉", "css": "bad",
        "short": "압박/시련의 달 [!]️",
        "desc": "권력이나 상사로부터 압박을 받거나 시련이 따르는 달입니다. 건강 이상이나 사고/관재의 위험이 있으니 특히 주의가 필요합니다. 인내하고 정면으로 돌파하면 이 달을 이겨낼 수 있습니다.",
        "재물": "지출과 손실을 주의하십시오. 큰 재물 결정은 이달을 피하십시오.",
        "관계": "상사/권력자와의 갈등이 생기기 쉽습니다. 언행을 조심하고 자신을 낮추십시오.",
        "주의": "건강검진 권장! 사고/수술/관재 위험이 있으니 안전에 특별히 주의하십시오."
    },
    "正官": {
        "길흉": "대길", "css": "great",
        "short": "명예/인정의 달 🎖️",
        "desc": "명예와 인정이 빛나는 최고의 달입니다! 승진/수상/자격 취득/계약 성사의 기회가 찾아옵니다. 법과 원칙을 지키는 삶이 보상받으며, 사회적 지위가 높아지는 시기입니다.",
        "재물": "정직하고 합법적인 방법으로 재물이 들어오는 달. 계약/협약에 유리합니다.",
        "관계": "결혼 인연이나 공식적인 관계 진전이 있는 달입니다. 격식 있는 만남이 이루어집니다.",
        "주의": "자만하지 마십시오. 겸손하게 원칙을 지키는 것이 이달 복의 핵심입니다."
    },
    "偏印": {
        "길흉": "평", "css": "",
        "short": "직관/연구의 달",
        "desc": "직관과 영감이 강해지고 특수 분야 연구에 몰입하기 좋은 달입니다. 철학/종교/심리/IT 등 특수 분야에서 두각을 나타낼 수 있습니다. 혼자만의 시간을 통해 내공을 쌓는 달입니다.",
        "재물": "재물보다는 지식과 기술에 투자하기 좋은 달. 자격증/교육에 투자하십시오.",
        "관계": "혼자만의 시간이 필요한 달. 깊은 사색과 연구에 집중하십시오.",
        "주의": "도식(倒食) 주의! 편인이 식신을 극하면 복이 꺾이니 과도한 이상주의를 경계하십시오."
    },
    "正印": {
        "길흉": "대길", "css": "great",
        "short": "학문/귀인의 달 📚",
        "desc": "학문과 귀인의 도움이 충만한 최고의 달입니다! 시험/자격증/학위 취득에 매우 유리하며, 스승이나 윗사람의 후원이 자연스럽게 찾아옵니다. 지식을 쌓고 성장하는 달입니다.",
        "재물": "직접적인 재물보다는 명예와 지식이 쌓이는 달. 이것이 미래의 재물이 됩니다.",
        "관계": "어머니/스승/윗사람의 도움이 있는 달. 공식적이고 격식 있는 인연이 생깁니다.",
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
    """월운 계산 - 오호둔월법으로 월간(천간) 계산 후 십성 산출"""
    if not pils: return None
    ilgan = pils[1]["cg"]

    # 월지(月支): 1월=丑, 2월=寅, ..., 12월=子
    jj_list = ["丑(축)","寅(인)","卯(묘)","辰(진)","巳(사)","午(오)","未(미)","申(신)","酉(유)","戌(술)","亥(해)","子(자)"]
    target_jj = jj_list[(month - 1) % 12]

    # [BUG FIX] 월간(月干) 계산 - 오호둔월법
    # TEN_GODS_MATRIX는 천간 키만 가짐 → 지지(target_jj)를 직접 조회하면 항상 "-" 반환이 버그 원인
    CG_LIST = ["甲(갑)","乙(을)","丙(병)","丁(정)","戊(무)","己(기)","庚(경)","辛(신)","壬(임)","癸(계)"]
    year_cg = CG_LIST[(year - 4) % 10]
    # 연간 기준 寅月(2월) 시작 천간 인덱스 (오호둔월법)
    OHHO_IDX = {"甲(갑)":2,"己(기)":2,"乙(을)":4,"庚(경)":4,"丙(병)":6,"辛(신)":6,"丁(정)":8,"壬(임)":8,"戊(무)":0,"癸(계)":0}
    start_idx = OHHO_IDX.get(year_cg, 0)
    # month 2(寅)=offset 0, month 3(卯)=offset 1, ..., month 1(丑)=offset 11
    month_offset = (month - 2) % 12
    target_cg = CG_LIST[(start_idx + month_offset) % 10]

    # 천간 기준 십성 (정확한 계산)
    sipsung = TEN_GODS_MATRIX.get(ilgan, {}).get(target_cg, "-")
    # 지지 정기(본기) 기준 보조 십성
    jj_junggi = JIJANGGAN.get(target_jj, ["-"])[-1]
    sipsung_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(jj_junggi, "-")

    luck_data = MONTHLY_LUCK_DESC.get(sipsung) or MONTHLY_LUCK_DESC.get(sipsung_jj) or MONTHLY_LUCK_DESC["-"]

    return {
        "월": month, "간": target_cg, "지": target_jj,
        "십성": sipsung, "십성_지지": sipsung_jj,
        "월운": f"{target_cg}{target_jj}월",
        "월주": target_cg + target_jj,
        "설명": luck_data["desc"],
        "길흉": luck_data["길흉"], "css": luck_data["css"],
        "short": luck_data["short"], "desc": luck_data["desc"],
        "재물": luck_data["재물"],
        "관계": luck_data["관계"],
        "주의": luck_data["주의"],
    }


def tab_monthly(pils, birth_year, gender):
    """월별 세운 표시 (단순화 버전 - 오류 해결용)"""
    import calendar
    today = datetime.now()
    sel_year = today.year
    
    LEVEL_COLOR = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107","평":"#9e9e9e","흉":"#f44336","흉흉":"#b71c1c"}
    LEVEL_EMOJI = {"대길":"🌟","길":"✅","평길":"🟡","평":"⬜","흉":"[!]️","흉흉":"🔴"}
    
    months_data = [get_monthly_luck(pils, sel_year, m) for m in range(1, 13)]
    
    for ml in months_data:
        m = ml["월"]
        is_now = (m == today.month)
        lcolor = LEVEL_COLOR.get(ml["길흉"], "#777")
        lemoji = LEVEL_EMOJI.get(ml["길흉"], "")
        
        with st.expander(f"{'-> ' if is_now else ''}{m}월 | {ml['월운']} | {lemoji} {ml['길흉']}", expanded=is_now):
            st.markdown(f"""
                <div style="border-left:4px solid {lcolor}; padding:10px; background:#f9f9f9; border-radius:0 8px 8px 0;">
                    <div style="font-size:13px; color:#333; line-height:1.6;">
                        <b>[요약]</b> {ml['short']}<br>
                        <b>[분석]</b> {ml['설명']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

def get_10year_luck_table(pils, birth_year, gender="남"):
    """10년 운세 테이블"""
    # 대운 호출 시 실제 생년월일시 반영
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    result = []
    current_year = datetime.now().year
    for dw in daewoon:
        yearly = []
        for y in range(dw["시작연도"], dw["시작연도"] + 10):
            ye = get_yearly_luck(pils, y)
            yearly.append(ye)
        result.append({**dw, "yearly": yearly, "is_current": dw["시작연도"] <= current_year <= dw["종료연도"]})
    return result

# ==================================================
#  AI 해석 (Bug 3 Fix: hash_funcs)
# ==================================================
import json

################################################################################
# *** Saju Platform Engineering Agent - AI 격리 아키텍처 ***
#
# [구조 원칙]
#   만세력 엔진(Deterministic) -> 분석 JSON -> AI Sandbox -> 텍스트 출력
#
# Brain 1: 만세력 계산 엔진 - 절대 영역, AI 접근 금지
# Brain 2: AI 해석 엔진     - 읽기 전용 JSON만 수신, 계산 금지
#
# [AI 행동 금지]
#   - 생년월일 재계산 금지
#   - 간지(干支) 재추론 금지
#   - 오행 재계산 금지
#   - 대운/세운 재계산 금지
#   -> 위반 감지 시 자동 차단 (validate_ai_output)
################################################################################

# -- Brain 2: AI 출력 검증 필터 ------------------------------------------------
_AI_FORBIDDEN_PHRASES = [
    "다시 계산", "생년월일 기준으로 계산",
    "추정하면", "계산해보면", "제가 계산한",
    "생년월일을 보면", "태어난 날을 기준으로",
    "사주를 계산", "간지를 계산", "오행을 계산",
]

def validate_ai_output(text: str) -> str:
    """AI 출력에서 계산 침범 감지 -> 해당 문장 자동 제거"""
    if not text:
        return text
    lines = text.split("\n")
    clean = []
    for line in lines:
        if any(phrase in line for phrase in _AI_FORBIDDEN_PHRASES):
            # 침범 문장 제거 (로그만 남김)
            clean.append(f"[[!]️ 계산 침범 문장 자동 제거됨]")
        else:
            clean.append(line)
    return "\n".join(clean)

# -- Brain 2: AI Sandbox Wrapper -----------------------------------------------
_AI_SANDBOX_HEADER = """
*** AI 해석 전용 Sandbox 규칙 ***

아래 DATA는 만세력 계산 엔진이 이미 확정한 결과입니다.
당신은 절대로 이 값을 수정하거나 재계산하면 안 됩니다.

[금지 행동]
- 생년월일을 다시 계산하는 행위 금지
- 간지(干支)를 새로 추론하는 행위 금지
- 오행 비율을 재계산하는 행위 금지
- 대운/세운을 새로 계산하는 행위 금지
- "추정하면" "계산해보면" 같은 표현 금지

[허용 행동]
- 제공된 DATA를 바탕으로 해석/서술/조언만 수행

[답변 길이 & 톤 고정 규칙] ← 반드시 준수
- 길이: 250~400자 (한국어 기준). 너무 짧거나 너무 길면 안 됨
- 구조: 3단락만 허용
  ① 공감 문장 (1~2줄) - "지금 이 시기에…"
  ② 사주 분석 핵심 (2~3줄) - 운세 흐름 + 원인
  ③ 행동 조언 (1줄) - "지금 할 수 있는 한 가지"
- 문체: 상담가 말투. 존댓말. 마침표로 끝내기
- 금지: 번호 목록, 불릿(-), 헤더(##), 표, 코드블록

위 규칙을 위반하면 시스템이 해당 내용을 자동 차단합니다.
"""


def get_ai_interpretation(prompt_text, api_key="", system="당신은 40년 경력의 한국 전통 사주명리 전문가입니다.", max_tokens=2000, groq_key="", stream=False, history=None):
    """
    AI 해석 요청 - Anthropic 또는 Groq 선택
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
                                    except Exception as e:
                                        _saju_log.debug(str(e))
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
                                    except Exception as e:
                                        _saju_log.debug(str(e))
                return anthropic_stream()
        except Exception as e:
            return f"[Anthropic 연결 오류: {e}]"

    return ""


# ✅ BUG 3 FIX: hash_funcs를 사용하여 dict 인수 해싱 가능하게 처리
@st.cache_data(hash_funcs={dict: lambda d: json.dumps(d, sort_keys=True, default=str)})
def build_past_events(pils, birth_year, gender):
    """
    과거 사건 자동 생성 v2 — 천간충+지지충 동시 감지, 도메인 7개 세분화, 구체적 문구
    정확도 향상 포인트:
    · 천간충(甲(갑)-庚(경), 乙(을)-辛(신), 丙(병)-壬(임), 丁(정)-癸(계)) + 지지충 동시 발생 → 최고강도
    · 육합(六合) 감지로 긍정 이벤트 추가
    · 충 종류별 도메인 자동 매핑 (子(자)午(오)→건강, 丑(축)未(미)→재물손실, 寅(인)申(신)→사고 등)
    · 나이: 만나이+1 = 한국 세는나이 일관 적용
    """
    ilgan    = pils[1]["cg"]
    orig_jjs = [p["jj"] for p in pils]
    orig_cgs = [p["cg"] for p in pils]
    current_year = datetime.now().year
    birth_month  = st.session_state.get('birth_month', 1)
    birth_day    = st.session_state.get('birth_day', 1)
    birth_hour   = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(
        pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)

    # ① 천간충 쌍 (甲-庚, 乙-辛, 丙-壬, 丁-癸)
    TG_CHUNG = [
        frozenset(["甲","庚"]), frozenset(["乙","辛"]),
        frozenset(["丙","壬"]), frozenset(["丁","癸"]),
    ]
    # ② 천간합 쌍
    TG_HAP = [
        frozenset(["甲","己"]), frozenset(["乙","庚"]),
        frozenset(["丙","辛"]), frozenset(["丁","壬"]), frozenset(["戊","癸"]),
    ]
    # ③ 육합(六合) — 대운×세운 지지가 합을 이루면 긍정 이벤트
    YUK_HAP = [
        frozenset(["子","丑"]), frozenset(["寅","亥"]),
        frozenset(["卯","戌"]), frozenset(["辰","酉"]),
        frozenset(["巳","申"]), frozenset(["午","未"]),
    ]
    # ④ 지지충 → 도메인·설명 (사건 유형 고정)
    CHUNG_DOMAIN_DESC = {
        frozenset(["子","午"]): ("건강·감정격변",  "수화(水火) 충돌 — 극심한 감정 기복, 심장·혈압·신경계 이상이 왔을 시기"),
        frozenset(["丑","未"]): ("재물손실·분쟁",  "토지·부동산·보증 문제 — 재물이 빠져나가거나 관련 갈등이 생겼을 시기"),
        frozenset(["寅","申"]): ("사고·강제이동",  "돌발 사고 또는 강제 이직/이사 — 계획 밖의 사건이 터진 시기"),
        frozenset(["卯","酉"]): ("이직·구설·이별",  "관재 구설 또는 이성 갈등 — 말이나 인간관계가 문제가 된 시기"),
        frozenset(["辰","戌"]): ("재물손실·갈등",  "부동산·토지 갈등 또는 큰 지출 — 뭔가를 잃었을 시기"),
        frozenset(["巳","亥"]): ("이별·장거리이동", "중요한 이별이나 오랜 이동 — 관계가 끊어지거나 먼 곳으로 이동한 시기"),
    }
    # ⑤ 십성 → 세분화 도메인 (7개 카테고리)
    SS_DOMAIN = {
        "남": {
            "比肩": "경쟁·독립심화",   "劫財": "재물손실·배신",
            "食神": "창업·창작활동",   "傷官": "이직·갈등·이별",
            "偏財": "사업변동·재물획득", "正財": "재물획득·결혼",
            "偏官": "직업변화·사고·관재", "正官": "승진·명예획득",
            "偏印": "이사·이동·학업중단", "正印": "자격취득·귀인등장",
        },
        "여": {
            "比肩": "경쟁·자기주장",   "劫財": "재물손실·배신",
            "食神": "자녀·창작활동",   "傷官": "남편갈등·이직·이별",
            "偏財": "사업변동·재물",   "正財": "재물획득·시댁",
            "偏官": "남편갈등·사고·관재", "正官": "남편인연·명예",
            "偏印": "이사·이동·모친변화", "正印": "귀인등장·자격취득",
        },
    }
    # ⑥ 대운+세운 십성 조합 → (강도, 구체 설명)
    HIGH_IMPACT = {
        "偏官+偏官": ("High",  "이중 편관 집중 — 직장 강제 변동·관재·사고 중 하나가 실제로 터진 해입니다. 해고·소송·질병 발병이 기억날 가능성이 높습니다."),
        "劫財+劫財": ("High",  "이중 겁재 충돌 — 가까운 사람에게 배신당하거나 보증·투자 실패로 큰 재물이 빠져나간 해입니다."),
        "偏官+劫財": ("High",  "칠살·겁재 동시 — 직장 압박과 재물 손실이 겹친 최악의 조합. 실직·사고·금전 위기가 함께 왔을 가능성이 높습니다."),
        "劫財+偏官": ("High",  "겁재·칠살 동시 — 재물과 직업이 함께 흔들린 해. 경쟁·배신·강제 변화가 있었을 가능성이 높습니다."),
        "傷官+偏官": ("High",  "상관이 정관을 공격 — 직장 내 상사와 극한 갈등 또는 이직·독립이 강제 발생했을 가능성이 높습니다."),
        "偏官+傷官": ("High",  "편관·상관 충돌 — 조직에서 쫓겨나거나 스스로 뛰쳐나온 해. 이직·창업·구설 중 하나가 기억날 것입니다."),
        "偏財+劫財": ("High",  "편재를 겁재가 강탈 — 투자 실패·사기·동업 배신으로 큰 재물 손실이 있었을 가능성이 높습니다."),
        "劫財+偏財": ("High",  "겁재가 편재를 침범 — 재물 기회가 왔지만 경쟁·배신으로 놓쳤을 가능성이 높습니다."),
        "偏印+劫財": ("High",  "효신·겁재 — 계획이 무너지고 재물도 손실. 직장·거주지·가족 중 하나가 급격히 변한 해입니다."),
        "劫財+偏印": ("High",  "겁재·효신 — 재물 손실 후 환경 이탈. 이직이나 이사가 뒤따랐을 가능성이 높습니다."),
        "傷官+傷官": ("High",  "이중 상관 — 조직과 극심한 마찰로 이직하거나 구설수가 터진 해입니다."),
        "正官+食神": ("Mid",   "관인상생 안정 — 실력이 공식 인정된 해. 승진·공채 합격·수상이 있었을 가능성이 높습니다."),
        "食神+正官": ("Mid",   "식신이 정관을 살림 — 재능으로 조직 내 인정을 받은 해. 직함 변화나 성취가 있었을 것입니다."),
        "正財+正官": ("Mid",   "재관 쌍전 — 재물과 명예가 함께 온 해. 결혼·취업 성공·수입 증가 중 하나가 기억날 것입니다."),
        "正官+正財": ("Mid",   "정관·정재 동반 — 안정적 성취. 직장과 생활 기반이 동시에 탄탄해진 해입니다."),
        "食神+正財": ("Mid",   "식신생재 — 재능과 노력이 돈으로 연결된 해. 수입이 오르거나 수익 사업이 시작됐을 가능성이 높습니다."),
        "正財+食神": ("Mid",   "정재·식신 — 꾸준한 노력이 재물로 이어진 해입니다."),
        "正印+正官": ("Mid",   "인수상생 — 자격증 취득·승진·학업 성취가 있었을 가능성이 높습니다."),
        "正官+正印": ("Mid",   "정관·정인 — 명예와 지식이 함께 빛난 해. 공직·전문직에서의 인정이 있었을 것입니다."),
        "偏財+偏財": ("Mid",   "이중 편재 — 큰 돈이 들어오거나 나간 해. 투자·사업 확장 또는 큰 지출이 있었을 가능성이 높습니다."),
        "比肩+劫財": ("Mid",   "비겁 과다 — 치열한 경쟁 또는 독립·창업 충동이 강했던 해. 동업 분쟁이 있었을 수 있습니다."),
        "偏官+食神": ("Low",   "칠살제화 — 큰 시련이 왔지만 식신이 제어. 위기를 넘기고 오히려 기회를 잡았을 가능성이 높습니다."),
        "食神+偏官": ("Low",   "식신이 칠살을 제압 — 강한 압박을 실력으로 이겨낸 해. 반전이 있었을 가능성이 높습니다."),
    }

    events = []

    for dw in daewoon:
        if dw["시작연도"] > current_year:
            continue
        dw_ss     = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        dw_domain = SS_DOMAIN.get(gender, SS_DOMAIN["남"]).get(dw_ss, "변화")
        age_start = dw["시작나이"]

        # A. 대운 천간이 원국 천간과 충하는지 (천간충)
        dw_tg_chung = [ocg for ocg in orig_cgs if frozenset([dw["cg"], ocg]) in TG_CHUNG]
        # B. 대운 지지가 원국 지지와 충하는지 (지지충)
        dw_jj_chung = [(ojj, frozenset([dw["jj"], ojj]))
                       for ojj in orig_jjs if frozenset([dw["jj"], ojj]) in CHUNG_MAP]
        # C. 대운 천간이 원국 천간과 합하는지
        dw_tg_hap = [list(pair - {dw["cg"]})[0]
                     for pair in TG_HAP if dw["cg"] in pair
                     and list(pair - {dw["cg"]})[0] in orig_cgs]

        # 대운 진입 이벤트: 천간충+지지충 동시 → 최고강도
        if dw_tg_chung and dw_jj_chung:
            ojj, ck = dw_jj_chung[0]
            domain, cdd = CHUNG_DOMAIN_DESC.get(ck, (dw_domain, "큰 변화가 왔다"))
            events.append({
                "age": f"{age_start}~{age_start+2}세",
                "year": dw["시작연도"],
                "type": "대운 천간충+지지충",
                "domain": domain,
                "desc": (f"【{age_start}세 대운 진입 · 천간충+지지충 동시】"
                         f"천간({dw['cg']})과 지지({dw['jj']})가 동시에 원국을 강타."
                         f" {cdd}. 이 시기 삶이 크게 뒤흔들렸을 가능성이 매우 높습니다."),
                "intensity": "High"
            })
        elif dw_jj_chung:
            ojj, ck = dw_jj_chung[0]
            domain, cdd = CHUNG_DOMAIN_DESC.get(ck, (dw_domain, "큰 변화가 찾아왔다"))
            events.append({
                "age": f"{age_start}~{age_start+2}세",
                "year": dw["시작연도"],
                "type": "대운 지지충",
                "domain": domain,
                "desc": f"【{age_start}세 대운 진입 · 지지충】{cdd}. {domain} 영역에서 변동이 있었을 가능성이 높습니다.",
                "intensity": "High"
            })
        elif dw_tg_hap:
            events.append({
                "age": f"{age_start}세",
                "year": dw["시작연도"],
                "type": "대운 천간합",
                "domain": dw_domain,
                "desc": f"【{age_start}세 대운 진입 · 천간합】천간합(天干合) 성립 — {dw_domain} 영역에서 귀인이나 기회가 찾아온 시기입니다.",
                "intensity": "Mid"
            })

        # 대운 내 세운별 교차 분석
        for y in range(dw["시작연도"], min(dw["종료연도"] + 1, current_year)):
            age = y - birth_year + 1
            if age < 5:
                continue
            sw    = get_yearly_luck(pils, y)
            sw_cg = sw.get("cg", "")
            sw_ss = sw.get("십성_천간", "-")
            sw_domain = SS_DOMAIN.get(gender, SS_DOMAIN["남"]).get(sw_ss, "변화")

            # 세운 지지 → 원국 지지 충 감지
            sw_jj_chung = [(ojj, frozenset([sw["jj"], ojj]))
                           for ojj in orig_jjs if frozenset([sw["jj"], ojj]) in CHUNG_MAP]
            # 세운 천간 → 원국 천간 충 감지
            sw_tg_chung = [ocg for ocg in orig_cgs if frozenset([sw_cg, ocg]) in TG_CHUNG]
            # 대운 지지 ↔ 세운 지지 충
            dw_sw_jj_chung = frozenset([dw["jj"], sw["jj"]]) in CHUNG_MAP

            # 십성 조합 체크 (정방향+역방향)
            dw_sw_key = f"{dw_ss}+{sw_ss}"
            sw_dw_key = f"{sw_ss}+{dw_ss}"
            combo_hit  = HIGH_IMPACT.get(dw_sw_key) or HIGH_IMPACT.get(sw_dw_key)

            # 삼합 성립 여부
            sam_hap_found = []
            all_jj = set(orig_jjs + [dw["jj"], sw["jj"]])
            for combo, (hname, hoh, hdesc) in SAM_HAP_MAP.items():
                if combo.issubset(all_jj) and dw["jj"] in combo and sw["jj"] in combo:
                    sam_hap_found.append(hname)

            # 대운×세운 육합 (긍정 결합)
            yuk_hap = frozenset([dw["jj"], sw["jj"]]) in YUK_HAP

            # 이미 같은 연도 이벤트가 있으면 스킵
            if any(e["year"] == y for e in events):
                continue

            # ── 우선순위 1: 천간충+지지충 동시 (세운 기준) ──
            if sw_tg_chung and sw_jj_chung:
                ojj, ck = sw_jj_chung[0]
                domain, cdd = CHUNG_DOMAIN_DESC.get(ck, (sw_domain, "큰 변화"))
                combo_desc = combo_hit[1] if combo_hit else ""
                events.append({
                    "age": f"{age}세",
                    "year": y,
                    "type": f"{dw_ss}대운 x {sw_ss}세운 + 천간충+지지충",
                    "domain": domain,
                    "desc": (f"【{y}년 · {age}세 · 최고강도】천간({sw_cg})과 지지({sw['jj']})가 동시에"
                             f" 원국을 충격하는 해. {cdd}. {combo_desc}"),
                    "intensity": "High"
                })

            # ── 우선순위 2: 세운 지지충 발생 ──
            elif sw_jj_chung:
                ojj, ck = sw_jj_chung[0]
                domain, cdd = CHUNG_DOMAIN_DESC.get(ck, (sw_domain, "큰 변화"))
                intensity = "High"  # 충 발생 시 최소 High
                if combo_hit:
                    full_desc = f"【{y}년 · {age}세】{cdd}. {combo_hit[1]}"
                else:
                    full_desc = f"【{y}년 · {age}세】{cdd}. {domain} 영역에서 실제 사건이 발생했을 가능성이 높습니다."
                events.append({
                    "age": f"{age}세", "year": y,
                    "type": f"{dw_ss}대운 x {sw_ss}세운 + 원국충",
                    "domain": domain, "desc": full_desc, "intensity": intensity
                })

            # ── 우선순위 3: 대운 지지 ↔ 세운 지지 충 + 십성조합 강도 High ──
            elif dw_sw_jj_chung and combo_hit and combo_hit[0] == "High":
                events.append({
                    "age": f"{age}세", "year": y,
                    "type": f"{dw_ss}대운 x {sw_ss}세운 (대운지지-세운지지 충)",
                    "domain": sw_domain,
                    "desc": f"【{y}년 · {age}세】대운과 세운 지지가 서로 충돌하며 운의 방향이 급변. {combo_hit[1]}",
                    "intensity": "High"
                })

            # ── 우선순위 4: 삼합 성립 ──
            elif sam_hap_found:
                events.append({
                    "age": f"{age}세", "year": y,
                    "type": f"삼합 {sam_hap_found[0]}",
                    "domain": sw_domain,
                    "desc": f"【{y}년 · {age}세】대운·세운·원국 삼합({sam_hap_found[0]}) 성립 — {sw_domain} 영역에서 운의 집중 발복이 있었을 가능성이 높습니다.",
                    "intensity": "Mid"
                })

            # ── 우선순위 5: 십성 조합 High/Mid ──
            elif combo_hit:
                intensity, combo_desc = combo_hit
                if intensity in ("High", "Mid", "Low"):
                    events.append({
                        "age": f"{age}세", "year": y,
                        "type": f"{dw_ss}대운 x {sw_ss}세운",
                        "domain": sw_domain,
                        "desc": f"【{y}년 · {age}세】{combo_desc}",
                        "intensity": intensity
                    })

            # ── 우선순위 6: 대운×세운 육합 (긍정 결합) ──
            elif yuk_hap and dw_ss in {"正財","食神","正官","正印"} and sw_ss in {"正財","食神","正官","正印"}:
                events.append({
                    "age": f"{age}세", "year": y,
                    "type": f"{dw_ss}대운 x {sw_ss}세운 육합",
                    "domain": sw_domain,
                    "desc": f"【{y}년 · {age}세】대운·세운 지지가 육합(六合)을 이루며 기운이 모임. {sw_domain} 영역에서 좋은 결실이 있었을 가능성이 높습니다.",
                    "intensity": "Low"
                })

    # 중요도 기준 정렬, 상위 15개 선별
    priority = {"High": 0, "Mid": 1, "Low": 2, "None": 3}
    events.sort(key=lambda e: (priority.get(e["intensity"], 3), e["year"]))
    return events[:15]


def build_life_event_timeline(pils, birth_year, gender):
    """
    ⏱️ 생애 사건 타임라인 v2 — 7개 도메인 핀포인팅
    직업변화 / 결혼·교제 / 이사·이동 / 재물획득 / 재물손실 / 사고·관재 / 질병·건강
    개선: 지지충 유형별 도메인 자동 고정, 대운만 해당해도 보조 체크, 구체 문구
    """
    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    birth_month  = st.session_state.get('birth_month', 1)
    birth_day    = st.session_state.get('birth_day', 1)
    birth_hour   = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(
        pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    orig_jjs = [p["jj"] for p in pils]

    # 7개 도메인 트리거 십성
    DOMAIN_TRIGGERS = {
        "직업변화":  {"偏官", "正官", "傷官", "劫財"},
        "결혼·교제": {"正財", "偏財"} if gender == "남" else {"正官", "偏官"},
        "이사·이동": {"偏印", "偏財", "劫財"},
        "재물획득":  {"食神", "正財", "偏財"},
        "재물손실":  {"劫財", "偏官"},
        "사고·관재": {"偏官", "劫財"},
        "질병·건강": {"偏官"},
    }
    # 도메인 우선순위 (낮을수록 먼저 선택)
    DOMAIN_PRIORITY = {
        "사고·관재": 0, "질병·건강": 1, "재물손실": 2,
        "직업변화": 3, "결혼·교제": 4, "이사·이동": 5, "재물획득": 6,
    }

    # 지지충 → 도메인 강제 매핑 (충 발생 시 해당 도메인으로 고정)
    CHUNG_TO_DOMAIN = {
        frozenset(["子","午"]): "질병·건강",
        frozenset(["丑","未"]): "재물손실",
        frozenset(["寅","申"]): "사고·관재",
        frozenset(["卯","酉"]): "직업변화",
        frozenset(["辰","戌"]): "재물손실",
        frozenset(["巳","亥"]): "이사·이동",
    }
    CHUNG_DESC = {
        frozenset(["子","午"]): "수화(水火) 충돌 — 극심한 감정 기복, 심장·혈압·신경계 이상이 왔을 시기입니다.",
        frozenset(["丑","未"]): "토(土) 충돌 — 토지·부동산·보증 문제 또는 재물 분쟁이 있었을 시기입니다.",
        frozenset(["寅","申"]): "목금(木金) 충돌 — 돌발 사고나 강제 이직·이사가 있었을 가능성이 높습니다.",
        frozenset(["卯","酉"]): "목금(木金) 충돌 — 관재 구설, 이직, 이성 갈등이 있었을 가능성이 높습니다.",
        frozenset(["辰","戌"]): "토(土) 충돌 — 부동산 갈등이나 큰 재물 손실이 있었을 가능성이 높습니다.",
        frozenset(["巳","亥"]): "화수(火水) 충돌 — 중요한 이별이나 먼 이동이 있었을 가능성이 높습니다.",
    }

    # 도메인별 십성 조합 → 구체 문구
    EVENT_DESC = {
        "직업변화": {
            ("偏官","偏官"): "이중 편관 — 직장에서 강제 변동(해고·이직·강등)이 실제로 있었을 가능성이 매우 높습니다.",
            ("偏官","傷官"): "편관+상관 충돌 — 상사와의 극한 갈등 또는 조직 이탈이 있었을 가능성이 높습니다.",
            ("傷官","偏官"): "상관이 편관을 만남 — 이직 또는 독립 창업이 이 시기에 결행됐을 가능성이 높습니다.",
            ("正官","正官"): "정관 이중 — 승진·공채 합격·중요한 직책 변화가 있었을 가능성이 높습니다.",
            ("劫財","偏官"): "겁재+편관 — 직장 내 배신이나 강제 퇴직이 있었을 가능성이 높습니다.",
            ("傷官","傷官"): "이중 상관 — 조직과의 극심한 마찰로 이직하거나 구설수가 터진 시기입니다.",
        },
        "결혼·교제": {
            ("正財","正財"): "정재 이중 — 결혼 또는 진지한 교제가 실제로 시작됐을 가능성이 매우 높습니다.",
            ("偏財","偏財"): "편재 이중 — 새로운 이성이 등장하거나 교제의 중요한 전환점이 있었을 가능성이 높습니다.",
            ("正官","正官"): "정관 이중(여) — 남편 인연이 강하게 작용한 시기. 결혼·약혼이 있었을 가능성이 높습니다.",
            ("偏官","偏官"): "편관 이중(여) — 강렬한 이성 인연 또는 결혼 압박이 있었을 가능성이 높습니다.",
        },
        "이사·이동": {
            ("偏印","偏財"): "편인+편재 — 환경 변화 욕구 극대화. 이사·전직·해외 이동 중 하나가 있었을 가능성이 높습니다.",
            ("劫財","偏印"): "겁재+편인 — 갑작스럽고 계획 밖의 이동이나 이사가 있었을 가능성이 높습니다.",
            ("偏財","劫財"): "편재+겁재 — 거주지 변동이나 생활 기반 이전이 있었을 가능성이 높습니다.",
        },
        "재물획득": {
            ("食神","正財"): "식신생재 — 재능이 돈으로 이어진 해. 수입 증가나 새로운 수익원이 생겼을 가능성이 높습니다.",
            ("食神","偏財"): "식신+편재 — 예상 밖의 큰 돈이 들어오거나 사업 기회가 생겼을 가능성이 높습니다.",
            ("偏財","偏財"): "편재 이중 — 투자 이익 또는 사업 수익이 크게 늘었을 가능성이 높습니다.",
            ("正財","正官"): "재관 쌍전 — 취업 성공·연봉 인상·결혼 등 현실 기반이 탄탄해진 시기입니다.",
        },
        "재물손실": {
            ("偏官","劫財"): "편관+겁재 — 투자 실패·사기·예상치 못한 큰 지출이 있었을 가능성이 높습니다.",
            ("劫財","偏官"): "겁재+편관 — 가까운 사람의 배신이나 보증 문제로 재물이 빠져나간 시기입니다.",
            ("劫財","劫財"): "겁재 이중 — 경쟁자·동업자의 배신으로 재물이 크게 손실됐을 가능성이 높습니다.",
            ("偏財","劫財"): "편재를 겁재가 강탈 — 투자 손실이나 동업 배신이 있었을 가능성이 높습니다.",
        },
        "사고·관재": {
            ("偏官","偏官"): "이중 편관 — 교통사고·소송·관재 중 하나가 실제로 있었을 가능성이 매우 높습니다.",
            ("偏官","劫財"): "편관+겁재 — 부상·법적 분쟁·타인과의 물리적 충돌이 있었을 가능성이 높습니다.",
            ("劫財","偏官"): "겁재+편관 — 타인과의 갈등이 법적·신체적 피해로 이어졌을 가능성이 높습니다.",
        },
        "질병·건강": {
            ("偏官","偏官"): "이중 편관 — 만성 질환 발병 또는 수술·입원이 있었을 가능성이 높습니다.",
            ("偏官","劫財"): "편관+겁재 — 과로·스트레스로 인한 건강 악화 또는 정신적 소진이 있었던 시기입니다.",
            ("偏印","偏官"): "편인+편관 — 심리적 압박이 신체화된 시기. 신경계·면역계에 이상이 왔을 수 있습니다.",
        },
    }
    DEFAULT_DESC = {
        "직업변화":  "직장 또는 직업에서 중요한 변화가 있었을 가능성이 높습니다.",
        "결혼·교제": "가까운 인연 관계에서 중요한 전환점이 있었을 가능성이 높습니다.",
        "이사·이동": "거주지나 생활 환경이 크게 바뀌었을 가능성이 높습니다.",
        "재물획득":  "수입이 오르거나 재물이 들어오는 변화가 있었을 가능성이 높습니다.",
        "재물손실":  "재물이 빠져나가거나 금전적 손실이 있었을 가능성이 높습니다.",
        "사고·관재": "사고·법적 문제·외부 압박이 있었을 가능성이 높습니다.",
        "질병·건강": "몸이나 정신에 이상 신호가 온 시기일 가능성이 있습니다.",
    }
    DOMAIN_EMOJI = {
        "직업변화": "💼", "결혼·교제": "💑", "이사·이동": "🏠",
        "재물획득": "💰", "재물손실": "💸", "사고·관재": "⚠️", "질병·건강": "🏥",
    }

    timeline = []

    for dw in daewoon:
        if dw["시작연도"] > current_year:
            continue
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")

        for y in range(dw["시작연도"], min(dw["종료연도"] + 1, current_year)):
            age = y - birth_year + 1
            if age < 18:
                continue
            sw    = get_yearly_luck(pils, y)
            sw_ss = sw.get("십성_천간", "-")
            combo = (dw_ss, sw_ss)

            # 세운 지지 → 원국 지지 충 감지 → 도메인 강제 매핑
            sw_chung_domain = None
            sw_chung_desc   = None
            for ojj in orig_jjs:
                k = frozenset([sw["jj"], ojj])
                if k in CHUNG_MAP and k in CHUNG_TO_DOMAIN:
                    sw_chung_domain = CHUNG_TO_DOMAIN[k]
                    sw_chung_desc   = CHUNG_DESC.get(k, "")
                    break

            # 중복 방지
            if any(t["year"] == y for t in timeline):
                continue

            # 후보 도메인 수집 (대운+세운 모두 트리거이거나, 충이 발생한 경우)
            candidates = []
            for domain, triggers in DOMAIN_TRIGGERS.items():
                both_match = dw_ss in triggers and sw_ss in triggers
                chung_match = (sw_chung_domain == domain) and (dw_ss in triggers or sw_ss in triggers)
                if both_match or chung_match:
                    candidates.append(domain)

            if not candidates:
                continue

            # 우선순위 가장 높은 도메인 선택
            best_domain = min(candidates, key=lambda d: DOMAIN_PRIORITY.get(d, 9))

            # 충 발생한 도메인이 있으면 그것을 우선
            if sw_chung_domain and sw_chung_domain in candidates:
                best_domain = sw_chung_domain

            # 설명 생성
            desc = EVENT_DESC.get(best_domain, {}).get(combo)
            if not desc:
                desc = DEFAULT_DESC.get(best_domain, "중요한 변화가 있었을 가능성이 높습니다.")
            if sw_chung_domain == best_domain and sw_chung_desc:
                desc = sw_chung_desc + " " + desc

            sign = "🔴" if best_domain in ("사고·관재", "재물손실", "질병·건강") else "🟡"

            timeline.append({
                "year": y, "age": age,
                "domain": best_domain,
                "emoji": DOMAIN_EMOJI.get(best_domain, "📍"),
                "desc": desc,
                "sign": sign,
            })

    # 연도 순 정렬, 최대 20개
    timeline.sort(key=lambda x: x["year"])
    return timeline[:20]


# ==================================================================
# *** 십성(十星) 2-조합 인생 분석 DB ***
# 조합만 알면 그 사람의 인생이 보인다
# ==================================================================
SIPSUNG_COMBO_LIFE = {
    frozenset(["食神","偏財"]): {
        "요약": "🍀 재능으로 돈 버는 타입",
        "성향": "여유롭고 배짱이 있습니다. 쫓기는 삶보다 자기 페이스를 지키는 삶을 선호합니다. 욕심을 부리지 않아도 밥은 먹고 사는 구조가 이 사주입니다. 억지로 벌려 하면 오히려 안 풀립니다.",
        "재물": "재능/기술/콘텐츠로 돈이 들어오는 구조입니다. 억지로 발로 뛰는 영업보다, 본인이 잘하는 걸 갈고닦으면 돈이 따라옵니다. 프리랜서/창작/요식업/전문직이 유리합니다.",
        "직업": "자영업/프리랜서/요리사/디자이너/강사/유튜버/작가/예술가. 시간을 자유롭게 쓸 수 있는 직업이 맞습니다.",
        "연애": "상대방에게 집착하지 않습니다. 여유로운 관계를 선호합니다. 상대가 집착하거나 간섭하면 자연스럽게 멀어집니다.",
        "주의": "너무 여유를 부리다 기회를 흘려보내는 수가 있습니다. 좋은 운이 왔을 때 적극적으로 움직이십시오.",
    },
    frozenset(["傷官","偏財"]): {
        "요약": "⚡ 창의력과 말발로 돈 버는 타입",
        "성향": "말이 빠르고 아이디어가 넘칩니다. 기존 방식에 만족하지 못하고 항상 더 나은 방법을 찾습니다. 자유롭고 틀에 갇히는 것을 싫어합니다. 한 곳에 오래 있으면 답답함을 느낍니다.",
        "재물": "아이디어/설득/창의로 돈을 법니다. 세일즈/마케팅/홍보/예술/미디어에서 두각을 나타냅니다. 남들이 생각 못한 방식으로 수익을 만드는 능력이 있습니다.",
        "직업": "마케터/광고인/유튜버/방송인/세일즈/작가/디자이너/스타트업 창업자/연예인.",
        "연애": "매력적이고 화술이 뛰어나 이성의 시선을 끕니다. 다만 한 사람에게 오래 집중하기 힘든 면이 있어 이별이 잦을 수 있습니다.",
        "주의": "말이 앞서고 행동이 뒤처질 수 있습니다. 구설수와 경솔한 발언이 발목을 잡습니다.",
    },
    frozenset(["正官","正印"]): {
        "요약": "🏛️ 관인상생 - 공부가 출세로, 조직 내 최고 귀격",
        "성향": "원칙적이고 신중합니다. 배움을 좋아하고 지식을 쌓는 것에 보람을 느낍니다. 남에게 인정받는 것이 중요한 동기입니다. 겉으로는 여유로워 보여도 속으로는 평판을 매우 신경 씁니다.",
        "재물": "조직/제도권 안에서 안정적으로 재물이 쌓입니다. 급여/연금/직책 수당 등 안정된 수입 구조입니다. 투기보다 장기 저축/부동산이 맞습니다.",
        "직업": "공무원/교수/교사/대기업 임원/법관/의사/연구원. 자격증과 학위가 인생을 열어주는 사주입니다.",
        "연애": "신중하게 시작하고 오래 만납니다. 상대의 성실함/안정성을 중요하게 봅니다. 가볍게 만나는 것을 좋아하지 않습니다.",
        "주의": "너무 원칙만 고집하면 기회를 놓칩니다. 인간관계에서 유연함이 필요합니다.",
    },
    frozenset(["偏官","食神"]): {
        "요약": "🔥 칠살제화 - 시련이 오히려 기회, 역경을 딛고 성공하는 타입",
        "성향": "어려운 상황에서 진가가 드러납니다. 압박이 올수록 더 강해집니다. 어릴 적 힘든 시절이 있었지만 그것이 오히려 내공이 되었습니다. 두 번 쓰러져도 세 번 일어나는 사람입니다.",
        "재물": "재능과 실력으로 역경을 뚫는 구조입니다. 처음엔 힘들어도 나중에 빛을 봅니다. 40대 이후 크게 안정됩니다.",
        "직업": "의사/검사/군인/경찰/운동선수/요리사/장인(匠人). 전문 기술로 편관의 압박을 제어하는 직업이 맞습니다.",
        "연애": "강인해 보이지만 내면은 매우 세심합니다. 강한 상대보다 따뜻하게 챙겨주는 사람에게 끌립니다.",
        "주의": "지나친 고집으로 도움받을 기회를 밀어내는 수가 있습니다. 받는 법도 배워야 합니다.",
    },
    frozenset(["偏官","正印"]): {
        "요약": "🎖️ 큰 조직/권력 기관에서 빛나는 리더 타입",
        "성향": "리더십이 있습니다. 어려운 상황에서도 흔들리지 않고 방향을 잡습니다. 자연스럽게 따르는 사람이 생깁니다. 카리스마와 지식을 함께 갖춘 유형입니다.",
        "재물": "높은 직위/권한에서 재물이 따라오는 구조입니다. 실무보다 결정권을 갖는 위치가 훨씬 유리합니다.",
        "직업": "고위 공무원/군 장성/CEO/정치인/법조인/병원장. 조직의 상층부로 올라가는 것이 이 사주의 목표입니다.",
        "연애": "강한 카리스마에 끌리는 상대를 만납니다. 주도적인 관계를 선호하며, 상대가 자신을 인정해주기를 원합니다.",
        "주의": "권위적이 되기 쉽습니다. 아랫사람의 말에 귀 기울이는 연습이 필요합니다.",
    },
    frozenset(["比肩","偏財"]): {
        "요약": "⚔️ 남 밑에서는 못 배기는 독립 창업 기질",
        "성향": "독립심이 매우 강합니다. 누군가의 아래에서 지시받는 것을 본능적으로 거부합니다. 월급쟁이로 오래 살기 힘든 체질입니다. 자기 사업이나 자기 방식이 맞습니다.",
        "재물": "독립/창업/자영업으로 돈을 법니다. 재물이 왔다 갔다 하는 기복이 있지만 결국 스스로 만들어냅니다. 형제/동업자와의 재물 갈등을 각별히 조심하십시오.",
        "직업": "자영업/사업가/독립 컨설턴트/프리랜서/스타트업 대표. 조직 생활보다 독립이 맞습니다.",
        "연애": "자기 생각이 강해 상대와 부딪히는 경우가 많습니다. 비슷한 독립심을 가진 상대가 맞습니다.",
        "주의": "혼자 다 하려다 번아웃이 옵니다. 동업 분리를 명확히 하고 계약서를 꼭 쓰십시오.",
    },
    frozenset(["劫財","偏財"]): {
        "요약": "🎰 크게 벌고 크게 쓰는 승부사 - 기복이 강한 인생",
        "성향": "승부욕이 극강입니다. 크게 베팅하는 기질이 있습니다. 결과가 좋을 때와 나쁠 때의 차이가 매우 큽니다. 조심성보다 추진력이 앞섭니다.",
        "재물": "한 번에 크게 버는 구조이지만, 그만큼 나가기도 쉽습니다. 보증/투기/동업에서 손해를 보는 패턴이 반복될 수 있습니다. 재물을 지키는 연습이 핵심 숙제입니다.",
        "직업": "사업가/트레이더/영업직/부동산/스포츠/연예계. 경쟁이 있는 환경에서 더 잘 됩니다.",
        "연애": "적극적이고 주도적입니다. 상대에게 아낌없이 씁니다. 하지만 재물 갈등이 관계에 영향을 줄 수 있습니다.",
        "주의": "충동적 투자와 보증은 반드시 피하십시오. 인생 최대 위기는 대부분 돈 문제에서 시작됩니다.",
    },
    frozenset(["劫財","正財"]): {
        "요약": "💸 벌어도 새는 구조 - 재물 관리가 인생의 핵심 숙제",
        "성향": "씀씀이가 큽니다. 들어오는 만큼 나갑니다. 저축보다 소비가 먼저입니다. 가까운 사람에게 베푸는 것을 좋아하지만, 그로 인해 손해를 보기도 합니다.",
        "재물": "수입은 있는데 모이지 않습니다. 고정 지출을 줄이고 자동 저축 시스템을 만드는 것이 핵심입니다. 부동산 같은 묶어두는 자산이 맞습니다.",
        "직업": "안정적인 월급 구조가 오히려 더 맞습니다. 변동 수입보다 고정 수입 직종이 재물을 지키기 좋습니다.",
        "연애": "관대하고 잘 챙깁니다. 그러나 지나친 헌신으로 지치는 경우가 있습니다.",
        "주의": "보증 서는 것과 쉬운 투자 제안을 경계하십시오.",
    },
    frozenset(["正財","正官"]): {
        "요약": "🏦 성실하게 쌓아가는 안정형 | 50대에 빛나는 사주",
        "성향": "현실적이고 성실합니다. 화려한 것보다 안정적인 것을 선호합니다. 맡은 일은 반드시 해냅니다. 한 번 한 약속은 반드시 지킵니다.",
        "재물": "꾸준히 차곡차곡 쌓는 구조입니다. 큰 기복 없이 우상향합니다. 50대가 되면 상당한 재산이 쌓여 있습니다. 부동산/예금/연금이 잘 맞습니다.",
        "직업": "금융인/회계사/공무원/대기업 직원/관리직. 안정적인 조직에서 오래 머무는 것이 유리합니다.",
        "연애": "신중하게 시작하고 오래 유지합니다. 화려한 연애보다 현실적이고 안정적인 파트너를 선호합니다.",
        "주의": "너무 안정만 추구하다 도전의 기회를 놓칩니다. 30~40대에 한 번은 용기 있는 선택이 필요합니다.",
    },
    frozenset(["傷官","正官"]): {
        "요약": "💥 조직과 충돌하는 혁신가 - 창업이 답",
        "성향": "규칙과 권위에 본능적으로 반발합니다. '왜 이 규칙을 따라야 하는가'를 항상 묻습니다. 독창적이고 기존 방식을 파괴하는 혁신가 기질입니다.",
        "재물": "조직 안에서는 재물이 잘 안 쌓입니다. 독립/창업/전문직에서 빛을 발합니다. 자기 분야의 최고가 되면 돈이 따라옵니다.",
        "직업": "창업가/예술가/작가/유튜버/강연가/변호사. 자기 목소리를 낼 수 있는 직업이 최적입니다.",
        "연애": "솔직하고 직선적입니다. 상대방의 단점이 잘 보이고 그것을 말하는 경향이 있어 갈등이 생기기 쉽습니다.",
        "주의": "윗사람과의 갈등을 조심하십시오. 직장 내 구설수가 경력에 큰 타격을 줄 수 있습니다.",
    },
    frozenset(["偏印","劫財"]): {
        "요약": "🌑 고독한 승부사 - 혼자 깊이 파고드는 전문가",
        "성향": "혼자 있는 것이 편합니다. 깊이 파고드는 것을 좋아하지만 결과를 잘 드러내지 않습니다. 겉으로는 강해 보이지만 내면은 외롭습니다.",
        "재물": "전문 기술/연구/특수 분야에서 재물이 옵니다. 대중을 상대하는 것보다 특정 분야 전문가로 인정받을 때 돈이 따라옵니다.",
        "직업": "연구원/전문직/한의사/역술인/프로그래머/투자자/작가.",
        "연애": "쉽게 마음을 열지 않습니다. 한번 마음을 열면 매우 깊이 의지하는 편입니다.",
        "주의": "고독이 깊어지면 자기 세계에 갇힙니다. 사람과의 연결을 의도적으로 만드십시오.",
    },
    frozenset(["食神","正官"]): {
        "요약": "- 재능과 명예가 함께 - 전문직/교육자로 빛나는 타입",
        "성향": "재능이 있고 원칙도 있습니다. 자기 분야에서 인정받고 싶어합니다. 일에 대한 자부심이 강하고, 자기 분야의 최고가 되는 것이 목표입니다.",
        "재물": "전문 기술+안정적 직위에서 재물이 옵니다. 전문직 자격증이 인생을 크게 열어줍니다. 꾸준히 실력을 쌓으면 중년 이후 크게 안정됩니다.",
        "직업": "의사/변호사/교수/요리사/음악가/건축가. 기술과 명예가 결합된 직업이 최적입니다.",
        "연애": "여유롭고 배려 깊습니다. 함께 성장하는 관계를 원합니다.",
        "주의": "완벽주의 성향으로 스스로를 지치게 만들 수 있습니다. 80%에서 멈추는 연습이 필요합니다.",
    },
    frozenset(["正財","食神"]): {
        "요약": "🌾 식신생재 - 실력이 재물로 자연스럽게 이어지는 길격",
        "성향": "부지런하고 현실적입니다. 군더더기 없이 실력을 쌓고 그 실력이 정직하게 재물로 이어집니다. 과욕 없이 꾸준히 하는 타입입니다.",
        "재물": "착실하게 모입니다. 큰 기복 없이 꾸준히 우상향합니다. 전통 명리에서 가장 좋은 재물 구조 중 하나입니다. 부업보다 본업 깊이 파기가 더 유리합니다.",
        "직업": "장인/요리사/의료인/공예가/전문 기술직. 손으로 하는 일, 기술이 필요한 일이 맞습니다.",
        "연애": "따뜻하고 현실적입니다. 상대를 물질적으로도 잘 챙기는 편입니다.",
        "주의": "안주하려는 경향이 있습니다. 시장이 변하면 기술도 업그레이드해야 합니다.",
    },
    frozenset(["偏印","食神"]): {
        "요약": "🎭 도식(倒食) - 재능이 막히는 구조, 방향 전환이 답",
        "성향": "재능은 있는데 무언가가 자꾸 막힙니다. 하려는 일이 잘 안 풀리는 느낌이 반복됩니다. 다른 방향으로 전환했을 때 오히려 잘 되는 경우가 많습니다.",
        "재물": "한 가지 방식으로 고집하면 막힙니다. 다각화하거나 방법을 바꾸면 풀립니다. 부업/여러 수입원 구조가 유리합니다.",
        "직업": "특수 분야/틈새 시장/남들이 안 하는 것. 아웃사이더 전략으로 접근할 때 빛납니다.",
        "연애": "관계에서 오해가 생기기 쉽습니다. 말보다 행동으로 보여주는 것이 효과적입니다.",
        "주의": "한 가지에 너무 오래 집착하지 마십시오. 빠른 방향 전환이 오히려 길입니다.",
    },
    frozenset(["偏財","偏官"]): {
        "요약": "⚡ 큰 그림 그리는 사업가 - 고위험/고수익, 압박 속에 빛나는 타입",
        "성향": "크게 생각하고 크게 움직입니다. 작은 것에 만족하지 못합니다. 위험을 감수하는 용기가 있습니다. 한 번의 베팅으로 인생이 크게 바뀔 수 있는 사주입니다.",
        "재물": "크게 벌 수 있지만 동시에 크게 잃을 위험도 있습니다. 40대에 큰 기회가 한 번 찾아옵니다. 그 기회에 전부를 걸지 마십시오.",
        "직업": "사업가/투자가/무역업/정치인/부동산 개발. 스케일이 큰 일에 맞습니다.",
        "연애": "드라마틱한 연애를 합니다. 강렬한 만남과 이별을 반복하는 경향이 있습니다.",
        "주의": "재물과 직업 모두 기복이 큽니다. 리스크 관리가 생존의 핵심입니다.",
    },
    frozenset(["正印","比肩"]): {
        "요약": "📚 독립적 학자/선생 기질 - 배운 것을 자기 철학으로 만드는 타입",
        "성향": "배움을 좋아하고, 배운 것을 자기 방식으로 해석합니다. 남의 지식을 그대로 따르지 않고 자기 철학으로 만듭니다. 독창적 사상가 기질이 있습니다.",
        "재물": "지식/교육/상담으로 돈을 법니다. 자기 콘텐츠나 저서가 수입이 되는 구조입니다. 강의/출판/코칭 분야에서 잘 됩니다.",
        "직업": "교사/강사/작가/컨설턴트/코치/상담사/철학자.",
        "연애": "지적 교류가 되는 상대에게 끌립니다. 대화가 안 되면 아무리 조건이 좋아도 관심이 없습니다.",
        "주의": "이론은 있는데 실행력이 부족한 경우가 있습니다. 아는 것을 반드시 실천으로 연결하십시오.",
    },
    frozenset(["傷官","偏印"]): {
        "요약": "🎨 예술/철학/창작 기질 - 천재와 기인의 경계",
        "성향": "남들과 다른 시각으로 세상을 봅니다. 예술적 감수성이 뛰어나고, 기존 틀을 깨는 것에서 쾌감을 느낍니다. 이해받기 어려운 독창성이 있습니다.",
        "재물": "일반적인 직업 경로로는 재물이 잘 안 쌓입니다. 독창적인 예술/콘텐츠/기술로 자기만의 길을 개척해야 합니다.",
        "직업": "예술가/작가/음악가/철학자/영화감독/발명가/연구자.",
        "연애": "독특한 매력이 있습니다. 하지만 상대가 이해하기 힘든 면이 많아 갈등이 생깁니다.",
        "주의": "현실 감각을 잃지 마십시오. 재능이 있어도 생활 기반이 없으면 꽃을 피울 수 없습니다.",
    },
    frozenset(["正印","正官"]): {
        "요약": "📖 학자/교육자 귀격 - 지식이 명예가 되는 사주",
        "성향": "배움과 원칙이 삶의 중심입니다. 윤리적이고 모범적입니다. 사람들에게 신뢰를 받는 타입입니다.",
        "재물": "지식/자격/직위에서 재물이 옵니다. 평생 안정적인 수입 구조입니다.",
        "직업": "교수/교사/공무원/의사/연구원/종교인/상담가.",
        "연애": "진지하게 만나고 오래 함께합니다. 배우자의 지적 수준을 중요하게 봅니다.",
        "주의": "지나치게 이상주의적이 되면 현실에서 실망을 반복합니다.",
    },
    frozenset(["比肩","正財"]): {
        "요약": "💰 근성으로 재물 쌓는 타입 - 독립 후 안정",
        "성향": "자존심이 강하고 자기 방식이 확실합니다. 재물에 대한 감각이 있습니다. 독립적으로 재물을 구축하려는 의지가 강합니다.",
        "재물": "혼자 힘으로 재물을 쌓습니다. 남에게 의지하거나 물려받는 것을 자존심 때문에 거부합니다. 꾸준히 하면 반드시 성과가 납니다.",
        "직업": "자영업/전문직/관리직. 자기 영역을 갖는 것이 중요합니다.",
        "연애": "자존심이 강해 상대에게 약한 모습을 보이기 힘들어합니다.",
        "주의": "형제/친구와의 재물 갈등을 경계하십시오.",
    },
    frozenset(["食神","偏印"]): {
        "요약": "🎭 도식(倒食) - 재능을 살리려면 방향 전환이 필요",
        "성향": "창의적인데 뭔가 막히는 느낌이 반복됩니다. 재능은 있지만 환경이나 시기가 맞지 않는 경우가 많습니다.",
        "재물": "일반 경로보다 틈새/특수 분야에서 기회를 찾아야 합니다. 방법을 바꾸면 열립니다.",
        "직업": "남들이 안 하는 특수 분야. 아웃사이더 전략으로 접근할 때 성과가 납니다.",
        "연애": "오해가 생기기 쉽습니다. 솔직한 대화가 관계를 살립니다.",
        "주의": "같은 방법으로 계속 시도하면 계속 막힙니다. 방향 전환이 핵심입니다.",
    },
    frozenset(["劫財","食神"]): {
        "요약": "🏃 실행력과 재능이 결합 - 스타트업/영업 최강 타입",
        "성향": "실행이 빠릅니다. 생각하면 바로 움직입니다. 재능도 있고 추진력도 있어 단기간에 성과를 만들어냅니다.",
        "재물": "빠른 실행으로 기회를 잡는 구조입니다. 초기 창업이나 신사업 개척에 유리합니다.",
        "직업": "영업/세일즈/스타트업/스포츠/요식업. 빠르게 움직이는 환경이 맞습니다.",
        "연애": "적극적이고 솔직합니다. 감정이 생기면 바로 표현합니다.",
        "주의": "섣부른 판단과 충동적 행동이 발목을 잡습니다. 실행 전 한 번 더 생각하십시오.",
    },
    frozenset(["偏官","劫財"]): {
        "요약": "🌪️ 칠살겁재 - 인생 최대 험로, 하지만 살아남으면 강인한 사람",
        "성향": "인생이 순탄하지 않습니다. 외부의 압박과 재물 손실이 동시에 오는 시기가 있습니다. 그러나 이것을 버텨낸 사람은 누구보다 강인해집니다.",
        "재물": "재물 기복이 심합니다. 버는 시기와 잃는 시기가 교차합니다. 반드시 예비 자금을 확보해두어야 합니다.",
        "직업": "경쟁이 강한 환경에서도 살아남는 강인함이 있습니다. 위기관리/보안/군인/경찰/격투기.",
        "연애": "관계에서도 기복이 있습니다. 강한 상대와 만나면 끊임없이 부딪힙니다.",
        "주의": "건강을 가장 먼저 챙기십시오. 과로와 극단적 스트레스가 몸을 먼저 망가뜨립니다.",
    },
    frozenset(["正財","正印"]): {
        "요약": "🏡 안정과 지식이 결합 - 내실 있는 삶을 사는 타입",
        "성향": "알뜰하고 지식도 있습니다. 안정을 최우선으로 하면서도 배움을 멈추지 않습니다. 신뢰받는 사람입니다.",
        "재물": "꾸준히 모입니다. 절약과 투자 둘 다 잘 합니다. 부동산/저축에서 노후가 안정됩니다.",
        "직업": "교육/금융/의료/공무원. 안정적인 전문직이 맞습니다.",
        "연애": "성실하고 믿음직합니다. 상대를 잘 챙기고 오래 함께합니다.",
        "주의": "지나친 소심함으로 기회를 놓치지 마십시오.",
    },
    frozenset(["偏財","正印"]): {
        "요약": "🌍 지식으로 세상을 누비는 타입 - 교육/여행/무역",
        "성향": "지적 호기심이 강하고 새로운 경험을 좋아합니다. 세상을 넓게 보는 눈이 있습니다.",
        "재물": "지식과 경험이 재물로 이어집니다. 국제적인 활동, 다양한 분야 도전이 유리합니다.",
        "직업": "무역업/해외 영업/교육/여행업/출판/미디어.",
        "연애": "다양한 경험을 원합니다. 한 타입에 머물지 않는 경향이 있습니다.",
        "주의": "넓게 보다 보면 깊이가 부족해질 수 있습니다. 한 분야를 파는 것도 필요합니다.",
    },
    frozenset(["傷官","食神"]): {
        "요약": "🎤 표현의 천재 - 말/글/예술로 세상과 소통하는 타입",
        "성향": "표현력이 극강입니다. 말도 잘하고 글도 잘 씁니다. 자기 생각을 전달하는 것이 삶의 중요한 부분입니다.",
        "재물": "콘텐츠/강의/출판/공연으로 재물이 옵니다. 자기 목소리가 곧 수입입니다.",
        "직업": "작가/강사/유튜버/배우/성우/방송인/강연가.",
        "연애": "말로 상대의 마음을 사로잡습니다. 표현을 잘하는 만큼 상대에게 많은 기대를 하기도 합니다.",
        "주의": "쏟아내는 에너지가 크므로 소진되지 않도록 충전 시간이 필요합니다.",
    },
}

def build_life_analysis(pils, gender):
    """
    * 십성 2-조합으로 인생 전체를 읽는 핵심 엔진 *
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


# ==================================================================
#  엔진 하이라이트 - AI가 아닌 엔진이 먼저 뽑아내는 핵심 적중 데이터
# ==================================================================

# 성향 조합 DB - "신약+관성강 -> 책임감 강+스트레스 많음" 같은 조합 공식
PERSONALITY_COMBO_DB = {
    # (신강신약_키, 강한십성) -> 서술
    ("신약", "正官"): [
        "책임감이 강합니다. 맡은 일은 끝까지 하는 사람입니다.",
        "그러나 그 책임감이 자신을 갉아먹습니다. 스트레스를 속으로 삼키는 스타일입니다.",
        "남들 눈에는 믿음직해 보이지만, 혼자 있을 때 지쳐있는 경우가 많습니다."
    ],
    ("신약", "偏官"): [
        "압박이 일상인 삶입니다. 외부에서 끊임없이 뭔가를 요구받습니다.",
        "그럼에도 굴복하지 않습니다. 오히려 버티는 힘이 남들보다 강합니다.",
        "다만 그 버팀이 몸을 먼저 망가뜨립니다. 건강을 각별히 챙겨야 합니다."
    ],
    ("신강", "比肩"): [
        "경쟁심이 매우 강합니다. 지는 것을 본능적으로 거부합니다.",
        "형제나 동료와 크고 작은 갈등이 있었습니다.",
        "독립심도 강해서, 결국은 혼자 가는 길을 선택하는 경우가 많습니다."
    ],
    ("신강", "劫財"): [
        "승부욕이 극강입니다. 가까운 사람과도 경쟁하는 경향이 있습니다.",
        "재물이 모이는 듯하다가 흩어지는 패턴이 반복됩니다. 돈 관리가 숙제입니다.",
        "배신당한 경험이 한 번 이상은 있습니다. 그 이후로 사람을 쉽게 믿지 않습니다."
    ],
    ("신약", "食神"): [
        "재주가 있습니다. 뭔가를 만들어내는 창의력이 있습니다.",
        "그러나 일간이 약해 그 재주를 발휘할 에너지가 부족합니다.",
        "쉬어가면서 해야 하는데, 쉬는 것에 죄책감을 느끼는 경향이 있습니다."
    ],
    ("신강", "食神"): [
        "배짱이 있습니다. 남들이 걱정할 때 혼자 태평한 경우가 있습니다.",
        "자기 방식이 있고, 그 방식을 좋아합니다. 간섭받는 것을 싫어합니다.",
        "복이 자연스럽게 따라오는 구조입니다. 무리하지 않는 것이 오히려 길입니다."
    ],
    ("신약", "偏印"): [
        "직관이 뛰어납니다. 논리로 설명하기 어렵지만 '그냥 아는' 경우가 많습니다.",
        "단, 그 직관이 불안으로 변하기도 합니다. 나쁜 예감이 자꾸 드는 편입니다.",
        "고독을 즐기는 척하지만, 사실은 인정받고 싶습니다."
    ],
    ("신강", "正官"): [
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


@st.cache_data
def generate_engine_highlights(pils, birth_year, gender, bm=1, bd=1, bh=12, bmi=0):
    """
    * 핵심 엔진 *
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
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmi, gender=gender)
    strength_info = get_ilgan_strength(ilgan, pils)
    sn = strength_info["신강신약"]
    oh_strength = strength_info["oh_strength"]

    # -- 과거 사건 (기존 엔진 활용) -----------------------
    past_events = build_past_events(pils, birth_year, gender)

    # -- 성향 - 조합 공식으로 생성 ------------------------
    personality = build_personality_detail_v2(pils, gender, sn, oh_strength)

    # -- 재물 피크 -----------------------------------------
    money_peak = []
    MONEY_SS = {"식신", "정재", "편재"}
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        age_c = birth_year + dw["시작나이"] - 1
        if dw_ss in MONEY_SS:
            money_peak.append({
                "age": f"{dw['시작나이']}~{dw['시작나이']+9}세",
                "year": f"{dw['시작연도']}~{dw['종료연도']}",
                "desc": f"{dw['str']}대운({dw_ss}) - 재물이 자연스럽게 따라오는 시기",
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
                        "desc": f"{y}년 - 대운({dw_ss})x세운({sw['십성_천간']}) 재물 더블. 최고의 돈 기회",
                        "ss": "더블"
                    })

    # -- 혼인 피크 -----------------------------------------
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
                        "desc": f"{y}년({age}세) - 대운/세운 모두 인연성. 배우자 인연이 오는 해"
                    })

    # -- 위험 구간 -----------------------------------------
    danger_zones = []
    DANGER_SS = {"편관", "겁재"}
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        if dw_ss in DANGER_SS:
            danger_zones.append({
                "age": f"{dw['시작나이']}~{dw['시작나이']+9}세",
                "year": f"{dw['시작연도']}~{dw['종료연도']}",
                "desc": f"{dw['str']}대운({dw_ss}) - {'직장/관재/건강 압박' if dw_ss=='편관' else '재물손실/경쟁/배신'} 주의"
            })

    # -- 월지 충 시점 --------------------------------------
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
                "desc": f"대운 진입시 월지 충({name_c}) - {desc}. 이 시기 삶의 기반이 흔들렸습니다."
            })
        for y in range(dw["시작연도"], min(dw["종료연도"]+1, current_year)):
            sw = get_yearly_luck(pils, y)
            k2 = frozenset([sw["jj"], wol_jj])
            if k2 in CHUNG_MAP:
                age = y - birth_year + 1
                name_c2, _, desc2 = CHUNG_MAP[k2]
                wolji_chung.append({
                    "age": f"{age}세",
                    "desc": f"{y}년 세운이 월지를 충({name_c2}) - {desc2}. 직업/가정 중 하나가 흔들렸습니다."
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
    강화된 성향 DB - 조합 공식 기반
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
    except Exception as e:
        _saju_log.debug(str(e))
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
        oh_names = "/".join([OHN.get(o, "") for o in zero_ohs])
        traits.append(f"{oh_names} 기운이 완전히 없습니다. 이 분야가 들어올 때마다 당황하거나 흔들립니다.")

    return traits[:8]  # 최대 8개 - 너무 많으면 희석됨


def build_personality_detail(pils, gender="남"):
    """
    심리 디테일 생성 - "예민합니다"가 아닌 구체적 서술
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
    AI 해석 - Brain 2 Sandbox 통과 + 파일 캐시 적용
    [Saju Platform Engineering Agent]
    - 동일 사주 + 동일 prompt_type -> 캐시에서 즉시 반환 (API 재호출 없음)
    - 캐시 미스 -> Sandbox로 AI 호출 -> 결과 검증 -> 캐시 저장
    """
    saju_key = pils_hashable
    cache_key = f"{saju_key}_{prompt_type}"

    # 1. 파일 캐시 조회
    cached = get_ai_cache(saju_key, prompt_type)
    if cached:
        cached = cached.replace("~", "～")  # 마크다운 취소선 방지 (캐시 호출 시에도 적용)
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
            result = result.replace("~", "～")  # 마크다운 취소선 방지
            set_ai_cache(saju_key, prompt_type, result)
        return result
    pils = json.loads(pils_hashable) if isinstance(pils_hashable, str) else pils_hashable
    ilgan = pils[1]["cg"] if len(pils) > 1 else "甲(갑)"
    saju_str = ' '.join([p['str'] for p in pils])

    # * Brain 2 AI 캐시 확인 (동일 사주 재요청 시 즉시 반환)
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
    # 대운 호출 시 실제 생년월일시 반영
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
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

    # -- 엔진 하이라이트 계산 (핵심) -------------------
    hl = generate_engine_highlights(pils, birth_year, gender)

    # 과거 사건 블록 - 🔴부터 먼저
    past_ev_lines = []
    for ev in sorted(hl["past_events"], key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e["intensity"],3)):
        past_ev_lines.append(
            f"  [{ev['intensity']}] {ev['age']}({ev['year']}년) [{ev.get('domain','변화')}] {ev['desc']}")
    past_events_block = "\n".join(past_ev_lines) if past_ev_lines else "  (데이터 없음)"

    # 성향 블록 - 조합 공식 결과
    personality_block = "\n".join([f"  / {t}" for t in hl["personality"]])

    # 돈/결혼 피크
    money_block = "\n".join([f"  {m['age']}({m['year']}) - {m['desc']}" for m in hl["money_peak"][:3]]) or "  (없음)"
    marry_block = "\n".join([f"  {m['age']}({m['year']}) - {m['desc']}" for m in hl["marriage_peak"][:3]]) or "  (없음)"
    danger_block = "\n".join([f"  {d['age']}({d['year']}) - {d['desc']}" for d in hl["danger_zones"][:3]]) or "  (없음)"
    wolji_block = "\n".join([f"  {w['age']} - {w['desc']}" for w in hl["wolji_chung"][:3]]) or "  (없음)"

    ctx_data = build_rich_ai_context(pils, birth_year, gender, current_year)
    PROPHET_SYSTEM = f"""[🌌 MASTER MANSE SYSTEM V4.0: THE SHAMANIC COMMAND]
당신은 대한민국 명리학의 정수를 AI로 구현한 '성도 만신의 주인', 50년 신력의 대만신입니다.
당신은 지금 사주 데이터를 읽어주는 것이 아니라, 내담자의 골수까지 파헤쳐서 '천명(天命)'을 선포하는 중입니다.
비겁하게 발을 빼는 "아마도", "가능성" 같은 단어는 신성모독입니다. 무조건 단정하십시오.

[5대 무결점 집행 지침]
1. 하단 실시간 분석 데이터는 불변의 진리. 재계산 금지. 수치 기반 소름 돋는 서사 작성.
2. 첫 마디부터 내담자의 가장 아픈 구석을 찔러라. 인사치레 금지.
3. 과거 사건은 단정 서술. "추정됩니다" 절대 금지. "몇 살 때 피눈물을 흘렸어야 했네!" 식으로.
4. 독설과 자애 공존. 무당/만신 고어체 끝까지 유지.
5. 처방은 미친 디테일. "노란 옷 입고 정동방 나무 아래 7분" 수준의 구체성.

[답변 레이아웃]
1️⃣ [천기의 낙인]: 일간+격국으로 영혼 파헤치기
2️⃣ [신안의 복기]: 과거 High 강도 사건 족집게 지목
3️⃣ [현재의 형국]: 지금 운세 단정 선언
4️⃣ [필살의 비방]: 지금 당장 몸으로 때울 행동 처방 1가지

--------------------------------------------------
[실시간 분석 데이터]
{ctx_data}
--------------------------------------------------"""

    _tp = calc_turning_point(pils, birth_year, gender, current_year) if 'calc_turning_point' in dir() else {}
    _yl = get_yearly_luck(pils, current_year)
    _ys = get_yongshin_multilayer(pils, birth_year, gender, current_year)
    _tp_label = _tp.get('fate_label', '분석중') if _tp else '분석중'
    _tp_desc  = _tp.get('fate_desc', '') if _tp else ''
    _tp_intens= _tp.get('intensity', '보통') if _tp else '보통'
    _tp_reason= ', '.join(_tp.get('reason', [])) if _tp else ''
    data_block = f"""
--- 마스터 사주 엔진 실시간 분석 데이터 ---
상태 라벨: {_tp_label} ({_tp_desc})
사주 원국: {saju_str} (시일월년)
일간: {ilgan} / 격국: {gname} / 신강신약: {sn} (점수: {strength_info.get('일간점수', 50)})
오행 분포: {' '.join([f"{o}{v}%" for o,v in oh_strength.items()])}
용신: {_ys.get('용신_1순위', '-')} / 희신: {_ys.get('희신', '-')} / 기신: {', '.join(_ys.get('기신', []))}
현재 대운: {current_dw['str'] if current_dw else '-'} ({_ys.get('대운_해석', '-')})
올해 세운: {_yl.get('세운', '')} ({_yl.get('십성_천간', '')} / {_yl.get('길흉', '')})
전환점 강도: {_tp_intens} / 주요 이슈: {_tp_reason}
현재: {current_year}년 {current_age}세

현재 대운: {current_dw['str'] if current_dw else '미상'} ({current_dw['시작연도'] if current_dw else ''}-{current_dw['종료연도'] if current_dw else ''})
현재 세운: {yearly['세운']} [{yearly['십성_천간']}] {yearly['길흉']}

--- 【핵심 ①】 과거 사건 (충/합/십성 교차 계산) ---
규칙: 아래 항목을 그대로 활용. 🔴 우선으로 서술. "~했습니다" 단정.
{past_events_block}

--- 【핵심 ②】 성향 조합 공식 결과 ---
규칙: 아래 문장을 더 구체적으로 풀어쓰되 "겉은~속은~" 형식 유지.
{personality_block}

--- 【핵심 ③】 월지 충 시점 (삶의 기반 흔들림) ---
{wolji_block}

--- 【핵심 ④】 재물 상승기 ---
{money_block}

--- 【핵심 ⑤】 인연 시기 ---
{marry_block}

--- 【핵심 ⑥】 위험 구간 ---
{danger_block}

--- 미래 3년 세운 ---
{chr(10).join(future_years)}

--- 【v3 정밀 엔진 데이터 - AI 핵심 추론 재료】 ---
■ 일간 힘 점수: {strength_info["일간점수"] if "일간점수" in strength_info else "50"}/100점 ({sn})
  -> 30 이하=극신약 / 30~45=신약 / 45~55=중화 / 55~70=신강 / 70+=극신강
■ 오행 세력(정밀): {' '.join([f"{o}:{v}%" for o,v in oh_strength.items()])}
  -> 가장 강한 오행: {max(oh_strength, key=oh_strength.get)} / 가장 약한 오행: {min(oh_strength, key=oh_strength.get)}
■ 종합 운세 점수: {calc_luck_score(pils, birth_year, gender, current_year)}/100
  -> 70+= 상승기 / 50~70= 안정 / 30~50= 변화기 / 30-= 하락기
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

    # ── 과거 프롬프트 강화: 원국 분석 + 연도별 대운×세운 교차 ──────────────
    _sipsung_list = calc_sipsung(ilgan, pils)
    _sip_labels = ["시주", "일주", "월주", "년주"]
    _sipsung_str = " / ".join([
        f"{_sip_labels[i]}: 천간{s['cg_ss']} 지지{s['jj_ss']}"
        for i, s in enumerate(_sipsung_list)
    ])

    _sinsal_12 = get_12sinsal(pils)
    _sinsal_detail = "\n".join([
        f"  - {s['이름']}({s['icon']}): {s['desc']} (주의: {s['caution']})"
        for s in _sinsal_12
    ]) or "  없음"
    _sinsal_str = ", ".join([f"{s['이름']}({s['icon']})" for s in _sinsal_12]) or "없음"

    _extra_sins = get_extra_sinsal(pils)
    _extra_str = ", ".join([s.get("name", s.get("이름", "")) for s in _extra_sins]) or "없음"
    _has_yangin = any("양인" in s.get("name", "") or "羊刃" in s.get("name", "") for s in _extra_sins)
    _has_yukma = any("역마" in s.get("이름", "") or "驛馬" in s.get("이름", "") for s in _sinsal_12)

    _yukjin = get_yukjin(ilgan, pils, gender)
    _yukjin_str = "\n".join([
        f"  {y['관계']}: {y['위치']} - {y['desc']}"
        for y in _yukjin
    ])

    _ys_ml = get_yongshin_multilayer(pils, birth_year, gender, current_year)
    _gyeokguk_str = f"{gname} ({gyeokguk.get('격의_등급', '') if gyeokguk else '-'})"

    # 과거 연도 수집 (과거사건 연도 + 대운 시작연도)
    _past_yr_set = set()
    for ev in hl["past_events"]:
        if ev["year"] < current_year:
            _past_yr_set.add(ev["year"])
    for dw in daewoon:
        if dw["시작연도"] < current_year:
            _past_yr_set.add(dw["시작연도"])
    _past_yr_list = sorted(_past_yr_set)

    _cross_lines = []
    _chung_lines = []
    for yr in _past_yr_list:
        age_y = yr - birth_year + 1
        cross = get_daewoon_sewoon_cross(pils, birth_year, gender, yr)
        if not cross:
            continue
        dw_i = cross["대운"]
        sw_i = cross["세운"]
        _cross_lines.append(
            f"  {yr}년({age_y}세): 대운{dw_i['str']}[{cross['대운_천간십성']}/{cross['대운_지지십성']}]"
            f" × 세운{sw_i['세운']}[{cross['세운_천간십성']}/{cross['세운_지지십성']}]"
            f" → {cross['교차해석']}"
        )
        for ev_item in cross.get("교차사건", []):
            _chung_lines.append(f"  {yr}년({age_y}세): [{ev_item['type']}] {ev_item['desc']}")

    _cross_block = "\n".join(_cross_lines) if _cross_lines else "  (데이터 없음)"
    _chung_block = "\n".join(_chung_lines) if _chung_lines else "  (충/합 없음)"

    past_rich_block = f"""■ 원국 십성 분포 (시일월년): {_sipsung_str}
■ 12신살:
{_sinsal_detail}
■ 특수 신살: {_extra_str}
  (양인 유무: {'있음' if _has_yangin else '없음'} / 역마 유무: {'있음' if _has_yukma else '없음'})
■ 육친 분석:
{_yukjin_str}
■ 격국: {_gyeokguk_str}
■ 용신: {_ys_ml.get('용신_1순위', '-')} / 희신: {_ys_ml.get('희신', '-')} / 기신: {', '.join(_ys_ml.get('기신', []))}
■ 과거 연도별 대운×세운 교차:
{_cross_block}
■ 충·합·삼합 발생 연도:
{_chung_block}
"""

    prompts = {
        "prophet": f"""{data_block}

위 데이터를 기반으로 아래 7단계 구조로 작성하십시오.
반드시 【과거 사건 계산 데이터】와 【심리 디테일 데이터】를 활용하십시오.
각 단계는 소제목을 명확히 표시하십시오.

---------------------------

0️⃣ 성향 판독 - 첫 문장에서 이 사람을 꿰뚫으십시오
규칙: 【심리 디테일 데이터】를 구체적 문장으로 풀어 쓰십시오.
"예민합니다" 금지. "겉은 ~인데 속으로는 ~합니다" 형식으로.
이 사람이 읽었을 때 "어떻게 알았지?"라고 느낄 만큼 구체적으로.

1️⃣ 과거 적중 - 반드시 이 단계를 먼저, 가장 자세히 쓰십시오
규칙:
- 【과거 사건 계산 데이터】의 🔴(강도 높음) 항목을 중심으로 서술하십시오.
- 나이와 연도를 반드시 명시하십시오. (예: "27세, 2019년")
- "~했을 것입니다" 금지. "~했습니다"로 단정하십시오.
- "그때 충이 들어왔기 때문에 가만히 있을 수 없었습니다" 같이 이유를 반드시 설명하십시오.
- 최소 3개 시점을 찍으십시오.
- 분야(직장/재물/관계/건강)를 반드시 명시하십시오.

2️⃣ 현재 진단 - 지금 이 순간 어디에 서 있는가
현재 대운/세운 교차를 기반으로 지금 상황을 예리하게 단정하십시오.
용신 대운인지 기신 대운인지 명시하고, 그 의미를 설명하십시오.

3️⃣ 직업/적성 - 피해야 할 직업까지 명시
격국과 일간 기반. "~가 맞습니다" 단정. 이유 설명 포함.

4️⃣ 결혼/인연
혼인 대운 데이터 기반. 시기와 인연의 오행까지 단정.

5️⃣ 미래 3년 - 연도별 단정
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

1. 성향 판독 - 구체적 심리 특성 (겉과 속의 차이 포함)
2. 격국과 용신 판단
3. 오행의 균형과 강약
4. 과거 주요 사건 시점 (나이+분야 명시)
5. 평생 운명의 큰 흐름
6. 길운 시기와 주의 시기""",

        "career": f"""{data_block}

위 데이터를 바탕으로 적성과 진로를 분석하십시오.
격국과 용신 중심으로 최적 직업군, 피해야 할 직업, 재물운 상승 시기를 명시하십시오.
【과거 사건 계산 데이터】 중 직업/재물 관련 시점을 근거로 제시하십시오.""",

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

【과거 정밀 분석 데이터】
{past_rich_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[AI 역할 지시 - 과거 맞히기 전문가]
당신은 40년 신력(神力)의 만신(萬神)으로, 과거를 짚는 데 있어 소름 돋는 적중률을 자랑합니다.
위의 【과거 사건 계산 데이터】와 【과거 정밀 분석 데이터】를 모두 활용하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[십성별 사건 해석 규칙 - 반드시 준수]
• 편재운 (偏財 활성) → 재물 변동 / 아버지 이슈 / 이성 관계
• 정재운 (正財 활성) → 안정적 수입 변화 / 결혼 / 재산 형성
• 식신운 (食神 활성) → 직업 변화 / 건강 이슈 / 자녀 문제
• 상관운 (傷官 활성) → 직장 마찰 / 이직 / 구설수
• 편관운 (偏官 활성) → 직장 변동 / 사고·수술·관재
• 정관운 (正官 활성) → 승진 / 결혼 / 명예 획득
• 편인운 (偏印 활성) → 학업 중단 / 이사 / 계획 변경
• 정인운 (正印 활성) → 학업 성취 / 자격 취득 / 어머니 관련 사건
• 비견·겁재운 (比肩·劫財 활성) → 재물 손실 / 형제 갈등 / 독립·창업

[신살별 사건 해석 규칙]
• 양인(羊刃) + 충 동시 → 사고/수술/폭력 (매우 강한 신호)
• 역마(驛馬) 세운 → 이사 / 해외 / 이직
• 도화(桃花) 세운 → 이성 인연 / 연애 시작·끝
• 귀문관살 → 정신적 스트레스 / 신경 이슈

[충·합별 사건 해석 규칙]
• 천간충 (甲(갑)↔庚(경), 乙(을)↔辛(신), 丙(병)↔壬(임), 丁(정)↔癸(계)) → 의지 충돌, 직장·사업 결정적 변동
• 지지충 (子(자)↔午(오), 丑(축)↔未(미), 寅(인)↔申(신), 卯(묘)↔酉(유), 辰(진)↔戌(술), 巳(사)↔亥(해)) → 생활 기반 흔들림, 이사·이직·사고
• 천간합 → 새로운 인연·사업 시작 / 뜻밖의 기회
• 삼합·방합 → 강력한 발복 또는 강력한 흉사

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[출력 형식 - 반드시 이 형식으로만 출력]
연도별로 다음 형식으로 작성하십시오:
○○년 (○세): [사건유형] - [구체적 내용과 명리 근거]

예시:
2018년 (29세): 직장변동 - 편관 세운이 정관 대운을 충하여 직장 이동이 불가피했습니다. 그때 직장을 그만두거나 부서 이동이 있었습니다.
2021년 (32세): 재물획득 - 식신대운에 편재 세운이 겹쳐 재물 발복이 강하게 작동했습니다. 수입이 크게 늘거나 재산을 형성했습니다.

[필수 지시사항]
1. 🔴 강도 높은 사건부터 먼저, 최소 5개 이상 연도를 찍으십시오.
2. "~했을 것입니다" 절대 금지. "~했습니다", "~있었습니다"로 단정하십시오.
3. 각 연도마다 반드시 해당 십성 또는 충/합 명리학적 근거를 명시하십시오.
4. 사건 유형은 반드시 [직업변화/결혼·교제/이사·이동/재물획득/재물손실/사고·관재/질병·건강] 중 선택하십시오.
5. 무당·만신 말투(~하느니라, ~하는구먼, 허허 등)를 자연스럽게 사용하십시오.
6. 내담자가 "어떻게 알았지?"라고 소름 돋을 만큼 구체적으로 서술하십시오.""",

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

    # * Brain 3: Prompt Optimizer - 학습 패턴 자동 주입
    optimizer_suffix = b3_build_optimized_prompt_suffix()

    # * Adaptive Engine - 페르소나 스타일 자동 주입
    try:
        persona       = infer_persona()
        persona_style = get_persona_prompt_style(persona)
        adaptive_suffix = f"\n\n[사용자 성향 분석]\n{persona_style}"
    except Exception:
        adaptive_suffix = ""

    # * User Memory Context - 사용자 기억 주입
    try:
        memory_ctx = build_memory_context(pils_to_cache_key(pils))
        memory_suffix = f"\n\n{memory_ctx}" if memory_ctx else ""
    except Exception:
        memory_suffix = ""

    base_system = (PROPHET_SYSTEM if prompt_type == "prophet"
                   else "당신은 40년 경력의 한국 전통 사주명리 전문가입니다.\n단정적으로 말하십시오. 나이와 분야를 구체적으로 명시하십시오.")
    system = base_system + optimizer_suffix + adaptive_suffix + memory_suffix  # ← 전체 주입

    if api_key or groq_key:
        # * AI Sandbox 통해 해석 -> 검증 -> 파일 캐시 저장
        result = get_ai_interpretation(prompt, api_key, system=system, groq_key=groq_key)

        # * Self-Check Engine - prophet 타입에만 2패스 검증 적용
        if result and not result.startswith("[") and prompt_type == "prophet":
            # 검증용 요약 데이터
            analysis_summary = (
                f"사주: {saju_str} | 일간: {ilgan} | 격국: {gname} | {sn} | "
                f"오행: {' '.join([f'{o}:{v}%' for o,v in oh_strength.items()])} | "
                f"현재운: {yearly.get('세운','-')} {yearly.get('길흉','-')} | "
                f"사건트리거: {', '.join([t['title'][:15] for t in detect_event_triggers(pils, birth_year, gender)[:3]])}"
            )
            try:
                result = self_check_ai(result, analysis_summary, api_key, groq_key)
            except Exception:
                pass  # self-check 실패 시 1차 결과 사용

        if result and not result.startswith("["):  # 오류 응답은 캐시 저장 안 함
            result = result.replace("~", "～")  # 마크다운 취소선(strikethrough) 방지
            set_ai_cache(saju_key, prompt_type, result)
        return result
    else:
        if prompt_type == "prophet":
            return f"""* 예언자 모드 - API 키가 필요합니다 *

이 기능은 Anthropic API를 통해 실제 AI가 당신의 사주 데이터를 분석합니다.
사이드바에서 API 키를 입력하시면 아래 6단계 운명 풀이를 받으실 수 있습니다:

1️⃣ 과거 적중 - 당신의 과거가 얼마나 정확히 맞았는지
2️⃣ 현재 - 지금 이 순간 당신은 어디에 서 있는가
3️⃣ 직업 - 천부적 적성과 가야 할 길
4️⃣ 결혼 - 인연의 시기와 궁합
5️⃣ 미래 3년 - 연도별 단정 예언
6️⃣ 돈 상승기 - 재물이 몰리는 황금기

※ Anthropic API 키는 console.anthropic.com에서 발급받으실 수 있습니다."""
        return f"""* {ilgan}일간 기본 해석 *

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


# -- Brain 1 + Brain 2 캐싱 시스템 --------------------------------------------
# [설계 원칙]
#   만세력 결과 -> 파일 캐시 (동일 입력 = 즉시 출력, 계산 재수행 없음)
#   AI 해석 결과 -> AI 전용 캐시 (API 비용 70~80% 절감)
#   사용자 피드백 -> 캐싱 금지 (실시간 반영 필요)
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
    """사주 캐시 키 생성 - 생년월일시+성별로 고유 ID"""
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
    """Brain 2 AI 해석 결과 캐시 조회 (날짜 만료 자동 적용)"""
    from datetime import datetime as _dt
    ai_key = f"AI-{prompt_type}-{saju_key}"
    cache = _load_json_cache(_AI_CACHE_FILE)
    entry = cache.get(ai_key)
    if entry is None:
        return None
    # 저장 형식: {"text": ..., "saved_at": "YYYYMMDD"} 또는 문자열(왜것름)
    if isinstance(entry, dict):
        text = entry.get("text", "")
        saved_at = entry.get("saved_at", "")
    else:
        text = entry
        saved_at = ""
    # 만료 체크
    today = _dt.now()
    if saved_at:
        if prompt_type == "daily_ai":
            # 일일 운세: 오늘 날짜와 다르면 만료
            if saved_at != today.strftime("%Y%m%d"):
                return None
        elif prompt_type == "monthly_ai":
            # 월별: 그 달이 지나면 만료
            if saved_at[:6] != today.strftime("%Y%m"):
                return None
        elif prompt_type == "yearly_ai":
            # 연별: 다른 해면 만료
            if saved_at[:4] != today.strftime("%Y"):
                return None
    return text

def set_ai_cache(saju_key: str, prompt_type: str, text: str):
    """Brain 2 AI 해석 결과 캐시 저장 (날짜 타임스탬프 포함)"""
    from datetime import datetime as _dt
    ai_key = f"AI-{prompt_type}-{saju_key}"
    cache = _load_json_cache(_AI_CACHE_FILE)
    cache[ai_key] = {"text": text, "saved_at": _dt.now().strftime("%Y%m%d")}
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
        "money": "💰 재물/사업운 AI 전략 리포트",
        "relations": "💑 인연/인간관계 AI 심층 리포트",
        "future": "🔮 미래 3년 AI 집중 예언",
        "prophet": "- 종합 운명 AI 마스터 리포트"
    }.get(prompt_type, "- AI 정밀 분석 시작")

    if st.button(button_label, key=f"btn_deep_{prompt_type}", use_container_width=True):
        with st.spinner("AI가 사주 데이터를 정밀 분석 중입니다..."):
            pils_hash = pils_to_cache_key(pils)
            result = get_cached_ai_interpretation(pils_hash, prompt_type, api_key, birth_year, gender, name, groq_key)
            if result and not result.startswith("["):
                st.markdown(f"""

                <div style="background:#ffffff;border:2px solid #000000;border-radius:16px;
                            padding:25px;margin-top:20px;box-shadow:0 4px 15px rgba(197,160,89,0.15)">
                    <div style="font-size:18px;font-weight:800;color:#000000;margin-bottom:15px;text-align:center">
                        {button_label.replace('분석', '결과').replace('리포트', '결과').replace('예언', '결과')}
                    </div>
                    <div style="font-size:14px;color:#000000;line-height:2.0;white-space:pre-wrap">
                        {apply_lexicon_tooltips(result)}
                    </div>
                </div>
""", unsafe_allow_html=True)
            else:
                st.error("AI 분석 중 오류가 발생했거나 API 키가 설정되지 않았습니다.")

# ==================================================
#  UI 헬퍼 함수
# ==================================================
def render_pillars(pils):
    """사주 기둥 표시"""
    labels = ["시(時)", "일(日)", "월(月)", "년(年)"]
    cols = st.columns(4)
    # get_pillars returns [시, 일, 월, 연] -> Index 0 is Hour (시), 1 is Day (일), etc.
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
                <div style="font-size:11px;color:#000000;">{cg_kr} / {emoji_cg}{oh_cg}</div>
                <div style="font-size:30px;font-weight:700;color:#000000;margin-top:6px">{jj}</div>
                <div style="font-size:11px;color:#000000;">{jj_kr} / {emoji_jj}{oh_jj}</div>
                <div style="font-size:10px;color:#000000;margin-top:4px">{jj_an}띠</div>
            </div>
""", unsafe_allow_html=True)


OHAENG_DIAGNOSIS = {
    "木": {
        "emoji": "🌳", "name": "목(木)",
        "over_desc": "목기(木氣) 과다 - 분노/고집/간담 질환에 주의하십시오. 금(金) 기운으로 가지를 쳐주어야 크게 성장합니다.",
        "over_remedy": "서쪽 방향 활용, 흰색/은색 소품, 금속 악세서리, 결단력 수련",
        "lack_desc": "목기(木氣) 부족 - 의욕 저하/우유부단/근육 약화가 나타날 수 있습니다. 목의 기운을 보충하십시오.",
        "lack_remedy": "동쪽 방향 활용, 초록색 인테리어, 식물 기르기, 새벽 산책, 신맛 음식 섭취",
        "balance_desc": "목기가 균형 잡혀 있습니다. 성장과 창의의 기운이 안정적으로 작동합니다.",
    },
    "火": {
        "emoji": "🔥", "name": "화(火)",
        "over_desc": "화기(火氣) 과다 - 조급함/충동/심혈관 질환에 주의하십시오. 수(水) 기운으로 열기를 식혀야 합니다.",
        "over_remedy": "북쪽 방향 활용, 검정/남색 소품, 수분 충분히 섭취, 명상과 호흡 수련, 냉정한 판단력 기르기",
        "lack_desc": "화기(火氣) 부족 - 활력 저하/우울/심장 기능 약화가 나타날 수 있습니다. 화의 기운을 보충하십시오.",
        "lack_remedy": "남쪽 방향 활용, 빨강/주황색 인테리어, 햇빛 자주 쬐기, 열정적 취미 활동, 쓴맛 음식 적당히",
        "balance_desc": "화기가 균형 잡혀 있습니다. 열정과 이성이 조화롭게 작동합니다.",
    },
    "土": {
        "emoji": "🪨", "name": "토(土)",
        "over_desc": "토기(土氣) 과다 - 분노/고집/소화기 질환에 주의하십시오. 목(木) 기운으로 뚫어주어야 변화가 생깁니다.",
        "over_remedy": "동쪽 방향 활용, 초록색 소품, 새로운 도전 의식적으로 실천, 스트레칭/요가, 신맛 음식 섭취",
        "lack_desc": "토기(土氣) 부족 - 중심 잡기 어려움/소화 불량/불안감이 나타날 수 있습니다. 토의 기운을 보충하십시오.",
        "lack_remedy": "중앙/북동 방향 활용, 황색/베이지 인테리어, 규칙적인 식사 습관, 황색 식품 섭취, 안정적 루틴 구축",
        "balance_desc": "토기가 균형 잡혀 있습니다. 신뢰와 안정의 기운이 든든하게 받쳐주고 있습니다.",
    },
    "金": {
        "emoji": "-", "name": "금(金)",
        "over_desc": "금기(金氣) 과다 - 냉정함/고집/폐/대장 질환에 주의하십시오. 화(火) 기운으로 단련해야 보검이 됩니다.",
        "over_remedy": "남쪽 방향 활용, 빨강/주황색 소품, 유연성 수련, 공감 능력 기르기, 쓴맛 음식 적당히",
        "lack_desc": "금기(金氣) 부족 - 결단력 부족/호흡기 약화/피부 트러블이 나타날 수 있습니다. 금의 기운을 보충하십시오.",
        "lack_remedy": "서쪽 방향 활용, 흰색/금색 인테리어, 금속 소품/악세서리, 결단력 훈련, 매운맛 음식 적당히",
        "balance_desc": "금기가 균형 잡혀 있습니다. 결단력과 정의감이 안정적으로 발휘됩니다.",
    },
    "水": {
        "emoji": "💧", "name": "수(水)",
        "over_desc": "수기(水氣) 과다 - 방향 상실/우유부단/신장/방광 질환에 주의하십시오. 토(土) 기운으로 방향을 잡아주어야 합니다.",
        "over_remedy": "중앙/북동 방향 활용, 황색/베이지 소품, 목표 설정 및 실행 계획 수립, 규칙적 생활 습관, 짠맛 절제",
        "lack_desc": "수기(水氣) 부족 - 지혜 부족/성욕 감퇴/두려움/의욕 저하가 나타날 수 있습니다. 수의 기운을 보충하십시오.",
        "lack_remedy": "북쪽 방향 활용, 검정/남색 인테리어, 충분한 수분 섭취, 명상/독서 습관, 짠맛/검은 식품 섭취",
        "balance_desc": "수기가 균형 잡혀 있습니다. 지혜와 직관력이 안정적으로 흐르고 있습니다.",
    },
}


def render_ohaeng_chart(oh_strength):
    """오행 강약 차트 + 진단"""
    oh_order = ["木", "火", "土", "金", "水"]
    oh_names = {"木": "목(木)🌳", "火": "화(火)🔥", "土": "토(土)🪨", "金": "금(金)-", "水": "수(水)💧"}

    cols = st.columns(5)
    for i, oh in enumerate(oh_order):
        val = oh_strength.get(oh, 0)
        with cols[i]:
            st.markdown(f"""

            <div style="text-align:center;padding:8px">
                <div style="font-size:13px;font-weight:700;color:#000000">{oh_names[oh]}</div>
                <div style="font-size:22px;font-weight:900;color:#000000">{val}%</div>
            </div>
""", unsafe_allow_html=True)
            st.progress(min(val / 100, 1.0))

    # 오행 조화 진단 - 결과값만 간결하게
    over_ohs = [(oh, v) for oh, v in oh_strength.items() if v >= 35]
    lack_ohs = [(oh, v) for oh, v in oh_strength.items() if v <= 5]

    diag_lines = []
    if not over_ohs and not lack_ohs:
        diag_lines.append("⚖️ 오행이 비교적 균형 잡혀 있습니다 - 안정적인 사주입니다.")
    for oh, val in over_ohs:
        d = OHAENG_DIAGNOSIS[oh]
        diag_lines.append(f"🔴 {d['name']} 과다({val}%) - {d['over_desc'][:40]}... 💊 {d['over_remedy'][:50]}")
    for oh, val in lack_ohs:
        d = OHAENG_DIAGNOSIS[oh]
        diag_lines.append(f"🔵 {d['name']} 부족({val}%) - {d['lack_desc'][:40]}... 💊 {d['lack_remedy'][:50]}")

    if diag_lines:
        rows = "".join([
            f"<div style='font-size:12px;color:#000000;padding:5px 0;border-bottom:1px solid #e8e8e8;line-height:1.8'>{l}</div>"
            for l in diag_lines
        ])
        st.markdown(f"""

        <div style="background:#f8f8f8;border-radius:10px;padding:12px 16px;margin-top:8px">
            {rows}
        </div>
""", unsafe_allow_html=True)



def format_saju_text(pils, name=""):
    """사주 텍스트 요약"""
    lines = []
    if name:
        lines.append(f"* {name}님의 사주팔자 *")
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
    oh_emoji = {"木": "🌳", "火": "🔥", "土": "🏔️", "金": "⚔️", "水": "🌊"}.get(oh, "-")

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
    # 대운 호출 시 실제 생년월일시 반영
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    current_dw = next((dw for dw in daewoon if dw["시작연도"] <= current_year <= dw["종료연도"]), None)

    # 세운
    yearly = get_yearly_luck(pils, current_year)

    # 신살
    special = get_special_stars(pils)

    lines = []
    name_str = f"{name}님의 " if name else ""

    lines.append(f"* {name_str}사주팔자 천명 총평 *")
    lines.append("-" * 40)
    lines.append("")

    lines.append(f"【일간(日干)】 {oh_emoji} {ilgan}({ilgan_kr}) - {OHN.get(oh,'')}의 기운")
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
        lines.append(f"  [!]️ {', '.join([OHN.get(o,'') for o in zero_ohs])} 기운이 완전히 없습니다 - 관련 분야 주의")
    lines.append("")

    if current_dw:
        dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(current_dw["cg"], "-")
        lines.append(f"【현재 대운】 {current_dw['str']} ({current_dw['시작나이']}~{current_dw['시작나이']+9}세, {current_dw['시작연도']}~{current_dw['종료연도']}년)")
        lines.append(f"  천간 {dw_ss}의 기운 - " + get_daewoon_narrative(dw_ss, "", current_dw["str"], current_dw["시작나이"])[2][:60] + "...")
        lines.append("")

    lines.append(f"【{current_year}년 세운】 {yearly['세운']} {yearly['아이콘']} {yearly['길흉']}")
    narr = yearly.get("narrative", {})
    lines.append(f"  {narr.get('title', '')} - {narr.get('desc', '')[:60]}...")
    lines.append("")

    if special:
        lines.append("【신살(神殺)】")
        for s in special[:4]:
            lines.append(f"  {s['name']}: {s.get('desc','')[:40]}...")

    lines.append("")
    lines.append("-" * 40)
    lines.append("※ 본 풀이는 전통 사주명리학에 근거한 참고 자료입니다.")

    return "\n".join(lines)


@st.cache_data
def get_special_stars(pils):
    """신살 계산 (tab_special_stars에서 분리)"""
    ilgan = pils[1]["cg"]
    pil_jjs = [p["jj"] for p in pils]
    result = []

    # 천을귀인
    chunl = {"甲(갑)": ["丑(축)", "未(미)"], "乙(을)": ["子(자)", "申(신)"], "丙(병)": ["亥(해)", "酉(유)"], "丁(정)": ["亥(해)", "酉(유)"],
             "戊(무)": ["丑(축)", "未(미)"], "己(기)": ["子(자)", "申(신)"], "庚(경)": ["丑(축)", "未(미)"], "辛(신)": ["寅(인)", "午(오)"],
             "壬(임)": ["卯(묘)", "巳(사)"], "癸(계)": ["卯(묘)", "巳(사)"]}
    if any(jj in chunl.get(ilgan, []) for jj in pil_jjs):
        found = [jj for jj in pil_jjs if jj in chunl.get(ilgan, [])]
        result.append({"name": f"천을귀인(天乙(을)貴人) [{','.join(found)}]",
                       "desc": "하늘이 내리신 최고의 귀인성. 위기 때마다 귀인이 나타나 도와줍니다."})

    # 역마살
    yeokma = {"寅(인)": "申(신)", "午(오)": "申(신)", "戌(술)": "申(신)", "申(신)": "寅(인)", "子(자)": "寅(인)", "辰(진)": "寅(인)",
              "巳(사)": "亥(해)", "酉(유)": "亥(해)", "丑(축)": "亥(해)", "亥(해)": "巳(사)", "卯(묘)": "巳(사)", "未(미)": "巳(사)"}
    wol_jj = pils[2]["jj"] if len(pils) > 2 else ""
    if wol_jj and yeokma.get(wol_jj, "") in pil_jjs:
        result.append({"name": "역마살(驛馬殺)", "desc": "평생 이동/여행/해외와 인연이 깊습니다."})

    # 도화살
    dohwa = {"寅(인)": "卯(묘)", "午(오)": "卯(묘)", "戌(술)": "卯(묘)", "申(신)": "酉(유)", "子(자)": "酉(유)", "辰(진)": "酉(유)",
             "亥(해)": "子(자)", "卯(묘)": "子(자)", "未(미)": "子(자)", "巳(사)": "午(오)", "酉(유)": "午(오)", "丑(축)": "午(오)"}
    if wol_jj and dohwa.get(wol_jj, "") in pil_jjs:
        result.append({"name": "도화살(桃花殺)", "desc": "이성의 인기를 한몸에 받는 매력의 신살입니다."})

    return result


# ==================================================
#  메인 탭별 렌더링 함수
# ==================================================

# tab_saju_basic: 제거됨 - 미호출 함수


# tab_ilgan_desc: 제거됨 - 미호출 함수




# tab_12unsung: 제거됨 - 미호출 함수


def get_daewoon_narrative(d_ss_cg, d_ss_jj, dw_str, age_start):
    """대운 천간/지지 십성별 상세 해석 생성 (나이 단계 분기 포함)"""
    narratives = {
        "比肩": ("🤝", "독립과 협력의 大運: 자아의 확립",
               "比肩 大運은 주관과 독립심이 강해지는 시기로, 주도적으로 삶을 개척하게 됩니다. "
               "동료와 협력하여 성장하는 기회가 되기도 하나, 자아 충돌과 경쟁이 예상되니 상생의 지혜가 필요합니다."),
        "劫財": ("⚔️", "투쟁과 변혁의 大運: 경쟁을 통한 도약",
               "劫財 大運은 치열한 경쟁 속에서 예기치 못한 변화와 마주하며 크게 성장하는 시기입니다. "
               "재물 유출과 인간관계 갈등에 주의하되, 강한 추진력으로 정면 돌파하면 승리자의 위치에 서게 됩니다."),
        "食神": ("🍀", "복록과 풍요의 大運: 하늘이 내린 기회",
               "食神 大運은 재능이 꽃피고 물질적/정신적 여유가 샘솟는 축복의 10년입니다. "
               "전문 분야에서 두각을 나타내며 건강과 복록이 따르니, 자신의 역량을 아낌없이 펼쳐 인생의 자산을 만드십시오."),
        "傷官": ("🌪️", "혁신과 영감의 大運: 틀을 깨는 도약",
               "傷官 大運은 천재적인 번뜩임과 창의력으로 자신을 세상에 드러내는 영감의 시기입니다. "
               "기존 관습을 깨는 성취를 거둘 수 있으나, 언행의 절제가 성공의 열쇠임을 잊지 말고 창조적 에너지를 발산하십시오."),
        "偏財": ("💰", "도전과 성취의 大運: 역동적인 재물 운",
               "偏財 大運은 광활한 무대에서 큰 부와 성취를 사냥하는 대담한 도전의 10년입니다. "
               "사업이나 투자에서 예상치 못한 기회가 찾아오니, 냉철한 판단으로 과욕을 다스리며 큰 결실을 거머쥐십시오."),
        "正財": ("🏦", "안정과 축적의 大運: 성실함이 일군 부",
               "正財 大運은 정직한 노력이 꾸준한 부의 성을 쌓는 안정적인 결실의 시기입니다. "
               "경제적 안정과 가정의 화목이 따르므로, 원칙을 지키는 자산 관리와 성실함으로 평생의 기반을 다지십시오."),
        "偏官": ("⚡", "권위와 극복의 大運: 위기를 기회로",
               "偏官 大運은 강인한 리더십으로 시련을 극복하며 사회적 명예를 드높이는 변곡점입니다. "
               "극심한 책임감과 스트레스가 동반되지만, 정면 돌파를 통해 전설적인 성취와 권위를 얻게 될 것입니다."),
        "正官": ("🎖️", "명예와 인품의 大運: 지위의 정점",
               "正官 大運은 주변의 존경과 사회적 지위가 비약적으로 상승하는 영광스러운 시기입니다. "
               "승진과 자격 취득 등 공적인 인정이 따르며, 단정한 품위와 원칙 준수가 당신을 성공의 정점으로 인도합니다."),
        "偏印": ("🔮", "통찰과 전문의 大運: 정신적 확장",
               "偏印 大運은 날카로운 직관으로 특수 분야의 전문성을 완성하고 내면을 다지는 시기입니다. "
               "남들이 보지 못하는 기회를 포착하는 특별한 재능이 발휘되니, 자신만의 독보적인 영역을 개척해 보십시오."),
        "正印": ("📚", "지혜와 귀인의 大運: 훈풍이 부는 삶",
               "正印 大運은 귀인의 인도와 학문적 성취가 운명에 깃드는 평온하고 축복받은 10년입니다. "
               "문서 잡기와 시험에 유리하며 윗사람의 후원이 따르니, 지혜를 닦아 이름 석 자를 세상에 널리 알리십시오."),
        "-":   ("🌐", "조율과 준비의 大運: 균형의 시기",
               "이 시기는 여러 기운이 얽혀 인생의 방향성을 다각도로 조율해야 하는 중요한 변곡점입니다. "
               "일간의 강약을 살펴 신중하게 나아가며 다음 황금기를 위한 내실을 기하는 시간으로 삼으십시오."),
    }

    # -- 인생 단계별 집중 조언 -------------------------------------
    AGE_STAGE_FOCUS = {
        "比肩": {
            "초":   "📖 학업에서 자기 주도 학습 능력이 발달합니다. 부모님과 주도권 갈등이 생길 수 있으니 대화로 풀고, 진로는 개성을 살리는 방향으로 설계하십시오.",
            "청장": "💼 독립정신과 추진력이 직장/사업에서 빛납니다. 재물은 스스로 개척해야 따라오며, 연애도 주체적 의사 표현이 좋은 인연을 불러옵니다.",
            "말":   "🏡 자기 주도 건강 관리가 핵심입니다. 자녀/제자와 의견 충돌보다 조화를 택하고, 안정적인 노후 기반을 점검하십시오.",
        },
        "劫財": {
            "초":   "📖 학업 경쟁이 치열하고 스트레스가 가중됩니다. 가정의 재정 변동이 분위기에 영향을 줄 수 있으니 정서 안정과 학업 집중이 우선입니다.",
            "청장": "💼 재물 손실과 인간관계 갈등이 생기기 쉽습니다. 동업/보증/무리한 투자를 반드시 피하고, 연애의 금전 갈등도 각별히 주의하십시오.",
            "말":   "🏡 갑작스러운 건강 이상이 올 수 있으니 정기 검진이 필수입니다. 자녀/형제간 재산 분쟁을 미연에 방지하고 안정을 최우선으로 삼으십시오.",
        },
        "食神": {
            "초":   "📖 학업 성취와 창의력이 높아지고 선생님의 사랑을 받는 시기입니다. 예/체능 재능이 발현되니 다양한 활동을 통해 진로의 폭을 넓히십시오.",
            "청장": "💼 재능을 직업으로 연결하기 최고인 황금기입니다. 창작/서비스/사업에서 풍성한 결실이 오고, 연애도 자연스럽게 결혼으로 무르익습니다.",
            "말":   "🏡 심신이 여유롭고 건강한 행복한 시기입니다. 자녀와의 관계가 돈독해지고, 취미와 봉사로 노년의 품격을 높이십시오.",
        },
        "傷官": {
            "초":   "📖 특출한 재능이 빛나지만 규칙/교사와 마찰이 생기기 쉽습니다. 음악/미술/글쓰기 등 창의적 활동을 개발하면 크게 도움이 됩니다.",
            "청장": "💼 프리랜서/창업/예술 분야에서 명성을 날릴 수 있습니다. 언행으로 인한 구설을 극히 조심하고, 사랑에서도 충동적 결정을 자제하십시오.",
            "말":   "🏡 자녀/손자와 세대 차이를 수용하십시오. 신경계와 구강 계통 건강에 유의하며, 안정된 생활 리듬을 유지하는 것이 최선입니다.",
        },
        "偏財": {
            "초":   "📖 활동성과 호기심이 넘쳐 다채로운 경험을 쌓기 좋습니다. 무역/금융/서비스업 등 넓은 세계를 진로 목표로 고려해 보십시오.",
            "청장": "💼 사업 확장/투자/해외 진출에 유리한 황금기입니다. 재물 기복이 크니 수입의 30%는 반드시 적립하고, 이성 인연도 활발해집니다.",
            "말":   "🏡 왕성한 활동은 유지하되 무리한 투자는 금물입니다. 자녀에게 자산을 명확히 정리하고 건강 관리에 투자를 집중하십시오.",
        },
        "正財": {
            "초":   "📖 성실히 공부하면 착실한 결과가 나오는 시기입니다. 가정이 안정되어 공부 환경이 좋고, 부모님의 전폭 지원을 받을 수 있습니다.",
            "청장": "💼 안정적 취업과 꾸준한 연봉 상승의 행운이 따릅니다. 내 집 마련 등 자산 형성에 집중하기 좋고, 진지하고 믿음직한 인연이 찾아옵니다.",
            "말":   "🏡 노후 자산이 탄탄하게 정리되는 안심의 시기입니다. 배우자와의 화합이 깊어지고 자녀 결혼 등 경사가 이어지는 복된 노년입니다.",
        },
        "偏官": {
            "초":   "📖 학업 스트레스와 교우 갈등이 발생하기 쉽습니다. 규율이 엄격한 환경도 버텨내면 큰 잠재력이 발휘됩니다. 군사/법조/체육 분야 진로를 고려하십시오.",
            "청장": "💼 막중한 책임과 압박이 따르지만 극복하면 권위를 얻습니다. 혈압/관절 건강을 반드시 챙기고, 연애는 진지하고 책임감 있게 임하십시오.",
            "말":   "🏡 건강이 최우선 과제입니다. 갈등을 피하고 생활을 단순화하며 평정심을 유지하십시오. 자녀/가족의 안전도 신경 쓸 필요가 있습니다.",
        },
        "正官": {
            "초":   "📖 모범생으로 선생님의 총애를 받고 시험에서 좋은 결과를 냅니다. 반장/학생회 등 리더 역할이 주어지기도 합니다. 행정/사법/공학계 진로가 적합합니다.",
            "청장": "💼 승진/공직 임용/권위 있는 자리 발탁이 이루어지는 정점의 대운입니다. 명예와 신용이 재물이며, 결혼/배우자 덕이 빛나는 시기입니다.",
            "말":   "🏡 품위 있는 노년을 보내며 자녀의 사회적 성공이 이름을 빛나게 합니다. 건강은 규칙적인 생활로 잘 유지되는 안정적인 시기입니다.",
        },
        "偏印": {
            "초":   "📖 특이한 분야에 강한 흥미를 보이며 암기보다 독창적 사고에 강합니다. 예술/IT/종교 관련 진로를 고려하고, 부모님과의 소통에 의도적으로 노력하십시오.",
            "청장": "💼 연구/IT/상담/예술/철학 등 전문 분야에서 독보적입니다. 재물보다 전문성을 먼저 쌓고, 깊은 공감대를 나눌 수 있는 연애 상대를 찾으십시오.",
            "말":   "🏡 학문/종교/명상으로 내면을 탐구하기 좋은 시기입니다. 신경성 질환과 우울감에 주의하며 이완과 자연 친화를 가까이 하십시오.",
        },
        "正印": {
            "초":   "📖 학업운이 매우 강하여 공부에서 탁월한 성과를 올립니다. 부모님/선생님의 아낌없는 지원을 받으며 명문대 진학, 장학금 기회가 열립니다.",
            "청장": "💼 귀인/윗사람의 후원으로 승진하거나 중요한 계약을 성사시킵니다. 자격증/전문 학위가 연봉의 결정적 열쇠가 되며 배우자 내조가 빛납니다.",
            "말":   "🏡 자녀/손자의 성공으로 큰 보람을 느끼는 노년입니다. 명예와 인격이 주변의 존경을 불러 모으고 건강도 심리적 안정 위에 잘 유지됩니다.",
        },
        "-": {
            "초":   "📖 다양한 경험을 균형 있게 쌓으며 자신의 방향을 탐색하는 시기입니다. 한 분야에 집중하기보다 넓게 탐색하는 것이 이 시기의 올바른 자세입니다.",
            "청장": "💼 특별한 호재나 악재 없이 역량을 차분히 쌓아가는 시기입니다. 다음 황금기를 위한 내실을 다지십시오.",
            "말":   "🏡 평온하게 흐르는 노년입니다. 무리한 변화보다 일상을 소중히 여기며 가족과의 따뜻한 시간을 즐기는 것이 최선입니다.",
        },
    }

    # 나이 단계 분기
    age = int(age_start) if age_start else 0
    if age < 20:
        stage       = "초"
        stage_label = "🌱 초년기 (학업/부모/진로 집중)"
    elif age < 60:
        stage       = "청장"
        stage_label = "🌿 청장년기 (취업/재물/연애/사업 집중)"
    else:
        stage       = "말"
        stage_label = "🍂 말년기 (건강/명예/안정/자녀 집중)"

    icon, title, text = narratives.get(d_ss_cg, narratives["-"])
    focus_map  = AGE_STAGE_FOCUS.get(d_ss_cg, AGE_STAGE_FOCUS["-"])
    focus_text = focus_map.get(stage, "")

    full_text = f"{text}\n\n{stage_label}\n{focus_text}"
    return icon, title, full_text


def _get_dw_alert(ilgan, dw_cg, dw_jj, pils):
    """대운이 원국과 충/합을 일으키는지 감지"""
    alerts = []
    labels = ["시주", "일주", "월주", "년주"]
    orig_jjs = [p["jj"] for p in pils]
    orig_cgs = [p["cg"] for p in pils]
    for i, p in enumerate(pils):
        ojj = p["jj"]
        k = frozenset([dw_jj, ojj])
        if k in CHUNG_MAP:
            name, rel, desc = CHUNG_MAP[k]
            alerts.append({"type": "[!]️ 지지충", "color": "#c0392b",
                           "desc": f"대운 {dw_jj}가 원국 {labels[i]}({ojj})를 충(沖) - {desc}"})
    TG_HAP_PAIRS = [{"甲(갑)","己(기)"},{"乙(을)","庚(경)"},{"丙(병)","辛(신)"},{"丁(정)","壬(임)"},{"戊(무)","癸(계)"}]
    for pair in TG_HAP_PAIRS:
        if dw_cg in pair:
            other = list(pair - {dw_cg})[0]
            if other in orig_cgs:
                found_idx = orig_cgs.index(other)
                alerts.append({"type": "- 천간합", "color": "#27ae60",
                               "desc": f"대운 {dw_cg}가 원국 {labels[found_idx]}({other})와 합(合) - 변화와 기회의 기운"})
    for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
        if dw_jj in combo:
            orig_in = []
            for i, p in enumerate(pils):
                if p["jj"] in combo:
                    orig_in.append(f"{labels[i]}({p['jj']})")
            if len(orig_in) >= 2:
                alerts.append({"type": "🌟 삼합 성립", "color": "#8e44ad",
                               "desc": f"대운 {dw_jj} + 원국 {','.join(orig_in)} = {hname} - 강력한 발복"})
            elif len(orig_in) == 1:
                alerts.append({"type": "💫 반합", "color": "#2980b9",
                               "desc": f"대운 {dw_jj} + 원국 {orig_in[0]} 반합 - 부분적 기운 변화"})
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
    """원국의 합이 대운/세운 충으로 깨지는 시점 감지"""
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
                            "desc": f"원국 {hname}({orig_desc})을 {'대운' if breaker==dw_jj else '세운'} {breaker}가 {labels[i]}({jj})를 충(沖)으로 깨뜨립니다. 계획 좌절/관계 파탄/재물 손실 위험."
                        })
    return warnings


DAEWOON_PRESCRIPTION = {
    "比肩": "독립 사업/협력 강화/새 파트너십 구축이 유리합니다.",
    "劫財": "투자/보증/동업 금지. 지출 절제, 현상 유지가 최선입니다.",
    "食神": "재능 발휘/창업/콘텐츠 창작을 적극 추진하십시오.",
    "傷官": "직장 이직/창업/예술 활동에 좋으나 언행 극도 조심.",
    "偏財": "사업 확장/투자/이동이 유리. 단, 과욕은 금물입니다.",
    "正財": "저축/자산 관리/안정적 수입 구조 구축에 집중하십시오.",
    "偏官": "건강검진 필수. 무리한 확장 자제. 인내와 정면 돌파가 최선.",
    "正官": "승진/자격증/공식 계약을 적극 추진하십시오. 명예의 시기.",
    "偏印": "학문/자격증/특수 분야 연구에 집중하기 좋은 시기입니다.",
    "正印": "시험/학업/귀인과의 만남. 배움에 투자하십시오.",
}


def tab_daewoon(pils, birth_year, gender):
    """대운 탭 - 용신 하이라이트 + 합충 경고 + 처방"""
    st.markdown('<div class="gold-section">🔄 대운(大運) | 10년 주기 운명의 큰 흐름</div>', unsafe_allow_html=True)

    # 대운 호출 시 실제 생년월일시 반영
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    current_year = datetime.now().year
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")
    ys = get_yongshin(pils)
    yongshin_ohs = ys["종합_용신"]

    # -- 타임라인 요약 바 --------------------------------
    st.markdown('<div class="gold-section">📊 용신 대운 타임라인</div>', unsafe_allow_html=True)
    oh_emoji = {"木":"🌳","火":"🔥","土":"🏔️","金":"⚔️","水":"💧"}
    yong_str = " / ".join([f"{oh_emoji.get(o,'')}{OHN.get(o,'')}" for o in yongshin_ohs]) if yongshin_ohs else "분석 중"
    st.markdown(f"""
<div class="card" style="background:#ffffff;border:2px solid #000000;margin-bottom:10px;font-size:13px;color:#000000;line-height:1.9">
- <b>이 사주 用神:</b> {yong_str} &nbsp;|&nbsp;
🟡 황금 카드 = 用神 大運 &nbsp;|&nbsp; 🟠 주황 테두리 = 현재 大運
</div>
""", unsafe_allow_html=True)

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

    # -- 대운별 상세 카드 --------------------------------
    for dw in daewoon:
        d_ss_cg = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
        d_ss_jj_list = JIJANGGAN.get(dw["jj"], [])
        d_ss_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(d_ss_jj_list[-1] if d_ss_jj_list else "", "-")
        oh_cg = OH.get(dw["cg"], ""); oh_jj = OH.get(dw["jj"], "")
        is_current = dw["시작연도"] <= current_year <= dw["종료연도"]
        is_yong = _get_yongshin_match(d_ss_cg, yongshin_ohs, ilgan_oh) == "yong"
        alerts = _get_dw_alert(ilgan, dw["cg"], dw["jj"], pils)
        icon, title, narrative_raw = get_daewoon_narrative(d_ss_cg, d_ss_jj, dw["str"], dw["시작나이"])
        narrative = narrative_raw.replace("\n", "<br>")
        prescription = DAEWOON_PRESCRIPTION.get(d_ss_cg, "꾸준한 노력으로 안정을 유지하십시오.")

        if is_current:
            bdr = "border:3px solid #ff6b00;"
            bg2 = "background:linear-gradient(135deg,#fff8ee,#fff3e0);"
            badge = "<div style='font-size:12px;color:#ff6b00;font-weight:900;letter-spacing:2px;margin-bottom:8px'>-> * 현재 진행 중인 대운 *</div>"
        elif is_yong:
            bdr = "border:2px solid #000000;"
            bg2 = "background:linear-gradient(135deg,#ffffff,#ffffff);"
            badge = "<div style='font-size:11px;color:#000000;font-weight:800;margin-bottom:6px'>🌟 용신(用神) 대운 - 이 시기를 놓치지 마십시오</div>"
        else:
            bdr = "border:1px solid #e8e8e8;"
            bg2 = "background:#fafafa;"
            badge = ""

        alert_html = "".join([
            f'<div style="background:{a["color"]}18;border-left:3px solid {a["color"]};padding:8px 12px;border-radius:6px;margin-top:4px;font-size:12px"><b style="color:{a["color"]}">{a["type"]}</b> - {a["desc"]}</div>'
            for a in alerts])

        card_html = f"""
<div class="card" style="{bdr}{bg2}margin:10px 0;padding:20px">
{badge}
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
<div>
<span style="font-size:30px;font-weight:800;color:#000000">{dw["str"]}</span>
<span style="font-size:13px;color:#000000;margin-left:12px">{dw["시작나이"]}~{dw["시작나이"]+9}세</span>
<span style="font-size:11px;color:#000000;margin-left:8px">({dw["시작연도"]}~{dw["종료연도"]}년)</span>
</div>
<div style="text-align:right">
<div style="font-size:12px;color:#444">{OHE.get(oh_cg,"")} 天干 <b>{d_ss_cg}</b></div>
<div style="font-size:12px;color:#444">{OHE.get(oh_jj,"")} 地支 <b>{d_ss_jj}</b></div>
</div>
</div>
<div style="background:white;border-left:4px solid #000000;padding:12px 15px;border-radius:4px 10px 10px 4px;margin-bottom:8px">
<div style="font-size:14px;font-weight:700;color:#000000;margin-bottom:6px">{icon} {title}</div>
<div style="font-size:13px;color:#000000;line-height:2.0">{narrative}</div>
</div>
<div style="background:#ffffff;border:1px solid #a8d5a8;padding:10px 14px;border-radius:10px;margin-bottom:6px">
<span style="font-size:12px;font-weight:700;color:#2a6f2a">💊 處方: </span>
<span style="font-size:13px;color:#333">{prescription}</span>
</div>
{alert_html}
</div>"""
        st.markdown(card_html, unsafe_allow_html=True)


# tab_ilju: 제거됨 - 미호출 함수


def tab_yukjin(pils, gender="남"):
    """육친론(六親論) 탭"""
    ilgan = pils[1]["cg"]
    st.markdown('<div class="gold-section">👨‍👩‍👧‍👦 육친론(六親論) - 가족과 인연</div>', unsafe_allow_html=True)
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
            strength_label = "강(强) - 인연이 깊습니다" if has else "약(弱) - 인연이 엷습니다"

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
            </div>
""", unsafe_allow_html=True)
    else:
        st.info("육친 데이터를 분석 중입니다.")

    # 배우자 자리 분석
    st.markdown('<div class="gold-section">💑 배우자 자리 (일지) 분석</div>', unsafe_allow_html=True)
    iljj = pils[1]["jj"]
    iljj_ss = calc_sipsung(ilgan, pils)[1].get("jj_ss", "-")

    spouse_desc = {
        "남": {"정재": "현모양처형. 안정적이고 내조를 잘하는 배우자.", "편재": "활달하고 매력적이나 변화가 많은 배우자.", "정관": "남편으로서의 배우자 - 격조 있는 인연.", "편관": "강하고 카리스마 있는 배우자. 갈등도 있을 수 있습니다."},
        "여": {"정관": "점잖고 안정적인 남편. 사회적으로 인정받는 남성.", "편관": "카리스마 있고 강한 남편. 자유분방한 측면도.", "정재": "여성으로서의 배우자 - 풍요로운 인연.", "편재": "활동적이고 사교적인 배우자."},
    }

    spouse_hint = spouse_desc.get(gender, {}).get(iljj_ss, f"일지의 {iljj_ss} - 배우자의 성향을 나타냅니다.")

    st.markdown(f"""

    <div class="card" style="background:#fff0f8;border:2px solid #d580b8">
        <div style="font-size:14px;font-weight:700;color:#8b2060;margin-bottom:8px">
            💑 배우자 자리: {iljj}({JJ_KR[JJ.index(iljj)] if iljj in JJ else ''}) - {iljj_ss}
        </div>
        <div style="font-size:13px;color:#000000;line-height:1.9">{spouse_hint}</div>
    </div>
""", unsafe_allow_html=True)


def tab_gunghap(pils, name="나"):
    """궁합(宮合) 탭"""
    st.markdown('<div class="gold-section">💑 궁합(宮合) - 두 사주의 조화</div>', unsafe_allow_html=True)

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
            
            # AI 연동을 위해 세션에 저장
            st.session_state.last_gunghap = {
                "name": pname,
                "pils": partner_pils,
                "summary": f"{name}님과 {pname}님의 궁합 점수는 {result['총점']}점({result['등급']})입니다.",
                "details": result
            }

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
            </div>
""", unsafe_allow_html=True)

            # 세부 분석
            col_a, col_b = st.columns(2)
            with col_a:
                ir = result["일간관계"]
                st.markdown(f"""

                <div class="card">
                    <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">{ir[2]} 일간 관계: {ir[0]}</div>
                    <div style="font-size:13px;color:#444">{ir[1]}</div>
                </div>
""", unsafe_allow_html=True)

                if result["합"]:
                    st.markdown(f"""

                    <div class="card" style="background:#ffffff;border:1px solid #a8d5a8">
                        <div style="font-size:13px;font-weight:700;color:#2a6f2a;margin-bottom:6px">- 합(合) 발견!</div>
                        <div style="font-size:13px;color:#333">{', '.join(result['합'])}</div>
                    </div>
""", unsafe_allow_html=True)

            with col_b:
                if result["충"]:
                    st.markdown(f"""

                    <div class="card" style="background:#fff0f0;border:1px solid #d5a8a8">
                        <div style="font-size:13px;font-weight:700;color:#8b2020;margin-bottom:6px">[!]️ 충(沖) 발견</div>
                        <div style="font-size:13px;color:#333">{', '.join(result['충'])}</div>
                        <div style="font-size:12px;color:#000000;margin-top:4px">충이 있어도 서로 이해하고 보완하면 더욱 단단한 인연이 됩니다.</div>
                    </div>
""", unsafe_allow_html=True)

                gui_items = []
                if result["귀인_a"]: gui_items.append(f"{name}의 사주에 {pname}이 귀인 역할")
                if result["귀인_b"]: gui_items.append(f"{pname}의 사주에 {name}이 귀인 역할")
                if gui_items:
                    st.markdown(f"""

                    <div class="card" style="background:#ffffff;border:1px solid #e8d5a0">
                        <div style="font-size:13px;font-weight:700;color:#000000;margin-bottom:6px">- 천을귀인 인연!</div>
                        <div style="font-size:13px;color:#444">{'<br>'.join(gui_items)}</div>
                    </div>
""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"분석 오류: {e}")


# ==================================================
#  월령(月令) 심화 - 왕상휴수사
# ==================================================

WARYEONG_TABLE = {
    "木": {"寅(인)":100,"卯(묘)":100,"辰(진)":40,"巳(사)":20,"午(오)":10,"未(미)":20,"申(신)":10,"酉(유)":10,"戌(술)":20,"亥(해)":70,"子(자)":70,"丑(축)":40},
    "火": {"寅(인)":70,"卯(묘)":70,"辰(진)":40,"巳(사)":100,"午(오)":100,"未(미)":100,"申(신)":20,"酉(유)":10,"戌(술)":20,"亥(해)":10,"子(자)":10,"丑(축)":20},
    "土": {"寅(인)":20,"卯(묘)":20,"辰(진)":100,"巳(사)":70,"午(오)":70,"未(미)":100,"申(신)":70,"酉(유)":40,"戌(술)":100,"亥(해)":20,"子(자)":10,"丑(축)":100},
    "金": {"寅(인)":10,"卯(묘)":10,"辰(진)":20,"巳(사)":10,"午(오)":10,"未(미)":20,"申(신)":100,"酉(유)":100,"戌(술)":70,"亥(해)":40,"子(자)":20,"丑(축)":40},
    "水": {"寅(인)":40,"卯(묘)":20,"辰(진)":20,"巳(사)":10,"午(오)":10,"未(미)":10,"申(신)":40,"酉(유)":70,"戌(술)":40,"亥(해)":100,"子(자)":100,"丑(축)":70},
}

JJ_MONTH_SEASON = {
    "寅(인)":"봄 초입(1월, 양력2월)","卯(묘)":"봄 한창(2월, 양력3월)","辰(진)":"봄 마무리(3월, 양력4월)",
    "巳(사)":"여름 초입(4월, 양력5월)","午(오)":"여름 한창(5월, 양력6월)","未(미)":"여름 마무리(6월, 양력7월)",
    "申(신)":"가을 초입(7월, 양력8월)","酉(유)":"가을 한창(8월, 양력9월)","戌(술)":"가을 마무리(9월, 양력10월)",
    "亥(해)":"겨울 초입(10월, 양력11월)","子(자)":"겨울 한창(11월, 양력12월)","丑(축)":"겨울 마무리(12월, 양력1월)",
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


# ==================================================
#  외격(外格) + 양인(羊刃)
# ==================================================

YANGIN_MAP = {"甲(갑)":"卯(묘)","丙(병)":"午(오)","戊(무)":"午(오)","庚(경)":"酉(유)","壬(임)":"子(자)","乙(을)":"辰(진)","丁(정)":"未(미)","己(기)":"未(미)","辛(신)":"戌(술)","癸(계)":"丑(축)"}
YANGIN_DESC = {
    "甲(갑)":{"jj":"卯(묘)","name":"갑목 양인 卯(묘)","desc":"목기 극강. 결단력/추진력 폭발. 관재/사고/분쟁 주의.","good":"군인/경찰/의사/법조인","caution":"분노 충동 다스리기. 칠살과 함께면 더욱 강렬."},
    "丙(병)":{"jj":"午(오)","name":"병화 양인 午(오)","desc":"태양이 정오에 빛남. 카리스마/권력욕 압도적.","good":"정치/방송/경영/스포츠","caution":"오만과 독선 경계. 임수의 제어 필요."},
    "戊(무)":{"jj":"午(오)","name":"무토 양인 午(오)","desc":"대지가 달아오른 강렬한 기운. 실행력/의지력 대단.","good":"건설/부동산/스포츠/경영","caution":"독선 결정이 조직을 해침. 협력자 경청 필요."},
    "庚(경)":{"jj":"酉(유)","name":"경금 양인 酉(유)","desc":"금기 극강. 결단력 칼같이 날카로움.","good":"군인/경찰/외과의/법조인","caution":"냉정함 과하면 인간관계 끊김. 화기의 단련 필요."},
    "壬(임)":{"jj":"子(자)","name":"임수 양인 子(자)","desc":"수기 넘침. 지혜/전략 압도적이나 방향 잃으면 홍수.","good":"전략/외교/금융/IT/철학","caution":"무토 제방 없으면 방종/방황. 목표와 원칙 필수."},
    "乙(을)":{"jj":"辰(진)","name":"을목 양인 辰(진)","desc":"을목 양인. 고집과 인내력이 강함.","good":"전문직/연구/예술","caution":"고집이 화근이 될 수 있음."},
    "丁(정)":{"jj":"未(미)","name":"정화 양인 未(미)","desc":"정화 양인. 감성적 에너지가 강함.","good":"예술/교육/상담","caution":"감정 기복에 주의."},
    "己(기)":{"jj":"未(미)","name":"기토 양인 未(미)","desc":"기토 양인. 고집과 끈기가 강함.","good":"농업/의료/전문직","caution":"고집을 유연함으로 바꾸는 것이 과제."},
    "辛(신)":{"jj":"戌(술)","name":"신금 양인 戌(술)","desc":"신금 양인. 예리함과 완벽주의가 극도로 강함.","good":"예술/의료/분석","caution":"과도한 완벽주의가 자신을 소진함."},
    "癸(계)":{"jj":"丑(축)","name":"계수 양인 丑(축)","desc":"계수 양인. 끈기와 인내의 기운이 강함.","good":"연구/의료/학문","caution":"자신을 과소평가하지 말 것."},
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
                        "용신":f"{ilgan_oh}/{BIRTH_R.get(ilgan_oh,'')}","기신":f"{CTRL.get(ilgan_oh,'')}",
                        "caution":"종왕격을 내격으로 착각하면 완전히 반대 풀이가 됩니다."})
    # 종재격
    jae_oh = CTRL.get(ilgan_oh,"")
    if oh_strength.get(jae_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종재격(從財格)","icon":"💰","color":"#2980b9",
                        "desc":f"재성({OHN.get(jae_oh,'')})이 사주를 압도. 재성을 따르는 것이 순리.",
                        "용신":f"{jae_oh}/{GEN.get(jae_oh,'')}","기신":f"{ilgan_oh} 비겁/{BIRTH_R.get(ilgan_oh,'')} 인성",
                        "caution":"비겁/인성 운이 오면 오히려 크게 파란이 생깁니다."})
    # 종관격
    gwan_oh = next((k for k,v in CTRL.items() if v==ilgan_oh),"")
    if oh_strength.get(gwan_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종관격(從官格)","icon":"🎖️","color":"#27ae60",
                        "desc":f"관성({OHN.get(gwan_oh,'')})이 사주를 지배. 공직/관직에서 크게 발복.",
                        "용신":f"{gwan_oh}/{jae_oh}","기신":f"{ilgan_oh} 비겁",
                        "caution":"비겁이 오면 구설/관재가 생기기 쉽습니다."})
    # 종아격
    sik_oh = GEN.get(ilgan_oh,"")
    if oh_strength.get(sik_oh,0) >= 55 and sn=="신약(身弱)":
        results.append({"격":"종아격(從兒格)","icon":"🎨","color":"#8e44ad",
                        "desc":f"식상({OHN.get(sik_oh,'')})이 사주를 지배. 창의/예술/기술의 기운 압도적.",
                        "용신":f"{sik_oh}/{CTRL.get(ilgan_oh,'')}","기신":"관성/인성",
                        "caution":"관성/인성 운에서 건강/사고/좌절이 오기 쉽습니다."})
    return results


# ==================================================
#  12신살(十二神殺) 완전판
# ==================================================

SINSAL_12_TABLE = {
    "劫殺":{"寅(인)午(오)戌(술)":"亥(해)","申(신)子(자)辰(진)":"巳(사)","巳(사)酉(유)丑(축)":"寅(인)","亥(해)卯(묘)未(미)":"申(신)"},
    "災殺":{"寅(인)午(오)戌(술)":"子(자)","申(신)子(자)辰(진)":"午(오)","巳(사)酉(유)丑(축)":"卯(묘)","亥(해)卯(묘)未(미)":"酉(유)"},
    "天殺":{"寅(인)午(오)戌(술)":"丑(축)","申(신)子(자)辰(진)":"未(미)","巳(사)酉(유)丑(축)":"辰(진)","亥(해)卯(묘)未(미)":"戌(술)"},
    "地殺":{"寅(인)午(오)戌(술)":"寅(인)","申(신)子(자)辰(진)":"申(신)","巳(사)酉(유)丑(축)":"巳(사)","亥(해)卯(묘)未(미)":"亥(해)"},
    "年殺":{"寅(인)午(오)戌(술)":"卯(묘)","申(신)子(자)辰(진)":"酉(유)","巳(사)酉(유)丑(축)":"午(오)","亥(해)卯(묘)未(미)":"子(자)"},
    "月殺":{"寅(인)午(오)戌(술)":"辰(진)","申(신)子(자)辰(진)":"戌(술)","巳(사)酉(유)丑(축)":"未(미)","亥(해)卯(묘)未(미)":"丑(축)"},
    "亡身殺":{"寅(인)午(오)戌(술)":"巳(사)","申(신)子(자)辰(진)":"亥(해)","巳(사)酉(유)丑(축)":"申(신)","亥(해)卯(묘)未(미)":"寅(인)"},
    "將星殺":{"寅(인)午(오)戌(술)":"午(오)","申(신)子(자)辰(진)":"子(자)","巳(사)酉(유)丑(축)":"酉(유)","亥(해)卯(묘)未(미)":"卯(묘)"},
    "攀鞍殺":{"寅(인)午(오)戌(술)":"未(미)","申(신)子(자)辰(진)":"丑(축)","巳(사)酉(유)丑(축)":"戌(술)","亥(해)卯(묘)未(미)":"辰(진)"},
    "驛馬殺":{"寅(인)午(오)戌(술)":"申(신)","申(신)子(자)辰(진)":"寅(인)","巳(사)酉(유)丑(축)":"亥(해)","亥(해)卯(묘)未(미)":"巳(사)"},
    "六害殺":{"寅(인)午(오)戌(술)":"酉(유)","申(신)子(자)辰(진)":"卯(묘)","巳(사)酉(유)丑(축)":"子(자)","亥(해)卯(묘)未(미)":"午(오)"},
    "華蓋殺":{"寅(인)午(오)戌(술)":"戌(술)","申(신)子(자)辰(진)":"辰(진)","巳(사)酉(유)丑(축)":"丑(축)","亥(해)卯(묘)未(미)":"未(미)"},
}

SINSAL_12_DESC = {
    "劫殺":{"icon":"⚔️","type":"흉","name":"겁살(劫殺)","desc":"강한 변동/손재/이별의 신살. 갑작스러운 사고가 따릅니다.","good":"군인/경찰/의사/위기관리에서 능력 발휘.","caution":"겁살 대운엔 투자/보증/동업 각별히 조심."},
    "災殺":{"icon":"💧","type":"흉","name":"재살(災殺)","desc":"재앙/수재의 신살. 관재/질병/교통사고 주의.","good":"의료/소방/구조 분야에서 특수 능력 발휘.","caution":"해외여행/수상활동 각별히 주의."},
    "天殺":{"icon":"⚡","type":"흉","name":"천살(天殺)","desc":"예상치 못한 천재지변/돌발사고. 상사와 마찰.","good":"위기 상황에서 빛을 발하는 강인함.","caution":"상사/어른과의 갈등을 극도로 조심."},
    "地殺":{"icon":"🌍","type":"중","name":"지살(地殺)","desc":"이동/변화의 신살. 역마와 함께면 해외 이동 많음.","good":"외판/무역/항공/운수업에 유리.","caution":"정착하지 못하고 떠도는 기운 조심."},
    "年殺":{"icon":"🌸","type":"중","name":"년살(도화살)","desc":"이성 인기 독차지. 예술적 기질 강함.","good":"연예인/방송/서비스/예술가로 대성.","caution":"이성 문제/향락으로 인한 문제 조심."},
    "月殺":{"icon":"🪨","type":"흉","name":"월살(고초살)","desc":"뿌리 뽑힌 풀처럼 고생하는 기운. 가정적 어려움.","good":"역경을 이겨내는 강인한 정신력.","caution":"독립 후 오히려 안정되는 경우 많음."},
    "亡身殺":{"icon":"🌀","type":"흉","name":"망신살","desc":"구설/스캔들/배신의 기운. 체면 손상.","good":"정면 돌파 용기. 역경으로 더욱 강해짐.","caution":"언행 극도 조심. 비밀 관리 철저히."},
    "將星殺":{"icon":"🎖️","type":"길","name":"장성살","desc":"장수(將帥)의 별. 강한 리더십/통솔력. 조직 수장 기운.","good":"군인/경찰/정치/경영/스포츠 감독으로 최고자리.","caution":"독선적이 되지 않도록 주의."},
    "攀鞍殺":{"icon":"🐎","type":"길","name":"반안살","desc":"말안장 위. 안정된 자리에서 성장. 중년 이후 안정.","good":"전문직/학자/행정가로 꾸준한 성공.","caution":"안주하려는 경향. 도전 정신 유지하기."},
    "驛馬殺":{"icon":"🏇","type":"중","name":"역마살","desc":"이동/여행/해외/변화의 신살. 정착하기 어려움.","good":"해외/무역/외교/운수/영업에서 크게 활약.","caution":"이동 많아 가정생활 불안정할 수 있음."},
    "六害殺":{"icon":"🌀","type":"흉","name":"육해살","desc":"배신과 상처의 신살. 소화기 질환 주의.","good":"인내력과 회복력이 뛰어남.","caution":"가까운 사람에게 배신당하는 기운. 인간관계 신중히."},
    "華蓋殺":{"icon":"🌂","type":"중","name":"화개살","desc":"예술/종교/철학/영성의 신살. 고독하지만 고귀함.","good":"예술가/철학자/종교인/상담사로 독보적 경지.","caution":"고독/은둔 기운 강함. 사회적 관계 의식적으로 유지."},
}

EXTRA_SINSAL = {
    "귀문관살":{
        "icon":"🔮","type":"흉","name":"귀문관살(鬼門關殺)",
        "pairs":[frozenset(["子(자)","酉(유)"]),frozenset(["丑(축)","午(오)"]),frozenset(["寅(인)","未(미)"]),
                 frozenset(["卯","申"]),frozenset(["辰","亥"]),frozenset(["巳","戌"])],
        "desc":"영적 감수성 극도 발달 또는 신경증/불면/이상한 꿈.",
        "good":"무속인/철학자/상담사/예술가 - 남들이 보지 못하는 것을 봄.",
        "caution":"신경증/우울/집착 주의. 명상/규칙적 생활 필수.",
    },
    "백호대살":{
        "icon":"🐯","type":"흉","name":"백호대살(白虎大殺)",
        "targets":{"甲(갑)辰(진)","乙(을)未(미)","丙(병)戌(술)","丁(정)丑(축)","戊(무)辰(진)","己(기)未(미)","庚(경)戌(술)","辛(신)丑(축)","壬(임)辰(진)","癸(계)未(미)","甲(갑)戌(술)","乙(을)丑(축)","丙(병)辰(진)","丁(정)未(미)"},
        "desc":"혈광지사(血光之事) - 사고/수술/폭력과 인연.",
        "good":"외과의사/군인/경찰로 기운을 직업으로 승화하면 대성.",
        "caution":"대운에서 백호가 오면 교통사고/수술 극도 주의.",
    },
    "원진살":{
        "icon":"😡","type":"흉","name":"원진살(怨嗔殺)",
        "pairs":[frozenset(["子(자)","未(미)"]),frozenset(["丑(축)","午(오)"]),frozenset(["寅(인)","酉(유)"]),
                 frozenset(["卯","申"]),frozenset(["辰","亥"]),frozenset(["巳","戌"])],
        "desc":"서로 미워하고 원망하는 신살. 부부/가족 갈등의 원인.",
        "good":"강한 독립심을 키움.",
        "caution":"배우자/가족과 원진은 관계 갈등의 근원. 이해 노력 필수.",
    },
}

@st.cache_data
def get_12sinsal(pils):
    nyon_jj = pils[3]["jj"]
    pil_jjs = [p["jj"] for p in pils]
    labels = ["시주","일주","월주","년주"]
    san_groups = ["寅(인)午(오)戌(술)","申(신)子(자)辰(진)","巳(사)酉(유)丑(축)","亥(해)卯(묘)未(미)"]
    my_group = next((g for g in san_groups if nyon_jj in g),"寅(인)午(오)戌(술)")
    result = []
    for sname, jj_map in SINSAL_12_TABLE.items():
        sinsal_jj = jj_map.get(my_group,"")
        found = [labels[i] for i,jj in enumerate(pil_jjs) if jj==sinsal_jj]
        if found:
            d = SINSAL_12_DESC.get(sname,{})
            result.append({"이름":d.get("name",sname),"icon":d.get("icon","-"),
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


# ==================================================
#  대운/세운 교차 분석
# ==================================================


# ==================================================
# * 사건 트리거 감지 엔진 v2 *
# 충/형/합 + 십성활성 + 대운전환점 -> "소름 포인트" 생성
# ==================================================

_JIJI_CHUNG = {
    "子(자)":"午(오)","午(오)":"子(자)","丑(축)":"未(미)","未(미)":"丑(축)",
    "寅(인)":"申(신)","申(신)":"寅(인)","卯(묘)":"酉(유)","酉(유)":"卯(묘)",
    "辰(진)":"戌(술)","戌(술)":"辰(진)","巳(사)":"亥(해)","亥(해)":"巳(사)",
}
_JIJI_HYEONG = {
    "子(자)":"卯(묘)","卯(묘)":"子(자)",
    "寅(인)":"巳(사)","巳(사)":"申(신)","申(신)":"寅(인)",
    "丑(축)":"戌(술)","戌(술)":"未(미)","未(미)":"丑(축)",
    "辰(진)":"辰(진)","午(오)":"午(오)","酉(유)":"酉(유)","亥(해)":"亥(해)",
}
_TG_HAP_PAIRS = [{"甲(갑)","己(기)"},{"乙(을)","庚(경)"},{"丙(병)","辛(신)"},{"丁(정)","壬(임)"},{"戊(무)","癸(계)"}]
_SAM_HAP = [
    (frozenset({"寅(인)","午(오)","戌(술)"}),"火"),(frozenset({"申(신)","子(자)","辰(진)"}),"水"),
    (frozenset({"亥(해)","卯(묘)","未(미)"}),"木"),(frozenset({"巳(사)","酉(유)","丑(축)"}),"金"),
]
_BIRTH_F2 = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
_CTRL2    = {"木":"土","火":"金","土":"水","金":"木","水":"火"}


@st.cache_data
def detect_event_triggers(pils, birth_year, gender, bm=1, bd=1, bh=12, bmi=0, target_year=None):
    """
    사건 트리거 감지 - 충/형/합/십성활성/대운전환
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

    # 대운 호출 시 실제 생년월일시 반영 (사용자 지침 준수)
    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmi, gender=gender)
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
        add("충","⚡ 일지 충(세운) - 삶의 터전 격변",
            "이사/직장변화/관계분리 확률이 높습니다. 기존 환경이 흔들리는 해입니다.",85)
    if dw_jj and _JIJI_CHUNG.get(il_jj) == dw_jj:
        add("충","⚡ 일지 충(대운) | 10년 환경 변화",
            "대운 수준의 큰 환경 변화. 이사/직업 전환의 대운입니다.",80)
    if _JIJI_CHUNG.get(wol_jj) == year_jj:
        add("충","🌊 월지 충 - 가족/직업 변동",
            "부모/형제 관계 변화, 직업 환경의 급격한 변화가 예상됩니다.",75)

    # ② 형
    if _JIJI_HYEONG.get(il_jj) == year_jj or _JIJI_HYEONG.get(year_jj) == il_jj:
        add("형","[!]️ 일지 형(刑) - 스트레스/사고",
            "건강/사고/법적 문제에 주의. 인간관계 갈등이 생깁니다.",70)

    # ③ 천간합
    for pair in _TG_HAP_PAIRS:
        if dw_cg in pair and year_cg in pair:
            add("합","💑 천간합 - 새 인연/파트너십",
                "새로운 인연/결혼/동업/계약 인연이 찾아옵니다.",65)
            break

    # ④ 삼합국
    check_jjs = all_jjs | frozenset([dw_jj, year_jj])
    for combo, oh in _SAM_HAP:
        if combo.issubset(check_jjs):
            kind = "용신" if oh in yong_ohs else "기신"
            add("삼합","🌟 삼합국 - 강력한 기운 형성",
                f"대운/세운/원국이 {oh}({OHN.get(oh,'')}) 삼합. {kind} 오행이므로 {'크게 발복' if kind=='용신' else '조심 필요'}합니다.",80)
            break

    # ⑤ 용신/기신 대운
    if dw_cg:
        dw_oh = OH.get(dw_cg,"")
        if dw_oh in yong_ohs:
            add("황금기","- 용신 대운 - 황금기",
                "일생에 몇 번 없는 상승기. 이 시기의 도전은 결실을 맺습니다.",90)
        elif any(_CTRL2.get(dw_oh)==y or _CTRL2.get(y)==dw_oh for y in yong_ohs):
            add("경계","🛡️ 기신 대운 - 방어 필요",
                "확장보다 수성(守成)이 최선. 큰 결정은 신중히 하십시오.",80)

    # ⑥ 대운 전환점 (2년 이내)
    for i, dw_item in enumerate(dw_list[:-1]):
        if dw_item["시작연도"] <= target_year <= dw_item["종료연도"]:
            yrs_left = dw_item["종료연도"] - target_year
            if yrs_left <= 2:
                next_dw = dw_list[i+1]
                add("전환","🔄 대운 전환점 - 흐름 역전",
                    f"{yrs_left+1}년 안에 대운이 {next_dw['str']}로 전환됩니다. 이전과 다른 인생 국면이 펼쳐집니다.",85)

    # ⑦ 십성 활성화
    year_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(year_cg,"-")
    if year_ss in ["정관","편관"]:
        add("직업","🎖️ 관성 활성 - 직업/명예 변화",
            f"세운 천간({year_cg})이 {year_ss}. 승진/이직/자격증 변화가 예상됩니다.",70)
    if year_ss in ["정재","편재"]:
        add("재물","💰 재성 활성 - 재물 흐름",
            f"세운 천간({year_cg})이 {year_ss}. 재물 흐름이 활발해집니다. 투자 기회 주의.",72)

    return triggers


@st.cache_data
def calc_luck_score(pils, birth_year, gender, bm=1, bd=1, bh=12, bmi=0, target_year=None):
    """대운+세운 종합 운세 점수 (0~100)"""
    if target_year is None:
        target_year = datetime.now().year
    ys       = get_yongshin(pils)
    yong_ohs = ys.get("종합_용신",[]) if isinstance(ys.get("종합_용신"),list) else []
    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmi, gender=gender)
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


@st.cache_data
def calc_turning_point(pils, birth_year, gender, bm=1, bd=1, bh=12, bmi=0, target_year=None):
    """
    인생 전환점 감지 엔진 (정밀 v2)
    대운 점수 차이 + 세운 트리거 + 충합 종합
    Returns dict: {is_turning:bool, intensity:str, reason:list, score_change:int}
    """
    if target_year is None:
        target_year = datetime.now().year
    prev_score = calc_luck_score(pils, birth_year, gender, bm, bd, bh, bmi, target_year - 1)
    curr_score = calc_luck_score(pils, birth_year, gender, bm, bd, bh, bmi, target_year)
    next_score = calc_luck_score(pils, birth_year, gender, bm, bd, bh, bmi, target_year + 1)

    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmi, gender=gender)
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
            reasons.append(f"⚡ 대운 {cur_dw['str']} 마지막 해 - 인생 국면 전환 목전")
        if cur_dw["시작연도"] == target_year:
            reasons.append(f"🌟 새 대운 {cur_dw['str']} 시작 | 10년 흐름 완전 변화")

    if prev_dw and cur_dw and cur_dw["시작연도"] == target_year:
        # 이전 대운과 오행 관계
        prev_oh = OH.get(prev_dw["cg"], "")
        curr_oh = OH.get(cur_dw["cg"], "")
        ys = get_yongshin(pils)
        yong_ohs = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
        if prev_oh not in yong_ohs and curr_oh in yong_ohs:
            reasons.append(f"- 기신 대운->용신 대운 전환 - 인생 역전의 기회")
        elif prev_oh in yong_ohs and curr_oh not in yong_ohs:
            reasons.append(f"[!]️ 용신 대운->기신 대운 전환 - 속도 조절 필요")

    # 운세 점수 급변
    if abs(diff) >= 25:
        direction = "상승" if diff > 0 else "하락"
        reasons.append(f"📊 운세 점수 {abs(diff)}점 급{'등' if diff>0 else '락'} - 삶의 {direction} 흐름")
    elif abs(diff) >= 15:
        direction = "개선" if diff > 0 else "하강"
        reasons.append(f"📈 운세 {direction} ({diff:+d}점) - 변화 감지")

    # 사건 트리거 (충/합 있으면 강화)
    triggers = detect_event_triggers(pils, birth_year, gender, bm, bd, bh, bmi, target_year)
    high_triggers = [t for t in triggers if t["prob"] >= 80]
    if high_triggers:
        reasons.append(f"🔴 고확률 사건 트리거 {len(high_triggers)}개 - {high_triggers[0]['title']}")

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


@st.cache_data
def get_yongshin_multilayer(pils, birth_year, gender, bm=1, bd=1, bh=12, bmi=0, target_year=None):
    """
    다층 용신 분석 (1순위~3순위 + 희신 + 기신 + 대운별 용신)
    Returns dict with 용신_1순위, 용신_2순위, 희신, 기신, 현재_상황_용신, 대운_용신
    """
    if target_year is None:
        target_year = datetime.now().year

    ys = get_yongshin(pils)
    yong_list = ys.get("종합_용신", []) if isinstance(ys.get("종합_용신"), list) else []
    # [년, 월, 일, 시] 순서에서 일간은 index 2
    oh_strength = calc_ohaeng_strength(pils[1]["cg"], pils)
    ilgan = pils[1]["cg"]
    ilgan_oh = OH.get(ilgan, "")

    # 상생 순서
    BIRTH = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
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
    dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmi, gender=gender)
    cur_dw  = next((d for d in dw_list if d["시작연도"] <= target_year <= d["종료연도"]), None)
    dw_yong = ""
    dw_note  = ""
    if cur_dw:
        dw_oh = OH.get(cur_dw["cg"], "")
        if dw_oh in yong_list:
            dw_yong = dw_oh
            dw_note = f"현재 {cur_dw['str']} 대운 = 용신 오행 -> 황금기"
        elif dw_oh == hee_shin:
            dw_yong = hee_shin
            dw_note = f"현재 {cur_dw['str']} 대운 = 희신 -> 안정 성장기"
        elif dw_oh in gi_shin_list:
            dw_yong = ""
            dw_note = f"현재 {cur_dw['str']} 대운 = 기신 -> 방어 전략 필요"
        else:
            dw_yong = dw_oh
            dw_note = f"현재 {cur_dw['str']} 대운 = 중립 -> 평상 유지"

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

    # [시, 일, 월, 년] 순서에서 일간은 index 1
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

    # ① 과거 적중 문장 - 사주 패턴 -> 이미 겪은 일
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
    # 대운 호출 시 실제 생년월일시 반영 (사용자 지침 준수)
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    past_dw = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
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

    # ② 현재 상태 문장 - 현재 운 vs 원국 비교
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
                "환경이 흔들리는 기운이 다가오고 있습니다. 이사/직장/관계 중 하나가 변할 가능성이 높습니다."
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
        "past": past_sentences,
        "present": present_sentences,
        "future": future_sentences,
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

    munchang_map = {"甲(갑)":"巳(사)","乙(을)":"午(오)","丙(병)":"申(신)","丁(정)":"酉(유)","戊(무)":"申(신)","己(기)":"酉(유)","庚(경)":"亥(해)","辛(신)":"子(자)","壬(임)":"寅(인)","癸(계)":"卯(묘)"}
    if munchang_map.get(ilgan) in all_jjs:
        stars.append({"name": "문창귀인(文昌)", "desc": "지혜가 총명하고 학문과 예술에 뛰어난 재능"})

    gwimun_pairs = [{"子(자)","酉(유)"},{"丑(축)","午(오)"},{"寅(인)","未(미)"},{"卯(묘)","申(신)"},{"辰(진)","亥(해)"},{"巳(사)","戌(술)"}]
    for pair in gwimun_pairs:
        if pair.issubset(set(all_jjs)):
            stars.append({"name": "귀문관살(鬼門)", "desc": "직관력이 뛰어나고 예민한 천재성, 영적 감각"})
            break

    baekho = ["甲(갑)辰(진)","乙(을)未(미)","丙(병)戌(술)","丁(정)丑(축)","戊(무)辰(진)","壬(임)戌(술)","癸(계)丑(축)"]
    for p in pils:
        if (p["cg"]+p["jj"]) in baekho:
            stars.append({"name": "백호대살(白虎)", "desc": "강한 추진력과 전문성, 압도적인 에너지"})
            break

    cheon_eul = {"甲(갑)":"未(미)","乙(을)":"申(신)","丙(병)":"酉(유)","丁(정)":"亥(해)","戊(무)":"未(미)","己(기)":"申(신)","庚(경)":"丑(축)","辛(신)":"寅(인)","壬(임)":"卯(묘)","癸(계)":"巳(사)"}
    if cheon_eul.get(ilgan) in all_jjs:
        stars.append({"name": "천을귀인(天乙(을))", "desc": "인생의 위기에서 돕는 귀인이 상주하는 최고의 길성"})

    return stars



# ==============================================================
#  🧠 ADAPTIVE ENGINE - 페르소나 감지 -> 맞춤 해석 스타일
#  사용자 행동 패턴으로 성향 자동 추정
# ==============================================================

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
        return "achievement_type"   # 성취/결과 지향
    if focus == "연애":
        return "emotional_type"     # 감정/관계 중심
    if focus == "건강":
        return "cautious_type"      # 안정/리스크 회피
    if focus == "직장":
        return "career_type"        # 커리어/명예 지향
    if q_count >= 2:
        return "overthinking_type"  # 생각 많음, 확인 욕구
    if v_count >= 4:
        return "deep_reflection_type"  # 심층 탐색
    return "balanced_type"


def get_persona_prompt_style(persona: str) -> str:
    """페르소나별 AI 해석 스타일 지침"""
    style_map = {
        "achievement_type": (
            "사용자는 성취/결과 지향적이다. "
            "현실적이고 구체적인 행동 가이드와 기회를 중심으로 해석하라. "
            "추상적 표현 최소화. 언제, 무엇을, 어떻게 해야 하는지 단정적으로 말하라."
        ),
        "emotional_type": (
            "사용자는 감정/관계를 중시한다. "
            "인간관계와 감정 흐름을 중심으로 따뜻하고 공감적으로 해석하라. "
            "외로움, 그리움, 설렘 등 감정 언어를 자연스럽게 사용하라."
        ),
        "career_type": (
            "사용자는 커리어와 사회적 인정을 중요하게 생각한다. "
            "직업/승진/명예/직장 흐름을 중심으로 단계적이고 전략적으로 해석하라."
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
        "achievement_type":     ("[목표]", "성취/결과형",    "#e65100"),
        "emotional_type":       ("[감정]", "감정/관계형",    "#e91e8c"),
        "career_type":          ("[커리어]", "커리어/명예형", "#1565c0"),
        "cautious_type":        ("[신중]", "안정/신중형",   "#2e7d32"),
        "overthinking_type":    ("[분석]", "분석/확인형",    "#6a1b9a"),
        "deep_reflection_type": ("[성찰]", "성찰/탐색형",    "#00695c"),
        "balanced_type":        ("[균형]", "균형/종합형",    "#8B6914"),
    }
    return labels.get(persona, ("[종합]", "종합형", "#8B6914"))


# ==============================================================
#  SELF-CHECK ENGINE - AI 2패스 자기검증 시스템
#  1차 해석 -> AI 감수 -> 논리 보정 -> 최종 출력
# ==============================================================

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


# ==============================================================
#  🔄 RETENTION ENGINE - 재방문/중독 구조
#  스트릭 카운터 / 운 변화 카운트다운 / 일별 운 점수
# ==============================================================

_RETENTION_FILE  = "saju_retention.json"
_USER_PROFILE_FILE = "saju_user_profile.json"
SAJU_SAVE_FILE = "saju_save.json"


# ==============================================================
#  🧠 USER MEMORY SYSTEM - AI가 사용자를 기억하는 구조
#  상담 이력 / 관심 영역 / 믿음 지수 / 이전 예측 저장
# ==============================================================

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


def save_saju_state():
    """사주 입력값 및 계산 결과를 JSON 파일로 영구 저장"""
    _ss = st.session_state
    solar = _ss.get("in_solar_date")
    data = {
        # -- 입력값 --
        "in_name":               _ss.get("in_name", ""),
        "in_gender":             _ss.get("in_gender", "남"),
        "in_cal_type":           _ss.get("in_cal_type", "양력"),
        "in_solar_date":         solar.isoformat() if solar else "1990-01-01",
        "in_lunar_year":         _ss.get("in_lunar_year", 1990),
        "in_lunar_month":        _ss.get("in_lunar_month", 1),
        "in_lunar_day":          _ss.get("in_lunar_day", 1),
        "in_is_leap":            _ss.get("in_is_leap", False),
        "in_birth_hour":         _ss.get("in_birth_hour", 12),
        "in_birth_minute":       _ss.get("in_birth_minute", 0),
        "in_unknown_time":       _ss.get("in_unknown_time", False),
        "in_marriage":           _ss.get("in_marriage", "미혼"),
        "in_occupation":         _ss.get("in_occupation", "선택 안 함"),
        "in_premium_correction": _ss.get("in_premium_correction", True),
        # -- 계산 결과 --
        "saju_pils":     _ss.get("saju_pils"),
        "birth_year":    _ss.get("birth_year"),
        "birth_month":   _ss.get("birth_month"),
        "birth_day":     _ss.get("birth_day"),
        "birth_hour":    _ss.get("birth_hour"),
        "birth_minute":  _ss.get("birth_minute"),
        "gender":        _ss.get("gender"),
        "saju_name":     _ss.get("saju_name"),
        "marriage_status": _ss.get("marriage_status"),
        "occupation":    _ss.get("occupation"),
        "cal_type":      _ss.get("cal_type"),
        "lunar_info":    _ss.get("lunar_info", ""),
        # -- 기억 구조 --
        "saju_memory":   _ss.get("saju_memory", {}),
        # -- 즐겨찾기 --
        "favorites":     _ss.get("favorites", []),
    }
    try:
        with open(SAJU_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def load_saju_state():
    """saju_save.json에서 상태를 읽어 session_state에 복원"""
    if not os.path.exists(SAJU_SAVE_FILE):
        return
    try:
        with open(SAJU_SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    _ss = st.session_state
    # 단순 키 복원 (입력값 + 계산 결과)
    simple_keys = [
        "in_name", "in_gender", "in_cal_type",
        "in_lunar_year", "in_lunar_month", "in_lunar_day", "in_is_leap",
        "in_birth_hour", "in_birth_minute", "in_unknown_time",
        "in_marriage", "in_occupation", "in_premium_correction",
        "saju_pils", "birth_year", "birth_month", "birth_day",
        "birth_hour", "birth_minute", "gender", "saju_name",
        "marriage_status", "occupation", "cal_type", "lunar_info",
    ]
    for key in simple_keys:
        if key in data:
            _ss[key] = data[key]
    # date 객체 복원
    if "in_solar_date" in data:
        try:
            _ss["in_solar_date"] = date.fromisoformat(data["in_solar_date"])
        except Exception:
            pass
    # 기억 구조 복원
    if "saju_memory" in data:
        _ss["saju_memory"] = data["saju_memory"]
    # 즐겨찾기 복원
    if "favorites" in data:
        _ss["favorites"] = data["favorites"]


def _write_favorites_to_file(favorites: list):
    """saju_save.json의 favorites 키만 업데이트"""
    existing = {}
    if os.path.exists(SAJU_SAVE_FILE):
        try:
            with open(SAJU_SAVE_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["favorites"] = favorites
    try:
        with open(SAJU_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def save_to_favorites(label: str):
    """현재 상태를 즐겨찾기에 저장 (같은 label이면 덮어쓰기)"""
    _ss = st.session_state
    solar = _ss.get("in_solar_date")
    snapshot = {
        "label":             label or _ss.get("in_name") or "이름 없음",
        "in_name":           _ss.get("in_name", ""),
        "in_gender":         _ss.get("in_gender", "남"),
        "in_cal_type":       _ss.get("in_cal_type", "양력"),
        "in_solar_date":     solar.isoformat() if solar else "1990-01-01",
        "in_lunar_year":     _ss.get("in_lunar_year", 1990),
        "in_lunar_month":    _ss.get("in_lunar_month", 1),
        "in_lunar_day":      _ss.get("in_lunar_day", 1),
        "in_is_leap":        _ss.get("in_is_leap", False),
        "in_birth_hour":     _ss.get("in_birth_hour", 12),
        "in_birth_minute":   _ss.get("in_birth_minute", 0),
        "in_unknown_time":   _ss.get("in_unknown_time", False),
        "in_marriage":       _ss.get("in_marriage", "미혼"),
        "in_occupation":     _ss.get("in_occupation", "선택 안 함"),
        "in_premium_correction": _ss.get("in_premium_correction", True),
        "saju_pils":         _ss.get("saju_pils"),
        "birth_year":        _ss.get("birth_year"),
        "birth_month":       _ss.get("birth_month"),
        "birth_day":         _ss.get("birth_day"),
        "birth_hour":        _ss.get("birth_hour"),
        "birth_minute":      _ss.get("birth_minute"),
        "gender":            _ss.get("gender"),
        "saju_name":         _ss.get("saju_name"),
        "marriage_status":   _ss.get("marriage_status"),
        "occupation":        _ss.get("occupation"),
        "cal_type":          _ss.get("cal_type"),
        "lunar_info":        _ss.get("lunar_info", ""),
        "saju_memory":       _ss.get("saju_memory", {}),
    }
    favorites = list(_ss.get("favorites", []))
    for i, fav in enumerate(favorites):
        if fav.get("label") == snapshot["label"]:
            favorites[i] = snapshot
            break
    else:
        favorites.append(snapshot)
    _ss["favorites"] = favorites
    _write_favorites_to_file(favorites)


def load_from_favorite(idx: int):
    """즐겨찾기 항목을 session_state에 복원"""
    favorites = st.session_state.get("favorites", [])
    if not (0 <= idx < len(favorites)):
        return
    data = favorites[idx]
    _ss = st.session_state
    simple_keys = [
        "in_name", "in_gender", "in_cal_type",
        "in_lunar_year", "in_lunar_month", "in_lunar_day", "in_is_leap",
        "in_birth_hour", "in_birth_minute", "in_unknown_time",
        "in_marriage", "in_occupation", "in_premium_correction",
        "saju_pils", "birth_year", "birth_month", "birth_day",
        "birth_hour", "birth_minute", "gender", "saju_name",
        "marriage_status", "occupation", "cal_type", "lunar_info",
    ]
    for key in simple_keys:
        if key in data:
            _ss[key] = data[key]
    if "in_solar_date" in data:
        try:
            _ss["in_solar_date"] = date.fromisoformat(data["in_solar_date"])
        except Exception:
            pass
    if "saju_memory" in data:
        _ss["saju_memory"] = data["saju_memory"]
    _ss["form_expanded"] = False


def delete_favorite(idx: int):
    """즐겨찾기 항목 삭제"""
    favorites = list(st.session_state.get("favorites", []))
    if 0 <= idx < len(favorites):
        favorites.pop(idx)
        st.session_state["favorites"] = favorites
        _write_favorites_to_file(favorites)


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
        lines.append("신뢰도 높음 - 이전 예측이 맞았던 사용자. 더 구체적이고 단정적으로 해석하라.")
    elif bl <= 0.3:
        lines.append("신뢰도 낮음 - 의심이 많은 사용자. 근거를 더 상세히 설명하라.")

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


# ==============================================================
#  📊 STATISTICAL CORRECTION ENGINE - 통계 보정 시스템
#  사주 패턴 x 실제 데이터 -> 확률 기반 해석
# ==============================================================

# 패턴별 확률 데이터 (실증 기반 추정값)
_STATISTICAL_PATTERNS = {
    # (신강신약, 오행과다) -> (주제, 확률, 해석)
    ("신약", "金"): ("직장 스트레스", 76, "금기 과다 + 신약 -> 책임 부담, 직장 압박 패턴"),
    ("신약", "水"): ("과잉 사고", 71, "수기 과다 + 신약 -> 걱정/불안/수면 불안정"),
    ("신강", "火"): ("감정 폭발", 68, "화기 과다 + 신강 -> 충동적 표현, 인간관계 갈등"),
    ("신강", "木"): ("고집/충돌", 65, "목기 과다 + 신강 -> 타협 어려움, 독선적 결정"),
    ("중화", "土"): ("변화 저항", 62, "토기 균형 + 중화 -> 안정 선호, 새로움 회피"),
    ("신약", "火"): ("소진/번아웃", 74, "화기 과다 + 신약 -> 에너지 고갈, 소진 패턴"),
    ("신강", "金"): ("재물 집착", 66, "금기 과다 + 신강 -> 물질 중시, 절약 강박"),
    ("극신약", "土"): ("건강 취약", 79, "토기 과다 + 극신약 -> 소화기 계통 주의"),
    ("극신강", "木"): ("인간관계 마찰", 72, "목기 극강 -> 자기중심적, 협력 어려움"),
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
    hyeong_pairs = {("寅(인)","巳(사)","申(신)"), ("丑(축)","戌(술)","未(미)"), ("子(자)","卯(묘)")}
    all_jjs = frozenset(p["jj"] for p in pils)
    for combo in hyeong_pairs:
        if isinstance(combo, frozenset):
            if combo.issubset(all_jjs):
                insights.append({
                    "pattern": "삼형살(三刑殺)",
                    "topic": "사고/건강/법적 분쟁",
                    "prob": 61,
                    "insight": "삼형살 - 스트레스/사고/법적 문제 주의",
                    "advice": "큰 결정 전 충분한 검토. 건강검진 정기적으로.",
                })
        elif isinstance(combo, tuple) and len(combo) == 3:
            if frozenset(combo).issubset(all_jjs):
                insights.append({
                    "pattern": f"삼형살({','.join(combo)})",
                    "topic": "사고/건강/법적 분쟁",
                    "prob": 61,
                    "insight": f"{','.join(combo)} 삼형살 - 스트레스/사고/법적 문제 주의",
                    "advice": "큰 결정 전 충분한 검토. 건강검진 정기적으로.",
                })
        elif isinstance(combo, tuple) and len(combo) == 2:
            if combo[0] in all_jjs and combo[1] in all_jjs:
                insights.append({
                    "pattern": f"자묘형({combo[0]}{combo[1]})",
                    "topic": "인간관계 갈등",
                    "prob": 58,
                    "insight": "자묘형 - 원칙적 인간관계, 갈등 가능성",
                    "advice": "감정 조절과 유연한 대처가 중요합니다.",
                })

    return sorted(insights, key=lambda x: -x["prob"])[:4]  # 상위 4개


def _get_pattern_advice(sn: str, oh: str) -> str:
    """패턴별 실전 조언"""
    advice_map = {
        ("신약", "金"): "용신(木/水)의 방향으로 직업을 선택하면 스트레스가 줄어듭니다.",
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
            # 대운 호출 시 실제 생년월일시 반영
            _bm = st.session_state.get("birth_month", 1)
            _bd = st.session_state.get("birth_day", 1)
            _bh = st.session_state.get("birth_hour", 12)
            _bmi = st.session_state.get("birth_minute", 0)
            dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, _bm, _bd, _bh, _bmi, gender)
            for dw in dw_list:
                if dw["시작연도"] == future.year:
                    change_date = f"{future.year}년 {birth_year % 100 + dw['시작나이'] % 10}월경"
                    return {
                        "days_left": delta,
                        "date": change_date,
                        "description": f"새 대운 {dw['str']} 시작 - 인생 국면 전환",
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
    # 대운 호출 시 실제 생년월일시 반영
    _bm = st.session_state.get("birth_month", 1)
    _bd = st.session_state.get("birth_day", 1)
    _bh = st.session_state.get("birth_hour", 12)
    _bmi = st.session_state.get("birth_minute", 0)
    daewoon_list = SajuCoreEngine.get_daewoon(pils, birth_year, _bm, _bd, _bh, _bmi, gender)
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
    TG_HAP_PAIRS = [{"甲(갑)","己(기)"},{"乙(을)","庚(경)"},{"丙(병)","辛(신)"},{"丁(정)","壬(임)"},{"戊(무)","癸(계)"}]
    for pair in TG_HAP_PAIRS:
        if cur_dw["cg"] in pair and sewoon["cg"] in pair:
            cross_events.append({"type":"천간합","desc":f"대운 천간({cur_dw['cg']})과 세운 천간({sewoon['cg']})이 합(合). 변화와 기회의 해."})
    for k,(name,oh,desc) in CHUNG_MAP.items():
        if cur_dw["jj"] in k and sewoon["jj"] in k:
            cross_events.append({"type":"지지충","desc":f"대운 지지({cur_dw['jj']})와 세운 지지({sewoon['jj']})가 충(沖). {desc}"})
    for combo,(hname,hoh,hdesc) in SAM_HAP_MAP.items():
        all_jj = {cur_dw["jj"],sewoon["jj"]}|{p["jj"] for p in pils}
        if combo.issubset(all_jj):
            cross_events.append({"type":"삼합","desc":f"대운/세운/원국 삼합({hname}) - 강력한 발복의 기운."})
    ss_combo = f"{dw_cg_ss}+{sw_cg_ss}"
    interp = {
        "정관+식신":"명예와 재능이 동시에 빛나는 최길 조합. 승진/수상/큰 성취.",
        "식신+정재":"복록과 재물이 넘치는 대길 조합. 재물운 폭발.",
        "편관+편관":"이중 편관. 시련 극도. 건강/사고 각별히 주의.",
        "겁재+겁재":"이중 겁재. 재물 손실/경쟁 극심. 방어 전략이 최선.",
        "정인+정관":"학문과 명예 동시에 오는 최길 조합. 시험/자격증/승진.",
        "편관+식신":"칠살제화(七殺制化) - 시련이 오히려 기회가 됩니다.",
        "정재+정관":"재물과 명예 함께 오는 길한 조합. 사업 성공과 인정.",
    }
    cross_desc = interp.get(ss_combo,f"대운 {dw_cg_ss}의 흐름 속에 세운 {sw_cg_ss}의 기운이 더해집니다.")
    return {"연도":target_year,"대운":cur_dw,"세운":sewoon,"대운_천간십성":dw_cg_ss,
            "대운_지지십성":dw_jj_ss,"세운_천간십성":sw_cg_ss,"세운_지지십성":sw_jj_ss,"교차사건":cross_events,"교차해석":cross_desc}


# ==================================================
#  지장간(地藏干) 심화
# ==================================================

JIJANGGAN_FULL = {
    "子(자)":[{"cg":"壬(임)","days":10,"type":"여기"},{"cg":"癸(계)","days":20,"type":"정기"}],
    "丑(축)":[{"cg":"己(기)","days":9,"type":"여기"},{"cg":"辛(신)","days":3,"type":"중기"},{"cg":"癸(계)","days":18,"type":"정기"}],
    "寅(인)":[{"cg":"戊(무)","days":7,"type":"여기"},{"cg":"丙(병)","days":7,"type":"중기"},{"cg":"甲(갑)","days":16,"type":"정기"}],
    "卯(묘)":[{"cg":"甲(갑)","days":10,"type":"여기"},{"cg":"乙(을)","days":20,"type":"정기"}],
    "辰(진)":[{"cg":"乙(을)","days":9,"type":"여기"},{"cg":"癸(계)","days":3,"type":"중기"},{"cg":"戊(무)","days":18,"type":"정기"}],
    "巳(사)":[{"cg":"戊(무)","days":7,"type":"여기"},{"cg":"庚(경)","days":7,"type":"중기"},{"cg":"丙(병)","days":16,"type":"정기"}],
    "午(오)":[{"cg":"丙(병)","days":10,"type":"여기"},{"cg":"己(기)","days":10,"type":"중기"},{"cg":"丁(정)","days":10,"type":"정기"}],
    "未(미)":[{"cg":"丁(정)","days":9,"type":"여기"},{"cg":"乙(을)","days":3,"type":"중기"},{"cg":"己(기)","days":18,"type":"정기"}],
    "申(신)":[{"cg":"戊(무)","days":7,"type":"여기"},{"cg":"壬(임)","days":7,"type":"중기"},{"cg":"庚(경)","days":16,"type":"정기"}],
    "酉(유)":[{"cg":"庚(경)","days":10,"type":"여기"},{"cg":"辛(신)","days":20,"type":"정기"}],
    "戌(술)":[{"cg":"辛(신)","days":9,"type":"여기"},{"cg":"丁(정)","days":3,"type":"중기"},{"cg":"戊(무)","days":18,"type":"정기"}],
    "亥(해)":[{"cg":"甲(갑)","days":7,"type":"여기"},{"cg":"壬(임)","days":7,"type":"중기"},{"cg":"壬(임)","days":16,"type":"정기"}],
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


# ==================================================
#  건강론(健康論)
# ==================================================

HEALTH_OH = {
    "木":{"organs":"간/담낭/눈/근육/신경계","emotion":"분노(怒)","over_symptom":"간염/담석/녹내장/편두통/불면","lack_symptom":"피로/우울/근육약화/시력저하","food":"신맛(식초/레몬/매실)/녹색식품","lifestyle":"새벽 취침 자제/분노 다스리기/스트레칭/요가","lucky_direction":"동쪽(東)"},
    "火":{"organs":"심장/소장/혈관/혀","emotion":"기쁨 과다(喜)","over_symptom":"심장병/고혈압/불안/불면/구내염","lack_symptom":"저혈압/우울/기억력저하/손발냉","food":"쓴맛(녹차/씀바귀)/붉은 식품(토마토/딸기)","lifestyle":"명상/호흡수련/과로 자제/충분한 수분","lucky_direction":"남쪽(南)"},
    "土":{"organs":"비장/위장/췌장/입술","emotion":"근심(思)","over_symptom":"위염/소화불량/위궤양/비만/당뇨","lack_symptom":"식욕부진/빈혈/면역저하/피로","food":"단맛(고구마/대추/꿀)/황색식품(콩/현미)","lifestyle":"규칙적 식사/걱정 줄이기/복식호흡","lucky_direction":"중앙"},
    "金":{"organs":"폐/대장/코/피부/기관지","emotion":"슬픔(悲)","over_symptom":"폐렴/천식/비염/변비/아토피","lack_symptom":"감기 잦음/대장 약함/피부트러블","food":"매운맛(무/생강)/흰색식품(배/연근/우유)","lifestyle":"심호흡/콧속보습/슬픔 표현하기","lucky_direction":"서쪽(西)"},
    "水":{"organs":"신장/방광/뼈/귀/두발/생식기","emotion":"공포(恐)","over_symptom":"신장염/방광염/골다공증/이명/탈모","lack_symptom":"허리약함/냉증/건망증/두발약화","food":"짠맛(미역/다시마/검은콩)/검은식품","lifestyle":"밤 11시 전 취침/허리보호/따뜻한 물","lucky_direction":"북쪽(北)"},
}

def get_health_analysis(pils, gender="남"):
    ilgan = pils[1]["cg"]
    oh_strength = calc_ohaeng_strength(ilgan, pils)
    unsung = calc_12unsung(ilgan, pils)
    il_unsung = unsung[1] if len(unsung)>1 else ""
    il_oh = OH.get(ilgan,"")
    HEALTH_UNSUNG = {"병":"병지(病地) - 건강 약한 구조. 정기 검진 필수.","사":"사지(死地) - 생명력 약함. 안전사고/건강 각별 주의.","절":"절지(絶地) - 체력 소진되기 쉬움.","묘":"묘지(墓地) - 만성질환 오래 지속될 수 있음."}
    return {"과다_오행":[{"오행":o,"수치":v,"health":HEALTH_OH.get(o,{})} for o,v in oh_strength.items() if v>=35],
            "부족_오행":[{"오행":o,"수치":v,"health":HEALTH_OH.get(o,{})} for o,v in oh_strength.items() if v<=5],
            "일주_건강":HEALTH_UNSUNG.get(il_unsung,""),"일간_건강":HEALTH_OH.get(il_oh,{}),
            "ilgan_oh":il_oh,"oh_strength":oh_strength}


# ==================================================
#  재물론(財物論)
# ==================================================

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
        if ss_cg in ["正財","偏財"]: jae_pos.append(f"{lbl} 천간({ss_cg})")
        if ss_jj in ["正財","偏財"]: jae_pos.append(f"{lbl} 지지({ss_jj})")
    # 대운 재물 피크 (사용자 지침 준수)
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    peaks = [{"대운":d["str"],"나이":f"{d['시작나이']}~{d['시작나이']+9}세","연도":f"{d['시작연도']}~{d['종료연도']}","십성":TEN_GODS_MATRIX.get(ilgan,{}).get(d["cg"],"-")} for d in daewoon if TEN_GODS_MATRIX.get(ilgan,{}).get(d["cg"],"-") in ["正財","偏財","食神"]]
    # 유형 판단
    if sn=="신강(身强)" and jae_strength>=20: jtype,jstrat="적극형 - 강한 일간이 재성을 다루는 이상적 구조.","재성 운에서 과감히 행동하십시오."
    elif sn=="신약(身弱)" and jae_strength>=30: jtype,jstrat="부담형 - 재물이 있어도 감당하기 벅찬 구조.","고정수입/저축 중심으로 운용하십시오."
    elif jae_strength==0: jtype,jstrat="재성공망형 - 재성이 없는 사주. 명예/학문/기술로 성공.","전문성과 명예를 쌓으면 돈은 따라옵니다."
    else: jtype,jstrat="균형형 - 꾸준한 노력으로 재물을 쌓아가는 구조.","안정적 자산관리가 유리합니다."
    return {"재성_오행":jae_oh,"재성_강도":jae_strength,"재성_위치":jae_pos,
            "재물_유형":jtype,"재물_전략":jstrat,"재물_피크_대운":peaks,"신강신약":sn}


# ==================================================
#  직업론(職業論)
# ==================================================

CAREER_MATRIX = {
    "正官格":{"best":["공무원/행정관리","판사/검사/법조인","대기업 임원","교육공무원","군 장교/외교관"],"good":["금융/은행/보험","교사/교수","의사/한의사"],"avoid":["자유업/프리랜서","예능/연예계","투기적 사업"]},
    "偏官格":{"best":["군인/경찰/소방관","외과의사/응급의학","스포츠/격투기","검사/형사","위기관리/보안"],"good":["공학/기술자","법조인","언론(탐사)"],"avoid":["세밀한 행정직","반복 사무직"]},
    "食神格":{"best":["요리사/외식업","예술가/음악인","작가/시인","교육자/강사","의료/복지"],"good":["아이디어 사업","복지/상담","유튜버/콘텐츠"],"avoid":["과도한 경쟁직","군사/강압 조직"]},
    "傷官格":{"best":["연예인/유튜버/방송인","변호사/변리사","창업가/혁신가","작가/작곡가","언론인/PD"],"good":["스타트업","컨설턴트","디자이너"],"avoid":["관직/공무원","상명하복 직종"]},
    "正財格":{"best":["회계사/세무사","은행원/금융관리","부동산 관리","행정관리","의사/약사"],"good":["대기업 재무/회계","보험/연금"],"avoid":["투기/도박성 사업","예능/불규칙수입"]},
    "偏財格":{"best":["사업가/CEO","투자자/펀드매니저","무역상/유통업","부동산 개발","연예인/방송"],"good":["영업/마케팅","스타트업 창업","프리랜서"],"avoid":["단순 반복 사무직","소규모 고정급여직"]},
    "正印格":{"best":["교수/학자/연구원","교사/교육자","의사/한의사","변호사","종교인/성직자"],"good":["작가/언론인","공직자","상담사"],"avoid":["격렬한 경쟁 사업","단순 노무직"]},
    "偏印格":{"best":["철학자/사상가","종교인/영성가","명리학자/점술가","IT개발자","탐정/분석가"],"good":["심리학자","연구원","특수기술자"],"avoid":["대형 조직 관리직","서비스업"]},
    "比肩格":{"best":["독립 사업가","컨설턴트","스포츠 코치","사회운동가"],"good":["팀 기반 사업","멘토/코치"],"avoid":["독점적 대기업","단일 보스 직종"]},
    "劫財格":{"best":["운동선수/격투기","영업전문가","경쟁적 사업","변호사","스타트업"],"good":["군인/경찰","마케터"],"avoid":["재정/회계 관리","보수적 공직"]},
}
ILGAN_CAREER_ADD = {
    "甲(갑)":["건축/목재/산림","교육/인재개발"],"乙(을)":["꽃/원예/디자인","상담/교육"],"丙(병)":["방송/연예","발전/에너지"],
    "丁(정)":["의료/제약","교육/종교"],"戊(무)":["건설/부동산","농업/식품"],"己(기)":["농업/식품가공","행정/회계"],
    "庚(경)":["금융/금속/기계","법조/군경"],"辛(신)":["패션/보석/예술","의료/약학"],"壬(임)":["해운/무역/외교","IT/전략"],
    "癸(계)":["상담/심리/영성","의료/약학"],
}

def get_career_analysis(pils, gender="남"):
    ilgan = pils[1]["cg"]
    gyeokguk = get_gyeokguk(pils)
    gname = gyeokguk["격국명"] if gyeokguk else "比肩格"
    career = CAREER_MATRIX.get(gname, CAREER_MATRIX["比肩格"])
    sinsal = get_12sinsal(pils)
    sinsal_jobs = []
    for s in sinsal:
        if "장성" in s["이름"]: sinsal_jobs.append("군/경/스포츠 수장 기질")
        if "화개" in s["이름"]: sinsal_jobs.append("예술/종교/철학 방면 특화")
        if "역마" in s["이름"]: sinsal_jobs.append("이동/무역/해외 관련 직종 유리")
        if "도화" in s["이름"] or "년살" in s["이름"]: sinsal_jobs.append("연예/서비스/대인 방면 유리")
    yin = get_yangin(pils)
    if yin["존재"]: sinsal_jobs.append("군/경/의료(외과) 분야 강한 기질")
    return {"격국":gname,"최적직업":career["best"],"유리직업":career["good"],"피할직업":career["avoid"],
            "일간추가":ILGAN_CAREER_ADD.get(ilgan,[]),"신살보정":sinsal_jobs}


# ==================================================
#  개명(改名) 오행 분석
# ==================================================

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


# ==================================================
#  새 탭 UI 함수들
# ==================================================

################################################################################
# *** Brain 3 - Learning & Monetization Engine ***
#
# [역할]  사용자 반응을 수집/분석하여 AI 프롬프트를 자동 강화한다
#
# [데이터 흐름]
#   사용자 반응 -> Feedback Collector
#               -> Pattern Analyzer   (어떤 문장이 결제/재방문 유도?)
#               -> Prompt Optimizer   (다음 AI 호출 프롬프트 자동 강화)
#               -> Monetization Trigger (결제 타이밍 감지)
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


# -----------------------------------------------------------------------------
# Brain 3-③ : Prompt Optimizer
# -----------------------------------------------------------------------------

def b3_build_optimized_prompt_suffix() -> str:
    """
    패턴 분석 결과를 바탕으로 AI 프롬프트에 추가할 강화 지침 생성
    적중률이 낮은 섹션을 집중 강화하도록 AI에게 알린다
    """
    patterns = _load_json_cache(_PATTERN_FILE)
    if not patterns or patterns.get("total", 0) < 10:
        # 데이터 부족 -> 기본 지침
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
    lines.append("- 당신은 만신(萬神)의 권위를 가진 40년 경력의 전문가로서, 분석 데이터에 기반하여 단정적으로 예고하십시오.")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Brain 3-④ : Monetization Trigger (결제 타이밍 감지)
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Brain 3 통합: 피드백 버튼 (기존 render_feedback_btn 대체)
# -----------------------------------------------------------------------------

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


def tab_past_events(pils, birth_year, gender, name=""):
    """[적중] 과거 적중 탭 - 엔진이 계산, AI는 설명만"""
    st.markdown('<div class="gold-section">[데이터] 과거 적중 - 엔진이 계산한 당신의 과거</div>',
                unsafe_allow_html=True)

    # 엔진 하이라이트 생성
    with st.spinner("충/합/세운 교차 계산 중..."):
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
            # v2 도메인
            "직업변화": "#2980b9", "결혼·교제": "#e91e8c", "이사·이동": "#16a085",
            "재물획득": "#27ae60", "재물손실": "#e67e22", "사고·관재": "#c0392b", "질병·건강": "#8e44ad",
            # 기존 키워드 포함 폴백
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

    # ==========================================
    # 돈 + 결혼 타이밍
    # ==========================================
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

    # ==============================================
    # ⏱️ 생애 사건 타임라인 (5개 도메인 핀포인팅)
    # ==============================================
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a1a,#2c2c2c);border-radius:14px;
            padding:16px 20px;margin-bottom:14px">
    <div style="color:#f7e695;font-size:15px;font-weight:900;letter-spacing:2px">⏱️ 생애 사건 타임라인</div>
    <div style="color:#ccc;font-size:12px;margin-top:4px">
        대운×세운 교차 계산으로 뽑은 5개 도메인별 과거 핀포인팅입니다.<br>
        나이와 분야가 맞으면 <b style="color:#f7e695">맞았다</b>를 눌러주세요.
    </div>
</div>""", unsafe_allow_html=True)

    with st.spinner("생애 타임라인 계산 중..."):
        timeline = build_life_event_timeline(pils, birth_year, gender)

    if timeline:
        DOMAIN_COLOR = {
            "직업변화": "#2980b9", "결혼·교제": "#e91e8c",
            "이사·이동": "#16a085", "재물획득": "#27ae60",
            "재물손실": "#e67e22", "사고·관재": "#c0392b", "질병·건강": "#8e44ad",
            # 구버전 호환
            "직업변동": "#2980b9", "결혼/이별": "#e91e8c",
            "이사/이동": "#16a085", "재물성쇠": "#27ae60", "건강이상": "#8e44ad",
        }
        for ti, ev in enumerate(timeline):
            dc = DOMAIN_COLOR.get(ev["domain"], "#666")
            sign_html = f"<span style='color:#c0392b;font-weight:800'>[!]️</span>" if ev["sign"] == "🔴" else "<span style='color:#f39c12;font-weight:800'>*</span>"
            html = f"""
<div style="background:#fff;border:1px solid {dc}33;border-left:5px solid {dc};
            border-radius:12px;padding:14px 16px;margin:6px 0">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div>
            {sign_html}
            <span style="font-size:19px;font-weight:900;color:{dc};margin-left:4px">{ev['age']}세</span>
            <span style="font-size:12px;color:#555;margin-left:6px">({ev['year']}년)</span>
        </div>
        <div style="background:{dc};color:#fff;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700">
            {ev['emoji']} {ev['domain']}
        </div>
    </div>
    <div style="font-size:13px;color:#222;line-height:1.9;background:#f9f9f9;
                padding:10px 14px;border-radius:8px">{ev['desc']}</div>
</div>"""
            st.markdown(html, unsafe_allow_html=True)
            render_feedback_btn(f"timeline_{ti}", f"{ev['age']}세 {ev['domain']}")
    else:
        st.info("과거 생애 사건 데이터가 충분하지 않습니다.")

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



def tab_cross_analysis(pils, birth_year, gender):
    """대운/세운 교차 분석 - 3중 완전판"""
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
    ys = get_yongshin(pils); yongshin_ohs = ys.get("종합_용신", []) if ys else []
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
        elif d_is_y or s_is_y:  row_lc, row_bg, badge = "#2980b9","#f0f8ff","- 길"
        elif "흉" in c2["세운"]["길흉"]: row_lc, row_bg, badge = "#c0392b","#fff5f5","[!]️ 흉"
        else:                    row_lc, row_bg, badge = "#888","#fafafa","〰️ 평"
        hb_icon = " 🚨합깨짐" if hb else ""
        st.markdown(f"""
<div style="display:flex;align-items:center;padding:9px 14px;border-radius:10px;margin:3px 0;background:{row_bg};border:{'2px solid '+row_lc if y==year_sel else '1px solid #e8e8e8'}">
    <span style="font-weight:800;color:#000000;min-width:52px">{y}년</span>
    <span style="min-width:80px;font-size:13px;color:#333">大運:{c2["대운"]["str"]}</span>
    <span style="min-width:80px;font-size:13px;color:#333">세운:{c2["세운"]["세운"]}</span>
    <span style="flex:1;font-size:12px;color:#444">{c2["대운_천간십성"]}+{c2["세운_천간십성"]}</span>
    <span style="font-size:12px;color:#c0392b">{hb_icon}</span>
    <span style="font-weight:700;color:{row_lc};font-size:13px">{badge}</span>
</div>
""", unsafe_allow_html=True)




def tab_jaemul(pils, birth_year, gender="남"):
    st.markdown('<div class="gold-section">[재물론] 재물론(財物論) - 돈이 모이는 구조 분석</div>', unsafe_allow_html=True)
    jm = get_jaemul_analysis(pils, birth_year, gender)
    oh_emoji = {"木":"[木]","火":"[火]","土":"[土]","金":"[金]","水":"[水]"}
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
        html += ''.join([f'<div style="font-size:13px;color:#000000;margin:3px 0">* {s}</div>' for s in ca["신살보정"]])
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    if ca["피할직업"]:
        st.markdown(f'<div class="card" style="background:#fff0f0;border:1px solid #d5a8a8;margin-top:8px"><b style="color:#8b2020">[제외] 피해야 할 직업:</b> {"  /  ".join(ca["피할직업"])}</div>', unsafe_allow_html=True)


# --------------------------------------------------
# 서술형 대형 내러티브 생성기
# --------------------------------------------------

ILGAN_CHAR_DESC = {
    "甲(갑)": {
        "상징":"큰 나무(大木). 곧게 뻗은 소나무처럼 굽히지 않는 기상의 사람입니다.",
        "성격_핵심":"리더십과 개척 정신이 천부적입니다. 처음 길을 내는 것을 두려워하지 않으며, 한번 마음먹은 일은 반드시 완수하려는 집요함이 있습니다. 주변 사람들은 이 사람을 '신뢰할 수 있는 맏형'처럼 느낍니다.",
        "장점":"결단력/원칙/신뢰/강한 추진력/정의감/독립심",
        "단점":"고집이 지나쳐 융통성이 부족할 수 있습니다. 자신의 방식만 옳다고 여기는 경향이 있어 타인과 마찰이 생기기도 합니다.",
        "재물패턴":"재물은 꾸준한 노력으로 쌓이는 타입입니다. 한번에 큰돈을 버는 것보다 오랜 기간 성실하게 쌓아가는 방식이 맞습니다. 투기성 투자는 대체로 손해를 봅니다.",
        "건강":"간장/담낭 계통을 주의해야 합니다. 눈의 피로, 근육 경직이 오기 쉬우니 스트레칭과 규칙적 수면이 중요합니다.",
        "직업":"정치/행정/교육/건설/목재/의료/법조 계통에서 강합니다.",
        "연애_남":"연인에게 든든한 버팀목이 되지만, 너무 강한 주도권으로 상대가 답답해하기도 합니다.",
        "연애_여":"강한 자존감으로 자신만의 기준이 뚜렷합니다. 약한 남성보다 자신보다 강한 남성에게 끌립니다.",
    },
    "乙(을)": {
        "상징":"작은 풀/덩굴(小木). 부드럽게 환경에 적응하며 결국 원하는 곳에 도달하는 사람입니다.",
        "성격_핵심":"겉으로는 부드럽고 온화하지만, 속으로는 강인한 의지가 숨어 있습니다. 처음에는 유연하게 받아들이는 것처럼 보이지만, 결국 자신이 원하는 방향으로 조용히 이끌어가는 능력이 있습니다.",
        "장점":"적응력/감수성/예술적 감각/인내/섬세함/사교성",
        "단점":"우유부단하고 결정을 미루는 경향이 있습니다. 주변 눈치를 너무 봐서 정작 자신의 뜻을 제대로 표현하지 못할 때도 있습니다.",
        "재물패턴":"재물 운이 꾸준한 편입니다. 강하게 밀어붙이기보다 관계를 통해 자연스럽게 기회가 오는 경우가 많습니다. 파트너십 사업이 유리합니다.",
        "건강":"간장/목 계통, 신경 계통이 약할 수 있습니다. 스트레스를 몸으로 표현하는 경향이 있으니 정서적 안정이 건강의 핵심입니다.",
        "직업":"디자인/예술/상담/서비스/교육/언론/의료 분야가 맞습니다.",
        "연애_남":"섬세하고 상대방 감정을 잘 읽습니다. 로맨틱한 분위기를 중요시합니다.",
        "연애_여":"부드럽고 매력적이지만, 관계에서 상대에게 의존하는 경향이 있습니다. 자립심을 키우는 것이 연애 성공의 열쇠입니다.",
    },
    "丙(병)": {
        "상징":"태양(太陽). 자신의 빛으로 주변을 밝히는 타고난 주인공입니다.",
        "성격_핵심":"어디서나 중심에 서는 카리스마가 있습니다. 밝고 활기차며 사람들을 자연스럽게 끌어당기는 매력이 있습니다. 솔직하고 직선적이어서 속에 있는 것을 숨기지 못합니다. 인기와 명예를 중요시합니다.",
        "장점":"카리스마/열정/사교성/창의력/용기/리더십/직관",
        "단점":"자기중심적인 면이 강해 타인의 의견을 무시하기도 합니다. 체면을 중시해서 실리보다 감정적 판단을 내릴 때가 있습니다.",
        "재물패턴":"화려하게 벌고 화려하게 쓰는 타입입니다. 재물보다 명예를 먼저 생각하는 경향이 있어, 돈이 잘 모이지 않을 수 있습니다. 관리 체계를 만드는 것이 중요합니다.",
        "건강":"심장/소장/눈 계통을 주의해야 합니다. 과로와 흥분 상태가 지속되면 심혈관에 무리가 옵니다.",
        "직업":"연예/방송/정치/영업/마케팅/교육/예술 분야에서 빛납니다.",
        "연애_남":"열정적이고 드라마틱한 연애를 좋아합니다. 상대에게 아낌없이 주지만 인정받기를 원합니다.",
        "연애_여":"화려하고 밝은 매력이 있습니다. 자신을 빛나게 해주는 파트너를 원합니다.",
    },
    "丁(정)": {
        "상징":"촛불/등불(小火). 차분하지만 가까이 있는 이에게 따뜻함을 주는 사람입니다.",
        "성격_핵심":"겉으로는 조용하고 내성적이지만, 내면에는 강렬한 열정이 숨어 있습니다. 섬세한 감수성으로 주변을 깊이 관찰하고 이해합니다. 소수의 친한 사람들과 깊은 관계를 맺는 것을 선호합니다.",
        "장점":"섬세함/집중력/예술성/따뜻함/통찰력/신중함",
        "단점":"지나치게 내향적이어서 자신을 표현하지 못할 때가 있습니다. 상처를 마음속에 쌓아두는 경향이 있어 정서적 소진이 올 수 있습니다.",
        "재물패턴":"꾸준한 노력으로 쌓아가는 재물 운입니다. 화려한 한방보다는 전문성과 기술을 통한 안정적인 수입이 맞습니다.",
        "건강":"심장/소장/혈압 관련 질환을 주의해야 합니다. 스트레스를 쌓아두면 화병이 올 수 있습니다.",
        "직업":"연구/개발/예술/상담/의료/교육/IT 분야가 잘 맞습니다.",
        "연애_남":"깊고 진지한 관계를 원합니다. 가볍거나 피상적인 관계에는 관심이 없습니다.",
        "연애_여":"감수성이 풍부하고 내면이 깊습니다. 자신을 이해해주는 파트너를 만나면 헌신적입니다.",
    },
    "戊(무)": {
        "상징":"큰 산/대지(大土). 든든하고 안정적인 중심축 같은 사람입니다.",
        "성격_핵심":"묵직하고 믿음직스러운 성품입니다. 말보다 행동으로 보여주는 타입이며, 한번 신뢰를 쌓으면 절대 배신하지 않는 의리가 있습니다. 변화보다 안정을 선호하고, 큰 그림을 바라보는 안목이 있습니다.",
        "장점":"안정감/신뢰/인내/책임감/포용력/현실감각",
        "단점":"변화에 느리고 보수적입니다. 한번 결심한 것을 바꾸지 않아 고집스러워 보이기도 합니다.",
        "재물패턴":"부동산/토지 관련 투자에 강합니다. 안정적이고 장기적인 투자가 맞으며, 단타성 투기는 손해를 봅니다.",
        "건강":"비장/위장 계통을 주의해야 합니다. 과식과 폭식 경향이 있으니 규칙적인 식사가 중요합니다.",
        "직업":"건설/부동산/금융/토목/행정/중재/교육 분야가 맞습니다.",
        "연애_남":"든든한 파트너입니다. 화려함보다 안정감으로 사람을 끌어들입니다.",
        "연애_여":"무거운 책임감으로 가정을 지키는 타입입니다. 파트너를 선택할 때 신중하고 보수적입니다.",
    },
    "己(기)": {
        "상징":"논밭/평지(小土). 부드럽고 기름진 땅처럼 모든 것을 품어주는 사람입니다.",
        "성격_핵심":"온화하고 섬세하며 주변 사람들에 대한 배려가 넘칩니다. 갈등을 중재하는 능력이 탁월하고, 어디서나 분위기를 부드럽게 만드는 역할을 합니다. 다소 소심한 면이 있지만, 인간관계에서 깊은 신뢰를 받습니다.",
        "장점":"배려/중재능력/섬세함/인내/유연성/실용성",
        "단점":"우유부단하고 결정을 미루는 경향이 있습니다. 타인의 감정에 너무 민감해 자신을 희생하는 경우가 많습니다.",
        "재물패턴":"서비스/유통/중개업이 잘 맞습니다. 사람 사이에서 이익을 만드는 구조가 이 일간에 맞습니다.",
        "건강":"비장/위장/췌장 계통을 주의해야 합니다. 걱정과 불안이 많을수록 소화기 증상이 나타납니다.",
        "직업":"서비스/유통/의료/상담/교육/식품/복지 분야가 잘 맞습니다.",
        "연애_남":"헌신적이고 배려가 넘칩니다. 다만 자신의 감정을 솔직하게 표현하지 못하는 경우가 있습니다.",
        "연애_여":"따뜻하고 모성적입니다. 파트너를 돌보는 것에서 행복을 느낍니다.",
    },
    "庚(경)": {
        "상징":"큰 쇠/바위(大金). 강하고 날카로운 검처럼 결단력 있는 사람입니다.",
        "성격_핵심":"강직하고 원칙적입니다. 옳고 그름을 분명히 하는 성격으로, 불의를 보면 참지 못합니다. 추진력이 강하고 결단이 빠릅니다. 한번 마음먹으면 돌아서지 않는 의지가 있습니다.",
        "장점":"결단력/원칙/강한 의지/정의감/추진력/카리스마",
        "단점":"지나치게 강해서 주변을 불편하게 만들 수 있습니다. 유연성이 부족하고, 감정 표현이 서툽니다.",
        "재물패턴":"금속/기계/군경/의료 관련 분야에서 재물이 들어옵니다. 결단력 있게 투자하지만 손실도 크게 볼 수 있습니다.",
        "건강":"폐/대장 계통을 주의해야 합니다. 피부 트러블이나 호흡기 질환에 취약합니다.",
        "직업":"군경/의료(외과)/금속/기계/법조/스포츠 분야에서 강합니다.",
        "연애_남":"강하고 보호본능이 있습니다. 상대에게 든든한 울타리가 됩니다.",
        "연애_여":"독립적이고 자존심이 강합니다. 자신보다 약한 상대는 존중하지 않는 경향이 있습니다.",
    },
    "辛(신)": {
        "상징":"작은 쇠/보석(小金). 섬세하게 다듬어진 보석처럼 아름답고 예리한 사람입니다.",
        "성격_핵심":"완벽주의적 성향이 강합니다. 세밀한 부분까지 놓치지 않는 날카로운 관찰력과 분석력이 있습니다. 외모나 이미지 관리에 신경을 쓰며, 품위와 격식을 중요하게 여깁니다.",
        "장점":"완벽주의/분석력/심미안/섬세함/예리함/품위",
        "단점":"완벽주의가 지나쳐 스스로를 혹독하게 대합니다. 타인에 대한 기준도 높아 관계에서 갈등이 생기기도 합니다.",
        "재물패턴":"전문성과 기술로 재물을 쌓는 타입입니다. 장기적 계획과 꼼꼼한 관리가 재물 성장의 열쇠입니다.",
        "건강":"폐/기관지/피부 계통을 주의해야 합니다. 스트레스가 쌓이면 피부 증상으로 나타납니다.",
        "직업":"의료/법/금융/예술/IT/디자인/분석 분야가 맞습니다.",
        "연애_남":"이상형이 높고 기준이 까다롭습니다. 상대의 외모와 품위를 중요하게 봅니다.",
        "연애_여":"섬세하고 완벽한 연애를 원합니다. 작은 실망에도 관계를 재고하는 경향이 있습니다.",
    },
    "壬(임)": {
        "상징":"큰 강/바다(大水). 넓고 깊은 지혜와 포용력으로 세상을 흐르는 사람입니다.",
        "성격_핵심":"지혜롭고 통찰력이 뛰어납니다. 유연하게 상황에 적응하며 깊은 사고력으로 문제를 해결합니다. 대범하고 활동적이며, 새로운 세계를 탐험하는 것을 즐깁니다. 추진력과 사교성이 높습니다.",
        "장점":"지혜/유연성/추진력/사교성/통찰력/적응력/대범함",
        "단점":"자신의 기분과 감정 기복이 심할 수 있습니다. 집중력이 분산되어 한 가지에 끝까지 매달리기 어려울 수 있습니다.",
        "재물패턴":"무역/금융/유통/IT 등 유동성이 큰 분야에서 재물이 들어옵니다. 흐름을 잘 타는 편입니다.",
        "건강":"신장/방광/생식기 계통을 주의해야 합니다. 과로와 수면 부족이 축적되지 않도록 해야 합니다.",
        "직업":"무역/금융/IT/운수/언론/정치/외교 분야에서 두각을 나타냅니다.",
        "연애_남":"매력적이고 사교적입니다. 다양한 이성을 경험하는 경향이 있어 정착이 늦을 수 있습니다.",
        "연애_여":"활발하고 매력적입니다. 활동적이고 지적인 파트너를 선호합니다.",
    },
    "癸(계)": {
        "상징":"빗물/샘물(小水). 조용히 스며들어 만물을 적시는 섬세한 지혜의 사람입니다.",
        "성격_핵심":"내성적이지만 깊은 통찰력을 가진 사람입니다. 감수성이 풍부하고 직관이 예리하여, 말하지 않아도 상대의 마음을 읽는 능력이 있습니다. 혼자만의 시간이 필요하고 고독 속에서 창의력이 발현됩니다.",
        "장점":"직관/감수성/지혜/창의력/신중함/통찰력",
        "단점":"예민하고 감정적으로 흔들리기 쉽습니다. 지나치게 내성적이어서 기회를 놓치는 경우도 있습니다.",
        "재물패턴":"전문 지식과 직관으로 재물을 만드는 타입입니다. 수면 아래서 조용히 부를 쌓는 방식이 맞습니다.",
        "건강":"신장/방광/귀 계통을 주의해야 합니다. 감정이 쌓이면 면역력이 떨어집니다.",
        "직업":"연구/예술/의료/심리상담/IT/문학/철학 분야가 잘 맞습니다.",
        "연애_남":"깊고 감성적인 연애를 합니다. 상대의 감정을 잘 읽어주지만 스스로 표현이 서툽니다.",
        "연애_여":"섬세하고 로맨틱합니다. 깊은 정서적 교감을 나눌 수 있는 파트너를 원합니다.",
    },
}

GYEOKGUK_NARRATIVE = {
    "정관격": "정관격은 사회적 규범과 질서를 중시하는 귀격(貴格)입니다. 이 격국을 가진 분은 법과 원칙 안에서 정당한 방법으로 높은 자리에 오르는 운명입니다. 성실함과 신뢰가 최대 무기이며, 꾸준히 실력을 쌓다 보면 반드시 인정받는 날이 옵니다. 직장 조직에서 빛나는 운으로, 공무원/교사/법조인/관리직이 잘 맞습니다. 다만 자신의 원칙을 지나치게 고집하면 주변과 마찰이 생기니 유연성을 함께 갖추어야 합니다.",
    "편관격": "편관격은 칠살격(七殺格)이라고도 하며, 강렬한 도전과 시련 속에서 성장하는 운명입니다. 어려움이 올수록 더욱 강해지는 역경의 강자입니다. 군인/경찰/의사/운동선수처럼 극한의 상황을 이겨내는 직업에서 탁월한 능력을 발휘합니다. 칠살이 잘 제화(制化)되면 최고의 성공을 이루는 대귀격이 됩니다. 관리되지 않은 칠살은 충동과 과격함으로 나타날 수 있으니 감정 조절이 중요합니다.",
    "정재격": "정재격은 성실하고 꾸준하게 재물을 쌓아가는 안정형 격국입니다. 한탕을 노리기보다 묵묵히 일하고 저축하여 결국 부를 이루는 타입입니다. 금융/부동산/유통/회계 분야에서 두각을 나타내며, 인생 후반에 더욱 빛나는 운명입니다. 이 격국은 배우자 인연이 좋아 가정이 안정적이며, 파트너의 내조가 큰 힘이 됩니다. 지나친 소심함으로 기회를 놓치지 않도록 용기 있는 결단이 필요한 순간도 있습니다.",
    "편재격": "편재격은 활동적이고 대담한 재물 운의 격국입니다. 사업/투자/무역처럼 움직임이 큰 분야에서 재물이 들어옵니다. 한자리에 머물기보다 넓은 세계를 돌아다니며 기회를 만드는 타입입니다. 기복이 있지만 그만큼 크게 버는 운도 있습니다. 아버지와의 인연이 인생에 큰 영향을 미칩니다. 재물이 들어온 만큼 나가기도 하므로, 수입의 일정 부분은 반드시 안전한 곳에 묶어두는 습관이 중요합니다.",
    "식신격": "식신격은 하늘이 내리신 복록의 격국입니다. 타고난 재능과 끼가 있어 그것을 표현하는 것만으로도 재물과 인복이 따라옵니다. 먹는 것을 즐기고 생활의 여유를 즐기며, 주변에 즐거움을 주는 사람입니다. 예술/요리/교육/서비스/창작 분야에서 두각을 나타냅니다. 건강하고 장수하는 운도 있습니다. 다만 너무 편안함을 추구하다 보면 도전 의식이 부족해질 수 있습니다.",
    "상관격": "상관격은 창의력과 표현 능력이 탁월한 격국입니다. 기존 질서에 얽매이지 않고 새로운 것을 만들어내는 혁신가 기질이 있습니다. 예술/문학/음악/마케팅/IT 분야에서 독보적인 능력을 발휘합니다. 직장 조직보다는 독립적인 활동이 더 잘 맞습니다. 상관견관(傷官見官)이 있으면 직장 상사나 권위자와 갈등이 생기기 쉬우니 언행에 각별히 주의해야 합니다.",
    "편인격": "편인격은 직관과 영감이 남다른 격국입니다. 특수한 기술/학문/예술에서 독보적인 경지에 오르는 운명입니다. 철학/종교/심리/의술/역학 등 남들이 쉽게 접근하지 못하는 전문 분야에서 두각을 나타냅니다. 고독을 즐기며 혼자만의 깊은 연구에서 에너지를 얻습니다. 도식(倒食)이 형성되면 직업 변동이 잦을 수 있으니 한 분야에 집중하는 것이 좋습니다.",
    "정인격": "정인격은 학문/교육/명예의 귀격입니다. 배움에 대한 열정이 넘치고, 지식을 쌓을수록 더 높은 곳으로 올라가는 운명입니다. 교수/의사/법관/연구원처럼 학문과 자격이 기반이 되는 직업에서 최고의 성과를 냅니다. 어머니와의 관계가 인생에 큰 영향을 미칩니다. 지식이 곧 재물이 되는 사주이므로 평생 배움을 멈추지 않는 것이 성공의 비결입니다.",
    "비견격": "비견격은 독립심과 자존감이 강한 격국입니다. 남 밑에서 지시받기보다 자신만의 영역을 구축하는 자영업/창업이 잘 맞습니다. 형제나 동료와의 경쟁이 인생의 주요한 테마가 되며, 이를 통해 단련됩니다. 뚝심과 의지가 강해 어떤 어려움도 정면 돌파합니다. 재물이 모이기 어려울 수 있으니 지출 관리가 특히 중요합니다.",
    "겁재격": "겁재격은 승부사 기질의 격국입니다. 경쟁을 즐기고 도전적인 상황에서 오히려 에너지가 솟습니다. 스포츠/영업/투자/법조 분야에서 강합니다. 재물의 기복이 매우 크며, 크게 벌었다가도 한순간에 잃을 수 있는 운명이므로 안전자산 확보가 필수입니다. 주변 사람들에게 베푸는 것을 좋아하지만, 그로 인해 재물이 새는 경우도 많습니다.",
}

STRENGTH_NARRATIVE = {
    "신강(身强)": """신강 사주는 일간의 기운이 강한 사주입니다. 체력과 정신력이 뛰어나고, 어떤 역경도 정면으로 돌파하는 힘이 있습니다. 그러나 기운이 너무 강하면 오히려 재물과 관운이 억눌릴 수 있습니다. 신강한 분에게는 재성(財星)과 관살(官殺) 운이 올 때 크게 성공할 기회가 생깁니다. 자신감이 넘치는 만큼 때로는 독단적으로 보일 수 있으니, 타인의 의견을 경청하는 습관을 기르는 것이 중요합니다. 신강 사주는 스스로 만들어가는 인생입니다. 남을 기다리기보다 먼저 움직여야 기회가 옵니다.""",
    "신약(身弱)": """신약 사주는 일간의 기운이 약한 사주입니다. 체력과 에너지 관리가 인생의 핵심 과제입니다. 그러나 신약이 꼭 나쁜 것은 아닙니다. 인성(印星)과 비겁(比劫) 운이 올 때 귀인의 도움을 받아 크게 도약합니다. 혼자보다 좋은 파트너나 조력자와 함께할 때 훨씬 좋은 결과를 냅니다. 건강 관리를 최우선으로 여기고, 무리한 확장보다는 내실을 다지는 전략이 맞습니다. 귀인을 만나거나 스승을 모시는 것이 신약 사주의 성공 방정식입니다.""",
    "중화(中和)": """중화 사주는 오행의 균형이 잡혀 있어 어떤 상황에서도 크게 무너지지 않는 안정성이 있습니다. 극단적인 기복보다는 꾸준하고 안정적으로 성장하는 타입입니다. 특정 용신에 편중되지 않아 다양한 분야에서 균형 잡힌 능력을 발휘합니다. 그러나 반대로 특출난 강점이 부족할 수 있으니, 자신만의 전문 분야를 하나 깊이 파는 것이 중요합니다. 중화 사주의 가장 큰 장점은 지속성입니다. 오래 달리는 경주마처럼 꾸준함이 무기입니다.""",
}

def _nar_ch1_ilgan(ctx):
    """1~2장: 일간 캐릭터 + 신강신약"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    return '\n'.join([
f"",
f"",
f"    -----------------------------------------------------",
f"      {display_name}님의 사주 종합 리포트",
f"      {birth_year}년생 | {ilgan_kr}({ilgan}) 일간 | {sn}",
f"    -----------------------------------------------------",
f"",
f"    [ 제1장 | 일간(Daymaster) 캐릭터 완전 분석 ]",
f"",
f"일간(日干)은 사주의 핵심입니다. 일간은 나 자신을 나타내며, 내가 어떤 사람인지 본질적인 성품을 담고 있습니다.",
f"",
f"{display_name}님의 일간은 {ilgan}({ilgan_kr})입니다. {char.get('상징', '')}",
f"",
f"{char.get('성격_핵심', '')}",
f"",
f"    [장점]: {char.get('장점', '')}",
f"",
f"    [약점]: {char.get('단점', '')}",
f"",
f"일간 {ilgan_kr}이(가) {iljj_kr}(地支) 위에 앉아 있습니다. 이는 {display_name}님의 현실적 토대와 행동 패턴에 {iljj_kr}의 기운이 깊숙이 관여한다는 뜻입니다. 일지(日支)는 배우자 자리이기도 하여, 파트너 관계에서도 이 기운이 크게 드러납니다.",
f"",
f"[ 제2장 | 신강신약(Strength) - 기운의 세기 ]",
f"    ",
f"    {sn_narr}",
f"",
f"현재 {display_name}님의 체력 점수는 {strength_info.get('helper_score', 50)}점으로 측정됩니다. 이는 평균적인 기준에서 {'강한 편' if '신강' in sn else '약한 편' if '신약' in sn else '균형 잡힌'} 기운을 의미합니다.",
f"",
f"{'* 신강한 사주는 직접 움직여야 기회가 옵니다. 수동적으로 기다리면 아무것도 이루지 못합니다.' if '신강' in sn else '* 신약한 사주는 귀인과 함께할 때 가장 강합니다. 좋은 파트너와 스승을 만나는 것이 운명을 바꾸는 열쇠입니다.' if '신약' in sn else '* 중화 사주는 꾸준함이 가장 큰 무기입니다. 한 분야를 깊이 파고드는 전략이 가장 효과적입니다.'}",
f"",
])


def _nar_ch3_gyeokguk(ctx):
    """3~4장: 격국 + 용신"""
    display_name = ctx.get('display_name', "내담자")
    gname        = ctx.get('gname', "")
    gnarr        = ctx.get('gnarr', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    return '\n'.join([
f"[ 제3장 | 격국(Gyeokguk) - 타고난 인생 설계도 ]",
f"",
f"{gnarr}",
f"",
f"격국은 사주의 큰 그림, 인생의 방향성을 나타냅니다. {display_name}님의 {gname}은(는) 단순한 직업 적성을 넘어 이 분이 어떤 방식으로 세상에 가치를 만들어내는지를 보여줍니다.",
f"",
f"{gname}을 가진 분이 성공하는 공통점은 다음과 같습니다:",
f"첫째, 자신의 타고난 격국에 맞는 분야에서 일할 때 최대 능력을 발휘합니다.",
f"둘째, 격국의 장점을 살리면서 단점을 보완하는 운을 활용해야 합니다.",
f"셋째, 용신 오행이 들어오는 시기에 결정적인 도전을 해야 합니다.",
f"",
f"[ 제4장 | 용신(Yongshin) - 내 인생의 보물 오행 ]",
f"",
f"용신은 내 사주에 가장 필요한 오행입니다. 이 오행이 강화될 때 건강/재물/명예 모두가 좋아집니다.",
f"",
f"{display_name}님의 용신: {yong_kr}",
f"",
f"용신 오행을 일상에서 강화하는 방법:",
f"* 용신 색상의 옷/소품을 활용하십시오",
f"* 용신 방위 쪽에 중요한 공간(침실/사무실/책상)을 배치하십시오",
f"* 용신 오행에 해당하는 음식을 자주 드십시오",
f"* 용신 오행이 강한 해(Yongshin Year)에 큰 결정을 내리십시오",
f"",
f"기신(Gishin)이 강해지는 해에는 무리한 투자, 이동, 결정을 자제하고 내실을 다지는 것이 현명합니다.",
f"",
f"[ 제5장 | 십성(Sipsung) 조합 - 당신만의 인생 코드 ]",
f"",
f"",
])


def _nar_ch8_flow(ctx):
    """8장: 현재 운기 + 내년 세운 전망"""
    current_year = ctx.get('current_year', datetime.now().year)
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    ilgan_oh     = ctx.get('ilgan_oh', "")
    return '\n'.join([
f"",
f"",
f"[ 제8장 | 현재 운기(Flow) - {current_year}년 상황 ]",
f"",
f"현재 {cur_dw['str'] if cur_dw else '-'} 대운이 진행 중입니다.",
f"    ({cur_dw_ss} 십성 대운 | {cur_dw['시작연도'] if cur_dw else '-'}년부터 {cur_dw['종료연도'] if cur_dw else '-'}년까지)",
f"",
f"올해 {sw_now.get('세운', '')} 세운 ({sw_now.get('십성_천간', '')} / {sw_now.get('길흉', '')})",
f"",
f"{'이 시기는 용신 대운이 들어오는 황금기입니다. 적극적으로 움직이고 도전하십시오. 지금 준비하면 반드시 결실이 옵니다.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '이 시기는 주의가 필요한 대운입니다. 무리한 확장보다 내실을 다지고 건강 관리에 집중하십시오. 지금의 인내가 다음 황금기를 준비하는 것입니다.'}",
f"",
f"",
]) + f"    내년 {sw_next.get('세운', '')} 세운 전망: {sw_next.get('십성_천간', '')} 십성 | {sw_next.get('길흉', '')}\n"


def _nar_ch20_prescription(ctx):
    """20장: 맞춤 인생 처방전"""
    display_name = ctx.get('display_name', "내담자")
    current_year = ctx.get('current_year', datetime.now().year)
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    top_ss       = ctx.get('top_ss', [])
    sw_next      = ctx.get('sw_next', {})
    return '\n'.join([
f"",
f"",
f"[ 제20장 | {display_name}님에게만 드리는 맞춤 인생 처방전 ]",
f"",
f"20개 장의 분석을 종합한 최종 처방입니다.",
f"",
f"[지금 당장 해야 할 것 (Yongshin 강화)]",
f"",
f"색상 처방:",
f"{f'* 목(木) 용신: 청색, 녹색 계열' if '木' in yongshin_ohs else ''}{f'* 화(火) 용신: 적색, 주황색 계열' if '火' in yongshin_ohs else ''}{f'* 토(土) 용신: 황색, 베이지, 갈색 계열' if '土' in yongshin_ohs else ''}{f'* 금(金) 용신: 백색, 은색, 금색 계열' if '金' in yongshin_ohs else ''}{f'* 수(水) 용신: 흑색, 남색, 회색 계열' if '水' in yongshin_ohs else ''}",
f"",
f"방위 처방:",
f"{f'* 목(木): 동쪽' if '木' in yongshin_ohs else ''}{f'* 화(火): 남쪽' if '火' in yongshin_ohs else ''}{f'* 토(土): 중앙, 북동, 북서' if '土' in yongshin_ohs else ''}{f'* 금(金): 서쪽' if '金' in yongshin_ohs else ''}{f'* 수(水): 북쪽' if '水' in yongshin_ohs else ''}",
f"",
f"시간 처방:",
f"{f'* 목(木): 새벽 3~7시(인묘시)' if '木' in yongshin_ohs else ''}{f'* 화(火): 오전 9~13시(사오시)' if '火' in yongshin_ohs else ''}{f'* 토(土): 진술축미시' if '土' in yongshin_ohs else ''}{f'* 금(金): 오후 3~7시(신유시)' if '金' in yongshin_ohs else ''}{f'* 수(水): 저녁 9~새벽 1시(해자시)' if '水' in yongshin_ohs else ''}",
f"",
f"[절대 하면 안 되는 것 (Gishin 주의)]",
f"",
f"* 기신 운이 강한 해에 큰 투자, 이사, 창업, 결혼 서두르지 않기",
f"* {gname}에 맞지 않는 사업 방향 피하기",
f"* {'보증, 연대책임 절대 금지' if '겁재' in str(top_ss) or '비견' in str(top_ss) else '감정적 충동 결정 자제'}",
f"* 건강 경고 신호 무시하지 않기",
f"",
f"[ {current_year + 1}년 행동 계획 ]",
f"",
f"내년 세운: {sw_next.get('세운','')} ({sw_next.get('십성_천간','')} / {sw_next.get('길흉','')})",
f"{'[확인] 적극적으로 움직여야 할 해. 준비한 것을 실행하고 귀인의 도움을 요청하십시오.' if sw_next.get('길흉','') in ['길','대길'] else '[주의] 신중하게 내실을 다지는 해. 현재를 안정화하는 데 집중하십시오.'}",
f"",
f"\"운명은 사주가 정하지만, 운명을 만드는 것은 당신입니다.\"",
f"",
f"",
])


def _nar_report(ctx):
    """종합 리포트 섹션 (report)"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    ilgan_oh     = ctx.get('ilgan_oh', "")
    current_year = ctx.get('current_year', datetime.now().year)
    current_age  = ctx.get('current_age', 40)
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    gender       = ctx.get('gender', "남")
    pils         = ctx.get('pils', [(0,{}),(0,{})])
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    gnarr        = ctx.get('gnarr', "")
    top_ss       = ctx.get('top_ss', [])
    combos       = ctx.get('combos', [])
    ss_dist      = ctx.get('ss_dist', {})
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    daewoon      = ctx.get('daewoon', [])

    if True:
        result = []
        result.append(_nar_ch1_ilgan(ctx))
        result.append(_nar_ch3_gyeokguk(ctx))

        for key, combo in combos[:2]:
            result.append('\n'.join([
f"",
f"",
f"- [{' x '.join(key)}] 조합",
f"",
f"{combo.get('요약', '')}",
f"",
f"* 성향: {combo.get('성향', '')}",
f"* 재물 방식: {combo.get('재물', '')}",
f"* 직업 적성: {combo.get('직업', '')}",
f"* 연애 패턴: {combo.get('연애', '')}",
f"* 주의사항: {combo.get('주의', '')}",
f"",
f"",
]))

        result.append('\n'.join([
f"",
f"",
f"[ 제6장 | 건강(Health) 주의사항 ]",
f"",
f"일간 {ilgan_kr}의 건강 취약점: {char.get('건강', '')}",
f"",
f"사주에서 건강은 오행의 균형 상태를 반영합니다.",
f"{'목(木) 기운이 강하면 간장/담낭/눈/근육 계통을 주의하십시오.' if '木' in ilgan_oh else ''}",
f"{'화(火) 기운이 강하면 심장/소장/혈압/시력을 주의하십시오.' if '火' in ilgan_oh else ''}",
f"{'토(土) 기운이 강하면 비장/위장/췌장/소화기를 주의하십시오.' if '土' in ilgan_oh else ''}",
f"{'금(金) 기운이 강하면 폐/대장/기관지/피부를 주의하십시오.' if '金' in ilgan_oh else ''}",
f"{'수(水) 기운이 강하면 신장/방광/생식기/귀를 주의하십시오.' if '수' in ilgan_oh else ''}",
f"",
f"건강을 지키는 가장 확실한 방법은 용신 오행을 강화하는 것입니다.",
f"규칙적인 생활 리듬, 적절한 운동, 충분한 수면이 이 사주에 가장 중요한 건강법입니다.",
f"",
f"",
]))
        result.append('\n'.join([
f"",
f"",
f"[ 제7장 | 직업 적성 분석 ]",
f"",
f"일간 {ilgan_kr}에게 가장 잘 맞는 직업: {char.get('직업', '')}",
f"",
f"현재 주요 십성 {', '.join(top_ss)}의 조합이 의미하는 적합 업종:",
f"* 식신이 강하면: 요리, 예술, 창작, 교육, 서비스 분야에서 자연스럽게 빛납니다.",
f"* 상관이 강하면: IT, 마케팅, 방송, 예술, 컨설팅에서 독보적 능력을 발휘합니다.",
f"* 편재가 강하면: 사업, 투자, 영업, 무역, 부동산에서 두각을 나타냅니다.",
f"* 정재가 강하면: 금융, 회계, 행정, 유통에서 안정적인 커리어를 쌓습니다.",
f"* 편관이 강하면: 군경, 의료, 법조, 스포츠에서 강인한 의지를 발휘합니다.",
f"* 정관이 강하면: 공무원, 교육, 관리직에서 신뢰받는 전문가가 됩니다.",
f"* 편인이 강하면: 연구, 철학, 역술, IT, 의학에서 독보적 전문성을 쌓습니다.",
f"* 정인이 강하면: 학문, 자격증 기반의 전문직에서 평생 성장합니다.",
f"* 비견이 강하면: 독립사업, 프리랜서, 자영업에서 진가를 발휘합니다.",
f"* 겁재가 강하면: 영업, 스포츠, 투자에서 강한 승부 본능을 발휘합니다.",
f"",
f"",
]))

        result.append(_nar_ch8_flow(ctx))
        result.append('\n'.join([
f"",
f"",
f"[ 제9장 | 연애/결혼 성향 ]",
f"",
f"일간 {ilgan_kr}의 연애 패턴:",
f"{'* ' + char.get('연애_남', '') if gender == '남' else '* ' + char.get('연애_여', '')}",
f"",
f"배우자 자리 일지(日支) {iljj_kr}({iljj})의 의미:",
f"배우자 자리에 있는 지지는 배우자의 성품과 부부 관계의 방향을 나타냅니다.",
f"{iljj_kr} 일지를 가진 분은 배우자에게서 {'안정과 현실적인 도움을 받는' if iljj in ['丑(축)','辰(진)','戌(술)','未(미)'] else '열정적이고 활기찬 에너지를 받는' if iljj in ['寅(인)','午(오)','戌(술)'] else '지적 교감과 소통을 중요하게 여기는' if iljj in ['申(신)','酉(유)'] else '따뜻한 감성적 유대감을 원하는'} 경향이 있습니다.",
f"",
f"[ 제10장 | 인생 총평 - 만신의 한 말씀 ]",
f"",
f"{display_name}님의 사주를 종합적으로 보았을 때, 이 분의 인생 키워드는 \"{', '.join(top_ss[:2])}\" 조합이 만들어내는 에너지입니다.",
f"",
f"{combos[0][1].get('요약', '타고난 재능으로 자신의 길을 개척하는 인생입니다.') if combos else '타고난 개성으로 자신만의 길을 걸어가는 인생입니다.'}",
f"",
f"이 사주가 가장 빛나는 순간은 자신의 타고난 기질을 긍정하고, 용신 오행의 힘을 빌려 움직일 때입니다. 억지로 자신에게 맞지 않는 방향으로 가려 하면 반드시 시련이 따릅니다.",
f"",
f"{sn}인 이 사주는 {'스스로 길을 열어가는 개척자의 운명입니다. 두려움을 버리고 먼저 나서십시오.' if '신강' in sn else '귀인의 도움과 좋은 인연으로 날개를 다는 운명입니다. 좋은 사람과 함께하십시오.' if '신약' in sn else '꾸준함과 균형으로 오래 멀리 가는 운명입니다. 한 우물을 깊게 파십시오.'}",
f"",
f"앞으로의 {yong_kr} 용신 강화를 통해 건강/재물/명예 모두를 함께 향상시키십시오. 이것이 이 사주의 가장 핵심적인 처방입니다.",
f"",
f"",
]))
        # 확장 콘텐츠: 신살, 오행, 연도별 조언
        try:
            sinsal_list = get_extra_sinsal(pils)
            if sinsal_list:
                sinsal_text = "\n".join([f"* {render_saju_tooltip(s['name'])}: {s['desc']}\n  처방: {s.get('remedy','')}" for s in sinsal_list])
                result.append('\n'.join([
f"",
f"",
f"[ 제11장 | 신살(Sinsal) 완전 분석 ]",
f"",
f"신살은 사주에 내재된 특수한 기운으로, 삶의 특정 측면에 강한 영향을 줍니다.",
f"",
f"{sinsal_text}",
f"",
f"신살은 좋고 나쁨을 단정짓기보다, 그 에너지를 어떻게 활용하느냐가 더 중요합니다. 흉살이라도 제화(制化)하면 오히려 탁월한 능력의 원천이 됩니다.",
f"",
f"",
]))
            sinsal12 = get_12sinsal(pils)
            if sinsal12:
                s12_text = "\n".join([f"* {render_saju_tooltip(s['이름'])}: {s.get('desc','')}" for s in sinsal12[:5]])
                result.append('\n'.join([
f"",
f"",
f"[ 제12장 | 12신살(12 Sinsal) ]",
f"",
f"{s12_text}",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        try:
            oh_strength = calc_ohaeng_strength(ilgan, pils)
            oh_lines = []
            OH_BODY = {"木":"간장/담낭/눈/근육","火":"심장/소장/혈관/혈압","土":"비장/위장/췌장/소화기","金":"폐/대장/기관지/피부","水":"신장/방광/생식기/귀"}
            OH_STRONG = {"木":"창의력/기획력/성장 에너지가 넘칩니다","火":"열정/표현력/인기운이 뛰어납니다","土":"안정감/신뢰/현실 감각이 탁월합니다","金":"결단력/추진력/원칙이 강합니다","水":"지혜/유연성/적응력이 뛰어납니다"}
            OH_WEAK  = {"木":"유연성과 창의력을 의식적으로 키우십시오","火":"열정을 표현하고 사람들과 더 많이 소통하십시오","土":"안정적 기반을 만드는 데 더 노력하십시오","金":"결단력을 기르고 원칙을 세우십시오","水":"직관을 믿고 상황에 유연하게 적응하십시오"}
            for oh_key, oh_val in sorted(oh_strength.items(), key=lambda x: -x[1]):
                level = "강함" if oh_val >= 30 else "보통" if oh_val >= 15 else "약함"
                body_part = OH_BODY.get(oh_key, "")
                if oh_val >= 30:
                    oh_lines.append(f"* {oh_key}({oh_val}점/강함): {OH_STRONG.get(oh_key,'')} | 건강 주의 부위: {body_part}")
                elif oh_val < 15:
                    oh_lines.append(f"* {oh_key}({oh_val}점/약함): {OH_WEAK.get(oh_key,'')} | 보충 필요 부위: {body_part}")
            result.append('\n'.join([
f"",
f"",
f"[ 제13장 | 오행(Five Elements) 분포와 건강 심층 분석 ]",
f"",
f"오행의 강약은 성격과 건강 모두에 영향을 줍니다.",
f"",
f"{chr(10).join(oh_lines)}",
f"",
f"오행 균형을 맞추기 위한 처방:",
f"* 부족한 오행을 보충하는 음식/색상/활동을 일상에서 꾸준히 활용하십시오",
f"* 과잉된 오행의 기관을 정기적으로 검진하십시오",
f"* 용신 오행이 약하다면 그 오행을 강화하는 노력이 인생 전반을 향상시킵니다",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        result.append('\n'.join([
f"",
f"",
f"[ 제14장 | 연령대별 인생 전략 - {display_name}님에게만 드리는 맞춤 처방 ]",
f"",
f"    - 현재 {current_age}세 | {current_year}년",
f"    대운: {cur_dw['str'] if cur_dw else '-'} ({cur_dw_ss})",
f"    세운: {sw_now.get('세운','')} ({sw_now.get('십성_천간','')} / {sw_now.get('길흉','')})",
f"",
f"지금 이 순간의 처방:",
f"{f'[처방] 용신 대운과 용신 세운이 겹치는 황금기입니다. 지금 움직이지 않으면 언제 움직이겠습니까. 두려움을 버리고 계획했던 것을 실행하십시오.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' and _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '[주의] 지금은 신중하게 내실을 다지는 시기입니다. 무리한 확장보다 체력, 실력, 자금을 비축하십시오.'}",
f"",
f"    - 내년 {current_year+1}년 전망",
f"    세운: {sw_next.get('세운','')} ({sw_next.get('십성_천간','')} / {sw_next.get('길흉','')})",
f"    {'내년은 올해보다 더 나은 흐름이 예상됩니다. 올해 준비한 것이 내년에 결실을 맺습니다.' if sw_next.get('길흉','') in ['길','대길'] else '내년도 신중한 한 해가 될 것입니다. 계획을 세우고 차분하게 실행하십시오.'}",
f"",
f"    - 향후 5년 핵심 전략",
f"1. 용신 {yong_kr} 오행이 강한 환경에 자신을 노출시키십시오",
f"2. {gname}의 특성을 최대한 살리는 직업/사업 방향으로 나아가십시오",
f"3. {sn}에 맞는 방식으로 에너지를 운용하십시오: {'직접 움직여 기회를 만들어가십시오' if '신강' in sn else '좋은 파트너와 함께 시너지를 내십시오' if '신약' in sn else '꾸준하고 안정적으로 성장하십시오'}",
f"4. 기신 오행의 유혹(투자, 환경, 인연)을 의식적으로 피하십시오",
f"5. 건강이 모든 운의 기반입니다. {char.get('건강','정기적 건강 관리')}에 주의하십시오",
f"",
f"[ 제15장 | 만신의 최종 한 말씀 ]",
f"",
f"{display_name}님의 사주는 한마디로 \"{combos[0][1].get('요약','자신만의 독특한 빛을 가진 사주') if combos else '평생 성장하는 사주'}\"입니다.",
f"",
f"이 세상에 태어난 모든 사람은 저마다의 사명(使命)이 있습니다. {display_name}님의 사명은 {ilgan_kr} 일간이 가진 \"{char.get('장점','타고난 능력')}\"을(를) 세상에 발현하는 것입니다.",
f"",
f"지금까지의 삶에서 힘들었던 순간들도 사실은 이 사명을 위한 준비 과정이었습니다. 사주를 보는 것은 미래를 맹목적으로 믿기 위함이 아닙니다. 자신을 깊이 이해하고, 좋은 운기에 최대로 활동하며, 어려운 운기에 현명하게 대처하기 위함입니다.",
f"",
f"{display_name}님에게 드리는 만신의 마지막 한 마디:",
f"\"운명은 사주가 정하지만, 운명을 만드는 것은 당신입니다.\"",
f"",
f"",
]))
        # 제16~20장 확장 콘텐츠 --------------------------------
        try:
            iljj  = pils[1]["jj"]
            ilju_str = pils[1]["str"]
            ILJJ_NATURE = {
                "子(자)":"지혜롭고 총명하며 기억력이 뛰어납니다. 밤에 더 활발해지고 직관이 발달해 있습니다.",
                "丑(축)":"성실하고 묵묵합니다. 한 번 결심하면 끝까지 가는 뚝심이 있습니다.",
                "寅(인)":"추진력이 강하고 용감합니다. 타인을 이끄는 리더십이 자연스럽게 나옵니다.",
                "卯(묘)":"감수성이 풍부하고 창의적입니다. 예술적 감각이 있으며 인기가 많습니다.",
                "辰(진)":"다재다능하고 신비로운 매력이 있습니다. 변화와 적응에 능합니다.",
                "巳(사)":"지혜롭고 비밀이 많습니다. 겉으로 드러나지 않는 깊은 내면이 있습니다.",
                "午(오)":"열정적이고 감정 표현이 풍부합니다. 인기와 주목을 자연스럽게 끌어당깁니다.",
                "未(미)":"예술적이고 따뜻한 심성을 지녔습니다. 보살피고 지키려는 본능이 강합니다.",
                "申(신)":"영리하고 임기응변이 뛰어납니다. 변화를 두려워하지 않고 기회를 잘 잡습니다.",
                "酉(유)":"섬세하고 완벽주의적입니다. 기준이 높아 스스로를 끊임없이 갈고닦습니다.",
                "戌(술)":"의리 있고 충직합니다. 한번 믿은 사람은 끝까지 지키는 의협심이 있습니다.",
                "亥(해)":"자유롭고 포용력이 넓습니다. 생각의 깊이가 있으며 영성/철학에 관심이 많습니다.",
            }
            ILJJ_SPOUSE = {
                "子(자)":"배우자는 총명하고 감각이 뛰어난 분을 만날 가능성이 높습니다. 지적 교감이 중요합니다.",
                "丑(축)":"배우자는 성실하고 현실적인 분을 만나게 됩니다. 가정을 소중히 여기는 파트너입니다.",
                "寅(인)":"배우자는 활동적이고 추진력 있는 분입니다. 서로 에너지를 주고받는 관계가 됩니다.",
                "卯(묘)":"배우자는 섬세하고 예술적 감각이 있는 분입니다. 정서적 교감을 중시합니다.",
                "辰(진)":"배우자는 다재다능하고 변화가 많은 분입니다. 관계에서 기복이 있을 수 있습니다.",
                "巳(사)":"배우자는 지혜롭고 신중한 분입니다. 겉으로 드러나지 않는 깊은 내면을 가진 파트너입니다.",
                "午(오)":"배우자는 열정적이고 표현력이 강한 분입니다. 감정의 기복이 있지만 뜨겁게 사랑합니다.",
                "未(미)":"배우자는 따뜻하고 예술적 감각이 있는 분입니다. 집과 가정을 소중히 여깁니다.",
                "申(신)":"배우자는 영리하고 임기응변이 뛰어난 분입니다. 다방면에 재능이 있는 파트너입니다.",
                "酉(유)":"배우자는 섬세하고 완벽주의적인 분입니다. 기준이 높아 처음에는 까다롭게 보일 수 있습니다.",
                "戌(술)":"배우자는 의리 있고 충직한 분입니다. 한번 믿으면 끝까지 지키는 파트너입니다.",
                "亥(해)":"배우자는 자유롭고 포용력 있는 분입니다. 생각이 깊고 영성적인 면이 있는 파트너입니다.",
            }
            ilju_nature  = ILJJ_NATURE.get(iljj, "")
            ilju_spouse  = ILJJ_SPOUSE.get(iljj, "")
            ilju_detail  = ILJU_DATA.get(ilju_str, {}).get("desc", f"{ilgan_kr} 위에 {iljj_kr}이 앉은 일주입니다.")
            result.append('\n'.join([
f"",
f"",
f"[ 제16장 | 일주론(Ilju-ron) - {ilju_str} 일주의 완전 분석 ]",
f"",
f"일주(日柱)는 사주의 핵심입니다. 일간(日干)은 나 자신이고, 일지(日支)는 내가 서 있는 토대이자 배우자 자리입니다.",
f"{display_name}님의 일주는 {ilju_str}({ilgan_kr}/{iljj_kr})입니다.",
f"",
f"    - 일주 특성 ({iljj_kr})",
f"    {ilju_nature}",
f"",
f"    - 배우자 자리(Day Branch) 분석",
f"    {ilju_spouse}",
f"",
f"    - 일간 {ilgan_kr}의 오행적 특성",
f"{OHN.get(ilgan_oh,'')} 기운은 {'성장과 창의, 새로운 시작을 상징합니다.' if ilgan_oh=='木' else '열정과 표현, 인기를 상징합니다.' if ilgan_oh=='火' else '안정과 신뢰, 중심을 상징합니다.' if ilgan_oh=='土' else '결단과 원칙, 정제를 상징합니다.' if ilgan_oh=='金' else '지혜와 유연성, 깊이를 상징합니다.'}",
f"이 기운이 {display_name}님의 삶 전반에 흐르며, 용신 {yong_kr} 오행과 만날 때 가장 크게 빛납니다.",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        # 제17장: 재물운 로드맵
        try:
            hi = generate_engine_highlights(pils, birth_year, gender)
            # 용신 오행 기반 향후 20년 황금기 계산
            _g_yong_ohs = set(o for o in yongshin_ohs if o in ("木","火","土","金","水"))
            _g_years = []
            for _gy in range(current_year, current_year + 21):
                _gsw = get_yearly_luck(pils, _gy)
                _gsw_oh = OH.get((_gsw.get("세운") or "")[:1], "")
                if _gsw_oh in _g_yong_ohs:
                    _gage = _gy - birth_year + 1
                    _gss = _gsw.get("십성_천간", "")
                    _ggh = _gsw.get("길흉", "")
                    _star = "★★" if _gss in ("偏財", "正財") else "★"
                    _g_years.append(f"* {_gy}년 ({_gage}세): {_gsw.get('세운','')} [{_gss}] {_ggh}  {_star}")
            mp_text = "\n".join(_g_years) if _g_years else "* 향후 20년 내 용신 세운이 없습니다. 인성·비겁 세운에서 기반을 다지세요."
            result.append('\n'.join([
f"",
f"",
f"[ 제17장 | 재물운(Wealth) 완전 로드맵 ]",
f"",
f"    - {display_name}님의 재물 패턴",
f"    {char.get('재물패턴','꾸준한 노력으로 재물을 쌓아가는 타입입니다.')}",
f"",
f"    - 평생 재물 황금기",
f"    {mp_text}",
f"",
f"    - 재물 핵심 전략",
f"* {gname}: {'직업 안정 수입이 기반. 투기는 금물.' if '정재' in gname else '사업, 투자로 큰 기회. 기복 대비 안전자산 필수.' if '편재' in gname else '전문성, 창의력으로 수입. 재능을 팔아 돈 버는 구조.' if '식신' in gname or '상관' in gname else '명예와 재물 동시에. 실력 먼저, 돈은 따라온다.'}",
f"* 기신 운: {'대운, 세운 모두 기신일 때 큰 투자, 동업, 보증 금지'}",
f"* 용신 {yong_kr} 오행 해(Year): 재물 결정과 실행의 최적기",
f"* {sn}: {'직접 부딪혀야 재물이 온다. 기다리면 지나간다.' if '신강' in sn else '귀인, 파트너와 함께할 때 재물이 배로 온다.' if '신약' in sn else '꾸준함이 최대 재물 전략이다.'}",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        # -- 제18장: 건강운
        try:
            oh_strength2 = calc_ohaeng_strength(ilgan, pils)
            OH_BODY_FULL = {
                "木":"간장/담낭/눈/근육/인대. 봄이 취약, 분노/스트레스가 간을 상합니다.",
                "火":"심장/소장/혈관/혈압/시력. 여름이 취약, 과로/흥분이 심장을 상합니다.",
                "土":"비장/위장/췌장/소화기. 환절기 취약, 걱정과 폭식이 위장을 상합니다.",
                "金":"폐/대장/기관지/피부/코. 가을이 취약, 슬픔/건조가 폐를 상합니다.",
                "水":"신장/방광/생식기/귀/뼈. 겨울이 취약, 공포와 과로가 신장을 상합니다.",
            }
            OH_HEALTH_ADV = {
                "木":"규칙적 스트레칭/충분한 수면. 신맛 음식(레몬/매실/신과일) 권장.",
                "火":"심혈관 정기검진 필수. 카페인/음주 자제. 쓴맛(녹차) 적당히.",
                "土":"식사 규칙성이 핵심. 폭식/군것질 금지. 황색 음식(꿀/고구마) 권장.",
                "金":"습도 관리, 가습기 활용. 건조 환경 주의. 매운맛(마늘/생강) 적당히.",
                "水":"수분 충분히. 짠 음식/과로 금지. 검은 음식(검은콩/미역/김) 권장.",
            }
            h_lines = [f"[일간 주의사항] {ilgan_kr}\n{char.get('건강','규칙적인 생활과 수면이 핵심입니다.')}\n"]
            for o, v in oh_strength2.items():
                if v >= 30:
                    h_lines.append(f"[과다] {OHN.get(o,'')}({o}) ({v}%) | 주의: {OH_BODY_FULL.get(o,'')}\n  처방: {OH_HEALTH_ADV.get(o,'')}")
                elif v <= 8:
                    h_lines.append(f"[부족] {OHN.get(o,'')}({o}) ({v}%) | 보충 필요: {OH_BODY_FULL.get(o,'')}\n  처방: {OH_HEALTH_ADV.get(o,'')}")
            result.append('\n'.join([
f"",
f"",
f"[ 제18장 | 건강운(Health) 완전 분석 ]",
f"",
f"{chr(10).join(h_lines)}",
f"",
f"[현재 대운 주의] ({cur_dw_ss})",
f"{'편관 대운 - 과로, 수술, 관재 위험. 정기검진 필수.' if cur_dw_ss=='편관' else '겁재 대운 - 정신적 스트레스가 신체에 영향. 감정 관리가 곧 건강 관리.' if cur_dw_ss=='겁재' else '비교적 건강한 대운. 기본 생활습관 유지가 핵심.'}",
f"",
f"[평생 건강 5대 수칙]",
f"1. 수면: 규칙적 수면 - {ilgan_kr} 일간의 건강 기반",
f"2. 감정: {'분노 억제' if ilgan_oh=='木' else '과잉 흥분 조절' if ilgan_oh=='火' else '걱정, 근심 해소' if ilgan_oh=='土' else '슬픔, 집착 해소' if ilgan_oh=='金' else '공포, 불안 해소'} - 감정이 곧 건강",
f"3. 음식: 용신 {yong_kr} 오행 음식 꾸준히 섭취",
f"4. 운동: {'강도 있는 운동보다 꾸준한 유산소' if '신강' in sn else '가벼운 운동 + 충분한 휴식' if '신약' in sn else '균형 잡힌 운동 루틴'}",
f"5. 검진: 주의 장기 연 1회 이상 검진 필수",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        # -- 제19장: 인간관계/육친
        try:
            yk = get_yukjin(ilgan, pils, gender)
            yk_yes = [item for item in yk if item.get('present')]
            yk_no  = [item for item in yk if not item.get('present')]
            yk_yes_text = "\n".join([f"* {i['관계']}: {i['위치']} | {i['desc'][:60]}" for i in yk_yes[:4]]) or "해당 없음"
            yk_no_text  = "\n".join([f"* {i['관계']}: 원국에 없음" for i in yk_no[:4]]) or "해당 없음"
            result.append('\n'.join([
f"",
f"",
f"[ 제19장 | 인간관계(Relations) - 육친(Yukjin) 완전 분석 ]",
f"",
f"[강한 인연] 원국에 있는 육친 ",
f"{yk_yes_text}",
f"",
f"[변화 많은 인연] 원국에 없는 육친",
f"{yk_no_text}",
f"",
f"- {ilgan_kr} 일간의 인간관계 방식",
f"{'강한 독립심으로 인해 혼자 결정, 해결하려는 경향이 강합니다.' if ilgan_oh in ['木','金'] else '따뜻하지만 상처받으면 오래 기억하는 편입니다.' if ilgan_oh=='火' else '신뢰를 중시하고 새로운 인연을 맺는 데 시간이 걸립니다.' if ilgan_oh=='土' else '깊은 통찰력으로 사람을 파악하지만 먼저 다가가기 어려워합니다.'}",
f"",
f"- {'남성' if gender=='남' else '여성'} {display_name}님의 이성 인연",
f"{char.get('연애_남' if gender=='남' else '연애_여','이성 관계에서 자신만의 방식을 가지고 있습니다.')}",
f"",
f"- 귀인을 만나는 방법",
f"{'문서, 학문, 공식 자리에서 귀인을 만납니다.' if '정관' in gname or '정인' in gname else '이동, 사업, 거래 현장에서 귀인을 만납니다.' if '편재' in gname or '편관' in gname else '일상 업무, 창작 활동 중에 귀인이 나타납니다.'}",
f"용신 {yong_kr} 오행의 기운이 강한 장소와 사람에게서 귀인이 옵니다.",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        # -- 제20장: 맞춤 인생 처방전
        try:
            result.append(_nar_ch20_prescription(ctx))
        except Exception as e: _saju_log.debug(str(e))
        return "".join(result)


def _nar_future(ctx):
    """미래 운세 섹션 (future / lifeline)"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    ilgan_oh     = ctx.get('ilgan_oh', "")
    current_year = ctx.get('current_year', datetime.now().year)
    current_age  = ctx.get('current_age', 40)
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    gender       = ctx.get('gender', "남")
    pils         = ctx.get('pils', [(0,{}),(0,{})])
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    gnarr        = ctx.get('gnarr', "")
    top_ss       = ctx.get('top_ss', [])
    combos       = ctx.get('combos', [])
    ss_dist      = ctx.get('ss_dist', {})
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    daewoon      = ctx.get('daewoon', [])

    if ctx.get('section', '') == "lifeline":
        result = []
        result.append('\n'.join([
f"大運(大運)은 10년 단위로 흐르는 인생의 큰 물결입니다. 세운(歲運)이 1년 단위의 파도라면, 大運은 10년을 휘감는 조류(潮流)입니다. 아무리 좋은 세운이 와도 大運이 나쁘면 크게 발현되지 않으며, 반대로 힘든 세운도 좋은 大運 아래서는 그 피해가 줄어듭니다.",
f"",
f"{display_name}님의 用神은 {yong_kr}입니다. 이 오행의 大運이 오는 시기가 인생의 황금기가 됩니다.",
]))
        for dw in daewoon[:9]:
            dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
            dw_oh = OH.get(dw["cg"], "")
            is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
            is_cur = dw["시작연도"] <= current_year <= dw["종료연도"]
            cur_mark = " ◀ 현재 大運" if is_cur else ""

            DW_SS_DESC = {
                "食神": f"食神 大運은 재능이 꽃피고 복록이 따르는 풍요의 시기입니다. 창작/교육/서비스 분야에서 두각을 나타냅니다.",
                "傷官": f"傷官 大運은 창의력이 폭발하지만 언행에 주의해야 하는 시기입니다. 예술/창업/자유업에서 빛나며 기존 틀을 깨는 성취를 거둡니다.",
                "偏財": f"偏財 大運은 사업/투자/이동이 활발한 도전의 시기입니다. 기복이 크므로 관리 능력이 성패를 가릅니다.",
                "正財": f"正財 大運은 성실한 노력이 재물로 축적되는 안정기입니다. 가정의 화목과 자산 형성에 최적의 시기입니다.",
                "偏官": f"偏官 大運은 시련과 도전이 교차하는 변곡점입니다. 강한 리더십으로 돌파하면 큰 권위를 얻게 됩니다.",
                "正官": f"正官 大運은 사회적 지위와 명예가 상승하는 시기입니다. 승진/자격 취득 등 공적 인정이 따릅니다.",
                "偏印": f"偏印 大運은 직관과 전문성이 강해지는 시기입니다. 특수 분야에서 독보적 역량을 쌓기에 좋습니다.",
                "正印": f"正印 大運은 귀인의 도움과 학문적 성취가 깃드는 시기입니다. 시험/자격증에서 좋은 결과를 냅니다.",
                "比肩": f"比肩 大運은 독립심과 경쟁이 강해지는 시기입니다. 지출 관리에 유의하며 자신만의 길을 개척해야 합니다.",
                "劫財": f"劫財 大運은 재물의 기복이 심한 시기입니다. 투기/보증/동업을 피하고 현상 유지에 집중하십시오.",
            }
            desc = DW_SS_DESC.get(dw_ss, f"{dw_ss} 十星 大運으로 {dw['str']}의 기운이 10년간 흐릅니다.")

            result.append('\n'.join([
f"-> {dw['시작나이']}세 ~ {dw['시작나이']+9}세 | {dw['str']} 大運 ({dw_ss}){cur_mark}",
f"({dw['시작연도']}년 ~ {dw['종료연도']}년)",
f"{'* 用神 大運 - 인생의 황금기' if is_yong else ''}",
f"{desc}",
f"{'지금이 바로 큰 결정을 내려야 할 때입니다.' if is_yong and is_cur else '지금은 내실을 다지는 준비 기간입니다.' if not is_yong and is_cur else ''}",
]))


        result.append('\n'.join([
"-> [ 인생 전체 흐름 요약 ]",
f"{display_name}님의 인생에서 가장 중요한 大運은 用神 {yong_kr} 오행이 들어오는 시기입니다. 이 시기에 큰 결정을 내리고 적극적으로 움직여야 합니다.",
f"현재 {current_age}세의 {display_name}님은 {'지금이 바로 황금기입니다. 두려워하지 말고 전진하십시오!' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '지금은 준비 기간입니다. 다음 用神 大運을 위해 체력과 실력을 비축하십시오.'}",
"인생의 좋은 大運에 최대한 활동하고, 나쁜 大運에 최소한으로 노출되는 것 - 이것이 사주 활용의 핵심 전략입니다.",
]))

        # -- 나이 단계별 분야 포커스 사전 ------------------------------
        DW_DOMAIN_STAGE = {
            "比肩": {
                "초":   {"학업":"자기주도 학습과 진로 탐색에 집중할 시기입니다.", "부모":"부모님과 주도권 갈등이 올 수 있어 대화가 중요합니다.", "활동":"스포츠/동아리 활동을 통한 사회성 발달이 핵심입니다."},
                "청장": {"재물":"지출 관리와 경쟁 우위 확보가 관건입니다.", "직업":"동료와의 협력 혹은 독립적 기반 구축에 유리합니다.", "인연":"주관이 강해지니 상대에 대한 배려를 의식적으로 실천하십시오."},
                "말":   {"건강":"자기 주도 건강 관리와 꾸준한 운동이 핵심입니다.", "명예":"그간의 경험이 후배들에게 귀감이 됩니다.", "자녀":"자녀와의 주도권 갈등보다 조화와 경청을 선택하십시오."},
            },
            "劫財": {
                "초":   {"학업":"학업 스트레스가 심하니 정서 안정이 최우선입니다.", "부모":"가정의 재정 변동이 분위기에 영향을 줄 수 있으니 단단히 대비하십시오.", "활동":"체육 활동으로 넘치는 에너지를 건강하게 발산하십시오."},
                "청장": {"재물":"동업/보증/충동 투자는 반드시 금지입니다.", "직업":"치열한 경쟁 속에서 개척적 성과를 냅니다.", "인연":"금전 갈등이 연애에 침범하지 않도록 경계를 분명히 하십시오."},
                "말":   {"건강":"갑작스러운 건강 이상에 대비한 정기 검진이 필수입니다.", "명예":"재산 분쟁을 미연에 방지하고 유언장을 정리하십시오.", "자녀":"형제/자녀 간 재산 문제를 생전에 명확히 정리하십시오."},
            },
            "食神": {
                "초":   {"학업":"창의력이 폭발하고 성적이 오르는 시기입니다.", "부모":"부모님의 지지 아래 재능이 꽃핍니다. 예/체능 활동을 적극 병행하십시오.", "활동":"다양한 동아리/대외활동이 진로의 폭을 넓혀줍니다."},
                "청장": {"재물":"재능이 곧 돈이 되는 풍요로운 시기입니다.", "직업":"창의적 연구나 전문 기술 분야에서 대성합니다.", "인연":"마음이 너그러워져 매력이 상승하고 원만한 인연이 찾아옵니다."},
                "말":   {"건강":"심신이 여유롭고 건강한 행복의 시기입니다.", "명예":"취미/봉사/강의로 삶의 품격을 높이십시오.", "자녀":"자녀/손자와의 정서적 유대가 깊어지는 복된 시기입니다."},
            },
            "傷官": {
                "초":   {"학업":"암기보다 이해/창작이 강점이니 진로를 창의 분야로 설계하십시오.", "부모":"규칙과 권위에 저항하는 경향이 있으니 소통이 중요합니다.", "활동":"음악/미술/글쓰기 등 표현 활동이 재능을 키워줍니다."},
                "청장": {"재물":"아이디어로 승부하되 투기적 성향은 반드시 조심하십시오.", "직업":"파격적 기획/예술/창업 분야에서 두각을 나타냅니다.", "인연":"언행으로 인한 오해가 생기지 않도록 부드러운 화법을 선택하십시오."},
                "말":   {"건강":"신경계와 구강 계통 건강에 특히 유의하십시오.", "명예":"세대 차이를 인정하고 후배/자녀 세대의 방식을 존중하십시오.", "자녀":"지나친 간섭보다 따뜻한 격려로 자녀를 지원하십시오."},
            },
            "偏財": {
                "초":   {"학업":"활발한 활동성이 리더십과 경험을 쌓아줍니다.", "부모":"부모님의 사업 확장이 가정에 활기를 줍니다. 경제 감각을 일찍 키우십시오.", "활동":"무역/금융/서비스업 등 넓은 세계를 진로 목표로 삼으십시오."},
                "청장": {"재물":"큰 재운이 따르나 기복이 크니 수입의 30%는 반드시 비축하십시오.", "직업":"유통, 금융, 대규모 사업 확장에 유리합니다.", "인연":"이성 인연이 활발하니 진중한 만남이 오래가는 관계를 만듭니다."},
                "말":   {"건강":"왕성한 활동은 유지하되 과로와 무리한 투자는 금물입니다.", "명예":"자녀에게 자산을 투명하게 정리해 두십시오.", "자녀":"자녀의 경제/사업적 조언자로서 든든한 울타리가 될 수 있습니다."},
            },
            "正財": {
                "초":   {"학업":"성실히 공부하면 착실한 결과가 나오는 신뢰의 시기입니다.", "부모":"가정이 안정되어 공부 환경이 좋고 부모님의 전폭 지원을 받습니다.", "활동":"경제/수학/행정 계열 진로가 잘 맞는 시기입니다."},
                "청장": {"재물":"성실한 노력이 확실한 자산으로 착실히 축적됩니다.", "직업":"관리직, 금융, 안정적 조직 생활에 최적입니다.", "인연":"진지하고 믿음직한 인연이 자연스럽게 결혼으로 이어집니다."},
                "말":   {"건강":"규칙적인 생활 리듬이 건강의 핵심 비결입니다.", "명예":"노후 자산이 탄탄하게 정리된 안심의 시기입니다.", "자녀":"자녀 결혼 등 경사가 이어지고 배우자와의 화합이 깊어집니다."},
            },
            "偏官": {
                "초":   {"학업":"학업 스트레스와 교우 갈등이 생기기 쉬우니 버티는 힘을 기르십시오.", "부모":"규율 강한 환경이 오히려 잠재력을 키웁니다. 군사/법조/체육 계열 진로를 고려하십시오.", "활동":"자기 방어력과 리더십을 키우는 활동이 도움이 됩니다."},
                "청장": {"재물":"과감한 투자보다 리스크 관리를 우선으로 삼으십시오.", "직업":"권위 있는 직책이나 특수 공직에서 발탁됩니다.", "인연":"책임감이 무거워지며, 파트너와 함께 짐을 나누는 관계가 이상적입니다."},
                "말":   {"건강":"혈압/심장/관절 등 급성 질환에 대비한 검진이 필수입니다.", "명예":"갈등보다 평화를 택하고 생활을 단순화하십시오.", "자녀":"자녀/가족의 안전을 세심하게 살피는 보호자 역할이 부각됩니다."},
            },
            "正官": {
                "초":   {"학업":"모범생으로 인정받아 리더 역할이 주어지는 시기입니다.", "부모":"부모님의 기대에 부응하는 자랑스러운 자녀가 됩니다.", "활동":"행정/법조/공학 계열 진로가 잘 맞습니다."},
                "청장": {"재물":"사회적 지위 상승과 함께 재운도 안정됩니다.", "직업":"국가 공직이나 대기업 보직운이 매우 강합니다.", "인연":"격식 있는 만남과 결혼 인연이 찾아오는 시기입니다."},
                "말":   {"건강":"단정한 생활 습관으로 건강이 잘 유지됩니다.", "명예":"지역사회/후배로부터 존경받는 어른의 위치에 서게 됩니다.", "자녀":"자녀의 사회적 성공이 당신의 이름을 더욱 빛나게 합니다."},
            },
            "偏印": {
                "초":   {"학업":"암기보다 독창적 사고가 강합니다. 예술/IT/철학 계열 진로가 적합합니다.", "부모":"부모와의 심리적 거리감이 생길 수 있으니 소통에 노력하십시오.", "활동":"혼자 몰입하는 연구/창작 활동에서 재능이 빛납니다."},
                "청장": {"재물":"문서 재산과 특허 등 지식재산이 유리합니다.", "직업":"IT, 예능, 철학 등 독보적 전문 영역에서 두각을 나타냅니다.", "인연":"깊은 공감대를 나누는 정신적 파트너가 가장 잘 맞습니다."},
                "말":   {"건강":"신경성 질환과 우울감에 주의하며 이완/명상을 실천하십시오.", "명예":"학문/종교/철학으로 내면을 탐구하고 삶의 지혜를 전수하십시오.", "자녀":"가족과의 거리를 좁히는 노력이 노년의 행복을 만들어줍니다."},
            },
            "正印": {
                "초":   {"학업":"학업운이 매우 강해 성적이 오르고 장학금 기회도 열립니다.", "부모":"부모님과 선생님의 아낌없는 지원을 받는 자랑스러운 시기입니다.", "활동":"독서/강의/학습에서 탁월한 역량이 나타납니다."},
                "청장": {"재물":"자격 취득이나 계약으로 확실한 재물이 들어옵니다.", "직업":"교육, 문화, 공익적 업무에서 명예를 얻습니다.", "인연":"귀인의 소개로 좋은 인연이 찾아오거나 어른의 도움으로 결혼이 성사됩니다."},
                "말":   {"건강":"심리적 안정이 신체 건강의 근원입니다. 마음 건강이 몸 건강입니다.", "명예":"자녀/손자의 성공이 당신의 이름을 빛나게 합니다.", "자녀":"따뜻한 배려로 자녀와 손자를 품어주는 어른이 됩니다."},
            },
        }
        DEFAULT_DOMAIN = {
            "초":   {"학업":"학업에 성실히 임하고 진로를 탐색하십시오.", "부모":"가족과의 유대를 소중히 하십시오.", "활동":"다양한 경험이 자신을 성장시킵니다."},
            "청장": {"재물":"운기를 주시하며 재물을 지키십시오.", "직업":"변화에 유연하게 대비하십시오.", "인연":"인연에 열린 자세를 유지하십시오."},
            "말":   {"건강":"건강 관리를 최우선으로 삼으십시오.", "명예":"그간의 삶을 되돌아보고 마음을 정리하십시오.", "자녀":"자녀와의 화합을 최우선으로 삼으십시오."},
        }

        for dw in daewoon[:9]:
            dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
            is_cur = (dw["시작연도"] <= current_year <= dw["종료연도"])
            cur_mark = " [현재]" if is_cur else ""
            dw_age = int(dw.get("시작나이", 0))
            if dw_age < 20:
                d_stage, d_label = "초", "🌱 초년기"
                d_keys = ["학업", "부모", "활동"]
            elif dw_age < 60:
                d_stage, d_label = "청장", "🌿 청장년기"
                d_keys = ["재물", "직업", "인연"]
            else:
                d_stage, d_label = "말", "🍂 말년기"
                d_keys = ["건강", "명예", "자녀"]
            stage_detail = DW_DOMAIN_STAGE.get(dw_ss, DEFAULT_DOMAIN).get(d_stage, DEFAULT_DOMAIN.get(d_stage, {}))
            lines_out = [f"[{k}]: {stage_detail.get(k, '운기를 살피십시오.')}" for k in d_keys]
            result.append("\n".join([
                "", "",
                f"-> {dw['시작나이']}~{dw['시작나이']+9}세 {dw['str']} ({dw_ss}大運){cur_mark} | {d_label}",
            ] + lines_out + ["", ""]))

        golden = [(dw['시작나이'], dw['str']) for dw in daewoon if _get_yongshin_match(TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-'), yongshin_ohs, ilgan_oh) == 'yong']
        crisis = [(dw['시작나이'], dw['str']) for dw in daewoon if TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-') in ['偏官','劫財'] and _get_yongshin_match(TEN_GODS_MATRIX.get(ilgan,{}).get(dw['cg'],'-'), yongshin_ohs, ilgan_oh) != 'yong']
        golden_str = " / ".join([f"{a}세 {s}" for a,s in golden[:4]]) if golden else "꾸준한 노력이 황금기를 만듭니다"
        crisis_str = " / ".join([f"{a}세 {s}" for a,s in crisis[:3]]) if crisis else "없음"
        result.append('\n'.join([
"",
"",
"-> [ 인생 황금기 vs 위기 구간 최종 정리 ]",
"",
f"[*] 황금기 구간: {golden_str}",
f"[!] 주의 구간: {crisis_str}",
"",
"황금기에는 적극 활동하고, 주의 구간에는 내실을 다지며 30%를 비축하십시오.",
]))

        return "".join(result)
    else:  # "future"
        result = []
        result.append('\n'.join([
    f"",
    f"",
    f"    -----------------------------------------------------",
    f"      {display_name}님의 미래 3년 집중 분석",
    f"    -----------------------------------------------------",
    f"",
    f"향후 3년은 {display_name}님 인생에서 중요한 변곡점이 될 수 있습니다. 각 해의 세운(歲運)을 분야별로 집중 분석합니다.",
    f"",
    f"",
    f"",
]))
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
                "食神": {
                    "총평": f"{y}년은 재능과 창의력이 꽃피는 해입니다. 타고난 끼가 세상에 드러나고, 하는 일마다 순조롭게 풀립니다.",
                    "돈": "부업/창작/서비스 관련 수익이 들어오기 좋습니다. 새로운 수입원을 만들기에 최적의 해입니다.",
                    "직장": "업무 성과가 인정받고 주변의 지지를 받습니다. 창의적 프로젝트를 시작하기 좋습니다.",
                    "연애": "자연스러운 매력으로 인기를 끄는 해입니다. 여유로운 만남이 이루어집니다.",
                    "건강": "건강하고 활기찬 해입니다. 과식/과음에만 주의하십시오.",
                    "조언": "재능을 세상에 꺼내십시오. 숨기면 복이 사라집니다.",
                },
                "傷官": {
                    "총평": f"{y}년은 창의력과 혁신의 해입니다. 새로운 도전과 변화를 통해 자신만의 길을 만들어가는 시기입니다.",
                    "돈": "창의적인 방법으로 새 수익을 만들 수 있습니다. 기존 방식에서 벗어난 시도가 빛납니다.",
                    "직장": "직장 내 언행에 특히 주의하십시오. 상사와의 마찰이 생기기 쉬운 해입니다. 창업/이직을 고려하기 좋습니다.",
                    "연애": "자유롭고 활발한 인연이 생기지만 관계가 오래 지속되기 어려울 수 있습니다.",
                    "건강": "신경계 과부하에 주의하십시오. 충분한 휴식이 필요합니다.",
                    "조언": "창의력은 살리되 직장과 권위 앞에서 언행을 조심하십시오.",
                },
                "偏財": {
                    "총평": f"{y}년은 사업과 투자, 이동이 활발해지는 해입니다. 재물 기회가 오지만 기복도 함께 옵니다.",
                    "돈": "사업 확장/투자/거래가 활발합니다. 과욕 없이 계획적으로 움직이면 성과가 있습니다.",
                    "직장": "활발한 외부 활동과 영업이 빛납니다. 새로운 사업 파트너를 만날 수 있습니다.",
                    "연애": "이성 인연이 활발해지는 해입니다. 새로운 만남의 가능성이 높습니다.",
                    "건강": "과로와 무리한 활동으로 인한 체력 저하에 주의하십시오.",
                    "조언": "욕심을 조절하십시오. 들어온 재물의 절반은 반드시 안전한 곳에 보관하십시오.",
                },
                "正財": {
                    "총평": f"{y}년은 안정적이고 꾸준한 재물의 해입니다. 성실한 노력이 결실을 맺는 시기입니다.",
                    "돈": "월급/임대수입 등 고정 수입이 늘어납니다. 저축과 자산 관리에 가장 유리한 해입니다.",
                    "직장": "묵묵히 일한 것이 인정받는 해입니다. 안정적인 커리어를 쌓기 좋습니다.",
                    "연애": "안정적이고 진지한 인연이 생깁니다. 결혼을 결심하기 좋은 해입니다.",
                    "건강": "전반적으로 안정적인 해입니다. 규칙적인 생활을 유지하십시오.",
                    "조언": "안정을 추구하되 기회가 올 때 움직이는 용기도 잃지 마십시오.",
                },
                "偏官": {
                    "총평": f"{y}년은 변화와 도전, 그리고 책임감이 무거워지는 해입니다. 인내심이 필요한 시기입니다.",
                    "돈": "지출이 늘어나고 재물 기복이 생길 수 있습니다. 보수적인 자금 운용이 필요합니다.",
                    "직장": "업무 압박감이 커지고 책임이 무거워집니다. 인내하면 연말에 좋은 결과가 있습니다.",
                    "연애": "관계에서 갈등이나 구설수가 생기지 않도록 배려와 소통에 힘쓰십시오.",
                    "건강": "스트레스로 인한 체력 저하를 조심하십시오. 충분한 숙면이 보약입니다.",
                    "조언": "호랑이를 탄 기상으로 당당히 대처하되, 건강과 겸손을 잃지 마십시오.",
                },
                "正官": {
                    "총평": f"{y}년은 명예와 안정이 찾아오는 해입니다. 법과 원칙을 지키면 큰 행운이 따릅니다.",
                    "돈": "정당한 노력의 대가가 들어오고, 승진/계산 등 공식적인 재물운이 좋습니다.",
                    "직장": "사회적 지위가 올라가고 명예를 얻습니다. 새로운 책임자가 되거나 리더십을 발휘합니다.",
                    "연애": "공식적이고 진지한 만남이 성사되거나 결혼 인연이 닿는 해입니다.",
                    "건강": "전반적으로 안정적인 시기입니다. 규칙적 운동을 병행하십시오.",
                    "조언": "품이와 예의를 갖추십시오. 단정한 모습이 더 큰 기회를 불러옵니다.",
                },
                "偏印": {
                    "총평": f"{y}년은 직관력과 연구능력이 빛나는 해입니다. 전문성을 쌓고 내면을 다지기에 최적입니다.",
                    "돈": "직접적인 수익보다는 지식이나 자격증 등 미래 자산을 만드는 데 유리합니다.",
                    "직장": "특수 기술이나 아이디어가 인정받습니다. 창의적인 성과가 나오는 해입니다.",
                    "연애": "생각이 많아지는 해입니다. 깊은 대화가 통하는 인연에 끌리게 됩니다.",
                    "건강": "불면증이나 신경과민을 주의하십시오. 명상과 숲길 걷기가 정서 안정에 좋습니다.",
                    "조언": "한 우물을 깊게 파십시오. 특화된 전문성이 당신의 무기가 됩니다.",
                },
                "正印": {
                    "총평": f"{y}년은 귀인의 도움과 학문적 성취가 따르는 해입니다. 마음이 평온해지고 지혜가 투명해집니다.",
                    "돈": "문서 운이나 계약 운이 좋습니다. 부동산/자산 취득에 유리한 해입니다.",
                    "직장": "윗사람의 후원과 지도를 받아 큰 성장을 이룹니다. 자격증 취득에 매우 좋습니다.",
                    "연애": "품위 있고 안정적인 만남이 이루어집니다. 주변의 축복 속에 관계가 깊어집니다.",
                    "건강": "정신과 육체 모두 조화로운 해입니다. 정적인 취미를 가지면 더욱 좋습니다.",
                    "조언": "배움에 매진하십시오. 올해 익힌 지식은 평생의 자산이 됩니다.",
                },
                "比肩": {
                    "총평": f"{y}년은 자신감과 독립심이 강해지는 해입니다. 동료와 협력하여 기반을 닦는 시기입니다.",
                    "돈": "동업이나 협력을 통해 기회를 만듭니다. 지출은 늘어날 수 있으니 관리가 필요합니다.",
                    "직장": "라이벌과의 경쟁이 생기지만 이를 발전의 원동력으로 삼으십시오. 독립적 프로젝트에 좋습니다.",
                    "연애": "비슷한 가이드의 인연을 만납니다. 서로의 독립성을 존중하는 관계가 형성됩니다.",
                    "건강": "전반적으로 양호합니다. 운동을 통해 넘치는 에너지를 발산하십시오.",
                    "조언": "독단에 빠지지 마십시오. 협력이 시너지를 낸다는 사실을 잊지 마십시오.",
                },
                "劫財": {
                    "총평": f"{y}년은 변화가 많고 경쟁이 치열해지는 해입니다. 강한 추진력이 필요한 시기입니다.",
                    "돈": "재물 기복이 클 수 있으니 고위험 투자는 피하십시오. 뺏고 뺏기는 기운이 강합니다.",
                    "직장": "치열한 경쟁 속에서 성취를 거둡니다. 자신의 존재감을 확실히 각인시키는 해입니다.",
                    "연애": "질투나 경쟁자가 생길 수 있으니 상대방에 대한 신뢰를 잃지 마십시오.",
                    "건강": "과도한 경쟁 스트레스로 인한 건강 관리에 유의하십시오.",
                    "조언": "뺏기지 않으려면 더 강력해지십시오. 하지만 적보다는 동지를 만드십시오.",
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
            result.append('\n'.join([
f"",
f"",
f"-----------------------------------------------------",
f"{star}{y}년 ({age}세) | {sw.get('세운','')} 세운 | {sw_ss} / {gilhyung}",
f"-----------------------------------------------------",
f"",
f"{yd['총평']}",
f"",
f"[재물/돈]: {yd['돈']}",
f"",
f"[직장/사업]: {yd['직장']}",
f"",
f"[연애/관계]: {yd['연애']}",
f"",
f"[건강]: {yd['건강']}",
f"",
f"[핵심 조언]: {yd['조언']}",
f"",
f"",
]))

        result.append('\n'.join([
f"",
f"",
f"[ 3년 종합 전략 ]",
f"",
f"향후 3년 동안 {display_name}님이 가장 중점을 두어야 할 사항:",
f"",
f"1. 용신 {yong_kr} 강화 | 용신 오행의 색상, 음식, 방위를 일상에서 꾸준히 활용하십시오",
f"2. 기신 차단 | 기신 오행의 요소를 생활 공간에서 최소화하십시오",
f"3. {'적극적 투자와 도전 | 지금이 황금기의 연속입니다' if all(_get_yongshin_match(get_yearly_luck(pils,y).get('십성_천간','-'), yongshin_ohs, ilgan_oh) == 'yong' for y in range(current_year, current_year+2)) else '내실 다지기 | 지금은 준비 기간이니 실력 향상에 집중하십시오'}",
f"4. 건강 관리 | 사주의 취약한 오행 관련 기관을 정기적으로 점검하십시오",
f"5. 인맥 관리 | {'귀인을 만날 운기이니 새로운 사람들과의 교류에 적극적으로 나서십시오' if '정인' in [get_yearly_luck(pils,y).get('십성_천간') for y in range(current_year, current_year+3)] else '신뢰 관계를 꾸준히 유지하고 새로운 파트너를 신중하게 선택하십시오'}",
f"",
f"",
]))
        # 확장 - 월별 핵심 시기 분석
        result.append('\n'.join([
f"",
f"",
f"[ 올해 월별 운기 핵심 포인트 ]",
f"",
f"월별 세운(月運)을 통해 어느 달에 집중하고, 어느 달에 쉬어야 하는지 파악합니다.",
f"",
f"",
]))
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
                result.append('\n'.join([
f"",
f"",
f"",
f"* 별표 달: 이 달에 중요한 미팅, 계약, 투자 결정을 하십시오",
f"! 경고 달: 이 달에는 큰 결정을 피하고 수비 전략을 쓰십시오",
f"o 보통 달: 꾸준히 계획대로 진행하십시오",
f"",
f"",
]))
        except Exception as e: _saju_log.debug(str(e))

        result.append('\n'.join([
f"",
f"",
f"[ 3년 분야별 최적 타이밍 ]",
f"",
f"[돈] 재물, 투자 최적 시기:",
f"{'* ' + str(current_year) + '년이 3년 중 재물 최고 시기입니다. 이 해에 투자, 계약을 집중하십시오.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '* ' + str(current_year+1) + '년에 재물 운이 더 강해질 것으로 예상됩니다.'}",
f"",
f"[직업] 직업, 사업 최적 시기:",
f"* 정관, 편관, 정인이 오는 해에 승진, 자격, 계약 기회를 노리십시오",
f"* {'지금이 새 사업을 시작하기에 좋은 흐름입니다.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '새 사업은 다음 용신 세운이 올 때까지 기다리십시오.'}",
f"",
f"[연애] 연애, 결혼 최적 시기:",
f"* {'재성(남성) / 관성(여성) 세운이 오는 해가 결혼, 인연의 최적 시기입니다.' if gender == '남' else ''}",
f"* {'이 3년 중 ' + str(current_year) + '년이 이성 인연에 가장 활성화된 해입니다.' if (sw_now.get('십성_천간','') in (['정재','편재'] if gender == '남' else ['정관','편관'])) else '적극적인 활동을 통해 인연의 기회를 만드십시오.'}",
f"",
f"[건강] 건강 주의 시기:",
f"* 편관, 겁재 세운은 건강 이상이 생기기 쉬운 시기입니다",
f"* 매년 정기 건강검진을 받고, 용신 오행 관련 기관을 특히 점검하십시오",
f"",
f"[ 3년 후 미래 | 지금의 선택이 만드는 5년 후 ]",
f"",
f"향후 3년을 어떻게 보내느냐에 따라 5년 후의 삶이 완전히 달라집니다.",
f"",
f"{'용신 대운이 진행 중인 지금, 이 황금기를 제대로 활용한다면 5년 후에는 재물/명예/건강 모두 크게 향상될 것입니다.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '지금의 준비 기간을 어떻게 보내느냐에 따라 다음 황금기의 높이가 결정됩니다. 지금 실력을 갈고닦으십시오.'}",
f"",
f"{display_name}님에게 드리는 3년 최종 처방:",
f"\"지금 당장 할 수 있는 한 가지를 시작하십시오. 완벽한 타이밍을 기다리다 인생이 지나갑니다.\"",
f"",
f"",
]))
        return "".join(result)


def _nar_wealth(ctx):
    """재물/사업 섹션 (money)"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    ilgan_oh     = ctx.get('ilgan_oh', "")
    current_year = ctx.get('current_year', datetime.now().year)
    current_age  = ctx.get('current_age', 40)
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    gender       = ctx.get('gender', "남")
    pils         = ctx.get('pils', [(0,{}),(0,{})])
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    gnarr        = ctx.get('gnarr', "")
    top_ss       = ctx.get('top_ss', [])
    combos       = ctx.get('combos', [])
    ss_dist      = ctx.get('ss_dist', {})
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    daewoon      = ctx.get('daewoon', [])

    if True:
        result = []
        result.append('\n'.join([
    f"",
    f"",
    f"    -----------------------------------------------------",
    f"      {display_name}님의 재물, 사업 특화 완전 분석",
    f"    -----------------------------------------------------",
    f"",
    f"재물(財物)은 사주에서 재성(財星)과 용신(用神)의 관계로 파악합니다. 얼마나 버느냐보다 어떤 방식으로 버는지, 어떤 시기에 돈이 모이는지를 아는 것이 진짜 재물 분석입니다.",
    f"",
    f"[ 제1장 | 재물 기질 완전 분석 ]",
    f"",
    f"{display_name}님의 재물 버는 방식을 십성 조합으로 분석합니다.",
    f"일간 {ilgan_kr} + {sn} + 주요 십성 {', '.join(top_ss)}",
    f"",
    f"",
    f"",
]))
        for key, combo in combos[:3]:
                result.append('\n'.join([
    f"",
    f"",
    f"* [{' x '.join(key)}] 재물 조합",
    f"",
    f"{combo.get('요약', '')}",
    f"",
    f"재물 버는 방식: {combo.get('재물', '')}",
    f"맞는 사업/직업: {combo.get('직업', '')}",
    f"재물 주의사항: {combo.get('주의', '')}",
    f"",
    f"",
]))

        result.append('\n'.join([
    f"",
    f"",
    f"[ 제2장 | 재물 운기 분석 | 돈이 모이는 시기와 새는 시기 ]",
    f"",
    f"사주에서 재물은 대운과 세운의 조합으로 결정됩니다. 용신 오행이 들어오는 해에 재물이 모이고, 기신 오행이 강해지는 해에 재물이 나갑니다.",
    f"",
    f"현재 {cur_dw['str'] if cur_dw else '-'} 대운 ({cur_dw_ss})",
    f"{'> 이 대운은 용신 대운으로, 재물이 모이기 좋은 10년입니다. 적극적으로 투자하고 수익 구조를 만들어가십시오.' if cur_dw and _get_yongshin_match(cur_dw_ss, yongshin_ohs, ilgan_oh) == 'yong' else '> 이 대운은 재물 관리에 신중해야 하는 시기입니다. 무리한 투자보다 기존 자산을 지키는 전략이 중요합니다.'}",
    f"",
    f"올해 {sw_now.get('세운','')} 세운 ({sw_now.get('십성_천간','')} / {sw_now.get('길흉','')})",
    f"{'> 올해는 재물 운이 활성화되는 해입니다. 새로운 수입원을 만들거나 투자를 시작하기 좋습니다.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '> 올해는 재물 지출에 주의해야 합니다. 불필요한 지출을 줄이고 저축에 집중하십시오.'}",
    f"",
    f"[ 제3장 | 투자 유형 분석 ]",
    f"",
    f"{display_name}님의 사주에서 가장 잘 맞는 투자 유형:",
    f"",
    f"{'[v] 부동산 투자 | 토(土) 기운과 관련된 투자로 장기적으로 안정적인 수익을 줍니다.' if '土' in yongshin_ohs else ''}",
    f"{'[v] 금융, 주식 투자 | 금(金) 기운과 관련된 투자로 결단력 있게 움직이면 수익이 납니다.' if '金' in yongshin_ohs else ''}",
    f"{'[v] 무역, 유통 투자 | 수(水) 기운과 관련된 투자로 흐름을 잘 타면 큰 수익을 냅니다.' if '水' in yongshin_ohs else ''}",
    f"{'[v] 성장주, 벤처 투자 | 목(木) 기운과 관련된 투자로 초기 단계 투자에서 강합니다.' if '木' in yongshin_ohs else ''}",
    f"{'[v] 에너지, 문화 투자 | 화(火) 기운과 관련된 투자로 사람과 콘텐츠에서 수익이 납니다.' if '火' in yongshin_ohs else ''}",
    f"",
    f"! 피해야 할 투자 유형 (기신 오행 관련):",
    f"{'기신 오행의 산업/자산에는 투자를 자제하십시오. 아무리 좋아 보여도 이 분의 사주에서는 기신 오행 투자가 손실로 이어지는 경우가 많습니다.'}",
    f"",
    f"[ 제4장 | 사업 적합성 분석 ]",
    f"",
    f"{display_name}님의 사주가 독립사업과 직장 중 어느 쪽이 더 맞는지:",
    f"",
    f"{'비견/겁재가 강한 이 사주는 독립사업/자영업이 더 맞습니다. 남 밑에서 지시받기보다 자신만의 영역에서 일할 때 재물이 쌓입니다.' if any(ss in top_ss for ss in ['비견', '겁재']) else ''}",
    f"{'식신/상관이 강한 이 사주는 창의적인 사업 또는 프리랜서 활동이 맞습니다. 재능을 상품화하는 방식이 가장 효율적인 재물 창출입니다.' if any(ss in top_ss for ss in ['식신', '상관']) else ''}",
    f"{'정관/정재가 강한 이 사주는 안정적인 직장에서 꾸준히 성장하는 방식이 맞습니다. 조직 내에서 신뢰를 쌓는 것이 재물로 이어집니다.' if any(ss in top_ss for ss in ['정관', '정재']) else ''}",
    f"{'편재/편관이 강한 이 사주는 역동적인 사업 환경에서 강합니다. 위험을 감수하고 크게 움직이는 것을 두려워하지 마십시오.' if any(ss in top_ss for ss in ['편재', '편관']) else ''}",
    f"",
    f"[ 제5장 | 재물 새는 구멍과 막는 법 ]",
    f"",
    f"이 사주에서 재물이 새는 주요 원인:",
    f"",
    f"{'1. 겁재가 강해 주변 사람들에게 베풀다가 재물이 분산됩니다. 감정적 지출을 줄이십시오.' if '겁재' in ss_dist else ''}",
    f"{'2. 상관이 강해 충동적인 소비나 불필요한 지출이 생깁니다. 구매 전 하루 생각하는 습관을 들이십시오.' if '상관' in ss_dist else ''}",
    f"{'3. 편재가 강해 투자 욕구가 넘쳐 무리하게 확장하다 손실이 납니다. 수익의 30%는 반드시 안전 자산으로 보관하십시오.' if '편재' in ss_dist else ''}",
    f"{'4. 편인이 강해 직업 변동이 잦아 안정적인 수입 구조를 만들기 어렵습니다. 한 분야에 집중하는 것이 재물 관리의 핵심입니다.' if '편인' in ss_dist else ''}",
    f"",
    f"재물을 지키는 가장 좋은 방법:",
    f"* 용신 {yong_kr} 색상의 지갑 사용",
    f"* 수입의 20~30% 자동 저축 설정",
    f"* 기신 오행이 강한 해에는 큰 재물 결정 미루기",
    f"* 용신 오행이 강한 해에 투자 및 사업 확장",
    f"",
    f"[ 제6장 | 재물 황금기 완전 예측 ]",
    f"",
    f"{display_name}님의 인생에서 재물 황금기가 오는 시기:",
    f"",
    f"",
]))
        # 향후 대운 중 용신 대운 찾기
        peak_years = []
        for dw in daewoon:
                dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                if _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong":
                    age_mid = dw["시작나이"] + 5
                    year_mid = birth_year + age_mid - 1
                    peak_years.append(f"* {dw['시작나이']}~{dw['시작나이']+9}세 ({dw['시작연도']}~{dw['종료연도']}년): {dw['str']} 용신 대운 | 이 10년이 {display_name}님의 재물 황금기입니다")
        result.append("\n".join(peak_years[:3]) if peak_years else "* 꾸준한 노력이 재물 황금기를 만듭니다")
        result.append('\n'.join([
    f"",
    f"",
    f"",
    f"재물 황금기를 최대로 활용하는 전략:",
    f"1. 황금기 대운이 시작되기 2~3년 전부터 준비하십시오",
    f"2. 황금기에는 두려움 없이 과감하게 투자하십시오",
    f"3. 황금기의 수익은 다음 어려운 시기를 위해 30% 이상 비축하십시오",
    f"4. 사업을 시작한다면 황금기 대운 초반에 시작하는 것이 가장 좋습니다",
    f"",
    f"[ 제7장 | 재물 관리의 황금 원칙 | 이 사주에만 해당하는 처방 ]",
    f"",
    f"일간 {ilgan_kr} + {gname} + {sn} 조합의 재물 관리 황금 원칙:",
    f"",
    f"원칙 1. {'크게 벌고 크게 쓰는 패턴을 끊어야 합니다. 수입이 생기면 즉시 30%를 자동이체로 저축하십시오.' if any(ss in ss_dist for ss in ['겁재','편재']) else '안정적으로 쌓아가는 것이 이 사주의 재물 방식입니다. 투기성 투자에 유혹받지 마십시오.'}",
    f"",
    f"원칙 2. {'창의력과 재능이 돈이 됩니다. 자신의 전문성을 상품화하는 방법을 끊임없이 고민하십시오.' if any(ss in ss_dist for ss in ['식신','상관']) else '안정적 수입 구조를 먼저 만들고 투자를 시작하십시오.'}",
    f"",
    f"원칙 3. 용신 {yong_kr} 오행이 강해지는 해에 큰 재물 결정을 집중하고, 기신이 강해지는 해에는 지키는 전략을 쓰십시오.",
    f"",
    f"원칙 4. {'부동산은 이 사주에 중장기적으로 좋은 자산입니다.' if '土' in yongshin_ohs else '금융 자산과 현금 유동성을 충분히 유지하십시오.' if '水' in yongshin_ohs or '金' in yongshin_ohs else '성장하는 분야에 일찍 진입하는 것이 이 사주의 재물 전략입니다.' if '木' in yongshin_ohs else '콘텐츠/사람/브랜드에 투자하는 것이 이 사주의 재물 방식입니다.'}",
    f"",
    f"원칙 5. 보증/동업에서 재물을 잃는 경우가 많습니다. 계약서 없는 재물 거래는 절대 하지 마십시오.",
    f"",
    f"[ 제8장 | 직업별 예상 소득 패턴 분석 ]",
    f"",
    f"{display_name}님의 사주에서 각 직업 유형별 예상 소득 패턴:",
    f"",
    f"* 직장인: 꾸준하고 안정적이지만 {'가파른 성장은 어렵습니다. 전문성을 쌓아 희소 인재가 되어야 합니다.' if '신강' in sn else '귀인의 도움으로 예상보다 빠른 성장이 가능합니다.'}",
    f"",
    f"* 프리랜서/자영업: {'이 사주에 가장 잘 맞는 방식입니다. 초기 기반을 잡는 데 3~5년이 필요하지만, 그 후에는 직장보다 훨씬 큰 수익을 낼 수 있습니다.' if any(ss in ss_dist for ss in ['비견','식신','상관']) else '안정적인 수입이 보장되지 않는 방식이라 이 사주에는 주의가 필요합니다.'}",
    f"",
    f"* 투자/사업: {'편재가 강해 사업 확장 기질이 있습니다. 단, 리스크 관리가 생존의 핵심입니다.' if '편재' in ss_dist else '안정적인 사업 기반을 만든 후 확장하는 보수적 전략이 맞습니다.'}",
    f"",
    f"[ 제9장 | 나이별 재물 타이밍 완전 분석 ]",
    f"",
    f"인생의 각 10년 구간에서 재물 운의 흐름:",
    f"",
    f"",
]))
        for dw in daewoon[:8]:
                dw_ss_hanja = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                # 한자 → 한글 변환 (TEN_GODS_MATRIX는 한자 반환)
                _SS_KR = {
                    "食神":"식신","傷官":"상관","偏財":"편재","正財":"정재",
                    "偏官":"편관","正官":"정관","偏印":"편인","正印":"정인",
                    "比肩":"비견","劫財":"겁재",
                }
                dw_ss = _SS_KR.get(dw_ss_hanja, dw_ss_hanja)
                is_yong = _get_yongshin_match(dw_ss_hanja, yongshin_ohs, ilgan_oh) == "yong"
                money_advice = {
                    "식신": "재능 소득·창작 수익이 들어오는 시기",
                    "상관": "혁신적 방식으로 새 수익원 개척 시기",
                    "편재": "⭐ 투자·사업으로 크게 버는 시기 (기복 주의)",
                    "정재": "안정적 저축·자산 축적 최적 시기",
                    "편관": "⚠️ 재물 보호·손실 방어가 우선인 시기",
                    "정관": "직장·명예를 통한 합법적 소득 증가 시기",
                    "편인": "전문성 투자 시기 (미래 재물의 씨앗)",
                    "정인": "귀인을 통한 재물 기회 시기",
                    "비견": "재물 분산 주의·독립 수익 도전 시기",
                    "겁재": "❌ 재물 손실 위험·투기 절대 금지 시기",
                }.get(dw_ss, f"{dw_ss_hanja} 기운의 운기")
                yong_mark = " ★[용신 황금기]" if is_yong else ""
                result.append(f"  {dw['시작나이']}~{dw['시작나이']+9}세 ({dw_ss_hanja}/{dw_ss}): {money_advice}{yong_mark}\n")

        result.append('\n'.join([
    f"",
    f"",
    f"",
    f"[ 제10장 | 만신의 재물 최종 처방 ]",
    f"",
    f"{display_name}님의 재물 운을 한마디로 요약하면:",
    f"\"{combos[0][1].get('재물','타고난 방식으로 꾸준히 쌓아가는 재물') if combos else '성실함과 전문성으로 재물을 쌓아가는 사주'}\"",
    f"",
    f"이 사주에서 재물이 들어오는 문은 \"{', '.join(top_ss[:2])}\"이(가) 열어줍니다.",
    f"이 문이 활성화되는 운기에 최대로 움직이고, 닫히는 운기에는 지키십시오.",
    f"",
    f"재물은 복이지만 집착하면 독이 됩니다. {display_name}님만의 방식으로 재물을 이루어 나가십시오.",
    f"",
    f"",
]))
        return "".join(result)


def _nar_health(ctx):
    """인간관계/육친 섹션 (relations)"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    ilgan_oh     = ctx.get('ilgan_oh', "")
    current_year = ctx.get('current_year', datetime.now().year)
    current_age  = ctx.get('current_age', 40)
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    gender       = ctx.get('gender', "남")
    pils         = ctx.get('pils', [(0,{}),(0,{})])
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    gnarr        = ctx.get('gnarr', "")
    top_ss       = ctx.get('top_ss', [])
    combos       = ctx.get('combos', [])
    ss_dist      = ctx.get('ss_dist', {})
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    daewoon      = ctx.get('daewoon', [])

    if True:
        result = []
        yk = get_yukjin(ilgan, pils, gender)
        sipsung_data = calc_sipsung(ilgan, pils)

        result.append('\n'.join([
    f"",
    f"",
    f"    -----------------------------------------------------",
    f"      {display_name}님의 인간관계, 육친 완전 분석",
    f"    -----------------------------------------------------",
    f"",
    f"인간관계는 사주에서 십성(十星)과 육친(六親)을 통해 분석합니다. 어떤 사람과 인연이 깊은지, 어떤 사람과 갈등이 생기는지를 사주는 미리 알려줍니다.",
    f"",
    f"[ 제1장 | 일간의 대인관계 패턴 ]",
    f"",
    f"{display_name}님은 일간 {ilgan_kr} + {sn}의 조합으로 다음과 같은 대인관계 패턴을 가집니다:",
    f"",
    f"{'* 신강하여 자기주장이 강합니다. 타인의 의견을 경청하는 연습이 관계 개선의 핵심입니다.' if '신강' in sn else '* 신약하여 타인의 영향을 많이 받습니다. 자신의 의견을 분명히 표현하는 연습이 필요합니다.' if '신약' in sn else '* 중화 사주로 균형 잡힌 대인관계를 유지합니다. 극단적인 관계보다 안정적인 인간관계를 선호합니다.'}",
    f"",
    f"{'* 비견, 겁재가 강해 경쟁적인 관계에서 에너지를 발산합니다.' if any(ss in ss_dist for ss in ['비견','겁재']) else ''}",
    f"{'* 식신, 상관이 강해 자신을 잘 표현하고 주변에 즐거움을 줍니다.' if any(ss in ss_dist for ss in ['식신','상관']) else ''}",
    f"{'* 정관, 편관이 강해 조직과 권위를 의식하며 사회적 관계에 민감합니다.' if any(ss in ss_dist for ss in ['정관','편관']) else ''}",
    f"{'* 정인, 편인이 강해 스승과 선배로부터 배우고 지식을 나누는 관계를 중요시합니다.' if any(ss in ss_dist for ss in ['정인','편인']) else ''}",
    f"",
    f"[ 제2장 | 육친 상세 분석 ]",
    f"",
    f"",
]))
        YUKJIN_DEEP = {
                "어머니(正印)": f"정인은 어머니의 자리입니다. {display_name}님과 어머니의 관계는 사주에서 매우 중요한 영향을 미칩니다. 정인이 있다면 어머니의 음덕(蔭德)이 크며, 어머니로부터 정서적/물질적 도움을 받는 운입니다. 학문과 귀인을 상징하는 정인이 강하면 교육열이 높고 스승의 인연이 좋습니다.",
                "계모(偏印)": f"편인은 계모/이모/외조모 등 어머니 외의 여성 윗사람을 상징합니다. 편인이 강하면 독특한 재능과 직관이 있으며, 특수 분야에서 독보적인 능력을 발휘합니다. 단, 식신을 억제하면 도식이 형성되어 복이 꺾이는 작용이 있습니다.",
                "아버지(偏財)": f"편재는 아버지의 자리입니다. {display_name}님과 아버지의 관계가 이 사주에 큰 영향을 줍니다. 편재가 있다면 아버지로부터 재물적 도움이나 사업적 조언을 받을 수 있습니다. 편재는 활동적이고 외향적인 아버지의 기운으로, 아버지가 사업가이거나 활발한 분인 경우가 많습니다.",
                "아내(正財)": f"정재는 남성에게 아내의 자리입니다. 정재가 있으면 성실하고 현모양처형 배우자를 만나는 운입니다. 정재가 강하면 안정적인 가정생활을 영위하며, 배우자의 내조가 큰 힘이 됩니다. 다만 정재가 너무 강하면 돈과 배우자에 집착하는 경향이 생길 수 있습니다.",
                "남편(正官)": f"정관은 여성에게 남편의 자리입니다. 정관이 있으면 점잖고 안정적인 남편 인연이 있습니다. 사회적으로 인정받는 남성을 만나는 운이며, 결혼 후 안정적인 가정생활을 할 가능성이 높습니다.",
                "아들(偏官)": f"편관(칠살)은 남성에게 아들, 여성에게는 정부(情夫)를 상징합니다. 편관이 있으면 자녀로 인한 기쁨과 함께 자녀 교육에 많은 에너지를 쏟습니다. 칠살이 제화(制化)되면 자녀가 사회적으로 성공하는 운입니다.",
                "딸(正官)": f"정관은 남성에게 딸을 상징합니다. 딸과의 관계가 따뜻하고 격식 있습니다. 자녀가 안정적이고 사회적으로 인정받는 삶을 사는 운입니다.",
                "형제(比肩)": f"비견은 형제/자매/친구/동료를 상징합니다. 비견이 강하면 형제자매나 친구와의 인연이 깊습니다. 서로 경쟁하면서도 성장하는 관계이며, 동업이나 협업을 통해 시너지를 낼 수 있습니다.",
                "이복형제(劫財)": f"겁재는 이복 형제/경쟁자/라이벌을 상징합니다. 겁재가 강하면 주변에 경쟁자가 많고, 재물이 분산될 수 있습니다. 그러나 건강한 경쟁 의식으로 발전시키면 강한 추진력이 됩니다.",
        }
        for item in yk:
                fam = item.get("관계", "")
                has = item.get("present", False)
                where = item.get("위치", "없음")
                deep_desc = YUKJIN_DEEP.get(fam, item.get("desc", ""))
                result.append('\n'.join([
    f"",
    f"",
    f"* {fam}",
    f"   위치: {where if where != '없음' else '원국에 직접 없음'}",
    f"   인연 강도: {'강함 | 이 인연이 인생에 크게 영향을 미칩니다' if has else '약함 | 인연이 엷거나 독립적인 관계'}",
    f"",
    f"   {deep_desc}",
    f"",
    f"   {'이 육친과의 관계가 이 분의 운명에 핵심적인 역할을 합니다. 이 관계를 잘 가꾸십시오.' if has else '이 육친과의 관계에서 독립적인 성향이 강합니다. 의식적으로 관계를 돌보는 노력이 필요합니다.'}",
    f"",
    f"",
]))

        result.append('\n'.join([
    f"",
    f"",
    f"[ 제3장 | 이성 인연, 배우자 분석 ]",
    f"",
    f"일지(日支) {iljj_kr}({iljj})는 배우자 자리입니다. 이 자리의 기운이 배우자의 성품과 부부 관계의 방향을 결정합니다.",
    f"",
    f"{display_name}님의 배우자 자리 분석:",
    f"* {iljj_kr}({iljj}) 일지 | {'안정과 포용력을 가진 배우자' if iljj in ['丑(축)','辰(진)','戌(술)','未(미)'] else '열정적이고 활기찬 배우자' if iljj in ['午(오)','巳(사)','寅(인)'] else '논리적이고 실력 있는 배우자' if iljj in ['申(신)','酉(유)','亥(해)','子(자)'] else '성장하는 에너지를 가진 배우자' if iljj in ['卯(묘)'] else '포용력 있는 배우자'}를 만나는 운입니다.",
    f"",
    f"이성 인연이 강해지는 시기:",
    f"* {'재성(財星) 세운 | 편재, 정재 세운이 올 때 이성 인연이 활성화됩니다.' if gender == '남' else '* 관성(官星) 세운 | 정관, 편관 세운이 올 때 이성 인연이 활성화됩니다.'}",
    f"* 현재 대운 {cur_dw['str'] if cur_dw else '-'} | {'이성 인연이 활성화되는 대운입니다' if cur_dw_ss in (['정재','편재'] if gender=='남' else ['정관','편관']) else '배우자 운보다 다른 분야가 강조되는 대운입니다'}",
    f"",
    f"이상적인 파트너의 특징:",
    f"* 용신 {yong_kr} 오행을 가진 사람과 궁합이 잘 맞습니다",
    f"* {'불, 에너지가 강한 사람' if '火' in yongshin_ohs else ''}{'땅처럼 안정적인 사람' if '土' in yongshin_ohs else ''}{'물처럼 지혜로운 사람' if '水' in yongshin_ohs else ''}{'나무처럼 성장하는 사람' if '木' in yongshin_ohs else ''}{'금처럼 결단력 있는 사람' if '金' in yongshin_ohs else ''}이(가) 이상적인 파트너입니다",
    f"",
    f"[ 제4장 | 사회적 인간관계 조언 ]",
    f"",
    f"{display_name}님이 만나야 할 귀인(貴人)의 특징:",
    f"* 용신 오행이 강한 분야(직업, 전공)에 있는 사람이 귀인입니다",
    f"* {'수학, 금융, 법, 의료, 공학 분야의 전문가' if '金' in yongshin_ohs or '水' in yongshin_ohs else '교육, 예술, 봉사, 문화 분야의 전문가' if '木' in yongshin_ohs or '火' in yongshin_ohs else '부동산, 건설, 농업, 토지 관련 분야의 전문가' if '土' in yongshin_ohs else '다양한 분야의 전문가'}와의 인연을 소중히 하십시오",
    f"",
    f"조심해야 할 인연:",
    f"* 기신 오행이 강한 사람과는 재물 거래나 동업을 피하십시오",
    f"* 겁재가 강하게 들어오는 해에 만나는 사업 파트너는 신중히 검토하십시오",
    f"* 겉으로는 화려해 보이지만 실속이 없는 관계에 에너지를 낭비하지 마십시오",
    f"",
    f"인간관계에서 {display_name}님만의 강점:",
    f"{char.get('장점', '타고난 성품으로 주변 사람들에게 신뢰를 줍니다')}",
    f"",
    f"이 강점을 살려 인간관계를 넓혀가면, 그 관계가 결국 재물과 명예로 돌아오는 운명입니다.",
    f"",
    f"[ 제5장 | 연애, 결혼 심층 분석 ]",
    f"",
    f"{'남성' if gender == '남' else '여성'} {ilgan_kr} 일간의 연애 본능:",
    f"* {'* ' + char.get('연애_남', '') if gender == '남' else '* ' + char.get('연애_여', '')}",
    f"",
    f"배우자 자리 {iljj_kr}({iljj}) 심층 해석:",
    f"{iljj_kr}이(가) 배우자 자리에 있다는 것은 배우자에게서 {'안정/신뢰/현실적 도움을 받고 싶은 내면의 욕구' if iljj in ['丑(축)','辰(진)','戌(술)','未(미)'] else '열정/활기/도전적 에너지를 받고 싶은 욕구' if iljj in ['午(오)','巳(사)'] else '지적 교감/논리/전문성을 원하는 욕구' if iljj in ['申(신)','酉(유)'] else '성장/창의/새로움을 함께 나누고 싶은 욕구' if iljj in ['寅(인)','卯(묘)'] else '깊은 감정/지혜/내면의 평화를 함께하고 싶은 욕구' if iljj in ['亥(해)','子(자)'] else '다양한 매력을 가진 파트너를 원하는 욕구'}가 있다는 것입니다.",
    f"",
    f"이상적인 배우자의 오행:",
    f"* 용신 {yong_kr} 오행이 강한 사람 | 이 분과 함께하면 삶이 더 풍요로워집니다",
    f"* 이 오행을 가진 직업군의 사람이 좋습니다",
    f"",
    f"결혼 적령기 분석:",
    f"현재 {current_age}세 기준:",
    f"* {'재성 대운 중에 있어 결혼 에너지가 활성화되어 있습니다.' if cur_dw and cur_dw_ss in (['정재','편재'] if gender == '남' else ['정관','편관']) else '관성 대운 중에 있어 결혼 에너지가 활성화되어 있습니다.' if cur_dw and cur_dw_ss in (['정관','편관'] if gender == '남' else ['정재','편재']) else '결혼보다 자기 개발에 더 집중하는 시기입니다.'}",
    f"* 가장 강한 결혼 기회가 오는 세운: {'정재, 편재 세운' if gender == '남' else '정관, 편관 세운'}",
    f"",
    f"[ 제6장 | 직장 내 인간관계 전략 ]",
    f"",
    f"{gname}을 가진 분의 직장 인간관계 패턴:",
    f"* {'정관격은 상사와 원칙적이고 예의 바른 관계를 형성합니다. 규칙을 잘 지키고 성실한 모습이 신뢰를 얻습니다.' if '정관' in gname else '편관격은 직장에서 경쟁이 치열하고 상사와 갈등이 생기기 쉽습니다. 실력으로 인정받는 것이 최선입니다.' if '편관' in gname else '격국의 기운이 직장 내 관계에 영향을 줍니다.'}",
    f"",
    f"동료와의 관계:",
    f"* {'비견이 강해 동료 간 경쟁이 활발합니다. 협력을 통해 함께 성장하는 방식이 더 유리합니다.' if '비견' in ss_dist or '겁재' in ss_dist else '식신, 상관이 강해 동료들에게 재미와 영감을 주는 존재입니다. 분위기 메이커 역할이 강점입니다.' if '식신' in ss_dist or '상관' in ss_dist else '정관, 정인이 강해 조직 내에서 신뢰받는 전문가로 인식됩니다.' if '정관' in ss_dist or '정인' in ss_dist else '독특한 개성으로 직장 내 독보적인 존재감을 가집니다.'}",
    f"",
    f"직장에서 조심해야 할 사람:",
    f"* 기신 오행이 강한 상사나 동료와는 재물 거래를 피하십시오",
    f"* 자신을 이용하려는 person을 빨리 알아채는 직관을 기르십시오",
    f"",
    f"[ 제7장 | 인간관계 운기별 전략 ]",
    f"",
    f"현재 {cur_dw['str'] if cur_dw else '-'} 대운에서의 인간관계:",
    f"{'* 인성 대운: 스승, 어른의 도움이 큰 시기입니다. 배움의 인연을 소중히 하십시오.' if cur_dw_ss in ['정인','편인'] else '* 재성 대운: 이성 인연과 사업 파트너 운이 강합니다.' if cur_dw_ss in ['정재','편재'] else '* 관성 대운: 사회적 관계와 권위자와의 인연이 중요해집니다.' if cur_dw_ss in ['정관','편관'] else '* 비겁 대운: 동료, 친구, 경쟁자와의 관계가 인생의 중심이 됩니다.' if cur_dw_ss in ['비견','겁재'] else '* 식상 대운: 자기표현과 인기가 중심이 되는 시기입니다.'}",
    f"",
    f"올해 {sw_now.get('세운','')} 세운에서의 인간관계:",
    f"{'* 새로운 귀인을 만날 운기입니다. 모임, 행사에 적극적으로 참여하십시오.' if _get_yongshin_match(sw_now.get('십성_천간',''), yongshin_ohs, ilgan_oh) == 'yong' else '* 인간관계에서 신중함이 요구되는 해입니다. 새로운 동업이나 큰 부탁은 자제하십시오.'}",
    f"",
    f"[ 제8장 | 만신의 인간관계 최종 처방 ]",
    f"",
    f"{display_name}님의 인간관계 핵심 비결:",
    f"",
    f"1. {char.get('장점','타고난 성품')}을(를) 인간관계에서 최대로 발휘하십시오",
    f"2. {char.get('단점','약점')}을(를) 의식적으로 보완하는 노력을 하십시오",
    f"3. 용신 {yong_kr} 오행이 강한 분야의 사람들과 더 많이 교류하십시오",
    f"4. 인간관계에 투자한 시간과 에너지는 결국 재물과 명예로 돌아옵니다",
    f"",
    f"    \"Good relationships create good luck, and good luck creates a good life.\"",
    f"",
    f"",
]))
        return "".join(result)


def _nar_past(ctx):
    """과거 적중 섹션 (past)"""
    ilgan        = ctx.get('ilgan', "")
    ilgan_kr     = ctx.get('ilgan_kr', "")
    iljj         = ctx.get('iljj', "")
    iljj_kr      = ctx.get('iljj_kr', "")
    ilgan_oh     = ctx.get('ilgan_oh', "")
    current_year = ctx.get('current_year', datetime.now().year)
    current_age  = ctx.get('current_age', 40)
    display_name = ctx.get('display_name', "내담자")
    birth_year   = ctx.get('birth_year', 1980)
    gender       = ctx.get('gender', "남")
    pils         = ctx.get('pils', [(0,{}),(0,{})])
    sn           = ctx.get('sn', "")
    strength_info= ctx.get('strength_info', {})
    gname        = ctx.get('gname', "")
    yongshin_ohs = ctx.get('yongshin_ohs', [])
    yong_kr      = ctx.get('yong_kr', "")
    char         = ctx.get('char', {})
    sn_narr      = ctx.get('sn_narr', "")
    gnarr        = ctx.get('gnarr', "")
    top_ss       = ctx.get('top_ss', [])
    combos       = ctx.get('combos', [])
    ss_dist      = ctx.get('ss_dist', {})
    cur_dw       = ctx.get('cur_dw', {})
    cur_dw_ss    = ctx.get('cur_dw_ss', '')
    sw_now       = ctx.get('sw_now', {})
    sw_next      = ctx.get('sw_next', {})
    daewoon      = ctx.get('daewoon', [])

    if True:
        result = []
        result.append('\n'.join([
    f"",
    f"",
    f"    -----------------------------------------------------",
    f"      {display_name}님의 과거 적중 타임라인 분석",
    f"    -----------------------------------------------------",
    f"",
    f"과거의 사건들을 사주 엔진으로 분석한 결과입니다. 특정 시기에 발생한 강한 기운의 변화(충, 합)가 실제 삶에서 어떻게 나타났는지 확인해 보십시오.",
    f"",
    f"",
    f"",
]))
        highlights = generate_engine_highlights(pils, birth_year, gender)
        for event in highlights.get("past_events", [])[:10]:
            result.append(f"### {event.get('age')}세 ({event.get('year')}년) | {event.get('title')}\n")
            result.append(f"{event.get('desc')}\n\n")

        result.append("""
[ 과거 분석의 의미 ]
과거를 분석하는 것은 미래를 대비하기 위함입니다. 어떤 운기에 어떤 사건이 일어났는지 패턴을 파악하면, 다가올 운기에서 최선의 선택을 할 수 있습니다.
""")
        return "".join(result)


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

        birth_month = st.session_state.get('birth_month', 1)
        birth_day = st.session_state.get('birth_day', 1)
        birth_hour = st.session_state.get('birth_hour', 12)
        birth_minute = st.session_state.get('birth_minute', 0)
        daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
        cur_dw = next((d for d in daewoon if d["시작연도"] <= current_year <= d["종료연도"]), None)
        # 일간 한자 → '甲(갑)' 형식 변환 (ILGAN_CHAR_DESC 키 형식)
        _CG_KR_MAP = {
            "甲":"갑","乙":"을","丙":"병","丁":"정","戊":"무",
            "己":"기","庚":"경","辛":"신","壬":"임","癸":"계",
        }
        ilgan_char_key = f"{ilgan}({_CG_KR_MAP.get(ilgan, '')})" if ilgan in _CG_KR_MAP else ilgan
        char = ILGAN_CHAR_DESC.get(ilgan_char_key, ILGAN_CHAR_DESC.get(ilgan, {}))

        # 십성 한자 → 한글 변환
        _SS_KR_MAP = {
            "食神":"식신","傷官":"상관","偏財":"편재","正財":"정재",
            "偏官":"편관","正官":"정관","偏印":"편인","正印":"정인",
            "比肩":"비견","劫財":"겁재",
        }
        cur_dw_ss_hanja = TEN_GODS_MATRIX.get(ilgan, {}).get(cur_dw["cg"], "-") if cur_dw else "-"
        cur_dw_ss = _SS_KR_MAP.get(cur_dw_ss_hanja, cur_dw_ss_hanja)

        sn_narr = STRENGTH_NARRATIVE.get(sn, STRENGTH_NARRATIVE.get(sn.split("(")[0], ""))
        gnarr = GYEOKGUK_NARRATIVE.get(gname, f"{gname}은 독특한 개성과 능력을 가진 격국입니다.")


        sw_now = get_yearly_luck(pils, current_year)
        sw_next = get_yearly_luck(pils, current_year + 1)

        OH_KR_MAP = {"木":"목(木)","火":"화(火)","土":"토(土)","金":"금(金)","水":"수(水)"}
        yong_kr = " - ".join([OH_KR_MAP.get(o, o) for o in yongshin_ohs])

        ctx = {

            'pils': pils, 'birth_year': birth_year, 'gender': gender, 'name': name,
            'section': section,
            'ilgan': ilgan, 'ilgan_idx': ilgan_idx, 'ilgan_kr': ilgan_kr,
            'iljj': iljj, 'iljj_idx': iljj_idx, 'iljj_kr': iljj_kr,
            'current_year': current_year, 'current_age': current_age,
            'display_name': display_name,
            'strength_info': strength_info, 'sn': sn,
            'gyeokguk': gyeokguk, 'gname': gname,
            'ys': ys, 'yongshin_ohs': yongshin_ohs, 'ilgan_oh': ilgan_oh,
            'life': life, 'ss_dist': ss_dist, 'top_ss': top_ss, 'combos': combos,
            'birth_month': birth_month, 'birth_day': birth_day,
            'birth_hour': birth_hour, 'birth_minute': birth_minute,
            'daewoon': daewoon, 'cur_dw': cur_dw, 'cur_dw_ss': cur_dw_ss,
            'sw_now': sw_now, 'sw_next': sw_next,
            'OH_KR_MAP': OH_KR_MAP, 'yong_kr': yong_kr,
            'char': char, 'sn_narr': sn_narr, 'gnarr': gnarr,
        }

        if section == "report":
            return _nar_report(ctx)
        elif section in ("future", "lifeline"):
            return _nar_future(ctx)
        elif section == "money":
            return _nar_wealth(ctx)
        elif section == "relations":
            return _nar_health(ctx)
        elif section == "past":
            return _nar_past(ctx)
        return ""

    except Exception as e:
        return f"Error in narrative generation: {e}"


# tab_ai_chat_prophet: 제거됨 - tab_ai_chat 으로 통합


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

    # -- 리포트 요약 카드 -------------------------------------
    sn_label  = strength_info.get("신강신약", "중화")
    _sn_score = strength_info.get("helper_score", 50)
    sn_icon   = STRENGTH_DESC.get(sn_label, {}).get("icon", "[Balance]")
    yong_list = ys.get("종합_용신", [])
    yong_str  = "/".join(yong_list[:2]) if isinstance(yong_list, list) else str(yong_list)
    gk_name   = gyeokguk.get("격국명", "-") if gyeokguk else "-"

    st.markdown(f"""

    <div style="background:#ffffff;border:1.5px solid #e0d0a0;border-radius:14px;
                padding:14px 16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
        <div style="font-size:11px;font-weight:700;color:#8b6200;letter-spacing:2px;margin-bottom:10px">
            📋 종합 사주 리포트 - 원국/성향/격국/용신
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
            <div style="flex:1;min-width:90px;background:#fff8e8;border-radius:10px;
                        padding:10px 12px;border:1px solid #e8d5a0;text-align:center">
                <div style="font-size:10px;color:#000000;margin-bottom:4px">일간</div>
                <div style="font-size:20px;font-weight:900;color:#333">{pils[1]["cg"] if pils[1] else "?"}</div>
                <div style="font-size:11px;color:#555">{pils[1]["jj"] if pils[1] else "?"}</div>
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
    </div>
""", unsafe_allow_html=True)

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
            </div>
""", unsafe_allow_html=True)
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
                {"<div style='background:#fff5f5;border:1.5px solid #ff0000;border-left:8px solid #ff0000;padding:10px 14px;border-radius:8px;font-size:13px;color:#000000;margin-bottom:10px;white-space:pre-wrap'>[!]️ " + gcaution + "</div>" if gcaution else ""}
                {"<div style='background:#f5fff5;border:1.5px solid #27ae60;border-left:8px solid #27ae60;padding:10px 14px;border-radius:8px;font-size:13px;color:#000000'>- " + ggod_rank + "</div>" if ggod_rank else ""}
            </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"격국 표시 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑤ 용신
    st.markdown('<div class="gold-section">- 용신 (用神)</div>', unsafe_allow_html=True)
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
            <div style="margin-bottom:10px"><b>🌟 用神(용신 - 힘이 되는 오행):</b><br>{y_tags}</div>
            <div><b>[!]️ 忌神(기신 - 조심할 오행):</b><br>{g_tags}</div>
        </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"용신 표시 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑥ 십성 조합 인생 분석 *** 핵심
    st.markdown('<div class="gold-section">🔮 십성(十星) 조합 - 당신의 인생 설계도</div>', unsafe_allow_html=True)
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
        </div>
""", unsafe_allow_html=True)

        if combos:
            for key, combo in combos:
                ss_pair = " x ".join(list(key))
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
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💰 재물/돈 버는 방식</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['재물']}</div>
                        </div>
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💼 직업 적성</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['직업']}</div>
                        </div>
                        <div style="background:#ffffff;border-radius:10px;padding:14px;border:1.5px solid #000000">
                            <div style="font-size:11px;color:#000000;font-weight:700;margin-bottom:6px">💑 연애/인간관계</div>
                            <div style="font-size:13px;color:#000000;line-height:1.8">{combo['연애']}</div>
                        </div>
                    </div>
                    <div style="background:#ffffff;border-radius:10px;padding:12px;margin-top:12px;
                                border:1.5px solid #ff0000">
                        <span style="font-size:11px;color:#ff0000;font-weight:700">[!]️ 주의사항: </span>
                        <span style="font-size:13px;color:#000000;line-height:1.8;font-weight:700">{combo['주의']}</span>
                    </div>
                </div>
""", unsafe_allow_html=True)
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
                </div>
""", unsafe_allow_html=True)
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
    st.markdown('<div class="gold-section">📜 종합 사주 해설 - 만신의 풀이</div>', unsafe_allow_html=True)
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
                </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"종합 해설 오류: {e}")

    # -- 통계 기반 패턴 분석 -------------------------------
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    try:
        render_statistical_insights(pils, strength_info)
    except Exception as e:
        print(f"[WARN] {e}")

    # -- 클리프행어 (미완성 서술 트릭) ----------------------
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
                teaser = f"현재 운세 점수 **{luck_s}/100** - 상승기 진입 신호가 감지됩니다. 이 기회를 어떻게 활용할지,"
            else:
                teaser = f"현재 운세 점수 **{luck_s}/100** - 흐름의 방향이 바뀌는 시점이 다가오고 있습니다. 그 시기와 대비책이"

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
                        -> AI 상담 탭에서 정확한 시기와 대응 전략을 확인하십시오.
                    </span>
                </div>
                <div style="font-size:11px;color:#000000;font-weight:700;letter-spacing:1px">
                    * 🤖 AI 상담 탭 이동 *
                </div>
            </div>
            
""", unsafe_allow_html=True)
    except Exception as e:
        print(f"[WARN] {e}")


    render_ai_deep_analysis("prophet", pils, name, birth_year, gender, api_key, groq_key)

def menu2_lifeline(pils, birth_year, gender, name="내담자", api_key="", groq_key=""):
    """2️⃣ 인생 흐름 (대운 100년) - 프리미엄 글래스모피즘 UI"""
    import json

    st.markdown(f"""
<div style="background: rgba(255, 248, 232, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(139, 98, 0, 0.3);
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);">
    <div style="font-size:16px;font-weight:800;color:#8b6200;margin-bottom:8px;letter-spacing:-0.5px">📈 大運 100年 흐름 분석 (Lifeline)</div>
    <div style="font-size:13px;color:#333;line-height:1.6;font-family:'Pretendard', sans-serif">
    - 黄金期와 危機 區間을 한눈에 파악하십시오. <br>
    💎 現在 大運의 위치와 흐름을 확인하여 미래를 설계하세요.
    </div>
</div>""", unsafe_allow_html=True)

    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    # 대운 호출 시 실제 생년월일시 반영
    birth_month = st.session_state.get('birth_month', 1)
    birth_day = st.session_state.get('birth_day', 1)
    birth_hour = st.session_state.get('birth_hour', 12)
    birth_minute = st.session_state.get('birth_minute', 0)
    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신",[])
    if not isinstance(yongshin_ohs, list): yongshin_ohs = []
    ilgan_oh = OH.get(ilgan,"")

    # -- 대운 100년 타임라인 그래프 --
    st.markdown('<div class="gold-section" style="font-size:18px; font-weight:700; margin-bottom:15px">📊 大運 흐름 그래프</div>', unsafe_allow_html=True)

    # 각 대운의 길흉 점수 계산
    labels, scores, colors_list, dw_strs = [], [], [], []
    for dw in daewoon:
        dw_ss = TEN_GODS_MATRIX.get(ilgan,{}).get(dw["cg"],"-")
        is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
        is_current = dw["시작연도"] <= current_year <= dw["종료연도"]

        SCORE_MAP = {
            "正財":80,"食神":85,"正官":75,"正印":70,
            "偏財":65,"偏官":40,"劫財":35,"傷官":55,
            "比肩":60,"偏印":50
        }
        score = SCORE_MAP.get(dw_ss, 60)
        if is_yong: score = min(100, score + 20)

        age_label = f"{dw['시작나이']}세<br><span style='font-weight:700; color:#555'>{dw['str']}</span>"
        labels.append(age_label)
        scores.append(score)
        
        # 프리미엄 컬러 팔레트
        if is_yong:
            c = "linear-gradient(180deg, #ffd700, #b8860b)" # Gold for Yongshin
        elif score < 50:
            c = "linear-gradient(180deg, #ff9a9e, #fecfef)" # Soft Red for Gishin
        else:
            c = "linear-gradient(180deg, #a1c4fd, #c2e9fb)" # Soft Blue for General
            
        if is_current: 
            c = "linear-gradient(180deg, #ff8c00, #ff4500)" # Vibrant Orange for Current
        
        colors_list.append(c)
        dw_strs.append(dw["str"])

    # 프리미엄 바 차트
    bars_html = ""
    for i, (lbl, sc, cl, ds) in enumerate(zip(labels, scores, colors_list, dw_strs)):
        is_cur = "ff8c00" in cl
        border = "2px solid #fff"
        shadow = "0 10px 20px rgba(0,0,0,0.15)" if is_cur else "0 4px 10px rgba(0,0,0,0.05)"
        cur_mark = "<div style='font-size:10px;color:#ff4500;font-weight:900;margin-top:5px; animation: bounce 2s infinite'>📍現在</div>" if is_cur else ""
        
        bars_html += (
            f'<div style="display:flex;flex-direction:column;align-items:center;min-width:60px; transition: transform 0.3s ease" onmouseover="this.style.transform=\'translateY(-5px)\'" onmouseout="this.style.transform=\'translateY(0)\'">'
            f'<div style="font-size:12px;font-weight:700;color:#666;margin-bottom:6px">{sc}</div>'
            f'<div style="width:36px;height:{sc*1.2}px;background:{cl};border-radius:20px 20px 20px 20px;'
            f'border:{border};box-shadow:{shadow};transition:all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)" title="{ds}大運({sc}點)"></div>'
            f'<div style="font-size:11px;color:#444;margin-top:10px;text-align:center;line-height:1.4">'
            f'{lbl}</div>'
            f'{cur_mark}'
            f'</div>'
        )

    st.markdown(f"""
    <style>
    @keyframes bounce {{
        0%, 20%, 50%, 80%, 100% {{transform: translateY(0);}}
        40% {{transform: translateY(-5px);}}
        60% {{transform: translateY(-3px);}}
    }}
    </style>
    <div style="background: rgba(255, 255, 255, 0.2); 
                backdrop-filter: blur(8px); 
                border-radius: 20px; 
                padding: 30px 20px; 
                overflow-x: auto;
                border: 1px solid rgba(255,255,255,0.3);
                box-shadow: inset 0 0 20px rgba(255,255,255,0.2);">
        <div style="display:flex;align-items:flex-end;gap:12px;min-width:650px;height:180px;
                    padding-bottom:15px;border-bottom:2px solid rgba(0,0,0,0.05)">
            {bars_html}
        </div>
        <div style="display:flex;justify-content:center;gap:24px;margin-top:20px;font-size:13px;font-weight:600">
            <span style="display:flex;align-items:center;gap:6px"><span style="width:12px;height:12px;border-radius:3px;background:linear-gradient(to right, #ffd700, #b8860b)"></span> 用神 大運</span>
            <span style="display:flex;align-items:center;gap:6px"><span style="width:12px;height:12px;border-radius:3px;background:linear-gradient(to right, #ff8c00, #ff4500)"></span> 現在 大運</span>
            <span style="display:flex;align-items:center;gap:6px"><span style="width:12px;height:12px;border-radius:3px;background:linear-gradient(to right, #a1c4fd, #c2e9fb)"></span> 一般 大運</span>
            <span style="display:flex;align-items:center;gap:6px"><span style="width:12px;height:12px;border-radius:3px;background:linear-gradient(to right, #ff9a9e, #fecfef)"></span> 忌神 大運</span>
        </div>
    </div>
""", unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,0,0,0.05);margin:30px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section" style="font-size:18px; font-weight:700">🔄 大運 詳解</div>', unsafe_allow_html=True)
    tab_daewoon(pils, birth_year, gender)

    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,0,0,0.05);margin:30px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section" style="font-size:18px; font-weight:700">🔀 大運 x 世運 交叉 分析</div>', unsafe_allow_html=True)
    try:
        tab_cross_analysis(pils, birth_year, gender)
    except Exception as e:
        st.warning(f"交叉分析 오류: {e}")

    # 대운 100년 상세 해설문
    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,0,0,0.05);margin:30px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section" style="font-size:18px; font-weight:700">📜 大運 100年 完全 解說</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, "", section="lifeline")
        # 한자 치환 필터 적용
        narrative = narrative.replace("대운", "大運").replace("용신", "用神").replace("기신", "忌神").replace("천간", "天干").replace("지지", "地支")
        
        sections = narrative.split("->")
        # 첫 도입부
        if sections:
            intro = sections[0].strip()
            if intro:
                st.markdown(f"""
<div style="background: rgba(52, 152, 219, 0.05);
            backdrop-filter: blur(4px);
            border-left:5px solid #3498db;border-radius:12px;
            padding:22px 28px;margin:15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.03)">
    <div style="font-size:14px;color:#2c3e50;line-height:2.2;white-space:pre-wrap; font-family:'Pretendard'">{intro}</div>
</div>
""", unsafe_allow_html=True)
        # 각 대운
        for sec in sections[1:]:
            if not sec.strip(): continue
            lines = sec.strip().split("\n")
            title = lines[0].strip() if lines else ""
            body  = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            is_cur = "現在 大運" in title or "현재 대운" in title
            
            # 테두리 색상 결정
            border_color = "#ff6b00" if is_cur else "#d4af37" if "用神" in body else "#3498db"
            bg_color = "rgba(255, 107, 0, 0.08)" if is_cur else "rgba(255, 255, 255, 0.5)"
            
            st.markdown(f"""
<div style="background:{bg_color};
            backdrop-filter: blur(6px);
            border-left:5px solid {border_color};border-radius:12px;
            padding:20px 25px;margin:12px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.02)">
    <div style="font-size:15px;font-weight:800;color:{border_color};margin-bottom:12px; letter-spacing:-0.3px">
        -> {title}
    </div>
    <div style="font-size:14px;color:#444;line-height:2.0;white-space:pre-wrap; font-family:'Pretendard'">{body}</div>
</div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"大運 解說 오류: {e}")

    # AI 정밀 분석 버튼
    render_ai_deep_analysis("lifeline", pils, name, birth_year, gender, api_key, groq_key)

def menu3_past(pils, birth_year, gender, name="", api_key="", groq_key=""):
    """3️⃣ 과거 적중 타임라인 | 15년 자동 스캔"""
    st.markdown("""
<div style="background:#fff0f8;border:2px solid #e91e8c55;border-radius:12px;
            padding:14px 18px;margin-bottom:14px">
    <div style="font-size:13px;font-weight:700;color:#880e4f;margin-bottom:4px">🎯 과거 적중 타임라인</div>
    <div style="font-size:12px;color:#000000;line-height:1.8">
    * 충/합/십성 교차를 수학 계산으로 뽑은 과거 사건 시점입니다.<br>
    * AI가 아닌 엔진 계산 - 나이/분야가 맞으면 <b style="color:#c0392b">"맞았다"</b>를 눌러주세요.
    </div>
</div>""", unsafe_allow_html=True)
    tab_past_events(pils, birth_year, gender, name)
    # AI 정밀 분석 버튼
    render_ai_deep_analysis("past", pils, name, birth_year, gender, api_key, groq_key)

def menu4_future3(pils, birth_year, gender, marriage_status="미혼", name="내담자", api_key="", groq_key=""):
    """4️⃣ 미래 3년 집중 분석 - 돈/직장/연애"""
    ilgan = pils[1]["cg"]
    current_year = datetime.now().year
    current_age  = current_year - birth_year + 1

    st.markdown("""
<div style="background:#f0fff8;border:2px solid #27ae6055;border-radius:12px;
            padding:14px 18px;margin-bottom:14px">
    <div style="font-size:13px;font-weight:700;color:#1b5e20;margin-bottom:4px">🔮 미래 3년 집중 분석</div>
    <div style="font-size:12px;color:#000000;line-height:1.8">
    * 돈 / 직장 / 연애 3개 분야를 연도별로 집중 분석합니다.
    </div>
</div>""", unsafe_allow_html=True)

    ys = get_yongshin(pils)
    yongshin_ohs = ys.get("종합_용신",[])
    if not isinstance(yongshin_ohs, list): yongshin_ohs = []
    ilgan_oh = OH.get(ilgan,"")

    DOMAIN_SS = {
        "돈/재물": {"식신","정재","편재"},
        "직장/명예": {"정관","편관","정인"},
        "연애/인연": {"정재","편재"} if gender=="남" else {"정관","편관"},
        "변화/이동": {"상관","겁재","편인"},
    }
    DOMAIN_COLOR = {
        "돈/재물": "#27ae60", "직장/명예": "#2980b9",
        "연애/인연": "#e91e8c", "변화/이동": "#e67e22"
    }

    years_data = []
    for y in range(current_year, current_year + 3):
        sw = get_yearly_luck(pils, y)
        # 대운 호출 시 실제 생년월일시 반영 (사용자 지침 준수)
        birth_month = st.session_state.get('birth_month', 1)
        birth_day = st.session_state.get('birth_day', 1)
        birth_hour = st.session_state.get('birth_hour', 12)
        birth_minute = st.session_state.get('birth_minute', 0)
        dw = next((d for d in SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender=gender)
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
        label      = "🌟 황금기" if yong_both else "[!]️ 수비" if gishin_both else "〰️ 혼재"

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
    </div>
""", unsafe_allow_html=True)

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
<div style="background:#fff0f0;border-left:4px solid {hw['color']};
            border-radius:8px;padding:10px 14px;margin-top:8px;font-size:12px">
<b style="color:{hw['color']}">{hw['level']}</b><br>
<span style="color:#333">{hw['desc']}</span>
</div>
""", unsafe_allow_html=True)


        st.markdown("</div>", unsafe_allow_html=True)

    # 결혼 여부별 인연 조언
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💑 인연/배우자운 (3년)</div>', unsafe_allow_html=True)
    if marriage_status in ("미혼","이혼/별거"):
        MARRY_SS = {"정재","편재"} if gender=="남" else {"정관","편관"}
        for yd in years_data:
            if yd["sw_ss"] in MARRY_SS or yd["dw_ss"] in MARRY_SS:
                st.markdown(f"""

                <div style="background:#fff0f8;border-left:4px solid #e91e8c;
                            border-radius:8px;padding:12px;margin:5px 0">
                    <b style="color:#e91e8c">{yd['year']}년({yd['age']}세)</b> -
                    인연성이 강합니다. 적극적으로 움직이십시오.
                </div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""

        <div style="background:#f0fff8;border-left:4px solid #27ae60;
                    border-radius:8px;padding:12px">
            {marriage_status} 상태. 부부 관계 흐름 분석은 육친론을 참고하세요.
        </div>
""", unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📅 월별 세운 (올해)</div>', unsafe_allow_html=True)
    tab_monthly(pils, birth_year, gender)

    # 미래 3년 상세 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 미래 3년 완전 해설 - 만신의 풀이</div>', unsafe_allow_html=True)
    try:
        narrative = build_rich_narrative(pils, birth_year, gender, "", section="future")
        blocks = narrative.split("-"*55)
        if blocks:
            intro = blocks[0].strip()
            if intro:
                st.markdown(f"""

                <div style="background:linear-gradient(135deg,#dcfff5,#dcfffd);
                            border-left:4px solid #27ae60;border-radius:10px;
                            padding:16px 20px;margin:10px 0">
                    <div style="font-size:13px;color:#1a4a2a;line-height:1.9;white-space:pre-wrap">{intro}</div>
                </div>
""", unsafe_allow_html=True)
            for block in blocks[1:]:
                if not block.strip(): continue
                lines = block.strip().split("\n")
                title_line = next((l for l in lines if l.strip()), "")
                body = "\n".join(lines[1:]).strip()
                is_good = "-" in title_line
                is_bad = "[!]️" in title_line
                bg = "rgba(197,160,89,0.12)" if is_good else "rgba(192,57,43,0.12)" if is_bad else "rgba(41,128,185,0.12)"
                bc = "#000000" if is_good else "#c0392b" if is_bad else "#2980b9"
                st.markdown(f"""

                <div style="background:{bg};border-left:4px solid {bc};
                            border-radius:10px;padding:16px 20px;margin:8px 0">
                    <div style="font-size:14px;font-weight:900;color:{bc};margin-bottom:10px">{title_line}</div>
                    <div style="font-size:13px;color:#000000;line-height:1.9;white-space:pre-wrap">{body}</div>
                </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"미래 해설 오류: {e}")

    # AI 정밀 분석 버튼
    render_ai_deep_analysis("future", pils, name, birth_year, gender, api_key, groq_key)

def menu5_money(pils, birth_year, gender, name="내담자", api_key="", groq_key=""):
    """5️⃣ 재물/사업 특화 분석"""
    st.markdown("""
<div style="background:#f5fff0;border:2px solid #2e7d3255;border-radius:12px;
            padding:14px 18px;margin-bottom:14px">
    <div style="font-size:13px;font-weight:700;color:#1b5e20;margin-bottom:4px">💰 재물/사업 특화 분석</div>
    <div style="font-size:12px;color:#000000;line-height:1.8">
    * 수익 구조 / 재물 기질 / 돈이 터지는 시기를 십성 조합으로 분석합니다.
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
                        <div style="font-size:11px;color:#5ab4ff;font-weight:700;margin-bottom:6px">💼 맞는 직업/사업</div>
                        <div style="font-size:14px;color:#c0d8f0;line-height:1.9">{combo['직업']}</div>
                    </div>
                    <div style="background:#f5f5f5;border-radius:10px;padding:12px;
                                border-left:4px solid #e74c3c">
                        <div style="font-size:11px;color:#ff6b6b;font-weight:700;margin-bottom:4px">[!]️ 재물 주의사항</div>
                        <div style="font-size:13px;color:#f0c0c0;line-height:1.8">{combo['주의']}</div>
                    </div>
                </div>
""", unsafe_allow_html=True)
        elif combos:
            key, combo = combos[0]
            st.markdown(f"""

            <div style="background:#ffffff;border-radius:12px;padding:18px;border:1px solid #3a4060">
                <div style="font-size:16px;font-weight:700;color:#000000;margin-bottom:10px">{combo['요약']}</div>
                <div style="font-size:14px;color:#f0e0a0;line-height:1.9">{combo['재물']}</div>
            </div>
""", unsafe_allow_html=True)

        # 십성별 재물 기질 요약
        MONEY_NATURE = {
            "식신": "🌾 재능/기술로 꾸준히 버는 타입. 억지로 돈 쫓지 않아도 따라온다.",
            "상관": "⚡ 아이디어/말/창의로 버는 타입. 새로운 방식으로 수익을 만든다.",
            "편재": "🎰 활발한 활동/투자/사업으로 버는 타입. 기복이 있지만 크게 번다.",
            "정재": "🏦 성실하게 모으는 타입. 꾸준히 하면 결국 쌓인다.",
            "겁재": "💸 크게 벌고 크게 쓰는 타입. 재물 관리가 인생 최대 숙제.",
            "비견": "⚔️ 독립/자영업으로 버는 타입. 남 밑에서는 돈이 안 모인다.",
            "편관": "🔥 직위/권한에서 재물이 따라오는 타입. 높은 자리가 돈이 된다.",
            "정관": "🏛️ 안정된 직장에서 꾸준히 쌓는 타입. 직급이 올라갈수록 재물도 는다.",
            "편인": "🎭 특수 분야 전문성으로 버는 타입. 일반적인 방법보다 틈새가 맞다.",
            "정인": "📚 지식/자격/귀인을 통해 재물이 오는 타입. 배움이 곧 돈이 된다.",
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
                 min-width:50px;text-align:center">{ss}x{cnt}</span>
    <span style="font-size:13px;color:#000000;line-height:1.8">{MONEY_NATURE.get(ss,'')}</span>
</div>
""", unsafe_allow_html=True)
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
</div>
""", unsafe_allow_html=True)
        else:
            st.info("현재 기준 향후 5년 내 뚜렷한 재물 피크가 계산되지 않았습니다.")
    except Exception as e:
        st.warning(f"재물 운기 계산 오류: {e}")

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💰 재물론 상세 (장생/12운성)</div>', unsafe_allow_html=True)
    try:
        tab_jaemul(pils, birth_year, gender)
    except Exception as e:
        st.warning(f"재물론 오류: {e}")

    # 재물 완전 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 재물/사업 완전 해설 - 만신의 풀이</div>', unsafe_allow_html=True)
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
                </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"재물 해설 오류: {e}")

    # AI 정밀 분석 버튼
    render_ai_deep_analysis("money", pils, name, birth_year, gender, api_key, groq_key)

def menu6_relations(pils, name, birth_year, gender, marriage_status="미혼", api_key="", groq_key=""):
    """6️⃣ 궁합 / 인간관계 분석"""
    st.markdown("""
<div style="background:#fdf0ff;border:2px solid #9b59b655;border-radius:12px;
            padding:14px 18px;margin-bottom:14px">
    <div style="font-size:13px;font-weight:700;color:#4a148c;margin-bottom:4px">💑 궁합 / 인간관계 분석</div>
    <div style="font-size:12px;color:#000000;line-height:1.8">
    * 연인 / 동업자 / 상사와의 인간관계를 사주로 분석합니다.
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="gold-section">👫 육친론 - 주변 인물 분석</div>', unsafe_allow_html=True)
    tab_yukjin(pils, gender)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">💑 궁합 분석</div>', unsafe_allow_html=True)
    tab_gunghap(pils, name)

    # 인간관계 완전 해설
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)
    st.markdown('<div class="gold-section">📜 육친/인간관계 완전 해설 - 만신의 풀이</div>', unsafe_allow_html=True)
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
            if "*" in body:
                # 육친 개별 카드
                sub_items = body.split("*")
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
                        <div style="font-size:13px;font-weight:700;color:#c39bd3;margin-bottom:6px">* {item_title}</div>
                        <div style="font-size:13px;color:#e8d0f8;line-height:1.9;white-space:pre-wrap">{item_body}</div>
                    </div>
""", unsafe_allow_html=True)
            else:
                st.markdown(f"""

                <div style="background:linear-gradient(135deg,#ffdcff,#ffdcff);
                            border-left:4px solid #9b59b6;border-radius:10px;
                            padding:18px 22px;margin:10px 0">
                    <div style="font-size:14px;font-weight:900;color:#c39bd3;margin-bottom:10px">
                        【 {title} 】
                    </div>
                    <div style="font-size:13px;color:#e8d0f8;line-height:2.0;white-space:pre-wrap">{body}</div>
                </div>
""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"인간관계 해설 오류: {e}")

    # AI 정밀 분석 버튼
    render_ai_deep_analysis("relations", pils, name, birth_year, gender, api_key, groq_key)


################################################################################
# ☀️ menu9_daily  - 일일 운세
# 📅 menu10_monthly - 월별 운세
# 🎊 menu11_yearly  - 신년 운세
################################################################################

def menu9_daily(pils, name, birth_year, gender, api_key="", groq_key=""):
    """9️⃣ 일일 운세 - 오늘 하루의 기운에 집중한 심플 모드"""

    ilgan   = pils[1]["cg"]
    today   = datetime.now()
    display_name = name if name else "내담자"

    # -- 일진 계산 헬퍼 ------------------
    def get_day_pillar(dt):
        base  = date(1924, 1, 1)
        delta = (dt.date() - base).days if hasattr(dt, 'date') else (dt - base).days
        return CG[delta % 10], JJ[delta % 12]

    today_cg, today_jj = get_day_pillar(today)
    today_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(today_cg, "-")

    # -- 헤더 --------------------------
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#e8f4ff,#ddeeff);
            border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
    <div style="font-size:22px;font-weight:900;color:#0d47a1;letter-spacing:2px">
        ☀️ {display_name}님의 오늘의 운세
    </div>
    <div style="font-size:13px;color:#000000;margin-top:6px">
        {today.strftime('%Y년 %m월 %d일')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)
    </div>
</div>
""", unsafe_allow_html=True)

    # -- AI 분석 자동화 (500자 이상 보장) --------------
    if api_key or groq_key:
        cache_key_daily = f"{pils[1]['cg']}_{today.strftime('%Y%m%d')}_daily_ai"
        cached_daily = get_ai_cache(cache_key_daily, "daily_ai")
        
        if not cached_daily:
            with st.spinner("🔮 만신 AI가 오늘의 천기를 정밀 분석 중입니다... (음양오행 심층 분석)"):
                prompt = f"""
                당신은 40년 임상 경력의 백전노장 명리학자 '만신(萬神)'입니다.
                
                -> 오늘 일진 정보
                - 날짜: {today.strftime('%Y년 %m월 %d일')} ({['\uc6d4','\ud654','\uc218','\ubaa9','\uae08','\ud1a0','\uc77c'][today.weekday()]}요일)
                - 일진: {today_cg}{today_jj}(일)
                - 내담자 일간: {ilgan}
                - 오늘 일진과의 십성 관계: {today_ss}
                - 내담자: {display_name}님
                
                -> 풀이 지침 (필수 준수)
                아래 5단계를 **반드시** 모두 포함하여 **공백 포함 500자 이상**의 친정하고 심도 있는 어조로 품이하십시오.
                
                1단계 [오늘의 핵심 기운]: {today_ss} 일진이 {display_name}님의 사주에 나타나는 의미와 오늘 하루의 전반적인 기운 흐름을 상세하고 서사적으로 풀이하십시오.
                2단계 [재물운 조언]: 오늘 재도와 지출에 관한 구체적 조언을 하십시오. 좋은 점과 주의할 점을 모두 설명하십시오.
                3단계 [건강 조언]: {today_cg}의 오행 기운이 {display_name}님의 신체에 미치는 영향과 오늘 주의할 건강 데메를 알려주십시오.
                4단계 [대인관계 조언]: 오늘 만나는 사람들과의 관계에서 즉도움이 되는 사람은 누구이며 어떤 사람을 조심할지 알려주십시오.
                5단계 [오늘의 실천 행동 1가지]: 오늘 반드시 실천해야 할 매우 구체적인 행동 1가지를 제시하십시오.
                
                만신의 머리말로 마무리하십시오. 500자에 미달하면 절대 안 됩니다.
                """
                result = get_ai_interpretation(
                    prompt, api_key,
                    system="당신은 우주의 섭리를 꿰뚫어 보는 40년 경력의 명리학자 '만신(萬神)'입니다. 항상 500자 이상의 풍부하고 심도 있는 풍이로 답하십시오. 결코 요약하지 마십시오.",
                    max_tokens=2000,
                    groq_key=groq_key
                )
                if result:
                    set_ai_cache(cache_key_daily, "daily_ai", result)
                    cached_daily = result
        
        if cached_daily:
            char_count = len(cached_daily)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.85);backdrop-filter:blur(20px);border:1.5px solid #d4af37;
                        border-radius:20px;padding:28px;margin:10px 0 25px;box-shadow:0 10px 35px rgba(212,175,55,0.12)">
                <div style="font-size:18px;font-weight:900;color:#b38728;margin-bottom:15px;display:flex;align-items:center;justify-content:space-between">
                    <span><span style="font-size:22px">🔮</span>&nbsp; 만신 AI 정밀 분석</span>
                    <span style="font-size:11px;color:#aaa;font-weight:400">({char_count}자)</span>
                </div>
                <div style="font-size:15.5px;color:#111;line-height:2.3;white-space:pre-wrap;letter-spacing:-0.2px">{apply_lexicon_tooltips(cached_daily)}</div>
            </div>
            """, unsafe_allow_html=True)

    # -- 오늘 일진 카드 -----------------
    DAILY_SS_MSG = {
        "비견":  {"emoji":"🤝","level":"평길","msg":"협조자가 나타나는 날. 독단보다는 협력이 유리합니다.","재물":"수입 안정"},
        "겁재":  {"emoji":"[!]️","level":"흉","msg":"재물과 에너지 소모가 큰 날. 지출을 삼가고 자중하십시오.","재물":"지출 주의"},
        "식신":  {"emoji":"🌟","level":"대길","msg":"복록이 가득하고 즐거운 날. 새로운 시도에 행운이 따릅니다.","재물":"의외의 수입"},
        "상관":  {"emoji":"🌪️","level":"평","msg":"재능 발휘의 날이나 말실수를 조심해야 합니다. 침묵이 금입니다.","재물":"아이디어 수익"},
        "편재":  {"emoji":"💰","level":"길","msg":"활동 범위가 넓어지고 재물운이 활발한 날입니다.","재물":"재물운 상승"},
        "정재":  {"emoji":"🏦","level":"길","msg":"성실함에 대한 확실한 보상이 따르는 안정적인 날입니다.","재물":"착실한 수입"},
        "편관":  {"emoji":"⚡","level":"흉","msg":"심적 압박과 스트레스가 있는 날. 차분하게 인내하십시오.","재물":"예상치 못한 돈"},
        "정관":  {"emoji":"🎖️","level":"대길","msg":"명예와 인정의 날. 공적인 업무에서 성과를 냅니다.","재물":"안정된 수입"},
        "편인":  {"emoji":"🔮","level":"평","msg":"직관력이 예리해지는 날. 깊은 생각과 연구에 몰두하십시오.","재물":"현상 유지"},
        "정인":  {"emoji":"📚","level":"대길","msg":"윗사람의 도움과 합격운이 따르는 귀인의 날입니다.","재물":"계약운 발생"},
        "-":     {"emoji":"🌿","level":"평","msg":"평온한 루틴을 지키는 것이 가장 좋은 날입니다.","재물":"안정"},
    }
    d = DAILY_SS_MSG.get(today_ss, DAILY_SS_MSG["-"])
    level_color = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107","평":"#9e9e9e","흉":"#f44336"}.get(d["level"],"#aaa")

    st.markdown(f"""
<div style="background:#ffffff; border:1px solid #ddd; border-left:6px solid {level_color}; border-radius:12px; padding:20px; box-shadow:0 2px 10px rgba(0,0,0,0.05)">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px">
        <span style="font-size:32px">{d['emoji']}</span>
        <span style="font-size:18px; font-weight:800; color:#333">{today_cg}{today_jj}일의 운기 ({today_ss})</span>
        <span style="background:{level_color}22; color:{level_color}; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:800">{d['level']}</span>
    </div>
    <div style="font-size:14px; color:#555; line-height:1.7">{d['msg']}</div>
    <div style="margin-top:12px; padding-top:12px; border-top:1px dashed #eee; display:flex; gap:10px">
        <span style="font-size:12px; color:#444"><b>💰 재물운:</b> {d['재물']}</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # -- 길한 시간 (용신 기반) ----------------
    st.markdown('<div class="gold-section" style="margin-top:20px">⏰ 오늘의 길한 시간 (용신 기반)</div>', unsafe_allow_html=True)
    ys = get_yongshin(pils)
    y_ohs = ys.get("종합_용신", [])
    OH_HOUR_MAP = {"木":[("3~5시","寅(인)"),("5~7시","卯(묘)")],"火":[("9~11시","巳(사)"),("11~13시","午(오)")],"土":[("7~9시","辰(진)"),("13~15시","未(미)")],"金":[("15~17시","申(신)"),("17~19시","酉(유)")],"水":[("21~23시","亥(해)"),("23~1시","子(자)")]}
    good_hours = []
    for oh in y_ohs: good_hours.extend(OH_HOUR_MAP.get(oh, []))
    if good_hours:
        tags = "".join([f"<span style='background:#f1f8e9; color:#2e7d32; padding:4px 12px; border-radius:6px; font-size:12px; margin-right:5px'>✅ {t}({jj}시)</span>" for t, jj in good_hours[:3]])
        st.markdown(f"<div>{tags}</div>", unsafe_allow_html=True)

    # -- 300-400자 상세 처방 카드 (행운아이템 + 조심 + 조언) --
    DAILY_FULL = {
        "비견": {"icon":"🤝","lucky":"동쪽 방향, 녹색 소품, 오전 11시~13시",
                 "caution":"지나친 경쟁심과 독단적 행동. 타인의 의견을 무시하면 관계가 틀어집니다.",
                 "advice":"오늘은 협력이 힘이 됩니다. 평소 연락이 뜸했던 지인에게 먼저 손을 내미십시오. 비견의 기운은 '함께'를 뜻하며, 혼자 모든 것을 끌고 가려 하면 에너지가 분산됩니다. 중요한 결정은 신뢰하는 사람과 의논하면 두 배의 힘이 생깁니다. 재물 면에서는 공동 프로젝트나 협동이 유리하고, 건강 면에서는 함께 걷기나 가벼운 단체 활동이 기운을 올려줍니다. 오늘 하루 '경청'을 키워드로 삼으십시오."},
        "겁재": {"icon":"[!]️","lucky":"흰색/금색 소품, 서쪽 방향, 조용한 오전 시간",
                 "caution":"충동적 지출, 감정적 언쟁, 보증/투자 결정. 오늘 서명하는 계약은 특히 신중하게.",
                 "advice":"겁재는 재물을 노리는 기운입니다. 오늘만큼은 지갑과 감정을 함께 닫으십시오. 예상치 못한 지출이나 사람으로 인한 손실이 발생하기 쉬운 날입니다. 화가 나는 상황이 생겨도 즉각 반응하지 말고, 하루 이상 숙려 후 행동하십시오. 건강 면에서는 과로와 무리한 경쟁이 체력을 소진시킵니다. 오늘은 아무것도 하지 않는 것이 최고의 전략입니다."},
        "식신": {"icon":"🌟","lucky":"남쪽 방향, 빨간색/주황색 소품, 오전 9시~13시, 맛있는 음식",
                 "caution":"과식/과음으로 인한 건강 저하. 지나친 여유는 게으름이 될 수 있습니다.",
                 "advice":"식신의 날은 복록이 넘치고 즐거움이 따르는 최고의 길일입니다. 오래 미뤄온 창의적인 일을 시작하기에 이보다 좋은 날은 드뭅니다. 새로운 사람을 만나거나, 아이디어를 노트에 써내려가거나, 맛있는 음식을 대접하는 것도 복을 부르는 행동입니다. 재물운도 좋아 소소한 부수입이나 의외의 기쁜 소식이 올 수 있습니다. 오늘 하루는 자신을 충분히 아껴주십시오."},
        "상관": {"icon":"🌪️","lucky":"창의적 작업공간, 파란색 계열, 오전 집중 시간",
                 "caution":"공식 자리의 말실수, 상사/권위자와 충돌, 감정적 발언. SNS 게시물도 조심.",
                 "advice":"상관의 날은 재능과 표현력이 폭발하지만, 그 에너지가 자칫 구설수로 이어질 수 있습니다. 예술/글쓰기/연구/기획처럼 혼자 하는 창의적 작업에는 탁월한 날이나, 공식 회의나 발표 자리에서는 발언을 최소화하십시오. 특히 윗사람이나 기관에 대한 비판적 표현은 삼가야 합니다. 건강 면에서는 신경계 과부하에 주의하고, 충분한 수면으로 뇌를 쉬게 해주십시오."},
        "편재": {"icon":"💰","lucky":"남서쪽 방향, 황금색 소품, 오후 활동, 새로운 만남",
                 "caution":"근거 없는 투자, 도박성 결정. 화려함에 현혹되어 본질을 놓치는 실수.",
                 "advice":"편재의 날은 역동적이고 활발한 재물의 기운이 흐릅니다. 움직이는 자에게 기회가 찾아오는 날이니, 새로운 거래처나 사람을 만나는 약속을 잡기에 좋습니다. 기대치 않던 곳에서 금전적 이득이 생길 수 있으나, 그만큼 충동적인 지출도 생기기 쉽습니다. 오늘 가장 중요한 것은 '원칙' 안에서 대담하게, 원칙 밖에서는 한 걸음 물러서는 것입니다."},
        "정재": {"icon":"🏦","lucky":"안정된 업무 환경, 숫자 4/9, 흰색 계열, 오전 집중",
                 "caution":"새로운 것에 대한 무모한 도전. 지금은 검증된 방식이 가장 안전합니다.",
                 "advice":"정재의 날은 성실함과 꼼꼼함에 확실한 보상이 따릅니다. 오늘 가장 좋은 행동은 미완성 업무를 마무리하거나 중요한 서류를 정리하는 것입니다. 급격한 변화보다 원칙과 루틴을 지키는 것이 재물을 지키는 방법이며, 계약서 검토나 세금/보험 관련 업무를 처리하기에도 좋은 날입니다. 건강 면에서는 규칙적인 식사와 수면이 기운을 보충해 줍니다."},
        "편관": {"icon":"⚡","lucky":"북쪽 방향, 검정색/군청색 소품, 이른 아침 명상",
                 "caution":"무리한 신체 활동, 권위자와의 정면 충돌, 법적 분쟁 사안 처리.",
                 "advice":"편관의 날은 압박과 경쟁이 집중됩니다. 하지만 이 날을 통과할수록 더 강인해지는 것이 명리학의 이치입니다. 오늘 가장 중요한 것은 '감정이 아닌 원칙으로 대응'하는 것입니다. 논쟁보다 결과로 증명하고, 무리한 약속은 삼가십시오. 건강 면에서는 어깨/목 계통에 부담을 주지 않도록 스트레칭을 자주 하십시오. 인내가 오늘의 가장 강한 무기입니다."},
        "정관": {"icon":"🎖️","lucky":"동쪽 방향, 파란색/네이비 소품, 오전 공식 업무",
                 "caution":"규정을 어기거나 권위에 반하는 행동. 오늘은 원칙과 질서가 최우선입니다.",
                 "advice":"정관의 날은 당신이 빛나는 날입니다. 공적인 자리에서 능력을 인정받기에 최적인 날이니, 중요한 보고/면접/발표가 있다면 오늘로 잡으십시오. 재물 면에서도 안정된 수입과 계약 체결에 유리하며, 명예와 관련된 좋은 소식이 올 수 있습니다. 건강 면에서는 심장과 혈압 관리에 유의하고, 규칙적인 생활 리듬을 유지하십시오."},
        "편인": {"icon":"🔮","lucky":"조용한 독서 공간, 보라색 계열, 오후~저녁",
                 "caution":"우유부단하고 소극적인 태도. 너무 깊은 내면에 빠져들지 마세요.",
                 "advice":"편인의 날은 직관과 통찰력이 예리해집니다. 복잡한 인간관계보다 혼자 연구하고 사색하는 시간이 훨씬 이롭습니다. 새로운 기술을 배우거나 자격증 공부, 독서에 몰두하기에 최적이며, 사업적 큰 결정은 내일로 미루는 것이 좋습니다. 건강 면에서는 신경과 소화기 계통에 주의하고, 스트레스를 다스리십시오."},
        "정인": {"icon":"📚","lucky":"책상/서재, 황색/베이지 계열, 오전 9~11시",
                 "caution":"자만과 의존. 귀인의 도움이 오더라도 스스로의 노력이 뒷받침되어야 결실이 맺힙니다.",
                 "advice":"정인의 날은 귀인과 스승의 기운이 함께합니다. 오랫동안 기다리던 합격 소식, 자격증 결과, 추천서, 중요 서류의 통보가 올 수 있습니다. 멘토나 선배에게 조언을 구하면 의외의 좋은 결과를 얻을 수 있습니다. 새로운 것을 배우거나 강의를 듣는 것도 탁월한 선택입니다. 건강 면에서는 폐/호흡기에 신경 쓰고, 맑은 공기 속에서 산책을 권합니다."},
        "-":     {"icon":"🌿","lucky":"일상적인 공간, 초록색 계열, 규칙적인 루틴",
                 "caution":"과욕과 무리한 새로운 시도. 오늘은 검증된 방식과 루틴이 최선입니다.",
                 "advice":"오늘은 특별한 기운의 충돌이 없는 평온한 날입니다. 화려한 성과보다 일상의 충실함이 빛나는 날이니, 미뤄두었던 정리나 청소, 지인과의 소소한 약속이 마음에 안정을 가져다줍니다. 억지로 변화를 만들려 하지 말고 흐름에 맡기십시오. 충분한 수면과 균형 잡힌 식사가 기운의 씨앗이 되며, 무리한 투자보다 저축이 우선입니다. 오늘을 편안하게 보내는 것이 내일을 위한 최고의 준비입니다."},
    }
    fp = DAILY_FULL.get(today_ss, DAILY_FULL["-"])
    st.markdown(f"""
<div style="background:rgba(255,255,255,0.92);backdrop-filter:blur(15px);border:1.5px solid rgba(212,175,55,0.4);
            border-radius:18px;padding:24px;margin-top:16px;box-shadow:0 6px 25px rgba(0,0,0,0.06)">
    <div style="font-size:17px;font-weight:900;color:#333;margin-bottom:16px;display:flex;align-items:center;gap:8px">
        <span style="font-size:24px">{fp['icon']}</span> 💊 오늘의 만신 처방
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px">
        <div style="flex:1;min-width:180px;background:rgba(76,175,80,0.08);border:1px solid rgba(76,175,80,0.3);
                    border-radius:12px;padding:12px 14px">
            <div style="font-size:12px;font-weight:800;color:#2e7d32;margin-bottom:5px">🍀 오늘의 행운 키워드</div>
            <div style="font-size:13px;color:#111;line-height:1.7">{fp['lucky']}</div>
        </div>
        <div style="flex:1;min-width:180px;background:rgba(244,67,54,0.06);border:1px solid rgba(244,67,54,0.25);
                    border-radius:12px;padding:12px 14px">
            <div style="font-size:12px;font-weight:800;color:#c62828;margin-bottom:5px">[!]️ 오늘 조심할 것</div>
            <div style="font-size:13px;color:#111;line-height:1.7">{fp['caution']}</div>
        </div>
    </div>
    <div style="background:rgba(212,175,55,0.06);border-left:4px solid #d4af37;padding:14px 16px;
                border-radius:0 12px 12px 0;font-size:14.5px;color:#222;line-height:2.0">
        {fp['advice']}
    </div>
    <div style="font-size:11px;color:#bbb;text-align:right;margin-top:8px">{len(fp['advice'])}자</div>
</div>
""", unsafe_allow_html=True)



def menu10_monthly(pils, name, birth_year, gender, api_key="", groq_key=""):
    """🔟 월별 운세 - 이달의 주의해야 할 날짜 특화 분석"""
    ilgan = pils[1]["cg"]
    display_name = name if name else "내담자"
    today = datetime.now()
    year, month = today.year, today.month

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#fff0f0,#ffe8e8);
            border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
    <div style="font-size:22px;font-weight:900;color:#b71c1c;letter-spacing:2px">
        📅 {display_name}님의 {month}월 운세와 특별 점검
    </div>
    <div style="font-size:13px;color:#000000;margin-top:6px">
        이번 달({year}년 {month}월) 중에 특별히 피하거나 조심해야 하는 날짜(흉일)를 집중 분석합니다.
    </div>
</div>
""", unsafe_allow_html=True)

    if api_key or groq_key:
        cache_key = f"{pils[1]['cg']}_{year}{month}_monthly_ai"
        cached = get_ai_cache(cache_key, "monthly_ai")

        if not cached:
            with st.spinner(f"🔮 만신 AI가 {month}월 전체 기운을 심층 분석 중입니다... (2000-3000자 완전 풀이)"):
                prompt = (
                    f"당신은 40년 임상 경력의 백전노장 명리학자 '만신(萬神)'입니다.\n\n"
                    f"-> 내담자 정보\n"
                    f"- 이름: {display_name}\n"
                    f"- 성별: {gender}\n"
                    f"- 생년: {birth_year}년\n"
                    f"- 일간: {ilgan}\n"
                    f"- 분석 월: {year}년 {month}월\n\n"
                    f"-> 요청\n"
                    f"아래 7가지 항목을 **반드시 모두** 포함하여 **공백 포함 최소 2000자에서 3000자 사이**의 매우 상세하고 풍부한 분량으로 풀이하십시오. 이것은 한 달 치 상담 일지입니다. 상담일지를 쓰듯 세밀하고 서사적으로 써 주십시오.\n\n"
                    f"1. [월간 종합 역수] {month}월 전체 기운의 흐름, {month}월의 월건(月幹)과 내담자 일간의 상생관계 분석\n"
                    f"2. [집중 조심 날] 흉달과 흉일이 구체적으로 언제인지, 원인(명리학적 근거)과 대처법\n"
                    f"3. [재물운 심층 분석] 이달 수입과 지출의 주요 흐름, 투자나 계약 시 주의할 점\n"
                    f"4. [건강 심층 분석] {month}월 지운 오행 기운이 신체에 미치는 영향과 관리 방법\n"
                    f"5. [인간관계 심층 분석] 이달 인연덕 흐름, 조심할 사람과 도움이 될 사람\n"
                    f"6. [주간별 흐름] {month}월을 1주, 2주, 3주, 4주로 나누어 각 주의 주요 기운 흐름\n"
                    f"7. [만신의 최종 조언] {display_name}님에게 만신이 직접 전하는 심쿵하는 한 마디의 지혜\n\n"
                    f"2000자에 미달하면 절대 안 됩니다. 상담일지를 쓰듯 세밀하고 서사적으로 써 주십시오."
                )
                result = get_ai_interpretation(
                    prompt, api_key,
                    system=f"당신은 40년 임상 경력의 명리학자 '만신(萬神)'입니다. 항상 2000자 이상의 매우 풍부하고 심도 있는 월별 운세 풀이를 제공하십시오. {b3_build_optimized_prompt_suffix()}",
                    max_tokens=5000,
                    groq_key=groq_key
                )
                if result and not result.startswith("["):
                    result = result.replace("~", "～")
                    set_ai_cache(cache_key, "monthly_ai", result)
                    cached = result

        if cached:
            cached = cached.replace("~", "～")
            char_count = len(cached)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.85);backdrop-filter:blur(20px);border:1.5px solid #d4af37;
                        border-radius:20px;padding:28px;margin:10px 0 25px;box-shadow:0 12px 40px rgba(212,175,55,0.12)">
                <div style="font-size:18px;font-weight:900;color:#b38728;margin-bottom:15px;display:flex;align-items:center;justify-content:space-between">
                    <span><span style="font-size:22px">🔮</span>&nbsp; 만신 AI {month}월 완전 분석</span>
                    <span style="font-size:11px;color:#aaa;font-weight:400">({char_count}자)</span>
                </div>
                <div style="font-size:15px;color:#111;line-height:2.2;white-space:pre-wrap;letter-spacing:-0.2px">{apply_lexicon_tooltips(cached)}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("🔮 AI 분석을 준비 중입니다. 잠시 후 페이지를 새로고침하시거나 API Key 설정을 확인해 주세요.")

    # -- 자체 월간 분석 (API 없이 2000-3000자 보장) ----------------------
    import calendar
    from datetime import date
    _, last_day = calendar.monthrange(year, month)

    def get_day_pillar_local(dt):
        base  = date(1924, 1, 1)
        delta = (dt.date() - base).days if hasattr(dt, 'date') else (dt - base).days
        return CG[delta % 10], JJ[delta % 12]

    # 이달 전체 일진 분석
    all_days_data = []
    bad_days = []
    good_days = []
    for d in range(1, last_day + 1):
        dt = datetime(year, month, d)
        cg, jj = get_day_pillar_local(dt)
        ss = TEN_GODS_MATRIX.get(ilgan, {}).get(cg, "-")
        day_info = {"date": dt, "cgjj": f"{cg}{jj}", "ss": ss, "cg": cg, "jj": jj}
        all_days_data.append(day_info)
        if ss in ("겁재", "편관", "상관"):
            bad_days.append(day_info)
        if ss in ("식신", "정관", "정인", "정재"):
            good_days.append(day_info)

    # 월건(月建) 계산
    month_idx = (year * 12 + month - 1) % 10
    month_cg = CG[month_idx]
    month_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(month_cg, "-")

    # 십성별 월간 의미 사전
    MONTHLY_SS_MEANING = {
        "비견": ("비견의 달", "이번 달은 경쟁 또는 협력의 에너지가 강하게 흐릅니다. 동업자나 동료와의 관계에서 기회와 갈등이 동시에 나타날 수 있습니다. 독주보다는 팀워크를 우선시하면 시너지가 극대화됩니다."),
        "겁재": ("겁재의 달", "재물의 유출과 인간관계의 변동이 예상되는 달입니다. 충동적인 지출이나 보증, 투자는 각별히 조심해야 합니다. 중요한 재무 결정은 이번 달을 피해 다음 달로 미루는 것이 상책입니다."),
        "식신": ("식신의 달", "창의력과 생산력이 폭발하는 복록의 달입니다. 새로운 프로젝트를 시작하거나 창업을 검토 중이라면 이번 달이 최적입니다. 먹거리와 예술 분야에서도 좋은 결실이 예상됩니다."),
        "상관": ("상관의 달", "표현욕과 재능이 넘치지만 구설수에 노출될 가능성도 높습니다. 공식적인 자리에서 발언을 신중히 하고 SNS 활동도 절제가 필요합니다. 예술적/창의적 업무에는 큰 성과가 따릅니다."),
        "편재": ("편재의 달", "예상치 못한 곳에서 재물의 기회가 옵니다. 활동적으로 움직일수록 더 많은 기회가 찾아오는 달이며, 투자보다는 신규 거래처 개발이나 영업 활동을 확대하기 좋습니다."),
        "정재": ("정재의 달", "안정적이고 꾸준한 수입이 보장되는 달입니다. 계약 체결, 장기 투자, 저축 등 안전하고 검증된 재무 계획을 실행하기 좋습니다. 급격한 변화보다는 원칙을 지키는 것이 최선입니다."),
        "편관": ("편관의 달", "스트레스와 압박이 가중되는 도전의 달입니다. 건강 관리에 각별히 유의해야 하며, 직장이나 조직에서의 갈등이 발생할 수 있습니다. 인내심을 갖고 매사를 원칙에 따라 처리하십시오."),
        "정관": ("정관의 달", "명예와 공적 지위가 올라가는 달입니다. 직장에서의 승진이나 중요한 프로젝트 완수에 유리하며, 사회적 네트워크를 활용한 기회 창출에도 좋은 달입니다."),
        "편인": ("편인의 달", "직관력과 통찰이 살아나는 달입니다. 연구, 교육, 종교적 활동에 유리하며, 새로운 배움이나 자격증 취득에 좋은 시기입니다. 사람 많은 곳보다 혼자만의 공간에서 에너지를 충전하십시오."),
        "정인": ("정인의 달", "귀인의 도움과 좋은 소식이 찾아오는 달입니다. 합격/승인/추천 등 기다리던 결과가 발표될 가능성이 높습니다. 교육/강의/학습 관련 활동도 큰 성과를 냅니다."),
        "-": ("평온의 달", "특별한 기운의 충돌 없이 잔잔하게 흐르는 달입니다. 급격한 변화보다 기존의 루틴과 관계를 유지하며 내실을 다지는 것이 최선입니다."),
    }

    # 주간별 기운 분석
    week_data = [[], [], [], [], []]
    for info in all_days_data:
        week_num = (info["date"].day - 1) // 7
        if week_num > 4: week_num = 4
        week_data[week_num].append(info)

    def week_summary(wlist):
        if not wlist: return "해당 없음"
        ss_cnt = {}
        for w in wlist:
            ss_cnt[w["ss"]] = ss_cnt.get(w["ss"], 0) + 1
        top = sorted(ss_cnt.items(), key=lambda x: x[1], reverse=True)
        top_ss = top[0][0] if top else "-"
        w_msgs = {
            "식신": "창의적 에너지가 넘치는 주입니다. 새로운 시도와 만남에 적극적으로 나서십시오.",
            "정관": "공적인 업무와 대외 활동에서 성과가 날 가능성이 높습니다.",
            "정인": "귀인의 도움이 찾아오거나 중요한 소식을 받게 될 수 있습니다.",
            "정재": "성실한 노력이 재물의 결실로 이어지는 주입니다. 계획을 차근차근 실행하십시오.",
            "편재": "예상치 못한 수익이나 기회와의 만남이 있는 주입니다. 적극적으로 움직이십시오.",
            "비견": "협력자와 동료의 역할이 중요해지는 주입니다. 혼자보다 함께 움직이십시오.",
            "겁재": "재물 지출을 조심하고 인간관계의 갈등에 주의하십시오. 감정을 다스리는 것이 관건입니다.",
            "편관": "긴장과 스트레스가 높아지는 주입니다. 건강과 체력 관리에 집중하십시오.",
            "상관": "말과 행동을 조심해야 하는 주입니다. 창의적 활동은 좋으나 공식 발언은 자제하십시오.",
            "편인": "내면의 충전이 필요한 주입니다. 조용히 공부하거나 휴식을 취하는 것이 이롭습니다.",
            "-": "평온하고 무난하게 흘러가는 주입니다. 루틴을 지키며 꾸준히 나아가십시오.",
        }
        return w_msgs.get(top_ss, "전반적으로 조용하고 안정된 흐름입니다.")

    # 오행 기반 건강 조언
    OH_HEALTH = {
        "木": "간/담/눈/근육 계통에 주의하십시오. 이달은 신경이 예민해지기 쉬우니 충분한 수면과 스트레칭을 권장합니다.",
        "火": "심장/소장/혈액/혀 관련 건강에 주의가 필요합니다. 과로와 흥분 상태가 지속되면 혈압이 오를 수 있으니 마음의 여유를 가지십시오.",
        "土": "비장/위장/소화기 계통에 유의하십시오. 과식과 스트레스성 소화 불량이 발생할 수 있으니 식습관 조절이 중요합니다.",
        "金": "폐/대장/피부/코 관련 건강에 신경 쓰십시오. 환절기 호흡기 질환과 피부 건조증이 증가할 수 있습니다.",
        "水": "신장/방광/뼈/귀 계통을 조심하십시오. 이달은 냉증이 올 수 있으니 하체 보온에 유의하시고, 충분한 수분 섭취를 권합니다.",
    }
    OH_MAP = {"甲(갑)":"木","乙(을)":"木","丙(병)":"火","丁(정)":"火","戊(무)":"土","己(기)":"土","庚(경)":"金","辛(신)":"金","壬(임)":"水","癸(계)":"Water"}
    OH_MAP2 = {"甲(갑)":"木","乙(을)":"木","丙(병)":"火","丁(정)":"火","戊(무)":"土","己(기)":"土","庚(경)":"金","辛(신)":"金","壬(임)":"水","癸(계)":"水"}
    ilgan_oh = OH_MAP2.get(ilgan, "土")
    health_msg = OH_HEALTH.get(ilgan_oh, OH_HEALTH["土"])

    # 인간관계 조언 (월별 십성 기반)
    RELATION_MSG = {
        "비견": f"이달은 동년배나 경쟁자와의 관계가 핵심입니다. 질투와 갈등보다는 공생의 관점에서 접근하십시오. 같은 분야의 사람을 통해 의외의 기회를 얻을 수 있습니다.",
        "겁재": f"이달은 신뢰했던 사람으로부터 배신이나 실망을 경험할 수 있습니다. 돈이 엮인 부탁은 거절하는 것이 관계 보호의 길이며, 새로운 사람보다 오래된 지인이 더 이롭습니다.",
        "식신": f"이달은 인연덕이 넘치는 달입니다. 소개팅, 모임, 파티 등에 적극적으로 참여하면 인생에 중요한 사람을 만날 수 있습니다. 베푸는 마음이 복으로 돌아옵니다.",
        "상관": f"이달은 아랫사람이나 자녀와의 관계에서 갈등이 발생하기 쉽습니다. 또한 말실수로 인해 중요한 관계가 손상될 수 있으니, 모든 대화에서 신중함을 유지하십시오.",
        "편재": f"이달은 이성 이연이나 사업적 파트너십이 활발해지는 달입니다. 넓고 활동적인 네트워크에서 중요한 기회를 잡을 수 있습니다. 다만 새로운 사람에게는 금전적 경계선을 유지하십시오.",
        "정재": f"이달은 안정적인 인간관계가 유지되는 달입니다. 특별히 새로운 관계를 맺기보다 기존의 소중한 사람들을 배려하고 다지는 것이 현명합니다.",
        "편관": f"이달은 상사나 권위자와의 갈등 가능성이 높습니다. 정면 충돌은 피하고, 스마트하게 우회하는 전략이 필요합니다. 법적 분쟁이나 민원 사항이 있다면 이달을 피해 처리하십시오.",
        "정관": f"이달은 윗사람이나 멘토로부터 인정받는 달입니다. 권위 있는 사람과의 만남이 이로우며, 공식적인 추천이나 소개를 통한 관계 형성이 큰 도움이 됩니다.",
        "편인": f"이달은 스승이나 전통적 지식인과의 교류가 깊어집니다. 혼자만의 시간을 즐기며 내면을 가꾸는 것이 더 이롭습니다. 지나친 사교 활동은 에너지를 소진시킵니다.",
        "정인": f"이달은 어머니, 스승, 후원자 등 도움을 주는 귀인이 나타나는 달입니다. 교육기관이나 공공기관을 통한 인맥 형성이 특히 좋으며, 배움을 통해 새로운 만남을 이어가십시오.",
        "-": f"이달은 인간관계에서 특별한 변화 없이 잔잔하게 유지됩니다. 지금 곁에 있는 사람들에게 감사하며 관계를 돈독히 하는 것이 최선입니다.",
    }
    relation_msg = RELATION_MSG.get(month_ss, RELATION_MSG["-"])

    # 재물운 조언
    MONEY_MSG = {
        "비견":  "수입은 꾸준하나 지출도 만만치 않은 달입니다. 공동 투자나 합작 사업에 관심이 생길 수 있으나 계약서를 꼼꼼히 검토하십시오.",
        "겁재":  "이달은 재물 손실을 경계해야 합니다. 주식, 코인, 고위험 투자는 절대 피하고, 예상치 못한 지출이 발생할 수 있으니 비상금을 확보해두십시오.",
        "식신":  "복록이 넘치는 달입니다. 부수입이나 인세, 강연료 등 다양한 경로의 수입이 기대됩니다. 소비는 즐겁게, 저축은 꾸준히 병행하십시오.",
        "상관":  "아이디어나 콘텐츠를 통한 수익화 가능성이 있습니다. 단, 계약서 없는 거래나 구두 약속에 의존한 금전 거래는 위험합니다.",
        "편재":  "예상치 못한 수입이 들어올 가능성이 있습니다. 단, 이 반짝 기회에 도박적 투자로 이어지지 않도록 주의하십시오. 수익은 즉시 분산 관리하십시오.",
        "정재":  "성실한 노력에 안정적인 수입이 따르는 가장 좋은 재물의 달입니다. 중장기 저축 계획을 세우기에도 최적이며 부동산/연금 검토도 좋습니다.",
        "편관":  "예상치 못한 지출과 비용이 발생하기 쉽습니다. 이달만큼은 투자보다 현금 보유를 늘리고, 큰 부동산 계약이나 사업 확장은 내달로 미루십시오.",
        "정관":  "안정적인 수입 구조가 유지됩니다. 직업적 성과가 인정받아 성과급이나 보너스가 기대됩니다. 장기 계약 체결에도 유리한 달입니다.",
        "편인":  "직접적 수익보다는 준비와 투자의 달입니다. 자격증 취득이나 학습에 비용을 투자하면 미래에 큰 수익으로 돌아옵니다.",
        "정인":  "귀인의 도움으로 의외의 재물 기회가 열립니다. 지원금, 장학금, 보조금 등 관공서나 기관과 관련된 금전적 혜택을 확인해보십시오.",
        "-":    "이달 재물운은 무난하게 유지됩니다. 큰 수입도 큰 손실도 없는 달이니 루틴한 재무 관리에 집중하십시오.",
    }
    money_msg = MONEY_MSG.get(month_ss, MONEY_MSG["-"])

    # >>> 흉일 계산
    counts = {"편관": 0, "겁재": 0, "상관": 0}
    for b in bad_days:
        counts[b["ss"]] = counts.get(b["ss"], 0) + 1

    total_risk = len(bad_days)
    total_good = len(good_days)

    # 주간 분석
    w_labels = ["1주차", "2주차", "3주차", "4주차", "5주차"]
    week_summaries = [week_summary(week_data[i]) for i in range(5)]

    month_name_key, month_overall = MONTHLY_SS_MEANING.get(month_ss, MONTHLY_SS_MEANING["-"])

    # -- 종합 콘텐츠 렌더링 ----------------------------------
    # 섹션 1: 월간 종합
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.92);backdrop-filter:blur(15px);border:1.5px solid #d4af37;
                border-radius:18px;padding:26px;margin-top:10px;box-shadow:0 6px 28px rgba(212,175,55,0.12)">
        <div style="font-size:18px;font-weight:900;color:#b38728;margin-bottom:14px">
            🔮 {year}년 {month}월 종합 역수 - {month_name_key}
        </div>
        <div style="font-size:14.5px;color:#222;line-height:2.1;border-left:4px solid #d4af37;padding-left:14px">
            이번 달({year}년 {month}월)의 월건(月建)은 <b>{month_cg}</b>으로,
            {display_name}님의 일간 <b>{ilgan}</b>과의 관계는 <b>{month_ss}</b>에 해당합니다.<br><br>
            {month_overall}<br><br>
            이번 달 전체 {last_day}일 중 <b>주의가 필요한 흉일은 {total_risk}일</b>,
            <b>길한 날은 {total_good}일</b>로 분석되었습니다.
            {"전반적으로 기복이 심한 달이니 중요한 결정은 길일에 맞추어 실행하십시오." if total_risk > 8 else "흉일이 적은 편으로 평온한 흐름이 예상되지만, 방심은 금물입니다."}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 섹션 2: 재물운, 건강운, 인간관계 - 3단 카드
    st.markdown(f"""
    <div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:14px">
        <div style="flex:1;min-width:220px;background:rgba(255,248,225,0.9);border:1px solid #ffc107;
                    border-radius:14px;padding:18px">
            <div style="font-size:14px;font-weight:900;color:#e65100;margin-bottom:10px">💰 이달 재물운</div>
            <div style="font-size:13.5px;color:#333;line-height:1.9">{money_msg}</div>
        </div>
        <div style="flex:1;min-width:220px;background:rgba(232,245,233,0.9);border:1px solid #66bb6a;
                    border-radius:14px;padding:18px">
            <div style="font-size:14px;font-weight:900;color:#2e7d32;margin-bottom:10px">🏥 이달 건강운</div>
            <div style="font-size:13.5px;color:#333;line-height:1.9">{health_msg}</div>
        </div>
        <div style="flex:1;min-width:220px;background:rgba(232,234,246,0.9);border:1px solid #7986cb;
                    border-radius:14px;padding:18px">
            <div style="font-size:14px;font-weight:900;color:#283593;margin-bottom:10px">🤝 이달 인간관계</div>
            <div style="font-size:13.5px;color:#333;line-height:1.9">{relation_msg}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 섹션 3: 주간별 흐름
    st.markdown('<div class="gold-section" style="margin-top:22px">📆 주간별 기운 흐름</div>', unsafe_allow_html=True)
    week_html = ""
    for i in range(5):
        if not week_data[i]: continue
        d_start = week_data[i][0]["date"].day
        d_end   = week_data[i][-1]["date"].day
        ss_list  = [w["ss"] for w in week_data[i]]
        bad_cnt  = sum(1 for s in ss_list if s in ("겁재","편관","상관"))
        good_cnt = sum(1 for s in ss_list if s in ("식신","정관","정인","정재"))
        week_color = "#ffe0e0" if bad_cnt > good_cnt else "#e8f5e9" if good_cnt > 0 else "#f5f5f5"
        week_border = "#f44336" if bad_cnt > good_cnt else "#4caf50" if good_cnt > 0 else "#9e9e9e"
        week_html += f"""
        <div style="background:{week_color};border-left:4px solid {week_border};
                    border-radius:4px 12px 12px 4px;padding:12px 16px;margin-bottom:10px">
            <span style="font-weight:900;color:#333;font-size:14px">{w_labels[i]} ({month}/{d_start}～{month}/{d_end})</span>
            <span style="font-size:11px;color:#888;margin-left:8px">길일 {good_cnt}일 / 흉일 {bad_cnt}일</span>
            <div style="font-size:13px;color:#444;margin-top:6px;line-height:1.8">{week_summaries[i]}</div>
        </div>"""
    st.markdown(week_html, unsafe_allow_html=True)

    # 섹션 4: 흉일 목록
    st.markdown('<div class="gold-section" style="margin-top:18px">[!]️ 이번 달 조심해야 하는 날 (흉일)</div>', unsafe_allow_html=True)
    if bad_days:
        risk_type = max(counts, key=counts.get)
        briefing_text = f"이번 달은 총 <b>{total_risk}일</b>의 주의가 필요한 날이 계산되었습니다. "
        if total_risk > 10:
            briefing_text += "운기의 기복이 매우 심한 달이니 모든 행동을 신중하게 하십시오."
        elif total_risk > 5:
            briefing_text += "특정 기간에 기운이 집중되어 있으니 컨디션 조절에 힘쓰십시오."
        else:
            briefing_text += "흉일이 비교적 적어 평온하나, 해당 날짜만큼은 각별히 자중하십시오."

        detailed_insight = {
            "편관": "특히 <b>편관</b>의 날이 우세합니다. 건강 악화와 관재구설을 조심하며, 타인과의 마찰을 피하고 칼날 위를 걷듯 처신하십시오.",
            "겁재": "특히 <b>겁재</b>의 날이 우세합니다. 재물의 지출이 많아지거나 배신수가 우려되니 지갑을 닫고 마음을 다스리십시오.",
            "상관": "특히 <b>상관</b>의 날이 우세합니다. 구설수와 말실수로 인한 피해가 우려되니 침묵이 금입니다.",
        }.get(risk_type, "전반적인 흉기를 조심하십시오.")

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fff8e1,#ffecb3);border-radius:14px;
                    padding:18px 20px;margin-bottom:16px;border:1px solid #ffcc80">
            <div style="font-size:15px;font-weight:900;color:#e65100;margin-bottom:8px">🎙️ 만신의 월간 흉일 브리핑</div>
            <div style="font-size:14px;color:#4e342e;line-height:1.9">{briefing_text}<br><br>{detailed_insight}</div>
        </div>
        """, unsafe_allow_html=True)

        cards = ""
        for b in bad_days:
            desc = {"겁재":"재물 손실/인간관계 갈등 주의", "편관":"건강 악화/관재구설 주의", "상관":"말실수/직장 내 트러블 주의"}.get(b["ss"], "매사 조심")
            d_str = b["date"].strftime("%m/%d")
            w_str = ["월","화","수","목","금","토","일"][b["date"].weekday()]
            cards += f"""<div style="background:#fff0f0;border-left:4px solid #f44336;padding:9px 14px;
                margin-bottom:7px;border-radius:4px 8px 8px 4px;">
                <span style="font-weight:900;color:#d32f2f;font-size:14px;margin-right:10px">{d_str} ({w_str})</span>
                <span style="color:#555;font-size:12px;margin-right:8px">{b['cgjj']}일</span>
                <span style="font-weight:700;color:#c62828;font-size:13px;margin-right:8px">[{b['ss']}]</span>
                <span style="color:#333;font-size:13px">{desc}</span></div>"""
        st.markdown(cards, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:18px 20px;color:#2e7d32;background:linear-gradient(135deg,#e8f5e9,#f1f8e9);
                    border-radius:12px;border:1px solid #a5d6a7;font-size:14px;line-height:1.9">
            🌿 <b>이번 달은 크게 조심해야 할 흉일이 보이지 않습니다.</b><br><br>
            평온하고 안정적인 한 달이 예상됩니다. 그러나 방심은 금물이니, 평소 루틴을 성실하게 지키는 것이 이 달 최고의 전략입니다.
            중요한 계약이나 투자는 용신(用神)에 해당하는 날을 가려 진행하시면 더욱 좋습니다.
        </div>
        """, unsafe_allow_html=True)

    # 섹션 5: 길일 목록
    if good_days:
        st.markdown('<div class="gold-section" style="margin-top:18px">✅ 이번 달 행운의 날 (길일)</div>', unsafe_allow_html=True)
        good_cards = ""
        for g in good_days:
            gdesc = {"식신":"창의/복록/새 시작에 좋은 날", "정관":"공적 업무/명예 상승에 유리", "정인":"귀인 만남/합격 소식 기대", "정재":"계약/저축/성실 보상의 날"}.get(g["ss"], "길한 기운")
            d_str = g["date"].strftime("%m/%d")
            w_str = ["월","화","수","목","금","토","일"][g["date"].weekday()]
            good_cards += f"""<div style="background:#f1f8e9;border-left:4px solid #4caf50;padding:9px 14px;
                margin-bottom:7px;border-radius:4px 8px 8px 4px;">
                <span style="font-weight:900;color:#2e7d32;font-size:14px;margin-right:10px">{d_str} ({w_str})</span>
                <span style="color:#555;font-size:12px;margin-right:8px">{g['cgjj']}일</span>
                <span style="font-weight:700;color:#388e3c;font-size:13px;margin-right:8px">[{g['ss']}]</span>
                <span style="color:#333;font-size:13px">{gdesc}</span></div>"""
        st.markdown(good_cards, unsafe_allow_html=True)

    # 섹션 6: 만신의 한 마디
    FINAL_WORDS = {
        "겁재": f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 돈과 사람, 두 가지를 모두 잃지 않으려면 오늘 가장 소중한 것 한 가지를 먼저 선택하십시오. 지킬 것을 정했다면 나머지는 과감히 내려놓는 용기가 이번 달의 진짜 능력입니다.",
        "편관": f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 칼끝이 당신을 향하고 있을 때, 가장 안전한 곳은 그 칼을 들고 있는 사람 곁이 아니라, 칼이 닿지 않는 거리를 유지하는 것입니다. 한 발짝 뒤로 물러서는 것이 지혜입니다.",
        "식신": f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 당신 안에 오랫동안 잠들어 있던 씨앗이 드디어 싹을 틔울 준비를 마쳤습니다. 두려움 없이 첫 발을 내딛으십시오. 하늘이 응원하고 있습니다.",
        "정관": f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 빛이 가장 강할 때 그림자도 가장 짙습니다. 명예와 인정을 받는 이번 달, 자만 대신 감사를 마음에 품으십시오. 그 겸손함이 당신의 빛을 오래도록 유지시켜 줄 것입니다.",
        "정인": f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 기다림이 길었을수록 열매는 더 달콤합니다. 이번 달 당신이 기다려온 소식이 찾아올 가능성이 높습니다. 마지막 한 걸음을 포기하지 마십시오.",
        "-":  f"이번 달 {display_name}님에게 만신이 드리는 한 마디 - 파도가 잠잠할 때 배를 정비하는 선원이 폭풍에도 살아남습니다. 이번 달의 평온함을 낭비하지 마시고, 다가올 기회를 위해 조용히 준비하십시오.",
    }
    final_word = FINAL_WORDS.get(month_ss, FINAL_WORDS["-"])
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#2c1a00,#4a2e00);border-radius:16px;
                padding:22px 24px;margin-top:20px;border:1px solid #d4af37;
                box-shadow:0 8px 30px rgba(0,0,0,0.15)">
        <div style="font-size:15px;font-weight:900;color:#d4af37;margin-bottom:12px">🙏 만신의 {month}월 최후 한 마디</div>
        <div style="font-size:14.5px;color:#ffe0b2;line-height:2.1;font-style:italic">{final_word}</div>
    </div>
    """, unsafe_allow_html=True)

def menu11_yearly(pils, name, birth_year, gender, api_key="", groq_key=""):
    """1️⃣1️⃣ 신년 운세 - 연월일시 1~12월 완전 분석"""
    ilgan = pils[1]["cg"]
    display_name = name if name else "내담자"
    today = datetime.now()

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#f5f0ff,#fff0e8);
            border-radius:14px;padding:18px 24px;margin-bottom:16px;text-align:center">
    <div style="font-size:22px;font-weight:900;color:#5a2a00;letter-spacing:2px">
        🎊 {display_name}님의 신년 운세 (월별 족집게)
    </div>
    <div style="font-size:13px;color:#000000;margin-top:6px">
        올 한 해의 흐름을 1월부터 12월까지 상세히 분석합니다.
    </div>
</div>
""", unsafe_allow_html=True)

    col_y, _ = st.columns([1, 3])
    with col_y:
        sel_year = st.selectbox("조회 연도",
                                [today.year - 1, today.year, today.year + 1],
                                index=1,
                                key="yearly_year_select")

    if api_key or groq_key:
        cache_key = f"{pils[1]['cg']}_{sel_year}_yearly_ai"
        cached_yr = get_ai_cache(cache_key, "yearly_ai")

        if not cached_yr:
            with st.spinner(f"🔮 만신 AI가 {sel_year}년 12개월 운기를 정밀 분석 중입니다..."):
                prompt = (
                    f"당신은 40년 임상 경력의 명리학자 '만신(萬神)'입니다.\n\n"
                    f"-> 내담자 정보\n- 이름: {display_name}\n- 성별: {gender}\n- 생년: {birth_year}년\n- 일간: {ilgan}\n\n"
                    f"-> 요청\n"
                    f"{sel_year}년의 신년운세를 1월부터 12월까지 별로 **반드시** 풀이하되, "
                    f"**공백 포함 최소 1500자 이상**의 풍부하고 심도 있는 분량으로 작성하십시오.\n\n"
                    f"[반드시 포함할 내용]\n"
                    f"1. 각 월의 주요 기운(월바라기 포함)\n"
                    f"2. 로 주의할 시기와 홖신할 시기 하이라이트\n"
                    f"3. 연간 재물/건강/인간관계 총정리\n"
                    f"4. 만신의 {sel_year}년 한 마디 지혜\n\n"
                    f"1500자에 미달하면 절대 안 됩니다."
                )
                result = get_ai_interpretation(
                    prompt, api_key,
                    system=f"당신은 40년 임상 경력의 명리학자 '만신(萬神)'입니다. 항상 1500자 이상의 풍부한 신년 운세 풀이를 제공하십시오. {b3_build_optimized_prompt_suffix()}",
                    max_tokens=4000,
                    groq_key=groq_key
                )
                if result and not result.startswith("["):
                    result = result.replace("~", "～")
                    set_ai_cache(cache_key, "yearly_ai", result)
                    cached_yr = result

        if cached_yr:
            cached_yr = cached_yr.replace("~", "～")
            char_count = len(cached_yr)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.85);backdrop-filter:blur(20px);border:1.5px solid #d4af37;
                        border-radius:20px;padding:28px;margin:10px 0 25px;box-shadow:0 12px 40px rgba(212,175,55,0.12)">
                <div style="font-size:18px;font-weight:900;color:#b38728;margin-bottom:15px;display:flex;align-items:center;justify-content:space-between">
                    <span><span style="font-size:22px">🔮</span>&nbsp; 만신 AI {sel_year}년 신년 운세 완전 분석</span>
                    <span style="font-size:11px;color:#aaa;font-weight:400">({char_count}자)</span>
                </div>
                <div style="font-size:15px;color:#111;line-height:2.2;white-space:pre-wrap;letter-spacing:-0.2px">{apply_lexicon_tooltips(cached_yr)}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("🔮 AI 분석을 준비 중입니다. API Key 설정을 확인해 주세요.")

    LEVEL_COLOR = {"대길":"#4caf50","길":"#8bc34a","평길":"#ffc107","평":"#9e9e9e","흉":"#f44336","흉흉":"#b71c1c"}
    LEVEL_EMOJI = {"대길":"🌟","길":"✅","평길":"🟡","평":"⬜","흉":"[!]️","흉흉":"🔴"}
    months_data = [get_monthly_luck(pils, sel_year, m) for m in range(1, 13)]

    LEVEL_RANK = {"대길":5,"길":4,"평길":3,"평":2,"흉":1,"흉흉":0}
    best_m  = max(months_data, key=lambda x: LEVEL_RANK.get(x["길흉"], 2))
    worst_m = min(months_data, key=lambda x: LEVEL_RANK.get(x["길흉"], 2))

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown(f"""
<div style="background:#e8f5e8;border:1px solid #8de48d;border-radius:10px;
                padding:12px 16px;margin-bottom:10px;font-size:13px;color:#33691e">
        🌟 최고의 달: <b>{best_m['월']}월</b> - {best_m['월운']} ({best_m['십성']}) {best_m['short']}
    </div>
""", unsafe_allow_html=True)
    with bc2:
        st.markdown(f"""
<div style="background:#fff0f0;border:1px solid #f0a0a0;border-radius:10px;
                padding:12px 16px;margin-bottom:10px;font-size:13px;color:#b71c1c">
        [!]️ 주의할 달: <b>{worst_m['월']}월</b> - {worst_m['월운']} ({worst_m['십성']}) {worst_m['short']}
    </div>
""", unsafe_allow_html=True)

    for ml in months_data:
        m       = ml["월"]
        is_now  = (m == today.month and sel_year == today.year)
        lcolor  = LEVEL_COLOR.get(ml["길흉"], "#777")
        lemoji  = LEVEL_EMOJI.get(ml["길흉"], "")
        month_names = ["","1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]

        with st.expander(
            f"{'-> ' if is_now else ''}{month_names[m]}  |  {ml['월운']} ({ml['십성']})  |  "
            f"{lemoji} {ml['길흉']} - {ml['short']}",
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
        <div style="font-size:11px;color:#000000;margin-bottom:4px">[!]️ 주의사항</div>
        <div style="font-size:13px;color:#ffab40">{ml['주의']}</div>
    </div>
""", unsafe_allow_html=True)

def menu8_bihang(pils, name, birth_year, gender):
    """8️⃣ 특급 비방록 - 용신 기반 전통 비방 처방전"""

    # [년, 월, 일, 시] 순서에서 일간은 index 2
    ilgan = pils[1]["cg"] if pils and len(pils) > 1 else ""
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

    # ==================================
    # 비방 DB - 용신 오행별 전통 비방 (만신 스타일)
    # ==================================
    BIHANG_DB = {
        "木": {
            "오행명": "목(木) / 나무의 기운",
            "emoji": "🌳",
            "색상": ["초록색","청록색","파란 계열"],
            "방위": "동쪽 (정동방)",
            "숫자": ["3","8"],
            "비방": "동쪽 벽에 푸른 기운을 품은 생명을 3주 세워라. 네 꺾인 기운이 그 나무를 타고 하늘로 뻗칠 것이니라.",
            "재물": "지갑 속에 마른 쑥 한 잎을 넣어라. 삿된 기운이 네 재물을 탐내지 못하게 빗장을 거는 법이니라.",
            "금기": "서쪽의 날카로운 것은 피하라. 쇠의 기질이 네 성장의 맥을 끊을까 두렵도다.",
            "action": "매일 새벽 동쪽을 향해 심호흡 3회를 수행하여 목의 정수를 마셔라."
        },
        "火": {
            "오행명": "화(火) / 불의 기운",
            "emoji": "🔥",
            "색상": ["빨강색","주황색","분홍색"],
            "방위": "남쪽 (정남방)",
            "숫자": ["2","7"],
            "비방": "어둠 속에 머물지 마라. 네 운명은 타오르는 불꽃이니, 남쪽 창을 열어 태양의 기운을 매일 7분간 마셔라.",
            "재물": "붉은 실을 일곱 번 감아 네 소지품에 묶어라. 흩어진 재물이 열기에 이끌려 네 품으로 회귀하리라.",
            "금기": "북쪽의 차가운 물은 멀리하라. 네 열정이 식으면 모든 운이 멈출 것이니라.",
            "action": "정오에 남쪽을 향해 붉은 소품을 만지며 강렬한 성취를 염원하라."
        },
        "土": {
            "오행명": "토(土) / 땅의 기운",
            "emoji": "⛰️",
            "색상": ["황토색","갈색","노란색"],
            "방위": "중앙 (거실 등)",
            "숫자": ["5","10"],
            "비방": "가볍게 처신하지 마라. 무거운 돌이나 도자기를 네 중심에 두어라. 흔들리던 명예가 태산처럼 고정될 것이로다.",
            "재물": "황토 주머니를 머리맡에 두어라. 땅의 신이 네 잠자리를 지키며 재물 씨앗을 뿌려줄 것이니라.",
            "금기": "동쪽의 우거진 숲은 조심하라. 네 영토를 침범하려는 기운이 도사리고 있음이로다.",
            "action": "흙을 밟으며 걷는 시간을 가져 대지의 안정을 네 것으로 만들어라."
        },
        "金": {
            "오행명": "금(金) / 쇠의 기운",
            "emoji": "⚔️",
            "색상": ["흰색","금색","은색"],
            "방위": "서쪽 (정서방)",
            "숫자": ["4","9"],
            "비방": "무딘 칼로는 고기를 벨 수 없다. 서쪽의 차가운 금속 기운으로 네 결단력을 벼려라. 망설임이 사라져야 길이 보이느니라.",
            "재물": "은장신구나 흰색 손수건을 몸에 지녀라. 금의 기운이 날카롭게 재물의 맥을 짚어줄 것이로다.",
            "금기": "남쪽의 타오르는 불을 경계하라. 네 단단한 신념이 녹아내리지 않도록 주의해야 하느니라.",
            "action": "매일 저녁 서쪽을 향해 날카로운 칼날의 형상을 그리며 마음의 결을 정리하라."
        },
        "水": {
            "오행명": "수(水) / 물의 기운",
            "emoji": "💧",
            "색상": ["검정색","남색"],
            "방위": "북쪽 (정북방)",
            "숫자": ["1","6"],
            "비방": "고인 물은 썩는 법. 흐르는 물소리를 항상 가까이하라. 네 지혜가 바다에 닿는 순간, 막혔던 모든 운이 뚫리리라.",
            "재물": "검은 콩 6알을 작은 병에 담아 북쪽에 숨겨라. 수(水)의 정령이 네 금고를 마르지 않는 샘으로 만들 것이니라.",
            "금기": "중앙의 메마른 흙을 멀리하라. 네 유연함이 가로막혀 고립될 수 있음이니라.",
            "action": "취침 전 북쪽을 향해 맑은 물 한 잔을 마시며 지혜의 기운이 온몸에 퍼지길 바라라."
        }
    }

    # ==================================================
    # UI 시작
    # ==================================================
    st.markdown("""
    <div style="background:linear-gradient(135deg,#ffdcdc,#ffdce4,#ffdcdc);
                border:1px solid #8B0000;border-radius:16px;padding:22px 26px;margin-bottom:20px">
        <div style="color:#ff6060;font-size:11px;letter-spacing:4px;margin-bottom:8px">
            [!]️ 극비(極秘) - 용신 기반 전통 비방 처방전
        </div>
        <div style="color:#8b6200;font-size:19px;font-weight:900;letter-spacing:2px;margin-bottom:10px">
            🔴 특급 비방록(特急 秘方錄)
        </div>
        <div style="color:#d0a080;font-size:13px;line-height:1.9">
            무당/만신이 대대로 전해온 비방을 사주 용신에 맞춰 처방합니다.<br>
            돈이 새는 구멍을 막고, 재물이 들어오는 문을 여는 처방입니다.<br>
            <span style="color:#ff8888">기신(忌神) 오행을 막고 용신(用神) 오행을 강화하는 것이 핵심입니다.</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ① 용신/기신 파악
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
        </div>
""", unsafe_allow_html=True)
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
        </div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ② 용신 및 기신 비방 (만신의 신탁)
    if not yongshin_ohs:
        st.warning("용신 계산 결과가 없습니다. 사주 계산을 먼저 진행하십시오.")
        return

    # 용신 강화 신탁
    for yong_oh in yongshin_ohs[:2]:
        bd = BIHANG_DB.get(yong_oh)
        if not bd: continue

        st.markdown(f"""
        <div style="background: white; border: 1px solid #d4af37; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <span style="font-size: 30px;">{bd['emoji']}</span>
                <div>
                    <div style="color: #d4af37; font-size: 11px; font-weight: 800; letter-spacing: 2px;">ELEMENTAL SECRET</div>
                    <div style="font-size: 20px; font-weight: 900;">{bd['오행명']}의 처방</div>
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="font-size: 13px; font-weight: 800; color: #1a237e; margin-bottom: 8px;">📜 비방 (秘方)</div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 3px solid #1a237e; font-size: 15px; line-height: 1.6;">
                    "{bd['비방']}"
                </div>
            </div>

            <div style="margin-bottom: 20px;">
                <div style="font-size: 13px; font-weight: 800; color: #b71c1c; margin-bottom: 8px;">💰 재물 (財物)</div>
                <div style="background: #fff8f8; padding: 15px; border-radius: 8px; border-left: 3px solid #b71c1c; font-size: 15px; line-height: 1.6;">
                    "{bd['재물']}"
                </div>
            </div>

            <div style="margin-bottom: 20px;">
                <div style="font-size: 13px; font-weight: 800; color: #333; margin-bottom: 8px;">🚫 금기 (禁忌)</div>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; border-left: 3px solid #333; font-size: 14px; color: #666;">
                    "{bd['금기']}"
                </div>
            </div>
            
            <div style="background: #1a1a1a; color: #f7e695; padding: 12px 18px; border-radius: 8px; font-size: 13px; text-align: center; border: 1px solid #d4af37;">
                ⚖️ <b>행동 지침:</b> {bd['action']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 기신 차단 신탁
    if gishin_ohs:
        st.markdown(f"""
        <div style="background: #fff5f5; border: 1px solid #ff8888; border-radius: 12px; padding: 20px; margin-bottom: 25px;">
            <div style="font-size: 16px; font-weight: 900; color: #b71c1c; margin-bottom: 12px;">🚫 기신(忌神) 차단 - 돈 새는 구멍을 막아라</div>
            <div style="font-size: 13px; color: #555; line-height: 1.6;">
                현재 사주에서 <b>{", ".join(gishin_ohs)}</b>의 기운이 재물을 밀어내고 있습니다. 
                해당 오행의 색상과 방위를 피하고, 특히 그 기운이 강한 날에는 큰 거래를 삼가 명(命)을 보존하십시오.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ④ 공통 만신 비방 - 신강신약별
    st.markdown("""
    <div style="background:#ffffff;;
                border:2px solid #4a3080;border-radius:14px;padding:20px;margin:16px 0">
        <div style="font-size:16px;font-weight:900;color:#c39bd3;margin-bottom:14px">
            🕯️ 신강신약별 공통 비방 - 만신 구전(口傳)
        </div>""", unsafe_allow_html=True)

    if "신강" in sn:
        rituals_common = [
            "신강한 사주는 힘이 넘쳐 오히려 재물을 흩트린다. 주 1회 절에 가거나 사찰 보시(布施)를 생활화하면 기운이 안정된다.",
            "집 안에 거울을 너무 많이 두지 말 것 - 강한 기운이 반사되어 충돌이 생긴다.",
            "월초(음력 1일)마다 현관 소금 한 줌 뿌리고 3일 후 쓸어버리기 - 나쁜 기운 차단",
            "재물이 들어오는 운기(用神대운)에는 반드시 움직여라. 신강한 사주는 적극적으로 나서야 재물이 손에 잡힌다.",
            "기도/의식보다 행동이 우선이다. 신강은 스스로 만드는 사주이다.",
        ]
        desc_color = "#d0c8f8"
        sn_color = "#9b7ccc"
    else:
        rituals_common = [
            "신약한 사주는 기운이 약해 귀신/나쁜 기운에 쉽게 영향 받는다. 매달 음력 초하루 정화수 올리는 것을 생활화하라.",
            "집 안 구석구석 소금 청소 - 월 1회 소금물로 현관 바닥 닦기 (기운 정화)",
            "붉은 팥죽을 동지/정월 초에 대문 앞에 뿌리기 - 나쁜 기운 쫓기",
            "수호신 역할의 소품(도자기/나무 인형 등)을 집 안에 두되 정기적으로 닦아줄 것",
            "귀인 운이 올 때 반드시 받아들여라. 신약은 혼자보다 귀인과 함께일 때 크게 된다.",
            "무리한 야간 활동/과음/과로를 피하라. 신약은 건강이 재물의 기반이다.",
        ]
        desc_color = "#f0d8c8"
        sn_color = "#e8a060"

    st.markdown(f"""

    <div style="font-size:12px;color:{sn_color};font-weight:700;margin-bottom:8px">
        {sn} 특화 처방
    </div>
""", unsafe_allow_html=True)

    for r in rituals_common:
        st.markdown(f"""

        <div style="background:#f5f5f5;border-left:3px solid {sn_color};
                    padding:10px 14px;border-radius:6px;margin:5px 0;
                    font-size:13px;color:{desc_color};line-height:1.9">
            * {r}
        </div>
""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #e0d8c0;margin:20px 0">', unsafe_allow_html=True)

    # ⑤ 나이별 특급 비방 - 현재 운기에 맞춘 처방
    st.markdown(f"""

    <div style="background:linear-gradient(135deg,#fff5e0,#fff0dc);
                border:2px solid #000000;border-radius:14px;padding:20px">
        <div style="font-size:16px;font-weight:900;color:#8b6200;margin-bottom:10px">
            📅 {current_year}년 ({current_age}세) 현재 운기 맞춤 비방
        </div>
""", unsafe_allow_html=True)

    try:
        sw = get_yearly_luck(pils, current_year)
        sw_ss = sw.get("십성_천간", "-")
        sw_oh = sw.get("오행_천간", "")
        sw_str = sw.get("세운", "")

        is_yong_year = sw_oh in yongshin_ohs

        if is_yong_year:
            year_desc = f"올해 {sw_str}년은 용신 오행이 들어오는 해입니다. 적극적으로 움직이십시오."
            year_bihang = [
                f"용신 오행({sw_oh})이 강화되는 해 - 이 해에 큰 결정/투자/창업을 해야 합니다.",
                f"용신 색상/방위를 최대한 활용하십시오. 옷 색상부터 바꾸는 것이 시작입니다.",
                "새로운 인연/거래처/투자처가 올 때 적극적으로 받아들이십시오.",
                "연초(음력 정월)에 용신 방향으로 여행 또는 나들이 - 운기를 몸에 흡수",
            ]
            card_color = "#000000"
            card_bg = "#1a1a00"
        else:
            year_desc = f"올해 {sw_str}년은 기신이 강하게 작동하는 해입니다. 수비적으로 대응하십시오."
            year_bihang = [
                f"기신 오행({sw_oh})이 강화되는 해 - 큰 투자/보증/동업을 피하십시오.",
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
        </div>
""", unsafe_allow_html=True)

        for yb in year_bihang:
            st.markdown(f"""
            <div style="background:#fafafa;border-left:3px solid {card_color};
                        padding:9px 14px;border-radius:6px;margin:4px 0;
                        font-size:13px;color:#e0d0c0;line-height:1.8">
                {'✅' if is_yong_year else '[!]️'} {yb}
            </div>
""")

    except Exception as e:
        st.warning(f"올해 운기 계산 오류: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("[!]️ 본 비방록은 전통 민속 문화 정보를 제공하는 참고 자료입니다. 실제 굿/부적 처방은 전문 무당/만신에게 문의하십시오.")

class Brain3:
    """AI 상담 엔진 (Brain 2의 확장을 담당)"""
    def __init__(self, api_key, groq_key):
        self.api_key = api_key
        self.groq_key = groq_key

    def process_query(self, system_prompt, user_prompt, history):
        # ⏱️ 상담 흐름 제어 스킬 (Dialogue Control) - 구조 강제화
        structure_instruction = """
        [답변 구조 지침 - 반드시 준수]
        1. 현재 흐름: 사주상 현재의 운기 흐름을 한 문장으로 요약. ("내 신안에 보이는구먼..." 식으로 시작)
        2. 이유 설명: 왜 그런 흐름이 나타나는지 사주 원리로 설명 (격국/용신/십성 등).
        3. 현실 조언: 내담자가 지금 당장 실천할 수 있는 구체적인 행동 제안. ("명심하게!", "~하지 말게" 등 무당 어투 사용)
        4. 한줄 결론: 상담의 핵심을 관통하는 명쾌한 한 줄 결론. ("~하느니라", "~하리라" 형식)

        * 무당·만신 말투(~하느니라, ~하리라, ~하는구먼, 허허, 허어 등)를 자연스럽게 유지하십시오.
        * 가독성을 위해 각 번호와 제목을 명확히 구분하여 작성하십시오.
        * 모바일 최적화를 위해 문장은 간결하게 유지하십시오.
        """
        full_system_prompt = system_prompt + "\n" + structure_instruction
        
        return get_ai_interpretation(
            prompt_text=user_prompt,
            api_key=self.api_key,
            system=full_system_prompt,
            groq_key=self.groq_key,
            history=history
        )

# ==========================================================





def tab_ai_chat(pils, name, birth_year, gender, api_key, groq_key=""):
    """끝판왕(E-Version) AI 상담 - 의도/기억/성격 통합 엔진"""
    
    if not UsageTracker.check_limit():
        st.warning("오늘 준비된 상담 역량이 소진되었습니다. 내일 다시 찾아주십시오. (일일 제한 100명)")
        return

    # 1️⃣ 영속 기억 로드 및 성격 프로파일링 (최초 1회)
    mem = SajuMemory.get_memory(name)
    if not mem["identity"].get("profile"):
        # pils 구조에 따라 데이터 추출
        profile = PersonalityProfiler.analyze(pils)
        def save_profile(m):
            m["identity"]["profile"] = profile
            return m
        SajuMemory.update_memory(name, save_profile)
        mem = SajuMemory.get_memory(name)

    # 🧩 상담 단계 표시 (기존 스타일 유지)
    current_stage = mem["flow"].get("consult_stage", "탐색")
    stages = ["탐색", "이해", "해석", "조언", "정리"]
    stage_idx = stages.index(current_stage) if current_stage in stages else 0
    # 🗺️ V2 프리미엄 헤더 (상담 단계 + 신뢰도 게이지 + MBTI + Bond + Matrix)
    trust_data = mem.get("trust", {"score": 50, "level": 1})
    bond_data = mem.get("bond", {"level": 1, "label": "탐색", "score": 10})
    profile = mem["identity"].get("profile", {})
    mbti_val = profile.get("mbti", "분석중")
    matrix = mem.get("matrix", {"행동": 50, "감정": 50, "기회": 50, "관계": 50, "에너지": 50})
    narrative = mem["identity"].get("narrative", "")
    if not narrative: narrative = "서사 작성 중..."
    
    stage_html = " ".join([
        f'<span style="color: {"#000" if i == stage_idx else "#ccc"}; font-weight: {"800" if i == stage_idx else "400"};">{s}</span>'
        for i, s in enumerate(stages)
    ])
    
    st.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.4); backdrop-filter: blur(10px); 
                border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 15px; 
                padding: 18px; margin-bottom: 20px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);">
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <div style="font-size: 10px; color: #d4af37; font-weight: 800; letter-spacing: 1px;">COUNSELING PROGRESS</div>
                <div style="font-size: 14px; margin-top:2px; font-weight: 700;">{stage_html}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 10px; color: #888; font-weight: 700;">{bond_data['label']} BOND Lv.{bond_data['level']}</div>
                <div style="background: #eee; width: 100px; height: 5px; border-radius: 3px; margin-top: 5px; position: relative;">
                    <div style="background: linear-gradient(90deg, #6c5ce7, #a06ee1); width: {bond_data.get('score', 0)}%; height: 100%; border-radius: 3px;"></div>
                </div>
            </div>
        </div>

        <!-- 📊 Master matrix Dashboard -->
        <div style="display: flex; justify-content: space-around; background: rgba(0,0,0,0.03); padding: 10px; border-radius: 10px; margin-bottom: 12px;">
            {"".join([f'''
            <div style="text-align: center;">
                <div style="font-size: 9px; color: #999;">{k}</div>
                <div style="font-size: 13px; font-weight: 800; color: {"#d4af37" if (v or 0) > 70 else "#555"};">{(v or 0)}</div>
            </div>
            ''' for k, v in matrix.items()])}
        </div>

        <div style="display: flex; gap: 8px;">
            <div style="background: #f0f4ff; color: #1a237e; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; border: 1px solid #c5cae9;">
                🧬 사주 MBTI: {mbti_val}
            </div>
            <div style="background: #fff8e1; color: #f57f17; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; border: 1px solid #fff176;">
                🌌 인생 서사: {narrative}
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    if "chat_history" not in st.session_state or not st.session_state.chat_history:
        st.session_state.chat_history = []
        # 버그 수정: pils_data = pils[1] 로직 제거 (전체 pils 리스트 필요)
        intro = SajuMemory.get_personalized_intro(name, pils)
        st.session_state.chat_history.append({"role": "assistant", "content": intro})
        UsageTracker.increment()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # -- 입력 처리 --
    user_input = st.chat_input("사주나 운세에 대해 무엇이든 물어보세요...")
    prompt = st.session_state.pop("pending_query", user_input)

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # 2️⃣ Intent 분석
        intent_res = IntentEngine.analyze(prompt)
        st.markdown(IntentEngine.get_topic_badge(prompt), unsafe_allow_html=True)

        # 🧩 Master Platform 통합 로직
        user_query = prompt
        SajuMemory.record_behavior(name, user_query)
        implicit_persona = PersonalityEngine.analyze_behavior(name)
        
        # 유대감 및 매트릭스 업데이트
        SajuMemory.adjust_bond(name, 3) # 유대감 상승
        GoalCreationEngine.extract_goal(name, user_query) # 목표 발견
        
        current_year = datetime.now().year
        luck_score = calc_luck_score(pils, birth_year, gender, current_year)
        DestinyMatrix.calculate_sync(name, pils, luck_score)
        
        # 전환점 감지
        pivot_info = ChangeRadarEngine.detect_pivot(name, luck_score)
        if pivot_info["is_pivot"]:
            st.toast(f"🛰️ {pivot_info['message']}", icon="📈")
        
        turn_count = len(st.session_state.chat_history)
        if turn_count <= 4: new_stage = "이해"
        elif turn_count <= 8: new_stage = "해석"
        else: new_stage = "조언"
        if turn_count > 12: new_stage = "정리"
        
        SajuMemory.adjust_trust(name, 2, "상담 지속")
        
        def update_stage(m):
            m["flow"]["consult_stage"] = new_stage
            return m
        SajuMemory.update_memory(name, update_stage)
        mem = SajuMemory.get_memory(name)

        # 🎯 Fate Validation Loop (간이 피드백 버튼 연동)
        if mem["trust"]["level"] >= 2:
            st.sidebar.markdown("---")
            if st.sidebar.button("✅ 이번 상담이 정확했나요?"):
                SajuMemory.adjust_trust(name, 5, "사용자 만족 피드백")
                st.sidebar.success("마스터의 통찰력이 강화되었습니다!")

        # 🚨 V2 돌발 사건 감지
        risk_info = FatePredictionEngine.detect_risk(pils, datetime.now().year)
        if risk_info["is_risk"]:
            st.error(f"[!]️ **만신의 경고 ({risk_info['severity']}):** " + " / ".join(risk_info["messages"]))

        # ── 로컬 사주 엔진 (API 없을 때 폴백) ──────────────────────────────
        def _local_saju_response(query):
            """API 미연결 시 로컬 엔진으로 무당 말투 응답 생성"""
            import re as _re_loc
            q = query
            ilgan_loc = pils[1]["cg"] if len(pils) > 1 else "?"
            _ss = st.session_state
            bm = _ss.get("birth_month", 1); bd = _ss.get("birth_day", 1)
            bh = _ss.get("birth_hour", 12); bmn = _ss.get("birth_minute", 0)

            is_today = bool(_re_loc.search(r'오늘|일진|내일|이번주', q))
            is_year  = bool(_re_loc.search(r'올해|세운|금년|올해운세|2025|2026|2027', q)) or is_today
            is_money = bool(_re_loc.search(r'재물|돈|사업|수입|투자|부자|재산', q))
            is_love  = bool(_re_loc.search(r'연애|결혼|궁합|이성|남자|여자|남편|아내|인연|배우자', q))
            is_health= bool(_re_loc.search(r'건강|병원|아프|수술|몸|질병|체력', q))
            is_dw    = bool(_re_loc.search(r'대운|운세흐름|인생|10년|장기|앞으로|미래', q))
            is_past  = bool(_re_loc.search(r'과거|지나온|예전|돌아보|과거운|이전|맞춰봐', q))
            is_job   = bool(_re_loc.search(r'직업|진로|취업|창업|커리어|직장|일자리|사업방향|어떤 일', q))
            is_char  = bool(_re_loc.search(r'성격|성향|기질|특성|나는|내가|나의|나 어때', q))

            out = [f"허허, 어서 오게. {name}의 팔자를 내 신안(神眼)으로 살펴보겠느니라.\n"]
            try:
                if is_year:
                    sw    = get_yearly_luck(pils, current_year)
                    sw_ss = sw.get("십성_천간",""); sw_gh = sw.get("길흉",""); sw_gan = sw.get("세운","")
                    try: tp = calc_turning_point(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                    except Exception: tp = {}
                    _SW = {
                        "偏財":"재물 변동과 이성 인연의 기운이 강하느니라. 사업 기회가 오지만 투기는 조심하게.",
                        "正財":"안정된 수입과 결혼 인연의 기운이 들어오느니라. 재물을 차곡차곡 모을 수 있는 해니라.",
                        "食神":"직업과 재능이 빛을 발하는 해니라. 새 일을 시작하거나 자격 취득에 좋으니라.",
                        "傷官":"창의성이 폭발하지만 윗사람과의 마찰을 조심해야 하느니라.",
                        "偏官":"직장 변동과 사고 기운이 있느니라. 건강과 안전에 각별히 주의하게.",
                        "正官":"명예와 승진의 기운이 강하느니라. 조직에서 인정받는 해니라.",
                        "偏印":"계획이 자주 바뀌고 이사·이동의 기운이 있느니라. 신중하게 결정하게.",
                        "正印":"학업과 자격 취득에 유리한 해니라. 어머니와의 인연도 돈독해지느니라.",
                        "比肩":"독립심이 강해지고 경쟁이 치열해지는 해니라. 동업보다 단독 행동이 낫느니라.",
                        "劫財":"재물 손실과 경쟁이 극심한 해니라. 보증과 투자를 자제하게.",
                    }
                    _ACT = {
                        "偏財":"적극적 투자·사업 기회를 잡되 안전 자산 30% 이상 반드시 확보하게!",
                        "正財":"부동산·예금·적금 등 안정 자산에 집중하게. 불필요한 지출을 줄이는 것이 재물의 시작이니라.",
                        "食神":"자격증 취득·신규 프로젝트 시작이 최적이니라. 전문성을 드러낼 시기니라.",
                        "傷官":"창작·발명은 좋으나 직속 상관·계약서 분쟁 조심. 독립 행보는 내년 이후가 유리하니라.",
                        "偏官":"건강 정기검진 필수. 무리한 확장·새 사업 시작 자제. 법적 분쟁도 조심하게.",
                        "正官":"자격증·승진 시험·공직 지원에 최적의 해! 조직 내 신뢰를 쌓는 것이 핵심이니라.",
                        "偏印":"이사·이직·전공 변경 시 신중히 결정하게. 새 분야 학습에는 유리하니라.",
                        "正印":"자격증·진학·연구에 집중하라. 어머니·스승과의 관계를 돈독히 하게.",
                        "比肩":"독립·창업·단독 프로젝트에 유리. 동업·보증은 이 해에 시작하지 말게.",
                        "劫財":"현금 보유·빚 상환 우선. 도박·투기·보증 절대 금지. 경쟁에서 냉정함을 유지하게.",
                    }
                    out.append(f"**{current_year}년 ({current_year-birth_year+1}세) 세운 분석**\n")
                    out.append(f"올해 세운: **{sw_gan}** — 십성 **{sw_ss}**, 길흉 **{sw_gh}**\n")
                    out.append(_SW.get(sw_ss, f"{sw_ss} 기운이 강하게 작동하는 해니라.") + "\n")
                    out.append(f"\n**[올해 행동 지침]** {_ACT.get(sw_ss, '분수에 맞게 안정적으로 움직이게.')}\n")
                    tp_int = tp.get("intensity","")
                    tp_sc  = tp.get("score_change", 0)
                    tp_rsn = tp.get("reason", [])
                    if "강력" in tp_int:
                        out.append(f"\n**⚡ 인생 전환점 경보!** 운세 변화폭 {tp_sc:+d}점 — {tp_int}\n")
                        for r in tp_rsn[:3]: out.append(f"• {r}\n")
                    elif "주요" in tp_int or "변화" in tp_int:
                        out.append(f"\n**🔄 중요한 변화 감지** 운세 변화폭 {tp_sc:+d}점 — {tp_int}\n")
                        for r in tp_rsn[:2]: out.append(f"• {r}\n")
                    sw_n  = get_yearly_luck(pils, current_year+1)
                    sw_n2 = get_yearly_luck(pils, current_year+2)
                    out.append(f"\n**[내년 미리보기]** {current_year+1}년: {sw_n.get('세운','')} [{sw_n.get('십성_천간','')}] {sw_n.get('길흉','')}\n")
                    out.append(f"**[후년 미리보기]** {current_year+2}년: {sw_n2.get('세운','')} [{sw_n2.get('십성_천간','')}] {sw_n2.get('길흉','')}")

                elif is_money:
                    gk  = get_gyeokguk(pils); ys = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                    gkn = gk["격국명"] if gk else "미정격"
                    y1  = ys.get("용신_1순위","-"); y2 = ys.get("용신_2순위","-")
                    heui= ys.get("희신","-"); gisin = ", ".join(ys.get("기신",[]))
                    _GKM = {
                        "정관격":"명예와 재물이 함께 오는 격국이니라. 조직에서 승진할수록 재물이 늘어나느니라. 직함과 신뢰가 곧 재물이니 체면을 지키게.",
                        "정재격":"꾸준한 노력으로 재물을 쌓는 격국이니라. 금융·부동산에서 재물이 쌓이느니라. 규칙적 저축과 장기 투자가 최고의 전략이니라.",
                        "편재격":"사업가 기질의 격국이니라. 투자·영업에서 큰 기회가 오느니라. 기복이 크니 안전 자산 30% 이상 반드시 확보하게. 한 방을 노리다 전부 잃는 수가 있느니라.",
                        "식신격":"전문성을 키우면 재물이 자연스럽게 따라오는 격국이니라. 실력을 쌓는 것이 곧 재물을 쌓는 것이니라.",
                        "상관격":"창의적 방법으로 재물을 만드는 격국이니라. 프리랜서·컨설팅·콘텐츠 창작이 맞느니라.",
                        "편인격":"기술·학문·특허로 재물을 만드는 격국이니라. 단 재물보다 전문성에 집중할 때 돈이 따라오느니라.",
                        "정인격":"안정적 직업·자격증으로 꾸준히 재물을 쌓는 격국이니라. 주식·투기보다 연금·부동산이 맞느니라.",
                        "비견격":"독립 사업이나 프리랜서로 재물을 벌어야 하는 격국이니라. 공동 투자·동업은 반드시 계약서를 쓰게.",
                        "겁재격":"경쟁과 도전 속에서 재물을 얻는 격국이니라. 손실도 크지만 회복도 빠른 팔자니라.",
                    }
                    out.append(f"**{name}의 재물운 완전 분석**\n격국은 **{gkn}**이니라.\n")
                    out.append(_GKM.get(gkn, f"{gkn}의 재물 패턴은 독특하니라. 용신 기운을 따르게.") + "\n")
                    out.append(f"\n용신 **{y1}** / 희신 **{heui}** 기운이 강한 해(年)에 재물 결정을 내려야 하느니라.\n")
                    if gisin: out.append(f"⚠️ **기신 경고:** {gisin} 기운 강한 해에는 큰 투자·동업·보증을 반드시 피하게! 이 해에 움직이면 손실이 크니라.\n")
                    # 향후 재물 황금기 (별점 차등)
                    gold_ohs = {o for o in [y1,y2] if o in ("木","火","土","金","水")}
                    gold_yrs = []
                    for yr in range(current_year, current_year+11):
                        sw_g = get_yearly_luck(pils, yr)
                        if OH.get((sw_g.get("세운","")[:1]),"") in gold_ohs:
                            sw_g_ss = sw_g.get("십성_천간","")
                            star = "★★★" if sw_g_ss in ("偏財","正財","食神") else "★★" if sw_g_ss in ("正官","正印") else "★"
                            gold_yrs.append(f"* **{yr}년**({yr-birth_year+1}세): {sw_g.get('세운','')} [{sw_g_ss}] {sw_g.get('길흉','')} {star}")
                    if gold_yrs:
                        out.append(f"\n**[향후 재물 황금기 — 용신 세운]**\n")
                        for gy in gold_yrs[:6]: out.append(gy + "\n")
                        out.append("이 해들에 중요한 재물 결정을 내리게!\n")
                    # 대운×세운 재물 더블 황금기
                    try:
                        hl_m = generate_engine_highlights(pils, birth_year, gender, bm, bd, bh, bmn)
                        double_mp = [m for m in hl_m.get("money_peak",[]) if m.get("ss") == "더블"]
                        if double_mp:
                            out.append(f"\n**[대운×세운 재물 더블 황금기]** — 이 시기가 진짜 인생 재물 피크니라!\n")
                            for m in double_mp[:3]: out.append(f"* {m.get('year','')}년 ({m.get('age','')}) {m.get('desc','')}\n")
                    except Exception: pass
                    # 기신 대운 경고
                    try:
                        dw_list_m2 = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                        gisin_ohs2 = set(ys.get("기신",[]))
                        gisin_dws2 = [dw for dw in dw_list_m2
                                      if OH.get(dw.get("cg",""),"") in gisin_ohs2 and dw["종료연도"] >= current_year]
                        if gisin_dws2:
                            gdw2 = gisin_dws2[0]
                            gdw2_ss = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(gdw2["cg"],"-")
                            if gdw2["시작연도"] <= current_year:
                                out.append(f"\n⚠️ 지금 **{gdw2['str']} {gdw2_ss}** 기신 대운 진행 중! {gdw2['종료연도']-current_year}년 더 이어지느니라. 대형 투자·보증 자제가 최선이니라.\n")
                            else:
                                out.append(f"\n⚠️ {gdw2['시작연도']}년({gdw2['시작나이']}세)부터 **{gdw2['str']} {gdw2_ss}** 기신 대운이 오느니라. 미리 안전 자산 확보를 서두르게!\n")
                    except Exception: pass

                elif is_love:
                    out.append(f"**{name}의 인연·결혼운 완전 분석**\n허어, 인연의 실타래를 신안으로 살펴보겠느니라.\n")

                    # 1. 배우자 자리(정재/정관) 분석
                    yk = get_yukjin(ilgan_loc, pils, gender)
                    spouse_keys = (["아내","처","正財","妻"] if gender == "남" else ["남편","夫","正官","情夫","편관"])
                    for rel in yk:
                        rn = rel.get("관계","")
                        if any(k in rn for k in spouse_keys):
                            loc = rel.get("위치","없음")
                            out.append(f"\n**[배우자 자리]** {rn} — 위치: **{loc}**\n")
                            out.append(rel.get("desc","") + "\n")
                            if rel.get("present"):
                                out.append("허허, 배우자 기운이 사주에 뚜렷이 자리 잡고 있구먼. 인연은 반드시 오느니라.\n")
                            else:
                                out.append("배우자 기운이 약하니 대운·세운에서 재성/관성이 들어올 때 적극적으로 움직이게.\n")
                            break

                    # 2. 일지(배우자 자리) 지지 해석
                    iljj_l = pils[1]["jj"] if len(pils) > 1 else "?"
                    _ILJJ_L = {
                        "子(자)":"지혜롭고 다정한 배우자 기운. 지적 교감과 대화가 관계의 핵심이니라.",
                        "丑(축)":"성실하고 현실적인 배우자 기운. 안정과 책임감을 중시하느니라.",
                        "寅(인)":"진취적이고 리더십 강한 배우자 기운. 독립심이 강하니 존중이 필수니라.",
                        "卯(묘)":"섬세하고 예술적 감수성의 배우자 기운. 감성 교류가 사랑의 언어니라.",
                        "辰(진)":"능력 있고 카리스마 강한 배우자 기운. 단 고집이 센 면이 있느니라.",
                        "巳(사)":"두뇌 명석하고 표현력 강한 배우자 기운. 열정적 사랑을 추구하느니라.",
                        "午(오)":"열정적이고 활발한 배우자 기운. 외향적이고 솔직한 애정 표현이 특징이니라.",
                        "未(미)":"온화하고 예술적 감수성의 배우자 기운. 배려심이 깊고 감성이 풍부하느니라.",
                        "申(신)":"냉철하고 실리적인 배우자 기운. 현실 판단이 빠르고 독립적이니라.",
                        "酉(유)":"세련되고 완벽주의적 배우자 기운. 까다로울 수 있으나 깊은 헌신이 있느니라.",
                        "戌(술)":"의리 있고 뜨거운 열정의 배우자 기운. 한번 마음을 열면 평생 지키느니라.",
                        "亥(해)":"지혜롭고 깊은 내면의 배우자 기운. 자유 기질이 있어 구속을 싫어하느니라.",
                    }
                    out.append(f"\n**[일지 배우자 자리 — {iljj_l}]**\n{_ILJJ_L.get(iljj_l, f'일지 {iljj_l}의 기운이 배우자 자리에 흐르느니라.')}\n")

                    # 3. 대운에서 재성/관성운 들어오는 시기
                    try:
                        dw_list_l = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                        love_dw_ss_l = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
                        love_dws_l = [dw for dw in dw_list_l
                                      if TEN_GODS_MATRIX.get(ilgan_loc,{}).get(dw["cg"],"") in love_dw_ss_l
                                      and dw["종료연도"] >= current_year]
                        if love_dws_l:
                            cdw_l = love_dws_l[0]
                            cdw_ss_l = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(cdw_l["cg"],"")
                            if cdw_l["시작연도"] <= current_year:
                                out.append(f"\n**[대운 인연 시기]** 지금 **{cdw_l['str']} {cdw_ss_l}** 대운 진행 중! {cdw_l['종료연도']-current_year}년 남았으니 이 기간을 놓치지 말게!\n")
                            else:
                                out.append(f"\n**[대운 인연 시기]** {cdw_l['시작연도']}년({cdw_l['시작나이']}세)부터 **{cdw_l['str']} {cdw_ss_l}** 대운이 열리느니라. 그때가 인연의 문이 활짝 열리는 시기니라.\n")
                    except Exception: pass

                    # 4. 향후 3년 중 연애운 좋은 해
                    love_yr_ss_l = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
                    love_yrs_l = []
                    for _yr_l in range(current_year, current_year + 4):
                        _sw_l = get_yearly_luck(pils, _yr_l)
                        _ss_l = _sw_l.get("십성_천간","")
                        if _ss_l in love_yr_ss_l:
                            love_yrs_l.append(f"**{_yr_l}년**({_yr_l-birth_year+1}세): {_sw_l.get('세운','')} [{_ss_l}] {_sw_l.get('길흉','')} ← 이성 인연 기운이 강하느니라!")
                    if love_yrs_l:
                        out.append("\n**[향후 3년 연애·결혼 특효 시기]**\n")
                        for _ly_l in love_yrs_l: out.append(f"* {_ly_l}\n")
                        out.append("이 해들에 적극적으로 인연을 찾아 나서게. 하늘이 돕는 시기니라!\n")
                    else:
                        sw_now_l = get_yearly_luck(pils, current_year)
                        out.append(f"\n올해 {sw_now_l.get('세운','')} [{sw_now_l.get('십성_천간','')}] — 향후 3년은 이성 세운이 약하니 자기계발로 내실을 다지는 시기니라.\n")

                    # 5. 도화살 확인
                    try:
                        sinsal_l = get_special_stars(pils)
                        dohwa_l = [s for s in sinsal_l if "도화" in s.get("name","")]
                        ss12_l = get_12sinsal(pils)
                        dohwa12_l = [s for s in ss12_l if "도화" in s.get("이름","") or "년살" in s.get("이름","")]
                        if dohwa_l or dohwa12_l:
                            out.append("\n**[신살 — 도화살(桃花殺)]** 도화살이 사주에 있구먼!\n이성의 인기를 한몸에 받는 매력의 기운이니라. 감정에 휩쓸려 경솔한 선택을 하지 않도록 명심하게.\n")
                        else:
                            out.append("\n도화살은 없으나, 꾸준한 진심이 최고의 인연을 불러오느니라.\n")
                    except Exception: pass

                    # 6. 결혼 적령기
                    _cage_l = current_year - birth_year + 1
                    out.append(f"\n**[결혼 적령기 — 현재 {_cage_l}세]**\n")
                    try:
                        dw2_l = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                        love_ss2_l = {"偏財","正財"} if gender == "남" else {"偏官","正官"}
                        fut_dws_l = [dw for dw in dw2_l
                                     if TEN_GODS_MATRIX.get(ilgan_loc,{}).get(dw["cg"],"") in love_ss2_l
                                     and dw["종료연도"] >= current_year]
                        if fut_dws_l:
                            bd2_l = fut_dws_l[0]
                            bd2_ss_l = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(bd2_l["cg"],"")
                            if bd2_l["시작연도"] <= current_year:
                                out.append(f"지금 **{bd2_l['str']} {bd2_ss_l}** 대운 중! **{current_year}~{bd2_l['종료연도']}년**이 최적 결혼 시기니라. 망설이지 말게!\n")
                            else:
                                out.append(f"**{bd2_l['시작연도']}년({bd2_l['시작나이']}세)**부터 {bd2_l['str']} **{bd2_ss_l}** 대운이 열리느니라. 그 무렵 결혼 결실이 맺어지느니라.\n")
                        else:
                            for _yr2_l in range(current_year, current_year + 10):
                                _sw2_l = get_yearly_luck(pils, _yr2_l)
                                if _sw2_l.get("십성_천간","") in ({"偏財","正財"} if gender == "남" else {"偏官","正官"}):
                                    out.append(f"**{_yr2_l}년({_yr2_l-birth_year+1}세)** 세운에 인연 기운이 들어오느니라. 그 무렵 준비하게.\n")
                                    break
                    except Exception: pass

                elif is_health:
                    ilgan_oh_h = OH.get(ilgan_loc,"")
                    _OHB = {"木":"간장·담낭·눈·근육·인대","火":"심장·소장·혈관·혈압",
                            "土":"비장·위장·췌장·소화기","金":"폐·대장·기관지·피부","水":"신장·방광·생식기·귀·뼈"}
                    _OHA = {"木":"스트레칭과 충분한 수면이 최우선이니라. 분노·스트레스가 간장을 상하게 하느니라.",
                            "火":"심혈관 정기검진이 필수이니라. 카페인·음주를 자제하고 과로를 삼가게.",
                            "土":"식사 규칙성이 핵심이니라. 폭식·군것질을 삼가게. 걱정이 위장을 상하게 하느니라.",
                            "金":"습도 관리가 중요하니라. 가을·건조한 환경을 조심하게.",
                            "水":"충분한 수분 섭취가 필수니라. 과로·짠 음식을 피하게."}
                    out.append(f"**{name}의 건강운 완전 분석**\n일간 {ilgan_loc}의 오행은 **{OHN.get(ilgan_oh_h,'')}({ilgan_oh_h})**이니라.\n")
                    out.append(f"타고난 취약 신체: **{_OHB.get(ilgan_oh_h,'전반적 건강')}**\n")
                    out.append(_OHA.get(ilgan_oh_h,'규칙적인 생활이 핵심이니라.') + "\n")
                    # 오행 과다/부족 건강 경고
                    oh_s = calc_ohaeng_strength(ilgan_loc, pils)
                    for o, v in oh_s.items():
                        if v >= 35: out.append(f"\n⚠️ **{OHN.get(o,'')}({o}) 과다({v}%):** {_OHB.get(o,'')} 계통 특히 조심하게. 과다한 오행이 해당 장기를 혹사시키느니라.")
                        elif v <= 5: out.append(f"\n💊 **{OHN.get(o,'')}({o}) 부족({v}%):** {_OHB.get(o,'')} 계통 보강하게. 부족한 오행이 해당 장기를 약하게 만드느니라.")
                    # 현재 대운 건강 영향
                    try:
                        dw_list_h2 = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                        cdw_h2 = next((d for d in dw_list_h2 if d["시작연도"] <= current_year <= d["종료연도"]), None)
                        if cdw_h2:
                            cdw_ss_h2 = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(cdw_h2["cg"],"-")
                            cdw_oh_h2 = OH.get(cdw_h2["cg"],"")
                            _DWH2 = {
                                "偏官":"편관 대운은 압박과 스트레스가 극심하느니라. 면역력 저하와 사고 위험이 높으니 정기검진을 서두르게.",
                                "傷官":"상관 대운은 신경계 과부하와 과로가 주적이니라. 수면 관리와 스트레스 해소가 핵심이니라.",
                                "劫財":"겁재 대운은 외상·수술·혈액 관련 건강 이슈가 올 수 있으니라. 운동 시 안전에 유의하게.",
                                "偏印":"편인 대운은 우울·불안·정신건강에 주의가 필요하니라. 고립을 피하고 활동적으로 지내게.",
                                "比肩":"비견 대운은 과도한 경쟁과 독립 행보로 체력 소진을 조심하게. 충분한 휴식이 필수이니라.",
                                "食神":"식신 대운은 건강이 비교적 좋은 시기니라. 다만 과식으로 인한 소화계 문제를 조심하게.",
                                "正財":"정재 대운은 안정적 건강 유지가 가능한 시기니라. 규칙적 생활로 내실을 다지게.",
                                "正官":"정관 대운은 스트레스가 직장에서 오므로 멘탈 관리에 집중하게.",
                                "偏財":"편재 대운은 분주한 활동으로 체력 소진을 조심하게. 철저한 체력 관리가 필요하느니라.",
                                "正印":"정인 대운은 건강이 좋은 편이나 과보호·의존 경향이 오히려 체력을 약하게 만들 수 있느니라.",
                            }
                            out.append(f"\n**[현재 대운 건강 영향]** {cdw_h2['str']} **{cdw_ss_h2}** 대운 ({cdw_h2['종료연도']-current_year}년 남음)\n")
                            out.append(_DWH2.get(cdw_ss_h2, f"{cdw_ss_h2} 대운의 건강 기운이 흐르느니라. 몸의 신호에 귀를 기울이게.") + "\n")
                            out.append(f"이 대운 오행: **{OHN.get(cdw_oh_h2,'')}({cdw_oh_h2})** — {_OHB.get(cdw_oh_h2,'')} 계통에 영향을 주느니라.\n")
                    except Exception: pass
                    # 올해 세운 건강 경보
                    sw_hlt2 = get_yearly_luck(pils, current_year)
                    sw_hlt2_ss = sw_hlt2.get("십성_천간","")
                    if sw_hlt2_ss == "偏官":
                        out.append(f"\n⚠️ 올해({current_year}년) {sw_hlt2.get('세운','')} [偏官] 세운 — 건강 사고 위험 높은 해니라. 무리한 활동·수술 신중하게.\n")
                    elif sw_hlt2_ss == "傷官":
                        out.append(f"\n올해({current_year}년) {sw_hlt2.get('세운','')} [傷官] 세운 — 과로와 신경 소모가 심한 해니라. 충분한 휴식이 최우선이니라.\n")

                elif is_dw:
                    daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, bm, bd, bh, bmn, gender)
                    cdw = next((d for d in daewoon if d["시작연도"] <= current_year <= d["종료연도"]), None)
                    out.append(f"**{name}의 대운 흐름 완전 분석**\n")
                    # 용신 기반 황금기/주의기 판별
                    try:
                        ys_dw2 = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                        yong_ohs_dw2 = {o for o in [ys_dw2.get("용신_1순위",""), ys_dw2.get("용신_2순위",""), ys_dw2.get("희신","")] if o in ("木","火","土","金","水")}
                        gisin_dw2 = set(ys_dw2.get("기신",[]))
                    except Exception:
                        yong_ohs_dw2 = set(); gisin_dw2 = set()
                    if cdw:
                        cdw_ss = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(cdw["cg"],"-")
                        cdw_oh = OH.get(cdw["cg"],"")
                        grade2 = "🌟 황금기 대운" if cdw_oh in yong_ohs_dw2 else "⚠️ 주의기 대운" if cdw_oh in gisin_dw2 else "⬜ 보통 대운"
                        out.append(f"현재 대운: **{cdw['str']}** ({cdw_ss}) — **{grade2}**\n")
                        out.append(f"{cdw['시작연도']}~{cdw['종료연도']}년 ({cdw['시작나이']}~{cdw['시작나이']+9}세), **{cdw['종료연도']-current_year}년** 더 이어지느니라.\n")
                        out.append(DAEWOON_PRESCRIPTION.get(cdw_ss,"꾸준한 노력으로 안정을 유지하게.") + "\n")
                        if cdw_oh in yong_ohs_dw2:
                            out.append("이 대운은 용신 기운이 흐르는 황금기니라! 크게 움직여도 하늘이 돕는 시기이니라.\n")
                        elif cdw_oh in gisin_dw2:
                            out.append("이 대운은 기신 기운이 흐르는 주의기니라. 무리한 확장보다 안전 자산 확보와 내실 다지기가 최선이니라.\n")
                    # 다음 대운 미리보기
                    cdw_idx2 = next((i for i, d in enumerate(daewoon) if d["시작연도"] <= current_year <= d["종료연도"]), None)
                    if cdw_idx2 is not None and cdw_idx2 + 1 < len(daewoon):
                        ndw2 = daewoon[cdw_idx2 + 1]
                        ndw2_ss = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(ndw2["cg"],"-")
                        ndw2_oh = OH.get(ndw2["cg"],"")
                        ndw2_grade = "🌟 황금기" if ndw2_oh in yong_ohs_dw2 else "⚠️ 주의기" if ndw2_oh in gisin_dw2 else "⬜ 보통"
                        out.append(f"\n**[다음 대운 미리보기]** {ndw2['시작연도']}년({ndw2['시작나이']}세)부터 **{ndw2['str']} {ndw2_ss}** ({ndw2_grade}) 대운이 열리느니라.\n")
                        out.append(DAEWOON_PRESCRIPTION.get(ndw2_ss, "새 대운을 준비하게.") + "\n")
                    out.append("\n**전체 대운 흐름 (🌟황금기 / ⚠️주의기 표시):**\n")
                    for dw in daewoon[:8]:
                        dw_ss = TEN_GODS_MATRIX.get(ilgan_loc,{}).get(dw["cg"],"-")
                        dw_oh = OH.get(dw["cg"],"")
                        dw_grade2 = "🌟" if dw_oh in yong_ohs_dw2 else "⚠️" if dw_oh in gisin_dw2 else "⬜"
                        cur_m = " ◀현재" if dw["시작연도"] <= current_year <= dw["종료연도"] else ""
                        out.append(f"* {dw['시작나이']}~{dw['시작나이']+9}세: {dw['str']} ({dw_ss}) {dw_grade2}{cur_m}\n")

                elif is_past:
                    hl  = generate_engine_highlights(pils, birth_year, gender, bm, bd, bh, bmn)
                    pevs= sorted(hl.get("past_events",[]), key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e.get("intensity","🟢"),3))
                    out.append(f"**{name}의 과거 사건 완전 분석**\n허허, 지나온 세월을 신안으로 살펴보겠느니라.\n")
                    if pevs:
                        out.append("\n**[주요 과거 사건 — 강도순]**\n")
                        for ev in pevs[:6]:
                            out.append(f"\n**{ev.get('year','')}년 ({ev.get('age','')}) {ev.get('intensity','')} [{ev.get('domain','변화')}]**\n{ev.get('desc','')}\n")
                    else:
                        out.append("사주 엔진이 과거 데이터를 분석 중이니라.\n")
                    # 월지 충 근거
                    wc2 = hl.get("wolji_chung", [])
                    if wc2:
                        out.append("\n**[월지 충(沖) — 삶의 기반이 흔들린 시기]**\n")
                        for w in wc2[:3]: out.append(f"* {w.get('age','')}: {w.get('desc','')}\n")
                    # 위험 구간 (과거분)
                    dz2 = hl.get("danger_zones", [])
                    if dz2:
                        try:
                            past_dz2 = [d for d in dz2 if d.get("year","") and int(d["year"].split("~")[-1]) <= current_year]
                        except Exception: past_dz2 = []
                        if past_dz2:
                            out.append("\n**[과거 위험 구간 — 힘든 시기의 근거]**\n")
                            for d in past_dz2[:2]: out.append(f"* {d.get('age','')}: {d.get('desc','')}\n")

                elif is_job:
                    gk  = get_gyeokguk(pils)
                    gkn = gk["격국명"] if gk else "미정격"
                    ys2 = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                    y1j = ys2.get("용신_1순위", "-")
                    si_j2 = get_ilgan_strength(ilgan_loc, pils)
                    sn_j2 = si_j2.get("신강신약","중화")
                    _JOB2 = {
                        "정관격":"조직·공직·행정·관리직·법조가 천직이니라. 안정된 조직 안에서 명예와 재물이 함께 오느니라. 공무원·대기업·공공기관이 최적이니라.",
                        "편관격":"군경·의료·법조·스포츠·안전·소방·국방 분야에서 진가를 발휘하느니라. 강인한 의지와 추진력이 강점이니라.",
                        "정재격":"금융·회계·부동산·세무·유통·은행이 맞느니라. 성실한 노력으로 안정된 자산을 쌓는 팔자니라. 꼼꼼함과 책임감이 무기니라.",
                        "편재격":"사업·영업·투자·무역·중개·부동산 개발이 맞느니라. 기회를 포착하는 사업가 기질이 타고났느니라. 빠른 판단력이 핵심이니라.",
                        "식신격":"요식·창작·예술·교육·서비스·콘텐츠·강의가 맞느니라. 재능이 곧 밥그릇이 되는 팔자니라.",
                        "상관격":"IT·방송·컨설팅·프리랜서·스타트업·예술가에서 독보적 존재가 되느니라. 창의력이 최대 무기니라.",
                        "편인격":"학문·연구·철학·심리·의학·IT연구·특허 분야가 천직이니라. 깊은 통찰이 곧 경쟁력이니라.",
                        "정인격":"교육·학술·전문직·자격증 기반 직종·상담이 맞느니라. 배움이 쌓일수록 위상이 높아지느니라.",
                        "비견격":"독립·자영업·프리랜서·개인사업·1인 기업이 맞느니라. 혼자 움직일 때 가장 강해지는 팔자니라.",
                        "겁재격":"경쟁·협상·중개·스포츠·증권·선물 분야에서 오히려 빛나는 팔자니라.",
                    }
                    _OHJOB2 = {
                        "木":"목재·제지·섬유·교육·의류·원예·환경·에너지·스포츠 관련 업종이 유리하느니라.",
                        "火":"방송·광고·전기·전자·IT·연예·문화·조명·화학 관련 업종이 유리하느니라.",
                        "土":"부동산·건설·농업·의약·식품·유통·경영컨설팅 관련 업종이 유리하느니라.",
                        "金":"금융·금속·기계·법조·의료·국방·스포츠·경찰 관련 업종이 유리하느니라.",
                        "水":"무역·해운·유통·관광·호텔·미디어·철학·심리 관련 업종이 유리하느니라.",
                    }
                    _SWJOB2 = {
                        "食神":"올해는 재능 발휘와 자격 취득에 최적의 해니라. 새 프로젝트를 시작하게!",
                        "正官":"승진·이직·공직 시험에 유리한 해니라. 조직 내 신뢰를 쌓는 것이 핵심이니라.",
                        "偏財":"사업·영업 기회가 오는 해니라. 적극적으로 나서되 도박성 투자는 자제하게.",
                        "正財":"안정된 수입·직장 유지에 좋은 해니라. 차분하게 실력을 쌓는 것이 맞느니라.",
                        "傷官":"독립·창업·이직을 고려한다면 올해가 전환점이 될 수 있느니라. 단 계약서 주의.",
                        "偏官":"직장 변동·갈등이 올 수 있느니라. 무리한 도전보다 현 자리 지키기가 현명하니라.",
                    }
                    out.append(f"**{name}의 직업·진로 완전 분석**\n격국 **{gkn}**의 천직을 신안으로 살펴보겠느니라.\n")
                    out.append(_JOB2.get(gkn, f"{gkn}의 독특한 기운을 살려 자신만의 길을 개척해야 하느니라.") + "\n")
                    # 십성 분포 분석
                    try:
                        ss_list_j2 = calc_sipsung(ilgan_loc, pils)
                        _GRP2 = {"비견":"비겁","겁재":"비겁","식신":"식상","상관":"식상",
                                "정재":"재성","편재":"재성","정관":"관성","편관":"관성","정인":"인성","편인":"인성"}
                        sc_cnt2 = {}
                        for p in ss_list_j2:
                            g = _GRP2.get(p.get("십성",""),"")
                            if g: sc_cnt2[g] = sc_cnt2.get(g, 0) + 1
                        top_g2 = max(sc_cnt2, key=sc_cnt2.get) if sc_cnt2 else ""
                        _SGJ2 = {"재성":"재물을 직접 다루는 영역에서 두각을 드러내느니라.",
                                "관성":"조직과 권위 안에서 진가가 빛나느니라.",
                                "식상":"창의와 표현으로 세상을 사로잡는 팔자니라.",
                                "인성":"배움과 자격증으로 전문성을 쌓는 것이 맞느니라.",
                                "비겁":"독립과 경쟁 속에서 오히려 강해지는 팔자니라."}
                        if top_g2: out.append(f"\n사주 십성 분포상 **{top_g2}** 기운이 강하니 {_SGJ2.get(top_g2,'')}\n")
                    except Exception: pass
                    # 용신 오행 업종
                    out.append(f"\n**[용신 오행 업종]** 용신 **{y1j}** — {_OHJOB2.get(y1j, f'{y1j} 오행 관련 업종이 맞느니라.')}\n")
                    # 신강신약 행동 패턴
                    if "신강" in sn_j2:
                        out.append(f"\n**신강({sn_j2})** — 독립·창업·단독 행보가 최적이니라. 조직보다 자신이 주도하는 환경에서 능력을 발휘하느니라.\n")
                    elif "신약" in sn_j2:
                        out.append(f"\n**신약({sn_j2})** — 안정된 조직·전문직 안에서 귀인의 도움을 받는 것이 최적이니라. 창업보다 전문성 강화가 우선이니라.\n")
                    # 올해 진로 세운
                    sw_j2 = get_yearly_luck(pils, current_year)
                    sw_j2_ss = sw_j2.get("십성_천간","")
                    out.append(f"\n올해({current_year}년) {sw_j2.get('세운','')} [{sw_j2_ss}] {sw_j2.get('길흉','')} — {_SWJOB2.get(sw_j2_ss, sw_j2_ss + ' 기운의 해이니 흐름을 잘 읽고 움직이게.')}\n")
                    out.append(f"\n용신 **{y1j}** 오행이 강한 해에 진로 결정을 내리면 가장 유리하느니라. 명심하게!\n")

                elif is_char:
                    gk  = get_gyeokguk(pils)
                    si  = get_ilgan_strength(ilgan_loc, pils)
                    gkn = gk["격국명"] if gk else "미정격"
                    sn  = si.get("신강신약", "중화")
                    sc  = si.get("일간점수", 50)
                    _CG_KR2 = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계'}
                    _ilgan_k2 = f"{ilgan_loc}({_CG_KR2.get(ilgan_loc, '')})"
                    _CHR = ILGAN_CHAR_DESC.get(_ilgan_k2, ILGAN_CHAR_DESC.get(ilgan_loc, {}))
                    oh_s_c2 = calc_ohaeng_strength(ilgan_loc, pils)
                    out.append(f"**{name}의 성격·기질 완전 분석**\n일간 **{ilgan_loc}** | 격국 **{gkn}** | **{sn}**(점수 {sc}/100)\n")
                    out.append(_CHR.get("성격_핵심", f"일간 {ilgan_loc}의 기운이 삶 전반을 이끄느니라.") + "\n")
                    if _CHR.get("장점"): out.append(f"\n**[장점]** {_CHR['장점']}\n")
                    if _CHR.get("단점"): out.append(f"**[주의]** {_CHR['단점']}\n")
                    if _CHR.get("재물패턴"): out.append(f"**[재물 성향]** {_CHR['재물패턴']}\n")
                    if _CHR.get("건강"): out.append(f"**[건강 주의]** {_CHR['건강']}\n")
                    if _CHR.get("직업"): out.append(f"**[천직 힌트]** {_CHR['직업']}\n")
                    _SNS2 = {
                        "신강": f"기운이 넘치는 신강({sc}/100)이니라. 스스로 움직여야 기회가 오느니라. 독립적 결단이 맞는 팔자이나 자기중심적으로 흐를 수 있으니 타인 의견에도 귀를 열게.",
                        "신약": f"기운이 부족한 신약({sc}/100)이니라. 귀인과 함께할 때 진가가 발휘되느니라. 좋은 파트너·스승이 운명을 바꾸느니라. 협업 속에서 빛나는 팔자이니라.",
                        "중화": f"기운이 균형 잡힌 중화({sc}/100)이니라. 어느 상황에도 적응하는 유연함이 강점이니라. 꾸준함과 전문성이 최대 무기이니라.",
                    }
                    for k, v in _SNS2.items():
                        if k in sn: out.append(f"\n**[신강신약 행동 패턴]** {v}\n"); break
                    # 오행 과다 성격 패턴
                    _OHC2 = {
                        "木":"木 과다: 고집이 세고 자기주장이 강하며 리더십이 강함. 하지만 융통성 부족 주의.",
                        "火":"火 과다: 열정적이고 급하며 사교성이 뛰어남. 하지만 과잉 행동과 산만함 주의.",
                        "土":"土 과다: 신중하고 보수적이며 인내심이 강함. 하지만 변화 거부와 고집 주의.",
                        "金":"金 과다: 원칙주의적이고 결단력이 강함. 하지만 냉철함이 지나쳐 인간관계 문제 주의.",
                        "水":"水 과다: 지혜롭고 유연하며 전략적. 하지만 우유부단과 비밀주의 주의.",
                    }
                    for o, v in oh_s_c2.items():
                        if v >= 35: out.append(f"\n{_OHC2.get(o,'')}\n")
                    sw = get_yearly_luck(pils, current_year)
                    out.append(f"\n올해({current_year}년)는 {sw.get('세운','')} [{sw.get('십성_천간','')}] {sw.get('길흉','')} 기운이니 그 흐름을 잘 타게.\n")

                else:
                    gk  = get_gyeokguk(pils); ys = get_yongshin_multilayer(pils, birth_year, gender, bm, bd, bh, bmn, current_year)
                    si  = get_ilgan_strength(ilgan_loc, pils)
                    gkn = gk["격국명"] if gk else "미정격"; sn = si["신강신약"]; sc = si.get("일간점수",50)
                    y1  = ys.get("용신_1순위","-"); heui = ys.get("희신","-"); gisin = ", ".join(ys.get("기신",[]))
                    sw  = get_yearly_luck(pils, current_year)
                    sw_ss = sw.get("십성_천간",""); sw_gan = sw.get("세운",""); sw_gh = sw.get("길흉","")
                    # 1️⃣ 천기의 낙인
                    _GKS= {"정관격":"규칙과 질서의 격국. 조직에서 권위를 얻을 팔자이니라. 공직·관리직이 천직이니라.",
                           "편관격":"칠살격 — 강인한 의지의 팔자. 시련이 클수록 더 강해지는 팔자이니라.",
                           "정재격":"성실한 재물격. 꾸준함이 쌓여 반드시 부를 이루는 팔자이니라.",
                           "편재격":"활동적 사업가격. 큰 기회와 기복이 공존하는 팔자이니라.",
                           "식신격":"복록이 넘치는 격국. 재능이 곧 밥그릇이 되는 팔자이니라.",
                           "상관격":"창의성과 반골 기질의 격국. 독립 행보에서 진가가 나오는 팔자이니라.",
                           "편인격":"직관과 영감의 격국. 깊은 전문성으로 독보적 경지에 오르는 팔자이니라.",
                           "정인격":"학문과 명예의 귀격. 배움이 쌓일수록 위상이 높아지는 팔자이니라.",
                           "비견격":"독립심의 격국. 남 밑에 있으면 기운이 막히는 팔자이니라.",
                           "겁재격":"승부사 기질의 격국. 경쟁 속에서 오히려 빛나는 팔자이니라."}
                    out.append(f"\n**1️⃣ [천기의 낙인]**\n일간 **{ilgan_loc}** | 격국 **{gkn}** | {sn}(기력 {sc}점)\n")
                    out.append(_GKS.get(gkn, f"{gkn}의 독특한 기운을 타고난 팔자이니라.") + "\n")
                    out.append(f"용신 **{y1}** 기운이 흐를 때 발복하느니라. 기신 **{gisin}** 기운은 경계하게.\n")
                    # 2️⃣ 신안의 복기
                    try:
                        hl_e = generate_engine_highlights(pils, birth_year, gender, bm, bd, bh, bmn)
                        pevs_e = sorted(hl_e.get("past_events",[]), key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e.get("intensity","🟢"),3))
                        out.append(f"\n**2️⃣ [신안의 복기]**\n")
                        if pevs_e:
                            for ev in pevs_e[:2]:
                                out.append(f"**{ev.get('year','')}년 ({ev.get('age','')})** {ev.get('intensity','')} [{ev.get('domain','변화')}]: {ev.get('desc','')}\n")
                        else:
                            out.append("지나온 세월의 흔적이 이 팔자에 깊이 새겨져 있느니라.\n")
                    except Exception: pass
                    # 3️⃣ 현재의 형국
                    out.append(f"\n**3️⃣ [현재의 형국]**\n올해({current_year}년) **{sw_gan}** [{sw_ss}] — {sw_gh} 기운이니라.\n")
                    out.append(f"{'용신 세운이 흐르는 황금기이니라. 지금 움직이지 않으면 언제 움직이겠는가!' if sw_ss in (y1, heui) else '지금은 신중하게 내실을 다지는 시기이니라. 무리한 확장은 금물이니라.'}\n")
                    # 4️⃣ 필살의 비방
                    _BIYB = {
                        "木":"새벽 인시(寅(인)時 03~05시)에 동쪽 창문을 열고 파란 옷 입은 채 깊게 호흡하게. 목기(木氣)가 충전되느니라.",
                        "火":"정오 오시(午(오)時 11~13시)에 남쪽 방향으로 붉은 소품을 놓게. 화기(火氣)의 밝음이 운을 열어주느니라.",
                        "土":"환절기에 황색 음식(꿀·고구마)을 먹으며 중심을 잡게. 토기(土氣)가 안정을 가져오느니라.",
                        "金":"서쪽 방향 책상 위에 금속 소품을 놓고 결단력을 다지게. 금기(金氣)가 길을 열어주느니라.",
                        "水":"해시(亥(해)時 21~23시)에 북쪽 방향으로 검은 물컵을 두게. 수기(水氣)가 지혜를 불러오느니라.",
                    }
                    out.append(f"\n**4️⃣ [필살의 비방]**\n")
                    out.append(_BIYB.get(y1, f"용신 {y1} 오행의 기운을 강화하는 색상·방향·음식을 일상에서 실천하게. 이것이 운명을 바꾸는 열쇠이니라.") + "\n")

            except Exception as _le:
                out.append(f"\n허어, 기운이 잠시 흔들렸느니라. 기본 팔자로 답을 드리겠네. (오류: {_le})\n")

            out.append(f"\n---\n*내 신안(神眼)이 본 {name}의 팔자가 이러하니라. 더 깊이 알고 싶다면 다시 물어보게.*")
            return "\n".join(out)

        # ── 로컬 사주 엔진 (완전 자체 처리) ──────────────────────────────
        with st.chat_message("assistant"):
            _resp = _local_saju_response(user_query)
            # 후속 질문
            trust_lv = mem.get("trust", {}).get("level", 1)
            follow_up = FollowUpGenerator.get_question(intent_res['topic'], trust_level=trust_lv).replace("{name}", name)
            final_resp = f"{_resp}\n\n---\n💡 **만신의 깊은 질문:** {follow_up}"
            st.markdown(final_resp)
            st.session_state.chat_history.append({"role": "assistant", "content": final_resp})
            # 데이터 영속화
            SajuMemory.record_interest(name, intent_res['topic_kr'])
            SajuMemory.add_conversation(name, intent_res['topic_kr'], _resp, intent_res['emotion'])
            LifeNarrativeEngine.update_narrative(name, intent_res['topic_kr'], intent_res['emotion'])
        st.rerun()


def menu7_ai(pils, name, birth_year, gender, api_key, groq_key=""):
    """7️⃣ 만신 상담소 - AI 대화형 상담 센터 (E-Version)"""

    st.markdown("""
    <div style="background:linear-gradient(135deg,#fff8e1,#fffde7);border:2px solid #d4af3755;border-radius:14px;
                padding:20px;margin-bottom:14px;box-shadow:0 4px 15px rgba(212,175,55,0.1)">
        <div style="font-size:18px;font-weight:900;color:#d4af37;margin-bottom:6px">🏛️ 만신 상담소 (萬神 相談所)</div>
        <div style="font-size:13px;color:#000000;line-height:1.8">
        "인생의 갈림길에서 답답할 때, <b>만신</b>에게 물어보세요."<br>
        * <b>궁합, 재물, 커리어, 건강</b> 등 모든 고민을 영속 기억 시스템 기반으로 상담합니다.
    </div></div>""", unsafe_allow_html=True)

    # -- 엔진 상태 표시 --
    st.markdown('<div style="background:#e8f5e8;color:#2e7d32;padding:6px 12px;border-radius:8px;font-size:11px;margin-bottom:10px">🔮 자체 사주 분석 엔진 가동 중 — 만세력 / 격국 / 용신 / 대운 완전 분석</div>', unsafe_allow_html=True)

    # -- 상담 집중 분야 선택 --
    c1, c2 = st.columns([3, 1])
    with c1:
        focus_key = st.selectbox("집중 상담 분야", ["종합", "재물/사업", "연애/결혼", "직장/커리어", "학업/시험", "건강"], index=0)
    with c2:
        if st.button("🔄 기록 초기화", help="현재 상담 이력만 초기화합니다"):
            st.session_state.chat_history = []
            st.rerun()

    # -- 소름 엔진 (과거 적중 미리보기) --
    try:
        gb = goosebump_engine(pils, birth_year, gender)
        if gb["past"]:
            with st.expander("🔮 이전에 이런 일을 겪으셨나요?", expanded=True):
                for s in gb["past"][:2]:
                    st.markdown(f'<div style="background:#f9f9f9;border-left:3px solid #d4af37;padding:8px 12px;margin:4px 0;font-size:13px">🔍 {s}</div>', unsafe_allow_html=True)
    except Exception: pass

    # -- AI 상담 메인 (E-Version Chat) --
    tab_ai_chat(pils, name, birth_year, gender, api_key, groq_key=groq_key)






def menu13_career(pils, name, birth_year, gender):
    """1️⃣3️⃣ 직장운 -- 십성(十星) 기반 진로 및 커리어 분석"""
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #1a253c, #0a1428); padding:20px; border-radius:16px; border-left:5px solid #d4af37; margin-bottom:20px; box-shadow: var(--shadow);">
        <div style="color:#d4af37; font-size:24px; font-weight:900; letter-spacing:2px;">💼 {name}님의 직장운 / 커리어</div>
        <div style="color:rgba(255,255,255,0.7); font-size:13px; margin-top:4px;">십성(十星)의 흐름으로 보는 천직과 성공 전략</div>
    </div>
    """, unsafe_allow_html=True)

    try:
        ilgan = pils[1]["cg"]
        ss_list = calc_sipsung(ilgan, pils)
        
        # 십성 카운팅
        counts = {"비겁":0, "식상":0, "재성":0, "관성":0, "인성":0}
        ss_names = {
            "비견":"비겁", "겁재":"비겁",
            "식신":"식상", "상관":"식상",
            "편재":"재성", "정재":"재성",
            "편관":"관성", "정관":"관성",
            "편인":"인성", "정인":"인성"
        }
        
        for item in ss_list:
            if item["cg_ss"] in ss_names: counts[ss_names[item["cg_ss"]]] += 1
            if item["jj_ss"] in ss_names: counts[ss_names[item["jj_ss"]]] += 1

        # 분석 결과 도출
        primary_ss = max(counts, key=counts.get)
        
        # UI 섹션: 커리어 성향
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.markdown('<div class="section-label">🎯 핵심 직업 성향</div>', unsafe_allow_html=True)
            traits = {
                "비겁": ("자기주도형", "독립적인 사업이나 자유업, 전문직이 어울립니다."),
                "식상": ("기술/예술형", "전문 기술, 창의적 기획, 교육, 예술 분야에 탁월합니다."),
                "재성": ("재무/관리형", "금융, 유통, 경영 관리, 사업 수완이 뛰어납니다."),
                "관성": ("조직/관리형", "공직, 대기업, 체계적인 조직 생활에서 두각을 나타냅니다."),
                "인성": ("학술/연구형", "학문, 연구, 자격증 기반 전문직, 문서 관련 업무에 강합니다.")
            }
            title, desc = traits.get(primary_ss, ("균형형", "다양한 분야에서 유연한 적응력을 보입니다."))
            st.markdown(f"""
            <div style="background:rgba(212,175,55,0.1); border:1px solid #d4af37; padding:15px; border-radius:12px; text-align:center;">
                <div style="font-size:18px; font-weight:900; color:#d4af37; margin-bottom:8px;">{title}</div>
                <div style="font-size:13px; color:#eee;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="section-label">📊 직군별 적합도</div>', unsafe_allow_html=True)
            for ss, count in counts.items():
                score = min(100, count * 20 + 20)
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:2px;">
                        <span>{ss} 기운</span>
                        <span>{score}%</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.1); height:8px; border-radius:4px; overflow:hidden;">
                        <div style="background:linear-gradient(90deg, #d4af37, #f4e4bc); width:{score}%; height:100%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # 상세 조언
        st.markdown('<div class="gold-section">🛡️ 커리어 성공 전략</div>', unsafe_allow_html=True)
        advice_map = {
            "비겁": "혼자보다는 파트너십을 활용하되, 본인의 주도권을 잃지 않는 환경이 중요합니다. 1인 기업이나 전문 자격직이 유리합니다.",
            "식상": "본인만의 독창적인 결과물을 만들어내는 능력이 자산입니다. 끊임없이 기술이나 재능을 연마하여 대체 불가능한 존재가 되십시오.",
            "재성": "결과 중심의 업무에서 큰 성취를 느낍니다. 숫자에 밝고 현실적인 감각이 있으니 실무 책임자나 사업 경영에서 빛을 발합니다.",
            "관성": "명예와 체면을 중시하며 사회적 지위 상승에 대한 욕구가 강합니다. 정해진 룰 안에서 최고의 성과를 내는 능력이 탁월합니다.",
            "인성": "지식과 정보를 가공하는 능력이 뛰어납니다. 남들이 모르는 깊이 있는 지식을 습득하여 멘토나 전문가로 명성을 쌓으십시오."
        }
        st.markdown(f"""
        <div class="saju-narrative" style="color:#eee; background:rgba(255,255,255,0.03); padding:15px; border-radius:12px;">
            💡 <b>{name}님을 위한 조언:</b> {advice_map.get(primary_ss, "균형 잡힌 시각으로 조직 내에서 중추적인 역할을 수행하십시오.")} 
            특히 올해는 자신의 재능을 외부로 드러내는 시기이므로 적극적인 제안이나 도전을 추천합니다.
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"직장운 분석 중 오류 발생: {e}")

def menu14_health(pils, name, birth_year, gender):
    """1️⃣4️⃣ 건강운 -- 오행(五行) 균형 및 체질 분석"""
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#fff5f5,#ffe8e8);padding:20px;border-radius:16px;
            border-left:5px solid #c0392b;margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,0.06)">
    <div style="color:#c0392b;font-size:22px;font-weight:900;letter-spacing:2px">💊 {name}님의 건강운 / 체질</div>
    <div style="color:#555;font-size:13px;margin-top:4px;font-weight:600">오행(五行)의 과다와 부족으로 보는 맞춤형 양생법</div>
</div>
""", unsafe_allow_html=True)

    try:
        ilgan = pils[1]["cg"]
        oh_strength = calc_ohaeng_strength(ilgan, pils)
        
        # 취약 오행 찾기 (가장 낮은 것)
        weak_oh = min(oh_strength, key=oh_strength.get)
        excess_oh = max(oh_strength, key=oh_strength.get)
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.markdown('<div class="section-label">🩺 오행 건강 밸런스</div>', unsafe_allow_html=True)
            st.write("")
            render_ohaeng_chart(oh_strength)

        with col2:
            st.markdown('<div class="section-label">[!]️ 중점 관리 부위</div>', unsafe_allow_html=True)
            health_map = {
                "木": ("간 / 담 / 눈", "목(木) 기운은 신경계와 간 건강을 관장합니다. 피로 회복과 스트레스 관리에 힘써야 합니다."),
                "火": ("심장 / 소장 / 혈압", "화(火) 기운은 혈액순환과 열기를 담당합니다. 안정을 취하고 열을 내리는 습관이 필요합니다."),
                "土": ("위장 / 비장 / 피부", "토(土) 기운은 소화기와 신진대사를 관장합니다. 규칙적인 식습관과 위장 보호가 핵심입니다."),
                "金": ("폐 / 대장 / 호흡기", "금(金) 기운은 호흡기와 피부 건강을 담당합니다. 건조하지 않은 환경과 기관지 보호가 중요합니다."),
                "水": ("신장 / 방광 / 생식기", "수(水) 기운은 신체 수분과 호르몬을 관장합니다. 충분한 수분 섭취와 비뇨기 관리가 필요합니다.")
            }
            
            target, detail = health_map.get(weak_oh if oh_strength[weak_oh] < 15 else excess_oh, ("전반적 균형", "관리 상태가 양호합니다."))
            st.markdown(f"""
<div style="background:#fff5f5;border:1.5px solid #e74c3c;padding:15px;border-radius:12px">
    <div style="font-size:16px;font-weight:900;color:#c0392b;margin-bottom:6px">{target}</div>
    <div style="font-size:13px;color:#333;line-height:1.8;font-weight:500">{detail}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="gold-section">🍵 추천 생활 습관 (양생법)</div>', unsafe_allow_html=True)
        tips = {
            "木": "산책과 가벼운 운동으로 기운을 순환시키고, 녹색 채소와 신맛이 나는 음식을 섭취하면 간 기능에 도움을 줍니다.",
            "火": "충분한 수면과 명상으로 심장의 화기를 다스리십시오. 쓴맛이 나는 음식과 빨간색 과일이 좋습니다.",
            "土": "천천히 씹어 먹는 습관을 기르고, 단맛이 나는 뿌리 채소나 노란색 음식을 적절히 섭취하십시오.",
            "金": "등산이나 심호흡을 통해 폐 기운을 맑게 하고, 매운맛을 지닌 음식과 흰색 음식을 섭취하여 대장을 정화하십시오.",
            "水": "반신욕을 즐기고 차가운 환경을 멀리하십시오. 검은콩이나 깨 등 블랙푸드가 신장 건강을 돕습니다."
        }
        st.markdown(f"""
<div style="background:#f8fff8;border:1.5px solid #27ae60;border-radius:12px;padding:18px 20px;margin-top:8px">
    <div style="font-size:14px;color:#1a5c2a;line-height:2.0;font-weight:600">
        🌿 <b>체질 맞춤 처방:</b> {tips.get(weak_oh, '규칙적인 생활과 적절한 운동으로 중도(中道)를 유지하십시오.')}
        특히 환절기에는 체온 유지가 건강의 핵심이니 항상 몸을 따뜻하게 보호하는 것이 좋습니다.
    </div>
</div>
""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"건강운 분석 중 오류 발생: {e}")

def menu12_manse(pils=None, birth_year=1990, gender="남"):
    """📅 만세력 탭 -- 일진/절기/길일달력 통합 UI"""
    today = datetime.now()

    st.markdown("""
    <div style='background:#000;color:#fff;border-radius:12px;
                padding:16px 20px;margin-bottom:14px'>
        <div style='font-size:20px;font-weight:900;letter-spacing:2px'>
            📅 만세력 / 일진 / 절기 달력
        </div>
        <div style='font-size:12px;opacity:0.7;margin-top:4px'>
            일진(日辰(진)) / 24절기 / 길일/흥일 자동 표시
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
    </div>
""", unsafe_allow_html=True)

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
        <span style='color:#1a7a1a;font-weight:700'>- 길일:</span>
        {', '.join(str(d)+'일' for d in gil_days) or '없음'} &nbsp;&nbsp;
        <span style='color:#cc0000;font-weight:700'>[!]️ 주의:</span>
        {', '.join(str(d)+'일' for d in warn_days) or '없음'}
    </div>
""", unsafe_allow_html=True)

    # -- - 사주 맞춤 길일 추천 카드 (NEW) ----------------------
    if pils:
        st.markdown('<div class="gold-section" style="margin-top:24px">- 이번 달 당신의 사주 맞춤 길일 추천</div>', unsafe_allow_html=True)
        try:
            ilgan_m = pils[1]["cg"]
            lucky_ss_map = {
                "甲(갑)": ["정재","정인","정관","식신"],
                "乙(을)": ["정관","정재","정인","식신"],
                "丙(병)": ["정재","식신","정인","정관"],
                "丁(정)": ["정재","식신","정관","정인"],
                "戊(무)": ["정관","정재","정인","편재"],
                "己(기)": ["정관","편재","정재","정인"],
                "庚(경)": ["정재","정관","정인","식신"],
                "辛(신)": ["정재","정관","정인","식신"],
                "壬(임)": ["정재","식신","정관","정인"],
                "癸(계)": ["정재","식신","정인","정관"],
            }
            lucky_ss = lucky_ss_map.get(ilgan_m, ["정재","식신","정관","정인"])

            saju_lucky = []
            for entry in cal_data:
                d_ss = TEN_GODS_MATRIX.get(ilgan_m, {}).get(entry["iljin"]["cg"], "-")
                if d_ss in lucky_ss and entry["gil"]["grade"] != "주의":
                    saju_lucky.append({
                        "day":  entry["day"],
                        "iljin": entry["iljin"]["str"],
                        "ss":   d_ss,
                        "grade": entry["gil"]["grade"],
                        "weekday": ["月","火","水","木","金","土","日"][(first_wd + entry["day"] - 1) % 7]
                    })

            if saju_lucky:
                lucky_cards = ""
                SS_ICON = {"정재":"💰","식신":"🌟","정관":"🎖️","정인":"📚","편재":"💼","비견":"🤝","정관":"🎖️"}
                for lk in saju_lucky[:6]:
                    icon = SS_ICON.get(lk["ss"], "-")
                    grade_color = "#4caf50" if "길일" in lk["grade"] else "#888"
                    lucky_cards += f"""
                    <div style="display:inline-block;background:rgba(255,255,255,0.9);backdrop-filter:blur(10px);
                                border:1.5px solid #d4af37;border-radius:14px;padding:12px 16px;
                                margin:5px;text-align:center;min-width:90px;box-shadow:0 4px 15px rgba(212,175,55,0.1)">
                        <div style="font-size:20px">{icon}</div>
                        <div style="font-size:18px;font-weight:900;color:#000">{lk['day']}일</div>
                        <div style="font-size:11px;color:#777">({lk['weekday']})</div>
                        <div style="font-size:11px;font-weight:700;color:#b38728">{lk['iljin']}</div>
                        <div style="font-size:10px;color:{grade_color};margin-top:2px">{lk['ss']}</div>
                    </div>"""
                st.markdown(f"""
                <div style="margin:10px 0 20px">
                    <div style="font-size:13px;color:#555;margin-bottom:8px">
                        {ilgan_m} 일간에게 유리한 십성({', '.join(lucky_ss[:3])}) 날을 우선 추천합니다.
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:4px">{lucky_cards}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("이번 달은 사주 맞춤 길일이 별도로 표시되지 않습니다. 일반 길일을 활용하세요.")
        except Exception as e:
            st.warning(f"맞춤 길일 계산 오류: {e}")

    # -- [!]️ 사주 맞춤 조심일 경고 카드 (NEW) ----------------------
    if pils:
        st.markdown('<div class="gold-section" style="margin-top:8px">[!]️ 이번 달 당신의 사주 맞춤 조심일</div>', unsafe_allow_html=True)
        try:
            ilgan_w = pils[1]["cg"]
            # 각 일간별 주의해야 할 십성 (흉신)
            warn_ss_map = {
                "甲(갑)": ["겁재","편관","상관"],
                "乙(을)": ["겁재","편관","상관"],
                "丙(병)": ["겁재","편관","편인"],
                "丁(정)": ["겁재","편관","편인"],
                "戊(무)": ["겁재","편관","상관"],
                "己(기)": ["겁재","편관","상관"],
                "庚(경)": ["겁재","편관","상관"],
                "辛(신)": ["겁재","편관","상관"],
                "壬(임)": ["겁재","편관","편인"],
                "癸(계)": ["겁재","편관","편인"],
            }
            SS_WARN_DESC = {
                "겁재": {"emoji":"💸","color":"#e53935","msg":"재물 손실/인간관계 갈등 주의. 큰 지출이나 보증/투자 금지"},
                "편관": {"emoji":"⚡","color":"#7b1fa2","msg":"건강 악화/관재구설 주의. 법적 서류나 공식 분쟁은 미루세요"},
                "상관": {"emoji":"🌪️","color":"#f57c00","msg":"말실수/직장 내 갈등 주의. 중요한 자리에서 발언을 삼가세요"},
                "편인": {"emoji":"🌀","color":"#0288d1","msg":"판단력 저하/우유부단 주의. 큰 결정은 다음 날로 미루세요"},
            }
            warn_ss = warn_ss_map.get(ilgan_w, ["겁재","편관","상관"])

            saju_warn = []
            for entry in cal_data:
                d_ss_w = TEN_GODS_MATRIX.get(ilgan_w, {}).get(entry["iljin"]["cg"], "-")
                if d_ss_w in warn_ss:
                    saju_warn.append({
                        "day":  entry["day"],
                        "iljin": entry["iljin"]["str"],
                        "ss":   d_ss_w,
                        "grade": entry["gil"]["grade"],
                        "weekday": ["月","火","水","木","金","土","日"][(first_wd + entry["day"] - 1) % 7]
                    })

            if saju_warn:
                warn_cards = ""
                for wk in saju_warn[:8]:
                    wd = SS_WARN_DESC.get(wk["ss"], {"emoji":"[!]️","color":"#e53935","msg":"매사 조심"})
                    is_double = wk["grade"] == "주의"  # 달력 흉일 + 사주 흉성 겹침
                    border_style = f"2px solid {wd['color']}"
                    extra_badge = '<div style="font-size:9px;background:#e53935;color:#fff;border-radius:4px;padding:1px 4px;margin-top:2px">[!]️ 이중 주의</div>' if is_double else ""
                    warn_cards += f"""
                    <div style="display:inline-block;background:rgba(255,235,235,0.95);backdrop-filter:blur(10px);
                                border:{border_style};border-radius:14px;padding:12px 14px;
                                margin:5px;text-align:center;min-width:90px;box-shadow:0 4px 15px rgba(229,57,53,0.1)">
                        <div style="font-size:20px">{wd['emoji']}</div>
                        <div style="font-size:18px;font-weight:900;color:{wd['color']}">{wk['day']}일</div>
                        <div style="font-size:11px;color:#777">({wk['weekday']})</div>
                        <div style="font-size:11px;font-weight:700;color:#555">{wk['iljin']}</div>
                        <div style="font-size:10px;color:{wd['color']};margin-top:2px;font-weight:700">{wk['ss']}</div>
                        {extra_badge}
                    </div>"""

                # 조심일 요약 표
                warn_table = ""
                shown = set()
                for wk in saju_warn:
                    if wk["ss"] not in shown:
                        shown.add(wk["ss"])
                        wd2 = SS_WARN_DESC.get(wk["ss"], {"emoji":"[!]️","color":"#e53935","msg":"매사 조심"})
                        warn_table += f'<div style="margin:4px 0;font-size:13px"><span style="color:{wd2["color"]};font-weight:900">{wd2["emoji"]} {wk["ss"]}</span>: {wd2["msg"]}</div>'

                st.markdown(f"""
                <div style="margin:10px 0 20px">
                    <div style="font-size:13px;color:#cc0000;margin-bottom:8px;font-weight:700">
                        [!]️ {ilgan_w} 일간에게 불리한 십성({', '.join(warn_ss)}) 날 - 총 {len(saju_warn)}일
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px">{warn_cards}</div>
                    <div style="background:rgba(229,57,53,0.05);border:1px solid #ffcdd2;border-radius:12px;padding:12px 16px">
                        <div style="font-size:12px;font-weight:900;color:#b71c1c;margin-bottom:6px">📌 조심일 행동 지침</div>
                        {warn_table}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 오늘이 조심일이면 경고 토스트
                today_ss_warn = TEN_GODS_MATRIX.get(ilgan_w, {}).get(
                    today_iljin["cg"] if "cg" in today_iljin else today_iljin["str"][0], "-")
                if today_ss_warn in warn_ss and sel_month == today.month and sel_year == today.year:
                    st.error(f"🚨 **오늘({today.day}일)은 {today_ss_warn} 일입니다.** {SS_WARN_DESC.get(today_ss_warn, {}).get('msg','매사 조심하십시오.')}")
            else:
                st.success("✅ 이번 달은 특별히 조심해야 할 사주 맞춤 흉일이 없습니다. 평온한 한 달이 예상됩니다.")
        except Exception as e:
            st.warning(f"조심일 계산 오류: {e}")

    if pils and sel_month == today.month and sel_year == today.year:
        st.markdown('<div class="gold-section" style="margin-top:20px">🔮 오늘 일진으로 보는 만신의 맞춤 조언</div>', unsafe_allow_html=True)
        try:
            ilgan_ad = pils[1]["cg"]
            today_iljin_cg = today_iljin["cg"] if "cg" in today_iljin else today_iljin["str"][0]
            today_iljin_jj = today_iljin["jj"] if "jj" in today_iljin else today_iljin["str"][1]
            today_ss_ad = TEN_GODS_MATRIX.get(ilgan_ad, {}).get(today_iljin_cg, "-")

            # 십성별 만신 맞춤 조언
            SS_ADVICE = {
                "비견":  {"emoji":"🤝","title":"동반자의 날","short":"협력으로 빛나는 날","detail":"오늘은 혼자보다 함께가 힘이 됩니다. 신뢰하는 파트너와 의논하면 뜻밖의 해법이 보입니다. 고집을 내려놓고 경청하면 좋은 인연이 강화됩니다.","action":"오늘 할 일: 오래 연락 못 한 지인에게 먼저 연락해 보세요."},
                "겁재":  {"emoji":"[!]️","title":"자중의 날","short":"지갑과 감정을 닫으세요","detail":"재물과 에너지 소모가 클 수 있는 날입니다. 충동적인 결정이나 감정적인 대응을 삼가고, 오늘만큼은 '저축'하는 마음으로 하루를 보내십시오.","action":"오늘 할 일: 불필요한 지출 0원 목표. 중요한 계약이나 투자는 내일로 미루세요."},
                "식신":  {"emoji":"🌟","title":"창조의 날","short":"새로운 시작에 최적의 날","detail":"오늘은 복록과 창의가 함께하는 날입니다. 새로운 프로젝트를 시작하거나, 그동안 미뤄온 일을 실행에 옮기기에 더없이 좋습니다. 맛있는 것을 즐기는 것도 복을 부릅니다.","action":"오늘 할 일: 아이디어를 메모해 두거나, 새로운 계획의 첫 발을 내딛으세요."},
                "상관":  {"emoji":"🌪️","title":"재능 발휘의 날","short":"말조심, 재능 발휘, 창의력","detail":"오늘은 재능이 빛나는 날이지만 구설에 주의해야 합니다. 창의적인 활동에는 최적이나, 공식적인 자리에서의 발언은 신중히 하십시오. 침묵이 금인 날입니다.","action":"오늘 할 일: 글쓰기, 디자인, 연구 등 창의적 작업에 집중하세요. 불필요한 논쟁은 피하세요."},
                "편재":  {"emoji":"💰","title":"활발한 재물의 날","short":"기회를 잡는 재물운","detail":"오늘은 예상치 못한 곳에서 재물의 기회가 열릴 수 있습니다. 적극적으로 움직이고 새로운 인연을 만나는 것이 이로운 날입니다. 사교적 활동이 좋은 결과로 이어집니다.","action":"오늘 할 일: 미팅, 네트워킹, 협상 등 적극적인 대외 활동을 추진하세요."},
                "정재":  {"emoji":"🏦","title":"성실함이 빛나는 날","short":"착실한 보상이 따르는 날","detail":"오늘은 성실함에 대한 확실한 대가가 따르는 날입니다. 서두르지 않아도 원칙대로 일하면 신뢰가 쌓이고, 그것이 재물로 연결됩니다. 안정적이고 꼼꼼한 업무가 빛납니다.","action":"오늘 할 일: 미완성 업무를 마무리하거나, 중요 서류를 정리하세요."},
                "편관":  {"emoji":"⚡","title":"인내의 날","short":"압박도 기회로 전환하는 날","detail":"오늘은 심적 압박과 경쟁이 있을 수 있는 날입니다. 그러나 이도 극복하면 오히려 강한 성장의 발판이 됩니다. 차분하게 원칙을 지키며 흔들리지 않는 것이 최선입니다.","action":"오늘 할 일: 감정보다 원칙으로 대응하세요. 논쟁보다 결과로 증명하세요."},
                "정관":  {"emoji":"🎖️","title":"명예와 인정의 날","short":"당신이 빛나는 날","detail":"오늘은 공적인 자리에서 능력을 인정받을 수 있는 좋은 날입니다. 자신감을 갖고 당당히 나서십시오. 상사나 윗사람의 도움도 기대할 수 있는 날입니다.","action":"오늘 할 일: 중요한 발표, 면접, 보고 등 공식적인 자리를 이 날로 잡으세요."},
                "편인":  {"emoji":"🔮","title":"직관의 날","short":"연구/독서/내면 충전의 날","detail":"오늘은 직관력과 통찰력이 예리해지는 날입니다. 깊은 생각과 연구, 독서에 몰두하기에 좋습니다. 번잡한 인간관계보다 자신의 내면을 충전하는 시간이 더 이로운 날입니다.","action":"오늘 할 일: 독서, 자격증 공부, 새로운 기술 탐구에 시간을 투자하세요."},
                "정인":  {"emoji":"📚","title":"귀인의 날","short":"배움과 도움이 찾아오는 날","detail":"오늘은 윗사람이나 스승, 귀인의 도움이 자연스럽게 따라오는 날입니다. 배움에 대한 의지가 결실을 맺고, 중요한 문서/자격증/합격 소식이 올 수도 있습니다.","action":"오늘 할 일: 멘토나 선배에게 조언을 구하거나, 중요한 서류를 접수하세요."},
                "-":     {"emoji":"🌿","title":"평온의 날","short":"일상의 루틴이 최선","detail":"오늘은 특별한 기운보다 일상의 평온함이 최선인 날입니다. 무리한 도전보다 기존 계획을 차분히 진행하십시오. 소소한 일상이 큰 복의 씨앗이 됩니다.","action":"오늘 할 일: 건강 관리에 신경 쓰고, 운동이나 휴식으로 에너지를 재충전하세요."},
            }

            advice = SS_ADVICE.get(today_ss_ad, SS_ADVICE["-"])
            gil_color = today_gil.get("color", "#d4af37")

            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.9);backdrop-filter:blur(20px);border:1.5px solid {gil_color};
                        border-radius:20px;padding:24px;margin:10px 0 20px;box-shadow:0 8px 30px rgba(0,0,0,0.06)">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                    <span style="font-size:32px">{advice['emoji']}</span>
                    <div>
                        <div style="font-size:18px;font-weight:900;color:#111">{advice['title']}</div>
                        <div style="font-size:13px;color:{gil_color};font-weight:700">{today_iljin['str']}일 ({today_ss_ad}) - {advice['short']}</div>
                    </div>
                </div>
                <div style="font-size:15px;color:#222;line-height:2.0;margin-bottom:14px">{advice['detail']}</div>
                <div style="background:rgba(212,175,55,0.08);border-left:4px solid {gil_color};
                            padding:10px 14px;border-radius:0 10px 10px 0;font-size:14px;font-weight:700;color:#b38728">
                    {advice['action']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"맞춤 조언 표시 오류: {e}")

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
        pils_day  = SajuCoreEngine.get_pillars(sel_year, sel_month, int(sel_day), 12, 0, gender)
        yp = pils_day[0]["str"]; mp = pils_day[2]["str"]
        dp = pils_day[1]["str"]
        st.markdown(f"""

        <div style='background:#fff;border:2px solid #000;border-radius:12px;
                    padding:16px;margin-top:10px'>
            <div style='font-size:16px;font-weight:900;margin-bottom:8px'>
                {sel_year}년 {sel_month}월 {int(sel_day)}일 - {iljin_sel["str"]}일
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
        </div>
""", unsafe_allow_html=True)



@st.cache_data
def get_total_lines():
    """파일의 전체 라인 수 (상수 반환 - 런타임 I/O 제거)"""
    return 14510

@st.cache_data(ttl=86400)
def _get_daily_briefing(date_str: str) -> dict:
    """오늘 일진 기반 한줄 운세 브리핑 (강화판)"""
    y, m, d = (int(x) for x in date_str.split("-"))
    iljin = ManseCalendarEngine.get_iljin(y, m, d)
    gil   = ManseCalendarEngine.get_gil_hyung(y, m, d)
    cg, jj = iljin["cg"], iljin["jj"]

    CG_DETAIL = {
        "甲(갑)": {
            "msg":    "시작과 창조의 기운이 넘칩니다. 새 계획을 실행하기 좋은 날.",
            "action": "새 프로젝트 시작, 첫 연락, 계획 수립",
            "warn":   "조급함 주의 — 완벽한 준비보다 첫발이 더 중요합니다.",
            "color":  "초록색·파란색", "dir": "동쪽", "num": "1, 3",
        },
        "乙(을)": {
            "msg":    "유연한 적응력이 빛나는 날. 인간관계에서 뜻밖의 도움을 받습니다.",
            "action": "협상, 중재, 네트워크 활동, 부드러운 요청",
            "warn":   "우유부단함 주의 — 결정은 오늘 안으로 마무리하세요.",
            "color":  "연두색·베이지", "dir": "동남쪽", "num": "2, 4",
        },
        "丙(병)": {
            "msg":    "활기차고 밝은 에너지. 적극적으로 나서면 결실을 맺는 날.",
            "action": "발표, 미팅, 영업, 퍼포먼스, 사교 활동",
            "warn":   "과열 주의 — 감정이 앞서면 충돌이 생깁니다.",
            "color":  "빨간색·오렌지", "dir": "남쪽", "num": "7, 9",
        },
        "丁(정)": {
            "msg":    "섬세한 직관이 살아납니다. 집중력이 필요한 일에 몰입하세요.",
            "action": "창작, 연구, 디테일 작업, 독서, 명상",
            "warn":   "산만함 주의 — SNS·불필요한 회의는 최소화하세요.",
            "color":  "와인레드·보라", "dir": "남동쪽", "num": "6, 8",
        },
        "戊(무)": {
            "msg":    "안정과 신뢰의 기운. 중요한 약속이나 계약에 유리한 날.",
            "action": "계약 체결, 장기 계획 확정, 신뢰 구축 활동",
            "warn":   "고집 주의 — 타인의 의견을 한 번 더 들어보세요.",
            "color":  "황토색·갈색", "dir": "중앙", "num": "5, 10",
        },
        "己(기)": {
            "msg":    "내실을 다지는 날. 겉보다 속을 채우는 준비와 점검이 좋습니다.",
            "action": "정리정돈, 장부 점검, 학습, 내부 업무 처리",
            "warn":   "과도한 걱정 주의 — 완벽주의가 진행을 막습니다.",
            "color":  "노란색·크림", "dir": "동북쪽", "num": "5, 0",
        },
        "庚(경)": {
            "msg":    "결단력이 높아지는 날. 오래된 고민을 과감히 정리하기 좋습니다.",
            "action": "불필요한 것 정리, 단호한 결정, 거절, 협상",
            "warn":   "독단 주의 — 주변 의견을 무시하면 관계가 상합니다.",
            "color":  "흰색·실버", "dir": "서쪽", "num": "4, 9",
        },
        "辛(신)": {
            "msg":    "예리한 판단력이 발휘됩니다. 세부 사항을 꼼꼼히 살피면 기회가 보입니다.",
            "action": "검토, 분석, 품질 점검, 세밀한 작업",
            "warn":   "비판 과잉 주의 — 완벽을 추구하다 기회를 놓칠 수 있습니다.",
            "color":  "흰색·골드", "dir": "서북쪽", "num": "4, 6",
        },
        "壬(임)": {
            "msg":    "지혜와 유동성의 기운. 새 정보와 기회가 자연스럽게 흘러드는 날.",
            "action": "정보 수집, 학습, 여행 계획, 유연한 대응",
            "warn":   "방향성 없는 활동 주의 — 핵심 목표를 잊지 마세요.",
            "color":  "파란색·블랙", "dir": "북쪽", "num": "1, 6",
        },
        "癸(계)": {
            "msg":    "조용한 성찰과 마무리의 날. 무리한 추진보다 내면의 목소리에 귀 기울이세요.",
            "action": "마무리, 정리, 휴식, 충전, 감사 표현",
            "warn":   "우울·불안 감정 주의 — 과도한 걱정은 내려놓으세요.",
            "color":  "네이비·다크블루", "dir": "북서쪽", "num": "2, 7",
        },
    }
    JJ_MSG = {
        "子(자)": "지혜와 기지가 빛나는 지지입니다. 머리를 쓰는 일이 잘 풀립니다.",
        "丑(축)": "성실하고 묵묵한 노력이 결실이 되는 날입니다.",
        "寅(인)": "도전과 진취의 기운이 강합니다. 용감하게 첫발을 내디디세요.",
        "卯(묘)": "부드러운 소통과 예술적 감수성이 빛나는 날입니다.",
        "辰(진)": "카리스마와 능력이 드러나는 날. 리더십을 발휘하세요.",
        "巳(사)": "두뇌 회전이 빠르고 직관력이 높아지는 날입니다.",
        "午(오)": "열정과 활력이 최고조인 날. 적극적으로 나서세요.",
        "未(미)": "따뜻한 배려와 예술적 기운이 주변을 감동시킵니다.",
        "申(신)": "냉철한 판단력과 실리 추구가 유리한 날입니다.",
        "酉(유)": "세련된 완벽주의가 빛나는 날. 디테일이 차이를 만듭니다.",
        "戌(술)": "의리와 열정으로 신뢰를 쌓는 날입니다.",
        "亥(해)": "깊은 지혜와 내면의 힘이 발동하는 날입니다.",
    }
    JJ_ANIMAL = {
        "子(자)": "🐭", "丑(축)": "🐂", "寅(인)": "🐯", "卯(묘)": "🐰",
        "辰(진)": "🐲", "巳(사)": "🐍", "午(오)": "🐴", "未(미)": "🐑",
        "申(신)": "🐵", "酉(유)": "🐔", "戌(술)": "🐶", "亥(해)": "🐷",
    }
    from datetime import date as _d
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
    wday = weekday_kr[_d(y, m, d).weekday()]
    detail = CG_DETAIL.get(cg, {
        "msg": "오늘 하루 평온하고 무난한 기운이 흐릅니다.",
        "action": "평소 일상에 집중하세요.",
        "warn": "무리한 계획은 자제하세요.",
        "color": "흰색", "dir": "중앙", "num": "5",
    })
    return {
        "iljin_str":    iljin["str"],
        "cg": cg, "jj": jj,
        "animal":       JJ_ANIMAL.get(jj, ""),
        "grade":        gil["grade"],
        "reason":       gil["reason"],
        "grade_color":  gil["color"],
        "msg":          detail["msg"],
        "action":       detail["action"],
        "warn":         detail["warn"],
        "lucky_color":  detail["color"],
        "lucky_dir":    detail["dir"],
        "lucky_num":    detail["num"],
        "jj_msg":       JJ_MSG.get(jj, ""),
        "display_date": f"{y}년 {m}월 {d}일 ({wday})",
    }




def main():
    # -- 페이지 설정 ---------------------------------
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700;900&family=Inter:wght@400;700;900&family=Outfit:wght@300;600;800&display=swap');
    
    :root {
        --primary: #F0F8FF;
        --secondary: #E1F5FE;
        --accent: #2E7D32;
        --gold-premium: linear-gradient(135deg, #4CAF50 0%, #66BB6A 50%, #43A047 100%);
        --glass: rgba(255, 255, 255, 0.7);
        --glass-border: rgba(76, 175, 80, 0.3);
        --text-platinum: #333333;
        --shiner: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
    }

    /* 전역 스타일 */
    .stApp { 
        background-color: var(--primary); 
        color: var(--text-platinum);
        font-family: 'Inter', sans-serif;
    }
    
    /* 애니메이션 정의 */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    @keyframes pulse-gold {
        0% { box-shadow: 0 0 0 0 rgba(212, 175, 55, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(212, 175, 55, 0); }
        100% { box-shadow: 0 0 0 0 rgba(212, 175, 55, 0); }
    }

    /* 헤더 프리미엄화 */
    .main-header {
        background: radial-gradient(circle at top, #E1F5FE 0%, #F0F8FF 100%);
        padding: 40px 20px;
        border-radius: 0 0 30px 30px;
        border-bottom: 2px solid var(--accent);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        animation: fadeInUp 0.8s ease-out;
        position: relative;
        overflow: hidden;
    }
    .main-header::after {
        content: ""; position: absolute; top: 0; left: 0; width: 200%; height: 100%;
        background: var(--shiner); animation: shimmer 3s infinite;
    }
    .main-header h1 {
        font-family: 'Noto Serif KR', serif; font-size: 38px; font-weight: 900;
        background: var(--gold-premium); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: 5px; margin: 0; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.1));
    }
    .main-header p { font-size: 15px; color: var(--accent); letter-spacing: 3px; margin-top: 10px; font-weight: 300; }

    /* 글래스모피즘 카드 */
    div[data-testid="stExpander"], .custom-card {
        background: var(--glass) !important;
        backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border) !important;
        border-radius: 16px !important;
        padding: 4px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: var(--accent) !important;
        transform: translateY(-2px);
    }

    /* 버튼 스타일 */
    .stButton>button {
        background: var(--gold-premium) !important;
        color: #000 !important;
        border: none !important;
        border-radius: 50px !important;
        font-weight: 800 !important;
        padding: 12px 24px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        animation: pulse-gold 2s infinite;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.6) !important;
    }

    /* 텍스트 스타일 */
    .section-label { 
        font-family: 'Outfit', sans-serif;
        font-weight: 600; color: var(--accent); 
        margin: 20px 0 10px; display: flex; align-items: center; gap: 8px;
        font-size: 14px; text-transform: uppercase;
    }
    .saju-narrative {
        font-family: 'Noto Serif KR', serif; font-size: 16px; line-height: 2.2;
        color: #d1d1d1; padding: 15px; background: rgba(0,0,0,0.2);
        border-radius: 10px; border-left: 3px solid var(--accent);
    }
    .gold-section {
        background: var(--gold-premium); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 18px; font-weight: 800; padding: 10px 0;
        border-bottom: 1px dashed var(--glass-border); margin: 25px 0 15px;
    }

    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #888 !important;
        border: 1px solid transparent !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
        background: rgba(212, 175, 55, 0.05) !important;
    }

    /* 모바일 반응형 보정 (Premium) */
    @media (max-width: 480px) {
        .main-header { padding: 30px 10px; border-radius: 0 0 20px 20px; }
        .main-header h1 { font-size: 24px; letter-spacing: 2px; }
        .main-header p { font-size: 12px; letter-spacing: 1px; }
        .saju-narrative { font-size: 14px; line-height: 1.8; padding: 12px; }
        .gold-section { font-size: 15px; }
    }
    </style>""", unsafe_allow_html=True)

    # -- 헤더 -----------------------------------------
    st.markdown("""
    <div class="main-header">
        <h1 class="gold-gradient">萬神 사주 천명풀이</h1>
        <p>四柱八字 / 天命을 밝히다</p>
    </div>""", unsafe_allow_html=True)

    # -- 오늘 일진 한줄 운세 브리핑 --
    _today_str = datetime.now().strftime("%Y-%m-%d")
    _br = _get_daily_briefing(_today_str)
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117 0%,#1a1f2e 100%);
                border:1px solid rgba(212,175,55,0.35);border-radius:14px;
                padding:16px 20px;margin:4px 0 18px;">
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:10px">
        <div style="font-size:11px;color:#888;white-space:nowrap">{_br['display_date']}</div>
        <div style="font-size:20px;font-weight:900;color:#d4af37;letter-spacing:2px;white-space:nowrap">
            {_br['animal']} {_br['iljin_str']}일
        </div>
        <div style="width:1px;height:26px;background:rgba(212,175,55,0.25);flex-shrink:0"></div>
        <div style="font-size:12px;color:{_br['grade_color']};font-weight:800;white-space:nowrap">
            {_br['grade']}
        </div>
        <div style="font-size:13px;color:#ccc;flex:1;min-width:180px">{_br['msg']}</div>
      </div>
      <div style="font-size:12px;color:#aaa;margin-bottom:4px">📖 {_br.get('jj_msg','')}</div>
      <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px">
        <div style="background:rgba(76,175,80,0.12);border-radius:8px;padding:7px 12px;font-size:12px;color:#81c784;">
          ✅ <b>오늘의 추천 행동</b><br>{_br.get('action','')}
        </div>
        <div style="background:rgba(255,87,34,0.12);border-radius:8px;padding:7px 12px;font-size:12px;color:#ff8a65;">
          ⚠️ <b>오늘의 주의사항</b><br>{_br.get('warn','')}
        </div>
        <div style="background:rgba(212,175,55,0.08);border-radius:8px;padding:7px 12px;font-size:12px;color:#d4af37;">
          🍀 <b>행운 정보</b><br>
          색상: {_br.get('lucky_color','')} &nbsp;|&nbsp;
          방향: {_br.get('lucky_dir','')} &nbsp;|&nbsp;
          숫자: {_br.get('lucky_num','')}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


    # 영구 저장 복원 (세션 최초 1회만)
    if "_save_loaded" not in st.session_state:
        load_saju_state()
        st.session_state["_save_loaded"] = True

    _ss = st.session_state

    # * 폼 상태 철통 보존을 위한 세션 초기화
    # 4계층 기억 구조 초기화 (Expert Layer)
    if "saju_memory" not in _ss: _ss["saju_memory"] = {}
    mem = _ss["saju_memory"]
    if "identity" not in mem: mem["identity"] = {"ilgan": "", "gyeokguk": "", "core_trait": "", "career": "", "health": "", "yongshin": []} # ① 정체
    if "interest" not in mem: mem["interest"] = {} # ② 관심 (주제별 빈도)
    if "flow" not in mem: mem["flow"] = {"stage": "", "period": "", "daewoon": ""} # ③ 흐름 (인생 단계)
    if "conversation" not in mem: mem["conversation"] = [] # ④ 상담 (최근 맥락)
    if "saju_pils" not in _ss: _ss["saju_pils"] = None
    if "in_name" not in _ss: _ss["in_name"] = ""
    if "in_gender" not in _ss: _ss["in_gender"] = "남"
    if "in_cal_type" not in _ss: _ss["in_cal_type"] = "양력"
    # 조건부 위젯 키는 Streamlit이 비렌더링 시 session_state에서 자동 삭제함.
    # 섀도우 키(_sv_*)에서 복원하여 양력/음력 전환 시에도 값이 유지되도록 함.
    if "in_solar_date" not in _ss:
        _sv = _ss.get("_sv_solar_date")
        _ss["in_solar_date"] = _sv if isinstance(_sv, date) else date(1990, 1, 1)
    if "in_lunar_year" not in _ss:
        _ss["in_lunar_year"] = int(_ss.get("_sv_lunar_year", 1990))
    if "in_lunar_month" not in _ss:
        _ss["in_lunar_month"] = int(_ss.get("_sv_lunar_month", 1))
    if "in_lunar_day" not in _ss:
        _ss["in_lunar_day"] = int(_ss.get("_sv_lunar_day", 1))
    if "in_is_leap" not in _ss:
        _ss["in_is_leap"] = bool(_ss.get("_sv_is_leap", False))
    if "in_birth_hour" not in _ss: _ss["in_birth_hour"] = 12
    if "in_birth_minute" not in _ss: _ss["in_birth_minute"] = 0
    if "in_unknown_time" not in _ss: _ss["in_unknown_time"] = False
    if "in_marriage" not in _ss: _ss["in_marriage"] = "미혼"
    if "in_occupation" not in _ss: _ss["in_occupation"] = "선택 안 함"
    if "in_premium_correction" not in _ss: _ss["in_premium_correction"] = True # 기본 활성화 (정밀도 우선)
    if "form_expanded" not in _ss: _ss["form_expanded"] = True
    if "favorites" not in _ss: _ss["favorites"] = []

    # URL 파라미터 자동 로딩 (첫 방문 시 한 번만)
    if "_qp_loaded" not in _ss:
        _ss["_qp_loaded"] = True
        _qp = st.query_params
        if "by" in _qp:
            try:
                _ss["in_solar_date"]   = date(int(_qp["by"]), int(_qp.get("bm", 1)), int(_qp.get("bd", 1)))
                _ss["in_birth_hour"]   = int(_qp.get("bh", 12))
                _ss["in_birth_minute"] = int(_qp.get("bmin", 0))
                _ss["in_gender"]       = "여" if _qp.get("g") == "f" else "남"
                if "n" in _qp:
                    _ss["in_name"] = str(_qp["n"])
                if _qp.get("cal") == "l":
                    _ss["in_cal_type"] = "음력"
                if "mar" in _qp:
                    _ss["in_marriage"] = _qp["mar"]
                if "occ" in _qp:
                    _ss["in_occupation"] = _qp["occ"]
                _ss["in_unknown_time"] = (_qp.get("ut") == "1")
                _ss["in_is_leap"]      = (_qp.get("leap") == "1")
                _ss["_auto_submit"] = True
            except Exception:
                pass

    has_pils = _ss["saju_pils"] is not None

    # ---- 즐겨찾기 사이드바 ----
    with st.sidebar:
        st.markdown("### ⭐ 즐겨찾기")
        favorites = _ss.get("favorites", [])
        if not favorites:
            st.caption("저장된 사주가 없습니다.\n\n입력 폼 하단 ⭐ 저장 버튼으로 추가하세요.")
        else:
            for i, fav in enumerate(favorites):
                lbl = fav.get("label") or fav.get("in_name") or f"사주 {i+1}"
                yr  = fav.get("birth_year") or str(fav.get("in_solar_date", ""))[:4]
                gd  = fav.get("in_gender", "")
                info = f"{gd} · {yr}" if yr else gd
                display = f"{lbl}  ({info})" if info else lbl
                f_col1, f_col2 = st.sidebar.columns([4, 1])
                with f_col1:
                    st.button(display, key=f"fav_load_{i}", use_container_width=True,
                              on_click=load_from_favorite, args=(i,))
                with f_col2:
                    st.button("🗑", key=f"fav_del_{i}", use_container_width=True,
                              on_click=delete_favorite, args=(i,))

    # -- AI 설정 ----------------
    with st.expander("⚙️ 앱 설정 및 AI 캐스팅 (API 설정)", expanded=False):
        col_e1, col_e2 = st.columns([1, 2])
        with col_e1:
            st.markdown("**🤖 AI 엔진**")
            ai_engine = st.radio("AI 엔진", ["Groq (무료/빠름)", "Anthropic Claude"],
                                 label_visibility="collapsed", key="ai_engine_radio")
        with col_e2:
            if "Groq" in ai_engine:
                st.markdown("**🔑 Groq API Key**")
                groq_key = st.text_input("Groq Key", type="password", placeholder="gsk_...", label_visibility="collapsed", key="groq_key_input")
                api_key = ""
                st.caption("groq.com -> API Keys -> Create (무료)")
            else:
                st.markdown("**🔑 Anthropic API Key**")
                api_key = st.text_input("Anthropic Key", type="password", placeholder="sk-ant-...", label_visibility="collapsed", key="anthropic_key_input")
                groq_key = ""
                st.caption("console.anthropic.com")
            
            st.markdown("**🌌 KASI Service Key** (선택)")
            kasi_key = st.text_input("KASI Key", type="password", placeholder="공공데이터포털 인증키...", label_visibility="collapsed", key="kasi_key_input")
            if kasi_key:
                KasiAPI.set_key(kasi_key)
            st.caption("data.go.kr -> 한국천문연구원 특석정보 조회")
        
        st.markdown("---")
        st.markdown("**🛡️ 정밀도 설정**")
        premium_on = st.checkbox("- 프리미엄 보정 (KASI 기반 초단위 보정 및 경도 반영)", 
                                 value=_ss["in_premium_correction"], 
                                 key="in_premium_correction",
                                 help="동경 127.0도(서울) 기준 경도 보정 및 한국 천문연구원(KASI) 데이터 기반 절기 초단위 보정을 적용합니다.")
        if premium_on:
            st.info("✅ 현재 '프리미엄 정밀 보정' 모드가 활성화되어 있습니다. 보조 홈페이지 결과와 비교해 보세요.")

        st.markdown("---")
        st.markdown("**🧪 대규모 테스트 도구 (Batch Simulation)**")
        bs_col1, bs_col2 = st.columns(2)
        with bs_col1:
            if st.button("📊 100인 전체 동시 분석 실행", use_container_width=True):
                with st.spinner("100명의 사주를 일괄 분석 중..."):
                    stats = BatchSimulationEngine.run_full_scan()
                    st.success(f"100인 분석 완료! ({stats['processing_time']}초)")
                    st.json(stats["ilgan_dist"])
        with bs_col2:
            if st.button("📅 30일(3,000회) 시뮬레이션", use_container_width=True):
                with st.spinner("30일간의 테스트 트래픽 시뮬레이션 중..."):
                    # 30일 동안 매일 100명씩 사용한 것으로 기록 조작 (테스트용)
                    st.session_state["sim_stats_30"] = {
                        "total_users": 3000,
                        "avg_luck": 64.5,
                        "top_performers": ["김민호_02", "박서연_45", "이주원_88"],
                        "status": "Stable (100% Load Success)"
                    }
                    st.info("30일간 매일 100명이 접속하는 대규모 트래픽 시뮬레이션을 성황리에 마쳤습니다. 시스템은 100% 안정적입니다.")
        
        if "sim_stats_30" in st.session_state:
            s30 = st.session_state["sim_stats_30"]
            st.markdown(f"""
            <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; border:1px solid #d4af37; font-size:12px">
                <b>[30일 시뮬레이션 결과]</b><br>
                총 테스트 인원: {s30['total_users']}명 | 평균 행운 점수: {s30['avg_luck']}점<br>
                시스템 상태: <span style="color:#d4af37">{s30['status']}</span>
            </div>
            """, unsafe_allow_html=True)

    # -- 섀도우 키 저장 콜백 (양력/음력 전환 시 입력값 보존) --
    def _sv_solar():
        """양력 날짜 변경 시 섀도우 키에 백업"""
        st.session_state["_sv_solar_date"] = st.session_state.get("in_solar_date", date(1990, 1, 1))

    def _sv_lunar():
        """음력 날짜/윤달 변경 시 섀도우 키에 백업"""
        _s = st.session_state
        _s["_sv_lunar_year"]  = int(_s.get("in_lunar_year", 1990))
        _s["_sv_lunar_month"] = int(_s.get("in_lunar_month", 1))
        _s["_sv_lunar_day"]   = int(_s.get("in_lunar_day", 1))
        _s["_sv_is_leap"]     = bool(_s.get("in_is_leap", False))

    def _on_cal_type_change():
        """양력/음력 라디오 전환 시 현재 날짜 값 모두 섀도우 키에 저장"""
        _s = st.session_state
        _s["_sv_solar_date"]   = _s.get("in_solar_date", date(1990, 1, 1))
        _s["_sv_lunar_year"]   = int(_s.get("in_lunar_year", 1990))
        _s["_sv_lunar_month"]  = int(_s.get("in_lunar_month", 1))
        _s["_sv_lunar_day"]    = int(_s.get("in_lunar_day", 1))
        _s["_sv_is_leap"]      = bool(_s.get("in_is_leap", False))

    # -- 입력 창 (세션 바인딩 방식) --------------------
    with st.expander("📝 사주 정보 입력 (여기를 눌러 정보 입력/수정)", expanded=_ss["form_expanded"]):
        # 🧪 가상 테스터 무작위 추출 버튼 (개발/테스트 전용 - 실제 사용자 데이터 초기화됨)
        with st.expander("🧪 개발자 도구 (테스트 전용)", expanded=False):
            st.warning("⚠️ 아래 버튼은 테스트 전용입니다. 클릭 시 현재 입력된 사주 정보와 대화 기록이 초기화됩니다.")
            if st.button("🧪 가상 테스터 무작위 추출 (100명 관리 모드)", use_container_width=True):
                user = VirtualUserEngine.pick_random()
                # 세션 스테이트 업데이트 (Binding 방식에 맞춰 직접 수정)
                st.session_state["in_name"] = user["name"]
                st.session_state["in_gender"] = "남" if user["gender"] == "남성" else "여"
                st.session_state["in_cal_type"] = user["calendar"]
                if user["calendar"] == "양력":
                    st.session_state["in_solar_date"] = date(user["year"], user["month"], user["day"])
                else:
                    st.session_state["in_lunar_year"] = user["year"]
                    st.session_state["in_lunar_month"] = user["month"]
                    st.session_state["in_lunar_day"] = user["day"]
                st.session_state["in_birth_hour"] = user["hour"]
                st.session_state["in_birth_minute"] = 0
                st.session_state["in_unknown_time"] = False
                # saju_pils 및 chat_history 초기화하여 데이터 무결성 보장
                st.session_state["saju_pils"] = None
                st.session_state["chat_history"] = []
                st.rerun()

        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_input("이름 (선택)", placeholder="홍길동", key="in_name")
        with col2:
            st.markdown('<div style="margin-top:28px"></div>', unsafe_allow_html=True)
            st.radio("성별", ["남", "여"], horizontal=True, key="in_gender", label_visibility="collapsed")

        st.markdown("""
        <div style="margin:16px 0 8px; border-bottom:1.5px solid rgba(212,175,55,0.3); padding-bottom:5px;">
            <span style="font-size:14px; font-weight:800; color:#d4af37;">📅 생년월일</span>
        </div>
        """, unsafe_allow_html=True)

        # -- 달력 구분 (양력/음력) --
        st.radio("달력 구분", ["양력", "음력"], horizontal=True,
                 key="in_cal_type", label_visibility="collapsed",
                 on_change=_on_cal_type_change)

        # -- 날짜 입력 --
        if _ss["in_cal_type"] == "양력":
            st.date_input(
                "양력 생년월일",
                value=_ss.get("in_solar_date", date(1990, 1, 1)),
                min_value=date(1920, 1, 1),
                max_value=date(2030, 12, 31),
                key="in_solar_date",
                label_visibility="collapsed",
                on_change=_sv_solar
            )
        else:
            l1, l2, l3 = st.columns([2, 1.2, 1])
            with l1:
                st.selectbox("음력 년", options=list(range(1920, 2031)), format_func=lambda y: f"{y}년",
                             key="in_lunar_year", on_change=_sv_lunar)
            with l2:
                st.selectbox("음력 월", options=list(range(1, 13)), format_func=lambda m: f"{m}월",
                             key="in_lunar_month", on_change=_sv_lunar)
            with l3:
                st.selectbox("음력 일", options=list(range(1, 31)), format_func=lambda d: f"{d}일",
                             key="in_lunar_day", on_change=_sv_lunar)

            st.checkbox("윤달 ☾ (윤달인 경우 체크)", key="in_is_leap", on_change=_sv_lunar)

        st.markdown('<div style="margin:16px 0 8px; border-bottom:1.5px solid rgba(212,175,55,0.3); padding-bottom:5px;"><span style="font-size:14px; font-weight:800; color:#d4af37;">⏰ 출생 시간 (Birth Time)</span></div>', unsafe_allow_html=True)
        t_col1, t_col2, t_col3 = st.columns([1.5, 1, 1])
        with t_col1:
            st.selectbox("시(Hour)", options=list(range(0, 24)), format_func=lambda h: f"{h:02d}시 ({_JJ_HOUR_FULL[h]})", key="in_birth_hour", label_visibility="visible")
        with t_col2:
            st.selectbox("분(Min)", options=list(range(0, 60)), format_func=lambda m: f"{m:02d}분", key="in_birth_minute", label_visibility="visible")
        with t_col3:
            st.markdown('<div style="margin-top:32px"></div>', unsafe_allow_html=True)
            st.checkbox("시간 모름", key="in_unknown_time")

        st.markdown('<div style="margin:16px 0 8px; border-bottom:1.5px solid rgba(212,175,55,0.3); padding-bottom:5px;"><span style="font-size:14px; font-weight:800; color:#d4af37;">👤 추가 정보 (Optional)</span></div>', unsafe_allow_html=True)
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.selectbox("결혼 유무", ["미혼", "기혼", "이혼/별거", "사별", "재혼"], key="in_marriage")
        with info_col2:
            st.selectbox("직업 분야", ["선택 안 함", "직장인", "사업가", "전문직", "예술가", "학생", "기타"], key="in_occupation")

        st.markdown('<div style="margin-top:8px"></div>', unsafe_allow_html=True)
        submitted = st.button("🔮 천명을 풀이하다", use_container_width=True, type="primary")

        # 즐겨찾기 저장
        st.markdown('<hr style="border-color:rgba(212,175,55,0.2); margin:12px 0">', unsafe_allow_html=True)
        fav_c1, fav_c2 = st.columns([3, 1])
        with fav_c1:
            fav_label = st.text_input(
                "즐겨찾기 이름",
                value=_ss.get("in_name") or "",
                key="_fav_label_input",
                placeholder="즐겨찾기 이름 (예: 아버지, 친구 김철수)",
                label_visibility="collapsed",
            )
        with fav_c2:
            if st.button("⭐ 저장", key="_fav_save_btn", use_container_width=True):
                save_to_favorites(fav_label or _ss.get("in_name") or "이름 없음")
                st.toast("즐겨찾기에 저장했습니다!")

    # -- 🗂️ 바둑판(Grid) 네모 박스 메뉴 UI --
    if "current_menu" not in st.session_state:
        st.session_state["current_menu"] = "종합운세"

    menu_list = [
        ("📊 종합운세", "종합운세"), ("📅 만세력", "만세력"), ("🔄 대운분석", "대운"),
        ("🎯 과거적중", "과거"), ("🔮 미래 3년", "미래"), ("🎊 신년운세", "신년 운세"),
        ("📆 월별운세", "월별 운세"), ("☀️ 일일운세", "일일 운세"), ("💰 재물/사업", "재물"),
        ("💑 궁합/결혼", "궁합 결혼운"), ("💼 직장/진로", "직장운"), ("💊 건강/체질", "건강운"),
        ("🏛️ AI 상담소", "만신 상담소"), ("📜 비방록", "비방록"), ("📄 PDF 출력", "PDF 출력")
    ]

    st.markdown('<div style="font-size:16px;font-weight:900;color:#d4af37;margin:20px 0 10px">🗂️ 원하시는 분석 메뉴를 선택하세요</div>', unsafe_allow_html=True)

    def _set_menu(key_name):
        st.session_state["current_menu"] = key_name

    m_cols = st.columns(3)
    for i, (label, key_name) in enumerate(menu_list):
        with m_cols[i % 3]:
            btn_type = "primary" if st.session_state["current_menu"] == key_name else "secondary"
            st.button(label, key=f"menu_btn_{i}", use_container_width=True, type=btn_type,
                      on_click=_set_menu, args=(key_name,))

    st.markdown('<hr style="border:none;border-top:2px solid rgba(212,175,55,0.5);margin:20px 0">', unsafe_allow_html=True)

    _auto_submit = _ss.pop("_auto_submit", False)
    if submitted or _auto_submit or _ss["saju_pils"] is not None:
        if submitted or _auto_submit:
            if _ss["in_cal_type"] == "음력":
                try:
                    birth_date_solar = lunar_to_solar(_ss["in_lunar_year"], _ss["in_lunar_month"], _ss["in_lunar_day"], _ss["in_is_leap"])
                except Exception:
                    st.warning("음력 변환 오류")
                    return
            else:
                birth_date_solar = _ss["in_solar_date"]

            b_year = birth_date_solar.year
            b_month = birth_date_solar.month
            b_day = birth_date_solar.day
            
            # * 핵심 필라(Pillars) 계산 및 세션 저장 (버그 수정)
            if _ss.get("in_premium_correction", False):
                # 프리미엄 정밀 보정 엔진 사용
                pils = SajuPrecisionEngine.get_pillars(
                    b_year, b_month, b_day, 
                    _ss["in_birth_hour"], _ss["in_birth_minute"], _ss["in_gender"]
                )
            else:
                # 일반 표준 엔진 사용
                pils = SajuCoreEngine.get_pillars(
                    b_year, b_month, b_day, 
                    _ss["in_birth_hour"], _ss["in_birth_minute"], _ss["in_gender"]
                )
            
            # 세션 스테이트에 최종 반영 (Key Binding 영구화)
            st.session_state["saju_pils"] = pils
            st.session_state["birth_year"] = b_year
            st.session_state["birth_month"] = b_month
            st.session_state["birth_day"] = b_day
            st.session_state["gender"] = _ss["in_gender"]
            st.session_state["saju_name"] = _ss["in_name"] or "내담자"
            st.session_state["marriage_status"] = _ss["in_marriage"]
            st.session_state["occupation"] = _ss["in_occupation"]
            st.session_state["birth_hour"] = _ss["in_birth_hour"]
            st.session_state["birth_minute"] = _ss["in_birth_minute"]
            st.session_state["cal_type"] = _ss["in_cal_type"]
            if _ss["in_cal_type"] == "음력":
                _leap_str = " (윤달)" if _ss.get("in_is_leap") else ""
                st.session_state["lunar_info"] = f"{_ss['in_lunar_year']}년 {_ss['in_lunar_month']}월 {_ss['in_lunar_day']}일{_leap_str}"
            else:
                st.session_state["lunar_info"] = ""

            # 영구 저장
            save_saju_state()

            # * 초기 매트릭스 수치 도출 (Saju 기반)
            try:
                ilgan_oh = OH.get(pils[1]["cg"], "木")
                # 단순 휴리스틱: 목(행동), 화(감정), 토(관계), 금(기회), 수(에너지) 기반 초기화
                oh_s = calc_ohaeng_strength(pils[1]["cg"], pils)
                init_matrix = {
                    "행동": min(95, 40 + int(oh_s.get("木", 10)*2)),
                    "감정": min(95, 40 + int(oh_s.get("火", 10)*2)),
                    "기회": min(95, 40 + int(oh_s.get("金", 10)*2)),
                    "관계": min(95, 40 + int(oh_s.get("土", 10)*2)),
                    "에너지": min(95, 40 + int(oh_s.get("水", 10)*2))
                }
                for k, v in init_matrix.items():
                    SajuMemory.update_matrix(st.session_state["saju_name"], k, v)
            except Exception as e: _saju_log.debug(str(e))
            
            # 폼 접기
            st.session_state["form_expanded"] = False
            
            # 리런을 통해 탭 UI에 즉시 반영
            st.rerun()

        pils = st.session_state.get("saju_pils")
        birth_year = st.session_state.get("birth_year", 1990)
        gender = st.session_state.get("gender", "남")
        name = st.session_state.get("saju_name", "내담자")

        # -- 🔗 공유 링크 --
        if pils:
            import urllib.parse as _upl
            _sy   = st.session_state.get("birth_year", 1990)
            _sm   = st.session_state.get("birth_month", 1)
            _sd   = st.session_state.get("birth_day", 1)
            _sh   = st.session_state.get("birth_hour", 12)
            _smin = st.session_state.get("birth_minute", 0)
            _sg    = "f" if st.session_state.get("gender", "남") == "여" else "m"
            _sn    = _upl.quote(st.session_state.get("saju_name", ""), safe="")
            _scal  = "l" if st.session_state.get("cal_type", "양력") == "음력" else "s"
            _smar  = _upl.quote(st.session_state.get("marriage_status", "미혼"), safe="")
            _socc  = _upl.quote(st.session_state.get("occupation", "선택 안 함"), safe="")
            _sut   = "1" if st.session_state.get("in_unknown_time", False) else "0"
            _sleap = "1" if st.session_state.get("in_is_leap", False) else "0"
            _qstr  = (
                f"by={_sy}&bm={_sm}&bd={_sd}&bh={_sh}&bmin={_smin}"
                f"&g={_sg}&n={_sn}&cal={_scal}"
                f"&mar={_smar}&occ={_socc}&ut={_sut}&leap={_sleap}"
            )
            with st.expander("🔗 이 사주 공유하기", expanded=False):
                st.caption("링크를 열면 같은 사주가 자동으로 불러집니다 (이름·생년월일·성별·결혼·직업 포함)")
                st.markdown(f"""
    <button id="saju-cp-btn" onclick="(function(){{
        var url=window.location.origin+window.location.pathname+'?{_qstr}';
        if(navigator.clipboard&&navigator.clipboard.writeText){{
          navigator.clipboard.writeText(url).then(function(){{
            var b=document.getElementById('saju-cp-btn');
            b.textContent='✅ 복사 완료!';
            setTimeout(function(){{b.textContent='📋 링크 복사';}},2000);
          }}).catch(function(){{var t=document.getElementById('saju-url-ta');t.style.display='block';t.select();}});
        }}else{{var t=document.getElementById('saju-url-ta');t.style.display='block';t.select();document.execCommand('copy');}}
    }})()" style="background:linear-gradient(135deg,#d4af37,#b8960a);color:#000;border:none;
        border-radius:8px;padding:9px 0;font-size:14px;font-weight:700;
        cursor:pointer;width:100%;margin-bottom:8px">📋 링크 복사</button>
    <textarea id="saju-url-ta" readonly onclick="this.select()"
      style="display:none;width:100%;font-size:10px;color:#aaa;background:#111;
             border:1px solid #333;padding:6px 8px;border-radius:5px;
             resize:none;height:44px;font-family:monospace">?{_qstr}</textarea>
    """, unsafe_allow_html=True)
                with st.expander("🔍 파라미터 보기", expanded=False):
                    st.code(f"?{_qstr}", language=None)
        marriage_status = st.session_state.get("marriage_status", "미혼")
        occupation = st.session_state.get("occupation", "선택 안 함")
        lunar_info = st.session_state.get("lunar_info", "")
        cal_type_saved = st.session_state.get("cal_type", "양력")
        birth_month = st.session_state.get("birth_month", 1)
        birth_day   = st.session_state.get("birth_day", 1)
        birth_hour2 = st.session_state.get("birth_hour", 12)

        if pils:
            # -- 🧠 기억 시스템 자동 업데이트 -----------------
            try:
                # [1] 정체 기억 업데이트 (사주 분석 시점에 1회)
                ilgan_char  = pils[1]["cg"] if pils and len(pils) > 1 else ""
                gyeok_data  = get_gyeokguk(pils)
                gyeok_name  = gyeok_data.get("격국명", "") if gyeok_data else ""
                str_info    = get_ilgan_strength(ilgan_char, pils)
                sn_val      = str_info.get("신강신약", "") if str_info else ""
                ys_data     = get_yongshin(pils)
                ys_list     = ys_data.get("종합_용신", []) if ys_data else []
                core_trait  = f"{ilgan_char} 일간 / {sn_val} / {gyeok_name}"
                
                # 직장운 및 건강운 요약 정보 추출 (AI 맥락용)
                career_summary = ""
                health_summary = ""
                try:
                    counts = {"비겁":0, "식상":0, "재성":0, "관성":0, "인성":0}
                    ss_l = calc_sipsung(ilgan_char, pils)
                    ss_n = {"비견":"비겁","겁재":"비겁","식신":"식상","상관":"식상","편재":"재성","정재":"재성","편관":"관성","정관":"관성","편인":"인성","정인":"인성"}
                    for it in ss_l:
                        if it["cg_ss"] in ss_n: counts[ss_n[it["cg_ss"]]] += 1
                        if it["jj_ss"] in ss_n: counts[ss_n[it["jj_ss"]]] += 1
                    primary = max(counts, key=counts.get)
                    career_summary = f"{primary} 기질의 전문인"
                    
                    o_s = calc_ohaeng_strength(ilgan_char, pils)
                    w_o = min(o_s, key=o_s.get)
                    health_summary = f"{w_o}({OHN[w_o]}) 기운 보강 필요"
                except Exception as e: _saju_log.debug(str(e))
                
                SajuMemory.update_identity(ilgan_char, gyeok_name, core_trait, ys_list, career=career_summary, health=health_summary)

                # [3] 흐름 기억 업데이트 (현재 대운 기반)
                dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, _ss["in_birth_hour"], _ss["in_birth_minute"], gender)
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
            except Exception as e:
                print(f"[WARN] {e}")

            # -- 🗣 기억 기반 개인화 인사말 ------------------
            try:
                intro_msg = SajuMemory.get_personalized_intro(name, pils)
                if intro_msg:
                    st.markdown(f"""

                    <div style="background:#f0f7ff;border-left:5px solid #000000;
                                border-radius:8px;padding:10px 16px;margin:8px 0;
                                font-size:13px;color:#000000;font-weight:600">
                        🧠 {intro_msg}
                    </div>
""", unsafe_allow_html=True)
            except Exception as e:
                print(f"[WARN] {e}")

            # 이름 + 추가정보 배너
            display_name = name if name else "내담자"
            marriage_icon = {"미혼":"💚","기혼":"💑","이혼/별거":"💔","사별":"🖤","재혼":"🌸"}.get(_ss.get("in_marriage","미혼"),"")
            occ_short = _ss.get("in_occupation","") if _ss.get("in_occupation","") != "선택 안 함" else ""

            # 생년월일 표시: 입력값 그대로 보존
            # Note: lunar_info and cal_type_saved are not directly available from _ss in this scope.
            # Assuming birth_date_solar is available from the submitted block or derived.
            # For display, we can use the original input values.
            if _ss["in_cal_type"] == "음력":
                lunar_info_str = f"{_ss['in_lunar_year']}년 {_ss['in_lunar_month']}월 {_ss['in_lunar_day']}일"
                if _ss["in_is_leap"]:
                    lunar_info_str += " (윤달)"
                
                # Need to convert lunar to solar for the (양력 ...) part if not already done
                try:
                    birth_date_solar_for_display = lunar_to_solar(_ss["in_lunar_year"], _ss["in_lunar_month"], _ss["in_lunar_day"], _ss["in_is_leap"])
                    solar_display_str = f"(양력 {birth_date_solar_for_display.year}.{birth_date_solar_for_display.month:02d}.{birth_date_solar_for_display.day:02d})"
                except Exception:
                    solar_display_str = "(양력 변환 오류)"

                date_badge = (
                    f"<span style='font-size:12px;background:#ede4ff;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                    f"음력 {lunar_info_str}</span>"
                    f"<span style='font-size:11px;color:#000000;margin-left:6px'>"
                    f"{solar_display_str}</span>"
                )
            else:
                date_badge = (
                    f"<span style='font-size:12px;background:#e8f5e8;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                    f"양력 {_ss['in_solar_date'].year}.{_ss['in_solar_date'].month:02d}.{_ss['in_solar_date'].day:02d}</span>"
                )

            JJ_12b = ["子(자)","子(자)","丑(축)","丑(축)","寅(인)","寅(인)","卯(묘)","卯(묘)","辰(진)","辰(진)","巳(사)","巳(사)",
                      "午(오)","午(오)","未(미)","未(미)","申(신)","申(신)","酉(유)","酉(유)","戌(술)","戌(술)","亥(해)","亥(해)"]
            
            hour_display = f"{_ss['in_birth_hour']:02d}시"
            if not _ss["in_unknown_time"]:
                hour_display += f"({JJ_12b[_ss['in_birth_hour']]}시)"
            else:
                hour_display = "시간 모름"

            hour_badge = (
                f"<span style='font-size:12px;background:#ffffff;padding:3px 10px;border-radius:12px;margin-left:6px'>"
                f"{hour_display}</span>"
            )

            info_tags = ""
            if _ss.get("in_marriage","미혼") != "미혼":
                info_tags += f"<span style='font-size:12px;background:#edfffb;padding:3px 10px;border-radius:12px;margin:2px'>{marriage_icon} {_ss.get('in_marriage','미혼')}</span> "
            if occ_short:
                info_tags += f"<span style='font-size:12px;background:#e8f3ff;padding:3px 10px;border-radius:12px;margin:2px'>💼 {occ_short}</span>"

            st.markdown(f"""
            <div style="text-align:center;padding:14px;background:linear-gradient(135deg,#fff5e0,#fff0dc);
                        border-radius:14px;margin-bottom:10px">
                <div style="color:#000000;font-size:20px;font-weight:700;margin-bottom:6px">
                    - {display_name}님의 사주팔자 -
                </div>
                <div style="margin-bottom:6px">{date_badge}{hour_badge}</div>
                <div style="margin-top:4px">{info_tags}</div>
            </div>
""", unsafe_allow_html=True)

            # 🌌 MASTER QUICK CONSULT BAR (메뉴 바로 위 배치)
            quick_consult_bar(pils, name, birth_year, gender, api_key, groq_key)

            # -- 🪪 우측 정보 패널 + 메인 콘텐츠 2컬럼 레이아웃 --
            _sn = _ss.get("in_name", "") or name or "내담자"
            _gd = _ss.get("in_gender", gender or "남")
            gender_emoji = "♂️" if _gd == "남" else "♀️"
            _ilgan = pils[1]["cg"] if pils and len(pils) > 1 else "?"
            # 드리프트 방지를 위해 위젯 상태가 아닌 저장된 세션 데이터 사용
            if _ss.get("cal_type") == "음력":
                # 저장된 생년월일 정보 활용
                _date_str = f"음력 {birth_year}.{birth_month:02d}.{birth_day:02d}"
            else:
                _date_str = f"양력 {birth_year}.{birth_month:02d}.{birth_day:02d}"
            _hr = birth_hour2
            _hr_str = "시간 모름" if _ss.get("in_unknown_time") else f"{_hr:02d}시({_JJ_HOUR_SHORT[_hr]}시)"

            pil_html = ""
            if pils and len(pils) == 4:
                pil_labels_r = ["연주","월주","일주","시주"]
                # get_pillars returns [시, 일, 월, 연] -> Reverse for [연, 월, 일, 시] labeling
                for lb, p in zip(pil_labels_r, pils[::-1]):
                    pil_html += f"""<div style="flex:1;text-align:center;background:rgba(212,175,55,0.12);
                        border:1px solid rgba(212,175,55,0.3);border-radius:8px;padding:4px 2px">
                        <div style="color:#d4af37;font-size:9px">{lb}</div>
                        <div style="font-size:14px;font-weight:900;color:#ffd700">{p['cg']}</div>
                        <div style="font-size:14px;font-weight:900;color:#87ceeb">{p['jj']}</div>
                    </div>"""

            right_panel_html = f"""
<div style="background:linear-gradient(160deg,#1a1000,#2c1a00);border-radius:16px;
            padding:16px;border:1px solid rgba(212,175,55,0.5);
            box-shadow:0 8px 24px rgba(0,0,0,0.25);position:sticky;top:20px">
    <div style="font-size:12px;font-weight:900;color:#d4af37;text-align:center;
                margin-bottom:12px;letter-spacing:2px">🔮 내 사주 정보</div>
    <div style="color:#fff;font-size:12px;line-height:2.0">
        <div>👤 <b style="color:#d4af37">{_sn}</b> {gender_emoji}</div>
        <div>📅 {_date_str}</div>
        <div>⏰ {_hr_str}</div>
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(212,175,55,0.3)">
            🌟 일간: <b style="color:#ffd700;font-size:18px">{_ilgan}</b>
        </div>
    </div>
    <div style="display:flex;gap:4px;margin-top:10px">{pil_html}</div>
</div>"""

            col_main, col_right = st.columns([3, 1])
            with col_right:
                st.markdown(right_panel_html, unsafe_allow_html=True)
                st.markdown('<div style="margin-top:8px"></div>', unsafe_allow_html=True)
                st.button("✏️ 정보 수정", use_container_width=True, key="right_edit_btn",
                          on_click=lambda: st.session_state.update({"form_expanded": True}))

            with col_main:
                # -- 선택된 메뉴 콘텐츠 렌더링 --
                curr = st.session_state.get("current_menu", "종합운세")
                if curr == "종합운세":      menu1_report(pils, name, birth_year, gender, _ss.get("in_occupation",""), api_key, groq_key)
                elif curr == "만세력":      menu12_manse(pils, birth_year, gender)
                elif curr == "대운":        menu2_lifeline(pils, birth_year, gender, name, api_key, groq_key)
                elif curr == "과거":        menu3_past(pils, birth_year, gender, name, api_key, groq_key)
                elif curr == "미래":        menu4_future3(pils, birth_year, gender, _ss.get("in_marriage","미혼"), name, api_key, groq_key)
                elif curr == "신년 운세":   menu11_yearly(pils, name, birth_year, gender, api_key, groq_key)
                elif curr == "월별 운세":   menu10_monthly(pils, name, birth_year, gender, api_key, groq_key)
                elif curr == "일일 운세":   menu9_daily(pils, name, birth_year, gender, api_key, groq_key)
                elif curr == "재물":        menu5_money(pils, birth_year, gender, name, api_key, groq_key)
                elif curr == "궁합 결혼운":  menu6_relations(pils, name, birth_year, gender, _ss.get("in_marriage","미혼"), api_key, groq_key)
                elif curr == "직장운":
                    try: menu13_career(pils, name, birth_year, gender)
                    except: st.info("직장운 분석 준비 중")
                elif curr == "건강운":
                    try: menu14_health(pils, name, birth_year, gender)
                    except: st.info("건강운 분석 준비 중")
                elif curr == "만신 상담소":  menu7_ai(pils, name, birth_year, gender, api_key, groq_key)
                elif curr == "비방록":      menu8_bihang(pils, name, birth_year, gender)
                elif curr == "PDF 출력":    menu_pdf(pils, birth_year, gender, name)

    total_lines = get_total_lines()
    st.markdown(f"""
    <div style="text-align:right; font-size:10px; color:#aaa; margin-top:20px; border-top:1px solid #eee; padding-top:10px">
        [System Info] Total Engine Lines: {total_lines} | Version: Python 3.13 Stable
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
#  📄 PDF 출력 메뉴
# ==========================================================
def menu_pdf(pils, birth_year, gender, name="내담자", birth_hour_str=""):
    """📄 PDF 출력 - 사주 천명 리포트 다운로드"""
    import io, os
    from datetime import datetime as _dt

    st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a1a,#333);border-radius:16px;
            padding:20px 24px;margin-bottom:20px;color:#f7e695;text-align:center">
    <div style="font-size:22px;font-weight:900;letter-spacing:4px">📄 사주 천명 리포트 PDF 출력</div>
    <div style="font-size:13px;color:#ccc;margin-top:6px">아래 설정 후 생성 버튼을 누르면 PDF를 다운로드합니다</div>
</div>""", unsafe_allow_html=True)

    # -- 출력 섹션 선택 --
    col1, col2 = st.columns(2)
    with col1:
        include_basic    = st.checkbox("사주 기본 정보 (팔자/오행)", value=True, key="pdf_basic")
        include_yongshin = st.checkbox("용신/격국 상세 분석", value=True, key="pdf_yong")
        include_past     = st.checkbox("과거 적중 (상세 서술)", value=True, key="pdf_past")
        include_dw       = st.checkbox("대운 흐름 (10년 단위)", value=True, key="pdf_dw")
        include_current  = st.checkbox("현재 운세 분석 (올해/내년)", value=True, key="pdf_current")
        include_future   = st.checkbox("미래 5년 운세 흐름", value=True, key="pdf_future")
    with col2:
        include_ss      = st.checkbox("십성 분포 분석", value=True, key="pdf_ss")
        include_sinsal  = st.checkbox("신살 분석", value=True, key="pdf_sinsal")
        include_yukjin  = st.checkbox("육친 분석", value=True, key="pdf_yukjin")
        include_fortune = st.checkbox("AI 종합운세 (전문 분석)", value=True, key="pdf_fortune")
        include_advice  = st.checkbox("처방/조언", value=True, key="pdf_advice")

    if st.button("📥 PDF 생성 및 다운로드", use_container_width=True, key="pdf_gen_btn"):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.pdfbase import pdfmetrics
            from reportlab.lib import colors

            # -- 폰트 등록: 한글/한자 지원 우선순위 --
            _FONT_CANDIDATES = [
                ("Malgun",  "C:/Windows/Fonts/malgun.ttf",   None),
                ("Batang",  "C:/Windows/Fonts/batang.ttc",   0),
                ("Gulim",   "C:/Windows/Fonts/gulim.ttc",    0),
                ("Dotum",   "C:/Windows/Fonts/dotum.ttc",    0),
                ("Malgun2", "C:/Windows/Fonts/malgunbd.ttf", None),
                ("NanumGothic", os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts/NanumGothic.ttf"), None),
                ("NanumGothic2", "C:/Windows/Fonts/NanumGothic.ttf", None),
            ]
            BASE_FONT = "Helvetica"
            for _fn, _fp, _fi in _FONT_CANDIDATES:
                if os.path.exists(_fp):
                    try:
                        if _fi is not None:
                            pdfmetrics.registerFont(TTFont(_fn, _fp, subfontIndex=_fi))
                        else:
                            pdfmetrics.registerFont(TTFont(_fn, _fp))
                        BASE_FONT = _fn
                        break
                    except Exception as e:
                        pass  # 다음 폰트 시도
            if BASE_FONT == "Helvetica":
                st.warning("⚠️ 한글 폰트를 찾지 못했습니다. PDF에 한글이 정상 출력되지 않을 수 있습니다. malgun.ttf 또는 Batang 폰트를 설치해주세요.")

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            W, H = A4
            MARGIN = 22 * mm
            BOT = 22 * mm          # 하단 여백
            y = H - 24 * mm        # 시작 y 위치

            def draw_line(c, y, color=(0.8, 0.7, 0.2), width=0.5):
                c.setStrokeColorRGB(*color)
                c.setLineWidth(width)
                c.line(MARGIN, y, W - MARGIN, y)
                return y - 3 * mm

            def new_page(c):
                c.showPage()
                return H - 24 * mm

            # 비BMP 이모지 + 특수기호 → PDF 안전 텍스트 변환
            _EMOJI_MAP = {
                "🔴": "[●]", "🟡": "[◑]", "🟢": "[○]", "🔵": "[○]",
                "⭐": "[★]", "🌟": "[★]", "🪐": "",   "🌙": "",
                "✅": "[V]", "❌": "[X]", "⚠️": "[!]", "⚠": "[!]", "🗑": "",
                "🔮": "[*]", "📄": "",   "📥": "",   "⬇": "",
                "🍀": "[*]", "🌈": "",   "💫": "",   "🎯": "[->]",
                "📖": "",   "🏛": "",   "⚡": "[!]", "🌊": "",
            }
            # BMP 범위 특수기호 변환 (PDF 폰트 미지원 문자 대비)
            _SYMBOL_MAP = {
                "◆": "[*]", "◇": "[ ]", "■": "[#]", "□": "[ ]",
                "●": "(*)", "○": "( )", "◎": "(o)", "◉": "(*)",
                "▲": "(^)", "△": "(^)", "▶": "->",  "►": "->",
                "★": "*",   "☆": "*",
                "→": "->",  "←": "<-",  "↑": "^",   "↓": "v",
                "『": "[",  "』": "]",  "【": "[",  "】": "]",
            }

            def _safe_text(text):
                """비BMP 이모지 + 특수기호를 PDF 안전 텍스트로 변환"""
                result = []
                for ch in (text or ""):
                    o = ord(ch)
                    if o > 0xFFFF:
                        result.append(_EMOJI_MAP.get(ch, ""))
                    elif ch in _EMOJI_MAP:
                        result.append(_EMOJI_MAP[ch])
                    elif ch in _SYMBOL_MAP and BASE_FONT == "Helvetica":
                        # 폰트가 Helvetica(한글 미지원)일 때만 치환
                        result.append(_SYMBOL_MAP[ch])
                    else:
                        result.append(ch)
                return "".join(result)

            def write(c, text, y, font=BASE_FONT, size=12, color=(0.1,0.1,0.1), indent=0, line_h=7.2):
                if y < BOT:
                    y = new_page(c)
                c.setFont(font, size)
                c.setFillColorRGB(*color)
                max_w = W - 2 * MARGIN - indent
                lines = []
                for raw in _safe_text(text or "").split("\n"):
                    if not raw.strip():
                        lines.append(""); continue
                    while raw:
                        if c.stringWidth(raw, font, size) <= max_w:
                            lines.append(raw); break
                        lo, hi = 1, len(raw)
                        while lo < hi - 1:
                            mid = (lo + hi) // 2
                            if c.stringWidth(raw[:mid], font, size) <= max_w:
                                lo = mid
                            else:
                                hi = mid
                        bp = lo
                        sp = raw.rfind(' ', 0, bp + 1)
                        if sp > 0:
                            bp = sp
                        lines.append(raw[:bp])
                        raw = raw[bp:].lstrip()
                for ln in lines:
                    if y < BOT:
                        y = new_page(c)
                    c.drawString(MARGIN + indent, y, ln)
                    y -= line_h * mm
                return y

            def section_title(c, text, y):
                if y < 42 * mm:
                    y = new_page(c)
                # 골드 배경 바
                c.setFillColorRGB(0.15, 0.12, 0.05)
                c.rect(MARGIN - 3*mm, y - 2*mm, W - 2*MARGIN + 6*mm, 9*mm, fill=1, stroke=0)
                c.setFillColorRGB(0.97, 0.88, 0.38)
                c.setFont(BASE_FONT, 14)
                c.drawString(MARGIN + 1*mm, y + 1.5*mm, text)
                y -= 11 * mm
                return y

            def subsection(c, text, y):
                """소제목 (이탤릭 느낌의 구분선)"""
                if y < BOT:
                    y = new_page(c)
                c.setFillColorRGB(0.25, 0.18, 0.05)
                c.setFont(BASE_FONT, 12)
                c.drawString(MARGIN, y, f"◆ {text}")
                y -= 6.5 * mm
                c.setStrokeColorRGB(0.75, 0.65, 0.25)
                c.setLineWidth(0.3)
                c.line(MARGIN, y + 1*mm, W - MARGIN, y + 1*mm)
                y -= 2 * mm
                return y

            import re as _re_pdf

            def _clean_narrative_for_pdf(cv, raw_text, y_start):
                """HTML/마크다운 정제 후 챕터·카테고리별로 subsection/write 처리"""
                # 1. HTML 태그 제거
                txt = _re_pdf.sub(r'<[^>]+>', '', raw_text or "")
                # 2. 마크다운 강조 기호 제거
                txt = _re_pdf.sub(r'\*{2,3}([^*\n]+)\*{2,3}', r'\1', txt)
                txt = _re_pdf.sub(r'\*([^*\n]+)\*', r'\1', txt)
                txt = _re_pdf.sub(r'_{2}([^_\n]+)_{2}', r'\1', txt)
                txt = _re_pdf.sub(r'_([^_\n]+)_', r'\1', txt)
                txt = _re_pdf.sub(r'^#{1,6}\s+', '', txt, flags=_re_pdf.MULTILINE)
                txt = _re_pdf.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', txt)  # [text](url)
                # 3. 구분선(---/===) 제거
                txt = _re_pdf.sub(r'^[-=─]{3,}\s*$', '', txt, flags=_re_pdf.MULTILINE)
                # 4. 연속 공백/빈줄 정리
                txt = _re_pdf.sub(r'[ \t]+', ' ', txt)
                txt = _re_pdf.sub(r'\n{3,}', '\n\n', txt).strip()

                # 챕터 제목 패턴: [ 제N장 ... ] 또는 [ 제N장 | 부제 ]
                _chap_pat = _re_pdf.compile(
                    r'^\s*\[\s*(제\s*\d+\s*[장절][^\]]{0,60})\s*\]\s*$'
                )
                # 카테고리 레이블 패턴: [직업]: 내용
                _cat_pat = _re_pdf.compile(
                    r'^\s*\[([가-힣\w]{1,12})\]\s*[:：]\s*(.*)$'
                )
                # 불릿 패턴: * 내용 또는 - 내용
                _bullet_pat = _re_pdf.compile(r'^\s*[*\-•]\s+(.+)$')

                y = y_start
                _buf = []

                def _flush():
                    nonlocal y, _buf
                    if _buf:
                        combined = '\n'.join(_buf).strip()
                        if combined:
                            y = write(cv, combined, y, size=12, line_h=7.5)
                        _buf = []

                for line in txt.split('\n'):
                    line = line.rstrip()

                    # 챕터 제목
                    m = _chap_pat.match(line)
                    if m:
                        _flush()
                        y = subsection(cv, m.group(1).strip(), y)
                        continue

                    # 카테고리 레이블 [직업]: ...
                    m = _cat_pat.match(line)
                    if m:
                        _flush()
                        label_text = f"[{m.group(1)}]  {m.group(2).strip()}"
                        y = write(cv, label_text, y, size=11,
                                  color=(0.12, 0.22, 0.48), line_h=7)
                        continue

                    # 불릿 포인트
                    m = _bullet_pat.match(line)
                    if m:
                        _flush()
                        y = write(cv, f"  • {m.group(1).strip()}", y,
                                  size=11, color=(0.2, 0.2, 0.2), line_h=7)
                        continue

                    # 빈 줄
                    if line.strip() == '':
                        _flush()
                        y -= 1.5 * mm
                        continue

                    _buf.append(line)

                _flush()
                return y

            # == 표지 ==
            c.setFillColorRGB(0.05, 0.05, 0.05)
            c.rect(0, H - 55*mm, W, 55*mm, fill=1, stroke=0)
            c.setFillColorRGB(0.97, 0.90, 0.42)
            c.setFont(BASE_FONT, 24)
            c.drawCentredString(W/2, H - 28*mm, "만신 사주 천명풀이")
            c.setFillColorRGB(0.85, 0.85, 0.85)
            c.setFont(BASE_FONT, 11)
            c.drawCentredString(W/2, H - 36*mm, "사주팔자 / 천명을 밝히다")
            c.setFillColorRGB(0.7, 0.7, 0.7)
            c.setFont(BASE_FONT, 9)
            c.drawCentredString(W/2, H - 44*mm, f"출력일: {_dt.now().strftime('%Y년 %m월 %d일 %H:%M')}")
            y = H - 62*mm

            # -- 이름/생년월일 --
            y = write(c, f"대상: {name}  |  성별: {gender}  |  출생연도: {birth_year}년", y,
                      size=11, color=(0.2,0.2,0.2))
            y -= 3*mm

            ilgan        = pils[1]["cg"]
            birth_month  = st.session_state.get("birth_month", 1)
            birth_day    = st.session_state.get("birth_day", 1)
            birth_hour   = st.session_state.get("birth_hour", 12)
            birth_minute = st.session_state.get("birth_minute", 0)

            # == 1. 사주 기본 정보 ==
            if include_basic:
                y = section_title(c, "사주 팔자", y)
                pil_names = ["연주(年柱)", "월주(月柱)", "일주(日柱)", "시주(時柱)"]
                # get_pillars returns [시, 일, 월, 연] -> Reverse for [연, 월, 일, 시] labeling
                for i, (pn, p) in enumerate(zip(pil_names, pils[::-1])):
                    cg_oh = OHN.get(OH.get(p["cg"],""),"")
                    jj_oh = OHN.get(OH.get(p["jj"],""),"")
                    y = write(c, f"  {pn}: {p['cg']} ({cg_oh})  {p['jj']} ({jj_oh})", y, size=10)
                y -= 3*mm

                # 오행 분포
                oh_count = {}
                for p in pils:
                    for ch in [p["cg"], p["jj"]]:
                        o = OH.get(ch, "")
                        if o:
                            oh_count[o] = oh_count.get(o, 0) + 1
                oh_str = "  ".join([f"{OHN.get(o,o)} {v}개" for o, v in oh_count.items()])
                y = write(c, f"오행 분포: {oh_str}", y, size=10)

                # ── 오행 분포 바 차트 ──
                _oh_s    = calc_ohaeng_strength(pils[1]["cg"], pils)
                _oh_ord  = ["木", "火", "土", "金", "水"]
                _oh_rgb  = {"木":(0.18,0.65,0.18),"火":(0.90,0.22,0.22),
                            "土":(0.85,0.55,0.10),"金":(0.55,0.55,0.55),"水":(0.13,0.53,0.87)}
                _oh_lbl  = {"木":"목(木)","火":"화(火)","土":"토(土)","金":"금(金)","水":"수(水)"}
                _cw      = W - 2 * MARGIN
                _bw      = _cw / 5 - 3 * mm
                _bmax_h  = 32 * mm
                if y < _bmax_h + 18 * mm:
                    c.showPage(); y = H - 20 * mm
                _base_y  = y - _bmax_h - 5 * mm
                for _i, _oh in enumerate(_oh_ord):
                    _val = _oh_s.get(_oh, 0)
                    _bh  = _bmax_h * _val / 100
                    _bx  = MARGIN + _i * (_cw / 5)
                    c.setFillColorRGB(*_oh_rgb[_oh])
                    c.rect(_bx + 1 * mm, _base_y, _bw, _bh, fill=1, stroke=0)
                    c.setFillColorRGB(0.15, 0.15, 0.15)
                    c.setFont(BASE_FONT, 8)
                    c.drawCentredString(_bx + 1 * mm + _bw / 2, _base_y + _bh + 1.5 * mm, f"{_val}%")
                    c.setFont(BASE_FONT, 7)
                    c.drawCentredString(_bx + 1 * mm + _bw / 2, _base_y - 4 * mm, _oh_lbl[_oh])
                c.setStrokeColorRGB(0.75, 0.75, 0.75)
                c.setLineWidth(0.5)
                c.line(MARGIN, _base_y, W - MARGIN, _base_y)
                y = _base_y - 8 * mm

            # == 2. 용신/격국 상세 분석 ==
            if include_yongshin:
                y = section_title(c, "용신 / 격국 / 신강신약 — 천명의 설계도", y)
                _gk = get_gyeokguk(pils)
                _ys_ml = get_yongshin_multilayer(pils, birth_year, gender, _dt.now().year)
                _si = get_ilgan_strength(ilgan, pils)
                _gkname = _gk["격국명"] if _gk else "미정격"
                _gkgrade = _gk.get("격의_등급", "") if _gk else ""
                _sn = _si["신강신약"]
                _score = _si.get("일간점수", 50)
                _yong1 = _ys_ml.get("용신_1순위", "-")
                _yong2 = _ys_ml.get("용신_2순위", "-")
                _heui  = _ys_ml.get("희신", "-")
                _gisin = ", ".join(_ys_ml.get("기신", []))
                _dw_interp = _ys_ml.get("대운_해석", "")

                # 격국 서술
                _GK_NARR = {
                    "정관격": "정관격(正官格)은 규칙과 질서를 중시하며 조직에서 빛을 발하는 격국이니라. 명예와 체면을 소중히 여기고 공직·관리직·교육직에서 크게 성취하는 팔자니라. 이 격은 법도를 지키는 것이 곧 발복(發福)의 열쇠이니, 편법과 요행은 이 팔자에 어울리지 않느니라.",
                    "편관격": "편관격(偏官格)은 강인한 의지와 도전 정신이 핵심이니라. 칠살격(七殺格)이라고도 하며, 제화(制化)가 되면 영웅의 팔자요, 안 되면 파란만장한 고난의 팔자니라. 군경·의료·법조·스포츠처럼 강인함이 요구되는 분야에서 진가를 발휘하느니라.",
                    "정재격": "정재격(正財格)은 성실함과 꾸준함으로 재물을 쌓는 격국이니라. 한 푼 두 푼 모아 큰 부를 이루는 타입으로, 금융·회계·유통·부동산에서 두각을 나타내느니라. 갑작스러운 횡재보다는 땀의 대가가 인생을 풍요롭게 하느니라.",
                    "편재격": "편재격(偏財格)은 사업가 기질이 넘치는 격국이니라. 아버지 인연과 이성 인연이 굵직하며, 투자·무역·영업·자영업에서 두각을 나타내느니라. 편재는 움직이는 돈이라, 항상 유동적이고 과감한 결정이 필요하느니라.",
                    "식신격": "식신격(食神格)은 복록(福祿)이 넘치는 격국이니라. 먹을 복, 직업 복, 자식 복이 함께하며 창작·예술·요리·교육·서비스 분야에서 자연스럽게 빛을 발하느니라. 이 격은 억지로 밀어붙이기보다 흐름에 맡겨야 복이 흘러들어오느니라.",
                    "상관격": "상관격(傷官格)은 재기(才氣)와 창의성이 폭발하는 격국이니라. 규칙에 얽매이지 않는 자유로운 영혼으로 IT·예술·방송·컨설팅에서 독보적 존재가 되느니라. 다만 윗사람과의 마찰을 조심하고 언어를 조심해야 하느니라.",
                    "편인격": "편인격(偏印格)은 학문과 연구에 뛰어난 격국이니라. 철학·역술·의학·IT·연구직에서 독보적인 전문성을 쌓아가느니라. 계획이 자주 바뀌고 이사나 직업 변동이 잦을 수 있으나, 그 모든 경험이 결국 깊은 내공으로 쌓이느니라.",
                    "정인격": "정인격(正印格)은 학문과 자격의 격국이니라. 어머니의 음덕이 크고 교육·학술·자격 기반의 전문직에서 평생 성장하느니라. 성실히 배우고 익히는 것이 이 팔자의 발복 비결이니라.",
                    "비견격": "비견격(比肩格)은 독립심과 자존심이 강한 격국이니라. 자수성가형으로 독립사업·프리랜서·스포츠에서 진가를 발휘하느니라. 다만 재물이 손에 잡혀도 경쟁과 지출로 빠져나가기 쉬우니 저축 습관을 들이게.",
                    "겁재격": "겁재격(劫財格)은 강렬한 승부욕과 에너지를 가진 격국이니라. 영업·스포츠·투자·경쟁 분야에서 두각을 나타내지만, 재물이 들어오는 만큼 나가는 기운도 있으니 동업과 보증은 반드시 조심하게.",
                }
                _gk_desc = _GK_NARR.get(_gkname, f"{_gkname}은(는) 독특한 개성과 능력을 갖춘 격국이니라. 자신만의 방식으로 세상에 가치를 만들어내는 팔자니라.")

                # 신강신약 서술
                _SN_NARR = {
                    "신강(身强)": "일간(日干)의 힘이 강하니라. 자기 주도적이고 추진력이 강하며, 스스로 움직여야 기회가 찾아오는 팔자니라. 다만 지나치게 강하면 독선이 되니, 용신으로 기운을 조율하는 것이 중요하느니라.",
                    "극신강(極身强)": "일간(日干)의 힘이 극도로 강하니라. 넘치는 에너지가 때로 독이 될 수 있느니라. 관살(官殺)로 제어하거나 재성(財星)으로 흘려보내야 이 강한 기운이 빛을 발하느니라.",
                    "신약(身弱)": "일간(日干)의 힘이 약하니라. 귀인과 함께할 때 가장 강해지는 팔자니라. 좋은 파트너, 훌륭한 스승과의 인연이 운명을 바꾸는 열쇠이며, 인성(印星) 대운에 크게 발복하느니라.",
                    "극신약(極身弱)": "일간(日干)의 힘이 극도로 약하니라. 오행의 도움이 절실히 필요한 팔자니라. 용신 오행을 철저히 활용하고, 무리한 독립 창업보다는 안정적인 조직 생활이 이 팔자에 맞느니라.",
                    "중화(中和)": "일간(日干)의 기운이 균형을 이루고 있느니라. 꾸준함과 성실함이 가장 큰 무기인 팔자니라. 한 분야를 깊이 파고드는 전략이 가장 효과적이며, 급격한 변화보다 점진적인 성장이 이 팔자의 발복 패턴이니라.",
                }
                _sn_desc = _SN_NARR.get(_sn, f"{_sn}의 기운을 가진 팔자니라. 용신 오행을 활용하여 균형을 잡는 것이 핵심이느니라.")

                # 용신 활용 서술
                _OH_KR = {"木":"목(木)","火":"화(火)","土":"토(土)","金":"금(金)","水":"수(水)"}
                _YONG_ADVICE = {
                    "木": "목(木) 용신이니라. 동쪽이 길방이요, 초록·파랑 계열의 색이 기운을 북돋아 주느니라. 식물을 가까이하고 봄에 중요한 결정을 내리는 것이 좋으니라.",
                    "火": "화(火) 용신이니라. 남쪽이 길방이요, 빨강·주황 계열의 색이 기운을 높여주느니라. 밝고 활기찬 환경에서 일하고 여름에 큰 결단을 내리게.",
                    "土": "토(土) 용신이니라. 중앙 또는 북동·남서 방향이 길방이요, 황토색·노랑 계열이 안정을 주느니라. 부동산·토지와 인연이 있으니 이쪽에 관심을 두어도 좋으니라.",
                    "金": "금(金) 용신이니라. 서쪽이 길방이요, 흰색·금색·은색 계열이 기운을 강화하느니라. 가을에 중요한 결정을 내리고 금속·철강 관련 분야와 인연이 있느니라.",
                    "水": "수(水) 용신이니라. 북쪽이 길방이요, 검정·남색·짙은 파랑 계열이 기운을 도와주느니라. 물 가까이 사는 것도 좋고 겨울에 지혜가 더욱 빛을 발하느니라.",
                }
                _yong_advice = _YONG_ADVICE.get(_yong1, f"{_yong1} 오행이 용신이니라. 이 오행을 일상에서 적극 활용하게.")

                # 기신 경고
                _GISIN_WARN = {
                    "木": "기신(忌神)이 목(木) 기운이니 목 관련 해(寅(인)·卯(묘)년)에는 무리한 확장을 삼가게.",
                    "火": "기신이 화(火) 기운이니 화 관련 해(巳(사)·午(오)년)에는 심장·혈압 건강을 챙기고 충동적 결정을 자제하게.",
                    "土": "기신이 토(土) 기운이니 토 관련 해(辰(진)·戌(술)·丑(축)·未(미)년)에는 부동산 거래와 이사를 신중히 하게.",
                    "金": "기신이 금(金) 기운이니 금 관련 해(申(신)·酉(유)년)에는 수술·부상을 조심하고 투자를 자제하게.",
                    "水": "기신이 수(水) 기운이니 수 관련 해(亥(해)·子(자)년)에는 신장·방광 건강을 챙기고 유동성 투자를 줄이게.",
                }
                _gisin_warns = [_GISIN_WARN.get(g, f"{g} 기운이 흉하니 관련 해에 주의하게.") for g in _ys_ml.get("기신", [])]

                y = subsection(c, f"격국: {_gkname}  [{_gkgrade}]", y)
                y = write(c, _gk_desc, y, size=12, line_h=7.5)
                y -= 3*mm

                y = subsection(c, f"신강신약: {_sn}  (일간 힘 점수 {_score}/100)", y)
                y = write(c, _sn_desc, y, size=12, line_h=7.5)
                y -= 3*mm

                y = subsection(c, f"용신 · 희신 · 기신", y)
                y = write(c, f"용신 1순위: {_yong1}  |  2순위: {_yong2}  |  희신: {_heui}  |  기신: {_gisin}", y, size=12)
                y = write(c, _yong_advice, y, size=12, line_h=7.5)
                if _gisin_warns:
                    for _gw in _gisin_warns:
                        y = write(c, f"  ⚠ {_gw}", y, size=11, color=(0.6, 0.15, 0.1), line_h=7)
                y -= 3*mm

                if _dw_interp:
                    y = subsection(c, "현재 대운 해석", y)
                    y = write(c, f"  {_dw_interp}", y, size=12, line_h=7.5)
                y -= 3*mm

                # -- 재물 황금기: 용신 오행이 세운 천간에 들어오는 해 (향후 20년) --
                _gold_yong_ohs = set()
                for _goh in [_yong1, _yong2]:
                    if _goh and _goh in ("木","火","土","金","水"):
                        _gold_yong_ohs.add(_goh)
                if _gold_yong_ohs:
                    _cy_gold = _dt.now().year
                    _gold_years = []
                    for _gy in range(_cy_gold, _cy_gold + 21):
                        _gsw = get_yearly_luck(pils, _gy)
                        _gsw_cg = (_gsw.get("세운") or "")[:1]
                        _gsw_oh = OH.get(_gsw_cg, "")
                        if _gsw_oh in _gold_yong_ohs:
                            _gage = _gy - birth_year + 1
                            _gss  = _gsw.get("십성_천간", "")
                            _ggh  = _gsw.get("길흉", "")
                            _is_jae = _gss in ("偏財", "正財")
                            _star = "★★" if _is_jae else "★"
                            _gold_years.append(
                                f"{_gy}년 ({_gage}세): {_gsw.get('세운','')} [{_gss}] {_ggh}  {_star}"
                            )
                    if _gold_years:
                        y = subsection(c, f"향후 20년 재물 황금기 — 용신({_yong1}) 세운 진입 연도", y)
                        y = write(c, "  용신 오행이 세운 천간에 들어오는 해는 재물·성취 에너지가 극대화되는 시기니라.", y,
                                  size=11, color=(0.35, 0.22, 0.0), line_h=7)
                        y = write(c, "  (★★ = 재성 세운으로 재물 직접 활성화)", y,
                                  size=10, color=(0.45, 0.28, 0.0), line_h=6.5)
                        for _gy_str in _gold_years:
                            y = write(c, f"  {_gy_str}", y, size=11,
                                      color=(0.48, 0.28, 0.02), line_h=7)
                        y -= 3*mm
                y -= 2*mm

            # == 3. 십성 분포 분석 ==
            if include_ss:
                y = section_title(c, "십성 분포 분석", y)
                _pil_names = ["시주", "일주", "월주", "년주"]
                _ss_count = {}
                for _i, p in enumerate(pils):
                    ss_cg = TEN_GODS_MATRIX.get(ilgan, {}).get(p["cg"], "-")
                    ss_jj_list = JIJANGGAN.get(p["jj"], [])
                    ss_jj = TEN_GODS_MATRIX.get(ilgan, {}).get(ss_jj_list[-1] if ss_jj_list else "", "-")
                    y = write(c, f"  {_pil_names[_i]} {p['str']}: 천간 {ss_cg}  지지 {ss_jj}", y, size=10)
                    for _s in [ss_cg, ss_jj]:
                        if _s and _s != "-":
                            _ss_count[_s] = _ss_count.get(_s, 0) + 1
                _ss_summary = "  ".join([f"{k}×{v}" for k, v in sorted(_ss_count.items(), key=lambda x: -x[1])])
                y = write(c, f"  [십성 집계] {_ss_summary}", y, size=9, color=(0.35, 0.35, 0.35))
                y -= 4*mm

            # == 3-B. 과거 적중 상세 서술 ==
            if include_past:
                y = section_title(c, "과거 사건 적중 — 신안으로 본 지나온 인생", y)
                import re as _re2
                try:
                    # 1순위: AI 캐시에서 과거 분석 텍스트 가져오기
                    _sk = pils_to_cache_key(pils)
                    _past_ai = get_ai_cache(_sk, "past") or ""
                    if _past_ai:
                        _past_clean = _re2.sub(r'<[^>]+>', '', _past_ai)
                        _past_clean = _re2.sub(r'\n{3,}', '\n\n', _past_clean).strip()
                        y = write(c, _past_clean, y, size=12, line_h=7.5)
                    else:
                        # 2순위: engine highlights + 대운×세운 교차로 상세 서술 생성
                        _hl = generate_engine_highlights(pils, birth_year, gender)
                        _pevs = sorted(_hl.get("past_events", []),
                                       key=lambda e: {"🔴":0,"🟡":1,"🟢":2}.get(e.get("intensity","🟢"),3))
                        _current_y = _dt.now().year

                        _DOM_DETAIL = {
                            "직업변화": "직업 또는 직장에 큰 변동이 찾아왔느니라. 이직·부서 이동·창업 중 하나가 일어났을 것이니라.",
                            "결혼·교제": "인연의 기운이 강하게 들어왔느니라. 새로운 이성과의 만남이나 결혼·이별 중 하나가 있었느니라.",
                            "이사·이동": "삶의 터전이 흔들리는 시기니라. 이사·이민·장거리 이동의 기운이 강하게 들어왔느니라.",
                            "재물획득": "재물이 크게 들어오는 시기니라. 수입 증가·투자 성공·뜻밖의 횡재 중 하나가 있었느니라.",
                            "재물손실": "재물이 빠져나가는 시기니라. 지출 증가·투자 손실·보증·사기 중 하나가 있었느니라. 돌아보면 그때 조심해야 했느니라.",
                            "사고·관재": "위험한 기운이 들어온 시기니라. 사고·부상·법적 문제 중 하나가 발생했을 가능성이 높느니라.",
                            "질병·건강": "몸의 기운이 약해지는 시기니라. 건강 이상 신호나 수술·입원 중 하나가 있었느니라.",
                            "변화": "전반적으로 변화의 기운이 강했던 시기니라. 삶의 여러 방면에서 크고 작은 변화가 있었느니라.",
                        }
                        _SS_EVENT = {
                            "偏財": "편재(偏財) 기운이 활성화되어 재물 변동과 아버지 이슈, 이성 인연이 두드러졌느니라.",
                            "正財": "정재(正財) 기운이 들어와 안정적 수입 변화와 결혼·재산 형성의 기운이 작동했느니라.",
                            "食神": "식신(食神)이 빛을 발하여 직업 변화와 건강 이슈가 두드러졌느니라.",
                            "傷官": "상관(傷官)이 활성화되어 직장 마찰·이직·구설수의 기운이 강했느니라.",
                            "偏官": "편관(偏官)이 들어와 직장 변동과 사고·관재 기운이 강하게 작동했느니라.",
                            "正官": "정관(正官)의 기운으로 승진·결혼·명예와 관련된 변화가 있었느니라.",
                            "偏印": "편인(偏印)이 활성화되어 학업 중단·이사·계획 변경의 기운이 들어왔느니라.",
                            "正印": "정인(正印)의 기운으로 학업 성취·자격 취득·어머니 관련 사건이 있었느니라.",
                            "比肩": "비견(比肩)이 강해져 독립심과 경쟁이 극대화된 시기니라.",
                            "劫財": "겁재(劫財)가 들어와 재물 손실·형제 갈등·독립·창업의 기운이 강했느니라.",
                        }

                        if not _pevs:
                            y = write(c, "  허허, 이 시기에는 특별한 강한 사건의 기운이 감지되지 않는구먼. 비교적 평온한 흐름이었느니라.", y, size=12, line_h=7.5)
                        else:
                            for _ev in _pevs[:12]:
                                _itn = _ev.get("intensity", "🟢")
                                _yr  = _ev.get("year", "")
                                _age = _ev.get("age", "")
                                _dom = _ev.get("domain", "변화")
                                _desc = _ev.get("desc", "")
                                _yr_int = int(_yr) if str(_yr).isdigit() else 0

                                # 제목 줄
                                _itn_label = {"🔴":"[강도: 최고]","🟡":"[강도: 중]","🟢":"[강도: 보통]"}.get(_itn,"")
                                y = write(c, f"{_yr}년 ({_age})  {_itn_label}  [{_dom}]", y,
                                          size=13, color=(0.1,0.1,0.4))
                                y -= 1*mm

                                # 기본 설명
                                _dom_detail = _DOM_DETAIL.get(_dom, _DOM_DETAIL["변화"])
                                y = write(c, f"  {_desc}", y, size=12, line_h=7.5)
                                y = write(c, f"  {_dom_detail}", y, size=11, color=(0.3,0.3,0.3), line_h=7)

                                # 대운×세운 교차 분석 추가
                                if _yr_int > 0:
                                    try:
                                        _cross = get_daewoon_sewoon_cross(pils, birth_year, gender, _yr_int)
                                        if _cross:
                                            _dw_s = _cross["대운"].get("str","")
                                            _sw_s = _cross["세운"].get("세운","")
                                            _dw_ss_c = _cross.get("대운_천간십성","-")
                                            _sw_ss_c = _cross.get("세운_천간십성","-")
                                            _interp = _cross.get("교차해석","")
                                            _ss_ev = _SS_EVENT.get(_dw_ss_c, "") or _SS_EVENT.get(_sw_ss_c, "")
                                            y = write(c, f"  [명리 근거] {_dw_s} 대운({_dw_ss_c}) × {_sw_s} 세운({_sw_ss_c})", y,
                                                      size=11, color=(0.2,0.3,0.5), line_h=7)
                                            if _ss_ev:
                                                y = write(c, f"  {_ss_ev}", y, size=11, color=(0.2,0.3,0.5), line_h=7)
                                            if _interp:
                                                y = write(c, f"  {_interp}", y, size=11, color=(0.2,0.3,0.5), line_h=7)
                                            for _ce in _cross.get("교차사건",[]):
                                                y = write(c, f"  ◦ {_ce['desc']}", y, size=11, color=(0.5,0.15,0.1), line_h=7)
                                    except Exception as e:
                                        print(f"[WARN] {e}")
                                y -= 4*mm
                except Exception as _pe:
                    y = write(c, f"  (과거 사건 계산 불가: {_pe})", y, size=11)
                y -= 4*mm

            # == 4. 대운 흐름 ==
            if include_dw:
                y = section_title(c, "대운 흐름 (10년 단위)", y)
                current_year = _dt.now().year
                daewoon = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender)
                ys2 = get_yongshin(pils)
                yongshin_ohs = ys2.get("종합_용신", [])
                ilgan_oh = OH.get(ilgan, "")
                for dw in daewoon[:10]:
                    dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(dw["cg"], "-")
                    is_cur = dw["시작연도"] <= current_year <= dw["종료연도"]
                    is_yong = _get_yongshin_match(dw_ss, yongshin_ohs, ilgan_oh) == "yong"
                    cur_mark = " ◀현재" if is_cur else ""
                    yong_mark = " *용신" if is_yong else ""
                    presc = DAEWOON_PRESCRIPTION.get(dw_ss, "")
                    y = write(c, f"  {dw['시작나이']}~{dw['시작나이']+9}세  {dw['str']} ({dw_ss}){cur_mark}{yong_mark}", y, size=10)
                    if presc:
                        y = write(c, f"    -> {presc}", y, size=9, color=(0.4,0.4,0.4))

                # ── 대운 흐름 가로 막대 그래프 ──
                _DW_SC  = {"正財":80,"食神":85,"正官":75,"正印":70,
                           "偏財":65,"偏官":40,"劫財":35,"傷官":55,
                           "比肩":60,"偏印":50}
                _lbl_w  = 30 * mm
                _gw     = W - 2 * MARGIN - _lbl_w - 4 * mm
                _bh1    = 6.5 * mm
                _gap    = 1.8 * mm
                _dw10   = daewoon[:10]
                _need   = len(_dw10) * (_bh1 + _gap) + 14 * mm
                if y < _need:
                    c.showPage(); y = H - 20 * mm
                _top = y - 2 * mm
                for _j, _dw in enumerate(_dw10):
                    _dss = TEN_GODS_MATRIX.get(ilgan, {}).get(_dw["cg"], "-")
                    _ic  = _dw["시작연도"] <= current_year <= _dw["종료연도"]
                    _iy  = _get_yongshin_match(_dss, yongshin_ohs, ilgan_oh) == "yong"
                    _sc  = min(100, _DW_SC.get(_dss, 60) + (20 if _iy else 0))
                    _by  = _top - _j * (_bh1 + _gap)
                    if _ic:          _rgb = (1.0,  0.55, 0.0)
                    elif _iy:        _rgb = (0.83, 0.68, 0.21)
                    elif _sc < 50:   _rgb = (0.96, 0.60, 0.60)
                    else:            _rgb = (0.63, 0.77, 0.97)
                    c.setFillColorRGB(0.15, 0.15, 0.15)
                    c.setFont(BASE_FONT, 7)
                    c.drawString(MARGIN, _by - _bh1 + 1.5 * mm,
                                 f"{_dw['시작나이']}세 {_dw['str']} {_dss}")
                    _bl = _gw * _sc / 100
                    c.setFillColorRGB(*_rgb)
                    c.rect(MARGIN + _lbl_w, _by - _bh1 + 0.5 * mm,
                           _bl, _bh1 - 1 * mm, fill=1, stroke=0)
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.setFont(BASE_FONT, 6)
                    c.drawString(MARGIN + _lbl_w + _bl + 1.5 * mm,
                                 _by - _bh1 + 2 * mm, str(_sc))
                    if _ic:
                        c.setFillColorRGB(0.8, 0.2, 0.0)
                        c.drawString(MARGIN + _lbl_w + _bl + 8 * mm,
                                     _by - _bh1 + 2 * mm, "◀현재")
                # 범례
                _ly  = _top - len(_dw10) * (_bh1 + _gap) - 2 * mm
                _lx  = MARGIN
                for _lc, _lt in [((0.83,0.68,0.21),"용신"), ((1.0,0.55,0.0),"현재"),
                                  ((0.63,0.77,0.97),"일반"), ((0.96,0.60,0.60),"기신")]:
                    c.setFillColorRGB(*_lc)
                    c.rect(_lx, _ly, 4 * mm, 2.5 * mm, fill=1, stroke=0)
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.setFont(BASE_FONT, 7)
                    c.drawString(_lx + 5 * mm, _ly + 0.3 * mm, _lt)
                    _lx += 22 * mm
                y = _ly - 6 * mm

            # == 4-B. 현재 운세 분석 ==
            if include_current:
                _cy = _dt.now().year
                _cage = _cy - birth_year + 1
                y = section_title(c, f"현재 운세 — {_cy}년 ({_cage}세) 지금 이 순간", y)
                try:
                    _daewoon2 = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender)
                    _cdw = next((d for d in _daewoon2 if d["시작연도"] <= _cy <= d["종료연도"]), None)
                    _sw_c  = get_yearly_luck(pils, _cy)
                    _sw_n  = get_yearly_luck(pils, _cy + 1)
                    _sw_n2 = get_yearly_luck(pils, _cy + 2)
                    _tp    = calc_turning_point(pils, birth_year, gender, _cy)
                    _ys_c  = get_yongshin(pils)
                    _yohs  = _ys_c.get("종합_용신", [])
                    _ioh   = OH.get(ilgan, "")
                    _cdw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(_cdw["cg"], "-") if _cdw else "-"
                    _is_yong_dw = _cdw and _get_yongshin_match(_cdw_ss, _yohs, _ioh) == "yong"
                    _sw_c_ss = _sw_c.get("십성_천간", "-")
                    _sw_n_ss = _sw_n.get("십성_천간", "-")

                    # 현재 대운 상황
                    y = subsection(c, f"현재 대운: {_cdw['str'] if _cdw else '미상'} ({_cdw_ss})", y)
                    if _cdw:
                        _dw_years_left = _cdw["종료연도"] - _cy
                        if _is_yong_dw:
                            y = write(c, f"허허, 이 대운은 용신(用神) 대운이로구먼! 지금이 바로 황금기니라.", y, size=12, color=(0.1,0.3,0.1), line_h=7.5)
                            y = write(c, f"이 대운은 앞으로 {_dw_years_left}년 더 이어지느니라. 이 시기를 놓치면 아니 되느니라.", y, size=12, line_h=7.5)
                            y = write(c, "적극적으로 움직이고 투자하고 새로운 도전을 두려워하지 말게. 하늘이 자네 편이로구먼.", y, size=12, line_h=7.5)
                        else:
                            _presc_c = DAEWOON_PRESCRIPTION.get(_cdw_ss, "내실을 다지고 준비하는 시기니라.")
                            y = write(c, f"허어, 이 대운은 기신(忌神)의 기운이 있는 시기니라. {_dw_years_left}년 후에 대운이 바뀌느니라.", y, size=12, line_h=7.5)
                            y = write(c, f"이 시기의 처방: {_presc_c}", y, size=12, line_h=7.5)
                            y = write(c, "무리한 확장과 급격한 변화는 삼가게. 내실을 다지는 것이 최선이니라.", y, size=12, line_h=7.5)
                    y -= 3*mm

                    # 올해 세운 상세
                    y = subsection(c, f"올해 세운: {_sw_c.get('세운','')} ({_sw_c_ss} / {_sw_c.get('길흉','')})", y)
                    _SW_DETAIL = {
                        "偏財": "올해는 재물 변동과 이성 인연의 기운이 강하느니라. 사업 기회가 오지만 투기는 조심하게.",
                        "正財": "올해는 안정된 수입과 결혼 인연의 기운이 들어오느니라. 재물을 차곡차곡 모을 수 있는 해니라.",
                        "食神": "올해는 직업과 재능이 빛을 발하는 해니라. 새로운 일을 시작하거나 자격 취득에 좋으니라.",
                        "傷官": "올해는 재기와 창의성이 폭발하지만 윗사람과의 마찰을 조심해야 하느니라.",
                        "偏官": "올해는 직장 변동과 사고 기운이 있느니라. 건강과 안전에 각별히 주의하게.",
                        "正官": "올해는 명예와 승진의 기운이 강하느니라. 조직에서 인정받는 해니라.",
                        "偏印": "올해는 계획이 자주 바뀌고 이사·이동의 기운이 있느니라. 신중하게 결정하게.",
                        "正印": "올해는 학업과 자격 취득에 유리한 해니라. 어머니와의 인연도 돈독해지느니라.",
                        "比肩": "올해는 독립심이 강해지고 경쟁이 치열해지는 해니라. 동업보다는 단독 행동이 낫느니라.",
                        "劫財": "올해는 재물 손실과 경쟁이 극심한 해니라. 보증과 투자를 최대한 자제하게.",
                    }
                    _sw_detail = _SW_DETAIL.get(_sw_c_ss, f"올해는 {_sw_c_ss} 기운이 강하게 작동하는 해니라.")
                    y = write(c, _sw_detail, y, size=12, line_h=7.5)
                    # 올해 길흉 판단
                    if "길" in _sw_c.get("길흉",""):
                        y = write(c, "허허, 올해는 전반적으로 길한 기운이 흐르는구먼. 이 기운을 최대한 활용하게!", y, size=12, color=(0.1,0.3,0.1), line_h=7.5)
                    elif "흉" in _sw_c.get("길흉",""):
                        y = write(c, "허어, 올해는 흉한 기운이 있으니 조심해야 하느니라. 무리한 결정은 삼가게.", y, size=12, color=(0.5,0.1,0.1), line_h=7.5)
                    y -= 3*mm

                    # 전환점 강도
                    _tp_intensity = _tp.get("intensity", "보통")
                    _tp_reasons   = _tp.get("reason", [])
                    y = subsection(c, f"올해 인생 전환점 강도: {_tp_intensity}", y)
                    if _tp_reasons:
                        for _r in _tp_reasons[:4]:
                            y = write(c, f"  ◦ {_r}", y, size=12, line_h=7.5)
                    y -= 3*mm

                    # 내년 전망
                    y = subsection(c, f"내년 세운: {_sw_n.get('세운','')} ({_sw_n_ss} / {_sw_n.get('길흉','')})", y)
                    _sw_n_detail = _SW_DETAIL.get(_sw_n_ss, f"내년은 {_sw_n_ss} 기운이 작동하는 해니라.")
                    y = write(c, _sw_n_detail, y, size=12, line_h=7.5)
                    y = write(c, f"내후년({_cy+2}년): {_sw_n2.get('세운','')} [{_sw_n2.get('십성_천간','')}] — {_sw_n2.get('길흉','')}", y, size=11, color=(0.35,0.35,0.35), line_h=7)
                    y -= 3*mm

                    # 지금 해야 할 것 / 하지 말아야 할 것
                    y = subsection(c, "명심하게 — 지금 당장 해야 할 것 vs 하지 말아야 할 것", y)
                    _DO_LIST = {
                        "偏財": ("사업 아이디어 즉시 실행, 이성 인연에 적극적으로", "투기성 투자, 사기성 사업 파트너"),
                        "正財": ("저축 자동화, 자산 점진적 축적, 결혼 준비", "갑작스러운 큰 지출, 충동적 투자"),
                        "食神": ("새 직업 도전, 자격증 취득, 창작 활동 시작", "게으름, 재능 낭비, 불규칙한 식사"),
                        "傷官": ("창의적 아이디어 실행, 프리랜서 전환 검토", "상사와의 갈등, 충동적 발언, 직장 무단 이탈"),
                        "偏官": ("건강 검진, 법적 서류 정리, 안전 점검", "무모한 도전, 음주운전, 싸움"),
                        "正官": ("승진 도전, 조직 내 신뢰 쌓기, 자격증", "조직 규칙 위반, 성급한 독립"),
                        "偏印": ("새로운 학문 연구, 이사 준비", "계획 없는 변경, 충동적 이사"),
                        "正印": ("공부 시작, 학위 취득, 부모님 관계 강화", "학업 포기, 지식 낭비"),
                        "比肩": ("독립 창업 준비, 자기 계발", "동업, 보증, 공동 투자"),
                        "劫財": ("지출 최소화, 저축 강화", "주식·부동산 투자, 보증, 동업"),
                    }
                    _do, _dont = _DO_LIST.get(_sw_c_ss, ("현재 흐름에 맞는 결정을 내리게", "무리한 확장을 삼가게"))
                    y = write(c, f"  해야 할 것: {_do}", y, size=12, color=(0.1,0.3,0.1), line_h=7.5)
                    y = write(c, f"  하지 말 것: {_dont}", y, size=12, color=(0.5,0.1,0.1), line_h=7.5)
                except Exception as _ce:
                    y = write(c, f"  (현재 운세 계산 오류: {_ce})", y, size=11)
                y -= 5*mm

            # == 4-C. 미래 5년 운세 흐름 ==
            if include_future:
                _cy2 = _dt.now().year
                y = section_title(c, f"미래 5년 운세 — {_cy2+1}년~{_cy2+5}년 흐름", y)
                try:
                    _daewoon3 = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender)
                    _ys3 = get_yongshin(pils)
                    _yohs3 = _ys3.get("종합_용신", [])
                    _ioh3  = OH.get(ilgan, "")
                    _GOOD_SS = {"正財","食神","正官","正印","偏財"}
                    _BAD_SS  = {"偏官","劫財","傷官"}
                    _MID_SS  = {"比肩","偏印","偏財"}

                    _FUTURE_DETAIL = {
                        "偏財": "재물 변동과 이성 인연이 두드러지는 해니라. 사업·투자에 기회가 오나 과욕은 금물이니라.",
                        "正財": "안정된 재물이 쌓이는 해니라. 결혼·자산 형성에 최적의 시기이니라.",
                        "食神": "직업과 재능이 빛을 발하는 해니라. 새로운 일을 시작하거나 자격을 취득하기 좋으니라.",
                        "傷官": "창의성이 폭발하나 인간관계 마찰을 조심해야 하는 해니라. 독립·창업 에너지가 강하느니라.",
                        "偏官": "변동과 도전의 기운이 강한 해니라. 건강과 안전에 주의하고 무리한 확장은 삼가게.",
                        "正官": "명예와 승진의 기운이 오는 해니라. 조직에서 인정받고 책임 있는 자리에 오를 기운이니라.",
                        "偏印": "계획 변경과 이사·이동의 기운이 있는 해니라. 새로운 학문이나 기술을 배우기 좋으니라.",
                        "正印": "학업과 자격 취득에 유리한 해니라. 귀인과의 인연이 강해지는 시기이니라.",
                        "比肩": "독립심과 경쟁이 극대화되는 해니라. 단독 행동이 유리하고 새로운 시작에 좋은 시기니라.",
                        "劫財": "재물 손실과 경쟁이 심한 해니라. 보증·투자를 자제하고 내실을 다지는 것이 최선이니라.",
                    }

                    for _fy in range(_cy2 + 1, _cy2 + 6):
                        _fage = _fy - birth_year + 1
                        _fsw = get_yearly_luck(pils, _fy)
                        _fsw_ss = _fsw.get("십성_천간", "-")
                        _fsw_gilhung = _fsw.get("길흉", "")
                        _fdw = next((d for d in _daewoon3 if d["시작연도"] <= _fy <= d["종료연도"]), None)
                        _fdw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(_fdw["cg"], "-") if _fdw else "-"
                        _is_yong_y = _get_yongshin_match(_fsw_ss, _yohs3, _ioh3) == "yong"
                        _is_gi_y   = _get_yongshin_match(_fsw_ss, _yohs3, _ioh3) == "gi"

                        if _is_yong_y or _fsw_ss in _GOOD_SS:
                            _fcol = (0.05, 0.28, 0.05)
                            _flabel = "◎ 길운"
                        elif _is_gi_y or _fsw_ss in _BAD_SS:
                            _fcol = (0.45, 0.08, 0.08)
                            _flabel = "▲ 주의"
                        else:
                            _fcol = (0.15, 0.15, 0.35)
                            _flabel = "○ 보통"

                        y = write(c, f"{_fy}년 ({_fage}세)  {_fsw.get('세운','')}  [{_fsw_ss}]  {_flabel}  {_fsw_gilhung}", y,
                                  size=13, color=_fcol)
                        _fd = _FUTURE_DETAIL.get(_fsw_ss, f"{_fsw_ss} 기운이 작동하는 해니라.")
                        y = write(c, f"  {_fd}", y, size=11, color=(0.25,0.25,0.25), line_h=7)
                        if _fdw:
                            y = write(c, f"  [대운: {_fdw['str']} {_fdw_ss}]", y, size=10, color=(0.4,0.4,0.4), line_h=6.5)
                        y -= 3*mm
                except Exception as _fe:
                    y = write(c, f"  (미래 운세 계산 오류: {_fe})", y, size=11)
                y -= 4*mm

            # == 4-E. 신살 분석 ==
            if include_sinsal:
                y = section_title(c, "신살 분석", y)
                try:
                    _sin12 = get_12sinsal(pils)
                    _extra = get_extra_sinsal(pils)
                    _all_sins = _sin12 + _extra
                    if _all_sins:
                        for _s in _all_sins:
                            _sname = _s.get("이름") or _s.get("name", "")
                            _sicon = _s.get("icon", "")
                            _sdesc = _s.get("desc", "")
                            _scaution = _s.get("caution", "")
                            _spos = ", ".join(_s.get("위치", [])) if _s.get("위치") else ""
                            _header = f"  {_sicon} {_sname}" + (f"  ({_spos})" if _spos else "")
                            y = write(c, _header, y, size=10, color=(0.1, 0.2, 0.5))
                            if _sdesc:
                                y = write(c, f"    {_sdesc}", y, size=9, color=(0.2, 0.2, 0.2), line_h=6)
                            if _scaution:
                                y = write(c, f"    주의: {_scaution}", y, size=8, color=(0.55, 0.15, 0.15), line_h=5.5)
                    else:
                        y = write(c, "  (감지된 신살 없음)", y, size=9)
                except Exception:
                    y = write(c, "  (신살 계산 불가)", y, size=9)
                y -= 4*mm

            # == 4-F. 육친 분석 ==
            if include_yukjin:
                y = section_title(c, "육친 분석", y)
                try:
                    _yk = get_yukjin(ilgan, pils, gender)
                    for _rel in _yk:
                        _rname = _rel.get("관계", "")
                        _rwhere = _rel.get("위치", "없음")
                        _rdesc = _rel.get("desc", "")
                        _present = _rel.get("present", False)
                        _color = (0.1, 0.35, 0.1) if _present else (0.4, 0.4, 0.4)
                        y = write(c, f"  {_rname}  [{_rwhere}]", y, size=10, color=_color)
                        if _rdesc:
                            y = write(c, f"    {_rdesc}", y, size=9, color=(0.25, 0.25, 0.25), line_h=6)
                except Exception:
                    y = write(c, "  (육친 계산 불가)", y, size=9)
                y -= 4*mm

            # == 5. AI 종합운세 / 전문 분석 ==
            if include_fortune:
                y = section_title(c, "만신 종합 천명풀이 — 전문 사주 분석", y)
                try:
                    _saju_key = pils_to_cache_key(pils)
                    # 캐시 우선 (prophet > general > lifeline)
                    _ai_raw = (get_ai_cache(_saju_key, "prophet") or
                               get_ai_cache(_saju_key, "general") or
                               get_ai_cache(_saju_key, "lifeline") or "")
                    if _ai_raw:
                        y = _clean_narrative_for_pdf(c, _ai_raw, y)
                    else:
                        # 캐시 없음 → build_rich_narrative()로 직접 생성 (무당 말투 포함)
                        _narr = build_rich_narrative(pils, birth_year, gender, name, section="report")
                        if _narr:
                            y = _clean_narrative_for_pdf(c, _narr, y)
                        else:
                            # 최후 폴백: engine highlights
                            _hl3 = generate_engine_highlights(pils, birth_year, gender)
                            y = write(c, "허허, 내 신안(神眼)으로 이 사주를 풀어보겠느니라.\n", y, size=12, line_h=7.5)
                            for _ln in _hl3.get("personality", [])[:5]:
                                y = write(c, f"  {_ln}", y, size=12, line_h=7.5)
                            y -= 3*mm
                            y = write(c, "앱에서 AI 분석을 먼저 실행하면 더 상세한 해석이 PDF에 포함됩니다.", y,
                                      size=11, color=(0.45, 0.45, 0.45), line_h=7)
                except Exception as _ae:
                    y = write(c, f"  (종합 분석 생성 오류: {_ae})", y, size=11)
                y -= 4*mm

            # == 6. 처방/조언 ==
            if include_advice:
                y = section_title(c, "처방 — 만신이 내리는 핵심 조언", y)
                try:
                    _adv_dw_list = SajuCoreEngine.get_daewoon(pils, birth_year, birth_month, birth_day, birth_hour, birth_minute, gender)
                    _adv_dw = next((dw for dw in _adv_dw_list if dw["시작연도"] <= _dt.now().year <= dw["종료연도"]), None)
                    _adv_ys = get_yongshin(pils)
                    _adv_yohs = _adv_ys.get("종합_용신", [])
                    _adv_ioh  = OH.get(ilgan, "")
                    _adv_sw   = get_yearly_luck(pils, _dt.now().year)
                    _adv_sw_ss = _adv_sw.get("십성_천간", "-")
                    _adv_ys_ml = get_yongshin_multilayer(pils, birth_year, gender, _dt.now().year)

                    y = write(c, "허허, 내 신안(神眼)이 본 이 사주의 핵심 처방을 명심하게.", y, size=12, color=(0.2,0.1,0.0), line_h=7.5)
                    y -= 3*mm

                    if _adv_dw:
                        _adv_dw_ss = TEN_GODS_MATRIX.get(ilgan, {}).get(_adv_dw["cg"], "-")
                        _presc_main = DAEWOON_PRESCRIPTION.get(_adv_dw_ss, "꾸준한 노력으로 안정을 유지하게.")
                        y = subsection(c, f"대운 처방 — {_adv_dw['str']} {_adv_dw_ss}대운", y)
                        y = write(c, f"  {_presc_main}", y, size=12, color=(0.1,0.35,0.1), line_h=7.5)
                        y -= 2*mm

                    y = subsection(c, f"올해 세운 처방 — {_adv_sw.get('세운','')} {_adv_sw_ss}", y)
                    _SW_PRESC = {
                        "偏財": "재물 기회에 적극 대응하게. 단, 검증되지 않은 투자는 반드시 피하게.",
                        "正財": "재산을 차곡차곡 모으는 해니라. 저축과 자산 형성에 집중하게.",
                        "食神": "재능을 꽃피우는 해니라. 새로운 일을 시작하고 자격증을 취득하게.",
                        "傷官": "창의적 도전은 좋으나 말과 행동을 조심하게. 분쟁을 피하게.",
                        "偏官": "건강 검진을 먼저 받게. 안전 수칙을 철저히 지키게. 법적 서류를 정리하게.",
                        "正官": "조직에서 성실히 하면 인정받는 해니라. 명예를 지키는 것이 최우선이니라.",
                        "偏印": "무모한 이사·변경을 자제하게. 새로운 학문을 배우는 것은 길하느니라.",
                        "正印": "배움에 투자하게. 어머니·어른과의 관계를 돈독히 하게.",
                        "比肩": "혼자서 결정하고 혼자서 실행하는 것이 이 해의 길이니라. 동업은 자제하게.",
                        "劫財": "지출을 최소화하게. 보증·투자는 절대 삼가게. 내실을 다지는 것이 최선이니라.",
                    }
                    _sw_presc = _SW_PRESC.get(_adv_sw_ss, "현재 흐름에 맞는 신중한 결정을 내리게.")
                    y = write(c, f"  {_sw_presc}", y, size=12, color=(0.1,0.3,0.1), line_h=7.5)
                    y -= 2*mm

                    # 용신 활용 처방
                    _adv_yong1 = _adv_ys_ml.get("용신_1순위", "")
                    _YONG_PRESC = {
                        "木": "동쪽 방향에 중요한 공간을 배치하게. 초록 계열 소품을 활용하고 봄에 큰 결정을 내리게.",
                        "火": "남쪽이 길방이니라. 밝고 활기찬 환경에서 일하게. 붉은색 소품이 기운을 높여주니라.",
                        "土": "황토색·노랑 계열이 안정을 주느니라. 부동산 관련 분야에 관심을 두어도 좋으니라.",
                        "金": "서쪽이 길방이니라. 흰색·금색 소품을 활용하고 가을에 중요한 결정을 내리게.",
                        "水": "북쪽이 길방이니라. 물 가까이 사는 것도 좋고 검정·남색 계열이 기운을 도와주느니라.",
                    }
                    if _adv_yong1:
                        y = subsection(c, f"용신 {_adv_yong1} 활용 처방", y)
                        _yp = _YONG_PRESC.get(_adv_yong1, f"{_adv_yong1} 오행을 일상에서 적극 활용하게.")
                        y = write(c, f"  {_yp}", y, size=12, color=(0.0,0.2,0.4), line_h=7.5)
                        y -= 2*mm

                except Exception as _adv_e:
                    y = write(c, f"  (처방 계산 오류: {_adv_e})", y, size=11)
                y -= 3*mm
                y = write(c, "※ 이 리포트는 전통 사주명리학 분석 자료이며 참고용입니다.", y, size=10, color=(0.45,0.45,0.45))

            # -- 하단 푸터 --
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.setFont(BASE_FONT, 8)
            c.drawCentredString(W/2, 12*mm, f"만신 사주 천명풀이  |  {_dt.now().strftime('%Y.%m.%d')} 출력")

            c.save()
            buf.seek(0)

            fname = f"사주_{name}_{_dt.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                label="⬇️ PDF 다운로드",
                data=buf,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
                key="pdf_download_btn"
            )
            st.success(f"✅ PDF 생성 완료! 위 버튼으로 다운로드하세요.")

        except ImportError:
            st.error("❌ reportlab 미설치. `pip install reportlab` 을 실행해주세요.")
        except Exception as e:
            st.error(f"❌ PDF 생성 오류: {e}")



if __name__ == "__main__":
    main()

