"""
Phase 2 Script Generator
유사 성공 케이스를 기반으로 실전 활용 스크립트 생성
"""

import streamlit as st
import google.generativeai as genai


def generate_practical_script(model, similar_cases, current_result):
    """
    유사 성공 케이스를 기반으로 실전 활용 스크립트 생성
    
    Args:
        model: Gemini AI 모델
        similar_cases: 유사 케이스 TOP 3 리스트
        current_result: 현재 통화 분석 결과
    
    Returns:
        str: 생성된 실전 스크립트 (마크다운 형식)
    """
    
    # 유사 케이스 요약
    cases_summary = []
    for idx, case in enumerate(similar_cases, 1):
        summary = f"""
케이스 {idx}:
- 통화 결과: {case.get('통화결과', 'N/A')}
- 종합 점수: {case.get('종합점수', 'N/A')}
- 고객 니즈: {case.get('고객니즈', 'N/A')}
- 강점: {', '.join(case.get('강점', [])[:2])}
"""
        cases_summary.append(summary)
    
    # 현재 상황 요약
    current_summary = f"""
현재 통화 분석:
- 통화 결과: {current_result.get('통화결과', 'N/A')}
- 고객 니즈: {current_result.get('고객니즈', 'N/A')}
- 개선점: {', '.join(current_result.get('개선점', [])[:2])}
"""
    
    # Gemini 프롬프트
    prompt = f"""당신은 SK텔레콤 텔레마케팅(TM) 스크립트 작성 전문가입니다.

## 현재 통화 상황
{current_summary}

## 유사 성공 케이스 분석
{''.join(cases_summary)}

## 요청사항
위 성공 케이스들을 분석하여, **실전에서 바로 활용 가능한 대화 스크립트**를 작성해주세요.

### 중요한 비즈니스 논리 (반드시 반영)
1. **무약정 → 약정 전환 시:**
   - 약정 할인 금액이 신규 단말기 할부금을 상쇄한다는 논리
   - 예: "약정으로 전환하시면 할인받으시는 금액으로 신규 단말기 비용을 충분히 커버하실 수 있습니다"
   - ⚠️ 구체적 금액은 절대 넣지 말 것 (실시간 가격 변동)

2. **스크립트 특징:**
   - 길이: 1분 분량 (자연스럽게 말할 수 있는 분량)
   - 고객 심리적 저항 최소화
   - 숫자보다 "방향성"과 "논리" 강조
   - T크루들이 이미 알고 있는 일반적인 논리 활용

### 출력 형식 (반드시 이 형식 준수)

#### 💬 상황별 대화 시나리오

**고객:** [고객의 전형적인 말/반응]

**TM:** [T크루의 응답 - 약정 전환 논리 포함, 1분 분량]

**고객:** [예상되는 고객 추가 질문]

**TM:** [마무리 멘트]

---

#### 🎯 핵심 포인트
1. [첫 번째 핵심 논리 - 약정 할인 = 단말 비용 상쇄]
2. [두 번째 핵심 논리]
3. [세 번째 핵심 논리]

---

#### 📝 상황별 응용 가이드

**[상황 1] 고객이 요금 부담을 느낄 때:**
→ [응용 방법 - 구체적 금액 없이 논리로 설명]

**[상황 2] 고객이 약정에 거부감이 있을 때:**
→ [응용 방법]

**[상황 3] 고객이 단말 교체를 고민할 때:**
→ [응용 방법]

---

#### ⚠️ 주의사항
- [피해야 할 표현이나 접근]
- [강조해야 할 부분]

**중요: 구체적인 금액, 모델명, 요금제 이름은 절대 포함하지 마세요. 논리와 방향성만 제시하세요.**
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        return f"⚠️ 스크립트 생성 중 오류 발생: {str(e)}"


def display_practical_script(model, similar_cases, current_result):
    """
    실전 활용 스크립트를 Streamlit에 표시
    
    Args:
        model: Gemini AI 모델
        similar_cases: 유사 케이스 TOP 3 리스트
        current_result: 현재 통화 분석 결과
    """
    
    st.markdown("---")
    st.markdown("## 📝 실전 활용 스크립트")
    st.info("💡 위 유사 성공 케이스를 기반으로 실전에서 바로 활용 가능한 스크립트를 생성합니다.")
    
    # 스크립트 생성 버튼
    if st.button("🎯 실전 스크립트 생성", use_container_width=True):
        with st.spinner("🤖 AI가 실전 스크립트를 생성하는 중입니다... (20-30초 소요)"):
            script = generate_practical_script(model, similar_cases, current_result)
            
            # 세션 스테이트에 저장
            st.session_state['generated_script'] = script
    
    # 생성된 스크립트 표시
    if 'generated_script' in st.session_state:
        st.markdown(st.session_state['generated_script'])
        
        # 다운로드 버튼
        st.download_button(
            label="📥 스크립트 다운로드",
            data=st.session_state['generated_script'],
            file_name="tm_script.md",
            mime="text/markdown"
        )