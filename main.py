import re
from collections import Counter
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="급식 규칙 찾기", layout="wide")

URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_process_data():
    # 데이터 불러오기
    df = pd.read_csv(URL, encoding="utf-8")

    transactions = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        if not isinstance(raw_menu, str):
            continue
        # 세로줄(|) 구분자로 분리
        items = raw_menu.split("|")
        cleaned_items = set()
        for item in items:
            # 괄호 및 괄호 안 내용 제거 및 공백 정리
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)
        if cleaned_items:
            transactions.append(cleaned_items)

    total_days = len(transactions)

    # 단일 항목 발생 빈도 계산
    item_counts = Counter()
    # 동시 발생 항목 쌍 빈도 계산
    pair_counts = Counter()

    for tx in transactions:
        for item in tx:
            item_counts[item] += 1
        for pair in combinations(sorted(tx), 2):
            pair_counts[pair] += 1

    # 연관 규칙 생성 (A -> B 및 B -> A)
    rules_data = []

    for (item_a, item_b), count_ab in pair_counts.items():
        support = count_ab / total_days

        # A -> B
        conf_a_b = count_ab / item_counts[item_a]
        lift_a_b = conf_a_b / (item_counts[item_b] / total_days)
        rules_data.append(
            {
                "조건": item_a,
                "결과": item_b,
                "동시": count_ab,
                "지지도": support,
                "신뢰도": conf_a_b,
                "향상도": lift_a_b,
            }
        )

        # B -> A
        conf_b_a = count_ab / item_counts[item_b]
        lift_b_a = conf_b_a / (item_counts[item_a] / total_days)
        rules_data.append(
            {
                "조건": item_b,
                "결과": item_a,
                "동시": count_ab,
                "지지도": support,
                "신뢰도": conf_b_a,
                "향상도": lift_b_a,
            }
        )

    rules_df = pd.DataFrame(rules_data)
    unique_pairs_count = len(pair_counts)

    return (
        rules_df,
        total_days,
        len(all_items),
        unique_pairs_count,
        sorted(list(all_items)),
    )


# 데이터 로드
rules_df, total_days, num_items, num_pairs, item_list = load_and_process_data()

st.title("🍽️ 송탄고 급식 메뉴 연관 규칙 찾기")

# 한 줄 요약 지표
st.write(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {num_items}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {num_pairs}쌍"
)

# 사이드바 / 필터 옵션
st.sidebar.header("필터 및 정렬 설정")

# 메뉴 선택 필터
selected_item = st.sidebar.selectbox(
    "메뉴 선택 (조건 또는 결과에 포함된 규칙 조회):", ["전체"] + item_list
)

# 정렬 기준 선택
sort_option = st.sidebar.radio(
    "정렬 기준 선택:",
    ["향상도 순", "신뢰도 순", "동시 순"],
    index=0,
)

sort_column_map = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시",
}
sort_col = sort_column_map[sort_option]

# 데이터 필터링
filtered_df = rules_df.copy()
if selected_item != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_item)
        | (filtered_df["결과"] == selected_item)
    ]

# 정렬 적용
filtered_df = filtered_df.sort_values(by=sort_col, ascending=False).reset_index(
    drop=True
)

# Plotly 가로 막대그래프 (향상도 상위 10개)
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10).copy()

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    top10_df_sorted = top10_df.sort_values(by="향상도", ascending=True)

    fig = px.bar(
        top10_df_sorted,
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10_df_sorted["향상도"].apply(lambda x: f"{x:.2f}"),
        title=f"향상도 TOP 10 ({'전체' if selected_item == '전체' else selected_item})",
    )
    fig.update_layout(yaxis_title="규칙 (조건 ➔ 결과)", xaxis_title="향상도")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("조건에 해당하는 규칙이 없습니다.")

# 규칙 표 출력
st.subheader("📋 연관 규칙 목록")
st.dataframe(
    filtered_df.style.format(
        {"지지도": "{:.4f}", "신뢰도": "{:.4f}", "향상도": "{:.4f}"}
    ),
    use_container_width=True,
)
