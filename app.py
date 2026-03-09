import streamlit as st
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go

# 한국 시간(KST) 설정
KST = timezone(timedelta(hours=9))

# 최신 단말기 정보 (한 곳에서만 관리)
def get_device_info():
    now = datetime.now(KST)
    s26_preorder = datetime(2026, 3, 6, tzinfo=KST)
    s26_launch   = datetime(2026, 3, 11, tzinfo=KST)

    s26_preorder_end = datetime(2026, 3, 5, 23, 59, tzinfo=KST)  # 사전예약 접수 마감
    s26_early_open   = datetime(2026, 3, 6, tzinfo=KST)           # 사전예약자 개통 시작
    s26_launch       = datetime(2026, 3, 11, tzinfo=KST)          # 공식 출시일

    if now <= s26_preorder_end:
        s26_status = "Galaxy S26 시리즈는 현재 사전예약 접수 중(3월 5일 마감, 3월 11일 공식 출시 예정)임 — 사전예약 혜택 중심으로 안내하세요."
    elif now < s26_launch:
        s26_status = (
            "Galaxy S26 시리즈는 사전예약 혜택 접수는 3월 5일 마감되었으나, "
            "매장 보유 재고로 즉시 개통 가능한 상태임(공식 출시일 3월 11일 임박) — "
            "'사전예약 혜택'이나 '사전예약 진행 중' 멘트는 절대 사용하지 말고, "
            "매장에서 바로 개통 가능한 최신 단말로 안내하세요."
        )
    else:
        s26_status = "Galaxy S26 시리즈는 공식 출시 완료된 최신 기종임 — 정상 판매 중으로 안내하세요."

    return f"""{now.strftime('%Y년 %m월 %d일')} 기준 최신 스마트폰 기종
- 아이폰: iPhone 17 시리즈 (17, 17 Pro, 17 Pro Max, Air)
- 삼성 갤럭시: Galaxy S25, S25+, S25 Ultra
- 삼성 폴더블: Galaxy Z Flip7, Galaxy Z Fold7
- {s26_status}
- 이전 모델(iPhone 16, Galaxy S24 등)을 최신 기종으로 언급하지 마세요."""
import json
import os
import tempfile
import base64
from modules import phase2_similar_cases
from modules import chat_script_generator
from core import unified_script_generator as generator
import dashboard_module as dashboard
import plotly.express as px

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
        client = genai.Client(api_key=api_key)
        return client
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
                    '매장코드': str(row.get('매장', '')).zfill(4) if str(row.get('매장', '')) != '' else '',
                    '매장명': row.get('매장명', '')
                }
        
        return list(tcrew_dict.values())
    except Exception as e:
        st.error(f"T크루 데이터 로드 실패: {str(e)}")
        return []

def analyze_audio_with_gemini(audio_file, client):
    """Gemini로 오디오 분석"""
    
    prompt = f"""당신은 텔레마케팅(TM) 통화 품질 분석 전문가입니다.

업로드된 통화 녹음을 분석하여 JSON 형식으로 출력해주세요.

## 분석 항목

{{
  "통화시간_초": 180,
  "분석날짜": "{datetime.now(KST).strftime('%Y-%m-%d')}",
  "내용요약": "3-4문장으로 통화 내용 요약",
  "고객니즈": "고객의 주요 관심사",
  "통화결과": "성공/보류/거절/기타 중 선택",
  
  "점수평가": {{
    "인사_및_오프닝": "0-10점",
    "니즈파악_질문": "0-10점", 
    "제안_설득력": "0-10점",
    "마무리_클로징": "0-10점"
  }},
  
  "말투분석": {{
    "말하기속도": "느림/적당/빠름",
    "목소리톤": "친근함/전문적/딱딱함",
    "톤적절성_점수": "0-10점 (상황에 맞는 톤 사용 여부)",
    "침묵활용": "적절함/부족함/과다함",
    "자신감수준": "0-10점 (목소리의 확신과 안정감)",
    "공감표현": "0-10점 (고객 감정에 대한 공감 빈도)"
  }},
  
  "강점": ["잘한 점 3가지"],
  "개선점": ["보완 필요한 점 3가지"],
  "코칭조언": ["구체적 팁 2가지"],
  
  "우수사례": {{
    "활용가능": true 또는 false,
    "이유": "우수 사례인 이유",
    "종합점수": 88
  }},
  
  "추천스크립트": "이 상황에 더 효과적인 대화 예시",
  "억양가이드": "말투 및 타이밍 가이드"
}}

중요: 
1. 반드시 유효한 JSON 형식으로만 출력하세요.
2. 추가 설명이나 마크다운은 포함하지 마세요.
3. 숫자, 모델명, 요금은 녹음에서 들린 그대로 정확히 기록하세요.
4. 모든 점수는 숫자만 입력하세요 (예: "종합점수": 88, "점" 문자 붙이지 말 것)

참고: {get_device_info()}
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
        audio_part = types.Part.from_bytes(
            data=audio_data,
            mime_type=mime_type
        )

        # 분석 요청
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt, audio_part]
        )
        
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
        톤점수_raw = 말투분석.get('톤적절성_점수', 0)
        톤점수 = int(톤점수_raw) if isinstance(톤점수_raw, (int, float)) else (int(톤점수_raw) if str(톤점수_raw).isdigit() else 0)
        자신감_raw = 말투분석.get('자신감수준', 0)
        자신감 = int(자신감_raw) if isinstance(자신감_raw, (int, float)) else (int(자신감_raw) if str(자신감_raw).isdigit() else 0)
        공감_raw = 말투분석.get('공감표현', 0)
        공감 = int(공감_raw) if isinstance(공감_raw, (int, float)) else (int(공감_raw) if str(공감_raw).isdigit() else 0)
        
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
    """실전 스크립트를 SECTION 태그 기반으로 섹션별 색상 박스로 표시"""
    import re

    def clean_body(text):
        text = re.sub(r'###\s+', '', text)
        text = re.sub(r'##\s+', '', text)
        text = re.sub(r'^#\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*', '', text)
        text = text.replace("[TM 대상군 분류 및 사전 준비사항]", "")
        text = re.sub(r'\n?---\n?', '', text)
        return text.strip()

    # SECTION 태그로 분리
    pattern = r'<SECTION:(\w+)>(.*?)</SECTION:\1>'
    matches = re.findall(pattern, script_text, re.DOTALL)

    if not matches:
        # SECTION 태그 없으면 그냥 출력
        st.markdown(script_text)
        return

    for section_type, content in matches:
        content = clean_body(content)

        if section_type == 'INFO':
            # 제목 교체
            content = content.replace("📌 미리 확인해야 할 사항", "📌 TM대상군 분류 및 사전 준비사항")
            content = content.replace("미리 확인해야 할 사항", "TM대상군 분류 및 사전 준비사항")
            title = "📌 TM대상군 분류 및 사전 준비사항"
            # 본문에서 제목 줄 제거
            body = re.sub(r'📌\s*TM대상군 분류 및 사전 준비사항\s*\n?', '', content).strip()
            st.markdown(f"""
            <div style="background-color:#d1ecf1;border-left:4px solid #17a2b8;padding:20px;border-radius:8px;margin:20px 0;">
                <h3 style="font-size:1.3em;font-weight:700;color:#2c5aa0;margin-top:0;margin-bottom:15px;">{title}</h3>
                <div style="font-size:14px;color:#333;">{body.replace(chr(10),'<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

        elif section_type == 'OPENING':
            title = "💬 오프닝 추천"
            body = re.sub(r'💬\s*오프닝 추천\s*\n?', '', content).strip()
            st.markdown(f"""
            <div style="background-color:#d4edda;border-left:4px solid #28a745;padding:20px;border-radius:8px;margin:20px 0;">
                <h3 style="font-size:1.3em;font-weight:700;color:#2c5aa0;margin-top:0;margin-bottom:15px;">{title}</h3>
                <div style="font-size:14px;color:#333;">{body.replace(chr(10),'<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

        elif section_type == 'SCRIPT':
            title = "💬 TM 스크립트"
            body = re.sub(r'💬\s*TM 스크립트\s*\n?', '', content).strip()
            st.markdown(f"""
            <div style="background-color:#d4edda;border-left:4px solid #28a745;padding:20px;border-radius:8px;margin:20px 0;">
                <h3 style="font-size:1.3em;font-weight:700;color:#2c5aa0;margin-top:0;margin-bottom:15px;">{title}</h3>
                <div style="font-size:14px;color:#333;">{body.replace(chr(10),'<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

        elif section_type == 'COACHING':
            title = "🎭 비언어적 코칭"
            body = re.sub(r'🎭\s*비언어적 코칭\s*\n?', '', content).strip()
            st.markdown(f"""
            <div style="background-color:#fff3cd;border-left:4px solid #ffc107;padding:20px;border-radius:8px;margin:20px 0;">
                <h3 style="font-size:1.3em;font-weight:700;color:#2c5aa0;margin-top:0;margin-bottom:15px;">{title}</h3>
                <div style="font-size:14px;color:#333;">{body.replace(chr(10),'<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

def remove_section_markers(text):
    """SECTION 태그 제거 (다운로드용)"""
    import re
    # <SECTION:xxx> 와 </SECTION:xxx> 모두 제거
    cleaned = re.sub(r'<SECTION:[A-Z]+>\n?', '', text)
    cleaned = re.sub(r'</SECTION:[A-Z]+>\n?', '', cleaned)
    return cleaned

def generate_script_html(script_text):
    """실전 스크립트를 HTML로 변환 (SECTION 태그 기반, 박스 분리)"""
    import re

    def clean_content(text):
        text = re.sub(r'###\s+', '', text)
        text = re.sub(r'##\s+', '', text)
        text = re.sub(r'^#\s*', '', text, flags=re.MULTILINE)
        text = text.replace("[TM 대상군 분류 및 사전 준비사항]", "")
        text = re.sub(r'\n?---\n?', '', text)
        text = re.sub(r'####\s+(.+)', r'<h4>\1</h4>', text)
        text = re.sub(r'\*\*(옵션 \d+[^:]*?):\*\*', r'<span class="option-label">\1:</span>', text)
        text = re.sub(r'- (A그룹|B그룹) ?\(([^)]+)\):', r'- <span class="group-label">\1 (\2):</span>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'</h4>\n', '</h4><br>', text)
        text = re.sub(r'\n\n', '<br><br>', text)
        text = re.sub(r'\n', '<br>', text)
        return text.strip()

    html_body = ""
    pattern = r'<SECTION:(\w+)>(.*?)</SECTION:\1>'
    matches = re.findall(pattern, script_text, re.DOTALL)

    section_config = {
        'INFO':     ('#d1ecf1', '#17a2b8', '📌 TM대상군 분류 및 사전 준비사항'),
        'OPENING':  ('#d4edda', '#28a745', '💬 오프닝 추천'),
        'SCRIPT':   ('#d4edda', '#28a745', '💬 TM 스크립트'),
        'COACHING': ('#fff3cd', '#ffc107', '🎭 비언어적 코칭'),
    }

    for section_type, content in matches:
        cfg = section_config.get(section_type)
        if not cfg:
            continue
        bg_color, border_color, title = cfg

        # 본문에서 제목 줄 제거
        content = re.sub(r'(📌|💬|🎭)[^\n]*\n?', '', content, count=1)
        content = clean_content(content)

        html_body += f"""
    <div style="background-color:{bg_color};border-left:4px solid {border_color};padding:20px;border-radius:8px;margin:20px 0;">
        <h3>{title}</h3>
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
            str(tcrew_info.get('매장코드', '')).zfill(4) if str(tcrew_info.get('매장코드', '')) != '' else '',
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
            datetime.now(KST).strftime("%Y-%m-%d"),  # 생성일자
            tcrew_info.get('T크루ID', ''),                 # T크루ID
            tcrew_info.get('이름', ''),                     # 이름
            tcrew_info.get('마케팅팀명', ''),              # 마케팅팀명
            tcrew_info.get('대리점코드', ''),              # 대리점코드
            tcrew_info.get('대리점명', ''),                # 대리점명
            str(tcrew_info.get('매장코드', '')).zfill(4) if str(tcrew_info.get('매장코드', '')) else '',  # 매장코드
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
    client = setup_gemini()
    sheets_client = setup_sheets()
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        st.divider()
        
# 메뉴 선택
        menu = st.radio(
            "메뉴 선택",
            ["🔍 통화 분석", "💬 Chat 스크립트", "📊 대시보드"],
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
        if client:
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
            elif menu == "💬 Chat 스크립트":
                st.info("1. 원하는 스크립트 입력\n2. 우수사례 검색 또는 AI 프리미엄 생성\n3. TTS 음성 변환")
            else:  # 대시보드
                st.info("생성된 스크립트 이력을 시각화하여 보여줍니다.\n- 날짜별 추이\n- T크루별 사용 현황\n- 키워드 분석 등")
  
    # 메뉴별 화면 표시
    # ============================================================
    if menu == "💬 Chat 스크립트":
        # AI 스크립트 상담만 표시
        st.markdown("## 💬 AI 스크립트 상담")
        chat_script_generator.show_chat_script_page(model=client, sheets_client=sheets_client, device_info=get_device_info())
    
    elif menu == "📊 대시보드":
        import plotly.express as px

        st.markdown("## 📊 TM SEED 대시보드")

        if not sheets_client:
            st.error("⚠️ Google Sheets 연결이 필요합니다.")
            st.stop()

        try:
            sheet_url = st.secrets["google"]["sheet_url"]

            with st.spinner("📊 데이터를 불러오는 중..."):
                script_df = dashboard.load_script_history(sheets_client, sheet_url)
                analysis_df = dashboard.load_analysis_results(sheets_client, sheet_url)

            # 기간 필터
            col_f1, col_f2 = st.columns([4, 1])
            with col_f1:
                date_option = st.radio(
                    "📅 기간",
                    ["오늘", "최근 7일", "최근 30일", "이번 달", "전체"],
                    index=4, horizontal=True, label_visibility="collapsed"
                )
            with col_f2:
                if st.button("🔄 새로고침", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            script_f = dashboard.filter_by_date(script_df, date_option)
            analysis_f = dashboard.filter_by_date(analysis_df, date_option)

            if script_df.empty and analysis_df.empty:
                st.warning("📭 아직 데이터가 없습니다.")
                st.stop()

            # 요약 카드
            summary = dashboard.get_summary_cards(script_f, analysis_f)
            call_stats = dashboard.get_call_analysis_stats(analysis_f)
            st.markdown("---")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("📝 스크립트 생성", f"{summary['total_scripts']:,}건")
            c2.metric("🔥 최다 키워드", summary['top_keyword'])
            c3.metric("🏆 최우수 크루", summary['best_crew'])
            c3.caption("통화분석 평균점수 1위")
            c4.metric("📞 통화분석", f"{call_stats['total_count']:,}건")
            c5.metric("⭐ 통화 평균 점수", f"{call_stats['avg_score']}점")
            c6.metric("🕐 최근 업데이트", summary['latest_update'])
            st.markdown("---")

            # ── 1) 현황 분석 ──────────────────────────────────
            with st.expander("📋 스크립트 생성 현황 분석", expanded=True):
                script_insights = dashboard.generate_script_insights(script_f)
                if script_insights:
                    st.markdown("#### 💡 스크립트 생성 인사이트")
                    for ins in script_insights:
                        st.info(ins)

                col_pie, col_trend = st.columns(2)
                with col_pie:
                    st.markdown("##### 🥧 유형별 분포")
                    type_stats = dashboard.get_script_type_stats(script_f)

                    if not type_stats.empty:
                        fig = go.Figure(go.Pie(
                            labels=type_stats['타입'].tolist(),
                            values=type_stats['건수'].tolist(),
                            hole=0.35,
                            marker_colors=px.colors.qualitative.Pastel
                        ))
                        fig.update_layout(height=300, margin=dict(t=10, b=10))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("데이터 없음")

                with col_trend:
                    script_daily, analysis_daily = dashboard.get_daily_trend(script_f, analysis_f, days=30)

                    st.markdown("##### 📝 스크립트 생성 추이")
                    if not script_daily.empty:
                        import pandas as pd
                        sd = script_daily.copy()
                        sd['날짜_dt'] = pd.to_datetime(sd['날짜'])
                        sd = sd.sort_values('날짜_dt').reset_index(drop=True)
                        sd['합계'] = sd['합계'].reset_index(drop=True)
                        sd['날짜_label'] = sd['날짜_dt'].apply(lambda d: f"{d.month}.{d.day:02d}")

                        fig = go.Figure()
                        type_cols = [c for c in sd.columns if c not in ['날짜', '날짜_dt', '날짜_label', '합계']]
                        colors = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2']
                        for i, col in enumerate(type_cols):
                            fig.add_trace(go.Scatter(
                                x=sd['날짜_label'].tolist(), y=sd[col].tolist(),
                                mode='lines+markers', name=col,
                                line=dict(color=colors[i % len(colors)])
                            ))
                        fig.add_trace(go.Scatter(
                            x=sd['날짜_label'].tolist(), y=sd['합계'].tolist(),
                            mode='lines+markers', name='합계',
                            line=dict(color='#333333', dash='dash', width=3)
                        ))
                        fig.update_layout(
                            height=280, margin=dict(t=30, b=50),
                            legend=dict(orientation='h', y=-0.4),
                            xaxis=dict(title='날짜', tickangle=-45, type='category'),
                            yaxis=dict(title='건수', rangemode='tozero', range=[0, sd['합계'].max() * 1.1])
                        )
                        st.caption("💡 클릭: 숨기기/보이기 | 더블클릭: 단독 보기 | 더블클릭 한 번 더: 전체 보기")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("스크립트 데이터 없음")

                    st.markdown("##### 📞 통화분석 추이")
                    if not analysis_daily.empty:
                        import pandas as pd
                        ad = analysis_daily.copy()
                        ad['날짜_dt'] = pd.to_datetime(ad['날짜'])
                        ad = ad.sort_values('날짜_dt').reset_index(drop=True)
                        ad['합계'] = ad['합계'].reset_index(drop=True)
                        ad['날짜_label'] = ad['날짜_dt'].apply(lambda d: f"{d.month}.{d.day:02d}")

                        fig = go.Figure()
                        result_colors = {'성공': '#2ecc71', '보류': '#f39c12', '거절': '#e74c3c', '기타': '#9b59b6'}
                        result_cols = [c for c in ad.columns if c not in ['날짜', '날짜_dt', '날짜_label', '합계']]
                        for col in result_cols:
                            fig.add_trace(go.Scatter(
                                x=ad['날짜_label'].tolist(), y=ad[col].tolist(),
                                mode='lines+markers', name=col,
                                line=dict(color=result_colors.get(col, '#888888'))
                            ))
                        fig.add_trace(go.Scatter(
                            x=ad['날짜_label'].tolist(), y=ad['합계'].tolist(),
                            mode='lines+markers', name='합계',
                            line=dict(color='#333333', dash='dash', width=3)
                        ))
                        fig.update_layout(
                            height=260, margin=dict(t=30, b=40),
                            legend=dict(orientation='h', y=-0.35),
                            xaxis=dict(title='날짜', tickangle=-45, type='category'),
                            yaxis=dict(title='건수', rangemode='tozero', range=[0, ad['합계'].max() * 1.1])
                        )
                        st.caption("💡 클릭: 숨기기/보이기 | 더블클릭: 단독 보기 | 더블클릭 한 번 더: 전체 보기")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("통화분석 데이터 없음")

            # ── 2) 통화분석 성과 ──────────────────────────────
            with st.expander("📞 통화분석 성과", expanded=False):
                call_insights = dashboard.generate_call_insights(analysis_f)
                if call_insights:
                    st.markdown("#### 💡 통화분석 인사이트")
                    for ins in call_insights:
                        st.info(ins)

                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("총 분석건수", f"{call_stats['total_count']:,}건")
                cc2.metric("평균 점수", f"{call_stats['avg_score']}점")
                cc3.metric("성공률", f"{call_stats['success_rate']}%")
                cc4.metric("우수사례(80점↑)", f"{call_stats['excellent_count']}건")

                col_bar, col_compare, col_pie2 = st.columns(3)
                with col_bar:
                    st.markdown("##### 📊 항목별 평균 점수")
                    score_avg = dashboard.get_score_avg_by_item(analysis_f)
                    if not score_avg.empty:
                        team_avg = round(score_avg['평균점수'].mean(), 1)
                        colors = ['#e74c3c' if v < team_avg else '#4C78A8'
                                  for v in score_avg['평균점수']]
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=score_avg['평균점수'].tolist(),
                            y=score_avg['항목'].tolist(),
                            orientation='h',
                            marker_color=colors,
                            text=score_avg['평균점수'].tolist(),
                            textposition='outside',
                            hovertemplate='%{y}: %{x}점<extra></extra>'
                        ))
                        fig.add_vline(
                            x=team_avg,
                            line_dash='dash', line_color='#888888', line_width=1.5,
                            annotation_text=f'팀 평균 {team_avg}점',
                            annotation_position='top right',
                            annotation_font_size=11
                        )
                        fig.update_layout(
                            height=280, margin=dict(t=10, b=10),
                            xaxis=dict(range=[0, 10], dtick=1, title='평균점수'),
                            yaxis=dict(title=None)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("JSON 데이터 없음")

                with col_compare:
                    st.markdown("##### 📊 성공 통화가 거절보다 높은 항목")
                    score_by_result = dashboard.get_score_by_result(analysis_f)
                    if not score_by_result.empty:
                        gaps = score_by_result['Gap'].tolist()
                        items = score_by_result['항목'].tolist()
                        colors = ['#2ecc71' if g > 0 else '#e74c3c' for g in gaps]
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=gaps, y=items,
                            orientation='h',
                            marker_color=colors,
                            text=[f'+{g}점' if g > 0 else f'{g}점' for g in gaps],
                            textposition='outside',
                            hovertemplate='%{y}<br>성공-거절 차이: %{x}점<extra></extra>'
                        ))
                        fig.add_vline(x=0, line_color='#333333', line_width=1.5)
                        fig.add_annotation(x=0, y=1.08, xref='x', yref='paper',
                                           text='← 거절이 높음 | 성공이 높음 →',
                                           showarrow=False, font=dict(size=10, color='#666666'),
                                           xanchor='center')
                        fig.update_layout(
                            height=320, margin=dict(t=35, b=10),
                            xaxis=dict(title=None, dtick=1),
                            yaxis=dict(title=None)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("데이터 없음")

                with col_pie2:
                    st.markdown("##### 🥧 통화결과 분포")
                    # call_stats 대신 analysis_f에서 직접 집계 (필터 반영)
                    if not analysis_f.empty and '통화결과' in analysis_f.columns:
                        result_dist_f = analysis_f['통화결과'].value_counts().reset_index()
                        result_dist_f.columns = ['통화결과', '건수']
                        color_map = {'성공': '#2ecc71', '거절': '#e74c3c', '보류': '#f39c12', '기타': '#95a5a6'}
                        pie_colors = [color_map.get(n, '#cccccc') for n in result_dist_f['통화결과'].tolist()]
                        fig = go.Figure(go.Pie(
                            labels=result_dist_f['통화결과'].tolist(),
                            values=result_dist_f['건수'].tolist(),
                            hole=0.35,
                            marker_colors=pie_colors
                        ))
                        fig.update_layout(height=280, margin=dict(t=10, b=10))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("데이터 없음")

            # ── 3) T크루 활동 순위 ────────────────────────────
            with st.expander("🏆 T크루 활동 순위", expanded=False):
                tcrew_ranking = dashboard.get_tcrew_ranking(script_f, analysis_f, top_n=10)
                if not tcrew_ranking.empty:
                    medals = ["🥇", "🥈", "🥉"]
                    top3 = tcrew_ranking.head(3)
                    cols_top3 = st.columns(3)
                    for i, (_, row) in enumerate(top3.iterrows()):
                        with cols_top3[i]:
                            st.markdown(
                                f"""<div style="background:#f0f2f6;border-radius:12px;padding:18px;text-align:center;">
                                <div style="font-size:2rem;">{medals[i]}</div>
                                <div style="font-size:1.2rem;font-weight:700;">{row['이름']}</div>
                                <div style="color:#666;font-size:0.9rem;">총 {row['총건수']}건</div>
                                <div style="color:#aaa;font-size:0.8rem;">스크립트 {row['스크립트']} · 통화분석 {row['통화분석']}</div>
                                </div>""",
                                unsafe_allow_html=True
                            )
                    st.markdown("<br>", unsafe_allow_html=True)
                    display_rank = tcrew_ranking.reset_index(drop=True)
                    display_rank.index += 1
                    display_rank.index.name = "순위"
                    st.dataframe(display_rank[['이름', '스크립트', '통화분석', '총건수']], use_container_width=True)
                else:
                    st.info("T크루 데이터가 없습니다.")

            # ── 4) 스크립트 상세 ──────────────────────────────
            with st.expander("🏢 스크립트 상세", expanded=False):
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    search_agency = st.text_input("🔍 대리점명 검색", placeholder="대리점명 입력")
                with col_s2:
                    search_crew = st.text_input("🔍 T크루명 검색", placeholder="이름 입력")

                import pandas as _pd
                detail_df = script_f.copy() if not script_f.empty else _pd.DataFrame()
                if not detail_df.empty:
                    if search_agency:
                        detail_df = detail_df[detail_df['대리점명'].str.contains(search_agency, na=False)]
                    if search_crew:
                        detail_df = detail_df[detail_df['이름'].str.contains(search_crew, na=False)]

                keyword_stats = dashboard.get_keyword_stats(
                    detail_df if not detail_df.empty else script_f, top_n=10
                )
                if not keyword_stats.empty:
                    st.markdown("##### 🔥 요즘 뜨는 키워드 TOP 10")
                    fig = px.bar(keyword_stats, x='건수', y='키워드', orientation='h',
                                 text='건수', color='건수', color_continuous_scale='Oranges')
                    fig.update_layout(height=300, margin=dict(t=10, b=10),
                                      yaxis={'categoryorder': 'total ascending'},
                                      coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("##### 📂 대리점 > 매장 > T크루 상세")
                if not detail_df.empty:
                    tree = dashboard.get_script_detail_tree(detail_df)
                    type_icons = {
                        'AI프리미엄': '✨',
                        '우수사례': '🏆',
                        '실전 활용_AI프리미엄': '📞'
                    }
                    for agency, stores in sorted(tree.items()):
                        agency_total = sum(
                            len(rows) for crews in stores.values() for rows in crews.values()
                        )
                        st.markdown(
                            f"<div style='background:#e8eaf6;border-radius:8px;padding:8px 14px;"
                            f"font-weight:700;font-size:1rem;margin:8px 0;'>🏢 {agency} (총 {agency_total}건)</div>",
                            unsafe_allow_html=True
                        )
                        for store, crews in sorted(stores.items()):
                            store_total = sum(len(rows) for rows in crews.values())
                            st.markdown(
                                f"<div style='font-weight:600;color:#555;padding:4px 0 4px 16px;'>"
                                f"📍 {store} ({store_total}건)</div>",
                                unsafe_allow_html=True
                            )
                            for crew, rows in sorted(crews.items()):
                                try:
                                    dates = [_pd.to_datetime(r.get('분석일자', '')) for r in rows]
                                    latest_dt = max(dates).strftime('%m/%d') if dates else '-'
                                except:
                                    latest_dt = '-'
                                st.markdown(
                                    f"<div style='font-weight:600;color:#333;padding:4px 0 4px 32px;'>"
                                    f"○ {crew} (최근 {latest_dt})</div>",
                                    unsafe_allow_html=True
                                )
                                for r in sorted(rows, key=lambda x: str(x.get('분석일자', '')), reverse=True):
                                    stype = str(r.get('스크립트 타입', ''))
                                    icon = type_icons.get(stype, '📄')
                                    kw = r.get('키워드', '')
                                    req = r.get('요청내용', '')
                                    date_str = str(r.get('분석일자', ''))[:10]
                                    st.markdown(
                                        f"<div style='background:#f8f9fa;border-radius:8px;padding:8px 12px;"
                                        f"margin:4px 0 4px 32px;font-size:0.85rem;'>"
                                        f"<span style='background:#e9ecef;border-radius:4px;padding:2px 6px;"
                                        f"font-weight:600;'>{icon} {stype}</span>"
                                        f"&nbsp;&nbsp;<span style='color:#888;'>{date_str}</span><br>"
                                        f"<b>키워드:</b> {kw}&nbsp;&nbsp;<b>요청:</b> {req}"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )
                else:
                    st.info("검색 결과가 없습니다.")

        except Exception as e:
            st.error(f"⚠️ 대시보드 로드 중 오류: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
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
                
                    if not client:
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
                            result = analyze_audio_with_gemini(temp_path, client)
                        
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
                                    model=client,
                                    cases=similar_cases,
                                    user_request="",
                                    current_result=result,
                                    device_info=get_device_info()
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
                톤점수_raw = 말투분석.get('톤적절성_점수', 0)
                톤점수 = int(톤점수_raw) if isinstance(톤점수_raw, (int, float)) else (int(톤점수_raw) if str(톤점수_raw).isdigit() else 0)
                st.write(f"**톤 적절성:** {톤점수}/10")
            with col3:
                자신감_raw = 말투분석.get('자신감수준', 0)
                자신감 = int(자신감_raw) if isinstance(자신감_raw, (int, float)) else (int(자신감_raw) if str(자신감_raw).isdigit() else 0)
                st.write(f"**자신감:** {자신감}/10")
                공감_raw = 말투분석.get('공감표현', 0)
                공감 = int(공감_raw) if isinstance(공감_raw, (int, float)) else (int(공감_raw) if str(공감_raw).isdigit() else 0)

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