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
