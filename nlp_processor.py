"""
nlp_processor.py — распознавание намерений и сущностей из текстовых команд
"""
from dataset import ITEMS, STORES, fuzzy_item, fuzzy_store


def find_command(text: str) -> str | None:
    """
    Определяет намерение пользователя по ключевым словам.

    Returns
    -------
    Строка-намерение: 'recommend' | 'rules' | 'add' | 'show' |
                      'delete' | 'plot' | 'history' | 'train' | 'exit'
    или None если намерение не распознано.
    """
    t = text.lower()

    if any(w in t for w in ["рекоменд", "что купят", "suggest", "recommend"]):
        return "recommend"
    if any(w in t for w in ["правил", "rules", "ассоц"]):
        return "rules"
    if any(w in t for w in ["добав", "add", "новый чек", "новый"]):
        return "add"
    if any(w in t for w in ["покажи", "show", "данные", "список"]):
        return "show"
    if any(w in t for w in ["удал", "delete", "remove", "убери"]):
        return "delete"
    if any(w in t for w in ["граф", "plot", "визуал", "heatmap", "chart"]):
        return "plot"
    if any(w in t for w in ["истори", "history", "лог"]):
        return "history"
    if any(w in t for w in ["обучи", "train", "пересч", "построй"]):
        return "train"
    if any(w in t for w in ["выход", "exit", "quit", "стоп"]):
        return "exit"
    return None


def extract_item(text: str) -> str | None:
    """
    Пытается найти товар в тексте.
    Сначала точное совпадение, затем нечёткое через fuzzy_item.
    """
    t = text.lower()
    # Точное совпадение (без учёта регистра)
    for item in ITEMS:
        if item.lower() in t:
            return item
    # Нечёткое распознавание транслита
    for word in t.split():
        result = fuzzy_item(word)
        if result:
            return result
    return None


def extract_store(text: str) -> str | None:
    """
    Пытается найти магазин в тексте.
    Сначала точное совпадение, затем нечёткое через fuzzy_store.
    """
    t = text.lower()
    for store in STORES:
        if store.lower() in t:
            return store
    result = fuzzy_store(t)
    return result
