"""
predict.py — сохранение истории рекомендаций
"""
import pandas as pd
import os
from datetime import datetime

HISTORY_FILE = "история_рекомендаций.csv"
COLUMNS      = ["дата_запроса", "товар", "рекомендован", "уверенность", "лифт"]


def init_history():
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=COLUMNS).to_csv(
            HISTORY_FILE, index=False, encoding="utf-8-sig"
        )


def save_recommendation(query_item: str, recommendations: pd.DataFrame):
    """Добавляет записи в историю рекомендаций."""
    if recommendations is None or recommendations.empty:
        return
    init_history()
    df = pd.read_csv(HISTORY_FILE)
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for _, row in recommendations.iterrows():
        rows.append({
            "дата_запроса": ts,
            "товар":        query_item,
            "рекомендован": row["Товар"],
            "уверенность":  round(float(row["Уверенность"]), 4),
            "лифт":         round(float(row["Лифт"]), 4),
        })
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")


def load_history(n: int = 30) -> pd.DataFrame:
    """Загружает последние n записей истории."""
    init_history()
    df = pd.read_csv(HISTORY_FILE)
    # Защита от NaN в числовых колонках
    df["уверенность"] = pd.to_numeric(df["уверенность"], errors="coerce").fillna(0.0)
    df["лифт"]        = pd.to_numeric(df["лифт"],        errors="coerce").fillna(0.0)
    return df.tail(n)


def clear_history():
    """Очищает историю рекомендаций."""
    pd.DataFrame(columns=COLUMNS).to_csv(
        HISTORY_FILE, index=False, encoding="utf-8-sig"
    )
