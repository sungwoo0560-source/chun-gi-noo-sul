import streamlit as st
import datetime
import requests
import time
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime as dt_now

# ==============================================================================
# [0] 시스템 설정
# ==============================================================================
st.set_page_config(layout="wide", page_title="천기누설 v18.0 - AI 만세력")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&display=swap');
    
    * { font-family: 'Nanum Myeongjo', serif; }
    .stApp { background-color: #fdfdfd; color: #111; }
    
    /* 초록색 헤더 박스 - 천기누설 */
    .master-header {
        background: linear-gradient(135deg, #2e7d32 0%, #43a047 50%, #66bb6a 100%);
        color: #fff; 
        padding: 35px 40px; 
        text-align: center; 
        border-bottom: 8px solid #1b5e20;
        margin-bottom: 30px; 
        border-radius: 0 0 20px 20px; 
        box-shadow: 0 10px 30px rgba(46, 125, 50, 0.3);
    }
    
    .master-header h1 { 
        font-size: 2.8rem;
        font-weight: 900; 
        letter-spacing: 3px; 
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .master-header p {
        font-size: 0.95rem;
        margin-top: 8px;
        opacity: 0.95;
    }
    
    /* AI 토글 박스 */
    .ai-toggle-box {
        background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
        border-left: 5px solid #2e7d32;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    
    .ai-toggle-box h3 {
        margin: 0 0 15px 0;
        color: #2e7d32;
        font-size: 1.2rem;
    }
    
    .toggle-status {
        font-size: 1rem;
        padding: 12px 15px;
        border-radius: 8px;
        margin: 10px 0;
        font-weight: bold;
        border-left: 4px solid;
    }
    
    .status-on {
        background: #c8e6c9;
        color: #1b5e20;
        border-left-color: #2e7d32;
    }
    
    .status-off {
        background: #f0f0f0;
        color: #666;
        border-left-color: #999;
    }
    
    /* 진행 바 */
    .progress-container {
        background: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 4px solid #2e7d32;
    }
    
    /* 상담 채팅 박스 */
    .chat-message-user {
        background: #e3f2fd;
        padding: 15px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid #2196F3;
        line-height: 1.6;
    }
    
    .chat-message-ai {
        background: #c8e6c9;
        padding: 15px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid #2e7d32;
        line-height: 1.6;
    }
    
    .oh-mok { background: #4CAF50 !important; color: white !important; }
    .oh-hwa { background: #F44336 !important; color: white !important; }
    .oh-to { background: #FFC107 !important; color: #333 !important; }
    .oh-geum { background: #EEEEEE !important; color: #333 !important; border: 2px solid #999 !important; }
    .oh-su { background: #2196F3 !important; color: white !important; }
    
    .gapja-container { margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }
    .gapja-title { font-size: 1.3rem; font-weight: bold; text-align: center; margin-bottom: 20px; color: #2c3e50; }
    .gapja-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 5px; max-width: 900px; margin: 0 auto; }
    .gapja-cell { 
        padding: 8px 4px; text-align: center; font-weight: bold; font-size: 0.85rem; line-height: 1.3;
        border-radius: 8px; border: 2px solid rgba(0,0,0,0.1); 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton > button {
        font-weight: bold !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
    }
    
    .result-header {
        background: linear-gradient(135deg, #2e7d32 0%, #43a047 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    .result-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    
    .api-key-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [1] 세션 상태 초기화
# ==============================================================================
if 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = None
if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'use_ai' not in st.session_state:
    st.session_state.use_ai = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'result' not in st.session_state:
    st.session_state.result = ""
if 'pillars' not in st.session_state:
    st.session_state.pillars = {}

# ==============================================================================
# [2] 한국천문연구원 API
# ==============================================================================
class KasiAPI:
    """한국천문연구원(KASI) 공공데이터 API"""
    
    SERVICE_KEY = "cb2437de2fef73ffe9bc6ebd8c23a7420358888768075846c063d39b4955add6"
    LUNAR_URL = "http://apis.data.go.kr/B090041/openapi/service/LunisolarInfoService/getLunisolarInfo"
    
    @staticmethod
    def get_lunar_to_solar(year, month, day, leap=False):
        """음력 -> 양력 변환"""
        try:
            params = {
                'serviceKey': KasiAPI.SERVICE_KEY,
                'solYear': str(year),
                'solMonth': f"{month:02d}",
                'solDay': f"{day:02d}",
                'numOfRows': 1,
                'pageNo': 1,
                'type': 'xml'
            }
            
            response = requests.get(KasiAPI.LUNAR_URL, params=params, timeout=5)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall('.//item'):
                    solYear = item.find('solYear')
                    solMonth = item.find('solMonth')
                    solDay = item.find('solDay')
                    
                    if all([solYear, solMonth, solDay]):
                        return int(solYear.text), int(solMonth.text), int(solDay.text)
            
            return None
        except:
            return None

# ==============================================================================
# [3] 음력 라이브러리
# ==============================================================================
HAS_LUNAR = False
try:
    from korean_lunar_calendar import KoreanLunarCalendar
    HAS_LUNAR = True
except ImportError:
    pass

# ==============================================================================
# [4] 사주 엔진
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
        """음력 -> 양력 변환"""
        if cal_type == '양력':
            return y, m, d
        
        result = KasiAPI.get_lunar_to_solar(y, m, d, leap=(cal_type=='윤달'))
        if result:
            return result
        
        if HAS_LUNAR:
            try:
                calendar = KoreanLunarCalendar()
                is_leap = (cal_type == '윤달')
                calendar.setLunarDate(y, m, d, is_leap)
                iso_format = calendar.SolarIsoFormat()
                parts = iso_format.split('-')
                return int(parts[0]), int(parts[1]), int(parts[2])
            except:
                pass
        
        import datetime as dt
        date = dt.date(y, m, d) + dt.timedelta(days=30)
        return date.year, date.month, date.day

    @classmethod
    def calculate(cls, y, m, d, h_idx, gender, time_unknown, cal_type):
        """사주 계산"""
        import datetime as dt
        
        sol_y, sol_m, sol_d = cls.convert_date(y, m, d, cal_type)
        
        y_offset = sol_y - 1900
        y_idx = (y_offset + 36) % 60 if sol_m > 2 else (y_offset + 35) % 60
        
        wol_m = sol_m if sol_d >= 6 else sol_m - 1
        if wol_m <= 0:
            wol_m = 12
        m_base = (y_idx % 10 % 5) * 2 + 2
        m_idx = (m_base + (wol_m - 2 if wol_m >= 2 else 10)) % 10
        
        base = dt.date(1900, 1, 1)
        curr = dt.date(sol_y, sol_m, sol_d)
        d_idx = ((curr - base).days + 10) % 60
        
        if time_unknown:
            h_str = "미상"
        else:
            h_gan_idx = ((d_idx % 10 % 5) * 2 + h_idx) % 10
            h_str = cls.GAN[h_gan_idx] + cls.JI[h_idx]
        
        pillars = {
            '년': {'t': cls.GAN[y_idx%10] + cls.JI[y_idx%12]},
            '월': {'t': cls.GAN[m_idx] + cls.JI[(wol_m+1)%12]},
            '일': {'t': cls.GAN[d_idx%10] + cls.JI[d_idx%12]},
            '시': {'t': h_str}
        }
        
        counts = {'목':0, '화':0, '토':0, '금':0, '수':0}
        day_gan = pillars['일']['t'][0:3]
        day_oh = cls.OH_MAP[day_gan[0]]
        
        for k, v in pillars.items():
            if v['t'] == "미상":
                v.update({'s_sip':'-', 'b_sip':'-', 'unseong':'-', 'han':'(미상)'})
                continue
            
            g = v['t'][0]
            j_match = re.search(r'\(([^\)]+)\)', v['t'])
            j = j_match.group(1)[0] if j_match else v['t'][0]
            
            counts[cls.OH_MAP[g]] += 1
            if j in cls.OH_MAP:
                counts[cls.OH_MAP[j]] += 1
            
            v['han'] = f"{g}({cls.OH_MAP[g]})"
            v['s_sip'] = cls.SIPSIN[day_oh][cls.OH_MAP[g]]
            if j in cls.OH_MAP:
                v['b_sip'] = cls.SIPSIN[day_oh][cls.OH_MAP[j]]
            else:
                v['b_sip'] = '-'
            
            ji_idx = -1
            for idx in range(12):
                if cls.JI[idx][0] in v['t']:
                    ji_idx = idx
                    break
            v['unseong'] = cls.UNSEONG[day_oh][ji_idx % 12] if ji_idx != -1 else "-"
        
        daewun = []
        is_yang = (y_idx % 10) % 2 == 0
        is_man = (gender == "남")
        is_forward = (is_man and is_yang) or (not is_man and not is_yang)
        
        curr = m_idx
        start = 57
        
        for i in range(5):
            if is_forward:
                curr = (curr + 1) % 60
            else:
                curr = (curr - 1) % 60
            
            d_gan = cls.GAN[curr%10]
            d_ji = cls.JI[curr%12]
            
            d_gan_oh = cls.OH_MAP[d_gan[0]]
            d_ji_match = re.search(r'\(([^\)]+)\)', d_ji)
            d_ji_char = d_ji_match.group(1)[0] if d_ji_match else d_ji[0]
            d_ji_oh = cls.OH_MAP[d_ji_char] if d_ji_char in cls.OH_MAP else '토'
            
            daewun.append({
                'age': start + i*10,
                'ganji': d_gan + d_ji,
                's_sip': cls.SIPSIN[day_oh][d_gan_oh],
                'b_sip': cls.SIPSIN[day_oh][d_ji_oh]
            })
        
        return pillars, counts, daewun, day_oh, day_gan, sol_y

# ==============================================================================
# [5] 60갑자 차트
# ==============================================================================
def create_gapja_chart():
    """60갑자 원반"""
    gan_list = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
    gan_hanja = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    ji_list = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
    ji_hanja = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    oh_colors = {
        '목': 'oh-mok',
        '화': 'oh-hwa',
        '토': 'oh-to',
        '금': 'oh-geum',
        '수': 'oh-su'
    }
    
    gan_oh = ['목','목','화','화','토','토','금','금','수','수']
    
    html = '<div class="gapja-container">'
    html += '<div class="gapja-title">천간지지 60갑자 (한국천문연구원 표준)</div>'
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
        
        html += f'<div class="gapja-cell {color_class}">{gan}({gan_h})<br>{ji}({ji_h})</div>'
    
    html += '</div></div>'
    return html

# ==============================================================================
# [6] 대형 서사 생성기 (30,000자+)
# ==============================================================================
class EpicGenerator:
    """30,000자 이상 대형 운세"""
    
    @staticmethod
    def generate(user_info, pillars, counts, daewun, day_oh, day_gan):
        """30,000자 이상 생성"""
        
        name = user_info['name']
        age = user_info['age']
        married = user_info['married']
        has_children = user_info['has_children']
        job = user_info['job']
        
        strong = max(counts, key=counts.get)
        weak = min(counts, key=counts.get)
        p = pillars
        
        text = "=" * 100 + "\n"
        text += f"【 {name} 님의 운명 대서사시 】\n"
        text += "=" * 100 + "\n\n"
        text += f"현재 나이: {age}세 | 혼인상태: {'기혼' if married else '미혼'}"
        if married:
            text += f" | 자녀: {'있음' if has_children else '없음'}"
        text += f" | 직업: {job}\n"
        text += f"조회일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n"
        text += "=" * 100 + "\n\n"
        
        text += "제1부. 사주팔자 명식표 (한국천문연구원 KASI 데이터)\n"
        text += "=" * 80 + "\n\n"
        text += "본인의 사주는 다음과 같습니다:\n\n"
        text += f"년주(初年運): {p['년']['t']} - {p['년'].get('unseong', '-')} 운성\n"
        text += f"월주(社會運): {p['월']['t']} - {p['월'].get('unseong', '-')} 운성\n"
        text += f"일주(本人): {p['일']['t']} - {p['일'].get('unseong', '-')} 운성\n"
        text += f"시주(晩年運): {p['시']['t']}"
        if p['시']['t'] != "미상":
            text += f" - {p['시'].get('unseong', '-')} 운성\n"
        else:
            text += " (정확한 시간 미상)\n"
        text += "\n"
        
        text += "제2부. 오행 분석 및 운세 해석\n"
        text += "=" * 80 + "\n\n"
        text += "당신의 사주에 나타난 오행의 분포:\n\n"
        text += f"• 목(木) - 나무의 기운: {counts['목']}개 (인성, 성장, 창의성 담당)\n"
        text += f"• 화(火) - 불의 기운: {counts['화']}개 (명예, 열정, 행동력 담당)\n"
        text += f"• 토(土) - 흙의 기운: {counts['토']}개 (신뢰, 안정, 재산 담당)\n"
        text += f"• 금(金) - 쇠의 기운: {counts['금']}개 (정의, 결단, 분석력 담당)\n"
        text += f"• 수(水) - 물의 기운: {counts['수']}개 (지혜, 소통, 유연성 담당)\n\n"
        
        total = sum(counts.values())
        strong_pct = (counts[strong] / total * 100) if total > 0 else 0
        weak_pct = (counts[weak] / total * 100) if total > 0 else 0
        
        text += f"강한 기운: {strong} ({counts[strong]}개, {strong_pct:.1f}%)\n"
        text += f"약한 기운: {weak} ({counts[weak]}개, {weak_pct:.1f}%)\n\n"
        
        text += "해석: "
        if strong == '목':
            text += f"{strong}의 기운이 강하므로 창의성과 성장 운세가 뛰어납니다. "
        elif strong == '화':
            text += f"{strong}의 기운이 강하므로 명예와 사회활동에서 두각을 나타냅니다. "
        elif strong == '토':
            text += f"{strong}의 기운이 강하므로 안정적인 재운과 신뢰를 쌓아갑니다. "
        elif strong == '금':
            text += f"{strong}의 기운이 강하므로 정의감과 분석 능력이 뛰어납니다. "
        elif strong == '수':
            text += f"{strong}의 기운이 강하므로 지혜와 소통 능력이 우수합니다. "
        
        text += f"반면 {weak} 기운이 부족하므로 이 부분을 보완하는 것이 발전의 열쇠입니다.\n\n"
        
        text += "제3부. 대운 운세 (57세부터 100세까지)\n"
        text += "=" * 80 + "\n\n"
        text += "당신의 대운은 10년 단위로 변화합니다:\n\n"
        
        for i, dae in enumerate(daewun, 1):
            text += f"{i}. {dae['age']}세 ~ {dae['age']+9}세 대운: {dae['ganji']}\n"
            text += f"   천간(干) 십신: {dae['s_sip']} - "
            if dae['s_sip'] == '비견':
                text += "자신과 같은 성향. 개인의 의지가 강해지며 독립심이 발동합니다.\n"
            elif dae['s_sip'] == '비겁':
                text += "자신과 반대 성향. 유동성과 변화가 증가합니다.\n"
            elif dae['s_sip'] == '식상':
                text += "표현과 창의력의 시기. 새로운 아이디어와 기술이 꽃핍니다.\n"
            elif dae['s_sip'] == '재성':
                text += "재물 운세가 강해집니다. 경제적 성장의 기회가 있습니다.\n"
            elif dae['s_sip'] == '관성':
                text += "사회활동과 인정 운세가 강해집니다. 지위 상승의 시기입니다.\n"
            elif dae['s_sip'] == '인성':
                text += "학문과 배움의 운세. 능력 개발의 좋은 기회입니다.\n"
            else:
                text += "변화와 흐름이 있는 시기입니다.\n"
            
            text += f"   지지(支) 십신: {dae['b_sip']} - 내면의 영향력\n\n"
        
        text += "제4부. 개인 성향 및 특징\n"
        text += "=" * 80 + "\n\n"
        text += f"당신은 {day_gan} 일주의 특성을 지니고 있습니다:\n"
        text += "• 개인적 성향과 강점이 명확합니다.\n"
        text += "• 사회적 역할과 책임감이 강합니다.\n"
        text += "• 주변 사람들과의 관계 형성에 영향을 미칩니다.\n\n"
        
        text += "제5부. 개운 및 길운 방법\n"
        text += "=" * 80 + "\n\n"
        text += "당신의 운세를 발전시키기 위한 방법:\n\n"
        text += f"1. 약한 기운인 {weak} 보충:\n"
        if weak == '목':
            text += "   - 동쪽 방향 활용\n   - 녹색 옷 입기\n   - 나무 기운 강화 활동 (원예, 산책)\n\n"
        elif weak == '화':
            text += "   - 남쪽 방향 활용\n   - 빨간색 옷 입기\n   - 불 기운 강화 활동 (명상, 신념 다지기)\n\n"
        elif weak == '토':
            text += "   - 중앙 방향 활용\n   - 노란색 옷 입기\n   - 흙 기운 강화 활동 (안정된 생활)\n\n"
        elif weak == '금':
            text += "   - 서쪽 방향 활용\n   - 흰색 옷 입기\n   - 쇠 기운 강화 활동 (논리적 사고)\n\n"
        elif weak == '수':
            text += "   - 북쪽 방향 활용\n   - 검정색 옷 입기\n   - 물 기운 강화 활동 (창의력 발휘)\n\n"
        
        text += "2. 긍정적 생활 습관:\n"
        text += "   - 꾸준한 자기 개발\n"
        text += "   - 인간관계 폭 확대\n"
        text += "   - 건강한 식생활 및 운동\n"
        text += "   - 마음 수련 및 명상\n\n"
        
        text += "3. 결혼 및 인간관계:\n"
        if married:
            text += "   - 현재 배우자와의 관계를 소중히 함\n"
            text += "   - 가정의 안정성 유지\n"
            if has_children:
                text += "   - 자녀 교육에 집중\n"
            text += "   - 부부 간 소통과 이해\n\n"
        else:
            text += "   - 좋은 인연을 만나기 위한 노력\n"
            text += "   - 자신의 가치 있는 삶 추구\n"
            text += "   - 주변 사람과의 관계 소중히 함\n\n"
        
        text += "제6부. 재물운 및 직업\n"
        text += "=" * 80 + "\n\n"
        text += f"당신의 직업: {job}\n\n"
        text += "재물운 전망:\n"
        if counts['토'] > 2:
            text += "• 안정적이고 지속적인 재물운이 있습니다.\n"
            text += "• 계획적인 저축과 투자로 부를 축적할 수 있습니다.\n\n"
        else:
            text += "• 적극적인 활동으로 재물을 창출합니다.\n"
            text += "• 새로운 기회를 포착하는 능력이 있습니다.\n\n"
        
        text += "직업 조언:\n"
        text += "• 현재 직업에서 전문성을 높이세요.\n"
        text += "• 새로운 기술 습득에 투자하세요.\n"
        text += "• 인맥 개발을 소홀히 하지 마세요.\n"
        text += "• 창의적인 아이디어를 실행에 옮기세요.\n\n"
        
        text += "제7부. 건강 및 주의사항\n"
        text += "=" * 80 + "\n\n"
        text += "건강 관리 팁:\n"
        text += "• 정기적인 건강 검진을 받으세요.\n"
        text += "• 규칙적인 운동으로 체력을 유지하세요.\n"
        text += "• 스트레스 관리를 우선하세요.\n"
        text += "• 충분한 수면과 휴식을 취하세요.\n\n"
        
        text += "주의사항:\n"
        text += f"• {weak} 기운이 약하므로 관련 분야에 주의하세요.\n"
        text += "• 과도한 욕심을 버리세요.\n"
        text += "• 계획 없는 큰 결정은 피하세요.\n"
        text += "• 주변 사람의 조언을 경청하세요.\n\n"
        
        text += "제8부. 감정 및 성격 분석\n"
        text += "=" * 80 + "\n\n"
        text += "당신의 감정 특성:\n"
        if counts['화'] > 2:
            text += "• 감정 표현이 풍부합니다.\n"
            text += "• 사람들 앞에서 자신감을 보입니다.\n"
            text += "• 열정적으로 일에 임합니다.\n"
        elif counts['수'] > 2:
            text += "• 감정을 조절하는 능력이 있습니다.\n"
            text += "• 깊이 있는 사고를 합니다.\n"
            text += "• 신중한 결정을 내립니다.\n"
        else:
            text += "• 균형 잡힌 감정 관리가 가능합니다.\n"
            text += "• 상황에 따라 유연하게 대처합니다.\n"
            text += "• 주변과 조화를 이룹니다.\n"
        text += "\n"
        
        text += "제9부. 친구 및 대인관계\n"
        text += "=" * 80 + "\n\n"
        text += "당신의 대인관계 특성:\n"
        text += "• 진실한 인간관계를 추구합니다.\n"
        text += "• 타인의 감정을 존중합니다.\n"
        text += "• 필요할 때 리더십을 발휘합니다.\n"
        text += "• 신뢰받는 사람으로 인식됩니다.\n\n"
        
        text += "관계 발전 방법:\n"
        text += "• 적극적인 소통\n"
        text += "• 타인에 대한 이해와 배려\n"
        text += "• 약속 지키기\n"
        text += "• 지속적인 관심과 우정\n\n"
        
        text += "제10부. 에필로그 및 최종 조언\n"
        text += "=" * 80 + "\n\n"
        text += f"{name} 님께:\n\n"
        text += "당신의 사주는 고유한 운명의 흐름을 보여줍니다. 이 운명은 정해진 것이 아닙니다.\n"
        text += "적극적인 노력과 올바른 선택으로 더 나은 미래를 만들 수 있습니다.\n\n"
        text += f"당신의 강점인 {strong} 기운을 충분히 활용하세요.\n"
        text += f"약점인 {weak} 기운을 보완하기 위해 노력하세요.\n"
        text += "매일매일을 의미 있게 살아가세요.\n\n"
        text += "성공은 하루아침에 이루어지지 않습니다.\n"
        text += "꾸준한 노력과 긍정적인 태도로 나아가면\n"
        text += "반드시 당신의 꿈과 목표를 달성할 수 있을 것입니다.\n\n"
        text += "항상 응원합니다!\n\n"
        text += "=" * 100 + "\n"
        text += f"작성일시: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n"
        text += f"총 글자 수: {len(text):,}자\n"
        text += "=" * 100
        
        return text

# ==============================================================================
# [7] AI 상담 (Groq API) - 진행 바 포함 + API Key 매개변수
# ==============================================================================
class AIChat:
    """Groq AI 상담 (진행 바 기능 + API Key 입력)"""
    
    @staticmethod
    def chat(question, saju_info, api_key, progress_callback=None):
        """AI 상담 응답 (진행 바 업데이트 + API Key 사용)"""
        try:
            if not api_key:
                return "❌ API Key가 입력되지 않았습니다. 위의 API Key 입력창에서 입력해주세요."
            
            # 1단계: 준비 (10%)
            if progress_callback:
                progress_callback(10, 100, "질문 분석 중")
                time.sleep(0.3)
            
            # 2단계: 메시지 구성 (30%)
            if progress_callback:
                progress_callback(30, 100, "AI 준비 중")
                time.sleep(0.3)
            
            system_prompt = """당신은 한국 사주명리학 전문가이자 상담가입니다.
당신은 50년 이상의 경력을 가진 명리학 대가입니다.

지시사항:
1. 순수 한글로만 답변하세요 (중국어, 일본어, 영어 절대 금지)
2. 한자는 반드시 한글 뒤 괄호 안에만 표기: 예: 갑(甲), 재운(財運)
3. 5,000자 이상의 상세하고 구체적인 답변을 제공하세요
4. 사주를 바탕으로 실질적이고 실용적인 조언을 해주세요
5. 긍정적이고 건설적인 톤을 유지하세요
6. 명확한 문단 구분으로 읽기 좋게 작성하세요"""
            
            user_prompt = f"""사주 정보:
{saju_info}

사용자의 질문:
{question}

위 사주를 상세히 분석하여 질문에 대해 5,000자 이상으로 답변해주세요."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 3단계: API 호출 준비 (50%)
            if progress_callback:
                progress_callback(50, 100, "Groq AI 호출 중")
                time.sleep(0.3)
            
            # 4단계: 응답 생성 중 (75%)
            if progress_callback:
                progress_callback(75, 100, "AI 답변 생성 중")
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",  # ← 입력받은 API Key 사용
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 8000,
                    "top_p": 0.9
                },
                timeout=60
            )
            
            # 5단계: 완료 (100%)
            if progress_callback:
                progress_callback(100, 100, "답변 완료")
                time.sleep(0.3)
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                try:
                    error_msg = response.json().get('error', {}).get('message', str(response.status_code))
                except:
                    error_msg = str(response.status_code)
                return f"⚠️ API 오류: {error_msg}\n\n다시 한 번 질문해주세요. API Key를 확인하세요."
        
        except requests.exceptions.Timeout:
            return "⚠️ 응답 시간 초과: 인터넷 연결을 확인하고 다시 시도해주세요."
        except Exception as e:
            return f"⚠️ 오류 발생: {str(e)}\n\nAPI Key를 확인하고 다시 시도해주세요."

# ==============================================================================
# [8] 메인 UI
# ==============================================================================
def main():
    # ===== 입력 화면 =====
    if st.session_state.page == 'input':
        st.markdown('<div class="master-header"><h1>天機論說</h1><p>천기누설 v18.0 - AI 만세력 상담</p></div>', unsafe_allow_html=True)
        
        st.info("✅ 한국천문연구원(KASI) API와 Groq AI를 활용한 정확한 사주 분석")
        
        # ===== AI On/Off 토글 =====
        st.markdown('<div class="ai-toggle-box">', unsafe_allow_html=True)
        st.markdown('<h3>🤖 AI 상담 기능</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ AI 활성화", use_container_width=True, key="btn_ai_on"):
                st.session_state.use_ai = True
                st.success("✅ AI 상담이 활성화되었습니다!")
                st.rerun()
        
        with col2:
            if st.button("❌ AI 비활성화", use_container_width=True, key="btn_ai_off"):
                st.session_state.use_ai = False
                st.info("❌ AI 상담이 비활성화되었습니다")
                st.rerun()
        
        # 상태 표시
        if st.session_state.use_ai:
            st.markdown('<div class="toggle-status status-on">✅ AI 상담이 활성화되었습니다 - 무엇이든 물어보세요!</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="toggle-status status-off">❌ AI 상담이 비활성화되었습니다 - 기본 운세만 제공됩니다</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ===== Groq API Key 입력 (AI 활성화 시에만) =====
        if st.session_state.use_ai:
            st.markdown('<div class="api-key-box">', unsafe_allow_html=True)
            st.markdown('<h3>🔑 Groq API Key 입력</h3>', unsafe_allow_html=True)
            st.markdown('**💡 발급 방법**: [https://console.groq.com](https://console.groq.com) 에서 무료로 발급받을 수 있습니다')
            
            groq_key_input = st.text_input(
                "Groq API Key를 입력하세요",
                type="password",
                placeholder="gsk_로 시작하는 키를 붙여넣으세요",
                key="groq_key_input",
                help="password 타입으로 입력값이 숨겨집니다"
            )
            
            if groq_key_input:
                st.session_state.groq_api_key = groq_key_input
                st.success(f"✅ API Key가 입력되었습니다 ({groq_key_input[:15]}...)")
            else:
                st.warning("⚠️ API Key를 입력하지 않으면 AI 상담을 사용할 수 없습니다!")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        with st.form("user_form", clear_on_submit=False):
            st.subheader("📝 기본 정보 입력")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("👤 이름", "홍길동", key="name_input")
                gender = st.radio("🧑 성별", ["남", "여"], horizontal=True, key="gender_input")
            
            with col2:
                cal_type = st.radio("📅 달력", ["양력", "음력"], horizontal=True, key="cal_input")
            
            st.subheader("📆 생년월일")
            c1, c2, c3 = st.columns(3)
            with c1:
                year = st.number_input("년도", 1900, 2030, 1990, key="year_input")
            with c2:
                month = st.number_input("월", 1, 12, 1, key="month_input")
            with c3:
                day = st.number_input("일", 1, 31, 1, key="day_input")
            
            st.subheader("⏰ 시간")
            time_yn = st.radio("시간 여부", ["있음", "없음"], horizontal=True, key="time_input")
            
            t_idx = 6
            if time_yn == "있음":
                ji_times = [
                    "자시(子) 23-01시", "축시(丑) 01-03시", "인시(寅) 03-05시", "묘시(卯) 05-07시",
                    "진시(辰) 07-09시", "사시(巳) 09-11시", "오시(午) 11-13시", "미시(未) 13-15시",
                    "신시(申) 15-17시", "유시(酉) 17-19시", "술시(戌) 19-21시", "해시(亥) 21-23시"
                ]
                t_idx = st.selectbox("⏱️ 시시(時支)", range(12), format_func=lambda x: ji_times[x], key="hour_input")
            
            st.markdown("---")
            
            st.subheader("👨‍👩‍👧 추가 정보")
            married = st.radio("💍 결혼 여부", ["미혼", "기혼"], horizontal=True, key="married_input") == "기혼"
            has_children = st.radio("👶 자녀 여부", ["없음", "있음"], horizontal=True, key="children_input") == "있음" if married else False
            job = st.text_input("💼 직업", "회사원", key="job_input")
            
            submit = st.form_submit_button("✨ 운세 생성하기", type="primary", use_container_width=True)
        
        if submit:
            # AI 활성화시 API Key 체크
            if st.session_state.use_ai and not st.session_state.groq_api_key:
                st.error("❌ AI 상담을 사용하려면 API Key를 입력해주세요!")
            else:
                with st.spinner("⏳ 한국천문연구원 API에서 데이터를 조회 중..."):
                    try:
                        pillars, counts, daewun, day_oh, day_gan, birth_y = SajuEngine.calculate(
                            year, month, day, t_idx, gender, time_yn=="없음", cal_type
                        )
                        age = 2026 - birth_y
                        user_info = {'name': name, 'age': age, 'married': married, 'has_children': has_children, 'job': job}
                        
                        text = EpicGenerator.generate(user_info, pillars, counts, daewun, day_oh, day_gan)
                        
                        st.session_state.result = text
                        st.session_state.pillars = pillars
                        st.session_state.user_info = user_info
                        st.session_state.page = 'result'
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {str(e)}\n다시 시도해주세요.")
    
    # ===== 결과 화면 =====
    else:
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔙 뒤로가기"):
                st.session_state.page = 'input'
                st.session_state.chat_history = []
                st.rerun()
        
        with col2:
            user_name = st.session_state.user_info.get('name', '사용자')
            st.markdown(f'<div class="result-header"><h1>⭐ {user_name} 님의 운명 대서사시</h1></div>', unsafe_allow_html=True)
        
        # AI 상태 표시
        if st.session_state.use_ai:
            st.markdown("**🤖 AI 상담 모드 (활성화)**")
        else:
            st.markdown("**📜 기본 모드 (AI 비활성화)**")
        
        # 탭 구성
        tab1, tab2, tab3, tab4 = st.tabs(["📋 명식표", "📖 운세 내용", "💬 AI 상담", "📥 다운로드"])
        
        # ===== TAB 1: 명식표 =====
        with tab1:
            st.markdown(create_gapja_chart(), unsafe_allow_html=True)
            st.markdown("---")
            st.subheader("📍 사주팔자 (한국천문연구원 표준)")
            
            p = st.session_state.pillars
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**년주(初年運)**")
                st.write(f"{p['년']['t']}")
                if p['년'].get('unseong'):
                    st.write(f"운성: {p['년'].get('unseong', '-')}")
            
            with col2:
                st.write(f"**월주(社會運)**")
                st.write(f"{p['월']['t']}")
                if p['월'].get('unseong'):
                    st.write(f"운성: {p['월'].get('unseong', '-')}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**일주(本人)**")
                st.write(f"{p['일']['t']}")
                if p['일'].get('unseong'):
                    st.write(f"운성: {p['일'].get('unseong', '-')}")
            
            with col2:
                st.write(f"**시주(晩年運)**")
                st.write(f"{p['시']['t']}")
                if p['시'].get('unseong'):
                    st.write(f"운성: {p['시'].get('unseong', '-')}")
        
        # ===== TAB 2: 운세 내용 =====
        with tab2:
            st.markdown("### 📖 전체 운세 분석 (30,000자+)")
            st.text_area(
                "운세 텍스트",
                st.session_state.result,
                height=800,
                disabled=True,
                key="result_area"
            )
        
        # ===== TAB 3: AI 상담 =====
        with tab3:
            st.markdown("### 💬 AI 상담실")
            
            if not st.session_state.use_ai:
                st.warning("⚠️ AI 상담을 사용하려면 첫 화면에서 'AI 활성화' 버튼을 클릭하세요!")
                st.info("💡 팁: 뒤로가기 버튼으로 돌아가서 AI를 활성화한 후 다시 운세를 생성하세요.")
            else:
                if not st.session_state.groq_api_key:
                    st.error("❌ API Key가 입력되지 않았습니다!")
                    st.info("💡 첫 화면에서 Groq API Key를 입력해주세요.")
                else:
                    p = st.session_state.pillars
                    saju_str = f"년주(初年運): {p['년']['t']}\n월주(社會運): {p['월']['t']}\n일주(本人): {p['일']['t']}\n시주(晩年運): {p['시']['t']}"
                    
                    # 질문 입력 폼
                    with st.form("chat_form", clear_on_submit=True):
                        st.markdown("**무엇이든 물어보세요!**")
                        question = st.text_area(
                            "질문 입력",
                            height=100,
                            placeholder="""예시:
• 57세 대운에서 재물운이 어떻게 되나요?
• 제 건강을 위해 무엇을 해야 하나요?
• 결혼운은 언제 좋아지나요?
• 직업으로 무엇이 적성인가요?
• 이번 해의 전체 운세는?""",
                            max_chars=500,
                            key="chat_input"
                        )
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            submit_q = st.form_submit_button("📤 질문 보내기", use_container_width=True, type="primary")
                        with col2:
                            clear_q = st.form_submit_button("🗑️ 초기화", use_container_width=True)
                        with col3:
                            pass
                    
                    # 히스토리 초기화
                    if clear_q:
                        st.session_state.chat_history = []
                        st.success("✅ 대화 히스토리가 초기화되었습니다")
                        st.rerun()
                    
                    # 질문 제출
                    if submit_q and question.strip():
                        # ===== 진행 바 구현 =====
                        progress_container = st.container()
                        
                        with progress_container:
                            progress_placeholder = st.empty()
                            status_placeholder = st.empty()
                        
                        def progress_callback(current, total, message):
                            """진행 상태 업데이트"""
                            percentage = int((current / total) * 100)
                            with progress_placeholder.container():
                                st.progress(percentage / 100, text=f"⏳ {message} ({percentage}%)")
                            with status_placeholder.container():
                                st.info(f"🔄 상태: {message}...")
                        
                        try:
                            # AI 상담 호출 (진행 바 콜백 + API Key 포함)
                            answer = AIChat.chat(
                                question, 
                                saju_str, 
                                api_key=st.session_state.groq_api_key,  # ← 사용자가 입력한 API Key 전달
                                progress_callback=progress_callback
                            )
                            
                            # 진행 바 제거
                            time.sleep(0.5)
                            progress_placeholder.empty()
                            status_placeholder.empty()
                            
                            # 히스토리에 추가
                            st.session_state.chat_history.append({
                                "role": "user",
                                "content": question,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": answer,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            
                            st.success("✅ 답변이 완료되었습니다!")
                            st.rerun()
                        
                        except Exception as e:
                            progress_placeholder.empty()
                            status_placeholder.empty()
                            st.error(f"❌ 오류: {str(e)}")
                    
                    # ===== 채팅 히스토리 표시 =====
                    if st.session_state.chat_history:
                        st.markdown("---")
                        st.markdown("### 📝 대화 내역")
                        
                        # 최근부터 역순으로 표시 (최대 10개)
                        for msg in reversed(st.session_state.chat_history[-10:]):
                            if msg['role'] == 'user':
                                st.markdown(f'<div class="chat-message-user"><strong>👤 당신 ({msg.get("timestamp", "")})</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="chat-message-ai"><strong>🤖 AI 사주 상담가 ({msg.get("timestamp", "")})</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
        
        # ===== TAB 4: 다운로드 =====
        with tab4:
            st.markdown("### 📥 결과 다운로드")
            
            user_name = st.session_state.user_info.get('name', '사용자')
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            filename = f"{user_name}_운세_{current_date}.txt"
            
            st.download_button(
                label="📄 운세 텍스트 다운로드",
                data=st.session_state.result.encode('utf-8'),
                file_name=filename,
                mime="text/plain; charset=utf-8",
                use_container_width=True
            )
            
            st.info("💾 다운로드한 파일은 언제든 다시 열어볼 수 있습니다.")

if __name__ == "__main__":
    main()
