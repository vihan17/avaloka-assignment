"""Build Vihan_Chorada_Avaloka_Assignment.pdf from build/template.html.

The script runs the test suite, the demo and the benchmark, injects their real
output plus the real source files into the template, renders it with headless
Chrome, then stamps page numbers onto every page.

Usage:  python build_report.py
"""

from __future__ import annotations

import ast
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
TEMPLATE = BUILD / "template.html"
OUT_PDF = ROOT / "Vihan_Chorada_Avaloka_Assignment.pdf"
MAIN_PDF = BUILD / "_main.pdf"
OVERLAY_PDF = BUILD / "_overlay.pdf"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

FOOTER_LEFT = "Vihan Chorada  ·  Avaloka take-home"
PYGMENTS = HtmlFormatter(style="friendly")


# ----------------------------------------------------------------------
# Source and output collection
# ----------------------------------------------------------------------
def source_block(relative: str) -> str:
    text = (ROOT / relative).read_text(encoding="utf-8").rstrip("\n")
    return highlight(text, PythonLexer(), PYGMENTS)


def definition_block(relative: str, name: str) -> str:
    """Extract one class/function from a module, with its real indentation."""
    source = (ROOT / relative).read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return highlight(
                "\n".join(lines[node.lineno - 1:node.end_lineno]),
                PythonLexer(),
                PYGMENTS,
            )
    raise LookupError(f"{name} not found in {relative}")


def run(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return (result.stdout + result.stderr).strip()


def test_count(pytest_output: str) -> str:
    match = re.search(r"(\d+) passed", pytest_output)
    if not match:
        raise RuntimeError(f"could not parse pytest output:\n{pytest_output}")
    return match.group(1)


def benchmark_numbers(output: str) -> dict[str, str]:
    """Lift the measured values out of the benchmark output.

    The prose quotes these exact numbers, so they are injected from the same
    run that appears in the appendix instead of being typed twice.
    """
    def grab(pattern: str, group: int = 1) -> str:
        match = re.search(pattern, output)
        if not match:
            raise ValueError(f"benchmark output lacks /{pattern}/:\n{output}")
        return match.group(group)

    return {
        "{{B_OPS}}": grab(r"([\d,]+) mixed operations"),
        "{{B_TIME}}": grab(r"mixed operations\s+([\d.]+) s"),
        "{{B_RATE}}": grab(r"mixed operations\s+[\d.]+ s\s+([\d.]+) M ops/s"),
        "{{B_BYTES}}": grab(r"live entries\s+(\d+) bytes/entry"),
        "{{B_NS1}}": grab(r"capacity 100\s+(\d+) ns/op"),
        "{{B_NS2}}": grab(r"capacity 10,000\s+(\d+) ns/op"),
        "{{B_NS3}}": grab(r"capacity 200,000\s+(\d+) ns/op"),
        "{{B_S1}}": grab(r"can_attend_all\s+([\d.]+) s"),
        "{{B_S2}}": grab(r"min_rooms_required\s+([\d.]+) s"),
        "{{B_S3}}": grab(r"assign_rooms\s+([\d.]+) s"),
        "{{B_ROOMS}}": grab(r"min_rooms_required\s+[\d.]+ s\s+(\d+) rooms"),
    }


# ----------------------------------------------------------------------
# Table of contents
# ----------------------------------------------------------------------
HEADING = re.compile(r"<h([23])[^>]*data-title=\"([^\"]+)\"[^>]*>(.*?)</h\1>", re.S)
NUMBER = re.compile(r"^([0-9]+(?:\.[0-9]+)?)")


def headings(markup: str) -> list[dict[str, str]]:
    found = []
    for level, title, inner in HEADING.findall(markup):
        title = html.unescape(title)
        if level == "2":
            span = re.search(r'<span class="num">(.*?)</span>', inner, re.S)
            if not span:
                raise ValueError(f"level-2 heading without number: {title}")
            num = re.sub(r"<[^>]+>", "", span.group(1))
            num = html.unescape(num).replace("Section ", "").strip()
        else:
            text = re.sub(r"<[^>]+>", "", inner)
            match = NUMBER.match(html.unescape(text).strip())
            if not match:
                raise ValueError(f"heading without number: {title}")
            num = match.group(1)
        found.append({"level": level, "num": num, "title": title})
    return found


def render_toc(entries: list[dict[str, str]], pages: dict[str, str]) -> str:
    rows = []
    for entry in entries:
        page = pages.get(entry["title"], "–")
        rows.append(
            f'<li class="lvl{entry["level"]}">'
            f'<span class="toc-num">{entry["num"]}</span>'
            f'<span class="toc-title">{html.escape(entry["title"])}</span>'
            f'<span class="dots"></span>'
            f'<span class="toc-page">{page}</span></li>'
        )
    return '<ul class="toc">\n' + "\n".join(rows) + "\n</ul>"


def normalise(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip()


def locate_pages(pdf_path: Path, entries: list[dict[str, str]]) -> dict[str, str]:
    reader = PdfReader(str(pdf_path))
    texts = [normalise(page.extract_text() or "") for page in reader.pages]
    pages: dict[str, str] = {}
    for entry in entries:
        needle = normalise(entry["title"])
        for index in range(2, len(texts)):        # skip cover and contents
            if needle in texts[index]:
                pages[entry["title"]] = str(index + 1)
                break
        else:
            print(f"  ! heading not found: {entry['title']}")
    return pages


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def find_chrome() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome or Edge not found")


def to_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = find_chrome()
    profile = BUILD / "_chrome_profile"
    shutil.rmtree(profile, ignore_errors=True)
    args = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        "--virtual-time-budget=8000",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if not pdf_path.exists():
        raise RuntimeError(f"PDF not produced:\n{result.stdout}\n{result.stderr}")
    if pdf_path.stat().st_size < 10_000:
        raise RuntimeError(f"PDF suspiciously small: {pdf_path.stat().st_size} bytes")


def stamp_footers(pdf_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    pages_html = []
    for number in range(1, total + 1):
        pages_html.append(
            '<div class="page"><div class="foot">'
            f"<span>{html.escape(FOOTER_LEFT)}</span>"
            f"<span>{number} / {total}</span>"
            "</div></div>"
        )

    overlay_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0; }}
html, body {{ margin: 0; padding: 0; }}
.page {{ width: 210mm; height: 297mm; position: relative; }}
.page + .page {{ break-before: page; }}
.foot {{
  position: absolute; left: 17mm; right: 17mm; bottom: 8.5mm;
  display: flex; justify-content: space-between;
  font-family: "Segoe UI", sans-serif; font-size: 7.4pt; color: #8b979c;
  letter-spacing: 0.03em;
}}
</style></head><body>
{''.join(pages_html)}
</body></html>"""

    overlay_source = BUILD / "_overlay.html"
    overlay_source.write_text(overlay_html, encoding="utf-8")
    to_pdf(overlay_source, OVERLAY_PDF)

    overlay = PdfReader(str(OVERLAY_PDF))
    if len(overlay.pages) != total:
        raise RuntimeError(
            f"overlay has {len(overlay.pages)} pages, document has {total}"
        )

    writer = PdfWriter()
    for page, layer in zip(reader.pages, overlay.pages):
        page.merge_page(layer)
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": "Data Structures & Systems Design — Avaloka take-home",
            "/Author": "Vihan Chorada",
            "/Subject": "O(1) LRU cache and interval-based event scheduler",
            "/Keywords": "LRU cache, doubly linked list, interval scheduling, heap, concurrency",
        }
    )
    with OUT_PDF.open("wb") as handle:
        writer.write(handle)


def main() -> None:
    print("Collecting evidence ...")
    pytest_output = run(["-m", "pytest", "tests", "-q"])
    demo_output = run(["demo.py"])
    bench_output = run(["benchmark.py"])
    tests = test_count(pytest_output)
    print(f"  {tests} tests passed")

    # The demo is two logical halves; keeping them in separate blocks stops a
    # page break from stranding the "can_attend_all" heading on its own.
    if "\ncan_attend_all\n" not in demo_output:
        raise RuntimeError("demo output did not contain the scheduler section")
    demo_cache, demo_sched = demo_output.split("\ncan_attend_all\n", 1)
    demo_sched = "can_attend_all\n" + demo_sched

    template = TEMPLATE.read_text(encoding="utf-8")
    entries = headings(template)

    replacements = {
        "{{CODE_LRU}}": source_block("lru_cache.py"),
        "{{CODE_SCHED}}": source_block("event_scheduler.py"),
        "{{CODE_ASSIGN}}": definition_block("event_scheduler.py", "assign_rooms"),
        "{{CODE_LOCK}}": definition_block("thread_safe.py", "ThreadSafeLRUCache"),
        "{{TEST_COUNT}}": tests,
        "{{OUT_DEMO_CACHE}}": html.escape(demo_cache.strip()),
        "{{OUT_DEMO_SCHED}}": html.escape(demo_sched.strip()),
        "{{OUT_TESTS}}": html.escape(pytest_output),
        "{{OUT_BENCH}}": html.escape(bench_output),
    }
    replacements.update(benchmark_numbers(bench_output))

    page_numbers: dict[str, str] = {}
    for attempt in range(4):
        markup = template
        for token, value in replacements.items():
            if token not in markup:
                raise KeyError(f"template is missing {token}")
            markup = markup.replace(token, value)
        markup = markup.replace("{{TOC}}", render_toc(entries, page_numbers))
        if "{{" in markup:
            raise ValueError("unresolved placeholder in template")

        html_path = BUILD / "report.html"
        html_path.write_text(markup, encoding="utf-8")
        print(f"Rendering PDF (pass {attempt + 1}) ...")
        to_pdf(html_path, MAIN_PDF)

        located = locate_pages(MAIN_PDF, entries)
        if located == page_numbers:
            break
        page_numbers = located
    else:
        print("  ! page numbers did not stabilise; keeping the last pass")

    missing = [entry["title"] for entry in entries if entry["title"] not in page_numbers]
    if missing:
        print(f"  ! no page number for: {missing}")

    print("Stamping footers ...")
    stamp_footers(MAIN_PDF)

    final = PdfReader(str(OUT_PDF))
    print(f"Wrote {OUT_PDF.name}: {len(final.pages)} pages, "
          f"{OUT_PDF.stat().st_size / 1024:.0f} KB")

    first = normalise(final.pages[0].extract_text() or "")
    last = normalise(final.pages[-1].extract_text() or "")
    assert "Vihan Chorada" in first
    assert "pytest" in normalise(final.pages[-2].extract_text() or "") or "passed" in last


if __name__ == "__main__":
    main()
