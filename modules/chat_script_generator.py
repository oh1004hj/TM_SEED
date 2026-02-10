"""
TM SEED - AI 스크립트 상담 모듈 (Chat 탭)
- 우수사례 검색: unified_script_database 사용
- AI 생성: unified_script_generator 사용
- Edge TTS 음성 변환 (개선)
"""

import streamlit as st
import subprocess
import os
import hashlib
import re
from core import unified_script_database as db
from core import unified_script_generator as generator

# ============================================================
# 텍스트 정리 함수 (TTS용)
# ============================================================

def clean_markdown_for_tts(text):
    """
    마크다운을 TTS용 순수 텍스트로 변환
    - 특수문자, 이모지, 마크다운 문법 제거
    """
    # 1. 마크다운 헤더 제거 (###, ##, #)
    text = re.sub(r'#+\s*', '', text)
    
    # 2. 볼드/이탤릭 제거 (**, __, *, _)
    text = re.sub(r'\*\*|\*|__|_', '', text)
    
    # 3. 이모지 제거
    text = re.sub(r'[📌💬🎭✅❌🔍⭐📝📄🎯📋🏆💡🤖🔊▶️]', '', text)
    
    # 4. 특수문자 제거 (마크다운 관련)
    text = re.sub(r'[`\-]+', '', text)
    
    # 5. 괄호 안 설명 제거 (예: "(3초 이내)")
    text = re.sub(r'\([^)]*\)', '', text)
    
    # 6. 대괄호 제거 ([TM 대상군 분류])
    text = re.sub(r'\[|\]', '', text)
    
    # 7. 연속 공백/줄바꿈 정리
    text = re.sub(r'\s+', ' ', text)
    
    # 8. 앞뒤 공백 제거
    return text.strip()

# ============================================================
# 우수사례 스크립트 포맷팅 함수 (무료 버전)
# ============================================================

def format_script_with_opening_options(script_text, coaching=""):
    """
    무료 버전: 2가지 오프닝 옵션 + 기존 스크립트 조합
    
    Args:
        script_text: 기존 우수사례 스크립트
        coaching: 비언어적 코칭 정보
    
    Returns:
        4단 구조 포맷팅된 스크립트 (섹션 구분 마커 포함)
    """
    
    # 2가지 오프닝 옵션
    opening_option1 = "안녕하세요, 고객님! 단골 등록하신 [랜드마크]에 위치한 SK텔레콤 [매장명]입니다."
    opening_option2 = "안녕하세요, 고객님! 단골 등록하신 SK텔레콤 [매장명]입니다."
    
    # 예시
    opening_examples = """
**사용 예시:**
- 옵션 1: "안녕하세요, 고객님! 단골 등록하신 강남역 10번 출구 근처에 위치한 SK텔레콤 강남점입니다."
- 옵션 2: "안녕하세요, 고객님! 단골 등록하신 SK텔레콤 강남점입니다."
"""
    
    # 4단 구조 조립 (섹션별 구분 마커 추가)
    formatted = f"""<SECTION:INFO>
### 📌 미리 확인해야 할 사항
[TM 대상군 분류 및 사전 준비사항]

**새학기 초등, 12세 이하 010**
- A그룹 (12세 이하 가족010 가망군): 28~50세 부모가망 회선 중 자사 자녀회선이 없고, 초등용 키즈App. 월 사용일수 5일 이상
- B그룹 (기기변경 가망군): 매장 단골 고객으로 전화 수신자 및 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준

**타사단골**
- A그룹 (MNP/가족MNP/초고속 동판): 매장에서 등록한 타사 단골고객 *14세 미만 제외

**무약정**
- A그룹 (기기변경 가망군): 무약정, 잔여할부금 20만원 이하
- B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준

**VIP 기변**
- A그룹 (VIP 기기변경 가망군): SKT 장기사용 우수 고객 중 해지이탈 위험이 높은 고객

**갤S26 가망고객 1순위**
- A그룹(갤S26 1순위): S22~S24 & 폴더블4~5 사용, 출시 D+7 內 구매, 잔여할부금 20만원 이하, 단골매장=최근구입매장
- B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준

**갤S26 가망고객 2순위**
- A그룹(갤S26 2순위): S22~S24 & 폴더블4~5 사용, 기기사용 24개월 경과, 잔여할부금 20만원 이하, 단골매장=최근구입매장
- B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준

**갤S26 가망고객 Sim MNP**
- A그룹(갤S26 Sim MNP): K위약금 면제 기간 중 SIM MNP로 인입, USIM 단독개통 고객이거나 중고MNP & 현재 사용단말 최초 출시일자 24개월 경과된 고객
- B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준
</SECTION:INFO>

---

<SECTION:SCRIPT>
### 💬 TM 스크립트

#### 1️⃣ 오프닝 (3초 이내) - 아래 옵션 중 선택

**옵션 1 (랜드마크 포함 - 추천):**
{opening_option1}

**옵션 2 (기본):**
{opening_option2}

{opening_examples}

---

#### 2️⃣~4️⃣ 스크립트 내용

{script_text}
</SECTION:SCRIPT>

---

<SECTION:COACHING>
### 🎭 비언어적 코칭

{coaching if coaching else '''#### 말투 및 억양
- 속도: 오프닝은 또박또박, 본론은 자연스럽게
- 톤: 친근하면서도 전문적인 톤 유지
- 강조점: 혜택 관련 숫자는 명확하게

#### 고객 반응 대처법
- 긍정 반응: 즉시 혜택 상세 설명
- 거절 시: 정중히 마무리, 문자 안내 제안

#### 심리적 장벽 낮추기
- "단골 고객님" 강조로 친밀감 형성
- 부담 없이 정보 제공 위주로 접근'''}
</SECTION:COACHING>

---

<SECTION:TIP>
### 🎯 활용 Tip

- 매장 상황에 맞게 랜드마크를 구체적으로 언급하면 고객 기억 환기에 효과적
- TM 초보자는 옵션 2로 시작, 익숙해지면 옵션 1 활용 권장
</SECTION:TIP>
"""
    return formatted

def display_script_with_colors(script_text):
    """
    스크립트를 섹션별 색상으로 구분하여 Streamlit에 표시
    INFO 섹션은 펼쳐보기(Expander)로 표시 (중첩 없이 독립적으로)
    
    Args:
        script_text: 섹션 마커가 포함된 스크립트
    """
    import re
    
    # 섹션별 색상 정의
    section_colors = {
        "INFO": "#d1ecf1",
        "SCRIPT": "#d4edda",
        "COACHING": "#fff3cd",
        "TIP": "#f8f9fa"
    }
    
    # 섹션별로 분리
    sections = re.split(r'<SECTION:(\w+)>|</SECTION:\w+>', script_text)
    
    current_section = None
    for part in sections:
        if not part or part.strip() == "---":
            continue
        
        # 섹션 태그 감지
        if part in section_colors:
            current_section = part
            continue
        
        # 내용 표시
        if current_section:
            bg_color = section_colors.get(current_section, "#ffffff")
            
            # INFO 섹션은 펼쳐보기로 표시 (중첩 없이)
            if current_section == "INFO":
                # 헤더만 표시
                st.markdown("### 📌 미리 확인해야 할 사항")
                st.caption("[TM 대상군 분류 및 사전 준비사항]")
                
                # 캠페인별 데이터
                campaigns = {
                    "새학기 초등, 12세 이하 010": [
                        "A그룹 (12세 이하 가족010 가망군): 28~50세 부모가망 회선 중 자사 자녀회선이 없고, 초등용 키즈App. 월 사용일수 5일 이상",
                        "B그룹 (기기변경 가망군): 매장 단골 고객으로 전화 수신자 및 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준"
                    ],
                    "타사단골": [
                        "A그룹 (MNP/가족MNP/초고속 동판): 매장에서 등록한 타사 단골고객 *14세 미만 제외"
                    ],
                    "무약정": [
                        "A그룹 (기기변경 가망군): 무약정, 잔여할부금 20만원 이하",
                        "B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준"
                    ],
                    "VIP 기변": [
                        "A그룹 (VIP 기기변경 가망군): SKT 장기사용 우수 고객 중 해지이탈 위험이 높은 고객"
                    ],
                    "갤S26 가망고객 1순위": [
                        "A그룹(갤S26 1순위): S22~S24 & 폴더블4~5 사용, 출시 D+7 內 구매, 잔여할부금 20만원 이하, 단골매장=최근구입매장",
                        "B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준"
                    ],
                    "갤S26 가망고객 2순위": [
                        "A그룹(갤S26 2순위): S22~S24 & 폴더블4~5 사용, 기기사용 24개월 경과, 잔여할부금 20만원 이하, 단골매장=최근구입매장",
                        "B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준"
                    ],
                    "갤S26 가망고객 Sim MNP": [
                        "A그룹(갤S26 Sim MNP): K위약금 면제 기간 중 SIM MNP로 인입, USIM 단독개통 고객이거나 중고MNP & 현재 사용단말 최초 출시일자 24개월 경과된 고객",
                        "B그룹 (가족MNP 가망군): 매장 단골 고객으로 전화 수신자의 가족 가망군 탐색, 직전 구매 이력이 2년 이상 경과했거나, 단말 할부금 잔액이 부담이 없는 수준"
                    ]
                }
                
                # 각 캠페인을 독립적인 Expander로 표시 (중첩 없음)
                for campaign_name, groups in campaigns.items():
                    with st.expander(f"▶ {campaign_name}"):
                        for group in groups:
                            st.markdown(f"- {group}")
            else:
                # 다른 섹션은 기존 방식대로 색상 박스로 표시
                st.markdown(
                    f'<div style="background-color: {bg_color}; padding: 20px; border-radius: 8px; border-left: 4px solid #1f77b4; margin: 10px 0;">{part}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(part)

# ============================================================
# HTML 변환 함수
# ============================================================

def markdown_to_html(markdown_text):
    """
    마크다운을 HTML로 변환 (한글 폰트 포함 + 섹션별 색 구분)
    브라우저에서 열어서 Ctrl+P로 PDF 저장 가능
    """
    import re
    
    # 섹션 마커 제거 및 색상 매핑
    section_colors = {
        "INFO": "#d1ecf1",      # 파란색 - 미리 확인
        "SCRIPT": "#d4edda",    # 초록색 - TM 스크립트
        "COACHING": "#fff3cd",  # 노란색 - 비언어적 코칭
        "TIP": "#f8f9fa"        # 회색 - 활용 Tip
    }
    
    # HTML 본문 구성
    html_body = ""
    
    # 섹션별로 분리 및 처리
    sections = re.split(r'<SECTION:(\w+)>|</SECTION:\w+>', markdown_text)
    
    current_section = None
    for part in sections:
        if not part or part.strip() == "---":
            continue
        
        # 섹션 태그 감지
        if part in section_colors:
            current_section = part
            continue
        
        # 내용 처리
        if current_section:
            bg_color = section_colors.get(current_section, "#ffffff")
        else:
            bg_color = "#ffffff"
        
        # 마크다운을 간단한 HTML로 변환
        content = part.strip()
        content = content.replace('####', '<h4>').replace('###', '<h3>').replace('##', '<h2>')
        content = content.replace('**', '<strong>').replace('</strong>', '</strong>', 1)
        # ** 태그 쌍 처리
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        content = content.replace('\n', '<br>')
        
        # 섹션을 div로 감싸기
        html_body += f"""
        <div class="section" style="background-color: {bg_color}; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #1f77b4;">
            {content}
        </div>
        """
    
    html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TM SEED 스크립트</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        
        h1, h2, h3, h4 {{
            color: #1f77b4;
            margin-top: 20px;
            margin-bottom: 15px;
        }}
        
        h1 {{
            font-size: 1.5em;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 10px;
        }}
        
        h2 {{
            font-size: 1.25em;
            color: #2c5aa0;
            margin-top: 25px;
            font-weight: 700;
        }}
        
        h3 {{
            font-size: 1.25em;
            color: #2c5aa0;
            margin-top: 20px;
            font-weight: 700;
        }}
        
        h4 {{
            font-size: 1.1em;
            color: #3d6fb5;
            margin-top: 15px;
            font-weight: 600;
        }}
        
        p {{
            margin: 10px 0;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        strong {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        
        .section {{
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1f77b4;
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


def markdown_to_html_premium(markdown_text):
    """
    AI 프리미엄 전용 HTML 변환
    - A그룹/B그룹 레이블만 빨간색, 내용은 검정색
    - 오프닝 옵션 레이블만 빨간색, 내용은 검정색
    - 글씨 크기 14px 균일화
    - ai프리미엄_베스트_양식.html 스타일 적용
    """
    import re
    
    # 섹션 마커 제거 및 색상 매핑
    section_colors = {
        "INFO": "#d1ecf1",      # 파란색 - 미리 확인
        "SCRIPT": "#d4edda",    # 초록색 - TM 스크립트
        "COACHING": "#fff3cd",  # 노란색 - 비언어적 코칭
        "TIP": "#f8f9fa"        # 회색 - 활용 Tip
    }
    
    # HTML 본문 구성
    html_body = ""
    
    # 섹션별로 분리 및 처리
    sections = re.split(r'<SECTION:(\w+)>|</SECTION:\w+>', markdown_text)
    
    current_section = None
    for part in sections:
        if not part or part.strip() == "---":
            continue
        
        # 섹션 태그 감지
        if part in section_colors:
            current_section = part
            continue
        
        # 내용 처리
        if current_section:
            bg_color = section_colors.get(current_section, "#ffffff")
        else:
            bg_color = "#ffffff"
        
        content = part.strip()
        
        # 빈 섹션 건너뛰기
        if not content or len(content) < 5:
            continue
        
        # === AI 프리미엄 전용 처리 ===
        
        # 1. --- 구분선 제거
        content = content.replace('---', '')
        
        # 2. A그룹/B그룹 색상 처리 (레이블만 빨간색)
        content = re.sub(
            r'- (A그룹|B그룹) \(([^)]+)\):',
            r'- <span class="group-label">\1 (\2):</span>',
            content
        )
        
        # 3. 오프닝 옵션 색상 처리 (레이블만 빨간색)
        content = re.sub(
            r'\*\*(옵션 \d+[^:]*?):\*\*',
            r'<span class="option-label">\1:</span>',
            content
        )
        
        # 4. 헤더 변환
        content = re.sub(r'####\s*(.+?)(?=<br>|$)', r'<h4>\1</h4>', content)
        content = re.sub(r'###\s*(.+?)(?=<br>|$)', r'<h3>\1</h3>', content)
        content = re.sub(r'##\s*(.+?)(?=<br>|$)', r'<h2>\1</h2>', content)
        
        # 5. 나머지 **텍스트** 처리 (강조용)
        content = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', content)
        
        # 6. 과도한 줄바꿈 정리 (4개 이상 → 2개)
        content = re.sub(r'(<br>\s*){4,}', '<br><br>', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 7. 줄바꿈을 <br>로 변환 (헤더 제외)
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            # 이미 HTML 태그가 있는 줄은 그대로
            if line.strip().startswith('<h') or line.strip().startswith('</h'):
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        content = '<br>'.join(processed_lines)
        
        # 8. 연속된 <br> 정리
        content = re.sub(r'(<br>\s*){3,}', '<br><br>', content)
        
        # 섹션을 div로 감싸기
        html_body += f"""
    <div class="section" style="background-color: {bg_color}; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #1f77b4;">
        {content}
    </div>
    """
    
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TM SEED 스크립트</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.8;
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
            margin-top: 20px;
            font-weight: 700;
        }}
        
        h4 {{
            font-size: 1.15em;
            color: #3d6fb5;
            margin-top: 15px;
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
        
        /* A그룹/B그룹 레이블만 빨간색, 나머지는 검정색 */
        .group-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        /* 오프닝 옵션 레이블만 빨간색 */
        .option-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        
        .section {{
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1f77b4;
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


def markdown_to_html_free(markdown_text):
    """
    우수사례 전용 HTML 변환
    - A그룹/B그룹 레이블만 빨간색, 내용은 검정색
    - 오프닝 옵션 레이블만 빨간색, 내용은 검정색
    - 글씨 크기 14px 균일화
    - --- 구분선 제거
    - 빈 섹션 제거
    """
    import re
    
    # 섹션 마커 제거 및 색상 매핑
    section_colors = {
        "INFO": "#d1ecf1",      # 파란색 - 미리 확인
        "SCRIPT": "#d4edda",    # 초록색 - TM 스크립트
        "COACHING": "#fff3cd",  # 노란색 - 비언어적 코칭
        "TIP": "#f8f9fa"        # 회색 - 활용 Tip
    }
    
    # HTML 본문 구성
    html_body = ""
    
    # 섹션별로 분리 및 처리
    sections = re.split(r'<SECTION:(\w+)>|</SECTION:\w+>', markdown_text)
    
    current_section = None
    for part in sections:
        if not part or part.strip() == "---":
            continue
        
        # 섹션 태그 감지
        if part in section_colors:
            current_section = part
            continue
        
        # 내용 처리
        if current_section:
            bg_color = section_colors.get(current_section, "#ffffff")
        else:
            bg_color = "#ffffff"
        
        content = part.strip()
        
        # 빈 섹션 건너뛰기
        if not content or len(content) < 5:
            continue
        
        # === 우수사례 전용 처리 ===
        
        # 1. --- 구분선 제거
        content = content.replace('---', '')
        
        # 2. 하드코딩된 캠페인명 처리 (강조 태그를 일반 검정색으로)
        content = re.sub(
            r'\*\*(새학기[^*]+|타사단골|무약정|VIP[^*]+|갤S26[^*]+)\*\*',
            r'<strong style="color: #333; font-weight: 700;">\1</strong>',
            content
        )
        
        # 3. A그룹/B그룹 색상 처리 (레이블만 빨간색)
        # 패턴 1: - A그룹 (...): 형태 (하이픈 있음)
        content = re.sub(
            r'- (A그룹|B그룹) \(([^)]+)\):',
            r'- <span class="group-label">\1 (\2):</span>',
            content
        )
        
        # 패턴 2: A그룹(...): 형태 (하이픈 없음, 갤S26 등)
        content = re.sub(
            r'(A그룹|B그룹)\(([^)]+)\):',
            r'<span class="group-label">\1(\2):</span>',
            content
        )
        
        # 4. 오프닝 옵션 색상 처리 (레이블만 빨간색)
        content = re.sub(
            r'\*\*(옵션 \d+[^:]*?):\*\*',
            r'<span class="option-label">\1:</span>',
            content
        )
        
        # 5. 사용 예시 레이블 처리
        content = re.sub(
            r'\*\*(사용 예시):\*\*',
            r'<span class="option-label">\1:</span>',
            content
        )
        
        # 6. 헤더 변환
        content = re.sub(r'####\s*(.+?)(?=\n|$)', r'<h4>\1</h4>', content)
        content = re.sub(r'###\s*(.+?)(?=\n|$)', r'<h3>\1</h3>', content)
        content = re.sub(r'##\s*(.+?)(?=\n|$)', r'<h2>\1</h2>', content)
        
        # 7. 나머지 **텍스트** 처리 (강조용 빨간색)
        content = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', content)
        
        # 8. 과도한 줄바꿈 정리
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 9. 줄바꿈을 <br>로 변환
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip().startswith('<h') or line.strip().startswith('</h'):
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        content = '<br>'.join(processed_lines)
        
        # 10. 연속된 <br> 정리 (3개 이상 → 2개)
        content = re.sub(r'(<br>\s*){3,}', '<br><br>', content)
        
        # 11. 헤더 바로 뒤 공백 완전 제거 (여러 개도 제거)
        content = re.sub(r'(</h\d>)(<br>\s*)+', r'\1', content)
        
        # 섹션을 div로 감싸기
        html_body += f"""
    <div class="section" style="background-color: {bg_color}; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #1f77b4;">
        {content}
    </div>
    """
    
    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TM SEED 스크립트</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.8;
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
            margin-top: 20px;
            font-weight: 700;
        }}
        
        h4 {{
            font-size: 1.15em;
            color: #3d6fb5;
            margin-top: 15px;
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
        
        /* A그룹/B그룹 레이블만 빨간색 */
        .group-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        /* 오프닝 옵션 레이블만 빨간색 */
        .option-label {{
            color: #d9534f;
            font-weight: 700;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        
        .section {{
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1f77b4;
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


# ============================================================
# Edge TTS 함수
# ============================================================

@st.cache_data(show_spinner=False)
def generate_tts_subprocess(text, voice_id):
    """Edge TTS CLI로 음성 생성 (subprocess) - 속도 조정"""
    try:
        # 텍스트 해시로 고유 파일명 생성 (캐싱용)
        text_hash = hashlib.md5((text + voice_id).encode()).hexdigest()[:8]
        temp_file = f"temp_{text_hash}.mp3"
        
        # edge-tts CLI 실행 (속도 -10% 느리게)
        command = [
            "edge-tts",
            "--voice", voice_id,
            "--rate=-10%",  # 10% 느리게 (띄어쓰기 명확화)
            "--text", text,
            "--write-media", temp_file
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 파일 읽기
        with open(temp_file, "rb") as f:
            audio_bytes = f.read()
        
        # 임시 파일 삭제
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return audio_bytes
        
    except subprocess.CalledProcessError as e:
        st.error(f"음성 생성 오류: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        return None

# ============================================================
# 메인 UI 함수
# ============================================================

def show_chat_script_page(model=None, sheets_client=None):
    """AI 스크립트 상담 메인 페이지"""
    
    st.markdown("#### 💬 Chat 기반 스크립트 검색 & 생성")
    
    # Google Sheets URL
    sheet_url = st.secrets.get("google", {}).get("sheet_url", None) if hasattr(st, 'secrets') else None
    
    # unified DB 데이터 로드 (캐싱)
    try:
        all_data = db.load_all_data(sheets_client, sheet_url)
        
        # 데이터 통계 표시
        stats = db.get_data_statistics(all_data)
        st.caption(f"📊 활용 가능한 데이터: Google Sheets {stats['google_sheets_count']}개 + JSON 우수사례 {stats['json_excellent_count']}개 + 템플릿 {stats['json_template_count']}개")
    except Exception as e:
        st.error(f"⚠️ 데이터 로드 중 오류: {str(e)}")
        all_data = None
    
    # ============================================================
    # 1. 입력창
    # ============================================================
    user_request = st.text_area(
        "원하는 스크립트를 요청하세요",
        height=100,
        placeholder="예: 키즈폰 가망 스크립트\n예: S26 가망 스크립트\n예: 무약정 기변 가망 스크립트",
        key="chat_request"
    )
    
    # ============================================================
    # 2. 버튼 선택 (2개 나란히)
    # ============================================================
    col1, col2 = st.columns(2)
    
    with col1:
        search_cases = st.button(
            "🏆 우수사례 검색 (무료, 즉시)",
            use_container_width=True,
            type="secondary",
            help="통합 데이터베이스에서 우수사례 검색"
        )
        st.caption("⭐ **실제 통화 + JSON 우수사례 + 템플릿 통합 검색**")
    
    with col2:
        generate_ai = st.button(
            "✨ AI 프리미엄 (맞춤형)",
            use_container_width=True,
            type="primary",
            help="Gemini AI가 우수사례를 참고하여 Alice의 4단 구조로 맞춤형 스크립트 생성"
        )
        st.caption("🤖 **Alice의 4단 구조 + 비언어적 코칭**")
    
    # 안내 메시지
    st.info("💡 **우수사례 검색**: 통합 DB에서 키워드 매칭 (무료, 최대 5개)\n✨ **AI 프리미엄**: Gemini가 Alice의 4단 구조로 맞춤 생성 (~₩0.5/회)")
    
    # ============================================================
    # 3-A. 우수사례 검색 (무료) - 디버그 정보 추가
    # ============================================================
    if search_cases and user_request:
        st.markdown("---")
        st.markdown("### 🔍 우수사례 검색 중...")
        
        # 디버그 1: 버튼 클릭 확인
        st.write("✅ [디버그] 버튼 클릭됨!")
        st.write(f"📝 [디버그] 입력된 요청: `{user_request}`")
        
        # 디버그 2: 데이터 로드 확인
        if not all_data:
            st.error("❌ [디버그] 데이터 로드 실패! Google Sheets 연결을 확인하세요.")
        else:
            st.write(f"✅ [디버그] 데이터 로드 성공!")
            st.write(f"📊 [디버그] 데이터 통계: {stats}")
        
        with st.spinner("🔍 통합 데이터베이스에서 우수사례를 검색하는 중..."):
            try:
                st.info(f"🔍 검색어: {user_request[:100]}...")
                
                # unified DB 검색
                results = db.search_cases(
                    query=user_request,
                    all_data=all_data,
                    source="all",  # 모든 소스 검색
                    top_n=5
                )
                
                # 디버그 3: 검색 결과 확인
                st.write(f"🔍 [디버그] 검색 결과 개수: {len(results) if results else 0}개")
                
                if results:
                    st.success(f"✅ 검색 성공: {len(results)}개 발견")
                
                if results:
                    st.success(f"✅ {len(results)}개의 결과를 찾았습니다!")
                    
                    # 디버그 4: 첫 번째 결과 미리보기
                    with st.expander("🔍 [디버그] 첫 번째 검색 결과 미리보기"):
                        st.json(results[0])
                    
                    st.markdown("---")
                    st.markdown("##### 📋 검색 결과")
                    
                    # 결과 표시
                    for idx, result in enumerate(results, 1):
                        출처 = result.get("출처", "")
                        
                        # 제목 구성
                        if "우수사례" in 출처 or "Google Sheets" in 출처:
                            st.markdown(f"**🏆 #{idx} 우수사례 (점수: {result.get('종합점수', 'N/A')}점) | 출처: {출처}**")
                            st.markdown(f"**고객 니즈:** {result.get('고객니즈', 'N/A')}")
                            st.markdown(f"**통화 결과:** {result.get('통화결과', 'N/A')}")
                        
                        elif "JSON 우수사례" in 출처:
                            st.markdown(f"**⭐ #{idx} JSON 우수사례 (점수: {result.get('종합점수', 'N/A')}점)**")
                            st.markdown(f"**파일명:** {result.get('파일명', 'N/A')}")
                            st.markdown(f"**강점:** {result.get('강점', 'N/A')}")
                        
                        else:  # JSON 템플릿
                            st.markdown(f"**📚 #{idx} 템플릿 - {result.get('카테고리', '')}**")
                            st.markdown(f"**상황:** {result.get('세그먼트', 'N/A')}")
                        
                        st.markdown("---")
                        st.markdown("**📋 스크립트 (4단 구조)**")
                        
                        # 기존 스크립트와 코칭 정보 가져오기
                        script = result.get('추천스크립트', result.get('스크립트', 'N/A'))
                        coaching = result.get('비언어적코칭', result.get('코칭', ''))
                        
                        # 4단 구조로 포맷팅 (무료)
                        formatted_script = format_script_with_opening_options(script, coaching)
                        
                        # 섹션별 색상 구분하여 표시
                        display_script_with_colors(formatted_script)
                        
                        # 버튼 2개 (사용 / HTML 다운로드)
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button(f"✅ 이 스크립트 사용", key=f"use_{idx}"):
                                st.session_state['generated_script'] = formatted_script
                                st.session_state['script_data'] = result
                                st.success("✅ 스크립트가 선택되었습니다!")
                        
                        with col_btn2:
                            # HTML 다운로드 (우수사례 전용 함수 사용)
                            html_content = markdown_to_html_free(formatted_script)
                            st.download_button(
                                label="📥 HTML 다운로드",
                                data=html_content.encode('utf-8'),
                                file_name=f"tm_script_{idx}.html",
                                mime="text/html",
                                key=f"download_{idx}"
                            )
                        
                        st.markdown("---")
                else:
                    st.warning("🔍 매칭되는 결과가 없습니다.")
                    st.write("💡 [디버그] 시도해볼 방법:")
                    st.write("1. 검색어를 더 간단하게 (예: '초등학생', '아이폰', '요금제')")
                    st.write("2. 다른 키워드로 검색")
                    st.write("3. AI 프리미엄 버튼 사용")
                    
            except Exception as e:
                st.error(f"❌ [디버그] 검색 중 오류 발생: {str(e)}")
                import traceback
                with st.expander("🔍 [디버그] 상세 오류 정보"):
                    st.code(traceback.format_exc())
    
    # ============================================================
    # 3-B. AI 프리미엄 생성 (유료) - UI 개선
    # ============================================================
    if generate_ai and user_request:
        if not model:
            st.error("⚠️ Gemini API 연결이 필요합니다.")
        else:
            with st.spinner("🤖 Gemini AI가 Alice의 4단 구조로 맞춤형 스크립트를 생성하는 중... (5-10초 소요)"):
                try:
                    # unified DB 검색
                    cases = db.search_cases(
                        query=user_request,
                        all_data=all_data,
                        source="all",
                        top_n=3
                    )
                    
                    # unified generator로 생성
                    script_markdown = generator.generate_script(
                        model=model,
                        cases=cases,
                        user_request=user_request
                    )
                    
                    if script_markdown:
                        st.session_state['generated_script_full'] = script_markdown
                        st.success("✅ AI 맞춤형 스크립트 생성 완료!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ 스크립트 생성 중 오류: {str(e)}")
    
    # ============================================================
    # 4. AI 생성 결과 표시 (UI 개선: 탭 + Expander + 컬러 박스)
    # ============================================================
    if 'generated_script_full' in st.session_state:
        st.markdown("---")
        st.markdown("## 📋 AI 생성 스크립트")
        
        full_script = st.session_state['generated_script_full']
        
        # 탭으로 구분 (섹션별 보기 삭제, 전체 보기에 색 구분 추가)
        tab1, tab2 = st.tabs(["📄 전체 보기", "📥 다운로드"])
        
        with tab1:
            # 전체 스크립트를 섹션별로 색 구분하여 표시
            sections = full_script.split("---")
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                if "미리 확인해야 할 사항" in section:
                    st.markdown("### 🔍 미리 확인해야 할 사항")
                    st.info(section.replace("### 📌 미리 확인해야 할 사항", "").replace("### 미리 확인해야 할 사항", "").strip())
                
                elif "TM 스크립트" in section:
                    st.markdown("### 💬 TM 스크립트")
                    st.success(section.replace("### 💬 TM 스크립트", "").strip())
                
                elif "비언어적 코칭" in section:
                    st.markdown("### 🎭 비언어적 코칭")
                    st.warning(section.replace("### 🎭 비언어적 코칭", "").strip())
                
                elif "종합 Tip" in section or "우수사례 공통 패턴" in section:
                    st.markdown("### 🎯 종합 Tip")
                    st.markdown(section)
        
        with tab2:
            # 다운로드 버튼 (마크다운 + HTML)
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 마크다운 다운로드",
                    data=full_script,
                    file_name="tm_script.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                st.caption("💡 메모장이나 마크다운 뷰어로 열기")
            
            with col2:
                # HTML 변환 (AI 프리미엄 전용 함수 사용)
                html_content = markdown_to_html_premium(full_script)
                st.download_button(
                    label="📄 HTML 다운로드 (PDF 인쇄용)",
                    data=html_content,
                    file_name="tm_script.html",
                    mime="text/html",
                    use_container_width=True
                )
                st.caption("💡 브라우저에서 열고 Ctrl+P로 PDF 저장")
        
        # TTS용 스크립트 추출
        st.session_state['generated_script'] = full_script
    
    # ============================================================
    # 5. 검색 결과 표시 (기존)
    # ============================================================
    if 'script_data' in st.session_state and 'generated_script_full' not in st.session_state:
        script_data = st.session_state['script_data']
        
        st.markdown("---")
        st.markdown("##### 📋 선택된 스크립트")
        
        # 출처 표시
        if '출처' in script_data:
            st.caption(f"📌 출처: {script_data.get('출처', 'N/A')}")
        
        # 스크립트 표시
        st.success(script_data.get('스크립트', script_data.get('추천스크립트', '')))
        
        # 코칭 정보
        if '비언어적코칭' in script_data or '코칭' in script_data:
            코칭 = script_data.get('비언어적코칭', script_data.get('코칭', ''))
            if 코칭:
                with st.expander("🎭 비언어적 코칭 보기"):
                    st.info(코칭)
    
    # ============================================================
    # 6. Edge TTS 음성 변환 (선희, 현수만 + 특수기호 제거)
    # ============================================================
    st.markdown("---")
    st.markdown("##### 🎤 음성 변환 (Edge TTS)")
    
    # TTS 입력창
    tts_text = st.text_area(
        "테스트할 스크립트",
        value=st.session_state.get('generated_script', ''),
        height=150,
        placeholder="검색/생성된 스크립트가 자동으로 입력됩니다. 수정 가능합니다.",
        key="tts_input"
    )
    
    # 음성 선택 (선희, 현수만)
    st.markdown("**🔊 음성 선택**")
    voices = {
        "선희 (여성, 밝고 친근)": "ko-KR-SunHiNeural",
        "현수 (남성, 부드럽고 전문적)": "ko-KR-HyunsuNeural"
    }
    
    st.info("💡 **자동 처리**: 특수문자, 이모지, 마크다운 문법은 자동으로 제거되어 읽기 쉽게 변환됩니다.")
    
    cols = st.columns(2)
    for idx, (name, voice_id) in enumerate(voices.items()):
        with cols[idx]:
            short_name = name.split('(')[0].strip()
            if st.button(f"▶️ {short_name}", key=f"tts_{voice_id}", use_container_width=True):
                if tts_text:
                    with st.spinner(f"{short_name} 음성 생성 중..."):
                        # 특수기호 제거
                        clean_text = clean_markdown_for_tts(tts_text)
                        
                        # 미리보기
                        with st.expander("🔍 음성 변환될 텍스트 미리보기"):
                            st.text(clean_text[:500] + "..." if len(clean_text) > 500 else clean_text)
                        
                        audio_bytes = generate_tts_subprocess(clean_text, voice_id)
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
                            st.success("✅ 재생 완료!")
                else:
                    st.warning("⚠️ 텍스트를 입력해주세요")