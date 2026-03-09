"""
TM SEED 대시보드 모듈 (개선 버전)
- 분석결과 시트: 통화분석 데이터
- 스크립트생성이력 시트: 스크립트 타입별 데이터
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter

# ============================================================
# 데이터 로드 함수
# ============================================================

def load_script_history(sheets_client, sheet_url):
    """
    스크립트생성이력 시트 로드
    
    Args:
        sheets_client: gspread 클라이언트
        sheet_url: 구글 시트 URL
        
    Returns:
        DataFrame: 스크립트 생성 이력 데이터
    """
    try:
        spreadsheet = sheets_client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("스크립트생성이력")
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # 생성일자 컬럼 변환 (스크립트생성이력은 '생성일자' 컬럼 사용)
        if '생성일자' not in df.columns:
            date_cols = [c for c in df.columns if '일자' in c or '일시' in c or '날짜' in c]
            if date_cols:
                df = df.rename(columns={date_cols[0]: '생성일자'})
        if '생성일자' in df.columns:
            df['생성일자'] = pd.to_datetime(df['생성일자'], errors='coerce').dt.date
        
        # 매장코드를 4자리 문자열로 변환 (0000 본점 포함)
        if '매장코드' in df.columns:
            df['매장코드'] = df['매장코드'].apply(
                lambda x: str(x).zfill(4) if pd.notna(x) and str(x).strip() else '0000'
            )
        
        # 대리점코드도 문자열로 변환
        if '대리점코드' in df.columns:
            df['대리점코드'] = df['대리점코드'].astype(str)
        
        return df
        
    except Exception as e:
        print(f"스크립트생성이력 로드 실패: {str(e)}")
        return pd.DataFrame()


def load_analysis_results(sheets_client, sheet_url):
    """
    분석결과 시트 로드 (통화분석 데이터)
    
    Args:
        sheets_client: gspread 클라이언트
        sheet_url: 구글 시트 URL
        
    Returns:
        DataFrame: 통화 분석 결과 데이터
    """
    try:
        spreadsheet = sheets_client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("분석결과")
        data = worksheet.get_all_records()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # 분석일자 컬럼 변환
        if '분석일자' in df.columns:
            df['분석일자'] = pd.to_datetime(df['분석일자'], errors='coerce')
        
        # 통화결과 공백 제거
        if '통화결과' in df.columns:
            df['통화결과'] = df['통화결과'].astype(str).str.strip()

        # 종합점수를 숫자로 변환
        if '종합점수' in df.columns:
            df['종합점수'] = pd.to_numeric(df['종합점수'], errors='coerce')
        
        # 매장코드를 4자리 문자열로 변환
        if '매장코드' in df.columns:
            df['매장코드'] = df['매장코드'].apply(
                lambda x: str(x).zfill(4) if pd.notna(x) and str(x).strip() else '0000'
            )
        
        return df
        
    except Exception as e:
        print(f"분석결과 로드 실패: {str(e)}")
        return pd.DataFrame()


# ============================================================
# D) 스크립트 타입별 분포 (최우선)
# ============================================================

def get_script_type_stats(df):
    """
    스크립트 타입별 통계
    
    Args:
        script_df: 스크립트생성이력 DataFrame
        
    Returns:
        DataFrame: 타입별 건수
    """
    if df.empty or '스크립트 타입' not in df.columns:
        return pd.DataFrame()
    
    type_stats = df['스크립트 타입'].value_counts().reset_index()
    type_stats.columns = ['타입', '건수']
    
    # 비율 계산
    total = type_stats['건수'].sum()
    type_stats['비율'] = (type_stats['건수'] / total * 100).round(1)
    
    return type_stats


# ============================================================
# B) 통화분석 성과
# ============================================================

def get_call_analysis_stats(analysis_df):
    """
    통화분석 성과 통계
    
    Args:
        analysis_df: 분석결과 DataFrame
        
    Returns:
        dict: 통화분석 성과 통계
    """
    if analysis_df.empty:
        return {
            'total_count': 0,
            'avg_score': 0,
            'excellent_count': 0,
            'success_rate': 0,
            'result_distribution': pd.DataFrame()
        }
    
    total = len(analysis_df)
    
    # 평균 점수
    avg_score = analysis_df['종합점수'].mean() if '종합점수' in analysis_df.columns else 0
    
    # 우수사례 (80점 이상)
    excellent_count = len(analysis_df[analysis_df['종합점수'] >= 80]) if '종합점수' in analysis_df.columns else 0
    
    # 통화결과별 분포
    result_dist = pd.DataFrame()
    if '통화결과' in analysis_df.columns:
        result_dist = analysis_df['통화결과'].value_counts().reset_index()
        result_dist.columns = ['통화결과', '건수']
        result_dist['비율'] = (result_dist['건수'] / total * 100).round(1)
    
    # 성공률 (통화결과가 '성공'인 경우)
    success_count = len(analysis_df[analysis_df['통화결과'] == '성공']) if '통화결과' in analysis_df.columns else 0
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    return {
        'total_count': total,
        'avg_score': round(avg_score, 1),
        'excellent_count': excellent_count,
        'success_rate': round(success_rate, 1),
        'result_distribution': result_dist
    }


# ============================================================
# C) T크루별 활동 순위
# ============================================================

def get_tcrew_ranking(script_df, analysis_df, top_n=10):
    """
    T크루별 활동 순위 (스크립트 생성 + 통화분석 합산)
    
    Args:
        script_df: 스크립트생성이력 DataFrame
        analysis_df: 분석결과 DataFrame
        top_n: 상위 N명
        
    Returns:
        DataFrame: T크루별 활동 통계
    """
    # 스크립트 생성 건수
    script_count = pd.DataFrame()
    if not script_df.empty and 'T크루ID' in script_df.columns:
        script_count = script_df.groupby(['T크루ID', '이름']).size().reset_index()
        script_count.columns = ['T크루ID', '이름', '스크립트']
    
    # 통화분석 건수
    analysis_count = pd.DataFrame()
    if not analysis_df.empty and 'T크루ID' in analysis_df.columns:
        analysis_count = analysis_df.groupby(['T크루ID', '이름']).size().reset_index()
        analysis_count.columns = ['T크루ID', '이름', '통화분석']
    
    # 합치기
    if script_count.empty and analysis_count.empty:
        return pd.DataFrame()
    
    if script_count.empty:
        result = analysis_count.copy()
        result['스크립트'] = 0
        result['총건수'] = result['통화분석']
    elif analysis_count.empty:
        result = script_count.copy()
        result['통화분석'] = 0
        result['총건수'] = result['스크립트']
    else:
        result = pd.merge(script_count, analysis_count, on=['T크루ID', '이름'], how='outer').fillna(0)
        result['총건수'] = result['스크립트'] + result['통화분석']
    
    # 정수로 변환
    result['스크립트'] = result['스크립트'].astype(int)
    result['통화분석'] = result['통화분석'].astype(int)
    result['총건수'] = result['총건수'].astype(int)
    
    # 정렬
    result = result.sort_values('총건수', ascending=False).head(top_n)
    
    return result


# ============================================================
# A) 날짜별 추이
# ============================================================

def get_daily_trend(script_df, analysis_df, days=7):
    """
    날짜별 활동 추이 - 스크립트/통화분석 분리 반환
    
    Args:
        script_df: 스크립트생성이력 DataFrame
        analysis_df: 분석결과 DataFrame
        days: 최근 N일
        
    Returns:
        tuple: (script_daily_df, analysis_daily_df)
               script_daily_df  - 컬럼: ['날짜', '스크립트타입별...', '합계']
               analysis_daily_df - 컬럼: ['날짜', '성공', '보류', '거절', '합계']
    """
    # ── 스크립트 생성 추이 (타입별) ──────────────────────────
    script_daily = pd.DataFrame()
    if not script_df.empty and '생성일자' in script_df.columns:
        recent = script_df.copy()
        recent['날짜'] = pd.to_datetime(recent['생성일자']).dt.strftime('%Y-%m-%d')
        recent = recent[recent['날짜'].str.match(r'\d{4}-\d{2}-\d{2}')]

        type_col = next((c for c in recent.columns if '타입' in c), None)
        if type_col:
            pivot = recent.groupby(['날짜', type_col]).size().unstack(fill_value=0)
            pivot.columns.name = None
            type_only_cols = list(pivot.columns)
            pivot['합계'] = pivot[type_only_cols].sum(axis=1)
            script_daily = pivot.reset_index()
        else:
            script_daily = recent.groupby('날짜').size().reset_index()
            script_daily.columns = ['날짜', '합계']

        script_daily = script_daily.sort_values('날짜').reset_index(drop=True)
        print("=== script_daily 확인 ===")
        print(script_daily.columns.tolist())
        print(script_daily.columns.name)
        print(script_daily[['날짜','합계']].to_string())
    
    # ── 통화분석 추이 (결과별) ────────────────────────────────
    analysis_daily = pd.DataFrame()
    if not analysis_df.empty and '분석일자' in analysis_df.columns:
        recent = analysis_df.copy()
        recent['분석일자'] = pd.to_datetime(recent['분석일자'], errors='coerce')
        recent['날짜'] = recent['분석일자'].dt.strftime('%Y-%m-%d')
        
        if '통화결과' in recent.columns:
            # 결과별 피벗
            pivot = recent.groupby(['날짜', '통화결과']).size().unstack(fill_value=0)
            pivot.columns.name = None
            type_only_cols = [c for c in pivot.columns if c != '합계']
            pivot['합계'] = pivot[type_only_cols].sum(axis=1)
            analysis_daily = pivot.reset_index()
        else:
            # 결과 컬럼 없으면 전체 합계만
            analysis_daily = recent.groupby('날짜').size().reset_index()
            analysis_daily.columns = ['날짜', '합계']
        
        analysis_daily = analysis_daily.sort_values('날짜')
    
    return script_daily, analysis_daily

# ============================================================
# 기타 통계 (키워드, 매장별)
# ============================================================

def get_keyword_stats(script_df, top_n=10):
    """키워드 TOP (스크립트생성이력 기반)"""
    if script_df.empty or '키워드' not in script_df.columns:
        return pd.DataFrame()
    
    all_keywords = []
    for keywords_str in script_df['키워드'].dropna():
        if isinstance(keywords_str, str) and keywords_str.strip():
            keywords = [k.strip() for k in keywords_str.split(',')]
            all_keywords.extend(keywords)
    
    if not all_keywords:
        return pd.DataFrame()
    
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(top_n)
    
    keyword_df = pd.DataFrame(top_keywords, columns=['키워드', '건수'])
    return keyword_df


def get_store_stats(script_df, analysis_df, top_n=10):
    """대리점/매장별 활동 현황"""
    # 스크립트 생성 건수
    script_store = pd.DataFrame()
    if not script_df.empty and '매장코드' in script_df.columns:
        script_store = script_df.groupby(['대리점코드', '대리점명', '매장코드', '매장명']).size().reset_index()
        script_store.columns = ['대리점코드', '대리점명', '매장코드', '매장명', '스크립트']
    
    # 통화분석 건수
    analysis_store = pd.DataFrame()
    if not analysis_df.empty and '매장코드' in analysis_df.columns:
        analysis_store = analysis_df.groupby(['대리점코드', '대리점명', '매장코드', '매장명']).size().reset_index()
        analysis_store.columns = ['대리점코드', '대리점명', '매장코드', '매장명', '통화분석']
    
    # 합치기
    if script_store.empty and analysis_store.empty:
        return pd.DataFrame()
    
    if script_store.empty:
        result = analysis_store.copy()
        result['스크립트'] = 0
        result['총건수'] = result['통화분석']
    elif analysis_store.empty:
        result = script_store.copy()
        result['통화분석'] = 0
        result['총건수'] = result['스크립트']
    else:
        result = pd.merge(
            script_store, 
            analysis_store, 
            on=['대리점코드', '대리점명', '매장코드', '매장명'], 
            how='outer'
        ).fillna(0)
        result['총건수'] = result['스크립트'] + result['통화분석']
    
    # 정수로 변환
    result['스크립트'] = result['스크립트'].astype(int)
    result['통화분석'] = result['통화분석'].astype(int)
    result['총건수'] = result['총건수'].astype(int)
    
    # 정렬
    result = result.sort_values('총건수', ascending=False).head(top_n)
    
    return result


# ============================================================
# 날짜 필터
# ============================================================

def filter_by_date(df, date_option):
    """
    기간 선택에 따라 DataFrame 필터링

    Args:
        df: 필터링할 DataFrame (분석일자 컬럼 필요)
        date_option: "오늘" / "최근 7일" / "최근 30일" / "이번 달" / "전체"

    Returns:
        filtered_df: 필터링된 DataFrame
    """
    from datetime import date

    if df.empty or date_option == "전체":
        return df

    today = date.today()

    if date_option == "오늘":
        date_from, date_to = today, today
    elif date_option == "최근 7일":
        date_from = today - timedelta(days=6)
        date_to = today
    elif date_option == "최근 30일":
        date_from = today - timedelta(days=29)
        date_to = today
    elif date_option == "이번 달":
        date_from = today.replace(day=1)
        date_to = today
    else:
        return df

    # 날짜 컬럼 확인 (분석일자 또는 생성일자)
    date_col = None
    if "분석일자" in df.columns:
        date_col = "분석일자"
    elif "생성일자" in df.columns:
        date_col = "생성일자"
    
    if date_col is None:
        return df

    df_f = df.copy()
    df_f[date_col] = pd.to_datetime(df_f[date_col], errors="coerce")
    return df_f[
        (df_f[date_col].dt.date >= date_from) &
        (df_f[date_col].dt.date <= date_to)
    ]

# ============================================================
# JSON 파싱 - 상세점수 추출
# ============================================================

def parse_score_from_json(analysis_df):
    """
    분석결과의 상세JSON 컬럼에서 점수 항목을 파싱하여 DataFrame에 추가
    
    Returns:
        DataFrame: 점수 컬럼 추가된 df
    """
    if analysis_df.empty or '상세JSON' not in analysis_df.columns:
        return analysis_df
    
    score_keys = ['인사_및_오프닝', '니즈파악_질문', '제안_설득력', '마무리_클로징']
    speech_keys = ['톤적절성_점수', '자신감수준', '공감표현']
    
    rows = []
    for _, row in analysis_df.iterrows():
        parsed = {}
        try:
            j = json.loads(row['상세JSON']) if isinstance(row['상세JSON'], str) else {}
            점수평가 = j.get('점수평가', {})
            for k in score_keys:
                v = 점수평가.get(k, None)
                parsed[k] = int(str(v).replace('점','').strip()) if v is not None and str(v).replace('점','').strip().isdigit() else None
            말투 = j.get('말투분석', {})
            for k in speech_keys:
                v = 말투.get(k, None)
                parsed[k] = int(str(v).replace('점','').strip()) if v is not None and str(v).replace('점','').strip().isdigit() else None
        except:
            pass
        rows.append(parsed)
    
    score_df = pd.DataFrame(rows)
    # 기존 컬럼과 중복되는 점수 컬럼은 score_df 것으로 덮어쓰기
    all_score_cols = list(score_df.columns)
    base = analysis_df.reset_index(drop=True).drop(columns=[c for c in all_score_cols if c in analysis_df.columns], errors='ignore')
    result = pd.concat([base, score_df], axis=1)
    return result


def get_score_avg_by_item(analysis_df):
    """점수 항목별 평균"""
    score_keys = ['인사_및_오프닝', '니즈파악_질문', '제안_설득력', '마무리_클로징']
    
    if analysis_df.empty:
        return pd.DataFrame()
    
    df = parse_score_from_json(analysis_df)
    
    records = []
    for k in score_keys:
        if k in df.columns:
            avg = df[k].dropna().mean()
            label = k.replace('_', ' ')
            records.append({'항목': label, '평균점수': round(avg, 1) if not pd.isna(avg) else 0})
    
    return pd.DataFrame(records)


def get_score_by_result(analysis_df):
    """성공 vs 거절 항목별 Gap 반환 (Gap 큰 순 정렬)"""
    if analysis_df.empty:
        return pd.DataFrame()
    
    df = parse_score_from_json(analysis_df)
    # 점수평가 4개 + 말투분석 3개 전체
    all_keys = ['인사_및_오프닝', '니즈파악_질문', '제안_설득력', '마무리_클로징',
                '톤적절성_점수', '자신감수준', '공감표현']
    
    records = []
    success = df[df['통화결과'] == '성공'] if '통화결과' in df.columns else pd.DataFrame()
    reject  = df[df['통화결과'] == '거절'] if '통화결과' in df.columns else pd.DataFrame()
    
    for k in all_keys:
        if k in df.columns:
            s_avg = success[k].dropna().mean() if not success.empty else None
            r_avg = reject[k].dropna().mean()  if not reject.empty  else None
            if s_avg is not None and r_avg is not None and not (pd.isna(s_avg) or pd.isna(r_avg)):
                gap = round(float(s_avg) - float(r_avg), 1)
                records.append({'항목': k.replace('_', ' '), 'Gap': gap})
    
    if not records:
        return pd.DataFrame()
    
    result = pd.DataFrame(records)
    result = result.sort_values('Gap', ascending=True)  # 가로 막대용 오름차순
    return result


# ============================================================
# 인사이트 자동 생성
# ============================================================

def generate_script_insights(script_df):
    """
    스크립트생성이력 기반 인사이트 멘트 생성
    
    Returns:
        list of str
    """
    insights = []
    if script_df.empty:
        return insights
    
    # 최다 키워드
    if '키워드' in script_df.columns:
        kw_stats = get_keyword_stats(script_df, top_n=1)
        if not kw_stats.empty:
            top_kw = kw_stats.iloc[0]['키워드']
            top_cnt = kw_stats.iloc[0]['건수']
            insights.append(f"🔥 **{top_kw}** 키워드가 이번 기간 가장 많이 활용됐어요! ({top_cnt}건)")
    
    # 최다 활동 크루
    if '이름' in script_df.columns:
        crew_cnt = script_df['이름'].value_counts()
        if len(crew_cnt) > 0:
            top_crew = crew_cnt.index[0]
            top_n = crew_cnt.iloc[0]
            total = len(script_df)
            pct = round(top_n / total * 100, 1) if total > 0 else 0
            insights.append(f"🏆 **{top_crew}** 크루가 전체의 {pct}%를 차지하며 가장 활발히 활동 중이에요!")
    
    # 이번 주 vs 저번 주 비교
    if '생성일자' in script_df.columns:
        col = '생성일자'
        try:
            df_copy = script_df.copy()
            df_copy[col] = pd.to_datetime(df_copy[col].astype(str), errors='coerce')
            today = datetime.now().date()
            this_week_start = today - timedelta(days=today.weekday())
            last_week_start = this_week_start - timedelta(days=7)
            
            this_week = len(df_copy[df_copy[col].dt.date >= this_week_start])
            last_week = len(df_copy[
                (df_copy[col].dt.date >= last_week_start) &
                (df_copy[col].dt.date < this_week_start)
            ])
            
            if last_week > 0:
                change = round((this_week - last_week) / last_week * 100, 1)
                icon = "📈" if change >= 0 else "📉"
                direction = "증가" if change >= 0 else "감소"
                insights.append(f"{icon} 이번 주 활동이 지난주 대비 **{abs(change)}% {direction}** 했어요!")
        except:
            pass
    
    return insights


def generate_call_insights(analysis_df):
    """
    통화분석 기반 인사이트 멘트 생성
    
    Returns:
        list of str
    """
    insights = []
    if analysis_df.empty:
        return insights
    
    df = parse_score_from_json(analysis_df)
    
    # 가장 낮은 항목 → 집중 코칭 필요
    score_keys = ['인사_및_오프닝', '니즈파악_질문', '제안_설득력', '마무리_클로징']
    avgs = {}
    for k in score_keys:
        if k in df.columns:
            avg = df[k].dropna().mean()
            if not pd.isna(avg):
                avgs[k] = round(avg, 1)
    
    if avgs:
        worst_key = min(avgs, key=avgs.get)
        worst_val = avgs[worst_key]
        insights.append(f"⚠️ **{worst_key.replace('_', ' ')}** 항목이 팀 평균 {worst_val}점으로 가장 낮아요 → 집중 코칭이 필요해요!")
    
    # 성공 vs 거절 제안_설득력 비교
    if '통화결과' in df.columns and '제안_설득력' in df.columns:
        success = df[df['통화결과'] == '성공']['제안_설득력'].dropna()
        reject = df[df['통화결과'] == '거절']['제안_설득력'].dropna()
        if len(success) > 0 and len(reject) > 0:
            diff = round(success.mean() - reject.mean(), 1)
            if diff > 0:
                insights.append(f"🎯 성공 통화는 제안·설득력이 거절 대비 **{diff}점 높아요** — 설득 훈련이 핵심이에요!")
    
    # 친근한 목소리톤 공통 특징
    try:
        json_rows = []
        for v in df['상세JSON'].dropna():
            try:
                j = json.loads(v) if isinstance(v, str) else {}
                json_rows.append(j)
            except:
                pass
        
        if json_rows:
            success_tones = []
            for j, row in zip(json_rows, df.itertuples()):
                if j.get('통화결과') == '성공':
                    tone = j.get('말투분석', {}).get('목소리톤', '')
                    if tone:
                        success_tones.append(tone)
            
            if success_tones:
                tone_cnt = Counter(success_tones)
                top_tone = tone_cnt.most_common(1)[0][0]
                insights.append(f"✅ 성공 통화의 공통 특징은 **{top_tone}** 목소리톤이에요!")
    except:
        pass
    
    return insights


# ============================================================
# 요약 카드 데이터
# ============================================================

def get_summary_cards(script_df, analysis_df):
    """
    상단 요약 카드 4개 데이터 반환
    
    Returns:
        dict: 누적스크립트, 최다키워드, 최우수크루, 최근업데이트
    """
    # 누적 스크립트 건수
    total_scripts = len(script_df) if not script_df.empty else 0
    
    # 최다 키워드
    top_keyword = "-"
    if not script_df.empty:
        kw_stats = get_keyword_stats(script_df, top_n=1)
        if not kw_stats.empty:
            top_keyword = kw_stats.iloc[0]['키워드']
    
    # 최우수 크루 (통화분석 평균점수 기준)
    best_crew = "-"
    if not analysis_df.empty and '종합점수' in analysis_df.columns and '이름' in analysis_df.columns:
        score_by_crew = analysis_df.groupby('이름')['종합점수'].mean()
        if not score_by_crew.empty:
            best_crew = score_by_crew.idxmax()
    
    # 최근 업데이트
    latest = "-"
    dfs = []
    if not script_df.empty and '생성일자' in script_df.columns:
        dfs.append(pd.to_datetime(script_df['생성일자'].astype(str), errors='coerce').dropna())
    if not analysis_df.empty and '분석일자' in analysis_df.columns:
        dfs.append(pd.to_datetime(analysis_df['분석일자'], errors='coerce').dropna())
    if dfs:
        try:
            all_dates = pd.concat(dfs, ignore_index=True)
            all_dates = pd.to_datetime(all_dates, errors='coerce').dropna()
            if len(all_dates) > 0:
                latest = all_dates.max().strftime('%m/%d')
        except:
            pass
    
    return {
        'total_scripts': total_scripts,
        'top_keyword': top_keyword,
        'best_crew': best_crew,
        'latest_update': latest,
    }


# ============================================================
# 스크립트 상세 계층 구조
# ============================================================

def get_script_detail_tree(script_df):
    """
    스크립트 상세 아코디언용 계층 구조 데이터
    
    Returns:
        dict: {대리점명: {매장명: {크루명: [row, ...], ...}, ...}, ...}
    """
    if script_df.empty:
        return {}
    
    tree = {}
    
    for _, row in script_df.iterrows():
        agency = str(row.get('대리점명', '미분류'))
        store = str(row.get('매장명', '미분류'))
        crew = str(row.get('이름', '미분류'))
        
        if agency not in tree:
            tree[agency] = {}
        if store not in tree[agency]:
            tree[agency][store] = {}
        if crew not in tree[agency][store]:
            tree[agency][store][crew] = []
        
        tree[agency][store][crew].append(row.to_dict())
    
    return tree
