import streamlit as st
import google.generativeai as genai
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timezone, timedelta

# 한국 시간(KST) 설정
KST = timezone(timedelta(hours=9))
import json
import os
import tempfile
import base64
from modules import phase2_similar_cases
from modules import chat_script_generator
from core import unified_script_generator as generator

# 페이지 설정
st.set_page_config(
    page_title="TM SEED 🌱",
    page_icon="🌱",
    layout="wide"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 타이틀
st.markdown('<div class="main-header">🌱 TM SEED</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666; margin-top: -1.5rem; margin-bottom: 2rem;">Script Evaluation & Education Development</p>', unsafe_allow_html=True)

# Gemini API 설정
@st.cache_resource
def setup_gemini():
    """Gemini API 초기화"""
    try:
        api_key = st.secrets["google"]["api_key"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        return model
    except Exception as e:
        st.error(f"Gemini API 설정 실패: {str(e)}")
        return None

# Google Sheets 설정
@st.cache_resource
def setup_sheets():
    """Google Sheets 연결"""
    try:
        # Streamlit Secrets에서 서비스 계정 정보 가져오기
        service_account_info = dict(st.secrets["gcp_service_account"])
        
        # 인증 설정
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Google Sheets 연결 실패: {str(e)}")
        st.info("secrets.toml에 gcp_service_account 정보를 추가해주세요.")
        return None

@st.cache_data(ttl=86400)
def load_tcrew_master():
    """NPS Raw Data에서 T크루 마스터 로드"""
    try:
        client = setup_sheets()
        if not client:
            return []
        
        # NPS Raw Data 시트 열기
        nps_sheet_url = st.secrets["google"]["nps_raw_sheet_url"]
        spreadsheet = client.open_by_url(nps_sheet_url)
        worksheet = spreadsheet.worksheet("세부")
        
        # 전체 데이터 로드
        data = worksheet.get_all_records()
        
        # T크루 정보 추출 (중복 제거)
        tcrew_dict = {}
        for row in data:
            tcrew_id = row.get('담당자ID', '')
            if tcrew_id and tcrew_id not in tcrew_dict:
                tcrew_dict[tcrew_id] = {
                    'T크루ID': row.get('담당자ID', ''),
                    '이름': row.get('담당자', ''),
                    '마케팅팀명': row.get('마케팅팀명', ''),
                    '대리점코드': row.get('대리점', ''),
                    '대리점명': row.get('대리점명', ''),
                    '매장코드': row.get('매장', ''),
                    '매장명': row.get('매장명', '')
                }
        
        return list(tcrew_dict.values())
    except Exception as e:
        st.error(f"T크루 데이터 로드 실패: {str(e)}")
        return []

def analyze_audio_with_gemini(audio_file, model):
    """Gemini로 오디오 분석"""
    
    prompt = """당신은 텔레마케팅(TM) 통화 품질 분석 전문가입니다.

업로드된 통화 녹음을 분석하여 JSON 형식으로 출력해주세요.

## 분석 항목

{
  "통화시간_초": 180,
  "분석날짜": "2026-01-27",
  "내용요약": "3-4문장으로 통화 내용 요약",
  "고객니즈": "고객의 주요 관심사",
  "통화결과": "성공/보류/거절/기타 중 선택",
  
  "점수평가": {
    "인사_및_오프닝": "0-10점",
    "니즈파악_질문": "0-10점", 
    "제안_설득력": "0-10점",
    "마무리_클로징": "0-10점"
  },
  
  "말투분석": {
    "말하기속도": "느림/적당/빠름",
    "목소리톤": "친근함/전문적/딱딱함",
    "톤적절성_점수": "0-10점",
    "침묵활용": "적절함/부족함/과다함",
    "자신감수준": "0-10점",
    "공감표현": "0-10점"
  },
  
  "강점": ["잘한 점 3가지"],
  "개선점": ["보완 필요한 점 3가지"],
  "코칭조언": ["구체적 팁 2가지"],
  
  "우수사례": {
    "활용가능": true 또는 false,
    "이유": "우수 사례인 이유",
    "종합점수": 88
  },
  
  "추천스크립트": "이 상황에 더 효과적인 대화 예시",
  "억양가이드": "말투 및 타이밍 가이드"
}

중요: 
1. 반드시 유효한 JSON 형식으로만 출력하세요.
2. 추가 설명이나 마크다운은 포함하지 마세요.
3. 숫자, 모델명, 요금은 녹음에서 들린 그대로 정확히 기록하세요.
4. 모든 점수는 숫자만 입력하세요 (예: "종합점수": 88, "점" 문자 붙이지 말 것)

참고: 2026년 1월 기준 최신 스마트폰 기종
- 아이폰: iPhone 17 시리즈 (17, 17 Pro, 17 Pro Max, Air)
- 삼성 갤럭시: Galaxy S25, S25+, S25 Ultra
- 삼성 폴더블: Galaxy Z Flip7, Galaxy Z Fold7
- 이전 모델(iPhone 16, Galaxy S24 등)을 최신 기종으로 언급하지 마세요.
- 개선점 작성 시 위 최신 기종을 참고하여 정확하게 제안하세요."""

    try:
        # 오디오 파일 직접 읽기
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        # MIME 타입 결정
        import mimetypes
        mime_type, _ = mimetypes.guess_type(audio_file)
        if not mime_type:
            mime_type = 'audio/mpeg'
        
        # Gemini Part 생성
        audio_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(audio_data).decode("utf-8")
            }
        }       
 
        # 분석 요청
        response = model.generate_content([prompt, audio_part])
        
        # JSON 파싱
        result_text = response.text.strip()
        
        # JSON 마크다운 제거
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        result = json.loads(result_text.strip())
        
        return result
    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
        return None

def generate_html_for_call_analysis(result, tcrew_info):
    """통화 분석 결과를 HTML로 변환 (PDF 인쇄용)"""
    
    # 기본 정보 추출
    통화결과 = result.get("통화결과", "N/A")
    통화시간 = result.get("통화시간_초", "N/A")
    
    # 우수사례 및 종합점수
    우수사례 = result.get("우수사례", {})
    종합점수_raw = 우수사례.get("종합점수", "0")
    if isinstance(종합점수_raw, (int, float)):
        종합점수 = int(종합점수_raw)
    elif isinstance(종합점수_raw, str):
        종합점수_str = 종합점수_raw.replace("점", "").strip()
        종합점수 = int(종합점수_str) if 종합점수_str.isdigit() else 0
    else:
        종합점수 = 0
    
    # 등급 계산
    if 종합점수 >= 90:
        grade = "🏆 우수"
    elif 종합점수 >= 70:
        grade = "😊 양호"
    elif 종합점수 >= 50:
        grade = "😐 보통"
    else:
        grade = "😟 개선필요"
    
    점수평가 = result.get("점수평가", {})
    말투분석 = result.get("말투분석", {})
    
    # HTML 생성
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통화 분석 결과 - {tcrew_info.get('이름', 'N/A')}</title>
    <style>
        @media print {{
            @page {{ margin: 1.5cm; }}
            body {{ margin: 0; }}
        }}
        body {{
            font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #0068C9;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #0068C9;
            font-size: 28px;
            margin: 0 0 10px 0;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .info-item {{
            text-align: center;
        }}
        .info-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .info-value {{
            font-size: 20px;
            font-weight: bold;
            color: #0068C9;
        }}
        h3 {{
            color: #0068C9;
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .score-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .score-label {{
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }}
        .score-value {{
            font-size: 24px;
            font-weight: bold;
            color: #0068C9;
        }}
        .content-box {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #0068C9;
        }}
        .success-box {{
            background: #d4edda;
            border-left-color: #28a745;
        }}
        .warning-box {{
            background: #fff3cd;
            border-left-color: #ffc107;
        }}
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .analysis-item {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
        }}
        .analysis-item strong {{
            color: #d9534f;
            font-weight: 700;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        li {{
            margin-bottom: 8px;
            line-height: 1.6;
        }}
        .script-box {{
            background: #fff3cd;
            padding: 20px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            border-left: 4px solid #ffc107;
            margin-bottom: 20px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📞 통화 분석 결과</h1>
        <div class="subtitle">🌱TM SEED - Script Evaluation & Education Development</div>
    </div>
    
    <div class="info-grid">
        <div class="info-item">
            <div class="info-label">통화 결과</div>
            <div class="info-value">{통화결과}</div>
        </div>
        <div class="info-item">
            <div class="info-label">통화 시간</div>
            <div class="info-value">{통화시간}초</div>
        </div>
        <div class="info-item">
            <div class="info-label">종합 점수</div>
            <div class="info-value">{종합점수}점</div>
        </div>
        <div class="info-item">
            <div class="info-label">등급</div>
            <div class="info-value">{grade}</div>
        </div>
    </div>
    
    <h3>📋 세부 평가 점수</h3>
    <div class="score-grid">
"""
    
    평가항목 = [
        ("인사_및_오프닝", "인사/오프닝"),
        ("니즈파악_질문", "니즈파악"),
        ("제안_설득력", "제안/설득"),
        ("마무리_클로징", "마무리")
    ]
    
    for key, label in 평가항목:
        if key in 점수평가:
            점수_값 = 점수평가[key]
            if isinstance(점수_값, str):
                점수_값 = int(점수_값) if 점수_값.isdigit() else 0
            html_content += f"""        <div class="score-item">
            <div class="score-label">{label}</div>
            <div class="score-value">{점수_값}/10</div>
        </div>
"""
    
    html_content += """    </div>
"""
    
    html_content += f"""    <h3>💬 통화 내용 요약</h3>
    <div class="content-box">{result.get("내용요약", "")}</div>
    
    <h3>🎯 고객 니즈</h3>
    <div class="content-box success-box">{result.get("고객니즈", "")}</div>
    
    <h3>🗣️ 말투 분석</h3>
    <div class="analysis-grid">
"""
    
    if 말투분석:
        톤점수_raw = 말투분석.get('톤적절성_점수', '0')
        톤점수 = int(톤점수_raw) if isinstance(톤점수_raw, str) and 톤점수_raw.isdigit() else 0
        자신감_raw = 말투분석.get('자신감수준', '0')
        자신감 = int(자신감_raw) if isinstance(자신감_raw, str) and 자신감_raw.isdigit() else 0
        공감_raw = 말투분석.get('공감표현', '0')
        공감 = int(공감_raw) if isinstance(공감_raw, str) and 공감_raw.isdigit() else 0
        
        html_content += f"""        <div class="analysis-item">
            <strong>말하기 속도:</strong> {말투분석.get('말하기속도', 'N/A')}<br>
            <strong>침묵 활용:</strong> {말투분석.get('침묵활용', 'N/A')}
        </div>
        <div class="analysis-item">
            <strong>목소리 톤:</strong> {말투분석.get('목소리톤', 'N/A')}<br>
            <strong>톤 적절성:</strong> {톤점수}/10
        </div>
        <div class="analysis-item">
            <strong>자신감:</strong> {자신감}/10<br>
            <strong>공감 표현:</strong> {공감}/10
        </div>
"""
    
    html_content += """    </div>
"""
    
    강점_list = result.get("강점", [])
    if 강점_list:
        html_content += """    <h3>✅ 강점</h3>
    <ul>
"""
        for strength in 강점_list:
            html_content += f"        <li>{strength}</li>\n"
        html_content += """    </ul>
"""
    
    개선점_list = result.get("개선점", [])
    if 개선점_list:
        html_content += """    <h3>📈 개선점</h3>
    <ul>
"""
        for improvement in 개선점_list:
            html_content += f"        <li>{improvement}</li>\n"
        html_content += """    </ul>
"""
    
    코칭조언_list = result.get("코칭조언", [])
    if 코칭조언_list:
        html_content += """    <h3>💡 코칭 조언</h3>
"""
        for idx, advice in enumerate(코칭조언_list, 1):
            html_content += f"""    <div class="content-box warning-box">
        <strong>조언 {idx}:</strong> {advice}
    </div>
"""
    
    if 우수사례.get("활용가능"):
        html_content += f"""    <h3>🌟 우수 사례</h3>
    <div class="content-box success-box">
        <strong>이 통화는 우수 사례로 활용 가능합니다!</strong><br><br>
        <strong>이유:</strong> {우수사례.get('이유', '')}
    </div>
"""
    
    추천스크립트 = result.get("추천스크립트", "")
    if 추천스크립트:
        html_content += f"""    <h3>📝 추천 스크립트</h3>
    <div class="script-box">{추천스크립트}</div>
"""
    
    억양가이드 = result.get("억양가이드", "")
    if 억양가이드:
        html_content += f"""    <h3>🎵 억양 가이드</h3>
    <div class="content-box">{억양가이드}</div>
"""
    
    html_content += f"""    <div class="footer">
        <p>상담사: {tcrew_info.get('이름', 'N/A')} (ID: {tcrew_info.get('T크루ID', 'N/A')})</p>
        <p>소속: {tcrew_info.get('마케팅팀명', 'N/A')} / {tcrew_info.get('매장명', 'N/A')}</p>
        <p>생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
    
    return html_content

def display_script_with_colors(script_text):
    """실전 스크립트를 Chat 스크립트 스타일로 표시 (제목 1.15em, ### 제거)"""
    import re
    
    # 1. SECTION 태그 제거
    cleaned_text = re.sub(r'</?SECTION:\w+>', '', script_text)
    
    # 2. ### 제거
    cleaned_text = re.sub(r'###\s+', '', cleaned_text)
    
    # 3. # 기호 제거 (1️⃣, #말투 등)
    cleaned_text = re.sub(r'^#\s*', '', cleaned_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r'\n#\s*', '\n', cleaned_text)
    
    # 4. ** 별표 제거 (문장 앞뒤)
    cleaned_text = re.sub(r'\*\*', '', cleaned_text)
    
    # 5. ## 제거 (1️⃣, 2️⃣ 등의 크기 통일)
    cleaned_text = re.sub(r'##\s+', '', cleaned_text)
    
    # 6. "미리 확인해야 할 사항" → "TM대상군 분류 및 사전 준비사항"
    cleaned_text = cleaned_text.replace("📌 미리 확인해야 할 사항", "📌 TM대상군 분류 및 사전 준비사항")
    cleaned_text = cleaned_text.replace("미리 확인해야 할 사항", "TM대상군 분류 및 사전 준비사항")
    
    # 7. 중복 제목 삭제
    cleaned_text = cleaned_text.replace("[TM 대상군 분류 및 사전 준비사항]", "")
    
    # 섹션별로 분리 (---)
    sections = cleaned_text.split("---")
    
    for part in sections:
        content = part.strip()
        
        # 빈 섹션 건너뛰기
        if not content or len(content) < 5:
            continue
        
        # 첫 줄 = 제목, 나머지 = 본문
        lines = content.split('\n', 1)
        first_line = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        
        # 제목 처리
        # 1. 오프닝 섹션 → "💬 오프닝 추천"
        if "1️⃣ 오프닝" in content and "옵션 1" in content:
            title = "💬 오프닝 추천"
            # "💬 TM 스크립트" 제목 제거
            body = content.replace("💬 TM 스크립트", "").strip()
        # 2. TM 스크립트 섹션 (1️⃣~4️⃣ 포함) → "💬 TM 스크립트"
        elif ("1️⃣ 도입" in content or "2️⃣" in content or "3️⃣" in content or "4️⃣" in content):
            title = "💬 TM 스크립트"
            # "💬 TM 스크립트" 제목 제거
            body = content.replace("💬 TM 스크립트", "").strip()
        # 3. 그 외 (제목 있는 섹션)
        else:
            title = first_line
        
        # 섹션 색상 결정
        if "TM대상군" in content or "미리 확인" in content or "📌" in title:
            # 파란색 박스
            st.markdown(f"""
            <div style="background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="font-size: 1.3em; font-weight: 700; color: #2c5aa0; margin-top: 0; margin-bottom: 15px;">{title}</h3>
                <div style="font-size: 14px; color: #333;">{body.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
        elif "TM 스크립트" in title or "오프닝" in title or "💬" in title:
            # 초록색 박스
            st.markdown(f"""
            <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="font-size: 1.3em; font-weight: 700; color: #2c5aa0; margin-top: 0; margin-bottom: 15px;">{title}</h3>
                <div style="font-size: 14px; color: #333;">{body.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
        elif "비언어적 코칭" in content or "🎭" in title:
            # 노란색 박스
            st.markdown(f"""
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="font-size: 1.3em; font-weight: 700; color: #2c5aa0; margin-top: 0; margin-bottom: 15px;">{title}</h3>
                <div style="font-size: 14px; color: #333;">{body.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            if content.strip():
                st.markdown(content)

def remove_section_markers(text):
    """SECTION 태그 제거 (다운로드용)"""
    import re
    # <SECTION:xxx> 와 </SECTION:xxx> 모두 제거
    cleaned = re.sub(r'<SECTION:[A-Z]+>\n?', '', text)
    cleaned = re.sub(r'</SECTION:[A-Z]+>\n?', '', cleaned)
    return cleaned

def generate_script_html(script_text):
    """실전 스크립트를 HTML로 변환 (Chat 스크립트와 완전 동일한 스타일)"""
    import re
    
    # 1. SECTION 태그 완전히 제거
    cleaned_text = re.sub(r'</?SECTION:\w+>', '', script_text)
    cleaned_text = re.sub(r'SECTION:\w+', '', cleaned_text)
    cleaned_text = re.sub(r'</>', '', cleaned_text)
    
    # 2. # 기호 제거 (1️⃣, #말투 등)
    cleaned_text = re.sub(r'^#\s*', '', cleaned_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r'\n#\s*', '\n', cleaned_text)
    
    # 3. "미리 확인해야 할 사항" → "TM대상군 분류 및 사전 준비사항"
    cleaned_text = cleaned_text.replace("### 📌 미리 확인해야 할 사항", "### 📌 TM대상군 분류 및 사전 준비사항")
    cleaned_text = cleaned_text.replace("미리 확인해야 할 사항", "TM대상군 분류 및 사전 준비사항")
    
    # 4. 중복 제목 삭제
    cleaned_text = cleaned_text.replace("[TM 대상군 분류 및 사전 준비사항]", "")
    
    # 섹션 색상
    section_colors = {
        "INFO": "#d1ecf1",      # 파란색
        "SCRIPT": "#d4edda",    # 초록색
        "COACHING": "#fff3cd",  # 노란색
    }
    
    # HTML 본문 구성
    html_body = ""
    
    # 섹션별로 분리 (---)
    sections = cleaned_text.split("---")
    
    for part in sections:
        content = part.strip()
        
        # 빈 섹션 건너뛰기
        if not content or len(content) < 5:
            continue
        
        # 섹션 색상 결정
        if "TM대상군" in content or "미리 확인" in content:
            bg_color = section_colors["INFO"]
        elif "TM 스크립트" in content or "오프닝" in content:
            bg_color = section_colors["SCRIPT"]
        elif "비언어적 코칭" in content:
            bg_color = section_colors["COACHING"]
        else:
            bg_color = "#f8f9fa"
        
        # 모든 이모지 제목을 h3로 변환
        emoji_pattern = r'(^|\n)(###?|##?)?\s*(📌|💬|🎭|🎯|💡|🔍|✨|⚡|📋|🎁|🏆)\s*([^\n<]+?)(?=\n|<br>|$)'
        
        def replace_emoji_header(match):
            newline = match.group(1) if match.group(1) else ''
            emoji = match.group(3)
            text = match.group(4).strip()
            return f'{newline}<h3>{emoji} {text}</h3>'
        
        content = re.sub(emoji_pattern, replace_emoji_header, content)
        
        # # 제거 (문장 앞의 모든 #)
        content = re.sub(r'(^|\n)#+\s*', r'\1', content)
        
        # 특수 처리: "💬 TM 스크립트" 분리
        sections_split = content.split('<h3>💬 TM 스크립트</h3>')
        
        if len(sections_split) > 1:
            result = sections_split[0]
            
            for i, section in enumerate(sections_split[1:], 1):
                next_h3_pos = section.find('<h3>')
                if next_h3_pos != -1:
                    section_content = section[:next_h3_pos]
                    remaining = section[next_h3_pos:]
                else:
                    section_content = section
                    remaining = ''
                
                # 첫 번째 TM 스크립트 섹션 (오프닝 옵션 있음) → "오프닝 추천"
                if i == 1 and ('옵션 1' in section_content or 'option-label' in section_content):
                    result += '<h3>💬 오프닝 추천</h3>' + section_content + remaining
                # 두 번째 TM 스크립트 섹션 (1️⃣~4️⃣) → "TM 스크립트"
                else:
                    result += '<h3>💬 TM 스크립트</h3>' + section_content + remaining
            
            content = result
        # 제목 없는 TM 스크립트 섹션 → 제목 추가
        elif ("1️⃣ 도입" in content or "1️⃣ 오프닝" in content or "2️⃣" in content or "3️⃣" in content or "4️⃣" in content) and "<h3>💬" not in content:
            content = '<h3>💬 TM 스크립트</h3><br>' + content
        
        # 특수 케이스 처리
        content = content.replace('<h3>📌 미리 확인해야 할 사항</h3>', '<h3>📌 TM대상군 분류 및 사전 준비사항</h3>')
        
        # 1. A그룹/B그룹 색상 처리
        content = re.sub(
            r'- (A그룹|B그룹)\(([^)]+)\):',
            r'- <span class="group-label">\1(\2):</span>',
            content
        )
        content = re.sub(
            r'- (A그룹|B그룹) \(([^)]+)\):',
            r'- <span class="group-label">\1 (\2):</span>',
            content
        )
        
        # 2. 오프닝 옵션 색상 처리
        content = re.sub(
            r'\*\*(옵션 \d+[^:]*?):\*\*',
            r'<span class="option-label">\1:</span>',
            content
        )
        
        # 3. 비언어적 코칭 "- xxx:" 패턴 빨간색
        content = re.sub(
            r'- ([^:\n]{2,50}?):(?=\s)',
            r'- <strong>\1</strong>:',
            content
        )
        
        # 4. 나머지 마크다운 변환
        content = re.sub(r'####\s+(.+)', r'<h4>\1</h4>', content)
        
        # 5. 줄바꿈 처리
        content = re.sub(r'</h3>\n+', '</h3><br>', content)  # h3 다음 1줄
        content = re.sub(r'</h4>\n', '</h4><br>', content)  # h4 다음 1줄
        content = re.sub(r'\n\n', '<br><br>', content)  # 2줄 공백 유지
        content = re.sub(r'\n', '<br>', content)  # 1줄 → <br>
        
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        
        # 섹션에 색상 박스 추가
        html_body += f"""
    <div style="background-color: {bg_color}; border-left: 4px solid {'#17a2b8' if bg_color == '#d1ecf1' else '#28a745' if bg_color == '#d4edda' else '#ffc107'}; padding: 20px; border-radius: 8px; margin: 20px 0;">
        {content}
    </div>
"""
    
    # 최종 HTML 템플릿 (Chat 스크립트와 동일)
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TM 실전 스크립트</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f9f9f9;
            font-size: 14px;
        }}
        
        h1, h2, h3, h4 {{
            color: #1f77b4;
            margin-top: 20px;
            margin-bottom: 15px;
        }}
        
        h1 {{
            font-size: 1.8em;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 10px;
        }}
        
        h2 {{
            font-size: 1.4em;
            color: #2c5aa0;
            margin-top: 25px;
            font-weight: 700;
        }}
        
        h3 {{
            font-size: 1.3em;
            color: #2c5aa0;
            margin-top: 0px;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        h4 {{
            font-size: 1.15em;
            color: #3d6fb5;
            margin-top: 15px;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        
        p {{
            margin: 10px 0;
            font-size: 14px;
            color: #333;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
            font-size: 14px;
            color: #333;
        }}
        
        strong {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        .coaching-subtitle {{
            color: #333;
            font-weight: 700;
        }}
        
        .group-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        .option-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 30px 0;
        }}
        
        @media print {{
            body {{
                background-color: white;
                margin: 0;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <h1>🌱 TM SEED 스크립트</h1>
    <p style="color: #666; font-size: 0.9em;">Script Evaluation & Education Development</p>
    <hr>
    {html_body}
</body>
</html>
"""
    return html_template

def save_to_sheets(client, result, filename):
    """Google Sheets에 결과 저장"""
    try:
        st.write("🔍 [디버그] save_to_sheets 함수 시작!")
        st.write(f"🔍 [디버그] client 객체: {client}")
        st.write(f"🔍 [디버그] filename: {filename}")
        
        # Sheets URL에서 스프레드시트 열기
        sheet_url = st.secrets["google"]["sheet_url"]
        st.write(f"🔍 [디버그] sheet_url: {sheet_url}")
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("분석결과")
        st.write(f"🔍 [디버그] worksheet 열기 성공! 시트명: {worksheet.title}")
        
        # T크루 정보 가져오기
        tcrew_info = st.session_state.get('selected_tcrew', {})
        
        # 우수사례에서 종합점수 추출 및 "점" 제거 처리
        우수사례 = result.get("우수사례", {})
        종합점수_raw = 우수사례.get("종합점수", "0")
        
        # 숫자 또는 문자열 처리 (방어 코드: "점" 제거)
        if isinstance(종합점수_raw, (int, float)):
            종합점수 = int(종합점수_raw)
        elif isinstance(종합점수_raw, str):
            # "88점" → "88" 변환
            종합점수_str = 종합점수_raw.replace("점", "").strip()
            종합점수 = int(종합점수_str) if 종합점수_str.isdigit() else 0
        else:
            종합점수 = 0
        
        # 새 행 데이터 준비 (T크루 정보 포함)
        new_row = [
            result.get("분석날짜", datetime.now().strftime("%Y-%m-%d")),
            tcrew_info.get('T크루ID', '미선택'),
            tcrew_info.get('이름', '미선택'),
            tcrew_info.get('마케팅팀명', ''),
            tcrew_info.get('대리점코드', ''),
            tcrew_info.get('대리점명', ''),
            str(tcrew_info.get('매장코드', '')).zfill(4) if tcrew_info.get('매장코드', '') else '',
            tcrew_info.get('매장명', ''),
            filename,
            result.get("통화결과", ""),
            result.get("내용요약", ""),
            result.get("통화시간_초", ""),
            종합점수,
            json.dumps(result, ensure_ascii=False)
        ]
        
        # 행 추가
        st.write(f"🔍 [디버그] 저장할 데이터 개수: {len(new_row)}개")
        st.write(f"🔍 [디버그] 첫 3개 값: {new_row[:3]}")
        worksheet.append_row(new_row, value_input_option='RAW')
        st.write("🔍 [디버그] append_row 완료!")

        # ← 여기 추가 (Streamlit에 바로 출력됨)
        st.success("시트에 행 추가 완료! (Google Sheet에서 확인하세요)")
        st.info(f"현재 시트 행 수: {len(worksheet.get_all_values())} 행")
        
        return True    
    except Exception as e:
        if 'permission' in str(e).lower() or 'insufficient' in str(e).lower():
            client_email = st.secrets["gcp_service_account"]["client_email"]
            st.error(f"권한 오류: Google Sheet에 '{client_email}'을 편집자(editor)로 공유해주세요.")
        else:
            st.error(f"저장 중 오류 발생: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False


def save_script_history_for_analysis(sheets_client, tcrew_info, analysis_result):
    """
    통화분석 실전활용 스크립트 이력 저장
    
    Args:
        sheets_client: Google Sheets 클라이언트
        tcrew_info (dict): T크루 정보
        analysis_result (dict): 통화 분석 결과
    
    Returns:
        bool: 저장 성공 여부
    """
    try:
        # TM_SEED_분석결과 파일 열기
        sheet_url = st.secrets["google"]["sheet_url"]
        spreadsheet = sheets_client.open_by_url(sheet_url)
        
        # 스크립트생성이력 시트 선택
        try:
            worksheet = spreadsheet.worksheet("스크립트생성이력")
        except:
            st.error("⚠️ '스크립트생성이력' 시트를 찾을 수 없습니다.")
            return False
        
        # 저장할 데이터 행 생성
        new_row = [
            datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),  # 분석일자
            tcrew_info.get('T크루ID', ''),                 # T크루ID
            tcrew_info.get('이름', ''),                     # 이름
            tcrew_info.get('마케팅팀명', ''),              # 마케팅팀명
            tcrew_info.get('대리점코드', ''),              # 대리점코드
            tcrew_info.get('대리점명', ''),                # 대리점명
            str(tcrew_info.get('매장코드', '')).zfill(4) if tcrew_info.get('매장코드', '') else '',  # 매장코드 (문자열 4자리)
            tcrew_info.get('매장명', ''),                  # 매장명
            f"통화분석 기반 실전 스크립트",                # 요청내용
            "실전 활용_AI프리미엄",                        # 스크립트 타입
            analysis_result.get('고객니즈', '')[:50]       # 키워드 (고객니즈 활용)
        ]
        
        # 시트에 행 추가
        worksheet.append_row(new_row, value_input_option='RAW')
        
        return True
        
    except Exception as e:
        st.error(f"⚠️ 스크립트 이력 저장 중 오류: {str(e)}")
        return False

# 메인 앱
def main():
    # API/Sheets 초기화 (사이드바 밖에서 먼저!)
    model = setup_gemini()
    sheets_client = setup_sheets()
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.divider()
        
# 메뉴 선택
        menu = st.radio(
            "메뉴 선택",
            ["🔍 통화 분석", "💬 Chat 스크립트"],
            index=0,
            horizontal=False
        )
        
        # 메뉴 전환 시 데이터 초기화
        if 'current_menu' not in st.session_state:
            st.session_state['current_menu'] = menu
        elif st.session_state['current_menu'] != menu:
            # 메뉴가 바뀌면 특정 데이터만 초기화
            keys_to_clear = [
                'analysis_result', 'phase2_generated_script', 'generated_script_full',
                'script_data', 'generated_script', 'selected_tcrew', 'selected_tcrew_chat'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['current_menu'] = menu
        
        st.divider()
        
        # API 상태 확인
        if model:
            st.success("✅ Gemini API 연결됨")
        else:
            st.error("❌ Gemini API 미연결")
            
        if sheets_client:
            st.success("✅ Google Sheets 연결됨")
        else:
            st.warning("⚠️ Google Sheets 미연결 - 관리자에게 문의해주세요.")
        
        st.divider()
        
        # 사용 방법
        with st.expander("📖 사용 방법"):
            if menu == "🔍 통화 분석":
                st.info("1. 통화 녹음 파일 업로드\n2. T크루 정보 선택\n3. 자동 분석 시작\n4. 결과 확인 및 저장")
            else:
                st.info("1. 원하는 스크립트 입력\n2. 우수사례 검색 또는 AI 프리미엄 생성\n3. TTS 음성 변환")
  
    # 메뉴별 화면 표시
    # ============================================================
    if menu == "💬 Chat 스크립트":
        # AI 스크립트 상담만 표시
        st.markdown("## 💬 AI 스크립트 상담")
        chat_script_generator.show_chat_script_page(model=model, sheets_client=sheets_client)
    else:
        # 통화 분석 표시 (기존 코드 계속)
    
        st.markdown("---")
        
        # ============================================================
        # 2. 통화 녹음 분석 (메인 화면)
        # ============================================================
        st.markdown("## 📞 통화 녹음 분석")
        
        # T크루 선택
        st.markdown("### 👤 T크루 정보")

        tcrew_list = load_tcrew_master()

        if tcrew_list:
            col1, col2 = st.columns([2, 1])
        
            with col1:
                search_term = st.text_input(
                    "🔍 T크루 검색",
                    placeholder="이름 또는 ID입력",
                    help="T크루 이름 또는 ID 일부만 입력하세요"
                )
        
            if search_term:
                # 검색어로 필터링
                filtered = [
                    t for t in tcrew_list 
                    if search_term.upper() in t['T크루ID'].upper() 
                    or search_term in t['이름']
                ]
            
                if filtered:
                    # 드롭다운 옵션
                    options = [
                        f"{t['이름']} ({t['T크루ID']}) - {t['매장명']}"
                        for t in filtered
                    ]
                
                    selected_option = st.selectbox(
                        "📋 매칭 결과",
                        options,
                        key="tcrew_select"
                    )
                
                    # 선택된 정보
                    selected_index = options.index(selected_option)
                    selected_tcrew = filtered[selected_index]
                
                    # 정보 확인
                    with st.expander("✅ 선택된 T크루 정보", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**이름:** {selected_tcrew['이름']}")
                            st.write(f"**T크루ID:** {selected_tcrew['T크루ID']}")
                            st.write(f"**팀:** {selected_tcrew['마케팅팀명']}")
                        with col2:
                            st.write(f"**대리점:** {selected_tcrew['대리점명']}")
                            st.write(f"**매장:** {selected_tcrew['매장명']}")
                
                    # Session state에 저장
                    st.session_state['selected_tcrew'] = selected_tcrew
                
                else:
                    st.warning("🔍 검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
            else:
                st.info("👆 T크루 이름 또는 ID를 입력하세요")
        else:
            st.warning("⚠️ T크루 데이터를 불러올 수 없습니다.")

        st.markdown("---")

        # 파일 업로드
        uploaded_file = st.file_uploader(
            "통화 녹음 파일을 업로드하세요 (mp3, wav, m4a)",
            type=['mp3', 'wav', 'm4a', 'ogg', 'flac']
        )

        if uploaded_file is not None:
            # 새 파일 업로드 시 이전 분석 결과 초기화
            if 'last_analyzed_file' not in st.session_state or st.session_state.get('last_analyzed_file') != uploaded_file.name:
                st.session_state['analysis_result'] = None
        
            st.success(f"✅ 파일 업로드됨: {uploaded_file.name}")
        
            # 오디오 플레이어
            st.audio(uploaded_file)
        
            # 자동 저장 토글 (눈에 안 띄게, 기본 OFF)
            with st.expander("⚙️ 고급 설정", expanded=False):
                auto_save = st.toggle(
                    "자동 저장",
                    value=True,
                    key="auto_save_toggle",
                    help="통화 분석 및 스크립트 생성 시 자동으로 Google Sheets에 저장합니다."
                )
                if auto_save:
                    st.caption("✅ 분석 결과 및 스크립트 이력이 자동 저장됩니다.")
                else:
                    st.caption("⚠️ 자동 저장 OFF - '저장' 버튼을 눌러야 저장됩니다.")
        
            # 분석 버튼
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                analyze_button = st.button("🔍 통화 분석 시작", use_container_width=True)
        
            if analyze_button:
                tcrew_info = st.session_state.get('selected_tcrew', None)
                if not tcrew_info or tcrew_info.get('T크루ID', '') in ['', '미선택']:
                    st.warning("⚠️ T크루 정보를 먼저 선택해주세요!")
                    st.stop()
                if st.session_state.get('is_analyzing', False):
                    st.warning("⏳ 이미 분석이 진행 중입니다. 잠시만 기다려주세요.")
                else:
                    st.session_state['is_analyzing'] = True
                
                    if not model:
                        st.error("Gemini API가 연결되지 않았습니다. secrets.toml을 확인해주세요.")
                        st.session_state['is_analyzing'] = False
                        return
                
                    try:
                        with st.spinner("🤖 AI가 통화를 분석 중입니다... (30-60초 소요)"):
                            # 임시 파일로 저장 (Windows 호환)
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                                tmp_file.write(uploaded_file.getbuffer())
                                temp_path = tmp_file.name
                        
                            # 분석 실행
                            result = analyze_audio_with_gemini(temp_path, model)
                        
                            # 임시 파일 삭제
                            os.remove(temp_path)
                        
                            # 분석 결과 저장
                            if result:
                                st.session_state['analysis_result'] = result
                                st.session_state['last_analyzed_file'] = uploaded_file.name
                                
                                # 자동 저장 (토글 ON일 때만)
                                if st.session_state.get('auto_save_toggle', False):
                                    if sheets_client and 'selected_tcrew' in st.session_state:
                                        try:
                                            save_result = save_to_sheets(sheets_client, result, uploaded_file.name)
                                            if save_result:
                                                st.toast("✅ 분석 결과가 자동 저장되었습니다!")
                                        except Exception as save_err:
                                            st.warning(f"⚠️ 자동 저장 중 오류: {str(save_err)}")
                
                    except Exception as e:
                        st.error(f"❌ 분석 중 오류 발생: {str(e)}")
                
                    finally:
                        st.session_state['is_analyzing'] = False
            
    # 분석 결과가 있으면 표시 (session_state 사용)
    if st.session_state.get('analysis_result'):
        result = st.session_state['analysis_result']
        st.balloons()
        
        # ============================================================
        # 액션 버튼 3개 (통화 분석 시작 바로 아래 배치)
        # ============================================================
        st.markdown("---")
        
        # CSS로 회색 버튼 스타일 추가
        st.markdown("""
        <style>
        /* 회색 버튼 스타일 */
        .stButton > button[kind="secondary"] {
            background-color: #4A4A4A !important;
            color: white !important;
            border: none !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background-color: #333333 !important;
            color: white !important;
        }
        /* 다운로드 버튼도 동일하게 */
        .stDownloadButton > button {
            background-color: #4A4A4A !important;
            color: white !important;
            border: none !important;
        }
        .stDownloadButton > button:hover {
            background-color: #333333 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
     
        with col1:
            # HTML 다운로드 (회색 secondary)
            if 'selected_tcrew' in st.session_state:
                tcrew_info = st.session_state['selected_tcrew']
                html_content = generate_html_for_call_analysis(result, tcrew_info)
                
                st.download_button(
                    label="📄 HTML 다운로드(PDF 인쇄용)",
                    data=html_content,
                    file_name=f"통화분석_{tcrew_info.get('이름', 'N/A')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    key="btn_download_html",
                    use_container_width=True
                )
            else:
                st.button("📄 HTML 다운로드(PDF 인쇄용)", disabled=True, key="btn_download_html_disabled", use_container_width=True)
        
        with col2:
            # 스크립트 생성 버튼 (회색 secondary)
            if st.button("📝 실전 스크립트 생성(Alice 4단 구조)", type="secondary", key="btn_script_gen", use_container_width=True):
                # 유사 케이스 먼저 검색 필요
                if sheets_client:
                    try:
                        sheet_url = st.secrets["google"]["sheet_url"]
                        similar_cases = phase2_similar_cases.run_similar_case_analysis(
                            sheets_client=sheets_client,
                            sheet_url=sheet_url,
                            current_result=result
                        )
                        
                        if similar_cases and len(similar_cases) > 0:
                            with st.spinner("🤖 AI가 실전 스크립트를 생성하는 중입니다... (5-10초 소요)"):
                                script = generator.generate_script(
                                    model=model,
                                    cases=similar_cases,
                                    user_request="",
                                    current_result=result
                                )
                                st.session_state['phase2_generated_script'] = script
                                
                                # 스크립트 생성 후 자동 저장 (토글 ON일 때만)
                                if st.session_state.get('auto_save_toggle', False):
                                    if 'selected_tcrew' in st.session_state:
                                        try:
                                            tcrew_info = st.session_state['selected_tcrew']
                                            script_save_result = save_script_history_for_analysis(
                                                sheets_client=sheets_client,
                                                tcrew_info=tcrew_info,
                                                analysis_result=result
                                            )
                                            if script_save_result:
                                                st.toast("✅ 스크립트 이력이 저장되었습니다!")
                                        except Exception as script_err:
                                            st.warning(f"⚠️ 스크립트 이력 저장 중 오류: {str(script_err)}")
                                
                                st.rerun()
                        else:
                            st.warning("💡 유사 케이스가 충분하지 않아 실전 스크립트를 생성할 수 없습니다.")
                    except Exception as e:
                        st.error(f"⚠️ 스크립트 생성 중 오류: {str(e)}")
                else:
                    st.error("⚠️ Google Sheets 연결이 필요합니다.")

        # 결과 표시
        st.markdown("---")
        st.subheader("📊 분석 결과")

        # 주요 정보
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("통화 결과", result.get("통화결과", "N/A"))
        with col2:
            통화시간 = result.get("통화시간_초", "N/A")
            st.metric("통화 시간", f"{통화시간}초")
        with col3:
            우수사례 = result.get("우수사례", {})
            종합점수_raw = 우수사례.get("종합점수", "0")
            # 점수 변환: 숫자/문자열 모두 처리
            if isinstance(종합점수_raw, (int, float)):
                종합점수 = int(종합점수_raw)
            elif isinstance(종합점수_raw, str):
                # "92점" → "92", "92" → 92
                종합점수_str = 종합점수_raw.replace("점", "").strip()
                종합점수 = int(종합점수_str) if 종합점수_str.isdigit() else 0
            else:
                종합점수 = 0
            st.metric("종합 점수", f"{종합점수}점")
        with col4:
            if 종합점수 >= 90:
                grade = "🏆 우수"
            elif 종합점수 >= 70:
                grade = "😊 양호"
            elif 종합점수 >= 50:
                grade = "😐 보통"
            else:
                grade = "😟 개선필요"
            st.metric("등급", grade)

        # 점수 평가 상세
        점수평가 = result.get("점수평가", {})
        if 점수평가:
            st.markdown("### 📋 세부 평가 점수")
            cols = st.columns(4)
            평가항목 = [
                ("인사_및_오프닝", "인사/오프닝"),
                ("니즈파악_질문", "니즈파악"),
                ("제안_설득력", "제안/설득"),
                ("마무리_클로징", "마무리")
            ]
            for idx, (key, label) in enumerate(평가항목):
                if key in 점수평가:
                    with cols[idx]:
                        점수_값 = 점수평가[key]
                        if isinstance(점수_값, str):
                            점수_값 = int(점수_값) if 점수_값.isdigit() else 0
                        st.metric(label, f"{점수_값}/10")

        # 내용 요약
        st.markdown("### 💬 통화 내용 요약")
        st.info(result.get("내용요약", ""))

        # 고객 니즈
        st.markdown("### 🎯 고객 니즈")
        st.success(result.get("고객니즈", ""))

        # 말투 분석
        st.markdown("### 🗣️ 말투 분석")
        말투분석 = result.get("말투분석", {})
        if 말투분석:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**말하기 속도:** {말투분석.get('말하기속도', 'N/A')}")
                침묵 = 말투분석.get('침묵활용', 'N/A')
                st.write(f"**침묵 활용:** {침묵}")
            with col2:
                st.write(f"**목소리 톤:** {말투분석.get('목소리톤', 'N/A')}")
                톤점수_raw = 말투분석.get('톤적절성_점수', '0')
                톤점수 = int(톤점수_raw) if isinstance(톤점수_raw, str) and 톤점수_raw.isdigit() else 0
                st.write(f"**톤 적절성:** {톤점수}/10")
            with col3:
                자신감_raw = 말투분석.get('자신감수준', '0')
                자신감 = int(자신감_raw) if isinstance(자신감_raw, str) and 자신감_raw.isdigit() else 0
                st.write(f"**자신감:** {자신감}/10")
                공감_raw = 말투분석.get('공감표현', '0')
                공감 = int(공감_raw) if isinstance(공감_raw, str) and 공감_raw.isdigit() else 0
                st.write(f"**공감 표현:** {공감}/10")

        # 강점
        st.markdown("### ✅ 강점")
        강점_list = result.get("강점", [])
        for idx, strength in enumerate(강점_list, 1):
            st.write(f"{idx}. {strength}")

        # 개선점
        st.markdown("### 📈 개선점")
        개선점_list = result.get("개선점", [])
        for idx, improvement in enumerate(개선점_list, 1):
            st.write(f"{idx}. {improvement}")

        # 코칭 조언
        st.markdown("### 💡 코칭 조언")
        코칭조언_list = result.get("코칭조언", [])
        for idx, advice in enumerate(코칭조언_list, 1):
            st.warning(f"**조언 {idx}:** {advice}")

        # 우수 사례 여부
        if 우수사례.get("활용가능"):
            st.markdown("### 🌟 우수 사례")
            st.success(f"**이 통화는 우수 사례로 활용 가능합니다!**\n\n**이유:** {우수사례.get('이유', '')}")

        # 추천 스크립트
        st.markdown("### 📝 추천 스크립트")
        추천스크립트 = result.get("추천스크립트", "")
        st.code(추천스크립트, language="text")

        # 억양 가이드
        st.markdown("### 🎵 억양 가이드")
        억양가이드 = result.get("억양가이드", "")
        st.info(억양가이드)

        # ============================================================
        # Phase 2: 유사 성공 케이스 검색 (전체 폭으로 표시)
        # ============================================================
        if sheets_client:
            try:
                sheet_url = st.secrets["google"]["sheet_url"]
            
                # Phase 2-1: 유사 케이스 검색
                similar_cases = phase2_similar_cases.run_similar_case_analysis(
                    sheets_client=sheets_client,
                    sheet_url=sheet_url,
                    current_result=result
                )
                
                # 생성된 스크립트 표시 (색상 박스)
                if 'phase2_generated_script' in st.session_state:
                    st.markdown("---")
                    st.markdown("## 📝 실전 활용 스크립트")
                    
                    # 섹션별 색상 박스로 표시
                    script_text = st.session_state['phase2_generated_script']
                    
                    # 다운로드 버튼 2개 (마크다운 + HTML)
                    col_html, col_md = st.columns(2)
                    
                    with col_html:
                        # HTML 생성 (Chat 스크립트 스타일)
                        html_content = generate_script_html(script_text)
                        st.download_button(
                            label="📄 HTML 다운로드 (PDF 인쇄용)",
                            data=html_content,
                            file_name=f"tm_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                            mime="text/html",
                            use_container_width=True
                        )

                    with col_md:
                        st.download_button(
                            label="📥 스크립트 다운로드 (.md)",
                            data=remove_section_markers(script_text),
                            file_name="tm_script.md",
                            mime="text/markdown",
                            use_container_width=True
                        )

                    display_script_with_colors(script_text)                    
             
            except Exception as e:
                st.warning(f"⚠️ 유사 케이스 검색 중 오류: {str(e)}")

if __name__ == "__main__":
    main()       