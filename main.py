import re
from collections import Counter
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="급식 규칙 찾기", layout="wide")

URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_process_data():
    # 데이터 불러오기 (UTF-8 인코딩)
    df = pd.read_csv(URL, encoding="utf-8")

    transactions = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        if not isinstance(raw_menu, str):
            continue
        items = raw_menu.split("|")
        cleaned_items = set()
        for item in items:
            # 괄호 및 괄호 안 내용 제거
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)
        if cleaned_items:
            transactions.append(cleaned_items)

    total_days = len(transactions)

    # 항목별 등장 횟수 및 쌍 동시 등장 횟수 카운트
    item_counts = Counter()
    pair_counts = Counter()

    for tx in transactions:
        for item in tx:
            item_counts[item] += 1
        for pair in combinations(sorted(tx), 2):
            pair_counts[pair] += 1

    # 연관 규칙 생성
    rules_data = []

    for (item_a, item_b), count_ab in pair_counts.items():
        # 지지도 = P(A ∩ B)
        support = count_ab / total_days

        # A -> B
        conf_a_b = count_ab / item_counts[item_a]
        lift_a_b = conf_a_b / (item_counts[item_b] / total_days)

        rules_data.append(
            {
                "조건": item_a,
                "결과": item_b,
                "동시": count_ab,
                "지지도": round(support, 4),
                "신뢰도": round(conf_a_b, 4),
                "향상도": round(lift_a_b, 4),
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
                "지지도": round(support, 4),
                "신뢰도": round(conf_b_a, 4),
                "향상도": round(lift_b_a, 4),
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


# 1. 데이터 로드
try:
    rules_df, total_days, num_items, num_pairs, item_list = load_and_process_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 2. 타이틀 및 요약 정보
st.title("🍽️ 송탄고 급식 메뉴 연관 규칙 찾기")

st.markdown(
    f"**급식 일수:** {total_days}일 &nbsp;|&nbsp; "
    f"**메뉴 종류 수:** {num_items}개 &nbsp;|&nbsp; "
    f"**함께 나온 적이 있는 메뉴 쌍의 수:** {num_pairs}쌍"
)

# 3. 사이드바 필터
st.sidebar.header("필터 및 정렬 옵션")

selected_item = st.sidebar.selectbox(
    "메뉴 선택 (조건/결과에 포함된 규칙):", ["전체"] + item_list
)

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

# 4. 필터링 및 정렬
filtered_df = rules_df.copy()
if selected_item != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_item)
        | (filtered_df["결과"] == selected_item)
    ]

filtered_df = filtered_df.sort_values(by=sort_col, ascending=False).reset_index(
    drop=True
)

# 5. Plotly 가로 막대그래프 (상위 10개)
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
        text="향상도",
        title=f"향상도 TOP 10 ({'전체' if selected_item == '전체' else selected_item})",
    )
    fig.update_layout(yaxis_title="규칙 (조건 ➔ 결과)", xaxis_title="향상도")
    st.plotly_chart(fig, use_container_width=True)
else:
