"""
Market Basket Analysis System
Тема 08 · Анализ рыночной корзины · Artificial Intelligence · E-Business 2025-2026
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich import box
from rich.rule import Rule

from database import load_dataset, add_transaction, delete_transaction, show_data, get_stats
from dataset import create_dataset, ITEMS, STORES, fuzzy_store, fuzzy_item
from model import (
    build_rules, build_rules_by_store, build_rules_by_year_range,
    save_rules, cache_rules, export_rules_excel,
    recommend, get_top_rules, get_business_recommendations,
    compare_algorithms, build_rules_by_season,
    MIN_SUPPORT, MIN_CONFIDENCE, RULES_FILE, RULES_CACHE,
)
from predict import save_recommendation, load_history, clear_history, init_history
from visualizer import generate_all_plots, export_html_report
from nlp_processor import find_command

import os
import pickle

console = Console()

# Глобальное состояние
_rules      = None
_df         = None
_support    = MIN_SUPPORT
_confidence = MIN_CONFIDENCE
_algorithm  = "apriori"   # 'apriori' | 'fpgrowth'


# ── Утилиты ───────────────────────────────────────────────────────────────────

def header():
    console.print()
    console.print(Panel(
        Text("Анализ Рыночной Корзины", justify="center", style="bold cyan"),
        subtitle="[dim]Apriori / FP-Growth · Retail Intelligence[/dim]",
        border_style="cyan", padding=(0, 4)
    ))


def show_menu():
    console.print()
    console.print(Rule(f"[bold cyan]МЕНЮ[/bold cyan]  "
                       f"[dim](алгоритм: {_algorithm.upper()}, "
                       f"support={_support}, confidence={_confidence})[/dim]",
                       style="cyan"))
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("№", style="bold cyan", width=4)
    t.add_column("", style="white")
    t.add_row("1",  "Показать чеки")
    t.add_row("2",  "Добавить чек")
    t.add_row("3",  "Удалить чек по ID")
    t.add_row("[dim]─[/dim]", "[dim]──────────────────────────────────────────[/dim]")
    t.add_row("4",  "Построить ассоциативные правила")
    t.add_row("5",  "Настроить параметры (support, confidence, алгоритм)")
    t.add_row("6",  "[green]Рекомендации для товара[/green]")
    t.add_row("7",  "[cyan]Топ-10 правил + бизнес-рекомендации[/cyan]")
    t.add_row("8",  "[yellow]Правила по магазину[/yellow]")
    t.add_row("9",  "Динамика правил по годам")
    t.add_row("10", "История рекомендаций")
    t.add_row("11", "Экспорт правил в Excel")
    t.add_row("[dim]─[/dim]", "[dim]──────────────────────────────────────────[/dim]")
    t.add_row("12", "Построить графики (8 штук)")
    t.add_row("13", "Пересоздать датасет")
    t.add_row("14", "[magenta]Сезонный анализ[/magenta]")
    t.add_row("15", "[blue]Экспорт HTML-отчёта[/blue]")
    t.add_row("[bold red]0[/bold red]", "[bold red]Выход[/bold red]")
    console.print(t)
    console.print(Rule(style="cyan"))


def rules_required() -> bool:
    if _rules is None or _rules.empty:
        console.print("  [yellow]⚠ Сначала постройте правила (пункт 4).[/yellow]")
        return False
    return True


def pick_item(prompt_text="  Введите номер или название товара") -> str | None:
    console.print("\n  [bold]Доступные товары:[/bold]")
    rows = [ITEMS[i:i+5] for i in range(0, len(ITEMS), 5)]
    for i, row in enumerate(rows):
        line = "   ".join(f"[cyan]{i*5+j+1:2}[/cyan]. {item}" for j, item in enumerate(row))
        console.print("  " + line)
    raw = Prompt.ask(prompt_text)
    try:
        return ITEMS[int(raw) - 1]
    except (ValueError, IndexError):
        result = fuzzy_item(raw)
        if result:
            console.print(f"  [dim]Распознано как: {result}[/dim]")
            return result
        console.print(f"  [yellow]Товар «{raw}» не найден.[/yellow]")
        return None


# ── Команды ───────────────────────────────────────────────────────────────────

def cmd_show():
    year_in  = Prompt.ask("  Год (Enter — все)", default="")
    store_in = Prompt.ask("  Магазин (Enter — все)", default="")
    year  = int(year_in) if year_in.strip() else None
    store = None
    if store_in.strip():
        store = fuzzy_store(store_in) or store_in
    df = show_data(year=year, store=store, n=25)
    if df.empty:
        console.print("  [yellow]Данных не найдено.[/yellow]")
        return
    t = Table(
        title=f"Чеки ({len(df)} записей)",
        box=box.ROUNDED, border_style="cyan",
        header_style="bold cyan", show_lines=False,
    )
    t.add_column("ID чека",  justify="right")
    t.add_column("Дата")
    t.add_column("Магазин")
    t.add_column("Кол-во",   justify="right")
    t.add_column("Состав",   max_width=55)
    for _, row in df.iterrows():
        t.add_row(
            str(row["ид_чека"]), str(row["дата"]),
            str(row["магазин"]), str(row["кол_товаров"]), str(row["состав"]),
        )
    console.print()
    console.print(t)


def cmd_add():
    global _df
    console.print("\n  [bold cyan]Новый чек:[/bold cyan]")
    try:
        # Дата с валидацией
        while True:
            date = Prompt.ask("  Дата (ГГГГ-ММ-ДД, например 2024-06-15)")
            parts = date.split("-")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                # Дополнительная проверка через datetime
                from datetime import datetime
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                    break
                except ValueError:
                    console.print("  [red]Несуществующая дата (например, 31 февраля). Попробуйте ещё.[/red]")
            else:
                console.print("  [red]Неверный формат. Пример: 2024-06-15[/red]")

        # Магазин с нечётким распознаванием
        console.print("  " + "  ".join(f"[cyan]{i+1}[/cyan]. {s}" for i, s in enumerate(STORES)))
        store_raw = Prompt.ask("  Магазин (номер или название)")
        try:
            store = STORES[int(store_raw) - 1]
        except (ValueError, IndexError):
            store = fuzzy_store(store_raw)
            if not store:
                console.print(f"  [yellow]Магазин «{store_raw}» не найден, использую {STORES[0]}.[/yellow]")
                store = STORES[0]
            else:
                console.print(f"  [dim]Распознано как: {store}[/dim]")

        # Товары с нечётким распознаванием
        console.print("  Доступные товары: " + ", ".join(ITEMS))
        console.print("  [dim](можно писать транслитом: moloko, hleb, syr и т.д.)[/dim]")
        items_raw = Prompt.ask("  Введите товары через запятую (минимум 2)")
        items   = []
        unknown = []
        for raw in items_raw.split(","):
            raw = raw.strip()
            if not raw:
                continue
            if raw in ITEMS:
                items.append(raw)
            else:
                matched = fuzzy_item(raw)
                if matched:
                    items.append(matched)
                    console.print(f"  [dim]«{raw}» → {matched}[/dim]")
                else:
                    unknown.append(raw)

        if unknown:
            console.print(f"  [yellow]Не распознаны: {', '.join(unknown)} — пропущены[/yellow]")

        # add_transaction сам бросит ValueError если < 2 товаров
        new_id = add_transaction(date, store, items)
        _df = load_dataset()
        console.print(Panel(
            f"[green]✓ Чек добавлен (ID: {new_id})[/green]\n"
            f"  [dim]Дата:[/dim] {date}  [dim]Магазин:[/dim] {store}\n"
            f"  [dim]Состав:[/dim] {', '.join(items)}",
            border_style="green", padding=(0, 2),
        ))
    except ValueError as e:
        console.print(f"  [red]❌ Ошибка валидации:[/red] {e}")
    except Exception as e:
        console.print(f"  [red]❌ Ошибка:[/red] {e}")


def cmd_delete():
    global _df
    try:
        tid = IntPrompt.ask("  ID чека для удаления")
        if Confirm.ask(f"  Удалить чек #{tid}?"):
            deleted = delete_transaction(tid)
            if deleted:
                _df = load_dataset()
                console.print(f"  [green]✓ Чек #{tid} удалён.[/green]")
            else:
                console.print(f"  [yellow]Чек #{tid} не найден.[/yellow]")
    except Exception as e:
        console.print(f"  [red]❌ Ошибка:[/red] {e}")


def cmd_train():
    global _rules, _df
    _df = load_dataset()
    console.print(f"\n  [dim]Чеков:[/dim]     [bold cyan]{len(_df):,}[/bold cyan]")
    console.print(f"  [dim]Алгоритм:[/dim]  [bold]{_algorithm.upper()}[/bold]")
    console.print(f"  [dim]Параметры:[/dim] support={_support}, confidence={_confidence}")

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Запускаю {_algorithm.upper()}..."),
        BarColumn(bar_width=30),
        console=console, transient=True,
    ) as p:
        task = p.add_task("", total=None)
        _rules = build_rules(_df, support=_support, confidence=_confidence, algorithm=_algorithm)
        p.update(task, completed=True)

    if _rules.empty:
        console.print("  [yellow]⚠ Правила не найдены. Снизьте min_support или min_confidence.[/yellow]")
        return

    save_rules(_rules)
    cache_rules(_rules)

    console.print(Panel(
        f"[green]✓ {_algorithm.upper()} завершён[/green]\n\n"
        f"  [dim]Найдено правил:[/dim]    [bold]{len(_rules)}[/bold]\n"
        f"  [dim]Макс. Лифт:[/dim]        [bold]{_rules['lift'].max():.4f}[/bold]\n"
        f"  [dim]Макс. Уверенность:[/dim] [bold]{_rules['confidence'].max():.4f}[/bold]\n\n"
        f"  [dim]💾 Сохранено → правила.csv + кэш[/dim]",
        title=f"[bold green]{_algorithm.upper()} — результат[/bold green]",
        border_style="green", padding=(0, 2),
    ))

    # Автоматическое сравнение алгоритмов
    console.print("\n  [dim]⚡ Сравниваю Apriori vs FP-Growth...[/dim]")
    with Progress(SpinnerColumn(), TextColumn("[cyan]Замер..."),
                  console=console, transient=True) as p:
        task = p.add_task("", total=None)
        cmp = compare_algorithms(_df, support=_support, confidence=_confidence)
        p.update(task, completed=True)

    t = Table(title="⚡ Сравнение алгоритмов", box=box.ROUNDED,
              border_style="cyan", header_style="bold cyan")
    t.add_column("Алгоритм",    style="bold")
    t.add_column("Время (сек)", justify="right")
    t.add_column("Правил",      justify="right")
    t.add_column("Макс. Lift",  justify="right", style="bold green")
    t.add_column("Макс. Conf",  justify="right")
    for r in cmp:
        t.add_row(r["algorithm"], str(r["time_sec"]),
                  str(r["rules_count"]), str(r["max_lift"]), str(r["max_confidence"]))
    console.print()
    console.print(t)


def cmd_params():
    global _support, _confidence, _algorithm
    console.print(
        f"\n  Текущие параметры:\n"
        f"  [dim]Алгоритм:[/dim]   [cyan]{_algorithm.upper()}[/cyan]\n"
        f"  [dim]Support:[/dim]    [cyan]{_support}[/cyan]\n"
        f"  [dim]Confidence:[/dim] [cyan]{_confidence}[/cyan]\n"
    )

    # Выбор алгоритма
    algo_raw = Prompt.ask(
        "  Алгоритм ([cyan]1[/cyan]=Apriori, [cyan]2[/cyan]=FP-Growth)",
        default="1" if _algorithm == "apriori" else "2",
    )
    if algo_raw.strip() == "2":
        _algorithm = "fpgrowth"
        console.print("  [dim]→ FP-Growth[/dim]")
    else:
        _algorithm = "apriori"
        console.print("  [dim]→ Apriori[/dim]")

    s_raw = Prompt.ask("  Мин. поддержка (0.01–0.30)", default=str(_support))
    c_raw = Prompt.ask("  Мин. уверенность (0.10–0.90)", default=str(_confidence))
    try:
        s = float(s_raw)
        c = float(c_raw)
        if 0.01 <= s <= 0.30 and 0.10 <= c <= 0.90:
            _support    = round(s, 3)
            _confidence = round(c, 3)
            console.print(f"  [green]✓ Параметры обновлены. Пересчитайте правила (пункт 4).[/green]")
        else:
            console.print("  [red]Значения вне допустимого диапазона.[/red]")
    except ValueError:
        console.print("  [red]Введите числа.[/red]")


def cmd_recommend():
    if not rules_required():
        return
    try:
        console.print("  [dim]Можно выбрать один или два товара для точной рекомендации[/dim]")
        item1 = pick_item("  Первый товар (номер или название)")
        if not item1:
            return

        item2_raw = Prompt.ask("  Второй товар (Enter — пропустить)", default="")
        items = [item1]
        if item2_raw.strip():
            if item2_raw.isdigit():
                try:
                    item2 = ITEMS[int(item2_raw) - 1]
                except IndexError:
                    item2 = None
            else:
                item2 = fuzzy_item(item2_raw.strip())
            if item2:
                items.append(item2)
                console.print(f"  [dim]Поиск по: {' + '.join(items)}[/dim]")

        recs = recommend(_rules, items, top_n=5)
        if recs.empty:
            console.print(f"  [yellow]Рекомендаций для «{' + '.join(items)}» не найдено.[/yellow]")
            return

        t = Table(
            title=f"Топ-5 к «{' + '.join(items)}»",
            box=box.ROUNDED, border_style="green", header_style="bold green",
        )
        t.add_column("Рекомендуемый товар", style="bold")
        t.add_column("Уверенность", justify="right")
        t.add_column("Лифт",        justify="right")
        t.add_column("Поддержка",   justify="right")
        for _, row in recs.iterrows():
            lc = "green" if row["Лифт"] >= 3 else "yellow" if row["Лифт"] >= 1.5 else "white"
            t.add_row(
                row["Товар"],
                f"{row['Уверенность']:.4f}",
                f"[{lc}]{row['Лифт']:.4f}[/{lc}]",
                f"{row['Поддержка']:.4f}",
            )
        console.print()
        console.print(t)
        save_recommendation(item1, recs)
        console.print("  [dim]💾 Сохранено в историю[/dim]")
    except Exception as e:
        console.print(f"  [red]❌ Ошибка:[/red] {e}")


def cmd_top_rules():
    if not rules_required():
        return
    top = get_top_rules(_rules, n=10)
    t = Table(
        title="Топ-10 ассоциативных правил (по Лифту)",
        box=box.ROUNDED, border_style="cyan", header_style="bold cyan",
    )
    t.add_column("Если куплено", style="bold")
    t.add_column("То купят")
    t.add_column("Поддержка",   justify="right")
    t.add_column("Уверенность", justify="right")
    t.add_column("Лифт",        justify="right", style="bold green")
    for _, row in top.iterrows():
        t.add_row(
            row["Если куплено"], row["То купят"],
            str(row["Поддержка"]), str(row["Уверенность"]), str(row["Лифт"]),
        )
    console.print()
    console.print(t)

    biz = get_business_recommendations(_rules, top_n=5)
    console.print()
    console.print(Panel(
        "\n".join(biz),
        title="[bold yellow]💡 Бизнес-рекомендации[/bold yellow]",
        border_style="yellow", padding=(0, 2),
    ))


def cmd_store_rules():
    if not rules_required():
        return
    console.print("\n  " + "  ".join(f"[cyan]{i+1}[/cyan]. {s}" for i, s in enumerate(STORES)))
    s_raw = Prompt.ask("  Магазин (номер или название)", default="1")
    try:
        store = STORES[int(s_raw) - 1]
    except (ValueError, IndexError):
        store = fuzzy_store(s_raw) or STORES[0]

    with Progress(
        SpinnerColumn(), TextColumn(f"[cyan]Анализирую {store}..."),
        console=console, transient=True,
    ) as p:
        task = p.add_task("", total=None)
        store_rules, err = build_rules_by_store(store, _df)
        p.update(task, completed=True)

    if err:
        console.print(f"  [yellow]{err}[/yellow]")
        return

    top = get_top_rules(store_rules, n=5)
    t = Table(
        title=f"Топ-5 правил — «{store}»",
        box=box.ROUNDED, border_style="yellow", header_style="bold yellow",
    )
    t.add_column("Если куплено", style="bold")
    t.add_column("То купят")
    t.add_column("Поддержка",   justify="right")
    t.add_column("Уверенность", justify="right")
    t.add_column("Лифт",        justify="right", style="bold green")
    for _, row in top.iterrows():
        t.add_row(
            row["Если куплено"], row["То купят"],
            str(row["Поддержка"]), str(row["Уверенность"]), str(row["Лифт"]),
        )
    console.print()
    console.print(t)


def cmd_year_dynamics():
    if not rules_required():
        return
    console.print("\n  [dim]Сравнение правил за два периода[/dim]")
    try:
        y1 = IntPrompt.ask("  Год начала периода 1", default=2015)
        y2 = IntPrompt.ask("  Год конца периода 1",  default=2019)
        y3 = IntPrompt.ask("  Год начала периода 2", default=2020)
        y4 = IntPrompt.ask("  Год конца периода 2",  default=2024)

        with Progress(
            SpinnerColumn(), TextColumn("[cyan]Анализирую..."),
            console=console, transient=True,
        ) as p:
            task = p.add_task("", total=None)
            r1, e1 = build_rules_by_year_range(_df, y1, y2)
            r2, e2 = build_rules_by_year_range(_df, y3, y4)
            p.update(task, completed=True)

        for label, rules, err in [(f"{y1}–{y2}", r1, e1), (f"{y3}–{y4}", r2, e2)]:
            if err:
                console.print(f"  [yellow]{label}: {err}[/yellow]")
                continue
            top = get_top_rules(rules, n=3)
            t = Table(
                title=f"Топ-3 правила за {label}",
                box=box.ROUNDED, border_style="cyan", header_style="bold cyan",
            )
            t.add_column("Если куплено", style="bold")
            t.add_column("То купят")
            t.add_column("Лифт", justify="right", style="bold green")
            for _, row in top.iterrows():
                t.add_row(row["Если куплено"], row["То купят"], str(row["Лифт"]))
            console.print()
            console.print(t)
    except Exception as e:
        console.print(f"  [red]❌ Ошибка:[/red] {e}")


def cmd_history():
    df = load_history(n=30)
    if df.empty:
        console.print("  [yellow]История пуста.[/yellow]")
        return
    t = Table(
        title=f"История рекомендаций ({len(df)} записей)",
        box=box.ROUNDED, border_style="cyan", header_style="bold cyan",
    )
    col_ru = {
        "дата_запроса": "Дата", "товар": "Товар",
        "рекомендован": "Рекомендован", "уверенность": "Уверенность", "лифт": "Лифт",
    }
    for col in df.columns:
        t.add_column(col_ru.get(col, col))
    for _, row in df.iterrows():
        t.add_row(*[str(v) for v in row])
    console.print()
    console.print(t)
    if Confirm.ask("\n  Очистить историю?", default=False):
        clear_history()
        console.print("  [green]✓ История очищена.[/green]")


def cmd_export_excel():
    if not rules_required():
        return
    with P4rogress(
        SpinnerColumn(), TextColumn("[cyan]Экспортирую в Excel..."),
        console=console, transient=True,
    ) as p:
        task = p.add_task("", total=None)
        path = export_rules_excel(_rules)
        p.update(task, completed=True)
    console.print(Panel(
        f"[green]✓ Экспорт завершён → [bold]{path}[/bold][/green]",
        border_style="green", padding=(0, 2),
    ))


def cmd_plots():
    global _df
    if not rules_required():
        return
    if _df is None:
        _df = load_dataset()
    with Progress(
        SpinnerColumn(), TextColumn("[cyan]Генерирую 8 графиков..."),
        console=console, transient=True,
    ) as p:
        task = p.add_task("", total=None)
        generate_all_plots(_df, _rules)
        p.update(task, completed=True)
    console.print(Panel(
        "[green]✓ Графики сохранены в папку [bold]./plots/[/bold][/green]\n\n"
        "  [dim]1_top_rules_lift.png[/dim]\n"
        "  [dim]2_cooccurrence_heatmap.png[/dim]\n"
        "  [dim]3_item_frequency.png[/dim]\n"
        "  [dim]4_support_confidence.png[/dim]\n"
        "  [dim]5_top_confidence.png[/dim]\n"
        "  [dim]6_store_lift.png[/dim]\n"
        "  [dim]7_wordcloud.png[/dim]\n"
        "  [dim]8_support_vs_rules.png[/dim]",
        border_style="green", padding=(0, 2),
    ))


def cmd_seasonal():
    global _df
    if _df is None:
        _df = load_dataset()
    SEASON_ICONS = {"Зима": "❄️", "Весна": "🌸", "Лето": "☀️", "Осень": "🍂"}
    console.print("\n  [dim]Строю правила по сезонам...[/dim]")
    with Progress(SpinnerColumn(), TextColumn("[cyan]Сезонный анализ..."),
                  console=console, transient=True) as p:
        task = p.add_task("", total=None)
        seasons = build_rules_by_season(_df)
        p.update(task, completed=True)

    if not seasons:
        console.print("  [yellow]⚠ Недостаточно данных для сезонного анализа.[/yellow]")
        return

    for season, top in seasons.items():
        icon = SEASON_ICONS.get(season, "")
        t = Table(
            title=f"{icon} {season} — топ-3 правила",
            box=box.ROUNDED, border_style="magenta", header_style="bold magenta",
        )
        t.add_column("Если куплено", style="bold")
        t.add_column("То купят")
        t.add_column("Поддержка",   justify="right")
        t.add_column("Уверенность", justify="right")
        t.add_column("Лифт",        justify="right", style="bold green")
        for _, row in top.iterrows():
            t.add_row(row["Если куплено"], row["То купят"],
                      str(row["Поддержка"]), str(row["Уверенность"]), str(row["Лифт"]))
        console.print()
        console.print(t)


def cmd_html_report():
    if not rules_required():
        return
    global _df
    if _df is None:
        _df = load_dataset()
    with Progress(SpinnerColumn(), TextColumn("[cyan]Генерирую HTML-отчёт..."),
                  console=console, transient=True) as p:
        task = p.add_task("", total=None)
        path = export_html_report(_df, _rules)
        p.update(task, completed=True)
    console.print(Panel(
        f"[green]✓ HTML-отчёт готов → [bold]{path}[/bold][/green]",
        border_style="green", padding=(0, 2),
    ))
    import webbrowser
    webbrowser.open(f"file:///{path.replace(os.sep, '/')}")


def cmd_recreate():
    global _rules, _df
    if Confirm.ask("  Пересоздать датасет? Текущие данные будут удалены", default=False):
        with Progress(
            SpinnerColumn(), TextColumn("[cyan]Генерирую датасет..."),
            console=console, transient=True,
        ) as p:
            task = p.add_task("", total=None)
            create_dataset(force=True)
            _rules = None
            _df    = load_dataset()
            p.update(task, completed=True)
        console.print("  [green]✓ Готово. Пересчитайте правила (пункт 4).[/green]")


# ── Запуск ────────────────────────────────────────────────────────────────────

def startup():
    global _rules, _df
    header()
    init_history()
    _df = load_dataset()

    stats = get_stats(_df)
    top3  = "  ".join(f"[cyan]{item}[/cyan] ({cnt})" for item, cnt in stats["топ_товары"])
    console.print(
        f"\n  [dim]Чеков:[/dim]       [bold cyan]{len(_df):,}[/bold cyan]"
        f" [dim]({_df['год'].min()}–{_df['год'].max()})[/dim]\n"
        f"  [dim]Средний чек:[/dim] [bold]{stats['средний_чек']} товара[/bold]\n"
        f"  [dim]Топ магазин:[/dim] [bold]{stats['топ_магазин']}[/bold] ({stats['топ_магазин_кол']} чеков)\n"
        f"  [dim]Топ товары:[/dim]  {top3}"
    )

    if os.path.exists(RULES_CACHE):
        with Progress(
            SpinnerColumn(), TextColumn("[cyan]Загружаю кэш правил..."),
            console=console, transient=True,
        ) as p:
            task = p.add_task("", total=None)
            with open(RULES_CACHE, "rb") as f:
                _rules = pickle.load(f)
            p.update(task, completed=True)
        console.print(f"  [green]✓ Правила загружены из кэша ({len(_rules)} шт.)[/green]")
    elif os.path.exists(RULES_FILE):
        console.print("  [dim]Правила есть в CSV, но кэш не найден — пересчитываю...[/dim]")
        _rules = build_rules(_df)
        cache_rules(_rules)
        console.print(f"  [green]✓ Правила готовы ({len(_rules)} шт.)[/green]")
    else:
        console.print("  [dim]Правила не построены — выберите пункт 4[/dim]")


def main():
    startup()

    DISPATCH = {
        "1":  cmd_show,
        "2":  cmd_add,
        "3":  cmd_delete,
        "4":  cmd_train,
        "5":  cmd_params,
        "6":  cmd_recommend,
        "7":  cmd_top_rules,
        "8":  cmd_store_rules,
        "9":  cmd_year_dynamics,
        "10": cmd_history,
        "11": cmd_export_excel,
        "12": cmd_plots,
        "13": cmd_recreate,
        "14": cmd_seasonal,
        "15": cmd_html_report,
    }
    NLP_MAP = {
        "recommend": "6",  "rules":   "7",  "add":    "2",
        "show":      "1",  "delete":  "3",  "plot":   "12",
        "history":   "10", "train":   "4",  "exit":   "0",
        "season":    "14", "html":    "15",
    }

    while True:
        show_menu()
        raw = Prompt.ask("[bold cyan]Команда[/bold cyan]").strip()

        if not raw.isdigit():
            intent = find_command(raw)
            raw    = NLP_MAP.get(intent, raw)

        if raw in ("0", "выход", "exit", "quit"):
            console.print(Panel(
                "[bold cyan]До свидания! 👋[/bold cyan]",
                border_style="cyan", padding=(0, 4),
            ))
            break

        action = DISPATCH.get(raw)
        if action:
            console.print()
            action()
        else:
            console.print("  [yellow]❓ Команда не распознана.[/yellow]")


if __name__ == "__main__":
    main()
