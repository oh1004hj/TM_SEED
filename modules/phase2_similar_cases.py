"""
Phase 2: 유사 성공 케이스 검색 모듈
TM SEED 프로젝트 - 키워드 기반 하이브리드 검색
"""

import streamlit as st

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
        "플립", "폴드", "S24", "S25", "아이폰15", "아이폰16", "아이폰17",
        "색상", "용량", "128GB", "256GB", "512GB", "1TB", 
        "사전예약", "출시"
    ],
    "할인혜택": [
        "할인", "지원금", "공시지원금", "선택약정", "요금할인",
        "이벤트", "프로모션", "사은품", "경품", "추가할인",
        "제휴할인", "멤버십", "포인트", "쿠폰"
    ],
    "서비스": [
        "로밍", "해외", "부가서비스", "티빙", "멜론", "유튜브",
        "넷플릭스", "OTT", "멤버십", "보험", "케어", "AS",
        "배송", "방문", "개통", "번호이동", "유심"
    ],
    "고객상황": [
        "변경", "신규", "번호이동", "기변", "기기변경", "해지",
        "망설임", "고민", "비교", "타사", "경쟁사", "LGU", "KT",
        "예산", "부담", "저렴", "비싸", "가격", "납부"
    ]
}

# =============================================================================
# 🔍 키워드 추출 함수
# =============================================================================

def extract_keywords(text, keyword_dict):
    """
    텍스트에서 사전에 정의된 키워드를 추출
    
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
# 📊 과거 데이터 로드 함수 (gspread 사용)
# =============================================================================

def load_past_successful_calls(sheets_client, sheet_url):
    """
    Google Sheets에서 성공 통화 데이터 로드
    - 통화결과 = "성공"
    - 종합점수 >= 80점
    
    Args:
        sheets_client: gspread 클라이언트 객체
        sheet_url: Google Sheets URL
    
    Returns:
        list: 필터링된 과거 통화 데이터
    """
    try:
        # 스프레드시트 열기
        spreadsheet = sheets_client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("시트1")
        
        # 전체 데이터 로드 (헤더 포함)
        all_data = worksheet.get_all_records()
        
        if not all_data:
            return []
        
        # 필터링: 통화결과 = "성공" AND 종합점수 >= 80
        filtered_data = []
        for row in all_data:
            call_result = row.get("통화결과", "")
            
            # 종합점수 추출 (우수사례.종합점수)
            try:
                # 우수사례 필드에서 종합점수 찾기
                total_score_raw = row.get("종합점수", "0")
                if isinstance(total_score_raw, str):
                    # "92점" → 92 변환
                    total_score = int(total_score_raw.replace("점", "").strip())
                else:
                    total_score = int(total_score_raw)
            except (ValueError, AttributeError):
                total_score = 0
            
            # 필터 조건: 성공 + 80점 이상
            if call_result == "성공" and total_score >= 80:
                filtered_data.append({
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
                    "코칭조언": row.get("코칭조언", "")
                })
        
        return filtered_data
    
    except Exception as e:
        st.error(f"⚠️ 과거 데이터 로드 중 오류: {str(e)}")
        return []

# =============================================================================
# 🎯 유사도 계산 함수
# =============================================================================

def calculate_similarity(current_summary, current_needs, past_data, top_n=3):
    """
    현재 통화와 과거 성공 통화의 유사도 계산
    
    Args:
        current_summary (str): 현재 통화 내용요약
        current_needs (str): 현재 통화 고객니즈
        past_data (list): 과거 성공 통화 데이터
        top_n (int): 반환할 상위 케이스 개수
    
    Returns:
        list: 유사도 높은 순으로 정렬된 TOP N 케이스
    """
    if not past_data:
        return []
    
    # 현재 통화 키워드 추출
    current_text = f"{current_summary} {current_needs}"
    current_keywords = extract_keywords(current_text, KEYWORD_CATEGORIES)
    
    if not current_keywords:
        return []
    
    # 각 과거 통화와의 유사도 계산
    similarity_scores = []
    
    for past_call in past_data:
        past_text = f"{past_call['내용요약']} {past_call['고객니즈']}"
        past_keywords = extract_keywords(past_text, KEYWORD_CATEGORIES)
        
        # 공통 키워드 개수 = 유사도
        common_keywords = current_keywords & past_keywords
        similarity = len(common_keywords)
        
        if similarity > 0:
            similarity_scores.append({
                **past_call,
                "유사도": similarity,
                "공통키워드": list(common_keywords)
            })
    
    # 정렬: 유사도 높은 순 → 점수 높은 순
    similarity_scores.sort(key=lambda x: (-x["유사도"], -x["종합점수"]))
    
    return similarity_scores[:top_n]

# =============================================================================
# 🎨 유사 케이스 UI 표시 함수
# =============================================================================

def display_similar_cases(similar_cases):
    """
    유사 케이스를 UI에 표시
    
    Args:
        similar_cases (list): 유사도 계산된 케이스 리스트
    """
    if not similar_cases:
        st.info("💡 유사한 성공 케이스가 없습니다. (점수 80점 이상인 과거 통화 데이터가 부족)")
        return
    
    st.markdown("---")
    st.subheader("🎯 유사 성공 케이스 TOP 3")
    st.caption("현재 통화와 비슷한 성공 사례를 참고하여 스크립트를 개선하세요!")
    
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, case in enumerate(similar_cases):
        medal = medals[idx] if idx < 3 else "📌"
        
        with st.expander(
            f"{medal} #{idx+1} | {case['T크루명']} ({case['매장코드']}) | "
            f"종합점수 {case['종합점수']}점 | 유사도: {case['유사도']}개 키워드",
            expanded=(idx == 0)  # 1위만 기본 펼침
        ):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**📅 분석날짜**")
                st.text(case['분석날짜'])
                
                st.markdown("**📝 내용요약**")
                st.text(case['내용요약'])
                
                st.markdown("**💡 고객니즈**")
                st.text(case['고객니즈'])
            
            with col2:
                st.markdown("**✅ 강점**")
                st.text(case['강점'])
                
                st.markdown("**📈 개선점**")
                st.text(case['개선점'])
                
                st.markdown(f"**📊 종합점수**: {case['종합점수']}점")
                
                st.markdown("**🔑 공통 키워드**")
                st.write(", ".join(case['공통키워드']))
            
            st.markdown("**📞 추천 스크립트**")
            st.code(case['추천스크립트'], language="text")
            
            if case.get('코칭조언'):
                st.markdown("**💡 코칭 조언**")
                st.info(case['코칭조언'])

# =============================================================================
# 🚀 메인 실행 함수 (app.py에서 호출)
# =============================================================================

def run_similar_case_analysis(sheets_client, sheet_url, current_result):
    """
    유사 케이스 분석 실행 (app.py에서 호출하는 메인 함수)
    
    Args:
        sheets_client: gspread 클라이언트 객체
        sheet_url: Google Sheets URL
        current_result: 현재 분석 결과 (dict)
    """
    if not sheets_client or not current_result:
        return
    
    # 현재 통화 정보
    current_summary = current_result.get("내용요약", "")
    current_needs = current_result.get("고객니즈", "")
    
    if not current_summary and not current_needs:
        st.info("💡 내용요약 또는 고객니즈 데이터가 없어 유사 케이스를 찾을 수 없습니다.")
        return
    
    # 과거 성공 케이스 로드
    past_successful_calls = load_past_successful_calls(sheets_client, sheet_url)
    
    if not past_successful_calls:
        st.info("💡 아직 성공 케이스 데이터가 부족합니다. (통화결과=성공, 점수≥80인 데이터 필요)")
        return
    
    # 유사도 계산
    similar_cases = calculate_similarity(
        current_summary=current_summary,
        current_needs=current_needs,
        past_data=past_successful_calls,
        top_n=3
    )
    
    # UI 표시
    display_similar_cases(similar_cases)
    
    # similar_cases 반환 (phase2_script_generator에서 사용)
    return similar_cases
```

**작업 방법:**
1. `phase2_similar_cases.py` 파일 열기
2. 마지막 줄 (218줄) 다음에 빈 줄 추가
3. `    return similar_cases` 입력 (들여쓰기 4칸!)

---

## 📋 전체 작업 체크리스트

### ✅ 완료된 작업
```
□ phase2_script_generator.py 생성 (A-1단계)
```

### 🔲 남은 작업

**A-2단계:**
```
□ app.py 수정 1: import 추가 (10-11줄)
□ app.py 수정 2: Phase 2 호출 코드 수정 (573-603줄)
□ phase2_similar_cases.py 수정: return 추가 (219줄)
```

**A-3단계: GitHub Push**
```
□ git add .
□ git commit -m "Phase 2 개선: 실전 스크립트 생성 기능 추가"
□ git push origin main