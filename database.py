"""
database.py — CRUD операции над датасетом транзакций
"""
import pandas as pd
import os
from datetime import datetime
from dataset import DATA_FILE, create_dataset, ITEMS, STORES
_ITEMS_SET = set(ITEMS)

RULES_CACHE = "rules_cache.pkl"


def _invalidate_cache():
    """Удаляет кэш правил при изменении данных."""
    if os.path.exists(RULES_CACHE):
        os.remove(RULES_CACHE)
        print("   🗑️  Кэш правил инвалидирован (данные изменились)")


def load_dataset():
    if not os.path.exists(DATA_FILE):
        print("⚙️  Датасет не найден, генерирую...")
        return create_dataset()
    return pd.read_csv(DATA_FILE)


def save_dataset(df):
    df.to_csv(DATA_FILE, index=False)


def validate_date(date_str: str) -> bool:
    """Проверяет корректность даты (отклоняет 31 февраля и т.д.)"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def add_transaction(date: str, store: str, items: list) -> int:
    """
    Добавляет новый чек.
    Raises ValueError если дата невалидна или товаров меньше 2.
    """
    if not validate_date(date):
        raise ValueError(f"Невалидная дата: «{date}». Формат: ГГГГ-ММ-ДД")

    items_clean = [i.strip() for i in items if i.strip()]
    if len(items_clean) < 2:
        raise ValueError(f"Минимум 2 товара в чеке, получено: {len(items_clean)}")

    for item in items_clean:
        if item not in _ITEMS_SET:
            raise ValueError(f"Неизвестный товар: «{item}». Используйте fuzzy_item() для распознавания.")

    df = load_dataset()
    new_id = int(df["ид_чека"].max()) + 1 if len(df) > 0 else 1
    year  = int(date.split("-")[0])
    month = int(date.split("-")[1])

    new_row = pd.DataFrame([{
        "ид_чека":     new_id,
        "дата":        date,
        "год":         year,
        "месяц":       month,
        "магазин":     store,
        "состав":      ", ".join(sorted(items_clean)),
        "кол_товаров": len(items_clean),
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_dataset(df)
    _invalidate_cache()
    return new_id


def delete_transaction(transaction_id: int) -> int:
    """
    Удаляет чек по ID.
    Возвращает количество удалённых строк (0 если не найден).
    """
    df = load_dataset()
    before = len(df)
    df = df[df["ид_чека"] != int(transaction_id)]
    deleted = before - len(df)
    if deleted > 0:
        save_dataset(df)
        _invalidate_cache()
    return deleted


def show_data(year=None, store=None, n=20):
    df = load_dataset()
    if year:
        df = df[df["год"] == int(year)]
    if store:
        df = df[df["магазин"].str.lower() == store.lower()]
    return df.tail(n)


def get_stats(df=None):
    """Статистика датасета для отображения при запуске."""
    if df is None:
        df = load_dataset()

    # Топ-3 товара по частоте
    freq = {}
    for row in df["состав"]:
        for item in [i.strip() for i in str(row).split(",")]:
            freq[item] = freq.get(item, 0) + 1
    top3 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]

    # Средний размер чека
    avg_basket = round(df["кол_товаров"].mean(), 1)

    # Самый активный магазин
    top_store = df["магазин"].value_counts().idxmax()
    top_store_cnt = int(df["магазин"].value_counts().max())

    return {
        "топ_товары":      top3,
        "средний_чек":     avg_basket,
        "топ_магазин":     top_store,
        "топ_магазин_кол": top_store_cnt,
    }
