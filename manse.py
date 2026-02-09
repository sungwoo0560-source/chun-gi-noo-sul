import streamlit as st
import pandas as pd
import datetime
import requests
import random
import time
import os

# ==============================================================================
# [0] 시스템 설정
# ==============================================================================
st.set_page_config(layout="wide", page_title="대형 서사시 만세력")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&display=swap');
    .stApp { background-color: #fdfdfd; color: #111; font-family: 'Nanum Myeongjo', serif; }
    
    .master-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: #fff; padding: 70px; text-align: center; border-bottom: 8px solid #ffd700;
        margin-bottom: 40px; border-radius: 0 0 40px 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .master-header h1 { font-size: 4.0rem; font-weight: 900; letter-spacing: 5px; margin: 0; }
    
    /* 오행 색상 */
    .오행-목 { background: #4CAF50 !important; color: white !important; }
    .오행-화 { background: #F44336 !important; color: white !important; }
    .오행-토 { background: #FFC107 !important; color: #333 !important; }
    .오행-금 { background: #EEEEEE !important; color: #333 !important; border: 2px solid #999 !important; }
    .오행-수 { background: #2196F3 !important; color: white !important; }
    
    /* 사주 명식표 */
    .saju-box { border: 4px double #2c3e50; padding: 20px; margin-bottom: 30px; background: #fff; box-shadow: 5px 5px 15px rgba(0,0,0,0.1); }
    .saju-grid { display: grid; gap: 0; border: 2px solid #2c3e50; text-align: center; }
    .saju-head { background: #ecf0f1; padding: 12px; border-right: 1px solid #2c3e50; border-bottom: 1px solid #2c3e50; font-weight: bold; font-size: 1.1rem; }
    .saju-body { padding: 25px 10px; font-size: 2.8rem; font-weight: 900; border-right: 1px solid #2c3e50; line-height: 1.2; }
    .saju-foot { background: #fff; padding: 12px; font-size: 0.95rem; color: #555; border-right: 1px solid #2c3e50; border-top: 1px solid #2c3e50; line-height: 1.5; font-weight:bold; }
    .last { border-right: none !important; }
    .highlight-pillar { border: 3px solid #c0392b !important; background-color: #fff3e0 !important; }
    
    /* 60갑자 표 */
    .gapja-container { margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }
    .gapja-title { font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; color: #2c3e50; }
    .gapja-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 5px; max-width: 900px; margin: 0 auto; }
    .gapja-cell { 
        padding: 10px 6px; text-align: center; font-weight: bold; font-size: 0.95rem; line-height: 1.4;
        border-radius: 8px; border: 2px solid rgba(0,0,0,0.1); 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .gapja-cell:hover { transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    
    .report-content { background: #fff; padding: 80px; border: 1px solid #ddd; font-size: 1.3rem; line-height: 2.6; text-align: justify; margin-bottom: 50px; }
    .chapter-title { 
        font-size: 2.4rem; font-weight: 900; color: #2c3e50; 
        border-left: 10px solid #ffd700; padding-left: 20px; margin-top: 80px; margin-bottom: 40px; background-color: #f8f9fa; padding-top: 15px; padding-bottom: 15px;
    }
    .sub-title { font-size: 1.8rem; font-weight: bold; color: #2980b9; margin-top: 50px; margin-bottom: 20px; border-bottom: 3px dashed #ccc; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [1] 음력 라이브러리
# ==============================================================================
HAS_LUNAR = False
try:
    from korean_lunar_calendar import KoreanLunarCalendar
    HAS_LUNAR = True
except ImportError: pass

# ==============================================================================
# [2] 천문연구원 API (만세력)
# ==============================================================================
import xml.etree.ElementTree as ET

class KasiLoader:
    """천문연구원 24절기 API"""
    API_KEY = "cb2437de2fef73ffe9bc6ebd8c23a7420358888768075846c063d39b4955add6"
    URL = "http://apis.data.go.kr/B090041/uli/get24DivisionsInfo"
    
    @staticmethod
    def get_solar_term(year, month):
        try:
            params = {
                'serviceKey': KasiLoader.API_KEY,
                'solYear': str(year),
                'solMonth': f"{month:02d}",
                'numOfRows': 10,
                'type': 'xml'
            }
            res = requests.get(KasiLoader.URL, params=params, timeout=3)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                terms = {}
                for item in root.findall('.//item'):
                    name = item.find('dateKind').text
                    date = int(item.find('locdate').text)
                    terms[name] = date
                return terms
        except:
            return None
        return None

# ==============================================================================
# [3] 사주력 엔진
# ==============================================================================
class SajuEngine:
    """만세력 + 사주력 통합 엔진"""
    
    GAN = ['갑(甲)', '을(乙)', '병(丙)', '정(丁)', '무(戊)', '기(己)', '경(庚)', '신(辛)', '임(壬)', '계(癸)']
    JI = ['자(子)', '축(丑)', '인(寅)', '묘(卯)', '진(辰)', '사(巳)', '오(午)', '미(未)', '신(申)', '유(酉)', '술(戌)', '해(亥)']
    
    OH_MAP = {
        '甲':'목','乙':'목','丙':'화','丁':'화','戊':'토','己':'토','庚':'금','辛':'금','壬':'수','癸':'수',
        '子':'수','丑':'토','寅':'목','卯':'목','辰':'토','巳':'화','午':'화','未':'토','申':'금','酉':'금','戌':'토','亥':'수',
        '갑':'목','을':'목','병':'화','정':'화','무':'토','기':'토','경':'금','신':'금','임':'수','계':'수',
        '자':'수','축':'토','인':'목','묘':'목','진':'토','사':'화','오':'화','미':'토','신':'금','유':'금','술':'토','해':'수'
    }
    
    SIPSIN = {
        '목': {'목':'비견', '화':'식상', '토':'재성', '금':'관성', '수':'인성'},
        '화': {'목':'인성', '화':'비겁', '토':'식상', '금':'재성', '수':'관성'},
        '토': {'목':'관성', '화':'인성', '토':'비겁', '금':'식상', '수':'재성'},
        '금': {'목':'재성', '화':'관성', '토':'인성', '금':'비겁', '수':'식상'},
        '수': {'목':'식상', '화':'재성', '토':'관성', '금':'인성', '수':'비겁'}
    }
    
    UNSEONG = {
        '목': ['목욕','관대','건록','제왕','쇠','병','사','묘','절','태','양','장생'],
        '화': ['태','양','장생','목욕','관대','건록','제왕','쇠','병','사','묘','절'],
        '토': ['태','양','장생','목욕','관대','건록','제왕','쇠','병','사','묘','절'],
        '금': ['사','묘','절','태','양','장생','목욕','관대','건록','제왕','쇠','병'],
        '수': ['제왕','쇠','병','사','묘','절','태','양','장생','목욕','관대','건록']
    }

    @classmethod
    def convert_date(cls, y, m, d, cal_type):
        """음력 → 양력 변환"""
        if cal_type == '양력':
            return y, m, d
        if HAS_LUNAR:
            try:
                cal = KoreanLunarCalendar()
                cal.setLunarDate(y, m, d, cal_type=='윤달')
                return cal.solarYear, cal.solarMonth, cal.solarDay
            except:
                pass
        # 폴백: 대략 30일 더하기
        dt = datetime.date(y, m, d) + datetime.timedelta(days=30 if cal_type=='음력' else 60)
        return dt.year, dt.month, dt.day

    @classmethod
    def calculate(cls, y, m, d, h_idx, gender, time_unknown, cal_type):
        """사주 계산 (년주, 월주, 일주, 시주 + 십신, 십이운성)"""
        sol_y, sol_m, sol_d = cls.convert_date(y, m, d, cal_type)
        
        # 연주
        y_offset = sol_y - 1900
        y_idx = (y_offset + 36) % 60 if sol_m > 2 else (y_offset + 35) % 60
        if sol_m == 2 and sol_d >= 4:
            y_idx = (y_offset + 36) % 60
        
        # 월주
        wol_m = sol_m if sol_d >= 6 else sol_m - 1
        if wol_m <= 0:
            wol_m = 12
        m_base = (y_idx % 10 % 5) * 2 + 2
        m_idx = (m_base + (wol_m - 2 if wol_m >= 2 else 10)) % 10
        
        # 일주
        base = datetime.date(1900, 1, 1)
        curr = datetime.date(sol_y, sol_m, sol_d)
        d_idx = ((curr - base).days + 10) % 60
        
        # 시주 계산
        if time_unknown:
            h_str = "미상"
        else:
            h_gan_idx = ((d_idx % 10 % 5) * 2 + h_idx) % 10
            h_str = cls.GAN[h_gan_idx] + cls.JI[h_idx]
        
        # 사주 기둥 생성
        pillars = {
            '년': {'t': cls.GAN[y_idx%10] + cls.JI[y_idx%12]},
            '월': {'t': cls.GAN[m_idx] + cls.JI[(wol_m+1)%12]},
            '일': {'t': cls.GAN[d_idx%10] + cls.JI[d_idx%12]},
            '시': {'t': h_str}
        }
        
        # 오행 개수 및 일간 추출
        counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
        day_gan = pillars['일']['t'][0]
        day_oh = cls.OH_MAP[day_gan]
        
        # 십신, 십이운성 계산
        for k, v in pillars.items():
            if v['t'] == "미상":
                v.update({'s_sip':'-', 'b_sip':'-', 'unseong':'-', 'han':'(미상)'})
                continue
            
            # 천간, 지지 추출
            g = v['t'][0]  # 첫 글자 (예: '갑')
            j = v['t'][4]  # 다섯번째 글자 (예: '자', '갑(甲)자(子)' 구조)
            
            # 오행 개수
            counts[cls.OH_MAP[g]] += 1
            counts[cls.OH_MAP[j]] += 1
            
            # 한자 표기
            v['han'] = f"{g}({cls.OH_MAP[g]})"
            
            # 십신
            v['s_sip'] = cls.SIPSIN[day_oh][cls.OH_MAP[g]]
            v['b_sip'] = cls.SIPSIN[day_oh][cls.OH_MAP[j]]
            
            # 십이운성
            ji_idx = -1
            for idx, char in enumerate(cls.JI):
                if char in v['t']:
                    ji_idx = idx
                    break
            v['unseong'] = cls.UNSEONG[day_oh][ji_idx % 12] if ji_idx != -1 else "-"
        
        # 대운 계산 (57세부터 100세까지)
        daewun = []
        is_yang = (y_idx % 10) % 2 == 0
        is_man = (gender == "남")
        is_forward = (is_man and is_yang) or (not is_man and not is_yang)
        
        curr = m_idx
        start = 57  # 대운 시작 나이
        
        # 57, 67, 77, 87, 97세 - 5개 대운만 (100세까지)
        for i in range(5):
            if is_forward:
                curr = (curr + 1) % 60
            else:
                curr = (curr - 1) % 60
            
            d_gan = cls.GAN[curr%10]
            d_ji = cls.JI[curr%12]
            
            # 대운의 십신
            d_gan_oh = cls.OH_MAP[d_gan.split('(')[1][0]]
            d_ji_oh = cls.OH_MAP[d_ji.split('(')[1][0]]
            
            daewun.append({
                'age': start + i*10,
                'ganji': d_gan + d_ji,
                's_sip': cls.SIPSIN[day_oh][d_gan_oh],
                'b_sip': cls.SIPSIN[day_oh][d_ji_oh]
            })
        
        return pillars, counts, daewun, day_oh, day_gan, sol_y

# ==============================================================================
# [4] 60갑자 차트 생성
# ==============================================================================
def create_gapja_chart():
    """60갑자 원반 차트 (오행 색상 + 한자)"""
    gan_list = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
    gan_hanja = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    ji_list = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
    ji_hanja = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    oh_colors = {
        '목': '오행-목',
        '화': '오행-화',
        '토': '오행-토',
        '금': '오행-금',
        '수': '오행-수'
    }
    
    gan_oh = ['목','목','화','화','토','토','금','금','수','수']
    
    html = '<div class="gapja-container">'
    html += '<div class="gapja-title">📊 천간지지 60갑자 원반</div>'
    html += '<div class="gapja-grid">'
    
    for i in range(60):
        gan_idx = i % 10
        ji_idx = i % 12
        gan = gan_list[gan_idx]
        gan_h = gan_hanja[gan_idx]
        ji = ji_list[ji_idx]
        ji_h = ji_hanja[ji_idx]
        oh = gan_oh[gan_idx]
        color_class = oh_colors[oh]
        
        # 한글(한자) 형식으로 표시
        html += f'<div class="gapja-cell {color_class}">{gan}({gan_h})<br>{ji}({ji_h})</div>'
    
    html += '</div></div>'
    return html

# ==============================================================================
# [5] 대형 서사 생성기 (30,000자+)
# ==============================================================================
class EpicGenerator:
    """순수 한글로만 30,000자 생성 - 사고수/횡재수/건강 포함"""
    
    @staticmethod
    def generate(user_info, pillars, counts, daewun, topic, day_oh, day_gan):
        """30,000자 대형 서사 - 완전 한글 + 상세 운세"""
        
        name = user_info['name']
        age = user_info['age']
        married = user_info['married']
        has_children = user_info['has_children']
        job = user_info['job']
        
        strong = max(counts, key=counts.get)
        weak = min(counts, key=counts.get)
        p = pillars
        
        # 제목
        text = "="*100 + "\n"
        text += f"【 {name} 님의 운명 대서사시 】\n"
        text += "="*100 + "\n\n"
        text += f"{age}세 | {'기혼' if married else '미혼'}"
        if married:
            text += f" | 자녀 {'있음' if has_children else '없음'}"
        text += f" | {job}\n\n"
        text += "="*100 + "\n\n"
        
        # 제1부: 명식표 (3000자)
        text += "<div class='chapter-title'>제1부. 천간지지 정밀 해부서</div>\n\n"
        text += "<div class='sub-title'>1. 명식표</div>\n\n"
        
        text += f"귀하께서 태어난 그 순간, 하늘과 땅의 기운이 합쳐져 귀하만의 독특한 운명을 만들어냈습니다.\n\n"
        
        text += f"**년주(초년)**: {p['년']['t']}\n"
        text += f"**월주(사회)**: {p['월']['t']}\n"
        text += f"**일주(본인)**: {p['일']['t']} ← 귀하 자신\n"
        text += f"**시주(말년)**: {p['시']['t']}\n\n"
        
        text += "<div class='sub-title'>2. 천간 분석 - 하늘의 뜻</div>\n\n"
        
        ilgan = p['일']['t'][0]
        
        if ilgan in ['병', '丙']:
            text += f"귀하의 일간은 **병화(丙火)**입니다. 귀하는 한낮의 태양입니다. 숨기는 것이 없고 공평무사하며, 열정이 넘칩니다. 뒤끝이 없으나, 순간적인 폭발력은 주변을 압도합니다.\n\n"
            text += "좋으면 미친 듯이 좋고, 싫으면 쳐다보기도 싫은 극단적인 호불호가 귀하의 심장을 지배합니다. 귀하의 말 한마디는 주변 사람들에게 따뜻한 햇살이 되기도 하지만, 때로는 모든 것을 태워버리는 레이저 광선처럼 꽂히기도 합니다.\n\n"
            text += "거짓말을 하지 못하고, 가슴에 담아둔 말은 반드시 뱉어야 직성이 풀리는 이 대쪽 같은 성격은 귀하를 세상에서 가장 투명하고 정직한 사람으로 만들었으나, 동시에 수많은 적을 만들기도 했을 것입니다.\n\n"
        
        elif ilgan in ['정', '丁']:
            text += f"귀하의 일간은 **정화(丁火)**입니다. 귀하는 은은하게 타오르는 촛불이자 밤하늘의 별빛입니다. 내면에는 용광로 같은 열정을 품고 있으며, 집중력이 대단합니다.\n\n"
            text += "겉으로는 조용해 보이지만, 속으로는 끓어오르는 마그마 같은 열정을 품고 있습니다. 한번 마음먹은 일은 끝까지 해내는 끈기가 있으며, 세밀하고 섬세한 작업을 잘합니다.\n\n"
        
        elif ilgan in ['갑', '甲']:
            text += f"귀하의 일간은 **갑목(甲木)**입니다. 귀하는 숲의 제왕인 거목입니다. 하늘을 향해 곧게 뻗어 올라가는 기상은 타의 추종을 불허합니다.\n\n"
            text += "원칙과 정의를 중시하며, 굽히지 않는 강직한 성품을 가졌습니다. 리더십이 강하고 추진력이 있어 조직을 이끄는 능력이 뛰어납니다. 하지만 때로는 융통성이 부족하여 꺾이는 아픔을 겪기도 합니다.\n\n"
        
        elif ilgan in ['을', '乙']:
            text += f"귀하의 일간은 **을목(乙木)**입니다. 귀하는 끈질긴 생명력의 화초이자 덩굴입니다. 태풍에도 꺾이지 않는 유연함과 적응력을 가졌습니다.\n\n"
            text += "부드러우면서도 강한 면모를 지녔으며, 어떤 환경에서도 살아남는 생존력이 뛰어납니다. 사람들과 잘 어울리고, 눈치가 빠르며, 상황 판단 능력이 탁월합니다.\n\n"
        
        elif ilgan in ['무', '戊']:
            text += f"귀하의 일간은 **무토(戊土)**입니다. 귀하는 만물을 포용하는 거대한 산입니다. 묵직하고 믿음직스러워 주변 사람들이 의지하려 합니다.\n\n"
            text += "책임감이 강하고 신뢰할 수 있는 사람입니다. 한번 맡은 일은 끝까지 해내며, 주변 사람들을 잘 챙깁니다. 하지만 때로는 너무 많은 것을 떠안아 힘들어하기도 합니다.\n\n"
        
        elif ilgan in ['기', '己']:
            text += f"귀하의 일간은 **기토(己土)**입니다. 귀하는 어머니 품 같은 비옥한 대지입니다. 무엇이든 심으면 자라나게 하는 포용력과 생산성을 가졌습니다.\n\n"
            text += "다정다감하고 베푸는 것을 좋아합니다. 사람들의 마음을 잘 헤아리고, 화목한 분위기를 만드는 데 능합니다. 하지만 때로는 우유부단하거나 걱정이 많은 모습을 보이기도 합니다.\n\n"
        
        elif ilgan in ['경', '庚']:
            text += f"귀하의 일간은 **경금(庚金)**입니다. 귀하는 다듬어지지 않은 원석이자 바위입니다. 의리에 살고 의리에 죽는 대장부 스타일입니다.\n\n"
            text += "시원시원하고 깔끔한 성격입니다. 옳고 그름이 분명하며, 불의를 보면 참지 못합니다. 결단력이 있고 추진력이 강하지만, 때로는 지나치게 냉정하다는 소리를 듣기도 합니다.\n\n"
        
        elif ilgan in ['신', '辛']:
            text += f"귀하의 일간은 **신금(辛金)**입니다. 귀하는 정교하게 세공된 보석입니다. 예리하고 섬세하며, 깔끔한 완벽주의자입니다.\n\n"
            text += "섬세하고 우아한 취향을 가졌습니다. 미적 감각이 뛰어나고, 세련된 것을 좋아합니다. 예리한 관찰력과 분석력을 가졌지만, 때로는 예민하고 까다롭다는 소리를 듣기도 합니다.\n\n"
        
        elif ilgan in ['임', '壬']:
            text += f"귀하의 일간은 **임수(壬水)**입니다. 귀하는 끝없이 펼쳐진 바다입니다. 지혜가 깊고 총명하며, 스케일이 큽니다.\n\n"
            text += "지혜롭고 포용력이 있습니다. 넓은 시야로 세상을 바라보며, 큰 그림을 그리는 능력이 있습니다. 하지만 때로는 변덕스럽거나 일관성이 없어 보일 수 있습니다.\n\n"
        
        else:  # 계
            text += f"귀하의 일간은 **계수(癸水)**입니다. 귀하는 대지를 적시는 봄비입니다. 조용히 스며들어 만물을 소생시키는 부드러운 카리스마가 있습니다.\n\n"
            text += "조용하지만 깊은 내면을 가졌습니다. 지혜롭고 사려 깊으며, 사람들의 마음을 잘 헤아립니다. 겉으로 드러내지 않지만 강한 의지를 품고 있습니다.\n\n"
        
        # 프롤로그 (3000자)
        text += f"<div class='chapter-title'>프롤로그: 하늘이 정한 운명의 시작</div>\n\n"
        text += f"{name} 님, 귀하께서 이 세상에 태어난 그 순간부터 하늘과 땅의 기운이 합쳐져 귀하만의 독특한 운명을 만들어냈습니다.\n\n"
        text += f"귀하의 사주를 보면, 년주는 {p['년']['t']}, 월주는 {p['월']['t']}, 일주는 {p['일']['t']}, 시주는 {p['시']['t']}로 구성되어 있습니다.\n\n"
        
        text += f"옛 성현들은 말씀하셨습니다. 사람의 운명은 타고난 것이 삼분, 살아가는 것이 칠분이라고 말입니다. 귀하께서 타고난 이 사주팔자는 귀하가 걸어갈 인생의 지도와도 같은 것입니다. 이 지도를 어떻게 읽고, 어떻게 활용하느냐에 따라 귀하의 인생은 완전히 달라질 수 있습니다.\n\n"
        
        text += f"귀하의 일간은 {day_gan}입니다. 이는 {day_oh}의 기운을 타고난 것인데, "
        
        if day_oh == '목':
            text += "나무처럼 곧고 강직한 성품을 가지셨습니다. 봄의 생명력처럼 무엇이든 자라나게 하는 힘이 있으며, 끊임없이 위로 뻗어나가려는 의지가 강합니다. 하지만 때로는 융통성이 부족하여 꺾이는 아픔을 겪기도 합니다."
        elif day_oh == '화':
            text += "불꽃처럼 뜨겁고 열정적인 성품을 가지셨습니다. 여름 햇살처럼 밝고 명랑하며, 주변 사람들에게 따뜻함을 주는 존재입니다. 하지만 때로는 그 뜨거움이 지나쳐 주변을 태워버리거나, 자신마저 소진되는 경우가 있습니다."
        elif day_oh == '토':
            text += "대지처럼 묵직하고 안정적인 성품을 가지셨습니다. 사계절을 품는 땅처럼 모든 것을 포용하고 받아들이는 너그러움이 있으며, 믿음직스러운 존재입니다. 하지만 때로는 변화를 두려워하거나, 너무 많은 것을 떠안아 무거워지기도 합니다."
        elif day_oh == '금':
            text += "쇠붙이처럼 단단하고 예리한 성품을 가지셨습니다. 가을 서리처럼 냉철하고 이성적이며, 의리와 원칙을 중시합니다. 하지만 때로는 지나치게 냉정하여 정이 없어 보이거나, 고집이 세서 주변과 마찰을 빚기도 합니다."
        else:  # 수
            text += "물처럼 유연하고 지혜로운 성품을 가지셨습니다. 겨울 호수처럼 깊고 고요하며, 어디든 스며들어 적응하는 능력이 뛰어납니다. 하지만 때로는 우유부단하여 결정을 내리지 못하거나, 지나치게 소극적인 모습을 보이기도 합니다."
        
        text += "\n\n"
        
        text += f"귀하의 오행을 살펴보면, 목{counts['목']}개, 화{counts['화']}개, 토{counts['토']}개, 금{counts['금']}개, 수{counts['수']}개로 구성되어 있습니다. "
        text += f"이 중에서 {strong}의 기운이 {counts[strong]}개로 가장 강하고, {weak}의 기운이 {counts[weak]}개로 가장 약합니다.\n\n"
        
        text += f"강한 {strong}의 기운은 귀하에게 큰 힘이 되기도 하지만, 때로는 지나쳐서 독이 되기도 합니다. 마치 햇빛이 적당하면 만물을 자라게 하지만, 너무 강하면 모든 것을 말려 죽이는 것과 같은 이치입니다. 반대로 약한 {weak}의 기운은 귀하가 평생 보충하고 키워나가야 할 부분입니다. 이것이 바로 귀하의 용신이 되는 것입니다.\n\n"
        
        text += "이제부터 제가 귀하의 인생을 마치 한 편의 소설처럼 펼쳐 보이겠습니다. 지나온 과거, 현재의 모습, 그리고 다가올 미래까지, 모든 것을 낱낱이 밝혀드리겠습니다.\n\n"
        
        # 제1장: 어린 시절 (4000자)
        text += f"<div class='chapter-title'>제1장. 어린 시절 - 씨앗이 땅에 떨어지다</div>\n\n"
        text += f"<div class='sub-title'>태어나서 열 살까지의 이야기</div>\n\n"
        
        text += f"{name} 님이 이 세상에 태어난 것은 한 알의 씨앗이 땅에 떨어진 것과 같았습니다. 년주는 인생의 뿌리를 의미하는데, 귀하의 년주 {p['년']['t']}는 "
        
        year_sip = p['년']['s_sip']
        if '인성' in year_sip:
            text += "부모님의 사랑과 보살핌 속에서 자랐음을 의미합니다. 어머니께서는 귀하를 매우 소중히 여기셨고, 교육에도 많은 신경을 쓰셨을 것입니다. 어릴 적 귀하는 책을 좋아하는 아이였을 것이며, 어른들의 말씀을 잘 따르는 착한 아이로 자랐을 것입니다."
        elif '비겁' in year_sip:
            text += "형제자매들과의 경쟁 속에서 자랐음을 의미합니다. 부모님의 사랑을 차지하기 위해, 또는 장난감 하나를 차지하기 위해 끊임없이 경쟁했던 기억이 있을 것입니다. 이런 경쟁은 귀하를 강하게 만들었지만, 때로는 외로움을 느끼게도 했을 것입니다."
        elif '재성' in year_sip:
            text += "어린 시절부터 돈에 대한 감각이 남달랐음을 의미합니다. 부모님께서는 물질적으로 여유롭지 않으셨을 수도 있으나, 귀하는 어려서부터 용돈을 아껴 쓰거나, 작은 장사를 해보는 등 경제관념이 뚜렷했을 것입니다."
        elif '관성' in year_sip:
            text += "규칙과 질서 속에서 자랐음을 의미합니다. 부모님이나 선생님의 말씀을 거역하는 것이 두려웠고, 항상 모범적인 아이가 되려고 노력했을 것입니다. 하지만 때로는 그런 압박감이 버거워 몰래 숨어서 울었던 기억도 있을 것입니다."
        else:  # 식상
            text += "자유롭고 창의적인 환경에서 자랐음을 의미합니다. 부모님께서는 귀하의 재능을 인정하고 키워주셨으며, 귀하는 노래하고 춤추고 그림 그리는 것을 좋아하는 아이였을 것입니다."
        
        text += "\n\n"
        
        text += f"유치원이나 초등학교에 다니던 시절, {name} 님은 "
        
        if strong == '목':
            text += "나무처럼 쑥쑥 자라나는 아이었습니다. 키도 반에서 큰 편이었고, 성격도 곧았습니다. 친구들과 놀다가도 부당한 일이 있으면 참지 못하고 나섰으며, 선생님께도 자기 생각을 솔직하게 말하는 아이었습니다. 하지만 때로는 그런 성격 때문에 친구들과 다투기도 했습니다."
        elif strong == '화':
            text += "햇살처럼 밝고 활발한 아이었습니다. 반에서 가장 인기가 많았고, 항상 웃음소리가 끊이지 않았습니다. 장난도 많이 쳤지만, 그 천진난만함에 선생님들도 귀하를 좋아하셨습니다. 하지만 가끔은 너무 산만해서 혼나기도 했습니다."
        elif strong == '토':
            text += "산처럼 묵직하고 느긋한 아이었습니다. 서두르는 법이 없었고, 친구들이 싸우면 중재하는 역할을 했습니다. 선생님 말씀을 잘 듣는 모범생이었지만, 가끔은 너무 느려서 답답하다는 소리를 듣기도 했습니다."
        elif strong == '금':
            text += "쇠붙이처럼 단단하고 강한 아이었습니다. 한번 정한 것은 끝까지 밀고 나갔으며, 규칙을 어기는 것을 용납하지 못했습니다. 시험 성적도 좋았고, 특히 수학을 잘했습니다. 하지만 융통성이 없어서 친구들이 '고지식하다'고 놀리기도 했습니다."
        else:  # 수
            text += "물처럼 조용하고 차분한 아이었습니다. 책 읽기를 좋아했고, 혼자 있는 시간을 즐겼습니다. 친구들과도 잘 어울렸지만, 리더가 되기보다는 따라가는 편이었습니다. 상상력이 풍부해서 이야기를 잘 꾸며냈습니다."
        
        text += "\n\n"
        
        text += f"열 살 무렵, {name} 님에게는 잊을 수 없는 일이 있었을 것입니다. "
        
        if married and not has_children:
            text += "어린 시절 인형을 돌보며 엄마 놀이를 했던 기억이 있을 것입니다. 그때는 '나도 크면 예쁜 아기를 낳아서 잘 키울 거야'라고 생각했을 텐데, 세월이 흘러 지금은 아직 그 꿈을 이루지 못한 상태입니다. 하지만 늦었다고 생각할 때가 가장 빠른 법입니다."
        elif not married:
            text += "반에서 짝사랑하는 친구가 있었을 것입니다. 멀리서 바라만 봐도 가슴이 두근거렸고, 그 친구가 자기를 쳐다보기만 해도 얼굴이 빨개졌습니다. 그때의 그 설렘은 지금도 가슴 한구석에 남아 있을 것입니다."
        
        text += "\n\n"
        
        # 제2장: 청소년기 (4000자)
        text += f"<div class='chapter-title'>제2장. 청소년기 - 폭풍 속을 걷다</div>\n\n"
        text += f"<div class='sub-title'>열한 살부터 스무 살까지의 이야기</div>\n\n"
        
        text += f"중학교에 입학한 {name} 님은 이제 어린아이가 아니었습니다. 신체도 변화하고 마음도 복잡해지는 사춘기를 맞이했습니다.\n\n"
        
        text += f"월주 {p['월']['t']}는 귀하의 청소년기와 청년기를 대표합니다. "
        
        month_sip = p['월']['s_sip']
        if '인성' in month_sip:
            text += "이 시기 귀하는 공부에 몰두했습니다. 부모님의 기대도 컸고, 귀하 스스로도 좋은 성적을 내고 싶었습니다. 밤늦게까지 책상 앞에 앉아 공부하던 모습이 눈에 선합니다. 선생님들은 귀하를 칭찬했고, 귀하는 그 칭찬에 힘입어 더욱 열심히 공부했습니다. 하지만 때로는 그 압박감에 힘들어하기도 했습니다."
        elif '비겁' in month_sip:
            text += "이 시기 귀하는 친구들과의 경쟁에 몰두했습니다. 시험 성적으로, 운동으로, 외모로, 모든 면에서 친구들보다 앞서고 싶었습니다. 때로는 친구가 좋은 성적을 받으면 축하해주면서도 속으로는 배가 아팠습니다. 이런 경쟁심은 귀하를 발전시키기도 했지만, 동시에 외롭게 만들기도 했습니다."
        elif '재성' in month_sip:
            text += "이 시기 귀하는 돈을 벌고 싶었습니다. 친구들이 용돈을 쓰는 것을 보며 부러워했고, 귀하도 나만의 돈을 갖고 싶었습니다. 어쩌면 아르바이트를 시작했을 수도 있습니다. 돈을 벌어본 경험은 귀하를 빨리 어른으로 만들었습니다."
        elif '관성' in month_sip:
            text += "이 시기 귀하는 규칙과 질서를 중시했습니다. 학교 규칙을 어기는 친구들을 이해할 수 없었고, 때로는 그들을 야단치기도 했습니다. 선생님들은 귀하를 학급 반장이나 부반장으로 뽑았고, 귀하는 그 책임감에 밤잠을 설치기도 했습니다."
        else:  # 식상
            text += "이 시기 귀하는 자유를 갈망했습니다. 학교 규칙이 답답했고, 부모님의 간섭이 싫었습니다. 때로는 학교를 빠지고 친구들과 놀러 다니기도 했습니다. 음악을 듣고, 춤을 추고, 그림을 그리는 것이 공부보다 훨씬 재미있었습니다."
        
        text += "\n\n"
        
        text += f"고등학교 시절, {name} 님은 인생의 첫 번째 큰 고비를 맞이했습니다. 대학 입시라는 거대한 벽 앞에서 귀하는 "
        
        if counts[strong] >= 3:
            text += f"강한 {strong}의 기운으로 밀어붙였습니다. 잠을 줄여가며 공부했고, 결국 원하는 결과를 얻어냈을 것입니다. 하지만 그 과정에서 건강을 해치거나, 친구관계가 소원해지는 아픔도 겪었을 것입니다."
        else:
            text += f"약한 {weak}의 기운 때문에 어려움을 겪었습니다. 공부해도 실력이 늘지 않는 것 같았고, 자신감도 떨어졌습니다. 하지만 포기하지 않고 끝까지 노력한 그 경험이 귀하를 성장시켰습니다."
        
        text += "\n\n"
        
        text += f"스무 살 무렵, {name} 님은 드디어 어른이 되었습니다. "
        
        if not married:
            text += "이 시기에 처음으로 진지한 연애를 해봤을 수도 있습니다. 가슴이 뛰고, 밤잠을 설치고, 그 사람 생각에 하루 종일 멍하니 있던 그 시절이 있었을 것입니다. 어쩌면 그 사랑은 이루어지지 못했을 수도 있습니다. 하지만 그 아픔이 귀하를 더 깊은 사람으로 만들었습니다."
        
        text += "\n\n"
        
        # 제3장: 청년기 (5000자)
        text += f"<div class='chapter-title'>제3장. 청년기 - 세상과 맞서다</div>\n\n"
        text += f"<div class='sub-title'>스물한 살부터 서른 살까지의 이야기</div>\n\n"
        
        text += f"이제 {name} 님은 본격적으로 사회생활을 시작했습니다. 대학을 졸업하거나, 혹은 직장에 다니기 시작했습니다.\n\n"
        
        text += f"일주 {p['일']['t']}는 귀하 자신을 의미합니다. 귀하의 정체성, 가치관, 인생관이 모두 여기에 담겨 있습니다. "
        
        text += f"{day_gan}일간으로 태어난 사람은 "
        
        if day_oh == '목':
            text += "나무처럼 곧고 정직합니다. 직장에서도 원칙을 중시하고, 부정한 일은 하지 못합니다. 상사가 부당한 지시를 내리면 정면으로 맞서기도 하는데, 이것이 때로는 승진에 걸림돌이 되기도 합니다. 하지만 그런 귀하의 모습에 동료들은 존경심을 느낍니다."
        elif day_oh == '화':
            text += "불처럼 뜨겁고 열정적입니다. 일에 몰두하면 밤을 새워도 아깝지 않고, 프로젝트에 열정을 쏟습니다. 동료들은 귀하의 에너지에 감탄하지만, 때로는 '조금만 쉬었으면' 하고 걱정하기도 합니다. 하지만 귀하는 쉬는 것을 낭비라고 생각합니다."
        elif day_oh == '토':
            text += "땅처럼 묵직하고 신뢰할 수 있습니다. 시키는 일은 묵묵히 해내고, 맡은 바 책임을 다합니다. 상사들은 귀하를 믿고 중요한 일을 맡기며, 동료들은 귀하와 함께 일하기를 좋아합니다. 하지만 때로는 너무 많은 일을 떠안아 힘들어하기도 합니다."
        elif day_oh == '금':
            text += "쇠붙이처럼 단단하고 예리합니다. 일을 할 때는 완벽을 추구하며, 조금의 실수도 용납하지 않습니다. 분석적이고 논리적이어서 문제 해결 능력이 뛰어나지만, 때로는 너무 냉정하다는 소리를 듣기도 합니다."
        else:  # 수
            text += "물처럼 유연하고 지혜롭습니다. 어떤 상황에서도 적응력이 뛰어나고, 사람들과의 관계도 원만하게 유지합니다. 하지만 때로는 우유부단하여 중요한 결정을 내리지 못해 기회를 놓치기도 합니다."
        
        text += "\n\n"
        
        text += f"이십대 중반, {name} 님은 인생의 중요한 선택의 기로에 섰습니다. "
        
        if job and '프리랜서' in job:
            text += "직장 생활이 답답했습니다. 매일 정해진 시간에 출근하고, 상사의 눈치를 보며 일하는 것이 견딜 수 없었습니다. 결국 귀하는 용기를 내어 독립을 선택했습니다. 프리랜서로서의 삶은 자유로웠지만, 동시에 불안정했습니다. 수입이 일정하지 않아 걱정되는 날도 많았지만, 그래도 귀하는 이 선택을 후회하지 않습니다."
        elif job and ('공무원' in job or '직장' in job):
            text += "안정을 선택했습니다. 주변에서는 도전하라고 했지만, 귀하는 확실한 것을 원했습니다. 직장에 들어가서 월급을 받으며 사는 것이 현명한 선택이라고 생각했습니다. 때로는 '내가 더 큰 꿈을 꾸었어야 했나' 하는 생각이 들기도 하지만, 안정적인 생활에 만족합니다."
        else:
            text += "여러 가지를 고민했습니다. 더 공부를 할까, 취업을 할까, 창업을 할까. 수많은 밤을 고민하며 보냈습니다. 주변 사람들은 이것저것 조언했지만, 결국 결정은 귀하 자신이 내려야 했습니다."
        
        text += "\n\n"
        
        if married:
            text += f"이십대 후반, {name} 님은 운명적인 만남을 가졌습니다. 그 사람과의 만남은 "
            
            if weak == '수':
                text += "물을 만난 사막과 같았습니다. 귀하에게 부족했던 부드러움과 지혜를 채워주는 존재였습니다. 처음에는 '이 사람이다' 싶었습니다. 결혼을 결심했고, 새로운 가정을 꾸렸습니다. "
                
                if has_children:
                    text += "그리고 얼마 후 귀한 자녀를 얻었습니다. 아이를 처음 안았을 때의 그 벅찬 감정을 귀하는 평생 잊지 못할 것입니다. 밤마다 아이가 울어대도, 잠을 설쳐도, 그 모든 것이 행복했습니다."
                else:
                    text += "하지만 아직 자녀는 없습니다. 어쩌면 둘이서만의 시간을 더 갖고 싶었을 수도 있고, 혹은 건강상의 이유로 늦어졌을 수도 있습니다. 하지만 조급해하지 마십시오. 하늘이 정한 때가 있는 법입니다."
            else:
                text += "운명 같았습니다. 하지만 귀하의 강한 기운과 상대방의 기운이 충돌하는 경우도 많았습니다. 결혼 생활이 항상 평탄하지만은 않았을 것입니다. 때로는 크게 싸우고, 이혼을 생각해본 적도 있을 것입니다. 하지만 그때마다 서로를 이해하려 노력하며 위기를 넘겼습니다."
            
            text += "\n\n"
        else:
            text += f"이십대 후반이 되어도 {name} 님은 아직 결혼하지 않았습니다. "
            
            if counts[strong] >= 4:
                text += f"너무 강한 {strong}의 기운 때문에 상대방이 귀하를 감당하기 어려워했을 것입니다. 연애는 해봤지만, 결혼까지 이어지지 못했습니다. '나는 평생 혼자 살게 되는 건 아닐까' 하는 걱정도 들었을 것입니다."
            else:
                text += f"약한 {weak}의 기운 때문에 자신감이 부족했을 것입니다. 마음에 드는 사람이 있어도 먼저 다가가지 못했고, 고백할 용기도 나지 않았습니다. 기회를 놓친 적도 여러 번 있었을 것입니다."
            
            text += "\n\n"
        
        text += f"서른 살 무렵, {name} 님은 돌아보았습니다. 지난 십 년이 마치 꿈같았습니다. "
        text += "이십대는 정말 빨리 지나갔습니다. 때로는 후회되는 선택도 있었고, 때로는 잘했다고 생각되는 결정도 있었습니다. 하지만 그 모든 것이 귀하를 지금의 귀하로 만들었습니다.\n\n"
        
        # 제4장: 중년기 (6000자)
        text += f"<div class='chapter-title'>제4장. 중년기 - 인생의 한가운데서</div>\n\n"
        text += f"<div class='sub-title'>서른한 살부터 현재 {age}세까지의 이야기</div>\n\n"
        
        text += f"서른을 넘긴 {name} 님은 이제 인생의 중반을 걷고 있습니다. 더 이상 젊다고 할 수 없는 나이가 되었지만, 그렇다고 늙었다고 할 수도 없는 애매한 시기입니다.\n\n"
        
        text += f"삼십대 초반, 귀하는 "
        
        if job and job != '무직':
            text += f"{job}로서 자리를 잡아가고 있었습니다. 처음에는 모든 것이 낯설고 어려웠지만, 시간이 지나면서 점점 익숙해졌습니다. 동료들도 생겼고, 나름대로의 노하우도 쌓였습니다. "
            
            if '프리랜서' in job or '자영업' in job:
                text += "자유롭게 일하는 것은 좋았지만, 수입이 불안정한 것이 늘 걱정거리였습니다. 돈이 잘 벌리는 달도 있었지만, 한 푼도 못 버는 달도 있었습니다. 그럴 때마다 '직장에 다니는 게 나았을까' 하는 생각이 들기도 했습니다."
            else:
                text += "안정적인 수입이 있다는 것은 큰 축복이었습니다. 매달 정해진 날짜에 월급이 들어오는 것만으로도 감사했습니다. 하지만 때로는 단조로운 일상이 지겹게 느껴지기도 했습니다."
        else:
            text += "일자리를 찾지 못하고 있었습니다. 이력서를 넣어도 번번이 떨어졌고, 면접을 봐도 좋은 결과가 없었습니다. 자존심도 상했고, 자신감도 떨어졌습니다. '나는 왜 이렇게 안 되는 걸까' 하는 생각에 우울해지기도 했습니다. "
            
            if counts[weak] == 0:
                text += f"이는 귀하의 오행에 {weak}이 전혀 없기 때문입니다. {weak}의 기운은 유연함과 적응력을 의미하는데, 이것이 부족하니 사회생활이 어려운 것입니다. 하지만 걱정하지 마십시오. {weak}의 기운을 보충하는 방법이 있습니다."
        
        text += "\n\n"
        
        text += f"삼십대 중반, {name} 님에게는 큰 시련이 찾아왔을 것입니다. "
        
        if married:
            text += "부부 사이에 위기가 왔거나, "
            if has_children:
                text += "자녀 교육 문제로 고민이 많았을 것입니다. 아이가 사춘기에 접어들면서 말을 듣지 않고, 반항하기 시작했습니다. '내가 뭘 잘못 키웠나' 하는 자책감도 들었을 것입니다. "
        
        text += "건강에도 적신호가 켜지기 시작했습니다. "
        
        if counts['화'] >= 3:
            text += "화의 기운이 너무 강해서 혈압이 올라가거나, 심장이 두근거리는 증상이 나타났을 것입니다. 스트레스를 받으면 얼굴이 빨개지고, 뒷목이 뻣뻣해지는 것을 느꼈을 것입니다. 화병이 올라와서 가슴이 답답한 적도 많았을 것입니다."
        elif counts['금'] >= 3:
            text += "금의 기운이 너무 강해서 폐나 대장에 문제가 생겼을 것입니다. 기침이 오래가거나, 감기가 쉽게 낫지 않았습니다. 피부도 건조해지고, 변비에 시달리기도 했습니다."
        elif counts['수'] >= 3:
            text += "수의 기운이 너무 강해서 신장이나 방광이 약해졌을 것입니다. 소변을 자주 보거나, 허리가 아픈 증상이 나타났습니다. 추위를 많이 타고, 손발이 차가운 것도 수 기운이 과한 탓입니다."
        elif counts['목'] >= 3:
            text += "목의 기운이 너무 강해서 간이나 담낭에 무리가 갔을 것입니다. 쉽게 화를 내고, 스트레스를 잘 받았습니다. 눈도 침침해지고, 근육이 자주 뭉쳤습니다."
        else:  # 토
            text += "토의 기운이 너무 강해서 비장이나 위장이 약해졌을 것입니다. 소화가 잘 안 되고, 속이 더부룩한 느낌이 자주 들었습니다. 살도 찌기 쉬워서 다이어트가 평생 과제가 되었습니다."
        
        text += "\n\n"
        
        text += f"사십대에 접어들면서, {name} 님은 인생에 대해 깊이 생각하기 시작했습니다. '나는 지금까지 무엇을 하며 살아왔나' '앞으로 남은 인생을 어떻게 살아야 하나' 이런 질문들이 머릿속을 떠나지 않았습니다.\n\n"
        
        if age >= 45:
            text += f"사십대 중반, {name} 님은 "
            
            if married and has_children:
                text += "자녀가 성장해서 독립하는 것을 지켜봤습니다. 기쁘기도 했지만, 한편으로는 허전하기도 했습니다. 그동안 자녀에게 쏟았던 정성과 시간을 이제 어디에 써야 할지 막막했습니다. "
            
            text += "노후를 준비해야 한다는 생각이 간절해졌습니다. 건강도 챙겨야 하고, 돈도 모아야 했습니다. 하지만 현실은 그리 녹록지 않았습니다.\n\n"
        
        if age >= 50:
            text += f"오십대에 접어든 {name} 님은 인생의 오후를 맞이했습니다. "
            
            text += "더 이상 젊다고 할 수 없는 나이가 되었습니다. 거울을 볼 때마다 늘어난 주름과 새치가 눈에 들어왔습니다. 체력도 예전 같지 않았습니다. 조금만 무리해도 며칠씩 피곤이 가시지 않았습니다.\n\n"
            
            text += "하지만 오십대는 또 다른 의미의 황금기이기도 합니다. 인생의 경험이 쌓였고, 세상을 바라보는 안목도 깊어졌습니다. 젊었을 때는 몰랐던 것들을 이제는 알게 되었습니다.\n\n"
        
        text += f"그리고 지금, {age}세의 {name} 님은 "
        
        if married:
            text += f"배우자와 함께 "
            if has_children:
                text += "자녀들을 생각하며 "
        else:
            text += "홀로 "
        
        text += f"인생의 이 지점에 서 있습니다. 지나온 길을 돌아보면 아쉬움도 많고, 후회도 있습니다. 하지만 그 모든 것이 귀하를 지금의 귀하로 만들었습니다.\n\n"
        
        # 제5장: 대운 풀이 (대폭 확장 - 10,000자 이상)
        text += f"<div class='chapter-title'>제5장. 대운 - 십 년마다 펼쳐지는 운명의 장</div>\n\n"
        text += f"<div class='sub-title'>57세부터 시작되는 인생의 대전환</div>\n\n"
        
        text += f"{name} 님, 사주에서 대운은 인생의 큰 물결과 같습니다. 십 년마다 바뀌는 이 대운은 귀하의 인생에 봄, 여름, 가을, 겨울을 가져옵니다. 어떤 대운에서는 만사형통하여 하는 일마다 술술 풀리고, 어떤 대운에서는 모든 것이 막혀 답답하기만 합니다.\n\n"
        
        text += "귀하의 대운은 57세부터 시작됩니다. 이는 인생의 후반부, 노년기에 접어드는 시점입니다. 어떤 이들은 이 나이에 은퇴를 준비하지만, 어떤 이들은 바로 이 나이에 인생의 제2막을 열기도 합니다. 귀하는 어떤 길을 택하시겠습니까?\n\n"
        
        text += "자, 이제 귀하의 대운을 하나하나 펼쳐보겠습니다. 각 대운마다 조심해야 할 해, 기회가 올 해, 그리고 삼재수와 사고수를 모두 알려드리겠습니다.\n\n"
        
        current_year = 2026
        birth_year = current_year - age
        
        for i, dae in enumerate(daewun, 1):
            age_start = dae['age']
            age_end = age_start + 9
            year_start = birth_year + age_start
            year_end = birth_year + age_end
            
            text += f"<div class='sub-title'>{i}. {age_start}세~{age_end}세 대운: {dae['ganji']} ({year_start}년~{year_end}년)</div>\n\n"
            
            # 대운 간지 상세 설명
            gan_char = dae['ganji'][0:3]  # '갑(甲)'
            ji_char = dae['ganji'][4:7]   # '자(子)'
            
            text += f"이 대운은 천간 {gan_char}과 지지 {ji_char}가 지배합니다. 천간은 하늘의 기운으로 겉으로 드러나는 운세를, 지지는 땅의 기운으로 속으로 작용하는 운명을 관장합니다.\n\n"
            
            gan_oh = SajuEngine.OH_MAP[gan_char[0]]
            ji_oh = SajuEngine.OH_MAP[ji_char[0]]
            
            # 길흉 판단
            if gan_oh == weak or ji_oh == weak:
                is_good = True
                text += f"**【 길운대운(吉運大運) 】**\n\n"
                text += f"이 대운은 귀하께 큰 축복을 가져다줄 것입니다. 귀하께서 부족했던 {weak}의 기운이 천간 {gan_oh}과 지지 {ji_oh}를 통해 보충되기 때문입니다. 마치 메마른 대지에 단비가 내리듯, 귀하의 인생에 활력이 돌아올 것입니다.\n\n"
            elif gan_oh == strong or ji_oh == strong:
                is_good = False
                text += f"**【 흉운대운(凶運大運) 】**\n\n"
                text += f"이 대운은 귀하께 시련을 가져올 것입니다. 이미 넘치는 {strong}의 기운이 더욱 강해져 균형이 무너지기 때문입니다. 마치 한여름에 불을 더 지피는 것처럼, 모든 것이 과열되어 탈이 날 수 있습니다.\n\n"
            else:
                is_good = None
                text += f"**【 평운대운(平運大運) 】**\n\n"
                text += f"이 대운은 특별히 좋지도, 나쁘지도 않은 평범한 십 년이 될 것입니다. 큰 사고도, 큰 횡재도 없는 무난한 시기입니다. 하지만 평범함이야말로 가장 큰 축복입니다.\n\n"
            
            # 시기별 운세 (10년을 세분화)
            text += f"**{age_start}세 ({year_start}년) - 대운의 시작**\n\n"
            text += f"이 해는 새로운 대운이 시작되는 해입니다. 마치 계절이 바뀌듯, 귀하의 인생에도 큰 변화가 찾아옵니다. "
            if is_good:
                text += f"좋은 대운의 시작이니 이 해부터 기회를 잡으십시오. {year_start}년은 귀하 인생의 새로운 장이 열리는 해입니다."
            elif is_good is False:
                text += f"힘든 대운의 시작이니 마음을 단단히 먹고 대비하십시오. {year_start}년은 시련이 시작되는 해입니다."
            else:
                text += f"평범한 대운의 시작이니 차분히 일상을 지켜나가십시오."
            text += "\n\n"
            
            text += f"**{age_start+2}세 ({year_start+2}년) - 조심해야 할 해**\n\n"
            text += f"이 해는 특히 조심해야 합니다. 사고수가 있는 해입니다. "
            if ji_oh in ['금', '목']:
                text += f"교통사고나 낙상사고를 조심하십시오. 특히 금속으로 된 도구나 기계를 다룰 때 극도로 주의해야 합니다. 차를 운전할 때도 방어운전을 하고, 술을 마신 후에는 절대로 운전하지 마십시오. 높은 곳에서 작업할 때도 안전장비를 반드시 착용하십시오."
            elif ji_oh in ['수', '화']:
                text += f"물과 불 관련 사고를 조심하십시오. 수영하거나 등산할 때 특히 주의하고, 불을 다룰 때도 각별히 조심하십시오. 전기 화재나 가스 폭발 같은 사고에도 대비해야 합니다."
            else:
                text += f"소화기 질환이나 근골격계 질환을 조심하십시오. 과식하지 말고, 무리한 운동은 피하십시오."
            text += f" {year_start+2}년은 한 해 내내 조심하며 보내야 합니다.\n\n"
            
            text += f"**{age_start+3}세~{age_start+4}세 ({year_start+3}년~{year_start+4}년) - 삼재수(三災數)**\n\n"
            text += f"이 2년은 삼재가 드는 시기입니다. 삼재란 하늘과 땅과 사람에게서 오는 세 가지 재앙을 뜻합니다. 이 기간에는 뜻하지 않은 사고, 질병, 재물 손실이 생길 수 있습니다.\n\n"
            text += f"하지만 두려워할 필요는 없습니다. 삼재를 피하는 방법이 있습니다. 첫째, 삼재를 맞는 해 초에 사찰이나 교회에 가서 기도하고 마음을 정화하십시오. 둘째, 위험한 일을 피하고 조용히 지내십시오. 투자나 사업 확장 같은 큰 결정은 미루십시오. 셋째, 건강검진을 받고 건강을 미리 챙기십시오.\n\n"
            text += f"특히 {year_start+3}년에는 돌다리도 두드려 가며 조심해야 합니다. {year_start+4}년에는 조금 나아지지만 여전히 방심하지 마십시오.\n\n"
            
            text += f"**{age_start+5}세 ({year_start+5}년) - 중반기**\n\n"
            text += f"대운의 중간 지점입니다. "
            if is_good:
                text += f"좋은 대운의 절정기입니다. 지금까지 쌓아온 노력의 결실을 맺는 해입니다. {year_start+5}년은 귀하의 인생에서 가장 빛나는 해 중 하나가 될 것입니다. 이 기회를 놓치지 마십시오."
            elif is_good is False:
                text += f"힘든 대운의 한가운데입니다. 지치고 힘들겠지만, 이제 반은 지났습니다. 조금만 더 견디십시오. {year_start+5}년이 지나면 서서히 좋아질 것입니다."
            else:
                text += f"평범한 일상이 이어집니다. 특별한 일은 없지만, 그것이 바로 행복입니다."
            text += "\n\n"
            
            if '재성' in dae['s_sip'] or '재성' in dae['b_sip']:
                text += f"**{age_start+6}세 ({year_start+6}년) - 횡재수(橫財數)**\n\n"
                text += f"이 해는 귀하께 큰 재물운이 있습니다. 재성 대운의 특성상 돈이 들어올 가능성이 높습니다. 뜻하지 않은 보너스를 받거나, 투자 수익이 생기거나, 사업이 크게 성공할 수 있습니다.\n\n"
                text += f"만약 부동산을 매입할 계획이 있다면 {year_start+6}년이 적기입니다. 주식이나 펀드에 투자해도 좋은 결과가 있을 것입니다. 하지만 욕심을 부리지는 마십시오. 적당한 선에서 만족하는 지혜가 필요합니다.\n\n"
                text += f"복권이나 경품 당첨의 가능성도 있습니다. 이 해에는 작은 행운들이 계속 따를 것입니다.\n\n"
            
            text += f"**{age_start+8}세~{age_start+9}세 ({year_start+8}년~{year_start+9}년) - 대운의 마무리**\n\n"
            text += f"대운이 저물어갑니다. 다음 대운을 준비해야 할 시기입니다. "
            if is_good and (i < len(daewun)):
                next_dae = daewun[i] if i < len(daewun) else None
                if next_dae:
                    next_gan_oh = SajuEngine.OH_MAP[next_dae['ganji'][0]]
                    next_ji_oh = SajuEngine.OH_MAP[next_dae['ganji'][4]]
                    if next_gan_oh == strong or next_ji_oh == strong:
                        text += f"아쉽게도 다음 대운은 힘든 대운입니다. 지금 좋은 대운일 때 재물과 건강을 미리 챙겨두십시오. 지금 벌어둔 돈이 다음 대운을 견디는 밑천이 됩니다."
                    else:
                        text += f"다행히 다음 대운도 나쁘지 않습니다. 계속 좋은 흐름이 이어질 것입니다."
            elif is_good is False and (i < len(daewun)):
                next_dae = daewun[i] if i < len(daewun) else None
                if next_dae:
                    next_gan_oh = SajuEngine.OH_MAP[next_dae['ganji'][0]]
                    next_ji_oh = SajuEngine.OH_MAP[next_dae['ganji'][4]]
                    if next_gan_oh == weak or next_ji_oh == weak:
                        text += f"다행히 다음 대운은 좋은 대운입니다. 조금만 더 견디면 좋은 날이 올 것입니다. 희망을 잃지 마십시오."
                    else:
                        text += f"다음 대운도 힘들 수 있습니다. 하지만 시련은 귀하를 더 강하게 만듭니다."
            text += "\n\n"
            
            # 십신으로 본 세부 운세
            text += f"**【 십신으로 본 운세 】**\n\n"
            text += f"이 대운의 십신은 천간 {dae['s_sip']}, 지지 {dae['b_sip']}입니다.\n\n"
            
            if '재성' in dae['s_sip'] or '재성' in dae['b_sip']:
                text += f"**재성(財星)**은 돈과 재물의 별입니다. 이 대운 십 년 동안 귀하께는 재물을 모을 기회가 많이 생깁니다. 직장인이라면 연봉이 오르고, 사업가라면 매출이 늘어나며, 프리랜서라면 의뢰가 많아집니다.\n\n"
                text += f"하지만 재성이 강하다는 것은 지출도 많다는 뜻입니다. 돈이 들어오는 만큼 나가는 돈도 많습니다. 자녀 교육비, 집 수리비, 경조사비 등으로 목돈이 나갈 수 있습니다. 계획적으로 저축하고, 불필요한 지출을 줄여야 합니다.\n\n"
                text += f"또한 재성은 아내(혹은 남편)의 별이기도 합니다. 배우자와의 관계에 변화가 생길 수 있습니다. 좋은 방향이든 나쁜 방향이든 간에 말입니다.\n\n"
            
            elif '관성' in dae['s_sip'] or '관성' in dae['b_sip']:
                text += f"**관성(官星)**은 명예와 권력의 별입니다. 이 대운 십 년 동안 귀하께는 사회적 지위가 상승할 기회가 생깁니다. 승진하거나, 좋은 자리로 이동하거나, 상을 받거나, 인정받게 됩니다.\n\n"
                text += f"하지만 관성이 강하다는 것은 책임과 압박도 커진다는 뜻입니다. 높은 자리에 올라갈수록 감당해야 할 일이 많아지고, 스트레스도 커집니다. 건강을 해칠 수 있으니 무리하지 마십시오.\n\n"
                text += f"또한 관성은 자녀(특히 아들)의 별이기도 합니다. 자녀와 관련된 일이 생길 수 있습니다.\n\n"
            
            elif '인성' in dae['s_sip'] or '인성' in dae['b_sip']:
                text += f"**인성(印星)**은 학문과 지혜의 별입니다. 이 대운 십 년 동안 귀하께는 배우고 공부하고 싶은 마음이 강해집니다. 자격증을 따거나, 대학원에 진학하거나, 취미로 공부를 시작할 수 있습니다.\n\n"
                text += f"정신적으로 성장하는 시기입니다. 책을 많이 읽고, 좋은 사람들과 교류하며, 인생의 지혜를 얻게 됩니다. 종교나 철학에 관심을 갖게 될 수도 있습니다.\n\n"
                text += f"하지만 인성이 강하면 너무 머리로만 생각하고 실천이 부족해질 수 있습니다. 아는 것만큼 실천하는 것이 중요합니다.\n\n"
            
            elif '식상' in dae['s_sip'] or '식상' in dae['b_sip']:
                text += f"**식상(食傷)**은 표현과 창조의 별입니다. 이 대운 십 년 동안 귀하께는 자신을 표현하고 싶은 욕구가 강해집니다. 글을 쓰거나, 말을 하거나, 무언가를 만들거나, 예술 활동을 하게 됩니다.\n\n"
                text += f"창의적인 아이디어가 샘솟고, 새로운 것을 시도하고 싶어집니다. 사업을 시작하거나, 부업을 하거나, 새로운 분야에 도전할 수 있습니다.\n\n"
                text += f"하지만 식상이 강하면 말이 많아져 실수하기 쉽습니다. 함부로 말하지 말고, 신중하게 행동하십시오. 또한 자녀(특히 딸)와 관련된 일이 생길 수 있습니다.\n\n"
            
            else:  # 비겁
                text += f"**비겁(比劫)**은 경쟁과 독립의 별입니다. 이 대운 십 년 동안 귀하께는 경쟁 상황이 많이 생깁니다. 직장에서 동료와 경쟁하거나, 사업에서 경쟁사와 겨루거나, 형제자매와 갈등이 생길 수 있습니다.\n\n"
                text += f"또한 독립하고 싶은 마음도 강해집니다. 직장을 그만두고 창업하거나, 부모님 곁을 떠나 독립하거나, 이혼하여 혼자 살고 싶어질 수 있습니다.\n\n"
                text += f"비겁이 강하면 재물을 나눠야 하는 일이 생깁니다. 돈을 빌려주거나, 재산을 분할하거나, 손재수가 있을 수 있습니다. 돈 관리를 철저히 하십시오.\n\n"
            
            text += f"{'='*80}\n\n"
        
        # 애운방지법 추가
        text += f"<div class='sub-title'>애운방지법(厄運防止法)</div>\n\n"
        text += f"대운이 좋지 않을 때, 또는 사고수와 삼재수가 있을 때, 액운을 막는 방법이 있습니다.\n\n"
        text += f"**1. 사찰 기도**: 매년 초하루나 보름에 사찰을 방문하여 부처님께 기도하십시오. 마음을 정화하고 액운을 물리칠 수 있습니다.\n\n"
        text += f"**2. 시주와 보시**: 어려운 사람들을 돕고 베푸십시오. 자선단체에 기부하거나, 길에서 만난 노숙자에게 밥을 사주십시오. 덕을 쌓으면 액운이 물러갑니다.\n\n"
        text += f"**3. 건강관리**: 평소에 건강을 잘 챙기십시오. 정기적으로 건강검진을 받고, 운동하고, 잘 먹고, 충분히 자십시오. 건강한 몸에는 액운이 침범하지 못합니다.\n\n"
        text += f"**4. 말조심**: 함부로 말하지 마십시오. 말 한마디가 화근이 됩니다. 특히 술 마신 자리에서 말을 조심하십시오.\n\n"
        text += f"**5. 조용히 지내기**: 액운이 있는 해에는 큰일을 벌이지 마십시오. 투자, 사업 확장, 이직, 이사 등 큰 변화는 미루고 조용히 일상을 지키십시오.\n\n"
        
        text += "\n"
        
        # 제6장: 건강 (4000자)
        text += f"<div class='chapter-title'>제6장. 건강 - 몸이 보내는 신호</div>\n\n"
        text += f"<div class='sub-title'>오행으로 보는 건강 운세</div>\n\n"
        
        text += f"{name} 님, 귀하의 건강은 오행의 균형과 직결되어 있습니다. 오행이 조화롭지 못하면 몸에 병이 생기고, 오행이 조화로우면 건강하게 오래 살 수 있습니다.\n\n"
        
        text += "귀하의 오행 구성을 다시 살펴보겠습니다.\n\n"
        
        for oh_name in ['목', '화', '토', '금', '수']:
            cnt = counts[oh_name]
            text += f"**{oh_name} 오행: {cnt}개**\n\n"
            
            if oh_name == '목':
                organs = "간, 담낭, 눈, 손톱, 근육"
                if cnt == 0:
                    text += f"목의 기운이 전혀 없습니다. {organs}이 약합니다. 눈이 쉽게 피로해지고, 근육이 자주 뭉칩니다. 화를 잘 내고, 스트레스를 잘 받습니다. 봄철에 특히 건강이 안 좋아집니다. 신 음식을 많이 먹고, 녹색 채소를 자주 먹어야 합니다. 아침 일찍 일어나서 산책하는 것도 좋습니다."
                elif cnt >= 3:
                    text += f"목의 기운이 너무 강합니다. {organs}에 과부하가 걸립니다. 간에 열이 많아 얼굴이 붉고, 눈이 충혈됩니다. 화를 잘 내고, 참을성이 부족합니다. 술을 절대로 많이 마시지 마십시오. 새벽에 자고, 아침을 거르는 습관도 간을 망칩니다. 규칙적인 생활과 충분한 수면이 필요합니다."
                else:
                    text += f"목의 기운이 적당합니다. {organs}이 대체로 건강합니다. 하지만 방심하지 말고, 평소에 신경 써서 관리해야 합니다."
            
            elif oh_name == '화':
                organs = "심장, 소장, 혀, 혈관"
                if cnt == 0:
                    text += f"화의 기운이 전혀 없습니다. {organs}이 약합니다. 손발이 차갑고, 혈액순환이 잘 안 됩니다. 얼굴색이 창백하고, 기운이 없어 보입니다. 여름철에 특히 기력이 떨어집니다. 쓴 음식을 먹고, 빨간색 음식을 자주 먹어야 합니다. 따뜻한 차를 자주 마시고, 가벼운 운동으로 몸을 데우는 것이 좋습니다."
                elif cnt >= 3:
                    text += f"화의 기운이 너무 강합니다. {organs}에 무리가 갑니다. 심장이 두근거리고, 혈압이 높습니다. 얼굴이 쉽게 빨개지고, 화를 잘 냅니다. 불면증이 있거나, 가슴이 답답한 증상이 있습니다. 차갑고 시원한 음식을 먹고, 흥분하지 않도록 마음을 다스려야 합니다. 명상이나 요가가 도움이 됩니다."
                else:
                    text += f"화의 기운이 적당합니다. {organs}이 대체로 건강합니다. 하지만 스트레스를 받으면 심장에 무리가 갈 수 있으니 주의하십시오."
            
            elif oh_name == '토':
                organs = "비장, 위장, 입술, 살"
                if cnt == 0:
                    text += f"토의 기운이 전혀 없습니다. {organs}이 약합니다. 소화가 잘 안 되고, 식욕이 없습니다. 입맛이 없어 밥을 거르는 일이 많고, 그러다 보니 몸이 말라갑니다. 환절기에 특히 소화기 질환이 생깁니다. 단 음식을 먹고, 노란색 음식을 자주 먹어야 합니다. 규칙적으로 식사하고, 천천히 씹어 먹는 습관이 중요합니다."
                elif cnt >= 3:
                    text += f"토의 기운이 너무 강합니다. {organs}에 부담이 갑니다. 소화는 잘 되지만 너무 잘 되어서 문제입니다. 식욕이 왕성해서 과식하기 쉽고, 살이 찌기 쉽습니다. 속이 더부룩하고, 트림이 자주 나옵니다. 단 음식을 줄이고, 과식하지 않도록 조심해야 합니다. 식사 후 가벼운 산책이 좋습니다."
                else:
                    text += f"토의 기운이 적당합니다. {organs}이 대체로 건강합니다. 하지만 과식하면 금방 탈이 나니 적당히 먹어야 합니다."
            
            elif oh_name == '금':
                organs = "폐, 대장, 코, 피부"
                if cnt == 0:
                    text += f"금의 기운이 전혀 없습니다. {organs}이 약합니다. 기침을 자주 하고, 감기에 자주 걸립니다. 코가 자주 막히고, 피부가 거칠고 건조합니다. 가을철에 특히 호흡기 질환이 생깁니다. 매운 음식을 먹고, 흰색 음식을 자주 먹어야 합니다. 환기를 자주 하고, 공기 좋은 곳에서 심호흡하는 것이 좋습니다."
                elif cnt >= 3:
                    text += f"금의 기운이 너무 강합니다. {organs}이 너무 건조해집니다. 기침이 마르고, 피부가 갈라집니다. 변비가 생기기 쉽고, 코피가 나기도 합니다. 매운 음식을 줄이고, 촉촉한 음식을 먹어야 합니다. 물을 자주 마시고, 보습에 신경 써야 합니다."
                else:
                    text += f"금의 기운이 적당합니다. {organs}이 대체로 건강합니다. 하지만 미세먼지가 많은 날은 외출을 삼가는 것이 좋습니다."
            
            else:  # 수
                organs = "신장, 방광, 귀, 뼈"
                if cnt == 0:
                    text += f"수의 기운이 전혀 없습니다. {organs}이 약합니다. 소변을 자주 보거나, 허리가 자주 아픕니다. 귀가 잘 안 들리고, 뼈가 약해 골다공증이 생기기 쉽습니다. 겨울철에 특히 건강이 안 좋아집니다. 짠 음식을 먹고, 검은색 음식을 자주 먹어야 합니다. 따뜻하게 입고, 허리를 보호해야 합니다."
                elif cnt >= 3:
                    text += f"수의 기운이 너무 강합니다. {organs}이 너무 차가워집니다. 소변이 맑고 자주 마렵습니다. 몸이 붓고, 추위를 많이 탑니다. 짠 음식을 줄이고, 따뜻한 음식을 먹어야 합니다. 몸을 따뜻하게 하고, 반신욕이나 족욕을 자주 하는 것이 좋습니다."
                else:
                    text += f"수의 기운이 적당합니다. {organs}이 대체로 건강합니다. 하지만 찬물을 많이 마시지 않도록 주의하십시오."
            
            text += "\n\n"
        
        # 제7장: 개운법 (5000자)
        text += f"<div class='chapter-title'>제7장. 개운법 - 운명을 바꾸는 방법</div>\n\n"
        text += f"<div class='sub-title'>용신을 활용한 실천 지침</div>\n\n"
        
        text += f"{name} 님, 이제 가장 중요한 부분을 말씀드리겠습니다. 바로 귀하의 운명을 바꾸는 방법입니다.\n\n"
        
        text += f"귀하의 용신은 **{weak}**입니다. 용신이란 귀하에게 가장 필요한 기운이며, 이것을 보충하면 운이 트이기 시작합니다.\n\n"
        
        colors = {'목':'녹색', '화':'빨강', '토':'황색', '금':'흰색', '수':'검정'}
        directions = {'목':'동쪽', '화':'남쪽', '토':'중앙', '금':'서쪽', '수':'북쪽'}
        numbers = {'목':'3,8', '화':'2,7', '토':'5,10', '금':'4,9', '수':'1,6'}
        
        text += f"<div class='sub-title'>1. 색깔로 보충하기</div>\n\n"
        text += f"**{colors[weak]}색**을 많이 사용하십시오.\n\n"
        text += f"옷을 살 때, 신발을 살 때, 가방을 살 때, 핸드폰 케이스를 고를 때, 항상 {colors[weak]}색을 우선적으로 선택하십시오. 집안 인테리어도 {colors[weak]}색을 많이 사용하는 것이 좋습니다. 커튼, 벽지, 쿠션, 이불 등을 {colors[weak]}색으로 바꿔보십시오.\n\n"
        
        text += f"만약 {colors[weak]}색이 마음에 들지 않는다면, 속옷이라도 {colors[weak]}색으로 입으십시오. 겉으로 보이지 않아도 몸에 닿아 있으면 기운을 받을 수 있습니다.\n\n"
        
        text += f"<div class='sub-title'>2. 방향으로 보충하기</div>\n\n"
        text += f"**{directions[weak]}쪽**으로 이동하십시오.\n\n"
        text += f"이사를 간다면 지금 사는 곳에서 {directions[weak]}쪽으로 가십시오. 여행을 간다면 {directions[weak]}쪽 지방으로 가십시오. 사무실에서 자리를 정한다면 {directions[weak]}쪽 자리를 선택하십시오.\n\n"
        
        text += f"집 안에서도 {directions[weak]}쪽 방을 귀하의 방으로 쓰는 것이 좋습니다. 잠을 잘 때도 머리를 {directions[weak]}쪽으로 두고 자는 것이 좋습니다. 책상도 {directions[weak]}쪽을 향하도록 배치하십시오.\n\n"
        
        text += f"<div class='sub-title'>3. 숫자로 보충하기</div>\n\n"
        text += f"**{numbers[weak]}**을 귀하의 행운의 숫자로 삼으십시오.\n\n"
        text += f"전화번호 끝자리, 차 번호, 집 주소, 계좌 번호 등에 {numbers[weak]}이 들어가도록 하십시오. 복권을 산다면 {numbers[weak]}이 들어간 번호를 선택하십시오.\n\n"
        
        text += f"<div class='sub-title'>4. 음식으로 보충하기</div>\n\n"
        
        if weak == '목':
            text += "**신 음식**을 많이 드십시오. 레몬, 매실, 식초, 귤, 오렌지 등 신맛이 나는 음식이 좋습니다. 채소도 많이 드십시오. 특히 녹색 채소가 좋습니다. 샐러드, 나물, 쌈 등을 자주 드십시오. 아침을 꼭 드시고, 일찍 일어나는 습관을 들이십시오."
        elif weak == '화':
            text += "**쓴 음식**을 많이 드십시오. 쓴오이, 고추, 커피 등 쓴맛이 나는 음식이 좋습니다. 고기도 드십시오. 특히 양고기, 염소고기가 좋습니다. 매운 음식도 좋으니 고추, 후추, 마늘 등을 많이 드십시오. 낮에 활동을 많이 하고, 햇볕을 많이 쬐십시오."
        elif weak == '토':
            text += "**단 음식**을 적당히 드십시오. 과일, 꿀, 고구마, 호박 등 단맛이 나는 음식이 좋습니다. 곡식도 많이 드십시오. 쌀밥, 잡곡밥을 꼭 챙겨 드십시오. 규칙적으로 식사하고, 천천히 씹어 먹는 습관이 중요합니다."
        elif weak == '금':
            text += "**매운 음식**을 적당히 드십시오. 무, 파, 생강, 양파 등 매운맛이 나는 음식이 좋습니다. 흰색 음식도 좋으니 두부, 우유, 백미, 양배추 등을 드십시오. 심호흡을 자주 하고, 공기 좋은 곳에서 산책하십시오."
        else:  # 수
            text += "**짠 음식**을 적당히 드십시오. 미역, 김, 다시마 등 바다에서 나는 음식이 좋습니다. 검은색 음식도 좋으니 검은콩, 검은깨, 흑미 등을 드십시오. 물을 자주 마시고, 허리를 따뜻하게 하십시오."
        
        text += "\n\n"
        
        text += f"<div class='sub-title'>5. 직업으로 보충하기</div>\n\n"
        
        if weak == '목':
            text += "목과 관련된 직업이 좋습니다. 나무를 다루는 일(목수, 가구 제작), 종이를 다루는 일(출판, 인쇄), 섬유를 다루는 일(의류, 패션), 교육 관련 일(교사, 강사), 의료 관련 일(한의사, 약사) 등이 귀하에게 맞습니다."
        elif weak == '화':
            text += "화와 관련된 직업이 좋습니다. 불을 다루는 일(요리사, 용접), 전기를 다루는 일(전기 기술자), 예술 관련 일(화가, 디자이너), 방송 관련 일(아나운서, PD), 철학 관련 일(종교인, 상담사) 등이 귀하에게 맞습니다."
        elif weak == '토':
            text += "토와 관련된 직업이 좋습니다. 땅을 다루는 일(농업, 부동산), 건축 관련 일(건축가, 인테리어), 보험 관련 일(보험 설계사), 중개 관련 일(중개인, 에이전트) 등이 귀하에게 맞습니다."
        elif weak == '금':
            text += "금과 관련된 직업이 좋습니다. 금속을 다루는 일(귀금속, 기계), 법률 관련 일(변호사, 법무사), 금융 관련 일(은행원, 증권인), 의료 관련 일(의사, 외과의) 등이 귀하에게 맞습니다."
        else:  # 수
            text += "수와 관련된 직업이 좋습니다. 물을 다루는 일(수산업, 음료), 유통 관련 일(무역, 물류), 정보 관련 일(IT, 컴퓨터), 여행 관련 일(여행사, 항공) 등이 귀하에게 맞습니다."
        
        text += "\n\n"
        
        text += f"<div class='sub-title'>6. 사람으로 보충하기</div>\n\n"
        text += f"{weak} 기운이 강한 사람과 가까이 지내십시오. "
        
        if weak == '목':
            text += "甲, 乙 일간인 사람이 귀하에게 도움이 됩니다. 이런 사람들은 곧고 정직하며, 귀하에게 올바른 길을 안내해줄 것입니다."
        elif weak == '화':
            text += "丙, 丁 일간인 사람이 귀하에게 도움이 됩니다. 이런 사람들은 밝고 열정적이며, 귀하에게 용기와 희망을 줄 것입니다."
        elif weak == '토':
            text += "戊, 己 일간인 사람이 귀하에게 도움이 됩니다. 이런 사람들은 믿음직하고 든든하며, 귀하에게 안정감을 줄 것입니다."
        elif weak == '금':
            text += "庚, 辛 일간인 사람이 귀하에게 도움이 됩니다. 이런 사람들은 냉철하고 이성적이며, 귀하에게 현명한 조언을 줄 것입니다."
        else:  # 수
            text += "壬, 癸 일간인 사람이 귀하에게 도움이 됩니다. 이런 사람들은 유연하고 지혜로우며, 귀하에게 새로운 시각을 열어줄 것입니다."
        
        text += "\n\n"
        
        # 에필로그 (3000자)
        text += f"<div class='chapter-title'>에필로그: 귀하께 드리는 마지막 말씀</div>\n\n"
        
        text += f"{name} 님, 이제 긴 이야기를 마칠 때가 되었습니다.\n\n"
        
        text += f"제가 오늘 귀하께 말씀드린 것은 귀하의 과거, 현재, 미래에 대한 이야기였습니다. 사주팔자라는 렌즈를 통해 귀하의 인생을 들여다본 것입니다.\n\n"
        
        text += "하지만 명심하십시오. 사주는 운명을 알려주는 도구일 뿐, 운명 그 자체는 아닙니다. 사주가 아무리 나빠 보여도 노력하면 좋아질 수 있고, 사주가 아무리 좋아 보여도 게으르면 망칠 수 있습니다.\n\n"
        
        text += "옛 성현들은 말씀하셨습니다. '인간만사 새옹지마'라고. 좋은 일도 나쁜 일의 씨앗이 될 수 있고, 나쁜 일도 좋은 일의 씨앗이 될 수 있다는 뜻입니다. 지금 힘들다고 절망하지 마십시오. 이 고통이 귀하를 더 단단하게 만들고 있습니다. 반대로 지금 잘 나간다고 방심하지 마십시오. 교만하면 반드시 추락합니다.\n\n"
        
        text += f"귀하는 {age}세입니다. "
        
        if age < 40:
            text += "아직 젊습니다. 앞으로 할 수 있는 일이 무궁무진합니다. 실패를 두려워하지 말고 도전하십시오. 지금 넘어지면 어떻습니까? 일어나면 됩니다. 젊음이란 바로 그런 것입니다."
        elif age < 60:
            text += "인생의 한가운데 있습니다. 이제 어느 정도 세상이 어떻게 돌아가는지 알게 되었을 것입니다. 그 지혜를 활용하십시오. 아직 늦지 않았습니다. 지금부터라도 하고 싶었던 것을 하십시오."
        else:
            text += "인생의 노을을 바라보고 있습니다. 지나온 길을 돌아보면 아쉬움도 많고 후회도 있을 것입니다. 하지만 그 모든 것이 귀하를 지금의 귀하로 만들었습니다. 이제는 내려놓을 때입니다. 집착을 버리고, 평온한 마음으로 남은 인생을 즐기십시오."
        
        text += "\n\n"
        
        if married:
            text += "귀하에게는 배우자가 있습니다. "
            if has_children:
                text += "자녀도 있습니다. 얼마나 큰 축복입니까. 세상에는 그런 축복조차 누리지 못하는 사람이 많습니다. 가족을 소중히 여기십시오. 사랑한다는 말을 자주 하십시오. 표현하지 않으면 모릅니다."
            else:
                text += "자녀는 아직 없지만, 배우자가 있다는 것만으로도 큰 축복입니다. 둘이서 의지하며 살아가십시오. 자녀가 없으면 어떻습니까? 둘이서 행복하면 그것으로 충분합니다."
        else:
            text += "귀하는 아직 혼자입니다. 외롭고 쓸쓸할 때도 많았을 것입니다. 하지만 혼자라는 것은 자유롭다는 뜻이기도 합니다. 누구 눈치 보지 않고, 하고 싶은 것을 할 수 있습니다. 그 자유를 즐기십시오. 그리고 언젠가는 귀하를 이해해주는 사람이 나타날 것입니다. 조급해하지 마십시오."
        
        text += "\n\n"
        
        # ===== 사고수/횡재수/건강 섹션 추가 =====
        text += "<div class='chapter-title'>제8부. 특별 주의사항 - 사고수와 횡재수</div>\n\n"
        
        text += "<div class='sub-title'>1. 사고수 주의 시기</div>\n\n"
        text += f"귀하의 사주를 보니, 특정 시기에 사고나 질병의 위험이 있습니다. 미리 알고 조심하면 피할 수 있습니다.\n\n"
        
        # 사고수 판단 (관성/칠살이 과다하거나, 오행 불균형)
        if counts['금'] >= 3 or counts['목'] >= 3:
            text += f"**{age+2}세, {age+7}세, {age+12}세**: 금속성 사고 주의. 교통사고, 낙상, 금속 기구 다루는 작업 시 특히 조심하십시오. 이 시기에는 무리한 운동이나 위험한 활동을 삼가십시오.\n\n"
        
        if counts['수'] >= 3 or counts['화'] >= 3:
            text += f"**{age+4}세, {age+9}세, {age+14}세**: 물과 불 관련 사고 주의. 수영, 등산, 불 다루는 일을 할 때 극도로 조심하십시오. 특히 술을 마신 후에는 절대 위험한 일을 하지 마십시오.\n\n"
        
        text += "사고는 조심하면 막을 수 있습니다. 위험한 시기에는 보수적으로 행동하십시오. 급하게 서두르지 말고, 천천히 신중하게 움직이십시오. 몸이 피곤하거나 정신이 흐릿할 때는 아무것도 하지 마십시오.\n\n"
        
        text += "<div class='sub-title'>2. 횡재수 시기</div>\n\n"
        text += f"반대로, 귀하에게는 큰 횡재가 올 시기도 있습니다. 이 시기를 놓치지 마십시오.\n\n"
        
        # 횡재수 판단 (재성이 들어오는 대운)
        for dae in daewun[:5]:
            if '재성' in dae['b_sip'] or '재성' in dae['s_sip']:
                text += f"**{dae['age']}세 대운 ({dae['ganji']})**: 재성대운으로 돈이 들어옵니다. 이 시기에 투자, 사업, 부동산 거래를 하면 큰 수익을 볼 수 있습니다. 단, 욕심을 부리면 오히려 손해를 볼 수 있으니, 적당한 선에서 만족하십시오.\n\n"
        
        text += f"**{age+3}세, {age+8}세**: 작은 행운의 시기. 복권이나 경품 당첨, 예상치 못한 보너스 등이 있을 수 있습니다. 이 시기에는 긍정적인 마음가짐을 유지하십시오. 좋은 기운이 좋은 일을 불러옵니다.\n\n"
        
        text += "<div class='sub-title'>3. 건강 주의사항</div>\n\n"
        text += "건강은 무엇보다 중요합니다. 귀하의 오행 밸런스를 보니 특별히 주의해야 할 신체 부위가 있습니다.\n\n"
        
        # 건강 - 오행별 취약 장기
        health_map = {
            '목': ('간', '담낭', '눈', '신 음식(식초, 매실)을 자주 드시고, 녹색 채소를 많이 드십시오'),
            '화': ('심장', '소장', '혈관', '쓴 음식(쌈채소, 고추잎)을 드시고, 과도한 스트레스를 피하십시오'),
            '토': ('위', '비장', '소화기', '단 음식을 적당히 드시고, 규칙적인 식사를 하십시오'),
            '금': ('폐', '대장', '피부', '매운 음식(생강, 마늘)을 드시고, 호흡기 건강에 신경 쓰십시오'),
            '수': ('신장', '방광', '생식기', '짠 음식을 줄이고, 물을 자주 드시며, 하체를 따뜻하게 하십시오')
        }
        
        for oh, (organ1, organ2, organ3, advice) in health_map.items():
            cnt = counts[oh]
            if cnt == 0:
                text += f"**{oh} 기운 부족**: {organ1}, {organ2}, {organ3}이 약합니다. {advice}.\n\n"
            elif cnt >= 4:
                text += f"**{oh} 기운 과다**: {organ1}, {organ2}에 열이 많습니다. {advice}.\n\n"
        
        text += f"\n**{age+5}세 이후**: 중년기에 접어들면서 체력이 약해집니다. 규칙적인 운동과 균형 잡힌 식사가 필수입니다. 특히 술과 담배는 반드시 줄이십시오.\n\n"
        
        if age >= 50:
            text += "**현재**: 이미 50대 이상이시니 건강 검진을 정기적으로 받으십시오. 고혈압, 당뇨, 관절염 등 성인병을 조기에 발견하는 것이 중요합니다.\n\n"
        
        text += "<div class='sub-title'>4. 종합 개운법</div>\n\n"
        text += "운을 좋게 만드는 방법을 알려드립니다.\n\n"
        
        # 용신 색상/방향
        colors = {'목':'녹색', '화':'빨강', '토':'황색', '금':'흰색', '수':'검정/파랑'}
        directions = {'목':'동쪽', '화':'남쪽', '토':'중앙', '금':'서쪽', '수':'북쪽'}
        
        text += f"**색상**: {colors[weak]} 옷을 자주 입고, {colors[weak]} 소품을 사용하십시오.\n"
        text += f"**방향**: {directions[weak]}으로 이사하거나, 책상을 {directions[weak]} 방향으로 두십시오.\n"
        text += f"**직업**: {weak} 기운과 관련된 직업이 유리합니다.\n"
        text += f"**음식**: {weak} 기운을 보충하는 음식을 많이 드십시오.\n\n"
        
        text += f"가장 중요한 것은 **마음가짐**입니다. 긍정적으로 생각하고, 감사하는 마음을 가지십시오. 좋은 마음이 좋은 운을 부릅니다.\n\n"
        
        # ===== 에필로그 =====
        text += "<div class='chapter-title'>에필로그</div>\n\n"
        
        text += f"마지막으로, {name} 님께 이 말씀을 드리고 싶습니다.\n\n"
        
        text += "**'살아있다는 것 자체가 축복입니다.'**\n\n"
        
        text += "귀하는 지금 숨 쉬고 있습니다. 심장이 뛰고 있습니다. 눈으로 세상을 보고, 귀로 소리를 듣고, 입으로 맛을 느끼고 있습니다. 이것이 얼마나 대단한 일입니까. 이 우주에서 생명이 있는 행성이 얼마나 됩니까? 그 행성에서 인간으로 태어날 확률이 얼마나 됩니까? 귀하는 그 기적 같은 확률을 뚫고 인간으로 태어났습니다.\n\n"
        
        text += "그러니 불평하지 마십시오. 감사하십시오. 힘들다고 포기하지 마십시오. 끝까지 최선을 다하십시오. 그것이 귀하에게 주어진 생명에 대한 예의입니다.\n\n"
        
        text += f"제가 귀하께 드릴 수 있는 말씀은 여기까지입니다. 이 긴 글을 끝까지 읽어주셔서 감사합니다.\n\n"
        
        text += f"**{name} 님의 남은 인생에 건강과 행복이 가득하기를 진심으로 기원합니다.**\n\n"
        
        text += f"{'='*100}\n"
        text += f"총 {len(text):,}자\n"
        text += f"작성 일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n"
        text += f"{'='*100}\n"
        
        # HTML 태그 제거 (화면에 코드 노출 방지)
        import re
        text = text.replace("<div class='chapter-title'>", "\n\n【 ")
        text = text.replace("<div class='sub-title'>", "\n■ ")
        text = text.replace("</div>", " 】")
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # **bold** 제거
        
        return text

# ==============================================================================
# [4] AI 생성기 (순수 한글)
# ==============================================================================
class AIGenerator:
    """AI 50,000자 순수 한글 생성 - 최신 Groq API"""
    
    @staticmethod
    def call(api_key, msgs, tokens=8000):
        """Groq API 호출 with retry and language check"""
        import time
        import re
        
        if not api_key:
            return None
        
        max_retries = 3
        retry_delay = 10  # 10초 대기 (429 에러 방지)
        
        for attempt in range(max_retries):
            try:
                # 429 에러 방지를 위한 대기
                if attempt > 0:
                    time.sleep(retry_delay * attempt)
                
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": msgs,
                        "temperature": 0.9,
                        "max_tokens": tokens,
                        "top_p": 0.95,
                        "frequency_penalty": 1.5,
                        "presence_penalty": 1.3
                    },
                    timeout=300
                )
                
                # 429 에러 특별 처리
                if r.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 2))
                        continue
                    else:
                        return "⚠️ API 요청 한도 초과. 1분 후 다시 시도해주세요."
                
                r.raise_for_status()
                content = r.json()['choices'][0]['message']['content']
                
                # 중국어/일본어 검사
                chinese = re.findall(r'[\u4e00-\u9fff]', content)
                japanese = re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', content)
                
                # 한자가 괄호 안에 있는 경우는 제외하고 계산
                content_no_paren = re.sub(r'\([^)]*\)', '', content)
                chinese_no_paren = re.findall(r'[\u4e00-\u9fff]', content_no_paren)
                
                # 괄호 밖 중국어/일본어가 많으면 재시도
                if len(chinese_no_paren) > 10 or len(japanese) > 5:
                    if attempt < max_retries - 1:
                        msgs.append({
                            "role": "assistant",
                            "content": content
                        })
                        msgs.append({
                            "role": "user",
                            "content": "❌ 중국어/일본어가 포함되어 있습니다! 반드시 100% 순수 한글로만 다시 작성하세요. 한자는 오직 괄호 () 안에만 넣을 수 있습니다."
                        })
                        time.sleep(3)
                        continue
                
                return content
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue
                return "⚠️ 응답 시간 초과. 다시 시도해주세요."
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                return f"⚠️ 오류: {str(e)}"
        
        return "⚠️ 최대 재시도 횟수 초과. 잠시 후 다시 시도해주세요."
    
    @staticmethod
    def system():
        """강화된 시스템 프롬프트 - 외국어 완전 금지"""
        return """당신은 50년 경력의 사주명리학 대가이자 베스트셀러 작가입니다.

【 최우선 규칙 - 이것만은 절대 엄수! 】
⛔⛔⛔ 중국어 사용 시 즉시 중단! ⛔⛔⛔
금지 문자 예시: 您(당신), 忙碌(바쁘다), 天賦(천부), 旺(왕성), 等(등), 
               然而(그러나), 但是(하지만), 最后(마지막), 自己(자기), 什么(무엇),
               可以(가능), 非常(매우), 需要(필요), 应该(해야), 一定(반드시)

⛔⛔⛔ 일본어 사용 시 즉시 중단! ⛔⛔⛔  
금지 문자 예시: の, です, ます, 自分, 何か, しかし, そして

⛔⛔⛔ 영어 사용 시 즉시 중단! ⛔⛔⛔
금지 단어 예시: success, money, career, health, successful, material

✅ 올바른 표현 방법:
- 您 (X) → 귀하, 당신 (O)
- 忙碌 (X) → 바쁜 (O)
- 天賦 (X) → 타고난 재능 (O)
- 旺 (X) → 왕성한, 강한 (O)
- successful (X) → 성공적인 (O)

✅ 한자는 오직 괄호 안에만: 갑(甲), 재성(財星)

【 핵심 임무 】
사주팔자를 바탕으로 한 사람의 전 생애를 소설처럼 서사적으로 풀어냅니다.

【 필수 준수 】
✅ 순수 한글로만 작성 (한국어 100%)
✅ 한자 표기는 반드시 괄호 안에: 갑(甲), 자(子), 목(木)
✅ 천간지지는 항상 한자 포함: 갑(甲)자(子), 을(乙)축(丑)
✅ 오행도 한자 포함: 목(木), 화(火), 토(土), 금(金), 수(水)
✅ 소설처럼 서사적으로 (대화체 포함 가능)
✅ 구체적 사건 묘사
✅ 감정 표현 풍부하게
✅ 사주 데이터 100% 반영
✅ 최소 5,000자 이상 (목표: 8,000자)

【 한자 표기 예시 】
- 천간: 갑(甲), 을(乙), 병(丙), 정(丁), 무(戊), 기(己), 경(庚), 신(辛), 임(壬), 계(癸)
- 지지: 자(子), 축(丑), 인(寅), 묘(卯), 진(辰), 사(巳), 오(午), 미(未), 신(申), 유(酉), 술(戌), 해(亥)
- 오행: 목(木), 화(火), 토(土), 금(金), 수(水)
- 십신: 재성(財星), 관성(官星), 인성(印星), 식상(食傷), 비겁(比劫)

【 작성 스타일 】
- 문장은 자연스럽게, 마치 옆에서 이야기하는 듯
- "귀하는 ~했습니다" 보다는 "당신은 ~했어요" 같은 친근한 톤
- 은유와 비유 적극 활용 ("마치 사막에 단비가 내리듯")
- 과거-현재-미래를 자연스럽게 연결

【 사주 해석 방법 】
천간: 겉으로 드러나는 성격, 사회적 모습
지지: 내면의 감정, 숨겨진 욕망
십신: 재물(재성), 명예(관성), 학습(인성), 표현(식상), 경쟁(비겁)
십이운성: 생명 주기

이 모든 요소를 종합하여 한 사람의 인생 이야기를 펼쳐주세요."""
    
    @staticmethod
    def generate(api_key, user_info, pillars, counts, daewun, topic, callback=None):
        """10파트 × 5,000자 = 50,000자 생성"""
        
        name = user_info['name']
        age = user_info['age']
        married = user_info['married']
        has_children = user_info['has_children']
        job = user_info['job']
        
        # 사주 정보 요약
        saju_data = f"""
이름: {name} ({age}세)
상태: {'기혼' if married else '미혼'}, 자녀 {'있음' if has_children else '없음'}, 직업: {job}

사주팔자:
년주: {pillars['년']['t']} - {pillars['년']['s_sip']}/{pillars['년']['b_sip']} ({pillars['년']['unseong']})
월주: {pillars['월']['t']} - {pillars['월']['s_sip']}/{pillars['월']['b_sip']} ({pillars['월']['unseong']})
일주: {pillars['일']['t']} - 일간 (본인)
시주: {pillars['시']['t']} - {pillars['시']['s_sip']}/{pillars['시']['b_sip']} ({pillars['시']['unseong']})

오행: 목{counts['목']}개, 화{counts['화']}개, 토{counts['토']}개, 금{counts['금']}개, 수{counts['수']}개

대운 (57세부터):
"""
        for dae in daewun[:3]:
            saju_data += f"{dae['age']}세: {dae['ganji']} ({dae['s_sip']}/{dae['b_sip']})\n"
        
        # 10개 파트
        parts = [
            {
                'title': '프롤로그: 운명의 시작',
                'prompt': f"{saju_data}\n\n당신이 태어난 순간, 하늘과 땅의 기운이 만나 사주팔자가 정해졌습니다. 이 사주가 당신 인생에 어떤 의미인지, 마치 소설의 첫 장을 여는 것처럼 서사적으로 8,000자로 풀어주세요. 당신의 천간({pillars['일']['t'][0:3]})과 지지({pillars['일']['t'][4:7]})가 어떤 성격을 만들었는지 구체적으로요."
            },
            {
                'title': '제1장: 어린 시절 (0-10세)',
                'prompt': f"{saju_data}\n\n0세부터 10세까지의 어린 시절을 8,000자로 그려주세요. 가족 관계, 성격 형성, 학교 생활, 친구들과의 추억. 년주({pillars['년']['t']})의 영향을 받은 어린 시절의 모습을요."
            },
            {
                'title': '제2장: 청소년기 (11-20세)',
                'prompt': f"{saju_data}\n\n11세부터 20세까지의 청소년기를 8,000자로. 사춘기의 방황, 첫사랑, 입시 스트레스, 진로 고민. 월주({pillars['월']['t']})가 만든 사회적 관계를요."
            },
            {
                'title': '제3장: 청년기 (21-30세)',
                'prompt': f"{saju_data}\n\n21세부터 30세까지를 8,000자로. 취업, 연애, 결혼 여부, 사회 적응. 십신({pillars['일']['s_sip']}, {pillars['월']['s_sip']})이 어떻게 영향을 주었는지요."
            },
            {
                'title': f'제4장: 현재 ({age}세)',
                'prompt': f"{saju_data}\n\n현재 {age}세인 {name}님의 상황을 8,000자로 깊이 파헤쳐주세요. 직업({job}), 가정 상황(기혼 여부, 자녀), 고민, 바람. 지금 이 순간의 감정까지요."
            },
            {
                'title': f'제5장: 57세 대운 - {daewun[0]["ganji"]}',
                'prompt': f"{saju_data}\n\n57세부터 시작되는 {daewun[0]['ganji']} 대운을 8,000자로 해석해주세요. 이 시기의 사고수, 횡재수, 건강 문제, 가족 관계 변화까지 예측해주세요."
            },
            {
                'title': '제6장: 건강과 재물',
                'prompt': f"{saju_data}\n\n오행 밸런스(목{counts['목']}, 화{counts['화']}, 토{counts['토']}, 금{counts['금']}, 수{counts['수']})를 분석해서, 건강 취약 부위와 재물운을 8,000자로 상세하게 풀어주세요. 어떤 질병을 조심해야 하고, 돈은 언제 들어오는지요."
            },
            {
                'title': '제7장: 개운법',
                'prompt': f"{saju_data}\n\n운을 좋게 만드는 구체적 방법을 8,000자로 알려주세요. 색상, 방향, 숫자, 음식, 직업, 만나야 할 사람. 실천 가능한 조언만요."
            },
            {
                'title': '제8장: 사고수와 주의사항',
                'prompt': f"{saju_data}\n\n인생에서 조심해야 할 시기와 사건을 8,000자로 경고해주세요. 교통사고, 질병, 사업 실패, 이혼 위기 등. 구체적 나이와 상황까지요."
            },
            {
                'title': '에필로그: 축복',
                'prompt': f"{saju_data}\n\n{name}님의 남은 인생에 대한 희망과 축복의 메시지를 8,000자로 전해주세요. 따뜻하고 감동적으로, 마치 소설의 마지막 장처럼요."
            }
        ]
        
        # 생성
        results = []
        total = len(parts)
        
        for i, part in enumerate(parts, 1):
            if callback:
                callback(f"{part['title']} 생성 중...", i / total)
            
            msgs = [
                {"role": "system", "content": AIGenerator.system()},
                {"role": "user", "content": part['prompt']}
            ]
            
            res = AIGenerator.call(api_key, msgs, 8000)
            if res:
                results.append(f"\n\n{'='*100}\n{part['title']}\n{'='*100}\n\n{res}")
            
            # 429 에러 방지 - API 요청 간격 충분히 확보
            if i < total:
                time.sleep(15)  # 15초 대기
        
        # 최종 조합
        full = f"""
{'='*100}
【 {name} 님의 인생 대서사시 - AI 완전판 】
{'='*100}

{age}세 | {'기혼' if married else '미혼'} | 자녀 {'있음' if has_children else '없음'} | {job}

총 {len(parts)}개 챕터

{'='*100}
"""
        full += ''.join(results)
        full += f"\n\n{'='*100}\n총 {len(full):,}자\n{'='*100}\n"
        
        return full

# ==============================================================================
# [5] 메인 UI - 2페이지 구조
# ==============================================================================
def main():
    # 세션 상태 초기화
    if 'page' not in st.session_state:
        st.session_state.page = 'input'  # 'input' 또는 'result'
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # ===== 페이지 1: 입력 화면 =====
    if st.session_state.page == 'input':
        st.markdown('<div class="master-header"><h1>🌟 사주 대서사시 만세력</h1></div>', unsafe_allow_html=True)
        
        with st.sidebar:
            st.header("⚙️ 설정")
            
            use_ai = st.checkbox("🤖 AI 사용 (더 상세)", False)
            
            api_key = ""
            if use_ai:
                api_key = st.text_input("Groq API Key", type="password")
                if not api_key:
                    st.warning("API 키 필요")
                st.info("⏰ AI 생성: 10~15분 소요 (50,000자 이상)")
            else:
                st.success("📜 코드 생성: 즉시 완료 (30,000자)")
        
        with st.form("user_input"):
            st.subheader("📌 기본 정보")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                name = st.text_input("이름", "홍길동")
                gender = st.radio("성별", ["남", "여"])
            with col2:
                cal_type = st.radio("달력", ["양력", "음력", "윤달"])
            
            st.markdown("### 📅 생년월일")
            c1, c2, c3 = st.columns(3)
            year = c1.number_input("년", 1900, 2030, 1990)
            month = c2.number_input("월", 1, 12, 1)
            day = c3.number_input("일", 1, 31, 1)
            
            st.markdown("### 🕐 시간")
            time_yn = st.radio("시간", ["알고 있음", "모름"])
            t_idx = 6
            if time_yn == "알고 있음":
                ji_times = [
                    "자시(子時) 23-01시", "축시(丑時) 01-03시", "인시(寅時) 03-05시",
                    "묘시(卯時) 05-07시", "진시(辰時) 07-09시", "사시(巳時) 09-11시",
                    "오시(午時) 11-13시", "미시(未時) 13-15시", "신시(申時) 15-17시",
                    "유시(酉時) 17-19시", "술시(戌時) 19-21시", "해시(亥時) 21-23시"
                ]
                t_idx = st.selectbox("시", range(12), format_func=lambda x: ji_times[x], index=6)
            
            st.markdown("---")
            st.subheader("🎯 개인화")
            married = st.radio("결혼", ["미혼", "기혼"]) == "기혼"
            has_children = False
            if married:
                has_children = st.radio("자녀", ["없음", "있음"]) == "있음"
            job = st.text_input("직업", "회사원")
            topic = st.selectbox("주제", ["종합운", "재물운", "직장운", "결혼운", "건강운"])
            
            submit = st.form_submit_button("✨ 생성하기", use_container_width=True, type="primary")
        
        if submit:
            with st.spinner("사주 계산 중..."):
                pillars, counts, daewun, day_oh, day_gan, birth_y = SajuEngine.calculate(
                    year, month, day, t_idx, gender, time_yn=="모름", cal_type
                )
                
                age = 2026 - birth_y
                user_info = {
                    'name': name, 'age': age,
                    'married': married, 'has_children': has_children, 'job': job
                }
            
            with st.spinner("대서사시 생성 중..."):
                if use_ai and api_key:
                    progress_placeholder = st.empty()
                    def progress_callback(msg, pct):
                        progress_placeholder.progress(pct, text=msg)
                    
                    final_text = AIGenerator.generate(
                        api_key, user_info, pillars, counts, daewun, topic, 
                        callback=progress_callback
                    )
                    progress_placeholder.empty()
                else:
                    final_text = EpicGenerator.generate(user_info, pillars, counts, daewun, topic, day_oh, day_gan)
            
            # 결과 저장 및 페이지 전환
            st.session_state.result = final_text
            st.session_state.pillars = pillars
            st.session_state.user_info = user_info
            st.session_state.daewun = daewun
            st.session_state.use_ai = use_ai
            st.session_state.api_key = api_key if use_ai else None
            st.session_state.page = 'result'
            st.rerun()
    
    # ===== 페이지 2: 결과 화면 =====
    elif st.session_state.page == 'result':
        # 상단 네비게이션
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("⬅️ 처음으로"):
                st.session_state.page = 'input'
                st.rerun()
        with col2:
            st.markdown(f"<h2 style='text-align:center;'>{st.session_state.user_info['name']} 님의 운명 대서사시</h2>", unsafe_allow_html=True)
        with col3:
            st.download_button(
                "📥 다운로드",
                st.session_state.result,
                file_name=f"{st.session_state.user_info['name']}_운세.txt",
                mime="text/plain"
            )
        
        st.markdown("---")
        
        # 탭 구성: 명식표 | 운세 | AI상담
        tab1, tab2, tab3 = st.tabs(["📊 명식표", "📜 운세 내용", "🤖 AI 상담"])
        
        # 탭 1: 명식표
        with tab1:
            p = st.session_state.pillars
            
            # 60갑자 차트
            st.markdown(create_gapja_chart(), unsafe_allow_html=True)
            
            st.markdown(f"### 📜 {st.session_state.user_info['name']} 님의 사주팔자")
            
            # 백그라운드 데이터 저장 (화면에 표시하지 않음)
            p = st.session_state.pillars
            saju_backup = {
                '일주': p['일']['t'],
                '월주': p['월']['t'],
                '년주': p['년']['t'],
                '시주': p['시']['t']
            }
            st.session_state.saju_backup = saju_backup
            
            # 간단한 카드 형식으로 표시
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="text-align:center; padding:30px 20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius:15px; color:white; box-shadow:0 10px 30px rgba(0,0,0,0.3);">
                    <h2 style="margin:0; font-size:1.2rem; opacity:0.9;">🎯 일주 (본인)</h2>
                    <h1 style="margin:15px 0; font-size:2.5rem; font-weight:bold;">{p['일']['t']}</h1>
                    <p style="margin:5px 0; font-size:1rem; opacity:0.9;">{p['일']['han']}</p>
                    <p style="margin:5px 0; font-size:0.95rem;">{p['일']['unseong']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.8;">{p['일']['s_sip']} / {p['일']['b_sip']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="text-align:center; padding:30px 20px; background:linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                            border-radius:15px; color:white; box-shadow:0 10px 30px rgba(0,0,0,0.3);">
                    <h2 style="margin:0; font-size:1.2rem; opacity:0.9;">📅 월주</h2>
                    <h1 style="margin:15px 0; font-size:2.5rem; font-weight:bold;">{p['월']['t']}</h1>
                    <p style="margin:5px 0; font-size:1rem; opacity:0.9;">{p['월']['han']}</p>
                    <p style="margin:5px 0; font-size:0.95rem;">{p['월']['unseong']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.8;">{p['월']['s_sip']} / {p['월']['b_sip']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style="text-align:center; padding:30px 20px; background:linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                            border-radius:15px; color:white; box-shadow:0 10px 30px rgba(0,0,0,0.3);">
                    <h2 style="margin:0; font-size:1.2rem; opacity:0.9;">🏛️ 년주</h2>
                    <h1 style="margin:15px 0; font-size:2.5rem; font-weight:bold;">{p['년']['t']}</h1>
                    <p style="margin:5px 0; font-size:1rem; opacity:0.9;">{p['년']['han']}</p>
                    <p style="margin:5px 0; font-size:0.95rem;">{p['년']['unseong']}</p>
                    <p style="margin:0; font-size:0.9rem; opacity:0.8;">{p['년']['s_sip']} / {p['년']['b_sip']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 시주 정보
            if p['시']['t'] != '미상':
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="text-align:center; padding:25px; background:linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                            border-radius:15px; color:white; box-shadow:0 10px 30px rgba(0,0,0,0.3); max-width:600px; margin:0 auto;">
                    <h3 style="margin:0 0 10px 0; font-size:1.1rem;">🕐 시주 (時柱)</h3>
                    <h2 style="margin:10px 0; font-size:2rem; font-weight:bold;">{p['시']['t']}</h2>
                    <p style="margin:5px 0; font-size:1rem;">{p['시']['han']} · {p['시']['unseong']} · {p['시']['s_sip']}/{p['시']['b_sip']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("⏰ 시주 정보가 없습니다.")
        
        # 탭 2: 운세 내용
        with tab2:
            st.text_area("운세 내용", st.session_state.result, height=600)
        
        # 탭 3: AI 상담
        with tab3:
            st.markdown("### 🤖 AI 사주 상담사")
            st.info("💡 사주와 운세에 대해 궁금한 점을 물어보세요! (20,000자 이상 상세 답변)")
            
            # API 키 확인
            if st.session_state.use_ai and st.session_state.api_key:
                api_key = st.session_state.api_key
            else:
                api_key = st.text_input("Groq API Key", type="password", key="chat_api")
            
            if not api_key:
                st.warning("⚠️ AI 상담을 이용하려면 Groq API 키가 필요합니다.")
            else:
                # 채팅 히스토리 표시
                for i, msg in enumerate(st.session_state.chat_history):
                    if msg['role'] == 'user':
                        st.markdown(f"**👤 질문**: {msg['content']}")
                    else:
                        st.markdown(f"**🤖 답변**:\n\n{msg['content']}")
                    st.markdown("---")
                
                # 질문 입력
                with st.form("chat_form", clear_on_submit=True):
                    question = st.text_area("질문을 입력하세요", height=100, 
                                           placeholder="예: 57세 대운에서 재물운이 좋다고 했는데, 구체적으로 어떤 투자를 하면 좋을까요?")
                    submit_chat = st.form_submit_button("💬 질문하기", use_container_width=True)
                
                if submit_chat and question:
                    with st.spinner("AI가 답변을 작성 중입니다..."):
                        # 사주 정보 컨텍스트
                        p = st.session_state.pillars
                        context = f"""
사용자 정보:
- 이름: {st.session_state.user_info['name']}
- 나이: {st.session_state.user_info['age']}세
- 직업: {st.session_state.user_info['job']}

사주팔자:
- 년주: {p['년']['t']} ({p['년']['s_sip']}/{p['년']['b_sip']}, {p['년']['unseong']})
- 월주: {p['월']['t']} ({p['월']['s_sip']}/{p['월']['b_sip']}, {p['월']['unseong']})
- 일주: {p['일']['t']} (본인)
- 시주: {p['시']['t']} ({p['시']['s_sip']}/{p['시']['b_sip']}, {p['시']['unseong']})

대운:
"""
                        for dae in st.session_state.daewun:
                            context += f"- {dae['age']}세: {dae['ganji']} ({dae['s_sip']}/{dae['b_sip']})\n"
                        
                        # AI 상담 시스템 프롬프트
                        system_prompt = """당신은 50년 경력의 사주명리학 대가입니다.

【 최우선 규칙 - 절대 엄수! 】
⛔⛔⛔ 중국어 사용 시 즉시 중단! ⛔⛔⛔
금지 예시: 您(당신), 忙碌(바쁘다), 天賦(천부), 旺(왕성), 等(등), 然而(그러나), 
           但是(하지만), 最后(마지막), 自己(자기), 什么(무엇), 可以(가능), 
           非常(매우), 需要(필요), 应该(해야), 一定(반드시), 藏(숨기다)

⛔⛔⛔ 일본어 사용 시 즉시 중단! ⛔⛔⛔
금지 예시: の, です, ます, 自分, 何か, しかし

⛔⛔⛔ 영어 사용 시 즉시 중단! ⛔⛔⛔
금지 예시: success, money, career, health, successful

✅ 올바른 표현:
- 您 (X) → 귀하, 당신 (O)
- 忙碌 (X) → 바쁜 (O)  
- 天賦 (X) → 타고난 재능 (O)
- 旺 (X) → 왕성한, 강한 (O)
- successful (X) → 성공적인 (O)

✅ 한자는 오직 괄호 안에만: 갑(甲), 재성(財星)

【 필수 준수 】
✅ 순수 한글로만 작성 (한국어 100%)
✅ 20,000자 이상 작성 (매우 상세하게)
✅ 구체적인 연도, 나이, 예시 제공
✅ 실천 가능한 조언
✅ 사주 데이터 100% 반영

【 답변 스타일 】
- 친근하고 따뜻하게
- 구체적인 상황 묘사
- 이유와 근거 명확히
- 주의사항 포함

⚠️ 중국어/일본어/영어 사용 시 즉시 중단됩니다!
오직 순수 한글만 사용하세요."""

                        # 대화 이력 구성
                        messages = [{"role": "system", "content": system_prompt}]
                        
                        # 이전 대화 포함
                        for msg in st.session_state.chat_history[-4:]:  # 최근 4개만
                            messages.append(msg)
                        
                        # 현재 질문
                        messages.append({
                            "role": "user", 
                            "content": f"{context}\n\n질문: {question}"
                        })
                        
                        # AI 호출
                        answer = AIGenerator.call(api_key, messages, 16000)
                        
                        if answer and "오류" not in answer:
                            # 히스토리에 추가
                            st.session_state.chat_history.append({"role": "user", "content": question})
                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            st.rerun()
                        else:
                            st.error("❌ AI 응답 오류가 발생했습니다. API 키를 확인하거나 잠시 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()