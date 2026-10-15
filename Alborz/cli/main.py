import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from Alborz.core.extractor import extract_metadata
from Alborz.core.formatters import (
    to_json, to_csv, to_html, humanize_value, dedup_entries,
)

app = typer.Typer(
    help="Alborz - استخراج متادیتا از فایل‌ها",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main():
    """Alborz - استخراج متادیتا از فایل‌ها"""
    pass


# ---------- تگ‌های مهم برای خلاصه ----------
SUMMARY_TAGS = {
    "مدل دستگاه":     ["Model"],
    "سازنده":         ["Make"],
    "نرم‌افزار":       ["Software"],
    "لنز":            ["LensModel", "Lens"],
    "ساعت ضبط":       ["DateTimeOriginal", "DateTimeDigitized", "DateTime"],
    "آخرین تغییر":    ["DateTime"],
    "ISO":            ["ISOSpeedRatings", "PhotographicSensitivity"],
    "دیافراگم":       ["FNumber", "ApertureValue"],
    "سرعت شاتر":      ["ExposureTime", "ShutterSpeedValue"],
    "فاصله کانونی":   ["FocalLength"],
    "فلاش":           ["Flash"],
    "حالت نوردهی":    ["ExposureProgram", "ExposureMode"],
    "رزولوشن":        ["ExifImageWidth", "ImageWidth",
                       "ExifImageHeight", "ImageHeight"],
    "طول جغرافیایی":  ["DecimalLongitude"],
    "عرض جغرافیایی":  ["DecimalLatitude"],
    "ارتفاع":         ["GPSAltitude"],
}


# ---------- توابع کمکی ----------

def _find_value(entries, tags):
    """اولین مقدار موجود از لیست تگ‌ها رو برمی‌گردونه"""
    for tag in tags:
        for e in entries:
            if e.tag.lower() == tag.lower():
                return e.value, e.group
    return None, None


def _build_summary(result):
    """ساخت خلاصه از تگ‌های مهم با ترجمه مقادیر"""
    rows = []
    for label, tags in SUMMARY_TAGS.items():
        value, group = _find_value(result.entries, tags)
        if value is not None and str(value).strip() not in ("", "None"):
            v = str(humanize_value(tags[0], value)).strip()
            if len(v) > 60:
                v = v[:57] + "..."
            rows.append((label, v))
    return rows


def _print_summary(result):
    """نمایش خلاصه مهم + اطلاعات فایل"""
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📄 {result.filename}[/bold cyan]\n"
        f"[dim]حجم:[/dim] {result.filesize:,} بایت   "
        f"[dim]نوع:[/dim] {result.mime_type}",
        border_style="cyan",
    ))

    summary = _build_summary(result)
    if summary:
        table = Table(
            title="📌 خلاصه اطلاعات مهم",
            title_style="bold yellow",
            show_header=False,
            box=None,
            padding=(0, 2),
        )
        table.add_column("کلید", style="yellow", no_wrap=True)
        table.add_column("مقدار", style="white")
        for label, value in summary:
            table.add_row(f"{label}:", value)
        console.print(table)
    else:
        console.print("[yellow]⚠️ این فایل متادیتای مهمی ندارد[/yellow]")


def _print_full_table(result):
    """نمایش جدول کامل تگ‌ها بدون تکراری"""
    deduped = dedup_entries(result.entries)

    if not deduped:
        return

    console.print()
    table = Table(title="📋 تمام تگ‌ها", title_style="bold cyan", show_lines=False)
    table.add_column("گروه", style="cyan", no_wrap=True)
    table.add_column("تگ", style="yellow")
    table.add_column("مقدار", style="white")

    for e in deduped:
        v = str(humanize_value(e.tag, e.value))
        if len(v) > 80:
            v = v[:77] + "..."
        table.add_row(e.group, e.tag, v)

    console.print(table)


# ---------- دستور اصلی ----------

@app.command("extract")
def extract_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True, help="مسیر فایل"),
    output: str = typer.Option(
        "table", "--format", "-f",
        help="فرمت خروجی: table, json, csv, html",
    ),
    save: Path = typer.Option(None, "--save", "-s", help="ذخیره خروجی در فایل"),
    filter: str = typer.Option(None, "--filter", help="فیلتر بر اساس تگ (مثلاً Model)"),
    summary_only: bool = typer.Option(
        False, "--summary", "-S", help="فقط خلاصه مهم را نشان بده"
    ),
    no_summary: bool = typer.Option(
        False, "--no-summary", help="خلاصه را نشان نده"
    ),
):
    """استخراج متادیتا از یک فایل"""
    with console.status("[cyan]در حال پردازش..."):
        result = extract_metadata(str(file))

    if filter:
        result.entries = [
            e for e in result.entries if filter.lower() in e.tag.lower()
        ]

    # ---------- خروجی‌های فایلی ----------
    if output == "json":
        text = to_json(result)
    elif output == "csv":
        text = to_csv(result)
    elif output == "html":
        text = to_html(result)
    else:
        # حالت table (پیش‌فرض)
        if not no_summary:
            _print_summary(result)
        if not summary_only:
            _print_full_table(result)
        return

    # ذخیره یا چاپ
    if save:
        save.write_text(text, encoding="utf-8")
        console.print(f"[green]✓ ذخیره شد در {save}[/green]")
    else:
        console.print(text)


# ---------- دستور Strip ----------

@app.command("strip")
def strip_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True, help="مسیر فایل"),
    output: Path = typer.Option(None, "--output", "-o",
                                 help="مسیر فایل خروجی (پیش‌فرض: نام اصلی + _clean)"),
    keep: str = typer.Option(None, "--keep", "-k",
                              help="گروه‌هایی که حفظ شوند (با کاما): EXIF,GPS"),
):
    """حذف متادیتا از یک فایل"""
    from Alborz.core.editor import strip_metadata

    if output is None:
        output = file.with_name(f"{file.stem}_clean{file.suffix}")

    keep_groups = None
    if keep:
        keep_groups = {g.strip().upper() for g in keep.split(",")}

    with console.status("[cyan]در حال حذف متادیتا..."):
        try:
            result_path = strip_metadata(str(file), str(output), keep_groups)
        except Exception as e:
            console.print(f"[red]✗ خطا: {e}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]✓ فایل پاک‌شده ذخیره شد:[/green] {result_path}")


# ---------- دستور Score ----------

@app.command("score")
def score_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True, help="مسیر فایل"),
):
    """محاسبه امتیاز حریم خصوصی فایل"""
    from Alborz.core.editor import compute_privacy_score

    with console.status("[cyan]در حال تحلیل..."):
        result = extract_metadata(str(file))
        score = compute_privacy_score(result.entries)

    color = score["color"]
    emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[color]

    console.print()
    console.print(Panel.fit(
        f"[bold]امتیاز حریم خصوصی:[/bold] "
        f"[bold {color}]{emoji} {score['score']}/100 ({score['label']})[/bold {color}]",
        title=f"📄 {result.filename}",
        border_style=color,
    ))

    if score["risks"]:
        console.print("\n[bold yellow]⚠️  خطرات شناسایی‌شده:[/bold yellow]")
        for r in score["risks"]:
            icon = "🔴" if r["level"] == "high" else "🟡"
            console.print(f"  {icon} [bold]{r['label']}[/bold] — {r['detail']}")
    else:
        console.print("\n[green]✓ خطر خاصی یافت نشد[/green]")

    console.print()
    console.print("[dim]راهنما: برای پاکسازی، دستور زیر را اجرا کن:[/dim]")
    console.print(f"[cyan]  python -m Alborz.cli.main strip {file.name}[/cyan]")
    console.print()


if __name__ == "__main__":
    app()