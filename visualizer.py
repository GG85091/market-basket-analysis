"""
visualizer.py — 7 графиков для Market Basket Analysis
Все графики сохраняются в папку plots/ как PNG файлы.
"""
import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use("Agg")   # non-interactive backend: рисуем в файл, не в окно
import matplotlib.pyplot as plt
import seaborn as sns

matplotlib.rcParams["font.family"]      = "DejaVu Sans"
matplotlib.rcParams["figure.facecolor"] = "white"

PLOTS_DIR = "plots"


# ── Внутренние утилиты ───────────────────────────────────────────────────────

def _ensure_dir():
    os.makedirs(PLOTS_DIR, exist_ok=True)


def _save(fig: plt.Figure, filename: str) -> str:
    _ensure_dir()
    path = os.path.join(PLOTS_DIR, filename)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"   📊 → {path}")
    return path


# ── График 1: Топ правил по Lift ─────────────────────────────────────────────

def plot_top_rules_by_lift(rules: pd.DataFrame, top_n: int = 15) -> str:
    top    = rules.head(top_n).copy()
    labels = (top["antecedents_str"] + "  →  " + top["consequents_str"]).values[::-1]
    lifts  = top["lift"].round(2).values[::-1]

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(top)))
    bars   = ax.barh(labels, lifts, color=colors, edgecolor="none", height=0.6)

    for bar, val in zip(bars, lifts):
        ax.text(
            bar.get_width() + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}", va="center", fontsize=9,
        )

    ax.set_title(f"Топ-{top_n} ассоциативных правил по Лифту",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Лифт (чем выше — тем сильнее связь)")
    ax.axvline(1.0, color="red", lw=0.8, ls="--", alpha=0.6,
               label="Лифт = 1 (случайность)")
    ax.legend(fontsize=9)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    return _save(fig, "1_top_rules_lift.png")


# ── График 2: Heatmap совместных покупок ─────────────────────────────────────

def plot_cooccurrence_heatmap(df: pd.DataFrame) -> str:
    from dataset import ITEMS
    items  = sorted(ITEMS)
    matrix = pd.DataFrame(0, index=items, columns=items, dtype=int)

    for _, row in df.iterrows():
        basket = [i.strip() for i in str(row["состав"]).split(",")]
        for a in basket:
            for b in basket:
                if a in matrix.index and b in matrix.columns:
                    matrix.loc[a, b] += 1

    # Убираем диагональ
    mat = matrix.values.copy()
    np.fill_diagonal(mat, 0)
    matrix = pd.DataFrame(mat, index=matrix.index, columns=matrix.columns)

    fig, ax = plt.subplots(figsize=(14, 11))
    sns.heatmap(
        matrix, ax=ax, cmap="Blues",
        linewidths=0.3, linecolor="#e0e0e0",
        annot=True, fmt="d", annot_kws={"size": 7},
        cbar_kws={"label": "Кол-во совместных покупок"},
    )
    ax.set_title("Матрица совместных покупок", fontsize=14, fontweight="bold")
    ax.set_xlabel("Товар Б")
    ax.set_ylabel("Товар А")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    fig.tight_layout()
    return _save(fig, "2_cooccurrence_heatmap.png")


# ── График 3: Частота товаров ─────────────────────────────────────────────────

def plot_item_frequency(df: pd.DataFrame) -> str:
    from dataset import ITEMS
    freq = {item: 0 for item in ITEMS}
    for _, row in df.iterrows():
        for item in [i.strip() for i in str(row["состав"]).split(",")]:
            if item in freq:
                freq[item] += 1

    total = len(df)
    s = pd.Series(
        {k: round(v / total * 100, 1) for k, v in freq.items()}
    ).sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.Purples(np.linspace(0.4, 0.9, len(s)))[::-1]
    bars   = ax.bar(s.index, s.values, color=colors, edgecolor="none", width=0.7)

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{bar.get_height():.1f}%",
            ha="center", va="bottom", fontsize=8,
        )

    ax.set_title("Частота встречаемости товаров в чеках",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("% чеков")
    ax.set_xlabel("Товар")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, "3_item_frequency.png")


# ── График 4: Support vs Confidence (scatter) ─────────────────────────────────

def plot_support_confidence(rules: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(
        rules["support"], rules["confidence"],
        c=rules["lift"], cmap="YlOrRd",
        s=60, alpha=0.7, edgecolors="none",
    )
    fig.colorbar(sc, ax=ax).set_label("Лифт")
    ax.set_title("Поддержка vs Уверенность (цвет = Лифт)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Поддержка (Support)")
    ax.set_ylabel("Уверенность (Confidence)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _save(fig, "4_support_confidence.png")


# ── График 5: Топ правил по Confidence ───────────────────────────────────────

def plot_top_rules_confidence(rules: pd.DataFrame, top_n: int = 10) -> str:
    top    = rules.nlargest(top_n, "confidence")
    labels = (top["antecedents_str"] + " → " + top["consequents_str"]).values[::-1]
    vals   = top["confidence"].round(3).values[::-1]

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(top)))
    ax.barh(labels, vals, color=colors, edgecolor="none", height=0.6)
    ax.set_title(f"Топ-{top_n} правил по Уверенности",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Уверенность — вероятность купить Б при покупке А")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    return _save(fig, "5_top_confidence.png")


# ── График 6: Сравнение магазинов по среднему Lift ────────────────────────────

def plot_store_comparison(df: pd.DataFrame) -> str | None:
    from dataset import STORES
    from model import build_rules as _build

    store_data = {}
    for store in STORES:
        df_s = df[df["магазин"] == store]
        if len(df_s) < 50:
            continue
        try:
            r = _build(df_s)
            if not r.empty:
                store_data[store] = round(r.head(3)["lift"].mean(), 3)
        except Exception:
            pass

    if not store_data:
        print("   ⚠️  Недостаточно данных по магазинам для графика 6")
        return None

    stores = list(store_data.keys())
    lifts  = [store_data[s] for s in stores]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.Oranges(np.linspace(0.4, 0.9, len(stores)))[::-1]
    bars   = ax.bar(stores, lifts, color=colors, edgecolor="none", width=0.6)

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{bar.get_height():.2f}",
            ha="center", va="bottom", fontsize=10,
        )

    ax.set_title("Средний Лифт топ-3 правил по магазинам",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Средний Лифт")
    ax.set_xlabel("Магазин")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return _save(fig, "6_store_lift.png")


# ── График 7: Wordcloud популярности товаров ──────────────────────────────────

def plot_wordcloud(df: pd.DataFrame) -> str | None:
    try:
        from wordcloud import WordCloud
    except ImportError:
        print("   ⚠️  Пакет wordcloud не установлен (pip install wordcloud). График 7 пропущен.")
        return None

    freq = {}
    for _, row in df.iterrows():
        for item in [i.strip() for i in str(row["состав"]).split(",")]:
            freq[item] = freq.get(item, 0) + 1

    wc = WordCloud(
        width=1200, height=600,
        background_color="white",
        colormap="Blues",
        max_font_size=120,
        min_font_size=20,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Популярность товаров — облако слов",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "7_wordcloud.png")


# ── График 8: Количество правил от min_support ───────────────────────────────

def plot_support_vs_rules(df: pd.DataFrame, selected_support: float = 0.05) -> str:
    from model import build_rules as _build

    support_values = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20]
    rule_counts = []
    for sup in support_values:
        try:
            r = _build(df, support=sup)
            rule_counts.append(len(r))
        except Exception:
            rule_counts.append(0)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(support_values, rule_counts, marker="o", color="#1f6aa5",
            linewidth=2.5, markersize=8)
    ax.axvline(selected_support, color="#ef4444", lw=1.5, ls="--", alpha=0.9,
               label=f"Выбранное значение ({selected_support})")
    for x, y in zip(support_values, rule_counts):
        ax.annotate(str(y), (x, y), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=9)
    ax.set_title("Количество правил от min_support", fontsize=14, fontweight="bold")
    ax.set_xlabel("min_support")
    ax.set_ylabel("Количество ассоциативных правил")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _save(fig, "8_support_vs_rules.png")


# ── HTML-отчёт ────────────────────────────────────────────────────────────────

def export_html_report(df: pd.DataFrame, rules: pd.DataFrame,
                        filename: str = "report.html") -> str:
    import base64
    from datetime import datetime
    from database import get_stats
    from model import get_top_rules, get_business_recommendations

    stats   = get_stats(df)
    top3_it = ", ".join(f"{i} ({c})" for i, c in stats["топ_товары"])
    top20   = get_top_rules(rules, n=20)
    biz     = get_business_recommendations(rules, top_n=5)
    now     = datetime.now().strftime("%Y-%m-%d %H:%M")

    graph_meta = [
        ("1_top_rules_lift.png",      "Топ-15 правил по Лифту"),
        ("2_cooccurrence_heatmap.png", "Матрица совместных покупок"),
        ("3_item_frequency.png",       "Частота товаров"),
        ("4_support_confidence.png",   "Support vs Confidence"),
        ("5_top_confidence.png",       "Топ правил по Уверенности"),
        ("6_store_lift.png",           "Средний Лифт по магазинам"),
        ("7_wordcloud.png",            "Облако слов"),
        ("8_support_vs_rules.png",     "Правила от min_support"),
    ]
    graphs_html = ""
    for fname, title in graph_meta:
        path = os.path.join(PLOTS_DIR, fname)
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            graphs_html += f"""
      <div class="card">
        <h3 class="card-title">{title}</h3>
        <img src="data:image/png;base64,{b64}" alt="{title}" class="plot-img">
      </div>"""

    rows_html = ""
    for _, row in top20.iterrows():
        lift = row["Лифт"]
        cls  = "lift-high" if lift >= 3 else ("lift-mid" if lift >= 1.5 else "lift-low")
        rows_html += f"""
      <tr>
        <td>{row['Если куплено']}</td><td>{row['То купят']}</td>
        <td>{row['Поддержка']}</td><td>{row['Уверенность']}</td>
        <td class="{cls}">{row['Лифт']}</td>
      </tr>"""

    biz_items = "".join(f"<li>{b}</li>" for b in biz)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Market Basket Analysis — Отчёт</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:Arial,sans-serif;background:#1e1e1e;color:#e0e0e0;padding:24px}}
    h1{{color:#1f6aa5;font-size:28px;margin-bottom:4px}}
    h2{{color:#1f6aa5;font-size:20px;margin:32px 0 12px;border-bottom:2px solid #1f6aa5;padding-bottom:6px}}
    h3.card-title{{color:#aaa;font-size:14px;margin-bottom:8px}}
    .subtitle{{color:#888;font-size:13px;margin-bottom:28px}}
    .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:8px}}
    .stat-card{{background:#252525;border:1px solid #333;border-radius:8px;padding:16px}}
    .stat-label{{font-size:12px;color:#888;margin-bottom:4px}}
    .stat-value{{font-size:22px;font-weight:bold;color:#1f6aa5}}
    .stat-sub{{font-size:12px;color:#aaa;margin-top:4px}}
    table{{width:100%;border-collapse:collapse;font-size:13px}}
    th{{background:#1f6aa5;color:#fff;padding:10px 12px;text-align:left;cursor:pointer;user-select:none}}
    th:hover{{background:#2980b9}}
    td{{padding:9px 12px;border-bottom:1px solid #333}}
    tr:hover td{{background:#2a2a2a}}
    .lift-high{{color:#10b981;font-weight:bold}}
    .lift-mid{{color:#f59e0b;font-weight:bold}}
    .lift-low{{color:#aaa}}
    .graphs-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:20px}}
    .card{{background:#252525;border:1px solid #333;border-radius:8px;padding:16px}}
    .plot-img{{width:100%;height:auto;border-radius:4px}}
    ul.biz-list{{list-style:none;padding:0}}
    ul.biz-list li{{background:#252525;border-left:3px solid #1f6aa5;margin-bottom:10px;padding:10px 14px;border-radius:0 6px 6px 0;font-size:14px}}
    footer{{margin-top:40px;color:#555;font-size:12px;text-align:center}}
  </style>
</head>
<body>
  <h1>🔍 Market Basket Analysis — Отчёт</h1>
  <p class="subtitle">Сгенерировано: {now} &nbsp;|&nbsp; Алгоритм: Apriori / FP-Growth</p>

  <h2>📊 Статистика датасета</h2>
  <div class="stats-grid">
    <div class="stat-card"><div class="stat-label">Всего чеков</div>
      <div class="stat-value">{len(df):,}</div></div>
    <div class="stat-card"><div class="stat-label">Средний чек</div>
      <div class="stat-value">{stats['средний_чек']}</div>
      <div class="stat-sub">товаров в чеке</div></div>
    <div class="stat-card"><div class="stat-label">Топ магазин</div>
      <div class="stat-value">{stats['топ_магазин']}</div>
      <div class="stat-sub">{stats['топ_магазин_кол']} чеков</div></div>
    <div class="stat-card"><div class="stat-label">Найдено правил</div>
      <div class="stat-value">{len(rules)}</div>
      <div class="stat-sub">Макс. Lift: {rules['lift'].max():.4f}</div></div>
    <div class="stat-card"><div class="stat-label">Топ товары</div>
      <div class="stat-value" style="font-size:13px">{top3_it}</div></div>
  </div>

  <h2>📋 Топ-20 ассоциативных правил</h2>
  <table id="rulesTable">
    <thead><tr>
      <th onclick="sortTable(0)">Если куплено ↕</th>
      <th onclick="sortTable(1)">То купят ↕</th>
      <th onclick="sortTable(2)">Поддержка ↕</th>
      <th onclick="sortTable(3)">Уверенность ↕</th>
      <th onclick="sortTable(4)">Лифт ↕</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  <h2>💡 Бизнес-рекомендации</h2>
  <ul class="biz-list">{biz_items}</ul>

  <h2>📈 Графики</h2>
  <div class="graphs-grid">{graphs_html}</div>

  <footer>Market Basket Analysis System · Retail Intelligence</footer>
  <script>
    function sortTable(col){{
      const tbl=document.getElementById('rulesTable'),tbody=tbl.tBodies[0];
      const rows=Array.from(tbody.rows);
      const asc=tbl.dataset.sortCol==col&&tbl.dataset.sortDir=='asc';
      rows.sort((a,b)=>{{
        const va=a.cells[col].innerText,vb=b.cells[col].innerText;
        const na=parseFloat(va),nb=parseFloat(vb);
        if(!isNaN(na)&&!isNaN(nb))return asc?na-nb:nb-na;
        return asc?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(r=>tbody.appendChild(r));
      tbl.dataset.sortCol=col;tbl.dataset.sortDir=asc?'desc':'asc';
    }}
  </script>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   🌐 HTML-отчёт → {os.path.abspath(filename)}")
    return os.path.abspath(filename)


# ── Генерация всех графиков ───────────────────────────────────────────────────

def generate_all_plots(df: pd.DataFrame, rules: pd.DataFrame) -> list[str]:
    print("\n📊 Генерирую графики...")
    paths = []

    try:
        paths.append(plot_top_rules_by_lift(rules))
    except Exception as e:
        print(f"   ❌ График 1: {e}")

    try:
        paths.append(plot_cooccurrence_heatmap(df))
    except Exception as e:
        print(f"   ❌ График 2: {e}")

    try:
        paths.append(plot_item_frequency(df))
    except Exception as e:
        print(f"   ❌ График 3: {e}")

    try:
        paths.append(plot_support_confidence(rules))
    except Exception as e:
        print(f"   ❌ График 4: {e}")

    try:
        paths.append(plot_top_rules_confidence(rules))
    except Exception as e:
        print(f"   ❌ График 5: {e}")

    try:
        p = plot_store_comparison(df)
        if p:
            paths.append(p)
    except Exception as e:
        print(f"   ❌ График 6: {e}")

    try:
        p = plot_wordcloud(df)
        if p:
            paths.append(p)
    except Exception as e:
        print(f"   ❌ График 7: {e}")

    try:
        paths.append(plot_support_vs_rules(df))
    except Exception as e:
        print(f"   ❌ График 8: {e}")

    print(f"✅ Готово: {len(paths)} графиков в папке ./plots/")
    return paths
