"""
model.py — Market Basket Analysis: Apriori + FP-Growth (mlxtend)
"""
import pandas as pd
import pickle
import os
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from database import load_dataset

RULES_FILE  = "правила.csv"
RULES_CACHE = "rules_cache.pkl"

MIN_SUPPORT    = 0.05
MIN_CONFIDENCE = 0.3
MIN_LIFT       = 1.5

BIZ_ACTIONS = [
    lambda a, b, pct, lift: f"📦 Разместить «{b}» рядом с «{a}» — вместе в {pct}% чеков.",
    lambda a, b, pct, lift: f"🏷  Акция «{a} + {b}» — связь в {lift}x сильнее случайной.",
    lambda a, b, pct, lift: f"🖥  Показывать «{b}» в блоке «С этим покупают» при выборе «{a}».",
    lambda a, b, pct, lift: f"📊 Совместная выкладка «{a}» и «{b}» увеличит конверсию (Лифт={lift}).",
    lambda a, b, pct, lift: f"🎁 Промо-набор «{a} + {b}» — уверенность покупки {pct}%.",
]


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    """Преобразует датасет транзакций в булеву матрицу для mlxtend."""
    transactions = [
        [i.strip() for i in str(row["состав"]).split(",")]
        for _, row in df.iterrows()
    ]
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    return pd.DataFrame(te_array, columns=te.columns_)


def build_frequent_itemsets(
    df=None,
    support=None,
    algorithm: str = "apriori",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Строит частые наборы через Apriori или FP-Growth.

    Parameters
    ----------
    df         : DataFrame транзакций (если None — загружается из файла)
    support    : минимальная поддержка (float 0..1)
    algorithm  : 'apriori' | 'fpgrowth'

    Returns
    -------
    (frequent_itemsets, basket_df)
    """
    if df is None:
        df = load_dataset()

    sup = support if support is not None else MIN_SUPPORT
    basket_df = _encode(df)

    if algorithm.lower() == "fpgrowth":
        frequent = fpgrowth(basket_df, min_support=sup, use_colnames=True)
    else:
        frequent = apriori(basket_df, min_support=sup, use_colnames=True)

    frequent["длина"] = frequent["itemsets"].apply(len)
    return frequent, basket_df


def build_rules(
    df=None,
    support=None,
    confidence=None,
    algorithm: str = "apriori",
    use_cache: bool = False,
) -> pd.DataFrame:
    """
    Строит ассоциативные правила.

    Parameters
    ----------
    df         : DataFrame транзакций
    support    : минимальная поддержка
    confidence : минимальная уверенность
    algorithm  : 'apriori' | 'fpgrowth'
    use_cache  : загрузить из кэша если есть

    Returns
    -------
    DataFrame правил, отсортированных по Lift убыванию
    """
    if use_cache and os.path.exists(RULES_CACHE):
        with open(RULES_CACHE, "rb") as f:
            return pickle.load(f)

    sup  = support    if support    is not None else MIN_SUPPORT
    conf = confidence if confidence is not None else MIN_CONFIDENCE

    frequent, _ = build_frequent_itemsets(df, support=sup, algorithm=algorithm)

    if frequent.empty:
        return pd.DataFrame()

    rules = association_rules(frequent, metric="lift", min_threshold=MIN_LIFT)
    rules = rules[rules["confidence"] >= conf]
    rules = rules.sort_values("lift", ascending=False).reset_index(drop=True)
    rules["antecedents_str"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents_str"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))
    return rules


def cache_rules(rules: pd.DataFrame):
    """Сохраняет правила в pickle-кэш."""
    with open(RULES_CACHE, "wb") as f:
        pickle.dump(rules, f)
    print(f"   💾 Кэш правил сохранён → {RULES_CACHE}")


def build_rules_by_store(store: str, df=None) -> tuple:
    """Правила только по одному магазину."""
    if df is None:
        df = load_dataset()
    df_store = df[df["магазин"].str.lower() == store.lower()]
    if len(df_store) < 50:
        return None, f"Недостаточно данных для «{store}» ({len(df_store)} чеков)"
    try:
        return build_rules(df_store), None
    except Exception as e:
        return None, str(e)


def build_rules_by_year_range(df: pd.DataFrame, year_from: int, year_to: int) -> tuple:
    """Правила за диапазон лет."""
    df_f = df[(df["год"] >= year_from) & (df["год"] <= year_to)]
    if len(df_f) < 50:
        return None, f"Недостаточно данных за {year_from}–{year_to} ({len(df_f)} чеков)"
    try:
        return build_rules(df_f), None
    except Exception as e:
        return None, str(e)


def save_rules(rules: pd.DataFrame) -> str:
    """Сохраняет правила в CSV."""
    if rules is None or rules.empty:
        return RULES_FILE
    export = rules[["antecedents_str", "consequents_str", "support", "confidence", "lift"]].copy()
    export.columns = ["Если куплено", "То купят", "Поддержка", "Уверенность", "Лифт"]
    for col in ["Поддержка", "Уверенность", "Лифт"]:
        export[col] = export[col].round(4)
    export.to_csv(RULES_FILE, index=False, encoding="utf-8-sig")
    print(f"   💾 Правила сохранены → {RULES_FILE}")
    return RULES_FILE


def export_rules_excel(rules: pd.DataFrame, filename: str = "правила.xlsx") -> str:
    """Экспортирует правила в Excel с форматированием."""
    export = rules[["antecedents_str", "consequents_str", "support", "confidence", "lift"]].copy()
    export.columns = ["Если куплено", "То купят", "Поддержка", "Уверенность", "Лифт"]
    for col in ["Поддержка", "Уверенность", "Лифт"]:
        export[col] = export[col].round(4)

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Правила")
        ws = writer.sheets["Правила"]
        for i, col in enumerate(export.columns, 1):
            ws.column_dimensions[chr(64 + i)].width = max(len(col) + 4, 22)

    print(f"   💾 Excel экспорт → {filename}")
    return filename


def recommend(rules: pd.DataFrame, items, top_n: int = 5) -> pd.DataFrame:
    """
    Рекомендации по одному или нескольким товарам.

    Parameters
    ----------
    rules  : DataFrame правил (из build_rules)
    items  : str или list[str] — входные товары
    top_n  : сколько рекомендаций вернуть

    Returns
    -------
    DataFrame с колонками: Товар, Уверенность, Лифт, Поддержка
    """
    if rules is None or rules.empty:
        return pd.DataFrame()

    if isinstance(items, str):
        items = [items]
    items = [i.strip() for i in items if i.strip()]

    # Точное совпадение: все входные товары есть в antecedents
    mask = rules["antecedents"].apply(lambda x: all(i in x for i in items))
    filtered = rules[mask].copy()

    # Fallback: если нет точного — ищем по первому товару
    if filtered.empty and len(items) > 1:
        mask = rules["antecedents"].apply(lambda x: items[0] in x)
        filtered = rules[mask].copy()

    if filtered.empty:
        return pd.DataFrame()

    recs = []
    seen = set()
    for _, row in filtered.iterrows():
        for c in sorted(row["consequents"]):
            if c not in items and c not in seen:
                seen.add(c)
                recs.append({
                    "Товар":       c,
                    "Уверенность": round(row["confidence"], 4),
                    "Лифт":        round(row["lift"], 4),
                    "Поддержка":   round(row["support"], 4),
                })
        if len(recs) >= top_n:
            break

    return pd.DataFrame(recs[:top_n])


def get_top_rules(rules: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Топ-N правил по Lift."""
    if rules is None or rules.empty:
        return pd.DataFrame()
    top = rules.head(n)[["antecedents_str", "consequents_str", "support", "confidence", "lift"]].copy()
    top.columns = ["Если куплено", "То купят", "Поддержка", "Уверенность", "Лифт"]
    for col in ["Поддержка", "Уверенность", "Лифт"]:
        top[col] = top[col].round(4)
    return top


def get_business_recommendations(rules: pd.DataFrame, top_n: int = 5) -> list[str]:
    """Генерирует текстовые бизнес-рекомендации по топ правилам."""
    if rules is None or rules.empty:
        return ["Нет правил для анализа."]
    top = rules.head(top_n)
    recs = []
    for i, (_, row) in enumerate(top.iterrows()):
        a    = row["antecedents_str"]
        b    = row["consequents_str"]
        lift = round(row["lift"], 2)
        pct  = round(row["confidence"] * 100, 1)
        recs.append(BIZ_ACTIONS[i % len(BIZ_ACTIONS)](a, b, pct, lift))
    return recs


SEASONS = {
    "Зима":  [12, 1, 2],
    "Весна": [3, 4, 5],
    "Лето":  [6, 7, 8],
    "Осень": [9, 10, 11],
}


def compare_algorithms(df=None, support=None, confidence=None) -> list:
    """
    Запускает Apriori и FP-Growth с одинаковыми параметрами, замеряет время.
    Сохраняет результат в comparison_results.csv.
    """
    import time
    if df is None:
        df = load_dataset()
    sup  = support    if support    is not None else MIN_SUPPORT
    conf = confidence if confidence is not None else MIN_CONFIDENCE

    results = []
    for algo in ("apriori", "fpgrowth"):
        t0      = time.perf_counter()
        rules   = build_rules(df, support=sup, confidence=conf, algorithm=algo)
        elapsed = time.perf_counter() - t0
        results.append({
            "algorithm":      algo.upper(),
            "time_sec":       round(elapsed, 4),
            "rules_count":    len(rules),
            "max_lift":       round(float(rules["lift"].max()), 4) if not rules.empty else 0.0,
            "max_confidence": round(float(rules["confidence"].max()), 4) if not rules.empty else 0.0,
        })

    pd.DataFrame(results).to_csv("comparison_results.csv", index=False, encoding="utf-8-sig")
    return results


def build_rules_by_season(df: pd.DataFrame) -> dict:
    """Строит топ-3 правила для каждого из 4 сезонов."""
    result = {}
    for season, months in SEASONS.items():
        df_s = df[df["месяц"].isin(months)]
        if len(df_s) < 50:
            print(f"   ⚠️ {season}: недостаточно данных ({len(df_s)} чеков), пропускаю")
            continue
        try:
            r = build_rules(df_s)
            if not r.empty:
                result[season] = get_top_rules(r, n=3)
            else:
                print(f"   ⚠️ {season}: правила не найдены")
        except Exception as e:
            print(f"   ⚠️ {season}: ошибка — {e}")
    return result
