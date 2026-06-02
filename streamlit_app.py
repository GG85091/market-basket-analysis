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
    st.title("⚙️ Настройки")

    min_support    = st.slider("min_support",    0.01, 0.30, 0.05, 0.01, format="%.2f")
    min_confidence = st.slider("min_confidence", 0.10, 0.90, 0.30, 0.05, format="%.2f")
    algorithm      = st.radio("Алгоритм", ["Apriori", "FP-Growth"])
    algo_key       = "fpgrowth" if algorithm == "FP-Growth" else "apriori"

    if st.button("🚀 Построить правила", use_container_width=True, type="primary"):
        with st.spinner(f"Запускаю {algorithm}..."):
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
                st.success(f"✅ Найдено {len(_rules)} правил")
            else:
                st.warning("⚠️ Правила не найдены. Снизьте параметры.")

    st.divider()

    _stats = get_stats(st.session_state.df)
    st.metric("Чеков",        f"{len(st.session_state.df):,}")
    st.metric("Средний чек",  f"{_stats['средний_чек']} товаров")
    st.metric("Топ магазин",  _stats["топ_магазин"])
    if st.session_state.rules is not None and not st.session_state.rules.empty:
        st.metric(
            "Правил построено", len(st.session_state.rules),
            delta=f"max lift {st.session_state.rules['lift'].max():.2f}",
        )

# ── Заголовок ─────────────────────────────────────────────────────────────────
st.title("🔍 Market Basket Analysis System")

tabs = st.tabs([
    "📋 Данные", "🎯 Рекомендации", "📊 Топ правил",
    "⚡ Сравнение", "🌍 Сезоны", "📈 Графики", "🌐 HTML-отчёт",
])

# ── Вкладка 1: Данные ─────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Чеки датасета")

    c1, c2 = st.columns(2)
    with c1:
        year_sel  = st.selectbox("Год", ["Все"] + list(range(2026, 2014, -1)))
    with c2:
        store_sel = st.selectbox("Магазин", ["Все"] + STORES)

    df_view = show_data(
        year=None  if year_sel  == "Все" else int(year_sel),
        store=None if store_sel == "Все" else store_sel,
        n=100,
    )
    st.dataframe(df_view, use_container_width=True, hide_index=True)
    st.caption(f"Показано {len(df_view)} чеков")

    st.divider()
    col_add, col_del = st.columns(2)

    with col_add:
        with st.expander("➕ Добавить чек"):
            with st.form("add_form", clear_on_submit=True):
                date_val  = st.date_input("Дата")
                store_val = st.selectbox("Магазин", STORES)
                items_raw = st.text_input(
                    "Товары через запятую",
                    placeholder="Молоко, Хлеб, Масло",
                )
                if st.form_submit_button("💾 Сохранить"):
                    try:
                        raw_list = [i.strip() for i in items_raw.split(",") if i.strip()]
                        resolved, unknown = [], []
                        for raw in raw_list:
                            matched = raw if raw in ITEMS else fuzzy_item(raw)
                            (resolved if matched else unknown).append(matched or raw)
                        if unknown:
                            st.warning(f"Пропущены нераспознанные: {', '.join(unknown)}")
                        new_id = add_transaction(str(date_val), store_val, resolved)
                        st.session_state.df = load_dataset()
                        st.success(f"✅ Чек #{new_id} добавлен")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    with col_del:
        with st.expander("🗑️ Удалить чек"):
            with st.form("del_form", clear_on_submit=True):
                del_id = st.number_input("ID чека", min_value=1, step=1, value=1)
                if st.form_submit_button("🗑️ Удалить"):
                    deleted = delete_transaction(int(del_id))
                    if deleted:
                        st.session_state.df = load_dataset()
                        st.success(f"✅ Чек #{int(del_id)} удалён")
                        st.rerun()
                    else:
                        st.error(f"Чек #{int(del_id)} не найден")

# ── Вкладка 2: Рекомендации ───────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Рекомендации по товару")
    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info("ℹ️ Сначала постройте правила в боковой панели")
    else:
        item_sel = st.selectbox("Выберите товар", ITEMS, key="rec_item")
        if st.button("🎯 Получить рекомендации"):
            recs = recommend(st.session_state.rules, item_sel, top_n=5)
            if recs.empty:
                st.warning(f"Рекомендаций для «{item_sel}» не найдено")
            else:
                st.dataframe(recs, use_container_width=True, hide_index=True)

# ── Вкладка 3: Топ правил ─────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Топ-10 ассоциативных правил")
    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info("ℹ️ Сначала постройте правила в боковой панели")
    else:
        top = get_top_rules(st.session_state.rules, n=10)
        st.dataframe(top, use_container_width=True, hide_index=True)

        st.subheader("💡 Бизнес-рекомендации")
        for b in get_business_recommendations(st.session_state.rules, top_n=5):
            st.markdown(f"- {b}")

# ── Вкладка 4: Сравнение алгоритмов ──────────────────────────────────────────
with tabs[3]:
    st.subheader("⚡ Apriori vs FP-Growth")
    st.caption("Оба алгоритма запускаются с текущими параметрами из боковой панели")

    if st.button("Запустить сравнение", key="run_cmp"):
        with st.spinner("Замеряю время..."):
            st.session_state.cmp_results = compare_algorithms(
                st.session_state.df,
                support=min_support,
                confidence=min_confidence,
            )

    if st.session_state.cmp_results:
        df_cmp = pd.DataFrame(st.session_state.cmp_results)
        df_cmp.columns = ["Алгоритм", "Время (сек)", "Правил", "Макс. Lift", "Макс. Conf"]
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)
        st.bar_chart(
            df_cmp.set_index("Алгоритм")[["Время (сек)"]],
            use_container_width=True,
        )

# ── Вкладка 5: Сезонный анализ ────────────────────────────────────────────────
with tabs[4]:
    st.subheader("🌍 Сезонный анализ")
    st.caption("Топ-3 правила для каждого сезона")

    if st.button("Анализировать сезоны", key="run_seasons"):
        with st.spinner("Строю правила по сезонам..."):
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
    st.subheader("📈 Все 8 графиков")

    if st.button("🎨 Построить все графики", key="run_plots"):
        if st.session_state.rules is None or st.session_state.rules.empty:
            st.warning("⚠️ Сначала постройте правила в боковой панели")
        else:
            with st.spinner("Генерирую 8 графиков..."):
                generate_all_plots(st.session_state.df, st.session_state.rules)
            st.success("✅ Готово — 8 графиков сохранены в plots/")

    GRAPH_META = [
        ("1_top_rules_lift.png",       "Топ-15 правил по Лифту"),
        ("2_cooccurrence_heatmap.png",  "Матрица совместных покупок"),
        ("3_item_frequency.png",        "Частота товаров"),
        ("4_support_confidence.png",    "Support vs Confidence"),
        ("5_top_confidence.png",        "Топ правил по Уверенности"),
        ("6_store_lift.png",            "Средний Лифт по магазинам"),
        ("7_wordcloud.png",             "Облако слов"),
        ("8_support_vs_rules.png",      "Правила от min_support"),
    ]
    img_cols = st.columns(2)
    any_found = False
    for i, (fname, title) in enumerate(GRAPH_META):
        path = os.path.join("plots", fname)
        if os.path.exists(path):
            any_found = True
            with img_cols[i % 2]:
                st.markdown(f"**{title}**")
                st.image(path, use_container_width=True)
    if not any_found:
        st.info("Графики ещё не построены. Нажмите кнопку выше.")

# ── Вкладка 7: HTML-отчёт ─────────────────────────────────────────────────────
with tabs[6]:
    st.subheader("🌐 Интерактивный HTML-отчёт")
    st.caption("Standalone файл со всеми графиками, таблицами и бизнес-рекомендациями")

    if st.session_state.rules is None or st.session_state.rules.empty:
        st.info("ℹ️ Сначала постройте правила в боковой панели")
    else:
        if st.button("📄 Сгенерировать отчёт", key="gen_html"):
            with st.spinner("Генерирую HTML-отчёт..."):
                report_path = export_html_report(st.session_state.df, st.session_state.rules)
            st.success(f"✅ Отчёт готов: {report_path}")

        if os.path.exists("report.html"):
            with open("report.html", "rb") as _f:
                st.download_button(
                    label="⬇️ Скачать report.html",
                    data=_f,
                    file_name="market_basket_report.html",
                    mime="text/html",
                    use_container_width=True,
                )
            st.caption(f"Размер: {os.path.getsize('report.html') / 1024:.0f} КБ")
