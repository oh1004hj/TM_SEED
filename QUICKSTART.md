# 🌱 TM SEED - 5분 안에 시작하기

**Script Evaluation & Education Development**

## Step 1: 패키지 설치 (1분)

터미널에서 프로젝트 폴더로 이동 후:

```bash
cd TM_SEED
pip install -r requirements.txt
```

## Step 2: API 키 설정 (2분)

### ✅ 최소 설정 (Gemini만 사용)

`.streamlit/secrets.toml` 파일을 열고:

```toml
[google]
api_key = "여기에_Alice의_API_키_붙여넣기"
sheet_url = "임시로_비워두어도_됨"

# 아래는 Google Sheets 연동 시 필요 (일단 주석 처리)
# [gcp_service_account]
# ...
```

**Alice의 API 키 위치**: 
- Google AI Studio에서 이미 발급받으신 키 (`...X_NY`로 끝나는 키)

### ⏰ 나중에 추가할 것 (Google Sheets 자동 저장)

Google Sheets에 자동 저장하려면 Service Account가 필요합니다.
일단은 분석 결과를 화면에서 확인하고, 필요시 수동으로 복사해도 됩니다!

## Step 3: 실행 (30초)

```bash
streamlit run app.py
```

자동으로 브라우저가 열립니다!

## Step 4: 테스트 (1분)

1. TM 샘플 녹음 파일 하나 업로드
2. "통화 분석 시작" 클릭
3. 30-60초 대기
4. 결과 확인! 🎉

## 🐛 안 되면?

### "ModuleNotFoundError"
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### "Invalid API key"
- secrets.toml의 api_key 확인
- 따옴표 안에 키가 제대로 들어갔는지 확인

### "Google Sheets 연결 실패"
- 괜찮습니다! 일단 분석 기능만 사용하세요
- 결과를 화면에서 복사해서 사용할 수 있습니다

## 📞 도움 요청

문제가 생기면 Claude에게 물어보세요:
- 에러 메시지 전체를 복사해서 붙여넣기
- 어느 단계에서 문제가 생겼는지 설명

## ✨ 성공하면

축하합니다! 🎉
이제 Phase 2 (유사 케이스 검색) 개발 준비 완료!
