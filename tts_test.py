import streamlit as st
import subprocess
import os
import hashlib

st.set_page_config(page_title="🎵 Edge TTS 테스트", page_icon="🎵")

st.title("🎵 Edge TTS 한국어 음성 테스트")
st.markdown("---")

# 한국어 음성 2개 (작동 확인됨)
voices = {
    "활기찬 여성 (Sun-Hi)": "ko-KR-SunHiNeural",
    "부드러운 남성 (Hyunsu)": "ko-KR-HyunsuNeural"
}

# 테스트용 텍스트
default_text = """안녕하세요, 고객님! SK텔레콤 인천 마케팅팀입니다. 

현재 고객님께서 사용 중이신 LG유플러스에서 SK텔레콤으로 번호이동 하시면, 최대 50만원의 추가 혜택을 받으실 수 있습니다.

특히 이번 달은 갤럭시 S26 사전예약 기간으로, 약정 가입 시 단말기 할인까지 받으실 수 있어 정말 좋은 기회입니다."""

test_text = st.text_area(
    "🎤 테스트할 스크립트 입력",
    default_text,
    height=150
)

st.markdown("---")
st.subheader("🔊 음성 선택 & 재생")

# TTS 생성 함수 (subprocess 사용 - 순수 텍스트)
@st.cache_data(show_spinner=False)
def generate_tts_subprocess(text, voice_id):
    """Edge TTS CLI로 음성 생성 (순수 텍스트)"""
    try:
        # 텍스트 해시로 고유 파일명 생성 (캐싱용)
        text_hash = hashlib.md5((text + voice_id).encode()).hexdigest()[:8]
        temp_file = f"temp_{text_hash}.mp3"
        
        # edge-tts CLI 실행 (순수 텍스트만)
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
        st.error(f"CLI 실행 오류: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        return None

# 음성별 버튼 (2개만)
cols = st.columns(2)

for idx, (name, voice_id) in enumerate(voices.items()):
    with cols[idx]:
        st.markdown(f"**{name}**")
        if st.button(f"▶️ 재생", key=voice_id):
            with st.spinner(f"{name} 음성 생성 중..."):
                audio_bytes = generate_tts_subprocess(test_text, voice_id)
                
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
                    st.success(f"✅ 재생 완료!")
                else:
                    st.error("음성 생성 실패")

st.markdown("---")
st.info("""
💡 **2개 대표 샘플 음성**

- **Sun-Hi (활기찬 여성)**: 20-30대 고객, MNP, S26 가망  
- **Hyunsu (부드러운 남성)**: 전 연령층, VIP, 학부모
""")