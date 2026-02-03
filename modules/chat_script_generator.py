import streamlit as st
import json
import subprocess
import os
import hashlib

# JSON 파일 로드
@st.cache_data
def load_script_templates():
    """스크립트 템플릿 JSON 로드"""
    json_path = os.path.join("data", "script_templates.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# TTS 생성 함수
@st.cache_data(show_spinner=False)
def generate_tts_subprocess(text, voice_id):
    """Edge TTS CLI로 음성 생성 (subprocess)"""
    try:
        # 텍스트 해시로 고유 파일명 생성 (캐싱용)
        text_hash = hashlib.md5((text + voice_id).encode()).hexdigest()[:8]
        temp_file = f"temp_{text_hash}.mp3"
        
        # edge-tts CLI 실행
        command = [
            "edge-tts",
            "--voice", voice_id,
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

# 메인 UI
def show_chat_script_page():
    """AI 스크립트 상담 페이지"""
    
    st.title("💬 AI 스크립트 상담")
    st.markdown("고객 유형을 선택하면 **최적화된 텔레마케팅 스크립트**를 즉시 확인할 수 있습니다.")
    st.markdown("---")
    
    # JSON 로드
    templates = load_script_templates()
    
    # 카테고리 정의
    categories = {
        "타사단말_MNP": "📱 타사단골 (MNP 번호이동)",
        "무약정_약정전환": "📋 무약정 → 약정 전환",
        "VIP_프로모션": "⭐ VIP 프로모션 대상",
        "학부모_12세이하": "👨‍👩‍👧 12세이하 학부모",
        "갤럭시S26_가망": "🔥 갤럭시S26 가망고객",
        "직접입력": "✏️ 직접 입력"
    }
    
    # 1단계: 카테고리 선택
    st.subheader("1️⃣ 고객 유형 선택")
    category_key = st.selectbox(
        "고객 유형을 선택하세요",
        options=list(categories.keys()),
        format_func=lambda x: categories[x],
        key="category_select"
    )
    
    # 직접입력 처리
    if category_key == "직접입력":
        st.markdown("---")
        st.subheader("✏️ 직접 입력")
        
        custom_script = st.text_area(
            "스크립트를 직접 입력하세요",
            height=200,
            placeholder="고객님께 전달할 스크립트를 작성해주세요..."
        )
        
        if custom_script:
            st.markdown("---")
            st.subheader("📝 입력하신 스크립트")
            st.info(custom_script)
            
            # TTS 음성 선택
            st.markdown("---")
            st.subheader("🎵 샘플 음성 듣기")
            
            voices = {
                "활기찬 여성 (Sun-Hi)": "ko-KR-SunHiNeural",
                "부드러운 남성 (Hyunsu)": "ko-KR-HyunsuNeural"
            }
            
            cols = st.columns(2)
            for idx, (name, voice_id) in enumerate(voices.items()):
                with cols[idx]:
                    if st.button(f"▶️ {name}", key=f"custom_{voice_id}"):
                        with st.spinner(f"{name} 음성 생성 중..."):
                            audio_bytes = generate_tts_subprocess(custom_script, voice_id)
                            if audio_bytes:
                                st.audio(audio_bytes, format="audio/mp3")
        
        return
    
    # 2단계: 세그먼트 선택
    scripts = templates.get(category_key, [])
    
    if not scripts:
        st.warning("해당 카테고리에 스크립트가 없습니다.")
        return
    
    st.markdown("---")
    st.subheader("2️⃣ 상황 선택")
    
    # 세그먼트 목록 생성
    segment_options = {i: script["세그먼트"] for i, script in enumerate(scripts)}
    
    selected_idx = st.selectbox(
        "구체적인 상황을 선택하세요",
        options=list(segment_options.keys()),
        format_func=lambda x: segment_options[x],
        key="segment_select"
    )
    
    selected_script = scripts[selected_idx]
    
    # 3단계: 스크립트 표시
    st.markdown("---")
    st.subheader("💬 추천 스크립트")
    
    st.success(selected_script["스크립트"])
    
    # 4단계: 비언어적 코칭
    st.markdown("---")
    st.subheader("🎭 비언어적 코칭")
    
    coaching_lines = selected_script["비언어적코칭"].split(". ")
    for line in coaching_lines:
        if line.strip():
            st.markdown(f"• {line.strip()}")
    
    # 5단계: TTS 음성 재생
    st.markdown("---")
    st.subheader("🎵 샘플 음성 듣기")
    
    voices = {
        "활기찬 여성 (Sun-Hi)": "ko-KR-SunHiNeural",
        "부드러운 남성 (Hyunsu)": "ko-KR-HyunsuNeural"
    }
    
    st.info("💡 **음성 선택 가이드**: Sun-Hi는 20-30대/MNP/S26 가망 고객에게, Hyunsu는 전 연령층/VIP/학부모 고객에게 추천합니다.")
    
    cols = st.columns(2)
    
    for idx, (name, voice_id) in enumerate(voices.items()):
        with cols[idx]:
            if st.button(f"▶️ {name}", key=f"{category_key}_{selected_idx}_{voice_id}"):
                with st.spinner(f"{name} 음성 생성 중..."):
                    audio_bytes = generate_tts_subprocess(selected_script["스크립트"], voice_id)
                    
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                        st.success(f"✅ 재생 완료!")