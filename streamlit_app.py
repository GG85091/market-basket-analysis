"""
streamlit_app.py — Streamlit интерфейс для Market Basket Analysis
"""
import os
import streamlit as st
import pandas as pd

from database import load_dataset, add_transaction, delete_transaction, show_data, get_stats
from dataset import ITEMS, STORES, fuzzy_item
from model import (
    build_rules, recommend, get_top_rules, get_business_recommendations,
    compare_algorithms, build_rules_by_season, save_rules, cache_rules,
)
from visualizer import generate_all_plots, export_html_report

TRANSLATIONS = {
    "en": {
        "title": "Market Basket Analysis System",
        "tab_data": "📋 Data",
        "tab_recommendations": "🎯 Recommendations",
        "tab_rules": "📊 Top Rules",
        "tab_comparison": "⚡ Comparison",
        "tab_seasons": "🌍 Seasons",
        "tab_charts": "📈 Charts",
        "tab_report": "🌐 HTML Report",
        "settings": "⚙️ Settings",
        "algorithm": "Algorithm",
        "build_rules": "🚀 Build Rules",
        "rules_found": "✅ Found {n} rules",
        "rules_not_found": "⚠️ No rules found. Lower the parameters.",
        "receipts": "Receipts",
        "avg_basket": "Avg basket",
        "top_store": "Top store",
        "rules_built": "Rules built",
        "dataset_title": "Dataset Receipts",
        "year": "Year",
        "store": "Store",
        "all": "All",
        "add_receipt": "➕ Add Receipt",
        "delete_receipt": "🗑️ Delete Receipt",
        "date": "Date",
        "items_input": "Items separated by commas",
        "items_placeholder": "Milk, Bread, Butter",
        "save": "💾 Save",
        "unknown_items": "Skipped unrecognised: {items}",
        "receipt_added": "✅ Receipt #{id} added",
        "receipt_id": "Receipt ID",
        "delete_btn": "🗑️ Delete",
        "receipt_deleted": "✅ Receipt #{id} deleted",
        "receipt_not_found": "Receipt #{id} not found",
        "shown": "Showing {n} receipts",
        "recommendations_title": "Product Recommendations",
        "build_first": "ℹ️ Build rules in the sidebar first",
        "select_product": "Select product",
        "get_recommendations": "🎯 Get Recommendations",
        "no_recs": "No recommendations found for «{item}»",
        "top_rules_title": "Top-10 Association Rules",
        "business_recs": "💡 Business Recommendations",
        "comparison_title": "⚡ Apriori vs FP-Growth",
        "comparison_caption": "Both algorithms run with current sidebar parameters",
        "run_comparison": "Run Comparison",
        "measuring": "Measuring time...",
        "col_algo": "Algorithm",
        "col_time": "Time (sec)",
        "col_rules": "Rules",
        "col_lift": "Max Lift",
        "col_conf": "Max Conf",
        "seasons_title": "🌍 Seasonal Analysis",
        "seasons_caption": "Top-3 rules per season",
        "run_seasons": "Analyse Seasons",
        "building_seasons": "Building rules by season...",
        "charts_title": "📈 All 8 Charts",
        "build_charts": "🎨 Build All Charts",
        "build_rules_first": "⚠️ Build rules in the sidebar first",
        "generating_charts": "Generating 8 charts...",
        "charts_done": "✅ Done — 8 charts saved to plots/",
        "charts_empty": "Charts not built yet. Click the button above.",
        "report_title": "🌐 Interactive HTML Report",
        "report_caption": "Standalone file with all charts, tables and business recommendations",
        "generate_report": "📄 Generate Report",
        "generating_report": "Generating HTML report...",
        "report_ready": "✅ Report ready: {path}",
        "download_report": "⬇️ Download report.html",
        "report_size": "Size: {kb} KB",
        "language": "🌐 Language",
        "spinner_algo": "Running {algo}...",
        "graph_titles": [
            "Top-15 Rules by Lift",
            "Co-occurrence Heatmap",
            "Item Frequency",
            "Support vs Confidence",
            "Top Rules by Confidence",
            "Avg Lift by Store",
            "Word Cloud",
            "Rules vs min_support",
        ],
    },
    "ru": {
        "title": "Market Basket Analysis System",
        "tab_data": "📋 Данные",
        "tab_recommendations": "🎯 Рекомендации",
        "tab_rules": "📊 Топ правил",
        "tab_comparison": "⚡ Сравнение",
        "tab_seasons": "🌍 Сезоны",
        "tab_charts": "📈 Графики",
        "tab_report": "🌐 HTML-отчёт",
        "settings": "⚙️ Настройки",
        "algorithm": "Алгоритм",
        "build_rules": "🚀 Построить правила",
        "rules_found": "✅ Найдено {n} правил",
        "rules_not_found": "⚠️ Правила не найдены. Снизьте параметры.",
        "receipts": "Чеков",
        "avg_basket": "Средний чек",
        "top_store": "Топ магазин",
        "rules_built": "Правил построено",
        "dataset_title": "Чеки датасета",
        "year": "Год",
        "store": "Магазин",
        "all": "Все",
        "add_receipt": "➕ Добавить чек",
        "delete_receipt": "🗑️ Удалить чек",
        "date": "Дата",
        "items_input": "Товары через запятую",
        "items_placeholder": "Молоко, Хлеб, Масло",
        "save": "💾 Сохранить",
        "unknown_items": "Пропущены нераспознанные: {items}",
        "receipt_added": "✅ Чек #{id} добавлен",
        "receipt_id": "ID чека",
        "delete_btn": "🗑️ Удалить",
        "receipt_deleted": "✅ Чек #{id} удалён",
        "receipt_not_found": "Чек #{id} не найден",
        "shown": "Показано {n} чеков",
        "recommendations_title": "Рекомендации по товару",
        "build_first": "ℹ️ Сначала постройте правила в боковой панели",
        "select_product": "Выберите товар",
        "get_recommendations": "🎯 Получить рекомендации",
        "no_recs": "Рекомендаций для «{item}» не найдено",
        "top_rules_title": "Топ-10 ассоциативных правил",
        "business_recs": "💡 Бизнес-рекомендации",
        "comparison_title": "⚡ Apriori vs FP-Growth",
        "comparison_caption": "Оба алгоритма запускаются с текущими параметрами из боковой панели",
        "run_comparison": "Запустить сравнение",
        "measuring": "Замеряю время...",
        "col_algo": "Алгоритм",
        "col_time": "Время (сек)",
        "col_rules": "Правил",
        "col_lift": "Макс. Lift",
        "col_conf": "Макс. Conf",
        "seasons_title": "🌍 Сезонный анализ",
        "seasons_caption": "Топ-3 правила для каждого сезона",
        "run_seasons": "Анализировать сезоны",
        "building_seasons": "Строю правила по сезонам...",
        "charts_title": "📈 Все 8 графиков",
        "build_charts": "🎨 Построить все графики",
        "build_rules_first": "⚠️ Сначала постройте правила в боковой панели",
        "generating_charts": "Генерирую 8 графиков...",
        "charts_done": "✅ Готово — 8 графиков сохранены в plots/",
        "charts_empty": "Графики ещё не построены. Нажмите кнопку выше.",
        "report_title": "🌐 Интерактивный HTML-отчёт",
        "report_caption": "Standalone файл со всеми графиками, таблицами и бизнес-рекомендациями",
        "generate_report": "📄 Сгенерировать отчёт",
        "generating_report": "Генерирую HTML-отчёт...",
        "report_ready": "✅ Отчёт готов: {path}",
        "download_report": "⬇️ Скачать report.html",
        "report_size": "Размер: {kb} КБ",
        "language": "🌐 Язык",
        "spinner_algo": "Запускаю {algo}...",
        "graph_titles": [
            "Топ-15 правил по Лифту",
            "Матрица совместных покупок",
            "Частота товаров",
            "Support vs Confidence",
            "Топ правил по Уверенности",
            "Средний Лифт по магазинам",
            "Облако слов",
            "Правила от min_support",
        ],
    },
}

st.set_page_config(
    page_title="Market Basket Analysis",
    page_icon="🔍",
    layout="wide",
)

# ── Session state ─────────────────────────────────────────────────────────────
for _key, _default in [
    ("rules",       None),
    ("df",          None),
    ("cmp_results", None),
    ("seasons",     None),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

if st.session_state.df is None:
    st.session_state.df = load_dataset()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    lang = st.radio("🌐 Language", ["EN", "RU"], horizontal=True)
    t = TRANSLATIONS["en"] if lang == "EN" else TRANSLATIONS["ru"]

    st.title(t["settings"])

    min_support    = st.slider("min_support",    0.01, 0.30, 0.05, 0.01, format="%.2f")
    min_confidence = st.slider("min_confidence", 0.10, 0.90, 0.30, 0.05, format="%.2f")
    algorithm      = st.radio(t["algorithm"], ["Apriori", "FP-Growth"])
    algo_key       = "fpgrowth" if algorithm == "FP-Growth" else "apriori"

    if st.button(t["build_rules"], use_container_width=True, type="primary"):
        with st.spinner(t["spinner_algo"].format(algo=algorithm)):
            _rules = build_rules(
                st.session_state.df,
                support=min_support,
                confidence=min_confidence,
                algorithm=algo_key,
            )
            st.session_state.rules = _rules
            if not _rules.empty:
                save_rules(_rules)
                cache_rules(_rules)
                st.success(t["rules_found"].format(n=len(_rules)))
            else:
                st.warning(t["rules_not_found"])

    st.divider()

    _stats = get_stats(st.session_state.df)
    st.metric(t["receipts"],   f"{len(st.session_state.df):,}")
    st.metric(t["avg_basket"], f"{_stats['средний_чек']} {'' if lang == 'EN' else 'товаров'}")
    st.metric(t["top_store"],  _stats["топ_магазин"])
    if st.session_state.rules is not None and not st.session_state.rules.empty:
        st.metric(
            t["rules_built"], len(st.session_state.rules),
            delta=f"max lift {st.session_state.rules['lift'].max():.2f}",
        )

# ── Заголовок ─────────────────────────────────────────────────────────────────
st.title(f"🔍 {t['title']}")

tabs = st.tabs([
    t["tab_data"], t["tab_recommendations"], t["tab_rules"],
    t["tab_comparison"], t["tab_seasons"], t["tab_charts"], t["tab_report"],
])

# ── Вкладка 1: Данные ─────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader(t["dataset_title"])

    c1, c2 = st.columns(2)
    with c1:
        year_sel  = st.selectbox(t["year"],  [t["all"]] + list(range(2026, 2014, -1)))
    with c2:
        store_sel = st.selectbox(t["store"], [t["all"]] + STORES)

    df_view = show_data(
        year=None  if year_sel  == t["all"] else int(year_sel),
        store=None if store_sel == t["all"] else store_sel,
        n=100,
    )
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    st.caption(t["shown"].format(n=len(df_view)))

    st.divider()
    col_add, col_del = st.columns(2)

    with col_add:
        with st.expander(t["add_receipt"]):
            with st.form("add_form", clear_on_submit=True):
                date_val  = st.date_input(t["date"])
                store_val = st.selectbox(t["store"], STORES)
                items_raw = st.text_input(
                    t["items_input"],
                    placeholder=t["items_placeholder"],
                )
                if st.form_submit_button(t["save"]):
                    try:
                        raw_list = [i.strip() for i in items_raw.split(",") if i.strip()]
                        resolved, unknown = [], []
                        for raw in raw_list:
                            matched = raw if raw in ITEMS else fuzzy_item(raw)
                            (resolved if matched else unknown).append(matched or raw)
                        if unknown:
                            st.warning(t["unknown_items"].format(items=", ".join(unknown)))
                        new_id = add_transaction(str(date_val), store_val, resolved)
                        st.session_state.df = load_dataset()
                        st.success(t["receipt_added"].format(id=new_id))
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with col_del:
        with st.expander(t["delete_receipt"]):
            with st.form("del_form", clear_on_submit=True):
                del_id = st.number_input(t["receipt_id"], min_value=1, step=1, value=1)
                if st.form_submit_button(t["delete_btn"]):
                    deleted = delete_transaction(int(del_id))
                    if deleted:
                        st.session_state.df = load_dataset()
                        st.success(t["receipt_deleted"].format(id=int(del_id)))
                        st.rerun()
                    else:
                        st.error(t["receipt_not_found"].format(id=int(del_id)))

# ── Вкладка 2: Рекомендации ───────────────────────────────────────────────────
with tabs[1]:
    st.subheader(t["recommendations_title"])
    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info(t["build_first"])
    else:
        item_sel = st.selectbox(t["select_product"], ITEMS, key="rec_item")
        if st.button(t["get_recommendations"]):
            recs = recommend(st.session_state.rules, item_sel, top_n=5)
            if recs.empty:
                st.warning(t["no_recs"].format(item=item_sel))
            else:
                st.dataframe(recs, use_container_width=True, hide_index=True)

# ── Вкладка 3: Топ правил ─────────────────────────────────────────────────────
with tabs[2]:
    st.subheader(t["top_rules_title"])
    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info(t["build_first"])
    else:
        top = get_top_rules(st.session_state.rules, n=10)
        st.dataframe(top, use_container_width=True, hide_index=True)

        st.subheader(t["business_recs"])
        for b in get_business_recommendations(st.session_state.rules, top_n=5):
            st.markdown(f"- {b}")

# ── Вкладка 4: Сравнение алгоритмов ──────────────────────────────────────────
with tabs[3]:
    st.subheader(t["comparison_title"])
    st.caption(t["comparison_caption"])

    if st.button(t["run_comparison"], key="run_cmp"):
        with st.spinner(t["measuring"]):
            st.session_state.cmp_results = compare_algorithms(
                st.session_state.df,
                support=min_support,
                confidence=min_confidence,
            )

    if st.session_state.cmp_results:
        df_cmp = pd.DataFrame(st.session_state.cmp_results)
        df_cmp.columns = [
            t["col_algo"], t["col_time"], t["col_rules"], t["col_lift"], t["col_conf"]
        ]
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)
        st.bar_chart(
            df_cmp.set_index(t["col_algo"])[[t["col_time"]]],
            use_container_width=True,
        )

# ── Вкладка 5: Сезонный анализ ────────────────────────────────────────────────
with tabs[4]:
    st.subheader(t["seasons_title"])
    st.caption(t["seasons_caption"])

    if st.button(t["run_seasons"], key="run_seasons"):
        with st.spinner(t["building_seasons"]):
            st.session_state.seasons = build_rules_by_season(st.session_state.df)

    if st.session_state.seasons:
        ICONS = {"Зима": "❄️", "Весна": "🌸", "Лето": "☀️", "Осень": "🍂"}
        seasons_list = list(st.session_state.seasons.items())
        for row_start in range(0, len(seasons_list), 2):
            col1, col2 = st.columns(2, gap="large")
            pair = seasons_list[row_start:row_start + 2]
            for col, (season, top) in zip([col1, col2], pair):
                with col:
                    st.markdown(
                        f"<h3 style='margin-top:0; padding-bottom:6px; "
                        f"border-bottom:2px solid #444;'>"
                        f"{ICONS.get(season, '')} {season}</h3>",
                        unsafe_allow_html=True,
                    )
                    st.dataframe(top, use_container_width=True, hide_index=True)
            st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)

# ── Вкладка 6: Графики ────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader(t["charts_title"])

    if st.button(t["build_charts"], key="run_plots"):
        if st.session_state.rules is None or st.session_state.rules.empty:
            st.warning(t["build_rules_first"])
        else:
            with st.spinner(t["generating_charts"]):
                generate_all_plots(st.session_state.df, st.session_state.rules)
            st.success(t["charts_done"])

    GRAPH_FILES = [
        "1_top_rules_lift.png",
        "2_cooccurrence_heatmap.png",
        "3_item_frequency.png",
        "4_support_confidence.png",
        "5_top_confidence.png",
        "6_store_lift.png",
        "7_wordcloud.png",
        "8_support_vs_rules.png",
    ]
    img_cols = st.columns(2)
    any_found = False
    for i, (fname, title) in enumerate(zip(GRAPH_FILES, t["graph_titles"])):
        path = os.path.join("plots", fname)
        if os.path.exists(path):
            any_found = True
            with img_cols[i % 2]:
                st.markdown(f"**{title}**")
                st.image(path, use_container_width=True)
    if not any_found:
        st.info(t["charts_empty"])

# ── Вкладка 7: HTML-отчёт ─────────────────────────────────────────────────────
with tabs[6]:
    st.subheader(t["report_title"])
    st.caption(t["report_caption"])

    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info(t["build_first"])
    else:
        if st.button(t["generate_report"], key="gen_html"):
            with st.spinner(t["generating_report"]):
                report_path = export_html_report(st.session_state.df, st.session_state.rules)
            st.success(t["report_ready"].format(path=report_path))

        if os.path.exists("report.html"):
            with open("report.html", "rb") as _f:
                st.download_button(
                    label=t["download_report"],
                    data=_f,
                    file_name="market_basket_report.html",
                    mime="text/html",
                    use_container_width=True,
                )
            st.caption(t["report_size"].format(kb=f"{os.path.getsize('report.html') / 1024:.0f}"))
