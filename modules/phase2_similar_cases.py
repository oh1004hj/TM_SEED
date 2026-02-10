"""
Phase 2: 유사 성공 케이스 검색 모듈 (UI 표시)
TM SEED 프로젝트 - unified_script_database 사용
"""

import streamlit as st
from core import unified_script_database as db

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
        
        # 제목 구성
        title_parts = [f"{medal} #{idx+1}"]
        
        if case.get('T크루명'):
            title_parts.append(f"{case['T크루명']}")
        if case.get('매장코드'):
            title_parts.append(f"({case['매장코드']})")
        if case.get('출처'):
            title_parts.append(f"| {case['출처']}")
        
        title_parts.append(f"| 종합점수 {case.get('종합점수', 'N/A')}점")
        
        if case.get('유사도'):
            title_parts.append(f"| 유사도: {case['유사도']}개 키워드")
        
        title = " ".join(title_parts)
        
        with st.expander(title, expanded=(idx == 0)):  # 1위만 기본 펼침
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if case.get('분석날짜'):
                    st.markdown("**📅 분석날짜**")
                    st.text(case['분석날짜'])
                
                st.markdown("**📝 내용요약**")
                st.text(case.get('내용요약', 'N/A'))
                
                st.markdown("**💡 고객니즈**")
                st.text(case.get('고객니즈', 'N/A'))
            
            with col2:
                st.markdown("**✅ 강점**")
                st.text(case.get('강점', 'N/A'))
                
                if case.get('개선점'):
                    st.markdown("**📈 개선점**")
                    st.text(case['개선점'])
                
                st.markdown(f"**📊 종합점수**: {case.get('종합점수', 'N/A')}점")
                
                if case.get('공통키워드'):
                    st.markdown("**🔑 공통 키워드**")
                    st.write(", ".join(case['공통키워드']))
            
            st.markdown("**📞 추천 스크립트**")
            script = case.get('추천스크립트', case.get('스크립트', 'N/A'))
            st.code(script, language="text")
            
            if case.get('코칭조언') or case.get('비언어적코칭'):
                st.markdown("**💡 코칭 조언**")
                coaching = case.get('코칭조언', case.get('비언어적코칭', ''))
                st.info(coaching)

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
    
    Returns:
        list: 검색된 유사 케이스
    """
    if not current_result:
        return []
    
    # 현재 통화 정보
    current_summary = current_result.get("내용요약", "")
    current_needs = current_result.get("고객니즈", "")
    
    if not current_summary and not current_needs:
        st.info("💡 내용요약 또는 고객니즈 데이터가 없어 유사 케이스를 찾을 수 없습니다.")
        return []
    
    # unified DB에서 모든 데이터 로드
    all_data = db.load_all_data(sheets_client, sheet_url)
    
    # 데이터 통계 표시
    stats = db.get_data_statistics(all_data)
    st.caption(f"📊 검색 가능한 우수사례: Google Sheets {stats['google_sheets_count']}개 + JSON {stats['json_excellent_count']}개")
    
    # 통합 검색
    query = f"{current_summary} {current_needs}"
    similar_cases = db.search_cases(
        query=query,
        all_data=all_data,
        source="all",  # 모든 소스에서 검색
        top_n=3
    )
    
    if not similar_cases:
        st.info("💡 유사한 성공 케이스가 없습니다. 다른 키워드로 시도해보세요.")
        return []
    
    # UI 표시
    display_similar_cases(similar_cases)
    
    # similar_cases 반환 (unified_script_generator에서 사용)
    return similar_cases