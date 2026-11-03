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

        # 각 메뉴의 단독 지지도
        supp_a = item_counts[item_a] / total_days
        supp_b = item_counts[item_b] / total_days

        # A -> B 규칙 계산
        conf_a_b = count_ab / item_counts[item_a]
        lift_a_b = conf_a_b / supp_b

        rules_data.append({
            "조건": item_a,
            "결과": item_b,
            "동시": count_ab,
            "지지도": round(support, 4),
            "신뢰도": round(conf_a_b, 4),
            "향상도": round(lift_a_b, 4),
        })

        # B -> A 규칙 계산
        conf_b_a = count_ab / item_counts[item_b]
        lift_b_a = conf_b_a / supp_a

        rules_data.append({
            "조건": item_b,
            "결과": item_a,
            "동시": count_ab,
            "지지도": round(support, 4),
            "신뢰도": round(conf_b_a, 4),
            "향상도": round(lift_b_a, 4),
        })

    rules_df = pd.DataFrame(rules_data)
    unique_pairs_count = len(pair_counts)

    return (
        rules_df,
        total_days,
        len(all_items),
        unique_pairs_count,
        sorted(list(all_items)),
        item_counts,
        pair_counts,
    )


# 1. 데이터 로드
try:
    (
        rules_df,
        total_days,
        num_items,
        num_pairs,
        item_list,
        item_counts,
        pair_counts,
    ) = load_and_process_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 2. 타이틀 및 요약 정보 (한 줄로 표시)
st.title("🍽️ 송탄고 급식 메뉴 연관 규칙 찾기")

st.markdown(
    f"**급식 일수:** {total_days}일 &nbsp;|&nbsp; "
    f"**메뉴 종류 수:** {num_items}개 &nbsp;|&nbsp; "
    f"**함께 나온 적이 있는 메뉴 쌍의 수:** {num_pairs}쌍"
)

# 3. 사이드바 필터 및 검색 옵션
st.sidebar.header("🔍 필터 및 검색 옵션")

# 텍스트 검색창
search_query = st.sidebar.text_input("메뉴 이름 직접 검색:", placeholder="예: 김치, 닭갈비").strip()

# 드롭다운 선택 필터
selected_item = st.sidebar.selectbox("메뉴 목록에서 선택:", ["전체"] + item_list)

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

# 최소 동시 일수 슬라이더 (1~10, 기본값 1)
min_cooccur = st.sidebar.slider(
    "최소 동시 일수:",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
)

# 4. 데이터 필터링
filtered_df = rules_df.copy()

# 최소 동시 일수 조건 적용
filtered_df = filtered_df[filtered_df["동시"] >= min_cooccur]

# 메뉴 검색/선택 필터 적용
if search_query:
    filtered_df = filtered_df[
        (filtered_df["조건"].str.contains(search_query, case=False, na=False))
        | (filtered_df["결과"].str.contains(search_query, case=False, na=False))
    ]
elif selected_item != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_item)
        | (filtered_df["결과"] == selected_item)
    ]

# 정렬 적용
filtered_df = filtered_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)

filter_title = search_query if search_query else selected_item

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
        title=f"향상도 TOP 10 ({filter_title} / 최소 동시 {min_cooccur}일 이상)",
    )
    fig.update_layout(yaxis_title="규칙 (조건 ➔ 결과)", xaxis_title="향상도")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("조건 또는 검색어에 해당하는 규칙이 없습니다.")

# 6. 연관 규칙 목록 표 출력
st.subheader("📋 연관 규칙 목록")

# 필터링 후 남아있는 규칙 수 표시 (한 줄)
st.markdown(f"**현재 조건에 부합하는 규칙 수:** 총 **{len(filtered_df)}**개")

st.dataframe(filtered_df, use_container_width=True)

st.divider()

# 7. 함께 나온 적 없는 짝 화면
st.subheader("🚫 함께 나온 적 없는 짝 찾기")

unpaired_target_item = st.selectbox(
    "조회할 메뉴를 선택해 주세요 (위의 좁혀 보기와 별도):",
    item_list,
    key="unpaired_item_select",
)

target_item_days = item_counts[unpaired_target_item]

# 함께 나온 적 없는 메뉴 탐색 (동시 등장 횟수가 0이고, 혼자서는 10일 이상 나온 메뉴)
unpaired_list = []
for other_item in item_list:
    if other_item == unpaired_target_item:
        continue

    # 두 항목의 pair 키 생성
    pair_key = tuple(sorted([unpaired_target_item, other_item]))

    # 한번도 같이 나온 적 없음 (pair_counts에 없음) & 상대 메뉴 등장 횟수 >= 10
    if pair_counts[pair_key] == 0 and item_counts[other_item] >= 10:
        unpaired_list.append({
            "메뉴": other_item,
            "나온 날 수": item_counts[other_item],
        })

unpaired_df = pd.DataFrame(unpaired_list)

st.write(f"선택한 메뉴 **'{unpaired_target_item}'**이(가) 나온 날 수: **{target_item_days}일**")

if not unpaired_df.empty:
    # 나온 날 수 기준 내림차순 정렬
    unpaired_df = unpaired_df.sort_values(by="나온 날 수", ascending=False).reset_index(drop=True)
    st.dataframe(unpaired_df, use_container_width=True)
else:
    st.info(f"혼자 10일 이상 나오면서 '{unpaired_target_item}'와 한 번도 함께 나오지 않은 메뉴가 없습니다.")
