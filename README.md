# 🌱 TM SEED
**Script Evaluation & Education Development**

TM(텔레마케팅) 통화 녹음을 AI로 자동 분석하고 코칭을 제공하는 Streamlit 웹앱

> 🌱 **SEED의 의미**: 신입 TM이 우수 TM으로 성장하도록 돕는 씨앗

## 🎯 주요 기능

- ✅ 오디오 파일 업로드 (mp3, wav, m4a 등)
- ✅ Google Gemini AI 자동 분석
- ✅ 통화 품질 점수 (0-100점)
- ✅ 말투, 억양 분석
- ✅ 강점 및 개선점 피드백
- ✅ 추천 스크립트 제공
- ✅ Google Sheets 자동 저장

## 🚀 설치 방법

### 1. 패키지 설치
```bash
cd TM_SEED
pip install -r requirements.txt
```

### 2. secrets.toml 설정

`.streamlit/secrets.toml` 파일을 열고 다음 정보를 입력하세요:

#### ① Google AI Studio API 키
1. https://aistudio.google.com/apikey 접속
2. API 키 생성 또는 기존 키 복사
3. `api_key = "여기에_붙여넣기"`

#### ② Google Sheets URL
```toml
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

#### ③ Google Cloud Service Account (선택사항)
Google Sheets 자동 저장 기능을 사용하려면:

1. https://console.cloud.google.com/ 접속
2. 새 프로젝트 생성
3. Google Sheets API 활성화
4. 서비스 계정 생성
5. JSON 키 다운로드
6. JSON 내용을 `secrets.toml`의 `[gcp_service_account]` 섹션에 복사

**간단한 방법**: 
- 일단 Gemini 분석만 사용하고 싶다면 Google Sheets 연동은 나중에 설정해도 됩니다!
- 분석 결과를 화면에서 복사해서 수동으로 저장할 수 있습니다.

## 🏃 실행 방법

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 앱이 실행됩니다.

## 📱 사용 방법

1. **파일 업로드**: 통화 녹음 파일 드래그 앤 드롭
2. **오디오 확인**: 업로드된 파일 재생
3. **분석 시작**: "통화 분석 시작" 버튼 클릭
4. **결과 확인**: 30-60초 후 상세 분석 결과 표시
5. **저장**: "Google Sheets에 저장" 버튼으로 데이터베이스 저장

## 🔧 기술 스택

- **Frontend**: Streamlit
- **AI Model**: Google Gemini 2.0 Flash Exp
- **Database**: Google Sheets
- **Language**: Python 3.9+

## 💰 비용 정보

### 무료 사용 (테스트/개발)
- Google AI Studio: 일일 15-60개 요청 무료
- Google Sheets: 무료

### 유료 사용 (운영)
- Gemini API: 1건당 약 7원
- 월 1,000건 처리 시: 약 7,000원

## 📊 분석 결과 예시

```json
{
  "통화결과": "성공",
  "점수": 92,
  "말투분석": {
    "속도": "적당",
    "톤": "친근함",
    "명확성": "명확함"
  },
  "강점": [
    "고객 니즈를 빠르게 파악함",
    "자연스러운 대화 진행"
  ],
  "개선점": [
    "상품 설명 시 구체적인 수치 제시 필요"
  ]
}
```

## 🐛 문제 해결

### Gemini API 오류
- API 키가 올바른지 확인
- 무료 할당량이 남아있는지 확인

### Google Sheets 연결 오류
- Service Account JSON 키가 올바른지 확인
- Sheets API가 활성화되어 있는지 확인
- 서비스 계정에 시트 편집 권한이 있는지 확인

### 오디오 분석 실패
- 파일 형식이 지원되는지 확인 (mp3, wav, m4a)
- 파일 크기가 너무 크지 않은지 확인 (최대 20MB 권장)

## 📝 다음 단계 (Phase 2-4)

- [ ] Phase 2: 유사 케이스 검색 기능
- [ ] Phase 3: 임베딩 기반 우수 사례 추천
- [ ] Phase 4: Streamlit Cloud 배포

## 👤 개발자

Alice - SK Telecom 인천마케팅팀

## 📅 프로젝트 날짜

2026-01-27 시작
