"""
TM SEED - 통합 스크립트 데이터베이스
모든 우수사례 및 템플릿 데이터를 단일 소스로 관리
"""

import streamlit as st
import json
import os

# =============================================================================
# 📚 키워드 사전 정의
# =============================================================================

KEYWORD_CATEGORIES = {
    "요금제": [
        "요금제", "데이터", "무제한", "5G", "LTE", "통화", "문자", 
        "데이터무제한", "음성무제한", "프리미엄", "슬림", "베이직",
        "결합", "할인", "시니어", "청소년", "가족결합"
    ],
    "단말기": [
        "단말", "기기", "스마트폰", "갤럭시", "아이폰", "폴더블", 
        "플립", "폴드", "S24", "S25", "S26", "아이폰15", "아이폰16", "아이폰17",
        "색상", "용량", "128GB", "256GB", "512GB", "1TB", 
        "사전예약", "출시", "신단말", "키즈폰"
    ],
    "할인혜택": [
        "할인", "지원금", "공시지원금", "선택약정", "요금할인",
        "이벤트", "프로모션", "사은품", "경품", "추가할인",
        "제휴할인", "멤버십", "포인트", "쿠폰", "신학기"
    ],
    "서비스": [
        "로밍", "해외", "부가서비스", "티빙", "멜론", "유튜브",
        "넷플릭스", "OTT", "멤버십", "보험", "케어", "AS",
        "배송", "방문", "개통", "번호이동", "유심"
    ],
    "고객상황": [
        "변경", "신규", "번호이동", "기변", "기기변경", "해지",
        "망설임", "고민", "비교", "타사", "경쟁사", "LGU", "KT",
        "예산", "부담", "저렴", "비싸", "가격", "납부", "단골"
    ]
}

# =============================================================================
# 🔍 키워드 추출 함수
# =============================================================================

def extract_keywords(text, keyword_dict=KEYWORD_CATEGORIES):
    """
    텍스트에서 키워드 추출
    
    Args:
        text (str): 분석할 텍스트
        keyword_dict (dict): 카테고리별 키워드 사전
    
    Returns:
        set: 추출된 키워드 집합
    """
    if not text or not isinstance(text, str):
        return set()
    
    text_lower = text.lower()
    found_keywords = set()
    
    for category, keywords in keyword_dict.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.add(keyword)
    
    return found_keywords

# =============================================================================
# 📊 데이터 로드 함수들
# =============================================================================

def load_google_sheets_cases(sheets_client, sheet_url):
    """
    Google Sheets에서 우수사례 로드
    - 통화결과 = "성공"
    - 종합점수 >= 80점
    
    Args:
        sheets_client: gspread 클라이언트 객체
        sheet_url: Google Sheets URL
    
    Returns:
        list: 필터링된 우수사례 데이터
    """
    try:
        spreadsheet = sheets_client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("분석결과")
        all_data = worksheet.get_all_records()
        
        if not all_data:
            return []
        
        # 필터링: 통화결과 = "성공" AND 종합점수 >= 80
        filtered_data = []
        for row in all_data:
            call_result = row.get("통화결과", "")
            
            # 종합점수 추출
            try:
                total_score_raw = row.get("종합점수", "0")
                if isinstance(total_score_raw, str):
                    total_score = int(total_score_raw.replace("점", "").strip())
                else:
                    total_score = int(total_score_raw)
            except (ValueError, AttributeError):
                total_score = 0
            
            # 필터 조건: 성공 + 80점 이상
            if call_result == "성공" and total_score >= 80:
                filtered_data.append({
                    "출처": "Google Sheets",
                    "분석날짜": row.get("분석날짜", ""),
                    "T크루명": row.get("T크루명", ""),
                    "매장코드": row.get("매장코드", ""),
                    "통화시간": row.get("통화시간_초", ""),
                    "통화결과": call_result,
                    "내용요약": row.get("내용요약", ""),
                    "고객니즈": row.get("고객니즈", ""),
                    "강점": row.get("강점", ""),
                    "개선점": row.get("개선점", ""),
                    "추천스크립트": row.get("추천스크립트", ""),
                    "종합점수": total_score,
                    "코칭조언": row.get("코칭조언", ""),
                    "비언어적코칭": row.get("억양가이드", "")
                })
        
        return filtered_data
    
    except Exception as e:
        st.warning(f"⚠️ Google Sheets 로드 중 오류: {str(e)}")
        return []

def load_json_excellent_cases():
    """
    JSON 우수사례 로드 (4.m4a, 23.m4a, 24.m4a, 32.m4a, 33.m4a)
    
    Returns:
        list: JSON 우수사례 데이터
    """
    try:
        json_path = os.path.join("data", "excellent_cases.json")
        
        if not os.path.exists(json_path):
            # 파일이 없으면 빈 리스트 반환 (에러 아님)
            return []
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 출처 태그 추가
        cases = data.get("우수사례", [])
        for case in cases:
            case["출처"] = "JSON 우수사례"
        
        return cases
    
    except Exception as e:
        st.warning(f"⚠️ JSON 우수사례 로드 중 오류: {str(e)}")
        return []

def load_json_templates():
    """
    JSON 템플릿 로드 (script_templates.json)
    
    Returns:
        dict: 템플릿 데이터
    """
    try:
        json_path = os.path.join("data", "script_templates.json")
        
        if not os.path.exists(json_path):
            return {}
        
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    except Exception as e:
        st.warning(f"⚠️ JSON 템플릿 로드 중 오류: {str(e)}")
        return {}

# =============================================================================
# 🎯 통합 데이터 로드 (앱 시작 시 1회 호출)
# =============================================================================

@st.cache_data(ttl=86400, show_spinner=False)  # 24시간 캐싱
def load_all_data(_sheets_client, sheet_url):
    """
    모든 데이터 소스를 통합 로드 (24시간 캐싱)
    - 하루 1번 갱신으로 충분
    - 필요시 Streamlit 메뉴 > "Clear cache"로 수동 갱신 가능
    
    Args:
        _sheets_client: gspread 클라이언트 (언더스코어: 캐싱 제외)
        sheet_url: Google Sheets URL
    
    Returns:
        dict: 통합된 모든 데이터
    """
    data = {
        "google_sheets_cases": [],
        "json_excellent_cases": [],
        "json_templates": {}
    }
    
    # 1. Google Sheets 우수사례
    if _sheets_client and sheet_url:
        data["google_sheets_cases"] = load_google_sheets_cases(_sheets_client, sheet_url)
    
    # 2. JSON 우수사례
    data["json_excellent_cases"] = load_json_excellent_cases()
    
    # 3. JSON 템플릿
    data["json_templates"] = load_json_templates()
    
    return data

# =============================================================================
# 🔍 통합 검색 함수
# =============================================================================

def search_cases(query, all_data, source="all", top_n=5):
    """
    통합 검색: 모든 소스에서 키워드 유사도 기반 검색
    
    Args:
        query (str): 검색 쿼리
        all_data (dict): load_all_data()로 로드된 데이터
        source (str): 검색 소스 ("all", "sheets", "json_excellent", "templates")
        top_n (int): 반환할 상위 케이스 개수
    
    Returns:
        list: 유사도 높은 순으로 정렬된 케이스
    """
    if not query or not all_data:
        return []
    
    # 쿼리 키워드 추출
    query_keywords = extract_keywords(query)
    
    if not query_keywords:
        return []
    
    results = []
    
    # 1. Google Sheets 우수사례 검색
    if source in ["all", "sheets"]:
        for case in all_data.get("google_sheets_cases", []):
            case_text = f"{case.get('내용요약', '')} {case.get('고객니즈', '')}"
            case_keywords = extract_keywords(case_text)
            
            common_keywords = query_keywords & case_keywords
            similarity = len(common_keywords)
            
            if similarity > 0:
                results.append({
                    **case,
                    "유사도": similarity,
                    "공통키워드": list(common_keywords)
                })
    
    # 2. JSON 우수사례 검색
    if source in ["all", "json_excellent"]:
        for case in all_data.get("json_excellent_cases", []):
            case_text = f"{case.get('내용요약', '')} {case.get('고객니즈', '')} {case.get('강점', '')}"
            case_keywords = extract_keywords(case_text)
            
            common_keywords = query_keywords & case_keywords
            similarity = len(common_keywords)
            
            if similarity > 0:
                results.append({
                    **case,
                    "유사도": similarity,
                    "공통키워드": list(common_keywords)
                })
    
    # 3. JSON 템플릿 검색
    if source in ["all", "templates"]:
        templates = all_data.get("json_templates", {})
        for category, scripts in templates.items():
            for script in scripts:
                script_text = f"{script.get('세그먼트', '')} {script.get('스크립트', '')}"
                script_keywords = extract_keywords(script_text)
                
                common_keywords = query_keywords & script_keywords
                similarity = len(common_keywords)
                
                if similarity > 0:
                    results.append({
                        "출처": "JSON 템플릿",
                        "카테고리": category,
                        "세그먼트": script.get("세그먼트", ""),
                        "스크립트": script.get("스크립트", ""),
                        "비언어적코칭": script.get("비언어적코칭", ""),
                        "종합점수": 0,  # 템플릿은 점수 없음
                        "유사도": similarity,
                        "공통키워드": list(common_keywords)
                    })
    
    # 정렬: 유사도 높은 순 → 점수 높은 순
    results.sort(key=lambda x: (-x["유사도"], -x.get("종합점수", 0)))
    
    return results[:top_n]

# =============================================================================
# 📊 데이터 통계 함수 (대시보드용)
# =============================================================================

def get_data_statistics(all_data):
    """
    로드된 데이터 통계 반환
    
    Args:
        all_data (dict): load_all_data()로 로드된 데이터
    
    Returns:
        dict: 데이터 통계
    """
    return {
        "google_sheets_count": len(all_data.get("google_sheets_cases", [])),
        "json_excellent_count": len(all_data.get("json_excellent_cases", [])),
        "json_template_count": sum(
            len(scripts) 
            for scripts in all_data.get("json_templates", {}).values()
        ),
        "total_cases": (
            len(all_data.get("google_sheets_cases", [])) +
            len(all_data.get("json_excellent_cases", []))
        )
    }