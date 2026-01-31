import streamlit as st
import google.generativeai as genai
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import json
import os
import tempfile
import base64
from modules import phase2_similar_cases
from modules import phase2_script_generator

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

@st.cache_data(ttl=3600)
def load_tcrew_master():
    """NPS Raw Data에서 T크루 마스터 로드"""
    try:
        client = setup_sheets()
        if not client:
            return []
        
        # NPS Raw Data 시트 열기
        nps_sheet_url = st.secrets["google"]["nps_raw_sheet_url"]
        spreadsheet = client.open_by_url(nps_sheet_url)
        worksheet = spreadsheet.sheet1
        
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
        worksheet = spreadsheet.worksheet("시트1")
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

# 메인 앱
def main():
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        st.info("📌 **사용 방법**\n\n1. 통화 녹음 파일 업로드\n2. 자동 분석 시작\n3. 결과 확인 및 저장")
        
        st.divider()
        
        # API 상태 확인
        model = setup_gemini()
        sheets_client = setup_sheets()
        
        if model:
            st.success("✅ Gemini API 연결됨")
        else:
            st.error("❌ Gemini API 미연결")
            
        if sheets_client:
            st.success("✅ Google Sheets 연결됨")
            # 개발/디버깅용으로만 필요할 때 아래 주석 해제
            # st.info(f"Service Account Email: {st.secrets['gcp_service_account']['client_email']}")
            # st.warning("위 email을 대상 Google Sheet (sheet_url)에 편집자 권한으로 공유해주세요. 공유되지 않으면 저장이 실패합니다.")
        else:
            st.warning("⚠️ Google Sheets 미연결 - 관리자에게 문의해주세요.")
    
    # 메인 컨텐츠
    st.subheader("🎙️ 통화 녹음 분석")
    
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
        
        # 분석 버튼
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button("🔍 통화 분석 시작", use_container_width=True)
        
        if analyze_button:
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
                
                except Exception as e:
                    st.error(f"❌ 분석 중 오류 발생: {str(e)}")
                
                finally:
                    st.session_state['is_analyzing'] = False
            
    # 분석 결과가 있으면 표시 (session_state 사용)
    if st.session_state.get('analysis_result'):
        result = st.session_state['analysis_result']
        st.balloons()
        
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
        # Phase 2: 유사 성공 케이스 검색 + 실전 스크립트
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
                
                # Phase 2-2: 실전 스크립트 생성
                if similar_cases and len(similar_cases) > 0:
                    phase2_script_generator.display_practical_script(
                        model=model,
                        similar_cases=similar_cases,
                        current_result=result
                    )
                else:
                    st.info("💡 유사 케이스가 충분하지 않아 실전 스크립트를 생성할 수 없습니다.")
                    
            except Exception as e:
                st.warning(f"⚠️ 유사 케이스 검색 중 오류: {str(e)}")
        else:
            st.info("💡 유사 케이스 검색을 위해 Google Sheets 연결이 필요합니다.")
                
    # Google Sheets 저장
    st.markdown("---")
    if sheets_client:    
        if st.button("💾 Google Sheets에 저장", use_container_width=True):
            st.write("🔍 [디버그] 저장 버튼 클릭됨!")
            st.write(f"🔍 [디버그] selected_tcrew 있음? {'selected_tcrew' in st.session_state}")
            st.write(f"🔍 [디버그] analysis_result 있음? {'analysis_result' in st.session_state}")
            
            if 'selected_tcrew' not in st.session_state:
                st.error("⚠️ T크루를 먼저 선택해주세요!")
            else:
                try:
                    with st.spinner("저장 중..."):
                        # session_state에서 분석 결과 가져오기
                        saved_result = st.session_state.get('analysis_result')
                        saved_filename = st.session_state.get('last_analyzed_file', 'unknown.mp3')
                        
                        if saved_result:
                            save_result = save_to_sheets(sheets_client, saved_result, saved_filename)
                        else:
                            st.error("⚠️ 저장할 분석 결과가 없습니다. 먼저 통화를 분석해주세요!")
                            save_result = False
                        
                        if save_result:
                            st.success("✅ 저장 완료!")
                            st.balloons()
                        else:
                            st.error("❌ 저장 실패")
                except Exception as e:
                    if 'permission' in str(e).lower() or 'insufficient' in str(e).lower():
                        client_email = st.secrets["gcp_service_account"]["client_email"]
                        st.error(f"권한 오류: Google Sheet에 '{client_email}'을 편집자(editor)로 공유해주세요.")
                    else:
                        st.error(f"❌ 저장 중 예외 발생: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Google Sheets가 연결되지 않아 저장할 수 없습니다.")

if __name__ == "__main__":
    main()