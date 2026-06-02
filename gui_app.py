"""
GUI приложение Market Basket Analysis
Красивый интерфейс на PyQt5 с вкладками, таблицами, графиками
"""

import sys
import os

# PyQt5 импорты — всё сразу в начале файла
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLineEdit, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit, QProgressBar,
    QHeaderView, QFrame, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

# Импорт нашей логики
from database import load_dataset, add_transaction, delete_transaction, show_data, get_stats
from dataset import ITEMS, STORES, fuzzy_store, fuzzy_item
from model import (
    build_rules, recommend, get_top_rules,
    get_business_recommendations, save_rules, cache_rules,
    compare_algorithms, build_rules_by_season,
)
from predict import load_history, save_recommendation
from visualizer import generate_all_plots, export_html_report


# ── Фоновый поток для Apriori (не блокирует UI) ──────────────────────────────

class AprioriWorker(QThread):
    finished = pyqtSignal(object, str)   # (rules_df, algorithm_name)
    error    = pyqtSignal(str)

    def __init__(self, df, support, confidence, algorithm):
        super().__init__()
        self.df         = df
        self.support    = support
        self.confidence = confidence
        self.algorithm  = algorithm

    def run(self):
        try:
            rules = build_rules(
                self.df,
                support=self.support,
                confidence=self.confidence,
                algorithm=self.algorithm,
            )
            self.finished.emit(rules, self.algorithm)
        except Exception as e:
            self.error.emit(str(e))


# ── Фоновый поток для сравнения алгоритмов ───────────────────────────────────

class CompareWorker(QThread):
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, df, support, confidence):
        super().__init__()
        self.df         = df
        self.support    = support
        self.confidence = confidence

    def run(self):
        try:
            results = compare_algorithms(self.df, self.support, self.confidence)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ── Главное окно ──────────────────────────────────────────────────────────────

class MBAApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Market Basket Analysis System")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(self._dark_stylesheet())

        self._rules          = None
        self._df             = load_dataset()
        self._worker         = None   # держим ссылку чтобы QThread не умер
        self._compare_worker = None

        self._init_ui()
        self._update_stats()

    # ── Стили ────────────────────────────────────────────────────────────────

    def _dark_stylesheet(self):
        return """
        QMainWindow { background-color: #1e1e1e; color: #ffffff; }
        QWidget     { background-color: #1e1e1e; color: #ffffff; }
        QTabWidget::pane  { border: 1px solid #444; background-color: #252525; }
        QTabBar::tab      { background-color: #2a2a2a; color: #aaa; padding: 8px 20px; border: 1px solid #444; }
        QTabBar::tab:selected { background-color: #1f6aa5; color: #fff; }
        QPushButton {
            background-color: #1f6aa5; color: white; border: none;
            padding: 8px 16px; border-radius: 4px;
            font-weight: bold; font-size: 11pt;
        }
        QPushButton:hover    { background-color: #2980b9; }
        QPushButton:pressed  { background-color: #1a4d7a; }
        QPushButton:disabled { background-color: #555; color: #888; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
            background-color: #2a2a2a; color: #fff;
            border: 1px solid #444; padding: 6px; border-radius: 3px;
        }
        QLineEdit:focus { border: 2px solid #1f6aa5; }
        QTableWidget         { background-color: #2a2a2a; color: #fff; gridline-color: #444; }
        QTableWidget::item   { padding: 5px; }
        QTableWidget::item:selected { background-color: #1f6aa5; }
        QHeaderView::section { background-color: #1f6aa5; color: white; padding: 5px; border: none; }
        QLabel    { color: #fff; }
        QTextEdit { background-color: #2a2a2a; color: #fff; border: 1px solid #444; }
        QRadioButton { color: #fff; }
        QProgressBar { border: 1px solid #444; border-radius: 3px; text-align: center; }
        QProgressBar::chunk { background-color: #1f6aa5; }
        """

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Заголовок
        title = QLabel("🔍 Market Basket Analysis System")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #1f6aa5;")
        layout.addWidget(title)

        # Строка статистики
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Arial", 10))
        self.stats_label.setStyleSheet("color: #aaa; padding: 6px 10px;")
        layout.addWidget(self.stats_label)

        # Вкладки
        tabs = QTabWidget()
        tabs.addTab(self._tab_data(),      "📋 Данные")
        tabs.addTab(self._tab_apriori(),   "⚙️  Apriori / FP-Growth")
        tabs.addTab(self._tab_recommend(), "🎯 Рекомендации")
        tabs.addTab(self._tab_rules(),     "📊 Топ-10 правил")
        tabs.addTab(self._tab_history(),   "📈 История")
        tabs.addTab(self._tab_seasons(),   "🌍 Сезоны")
        tabs.addTab(self._tab_plots(),     "📉 Графики")
        layout.addWidget(tabs)

        # Статус-бар
        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: #aaa; padding: 5px;")
        layout.addWidget(self.status_label)

    # ── Вкладка: Данные ───────────────────────────────────────────────────────

    def _tab_data(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        # Фильтры
        f_frame = QFrame()
        f_lay   = QHBoxLayout(f_frame)

        f_lay.addWidget(QLabel("Год:"))
        self.year_spin = QSpinBox()
        self.year_spin.setMinimum(2015)
        self.year_spin.setMaximum(2026)
        self.year_spin.setValue(2024)
        f_lay.addWidget(self.year_spin)

        f_lay.addWidget(QLabel("Магазин:"))
        self.store_combo_data = QComboBox()
        self.store_combo_data.addItem("Все")
        self.store_combo_data.addItems(STORES)
        f_lay.addWidget(self.store_combo_data)

        btn_filter = QPushButton("Показать")
        btn_filter.clicked.connect(self._show_data)
        f_lay.addWidget(btn_filter)
        f_lay.addStretch()
        lay.addWidget(f_frame)

        # Таблица чеков
        self.table_data = QTableWidget()
        self.table_data.setColumnCount(5)
        self.table_data.setHorizontalHeaderLabels(["ID", "Дата", "Магазин", "Кол-во", "Состав"])
        self.table_data.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_data.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.table_data)

        # Кнопки CRUD
        btn_frame = QFrame()
        btn_lay   = QHBoxLayout(btn_frame)
        btn_add = QPushButton("➕ Добавить чек")
        btn_add.clicked.connect(self._add_dialog)
        btn_lay.addWidget(btn_add)
        btn_del = QPushButton("🗑️  Удалить выбранный")
        btn_del.clicked.connect(self._delete_row)
        btn_lay.addWidget(btn_del)
        btn_lay.addStretch()
        lay.addWidget(btn_frame)

        return w

    # ── Вкладка: Apriori / FP-Growth ─────────────────────────────────────────

    def _tab_apriori(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        # Параметры
        p_frame = QFrame()
        p_lay   = QHBoxLayout(p_frame)

        p_lay.addWidget(QLabel("min_support:"))
        self.sup_spin = QDoubleSpinBox()
        self.sup_spin.setMinimum(0.01)
        self.sup_spin.setMaximum(0.30)
        self.sup_spin.setValue(0.05)
        self.sup_spin.setDecimals(3)
        self.sup_spin.setSingleStep(0.01)
        p_lay.addWidget(self.sup_spin)

        p_lay.addWidget(QLabel("min_confidence:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setMinimum(0.10)
        self.conf_spin.setMaximum(0.90)
        self.conf_spin.setValue(0.30)
        self.conf_spin.setDecimals(3)
        self.conf_spin.setSingleStep(0.05)
        p_lay.addWidget(self.conf_spin)

        # Выбор алгоритма
        p_lay.addWidget(QLabel("Алгоритм:"))
        self.rb_apriori  = QRadioButton("Apriori")
        self.rb_fpgrowth = QRadioButton("FP-Growth")
        self.rb_apriori.setChecked(True)
        algo_group = QButtonGroup(w)
        algo_group.addButton(self.rb_apriori)
        algo_group.addButton(self.rb_fpgrowth)
        p_lay.addWidget(self.rb_apriori)
        p_lay.addWidget(self.rb_fpgrowth)

        self.btn_build = QPushButton("🚀 Построить")
        self.btn_build.clicked.connect(self._build_rules_async)
        p_lay.addWidget(self.btn_build)
        p_lay.addStretch()
        lay.addWidget(p_frame)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # бесконечный спиннер
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        # Результат
        self.result_label = QLabel("Выберите параметры и нажмите «Построить»")
        self.result_label.setStyleSheet("color: #aaa; padding: 12px;")
        self.result_label.setWordWrap(True)
        lay.addWidget(self.result_label)

        # Сравнение алгоритмов
        btn_cmp = QPushButton("⚡ Сравнить алгоритмы")
        btn_cmp.clicked.connect(self._compare_algorithms)
        lay.addWidget(btn_cmp)

        self.table_compare = QTableWidget()
        self.table_compare.setColumnCount(5)
        self.table_compare.setHorizontalHeaderLabels(
            ["Алгоритм", "Время (сек)", "Правил", "Макс. Lift", "Макс. Conf"]
        )
        self.table_compare.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_compare.setMaximumHeight(100)
        lay.addWidget(self.table_compare)

        lay.addStretch()
        return w

    # ── Вкладка: Рекомендации ─────────────────────────────────────────────────

    def _tab_recommend(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        inp_frame = QFrame()
        inp_lay   = QHBoxLayout(inp_frame)
        inp_lay.addWidget(QLabel("Товар:"))
        self.item_combo = QComboBox()
        self.item_combo.addItems(ITEMS)
        inp_lay.addWidget(self.item_combo)
        btn_rec = QPushButton("🎯 Получить рекомендации")
        btn_rec.clicked.connect(self._get_recommendations)
        inp_lay.addWidget(btn_rec)
        inp_lay.addStretch()
        lay.addWidget(inp_frame)

        self.table_rec = QTableWidget()
        self.table_rec.setColumnCount(4)
        self.table_rec.setHorizontalHeaderLabels(["Товар", "Уверенность", "Лифт", "Поддержка"])
        self.table_rec.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        lay.addWidget(self.table_rec)

        return w

    # ── Вкладка: Топ-10 правил ────────────────────────────────────────────────

    def _tab_rules(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        btn_show = QPushButton("📊 Показать топ-10 правил")
        btn_show.clicked.connect(self._show_top_rules)
        lay.addWidget(btn_show)

        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(5)
        self.table_rules.setHorizontalHeaderLabels(
            ["Если куплено", "То купят", "Support", "Confidence", "Lift"]
        )
        self.table_rules.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        lay.addWidget(self.table_rules)

        lay.addWidget(QLabel("💡 Бизнес-рекомендации:"))
        self.biz_text = QTextEdit()
        self.biz_text.setReadOnly(True)
        self.biz_text.setMaximumHeight(150)
        lay.addWidget(self.biz_text)

        return w

    # ── Вкладка: История ──────────────────────────────────────────────────────

    def _tab_history(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        btn_load = QPushButton("📈 Загрузить историю")
        btn_load.clicked.connect(self._load_history)
        lay.addWidget(btn_load)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(5)
        self.table_history.setHorizontalHeaderLabels(
            ["Дата", "Товар", "Рекомендован", "Уверенность", "Лифт"]
        )
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        lay.addWidget(self.table_history)

        return w

    # ── Вкладка: Сезоны ───────────────────────────────────────────────────────

    def _tab_seasons(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        btn_season = QPushButton("🌿 Анализировать сезоны")
        btn_season.clicked.connect(self._show_seasonal)
        lay.addWidget(btn_season)

        self.season_tables = {}
        season_icons = [("❄️ Зима", "Зима"), ("🌸 Весна", "Весна"),
                        ("☀️ Лето", "Лето"),  ("🍂 Осень", "Осень")]
        for title, key in season_icons:
            lay.addWidget(QLabel(title))
            tbl = QTableWidget()
            tbl.setColumnCount(5)
            tbl.setHorizontalHeaderLabels(
                ["Если куплено", "То купят", "Поддержка", "Уверенность", "Лифт"]
            )
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            tbl.setMaximumHeight(140)
            lay.addWidget(tbl)
            self.season_tables[key] = tbl

        lay.addStretch()
        return w

    # ── Вкладка: Графики ──────────────────────────────────────────────────────

    def _tab_plots(self):
        w   = QWidget()
        lay = QVBoxLayout(w)

        btn_plots = QPushButton("🎨 Построить все графики (8 штук)")
        btn_plots.clicked.connect(self._generate_plots)
        lay.addWidget(btn_plots)

        self.plots_label = QLabel(
            "Графики сохранятся в папку plots/ и откроются в проводнике."
        )
        self.plots_label.setStyleSheet("color: #aaa; padding: 8px;")
        self.plots_label.setWordWrap(True)
        lay.addWidget(self.plots_label)

        btn_html = QPushButton("🌐 Экспорт HTML-отчёта")
        btn_html.clicked.connect(self._export_html_report)
        lay.addWidget(btn_html)

        self.html_label = QLabel("")
        self.html_label.setStyleSheet("color: #aaa; padding: 8px;")
        self.html_label.setWordWrap(True)
        lay.addWidget(self.html_label)

        lay.addStretch()
        return w

    # ── Слоты (обработчики событий) ───────────────────────────────────────────

    def _show_data(self):
        year  = self.year_spin.value()
        store = self.store_combo_data.currentText()
        store_filt = None if store == "Все" else store
        df = show_data(year=year, store=store_filt, n=100)
        self._fill_table(self.table_data, df,
                         ["ид_чека", "дата", "магазин", "кол_товаров", "состав"])
        self.status_label.setText(f"✓ Загружено {len(df)} чеков")

    def _add_dialog(self):
        dialog = QWidget()
        dialog.setWindowTitle("Добавить чек")
        dialog.setStyleSheet(self._dark_stylesheet())
        lay = QVBoxLayout(dialog)

        lay.addWidget(QLabel("Дата:"))
        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat("yyyy-MM-dd")
        lay.addWidget(date_edit)

        lay.addWidget(QLabel("Магазин:"))
        store_combo = QComboBox()
        store_combo.addItems(STORES)
        lay.addWidget(store_combo)

        lay.addWidget(QLabel("Товары (через запятую, минимум 2):"))
        items_edit = QLineEdit()
        items_edit.setPlaceholderText("Молоко, Хлеб, Масло")
        lay.addWidget(items_edit)

        def save():
            try:
                date_str = date_edit.date().toString("yyyy-MM-dd")
                raw_items = [i.strip() for i in items_edit.text().split(",") if i.strip()]
                # Нечёткое распознавание
                resolved = []
                unknown  = []
                for raw in raw_items:
                    matched = fuzzy_item(raw) if raw not in ITEMS else raw
                    if matched:
                        resolved.append(matched)
                    else:
                        unknown.append(raw)
                if unknown:
                    QMessageBox.warning(
                        dialog, "⚠️ Товары не распознаны",
                        f"Следующие товары пропущены:\n{', '.join(unknown)}"
                    )
                new_id = add_transaction(date_str, store_combo.currentText(), resolved)
                self._df = load_dataset()
                self._update_stats()
                QMessageBox.information(dialog, "✓", f"Чек #{new_id} добавлен")
                dialog.close()
            except ValueError as e:
                QMessageBox.critical(dialog, "❌ Ошибка валидации", str(e))
            except Exception as e:
                QMessageBox.critical(dialog, "❌ Ошибка", str(e))

        btn = QPushButton("💾 Сохранить")
        btn.clicked.connect(save)
        lay.addWidget(btn)

        dialog.setGeometry(500, 300, 420, 280)
        dialog.show()

    def _delete_row(self):
        row = self.table_data.currentRow()
        if row < 0:
            QMessageBox.warning(self, "⚠️", "Выберите строку для удаления")
            return
        item = self.table_data.item(row, 0)
        if item is None:
            return
        tid = int(item.text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить чек #{tid}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            deleted = delete_transaction(tid)
            if deleted:
                self.table_data.removeRow(row)
                self._df = load_dataset()
                self._update_stats()
                self.status_label.setText(f"✓ Чек #{tid} удалён")
            else:
                QMessageBox.warning(self, "⚠️", f"Чек #{tid} не найден")
        except Exception as e:
            QMessageBox.critical(self, "❌", str(e))

    def _build_rules_async(self):
        """Запускает построение правил в фоновом потоке."""
        algorithm = "fpgrowth" if self.rb_fpgrowth.isChecked() else "apriori"
        self.btn_build.setEnabled(False)
        self.progress.setVisible(True)
        self.result_label.setText(f"⏳ Запускаю {algorithm.upper()}...")
        self.result_label.setStyleSheet("color: #aaa; padding: 12px;")

        self._worker = AprioriWorker(
            df=self._df,
            support=self.sup_spin.value(),
            confidence=self.conf_spin.value(),
            algorithm=algorithm,
        )
        self._worker.finished.connect(self._on_rules_done)
        self._worker.error.connect(self._on_rules_error)
        self._worker.start()

    def _on_rules_done(self, rules, algorithm):
        self._rules = rules
        self.btn_build.setEnabled(True)
        self.progress.setVisible(False)

        if rules.empty:
            self.result_label.setText("⚠️ Правил не найдено. Снизьте min_support или min_confidence.")
            self.result_label.setStyleSheet("color: #f59e0b; padding: 12px;")
        else:
            save_rules(rules)
            cache_rules(rules)
            txt = (
                f"✅ {algorithm.upper()} завершён\n\n"
                f"Найдено правил:       {len(rules)}\n"
                f"Макс. Лифт:           {rules['lift'].max():.4f}\n"
                f"Макс. Уверенность:    {rules['confidence'].max():.4f}\n"
                f"Сохранено в:          правила.csv + кэш"
            )
            self.result_label.setText(txt)
            self.result_label.setStyleSheet("color: #10b981; padding: 12px;")
        self.status_label.setText(f"✓ {algorithm.upper()} готов ({len(rules)} правил)")

    def _on_rules_error(self, error_msg):
        self.btn_build.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "❌ Ошибка", error_msg)
        self.result_label.setText(f"❌ Ошибка: {error_msg}")
        self.result_label.setStyleSheet("color: #ef4444; padding: 12px;")

    def _get_recommendations(self):
        if self._rules is None or self._rules.empty:
            QMessageBox.warning(self, "⚠️", "Сначала постройте правила (вкладка Apriori)")
            return
        item = self.item_combo.currentText()
        recs = recommend(self._rules, item, top_n=5)
        self.table_rec.setRowCount(0)
        if recs.empty:
            QMessageBox.information(self, "ℹ️", f"Рекомендаций для «{item}» не найдено")
            return
        for i, (_, row) in enumerate(recs.iterrows()):
            self.table_rec.insertRow(i)
            self.table_rec.setItem(i, 0, QTableWidgetItem(row["Товар"]))
            self.table_rec.setItem(i, 1, QTableWidgetItem(f"{row['Уверенность']:.4f}"))
            lift_item = QTableWidgetItem(f"{row['Лифт']:.4f}")
            # Цветовая кодировка Lift
            if row["Лифт"] >= 3:
                lift_item.setForeground(QColor("#10b981"))
            elif row["Лифт"] >= 1.5:
                lift_item.setForeground(QColor("#f59e0b"))
            self.table_rec.setItem(i, 2, lift_item)
            self.table_rec.setItem(i, 3, QTableWidgetItem(f"{row['Поддержка']:.4f}"))
        save_recommendation(item, recs)
        self.status_label.setText(f"✓ Рекомендации для «{item}» загружены")

    def _show_top_rules(self):
        if self._rules is None or self._rules.empty:
            QMessageBox.warning(self, "⚠️", "Сначала постройте правила (вкладка Apriori)")
            return
        top = get_top_rules(self._rules, n=10)
        self.table_rules.setRowCount(0)
        for i, (_, row) in enumerate(top.iterrows()):
            self.table_rules.insertRow(i)
            self.table_rules.setItem(i, 0, QTableWidgetItem(row["Если куплено"]))
            self.table_rules.setItem(i, 1, QTableWidgetItem(row["То купят"]))
            self.table_rules.setItem(i, 2, QTableWidgetItem(str(row["Поддержка"])))
            self.table_rules.setItem(i, 3, QTableWidgetItem(str(row["Уверенность"])))
            lift_item = QTableWidgetItem(str(row["Лифт"]))
            if row["Лифт"] >= 3:
                lift_item.setForeground(QColor("#10b981"))
            elif row["Лифт"] >= 1.5:
                lift_item.setForeground(QColor("#f59e0b"))
            self.table_rules.setItem(i, 4, lift_item)

        biz = get_business_recommendations(self._rules, top_n=5)
        self.biz_text.setText("\n\n".join(biz))
        self.status_label.setText("✓ Топ-10 правил загружены")

    def _load_history(self):
        hist = load_history(n=50)
        self.table_history.setRowCount(0)
        if hist.empty:
            self.status_label.setText("История пуста")
            return
        for i, (_, row) in enumerate(hist.iterrows()):
            self.table_history.insertRow(i)
            self.table_history.setItem(i, 0, QTableWidgetItem(str(row["дата_запроса"])))
            self.table_history.setItem(i, 1, QTableWidgetItem(str(row["товар"])))
            self.table_history.setItem(i, 2, QTableWidgetItem(str(row["рекомендован"])))
            self.table_history.setItem(i, 3, QTableWidgetItem(f"{row['уверенность']:.4f}"))
            self.table_history.setItem(i, 4, QTableWidgetItem(f"{row['лифт']:.4f}"))
        self.status_label.setText(f"✓ История загружена ({len(hist)} записей)")

    def _generate_plots(self):
        if self._rules is None or self._rules.empty:
            QMessageBox.warning(self, "⚠️", "Сначала постройте правила (вкладка Apriori)")
            return
        try:
            generate_all_plots(self._df, self._rules)
            self.plots_label.setText("✅ 8 графиков сохранены в папку plots/")
            self.status_label.setText("✓ Графики готовы")
            # Открываем папку в проводнике
            import platform
            plots_path = os.path.abspath("plots")
            if platform.system() == "Windows":
                os.startfile(plots_path)
            elif platform.system() == "Darwin":
                os.system(f'open "{plots_path}"')
            else:
                os.system(f'xdg-open "{plots_path}"')
        except Exception as e:
            QMessageBox.critical(self, "❌", str(e))

    def _compare_algorithms(self):
        self._compare_worker = CompareWorker(
            df=self._df,
            support=self.sup_spin.value(),
            confidence=self.conf_spin.value(),
        )
        self._compare_worker.finished.connect(self._on_compare_done)
        self._compare_worker.error.connect(self._on_compare_error)
        self._compare_worker.start()
        self.status_label.setText("⏳ Сравниваю алгоритмы...")

    def _on_compare_done(self, results):
        self.table_compare.setRowCount(0)
        for i, r in enumerate(results):
            self.table_compare.insertRow(i)
            self.table_compare.setItem(i, 0, QTableWidgetItem(r["algorithm"]))
            self.table_compare.setItem(i, 1, QTableWidgetItem(str(r["time_sec"])))
            self.table_compare.setItem(i, 2, QTableWidgetItem(str(r["rules_count"])))
            self.table_compare.setItem(i, 3, QTableWidgetItem(str(r["max_lift"])))
            self.table_compare.setItem(i, 4, QTableWidgetItem(str(r["max_confidence"])))
        self.status_label.setText("✓ Сравнение завершено → comparison_results.csv")

    def _on_compare_error(self, msg):
        QMessageBox.critical(self, "❌", msg)
        self.status_label.setText("❌ Ошибка сравнения")

    def _show_seasonal(self):
        try:
            seasons = build_rules_by_season(self._df)
            if not seasons:
                QMessageBox.information(self, "ℹ️", "Недостаточно данных для сезонного анализа")
                return
            for key, tbl in self.season_tables.items():
                tbl.setRowCount(0)
                if key not in seasons:
                    continue
                top = seasons[key]
                for i, (_, row) in enumerate(top.iterrows()):
                    tbl.insertRow(i)
                    tbl.setItem(i, 0, QTableWidgetItem(str(row["Если куплено"])))
                    tbl.setItem(i, 1, QTableWidgetItem(str(row["То купят"])))
                    tbl.setItem(i, 2, QTableWidgetItem(str(row["Поддержка"])))
                    tbl.setItem(i, 3, QTableWidgetItem(str(row["Уверенность"])))
                    tbl.setItem(i, 4, QTableWidgetItem(str(row["Лифт"])))
            self.status_label.setText("✓ Сезонный анализ готов")
        except Exception as e:
            QMessageBox.critical(self, "❌", str(e))

    def _export_html_report(self):
        if self._rules is None or self._rules.empty:
            QMessageBox.warning(self, "⚠️", "Сначала постройте правила (вкладка Apriori)")
            return
        try:
            path = export_html_report(self._df, self._rules)
            self.html_label.setText(f"✅ Отчёт сохранён: {path}")
            self.status_label.setText("✓ HTML-отчёт готов")
            import webbrowser
            webbrowser.open(f"file:///{path.replace(os.sep, '/')}")
        except Exception as e:
            QMessageBox.critical(self, "❌", str(e))

    # ── Вспомогательные методы ────────────────────────────────────────────────

    def _fill_table(self, table: QTableWidget, df, columns: list):
        """Универсальное заполнение таблицы из DataFrame."""
        table.setRowCount(0)
        for i, (_, row) in enumerate(df.iterrows()):
            table.insertRow(i)
            for j, col in enumerate(columns):
                table.setItem(i, j, QTableWidgetItem(str(row[col])))

    def _update_stats(self):
        """Обновляет строку статистики в заголовке."""
        try:
            stats = get_stats(self._df)
            top3  = ", ".join(f"{item}({cnt})" for item, cnt in stats["топ_товары"])
            self.stats_label.setText(
                f"📊 Чеков: {len(self._df):,}  │  "
                f"Средний чек: {stats['средний_чек']} товаров  │  "
                f"Топ магазин: {stats['топ_магазин']} ({stats['топ_магазин_кол']} чеков)  │  "
                f"Топ товары: {top3}"
            )
        except Exception:
            pass


# ── Точка входа ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MBAApplication()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
