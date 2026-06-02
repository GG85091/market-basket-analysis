"""
dataset.py — генерация датасета транзакций для Market Basket Analysis
"""
import pandas as pd
import numpy as np
import os
import random

DATA_FILE = "transactions.csv"

ITEMS = [
    "Молоко", "Хлеб", "Яйца", "Масло", "Сыр",
    "Кофе", "Чай", "Сахар", "Мука", "Рис",
    "Макароны", "Курица", "Говядина", "Рыба", "Колбаса",
    "Йогурт", "Сметана", "Шоколад", "Печенье", "Сок"
]

STORES = ["Korzinka", "Makro", "Havas", "Smart", "Supermarket Baraka"]

# Нечёткое соответствие — транслит / опечатки → правильное название
STORE_ALIASES = {
    "korzinka": "Korzinka", "корзинка": "Korzinka", "korzinka.uz": "Korzinka",
    "корзинка.уз": "Korzinka", "korzika": "Korzinka", "кorzinka": "Korzinka",

    "makro": "Makro", "макро": "Makro", "macro": "Makro", "makra": "Makro",
    "мakro": "Makro", "макра": "Makro",

    "havas": "Havas", "хавас": "Havas", "havaz": "Havas", "xavas": "Havas",
    "havas market": "Havas",

    "smart": "Smart", "смарт": "Smart", "smar": "Smart", "smrt": "Smart",

    "baraka": "Supermarket Baraka", "барака": "Supermarket Baraka",
    "supermarket baraka": "Supermarket Baraka", "баракa": "Supermarket Baraka",
    "barak": "Supermarket Baraka",
}

# Нечёткое соответствие для товаров
ITEM_ALIASES = {
    "молоко": "Молоко", "moloko": "Молоко", "maloko": "Молоко", "молака": "Молоко",
    "хлеб": "Хлеб", "non": "Хлеб", "hleb": "Хлеб", "bread": "Хлеб",
    "яйца": "Яйца", "яица": "Яйца", "yayca": "Яйца", "eggs": "Яйца", "yajca": "Яйца",
    "масло": "Масло", "масла": "Масло", "maslo": "Масло", "butter": "Масло",
    "сыр": "Сыр", "syr": "Сыр", "cheese": "Сыр", "сир": "Сыр",
    "кофе": "Кофе", "kofe": "Кофе", "coffee": "Кофе", "кафе": "Кофе",
    "чай": "Чай", "chay": "Чай", "tea": "Чай", "чяй": "Чай",
    "сахар": "Сахар", "sahar": "Сахар", "sugar": "Сахар", "sahар": "Сахар",
    "мука": "Мука", "muka": "Мука", "flour": "Мука", "мукa": "Мука",
    "рис": "Рис", "ris": "Рис", "rice": "Рис", "риc": "Рис",
    "макароны": "Макароны", "pasta": "Макароны", "makaroni": "Макароны", "макарони": "Макароны",
    "курица": "Курица", "kurica": "Курица", "chicken": "Курица",
    "говядина": "Говядина", "myaso": "Говядина", "beef": "Говядина", "гавядина": "Говядина",
    "рыба": "Рыба", "ryba": "Рыба", "fish": "Рыба", "рыбa": "Рыба",
    "колбаса": "Колбаса", "kolbasa": "Колбаса", "sausage": "Колбаса", "калбаса": "Колбаса",
    "йогурт": "Йогурт", "yogurt": "Йогурт", "iogurt": "Йогурт", "ёгурт": "Йогурт",
    "сметана": "Сметана", "smetana": "Сметана", "сметанa": "Сметана",
    "шоколад": "Шоколад", "shokolad": "Шоколад", "chocolate": "Шоколад", "шакалад": "Шоколад",
    "печенье": "Печенье", "pechenye": "Печенье", "cookies": "Печенье", "пичение": "Печенье",
    "сок": "Сок", "sok": "Сок", "juice": "Сок", "сoк": "Сок",
}

PATTERNS = [
    ["Молоко", "Хлеб", "Масло"],
    ["Кофе", "Сахар", "Печенье"],
    ["Чай", "Сахар", "Печенье"],
    ["Яйца", "Масло", "Мука"],
    ["Макароны", "Говядина", "Сыр"],
    ["Курица", "Рис", "Сметана"],
    ["Йогурт", "Молоко", "Сметана"],
    ["Рыба", "Рис", "Сок"],
    ["Шоколад", "Кофе", "Молоко"],
    ["Колбаса", "Хлеб", "Сыр"],
]


def fuzzy_store(text: str) -> str | None:
    """Нечёткое распознавание магазина."""
    t = text.lower().strip()
    if t in STORE_ALIASES:
        return STORE_ALIASES[t]
    # Частичное совпадение
    for alias, store in STORE_ALIASES.items():
        if alias in t or t in alias:
            return store
    # Прямое совпадение с названием
    for store in STORES:
        if store.lower() == t:
            return store
    return None


def fuzzy_item(text: str) -> str | None:
    """Нечёткое распознавание товара."""
    t = text.lower().strip()
    if t in ITEM_ALIASES:
        return ITEM_ALIASES[t]
    # Частичное совпадение
    for alias, item in ITEM_ALIASES.items():
        if alias in t or t in alias:
            return item
    # Прямое
    for item in ITEMS:
        if item.lower() == t:
            return item
    return None


def create_dataset(force=False):
    if os.path.exists(DATA_FILE) and not force:
        print(f"📂 Датасет уже существует: {DATA_FILE}")
        return pd.read_csv(DATA_FILE)

    np.random.seed(42)
    random.seed(42)
    records = []
    tid = 1

    for year in range(2015, 2027):
        for month in range(1, 13):
            n = np.random.randint(24, 28)
            for _ in range(n):
                day   = np.random.randint(1, 29)
                store = np.random.choice(STORES)
                date  = f"{year}-{month:02d}-{day:02d}"
                basket = set(np.random.choice(ITEMS, size=np.random.randint(2, 5), replace=False))
                if random.random() < 0.70:
                    basket.update(random.choice(PATTERNS))
                records.append({
                    "ид_чека":     tid,
                    "дата":        date,
                    "год":         year,
                    "месяц":       month,
                    "магазин":     store,
                    "состав":      ", ".join(sorted(basket)),
                    "кол_товаров": len(basket),
                })
                tid += 1

    df = pd.DataFrame(records)
    df.to_csv(DATA_FILE, index=False)
    print(f"✅ Датасет создан: {len(df)} транзакций → {DATA_FILE}")
    return df


def get_item_list():
    return ITEMS

def get_store_list():
    return STORES


if __name__ == "__main__":
    create_dataset(force=True)