"""
TM SEED - 통합 스크립트 생성 모듈
Alice의 4단 구조 + 우수사례 패턴 반영
"""

import streamlit as st


def generate_script(model=None, cases=None, user_request="", current_result=None):
    """
    우수사례 기반 맞춤형 스크립트 생성 (Alice의 4단 구조)
    오프닝은 Python에서 강제 삽입하여 항상 고정
    
    Args:
        model: Gemini AI 모델 (선택)
        cases (list): 검색된 우수사례 리스트 (선택)
        user_request (str): 사용자 요청
        current_result (dict): 현재 통화 분석 결과 (선택)
    
    Returns:
        str: 생성된 스크립트 (마크다운 형식, 섹션 마커 포함)
    """
    
    # model이 없는 경우 오류 처리
    if model is None:
        return "⚠️ AI 모델이 초기화되지 않았습니다."
    
    # 우수사례 요약
    cases_summary = ""
    if cases:
        cases_summary = "\n\n## 📚 참고할 우수사례\n"
        for idx, case in enumerate(cases[:3], 1):  # 최대 3개
            cases_summary += f"""
### 우수사례 {idx} (점수: {case.get('종합점수', 'N/A')}점)
- **출처**: {case.get('출처', 'N/A')}
- **강점**: {case.get('강점', 'N/A')}
- **고객니즈**: {case.get('고객니즈', 'N/A')}
- **스크립트 예시**: 
{case.get('추천스크립트', case.get('스크립트', 'N/A'))[:200]}...
"""
    
    # 현재 통화 상황 (있는 경우)
    current_context = ""
    if current_result:
        current_context = f"""
## 🎯 현재 통화 분석 결과
- **통화결과**: {current_result.get('통화결과', 'N/A')}
- **고객니즈**: {current_result.get('고객니즈', 'N/A')}
- **개선점**: {', '.join(current_result.get('개선점', [])[:2]) if isinstance(current_result.get('개선점'), list) else current_result.get('개선점', 'N/A')}
"""
    
    # Gemini 프롬프트 (오프닝 제외 - 단순화)
    prompt = f"""당신은 SK텔레콤 TM 스크립트 작성 전문가입니다.

## 사용자 요청
{user_request}

{current_context}

{cases_summary}

---

## 📝 출력 형식

### 📌 미리 확인해야 할 사항
[TM 대상군 분류 및 사전 준비사항]

사용자 요청 "{user_request}"을 분석하여 적절한 A그룹/B그룹을 정의하세요.

참고 예시:
- S26 가망 → A그룹(고기능 단말 선호군), B그룹(교체 주기 도래군)
- 무약정 → A그룹(무약정 기기변경), B그룹(가족MNP 가망)
- 초등학생 → A그룹(12세 이하 가족010), B그룹(기기변경 가망)

---

### 💬 TM 스크립트

#### 2️⃣ 확인 질문 (고객 상황 파악)
[확인 질문 형태로 작성, 단정적 표현 금지]
예: "혹시 자녀분 중에 초등학생 계신가요?"

(고객 응답 대기)

#### 3️⃣ 본론 (핵심 혜택 안내)
[구체적 숫자와 혜택 중심, 2-3문장]
- 구체적 할인율/금액 언급
- "저희 매장에서 별도로 사은품도 준비해드릴 수 있어요" 형태

#### 4️⃣ 클로징 (내방 유도)
[구체적 행동 유도, 1-2문장]
- 매장 위치나 방문 시간 제안
- 예: "이번 주말 토요일 2시쯤 시간 괜찮으실까요?"

---

### 🎭 비언어적 코칭

#### 말투 및 억양
[속도, 톤, 강조점 가이드]

#### 고객 반응 대처법
[긍정/거절 시 대응 전략]

#### 심리적 장벽 낮추기
[신뢰감 형성 및 부담 완화 전략]

---

주의사항:
1. 마크다운 형식으로 출력하되, 코드블록(```)은 사용하지 마세요.
2. "단골 등록하신" 표현 필수 사용
3. 확인 질문은 "혹시 ~계신가요?" 형태 (단정 금지)
4. 구체적 숫자 언급 ("25% 할인", "20만원" 등)
"""
    
    try:
        # Gemini 호출 (오프닝 없이)
        response = model.generate_content(prompt)
        ai_result = response.text.strip()
        
        # Python에서 오프닝 강제 삽입
        fixed_opening = """### 💬 TM 스크립트

#### 1️⃣ 오프닝 (3초 이내)

**옵션 1 (랜드마크 포함 - 추천):**
안녕하세요, 고객님! 단골 등록하신 [랜드마크]에 위치한 SK텔레콤 [매장명]입니다.
이번에 단골 고객님께만 드리는 특별한 혜택이 있어 연락드렸습니다.

**옵션 2 (기본):**
안녕하세요, 고객님! 단골 등록하신 SK텔레콤 [매장명]입니다.
이번에 단골 고객님께만 드리는 특별한 혜택이 있어 연락드렸습니다.

---

"""
        
        # AI 결과에서 "### 💬 TM 스크립트" 찾아서 오프닝과 함께 재조립
        if "### 💬 TM 스크립트" in ai_result:
            # AI가 생성한 "### 💬 TM 스크립트"를 기준으로 분리
            parts = ai_result.split("### 💬 TM 스크립트", 1)
            
            # 재조립: 앞부분 + 오프닝 + "### 💬 TM 스크립트" + 뒷부분(AI 생성 내용)
            final_result = parts[0] + fixed_opening + "### 💬 TM 스크립트\n\n" + parts[1]
        else:
            # 못 찾으면 미리 확인사항 뒤에 오프닝 삽입
            if "---" in ai_result:
                first_separator = ai_result.find("---")
                final_result = ai_result[:first_separator + 3] + "\n\n" + fixed_opening + ai_result[first_separator + 3:]
            else:
                # 최후의 수단: 그냥 뒤에 붙임
                final_result = ai_result + "\n\n" + fixed_opening
        
        # 섹션 마커 추가 (HTML 색상 구분용)
        final_result = add_section_markers(final_result)
        
        return final_result
    
    except Exception as e:
        return f"⚠️ 스크립트 생성 중 오류 발생: {str(e)}"


def add_section_markers(markdown_text):
    """
    마크다운 텍스트에 섹션 마커 추가 (HTML 색상 구분용)
    
    Args:
        markdown_text (str): 마크다운 형식의 스크립트
    
    Returns:
        str: 섹션 마커가 추가된 스크립트
    """
    
    result = ""
    lines = markdown_text.split('\n')
    current_section = None
    section_content = []
    
    for line in lines:
        # 섹션 시작 감지
        if '📌 미리 확인해야 할 사항' in line or '📌 미리 확인' in line:
            # 이전 섹션 닫기
            if current_section and section_content:
                result += '\n'.join(section_content) + f'\n</SECTION:{current_section}>\n\n'
            
            # 새 섹션 시작
            current_section = 'INFO'
            section_content = [f'<SECTION:{current_section}>', line]
        
        elif '💬 TM 스크립트' in line:
            # 이전 섹션 닫기
            if current_section and section_content:
                result += '\n'.join(section_content) + f'\n</SECTION:{current_section}>\n\n'
            
            # 새 섹션 시작
            current_section = 'SCRIPT'
            section_content = [f'<SECTION:{current_section}>', line]
        
        elif '🎭 비언어적 코칭' in line:
            # 이전 섹션 닫기
            if current_section and section_content:
                result += '\n'.join(section_content) + f'\n</SECTION:{current_section}>\n\n'
            
            # 새 섹션 시작
            current_section = 'COACHING'
            section_content = [f'<SECTION:{current_section}>', line]
        
        else:
            if current_section:
                section_content.append(line)
            else:
                result += line + '\n'
    
    # 마지막 섹션 닫기
    if current_section and section_content:
        result += '\n'.join(section_content) + f'\n</SECTION:{current_section}>\n'
    
    return result


def generate_script_json_format(model=None, cases=None, user_request=""):
    """
    JSON 형식으로 스크립트 생성 (구조화된 데이터 필요 시)
    
    Args:
        model: Gemini AI 모델 (선택)
        cases (list): 검색된 우수사례 리스트 (선택)
        user_request (str): 사용자 요청
    
    Returns:
        dict: JSON 형태의 스크립트 데이터
    """
    
    # model이 없는 경우 오류 처리
    if model is None:
        st.error("⚠️ AI 모델이 초기화되지 않았습니다.")
        return None
    
    # 우수사례 요약
    cases_text = ""
    if cases:
        cases_text = "\n참고할 우수사례:\n"
        for idx, case in enumerate(cases[:3], 1):
            cases_text += f"\n사례 {idx} (점수: {case.get('종합점수', 'N/A')}점):\n"
            cases_text += f"- 강점: {case.get('강점', 'N/A')}\n"
            cases_text += f"- 고객니즈: {case.get('고객니즈', 'N/A')}\n"
    
    prompt = f"""당신은 SK텔레콤 TM 스크립트 작성 전문가입니다.

사용자 요청: {user_request}

{cases_text}

Alice의 4단 구조로 스크립트를 작성하고, JSON 형식으로 출력해주세요.

반드시 아래 JSON 형식을 따르세요 (마크다운 없이 순수 JSON만):

{{
  "미리_확인사항": "TM 대상군 분류 및 사전 준비",
  "스크립트": {{
    "오프닝": "3초 이내, 단골 등록하신 표현 포함",
    "확인질문": "혹시 ~계신가요? 형태",
    "본론": "구체적 숫자와 혜택 중심",
    "클로징": "내방 유도 및 구체적 시간 제안"
  }},
  "비언어적코칭": {{
    "말투_억양": "속도, 톤 가이드",
    "고객반응대처": "긍정/거절 시 대응",
    "심리적장벽": "신뢰감 형성 전략"
  }}
}}
"""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # JSON 마크다운 제거
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        import json
        return json.loads(result_text.strip())
    
    except Exception as e:
        st.error(f"JSON 스크립트 생성 중 오류: {e}")
        return None