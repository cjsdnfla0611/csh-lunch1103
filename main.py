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
    df = pd.read_csv(URL, encoding="utf-8")

    transactions = []
    all_items = set()

    # 데이터 전처리: 괄호 제거 및 메뉴 세로줄(|) 분리
    for raw_menu in df["메뉴"].dropna():
        if not isinstance(raw_menu, str):
            continue
        items = raw_menu.split("|")
        cleaned_items = set()
        for item in items:
            cleaned = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned:
                cleaned_items.add(cleaned)
                all_items.add(cleaned)
        if cleaned_items:
            transactions.append(cleaned_items)

    total_days = len(transactions)

    # 1. 단일 항목 발생 빈도 (Count(A))
    item_counts = Counter()
    # 2. 동시 발생 항목 쌍 빈도 (Count(A, B))
    pair_counts = Counter()

    for tx in transactions:
        for item in tx:
            item_counts[item] += 1
        for pair in combinations(sorted(tx), 2):
            pair_counts[pair] += 1

    # 연관 규칙 생성
    rules_data = []

    for (item_a, item_b), count_ab in pair_counts.items():
        # 지지도 (Support) = Count(A, B) / N
        support = count_ab / total_days

        # A -> B 규칙
        # 신뢰도 (Confidence A->B) = Count(A, B) / Count(A)
        conf_a_b = count_ab / item_counts[item_a]
        # 향상도 (Lift A->B) = Confidence(A->B) / Support(B)
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

        # B -> A 규칙
        # 신뢰도 (Confidence B->A) = Count(A, B) / Count(B)
        conf_b_a = count_ab / item_counts[item_b]
        # 향상도 (Lift B->A) = Confidence(B->A) / Support(A)
