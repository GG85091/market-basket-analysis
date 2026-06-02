# Market Basket Analysis System

Система анализа рыночной корзины на основе алгоритмов **Apriori** и **FP-Growth**.  

---

## Возможности

- Генерация и хранение датасета транзакций (чеков) супермаркетов
- Построение ассоциативных правил (Apriori / FP-Growth) через библиотеку `mlxtend`
- Рекомендации товаров по одному или двум входным товарам
- Анализ правил по магазину и по диапазону лет
- Экспорт правил в CSV и Excel
- История рекомендаций с сохранением на диск
- 8 информационных графиков (heatmap, scatter, wordcloud, support vs rules и др.)
- Нечёткое распознавание названий товаров и магазинов (транслит, опечатки)
- Замер и сравнение скорости Apriori vs FP-Growth
- Сезонный анализ (Зима / Весна / Лето / Осень)
- Интерактивный HTML-отчёт (standalone, с base64-графиками и JS-сортировкой)
- Три интерфейса: **CLI** (rich), **GUI** (PyQt5), **Web** (Streamlit)

---

## Структура проекта

```
.
├── main.py            # CLI-интерфейс (rich)
├── gui_app.py         # GUI-интерфейс (PyQt5)
├── streamlit_app.py   # Web-интерфейс (Streamlit)
├── model.py           # Apriori / FP-Growth, правила, рекомендации
├── database.py        # CRUD операции над датасетом
├── dataset.py         # Генерация датасета, fuzzy-распознавание
├── nlp_processor.py   # Распознавание намерений из текста
├── predict.py         # Сохранение и загрузка истории рекомендаций
├── visualizer.py      # 8 графиков + HTML-отчёт (matplotlib / seaborn)
├── .streamlit/
│   └── config.toml    # Тёмная тема Streamlit
└── requirements.txt   # Зависимости
```

---

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
```

---

## Запуск

### CLI
```bash
python main.py
```

### GUI (PyQt5)
```bash
python gui_app.py
```

### Web (Streamlit)
```bash
streamlit run streamlit_app.py
```

Приложение откроется в браузере по адресу **http://localhost:8501**

#### Вкладки Streamlit-интерфейса

| Вкладка | Функционал |
|---------|------------|
| 📋 Данные | Таблица чеков с фильтрами, добавление и удаление |
| 🎯 Рекомендации | Выбор товара → топ-5 рекомендаций |
| 📊 Топ правил | Таблица топ-10 + бизнес-рекомендации |
| ⚡ Сравнение | Замер времени Apriori vs FP-Growth + bar chart |
| 🌍 Сезоны | Топ-3 правила по каждому сезону |
| 📈 Графики | Все 8 PNG встроены через `st.image` |
| 🌐 HTML-отчёт | Генерация и скачивание standalone-отчёта |

---

## Зависимости

| Пакет | Назначение |
|-------|------------|
| `pandas` | Работа с датасетами |
| `numpy` | Числовые операции |
| `mlxtend` | Apriori, FP-Growth, association_rules |
| `matplotlib` | Графики |
| `seaborn` | Heatmap |
| `rich` | Красивый CLI |
| `PyQt5` | GUI |
| `openpyxl` | Экспорт в Excel |
| `wordcloud` | График 7 (облако слов, опционально) |
| `streamlit` | Web-интерфейс |

---

## Магазины и товары

**Магазины:** Korzinka, Makro, Havas, Smart, Supermarket Baraka

**Товары (20 шт.):** Молоко, Хлеб, Яйца, Масло, Сыр, Кофе, Чай, Сахар, Мука, Рис, Макароны, Курица, Говядина, Рыба, Колбаса, Йогурт, Сметана, Шоколад, Печенье, Сок

---

## Датасет

Генерируется автоматически при первом запуске (`transactions.csv`).  
Содержит ~3 000 транзакций за 2015–2026 гг. с заложенными паттернами покупок.

Принудительная пересборка:
```bash
python dataset.py
```
