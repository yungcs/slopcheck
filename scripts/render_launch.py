"""Render the launch hero, GIF, report shot, before/after, and social card."""

from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from slopcheck.config import Config
from slopcheck.engine import scan
from slopcheck.formatters.prompt import render_prompt
from slopcheck.globs import relative
from slopcheck.score import score_bar
from slopcheck.version import __version__

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MONO = Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf")
MONO_BOLD = Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf")
SANS = Path("/usr/share/fonts/truetype/macos/Inter-Regular.ttf")
SANS_MED = Path("/usr/share/fonts/truetype/macos/Inter-Medium.ttf")
SANS_SEMI = Path("/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf")
TAGLINE = "A linter for the mess AI agents leave in Python"
REPO = "github.com/yonguyungcs-pixel/slopcheck"

INK = "#14160f"
PAPER = "#f3f0e6"
PAPER_DEEP = "#e7e1d4"
LIME = "#c6f35a"
LIME_INK = "#31470c"
EMBER = "#ff7a32"
RED = "#ff5c39"
GREEN = "#8fdf4a"
MUTED_DARK = "#a8b09d"
MUTED_LIGHT = "#5e6556"
NIGHT = "#10140f"
NIGHT_CARD = "#181d14"
TERM = "#12160f"
TERM_BAR = "#1c2218"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def text_width(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), value, font=face)
    return box[2] - box[0]


def draw_mark(draw: ImageDraw.ImageDraw, origin: tuple[int, int], size: int, *, plate: str, tick: str) -> None:
    x, y = origin
    draw.rounded_rectangle((x, y, x + size, y + size), radius=int(size * 0.24), fill=plate)
    width = max(4, size // 9)
    draw.line(
        [
            (x + size * 0.24, y + size * 0.52),
            (x + size * 0.42, y + size * 0.70),
            (x + size * 0.76, y + size * 0.32),
        ],
        fill=tick,
        width=width,
        joint="curve",
    )
    radius = size * 0.13
    cx = x + size - radius * 0.15
    cy = y + size - radius * 0.15
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=EMBER)


def hero(path: Path, *, dark: bool) -> None:
    image = Image.new("RGB", (1600, 560), NIGHT if dark else PAPER)
    draw = ImageDraw.Draw(image)
    ink = "#f4f6ef" if dark else INK
    muted = MUTED_DARK if dark else MUTED_LIGHT
    plate = LIME if dark else INK
    tick = INK if dark else LIME
    mark = 92
    word = font(SANS_SEMI, 84)
    sub = font(SANS, 32)
    chip_face = font(SANS_MED, 26)
    label = "slopcheck"
    label_w = text_width(draw, label, word)
    row_w = mark + 28 + label_w
    left = (1600 - row_w) // 2
    top = 128
    draw_mark(draw, (left, top), mark, plate=plate, tick=tick)
    draw.text((left + mark + 28, top + 4), label, font=word, fill=ink)
    sub_w = text_width(draw, TAGLINE, sub)
    draw.text(((1600 - sub_w) // 2, top + mark + 36), TAGLINE, font=sub, fill=muted)
    chips = [("29", "sloppy", EMBER), ("94", "clean", LIME if dark else LIME_INK)]
    chip_gap = 28
    chip_w = 210
    total = chip_w * 2 + 56
    chip_x = (1600 - total) // 2
    chip_y = 430
    for score, name, color in chips:
        draw.rounded_rectangle(
            (chip_x, chip_y, chip_x + chip_w, chip_y + 64),
            radius=32,
            fill=NIGHT_CARD if dark else "#fffdf8",
            outline=color,
            width=2,
        )
        caption = f"{score}  {name}"
        caption_w = text_width(draw, caption, chip_face)
        draw.text((chip_x + (chip_w - caption_w) // 2, chip_y + 16), caption, font=chip_face, fill=color)
        chip_x += chip_w + chip_gap
        if score == "29":
            arrow = font(SANS_MED, 28)
            draw.text((chip_x - chip_gap + 8, chip_y + 16), "→", font=arrow, fill=muted)
    image.save(path, "PNG", optimize=True)


def social(path: Path) -> None:
    image = Image.new("RGB", (1280, 640), NIGHT)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 8), fill=LIME)
    draw_mark(draw, (72, 86), 88, plate=LIME, tick=INK)
    draw.text((184, 86), "slopcheck", font=font(SANS_SEMI, 72), fill="#f4f6ef")
    draw.text((76, 210), TAGLINE, font=font(SANS, 32), fill=MUTED_DARK)
    draw.text((76, 560), REPO, font=font(MONO, 22), fill="#6f7864")
    card = (700, 150, 1188, 520)
    draw.rounded_rectangle(card, radius=18, fill=TERM, outline="#2a3324", width=2)
    draw.rounded_rectangle((700, 150, 1188, 198), radius=18, fill=TERM_BAR)
    draw.rectangle((700, 180, 1188, 198), fill=TERM_BAR)
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        cx = 732 + index * 28
        draw.ellipse((cx, 166, cx + 14, 180), fill=color)
    body = font(MONO, 24)
    bold = font(MONO_BOLD, 28)
    rows = [
        (188, [("$ ", LIME), ("uvx slopcheck demo", "#f4f6ef")]),
        (236, [("score  ", "#f4f6ef"), ("29", RED), ("  sloppy", EMBER)]),
        (300, [("$ ", LIME), ("slopcheck demo", "#f4f6ef")]),
        (348, [("score  ", "#f4f6ef"), ("94", GREEN), ("  clean", LIME)]),
    ]
    for y, spans in rows:
        x = 732
        face = bold if any(part in {"29", "94"} for part, _color in spans) else body
        for part, color in spans:
            draw.text((x, y), part, font=face, fill=color)
            x += int(face.getlength(part))
    image.save(path, "PNG", optimize=True)


def _paint(line: str, *, comment: str = "#8b9384") -> list[tuple[str, str]]:
    if line.strip().startswith("#"):
        return [(line, comment)]
    keywords = {"def", "try", "except", "return", "pass", "import", "from", "raise", "for", "if", "in"}
    spans: list[tuple[str, str]] = []
    token = ""
    quote: str | None = None

    def flush(color: str) -> None:
        nonlocal token
        if token:
            spans.append((token, color))
            token = ""

    for char in line:
        if quote:
            token += char
            if char == quote:
                flush("#e6c07b")
                quote = None
            continue
        if char in {"'", '"'}:
            flush("#d7decc")
            quote = char
            token = char
            continue
        if char.isalnum() or char == "_":
            token += char
            continue
        color = "#c6f35a" if token in keywords else "#d7decc"
        flush(color)
        spans.append((char, "#8b9384" if char in "():," else "#d7decc"))
    if token:
        spans.append((token, "#e6c07b" if quote else ("#c6f35a" if token in keywords else "#d7decc")))
    return spans or [(" ", "#d7decc")]


def before_after(path: Path) -> None:
    image = Image.new("RGB", (1440, 900), NIGHT)
    draw = ImageDraw.Draw(image)
    draw.text((56, 36), "Before", font=font(SANS_SEMI, 28), fill=EMBER)
    draw.text((760, 36), "After", font=font(SANS_SEMI, 28), fill=LIME)
    pairs = [
        (
            "SLP001  bare except",
            ["def fetch_tasks(raw):", "    try:", "        return json.loads(raw)", "    except:", "        pass"],
            ["def fetch_tasks(raw):", "    try:", "        return json.loads(raw)", "    except json.JSONDecodeError:", "        raise"],
        ),
        (
            "SLP010  hallucinated import",
            ["import requets", "from jason import loads"],
            ["import json", "from collections import defaultdict"],
        ),
        (
            "SLP013  versioned name",
            ["def summarize_tasks_v2(tasks, limit):", "    rows = []", "    index = 0", "    for task in tasks:"],
            ["def summarize_tasks(tasks, limit):", "    rows = []", "    index = 0", "    for task in tasks:"],
        ),
    ]
    code_font = font(MONO, 22)
    label_font = font(SANS_MED, 18)
    y = 96
    for label, left_lines, right_lines in pairs:
        for x, lines in ((48, left_lines), (752, right_lines)):
            height = 36 + 34 * len(lines)
            draw.rounded_rectangle((x, y, x + 640, y + height + 28), radius=16, fill=NIGHT_CARD)
            draw.text((x + 20, y + 14), label, font=label_font, fill=MUTED_DARK)
            cursor_y = y + 46
            for line in lines:
                cursor_x = x + 20
                for part, color in _paint(line):
                    draw.text((cursor_x, cursor_y), part, font=code_font, fill=color)
                    cursor_x += int(code_font.getlength(part))
                cursor_y += 34
        y += 250
    image.save(path, "PNG", optimize=True)


def _client() -> str:
    return '''"""Task fetch."""

from __future__ import annotations

import json


def fetch_tasks(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise


def task_id(payload):
    try:
        return payload["id"]
    except KeyError:
        raise


def fetch_title(task):
    title = task.get("title")
    if title == "":
        raise ValueError("missing title")
    return str(title)
'''


def _imports() -> str:
    return '''"""Grouping helpers."""

from __future__ import annotations

import json
from collections import defaultdict


def loads_user(raw):
    return json.loads(raw)


def group_tasks(tasks):
    grouped = defaultdict(list)
    for task in tasks:
        owner = str(task.get("owner", "unassigned"))
        grouped[owner].append(task)
    return grouped
'''


def _utils(titles: list[str]) -> str:
    body = ["TITLES = ("]
    for title in titles:
        body.append(f"    {title!r},")
    body.append(")")
    body.append("")
    body.append("def nudge(index):")
    body.append("    # increment index")
    body.append("    index += 1")
    body.append("    return index")
    body.append("")
    body.append("def known_titles(names):")
    body.append("    picked = []")
    body.append("    index = 0")
    body.append("    for name in names:")
    body.append("        if name in TITLES:")
    body.append("            picked.append(name)")
    body.append("            index = nudge(index)")
    body.append("    return picked")
    body.append("")
    return "\n".join(body) + "\n"


def _write_tree(demo: Path, titles: list[str]) -> None:
    package = demo / "taskflow"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text('"""Task helpers."""\n', encoding="utf-8")
    (package / "client.py").write_text(_client(), encoding="utf-8")
    (package / "imports_ok.py").write_text(_imports(), encoding="utf-8")
    (package / "utils.py").write_text(_utils(titles), encoding="utf-8")


def cleaned_report() -> object:
    """A fixed demo with one narrating comment, tuned to score 94."""
    with tempfile.TemporaryDirectory(prefix="slopcheck-fixed-") as raw:
        parent = Path(raw)
        demo = parent / "demo"
        titles: list[str] = []
        report = None
        for _turn in range(240):
            _write_tree(demo, titles)
            report = scan([demo], config=Config(), root=parent, no_config=True)
            rules = {item.rule_id for item in report.findings}
            if rules != {"SLP004"}:
                raise RuntimeError(f"fixed tree rules were {sorted(rules)}")
            if report.score == 94:
                return report
            if report.score < 94:
                titles.append(f"task {len(titles):03d}")
            elif titles:
                titles.pop()
            else:
                break
        raise RuntimeError(f"could not reach score 94 (last {None if report is None else report.score})")


def _status(report: object) -> str:
    if any(item.severity in {"error", "warning"} for item in report.findings):
        return "fail"
    return "pass"


def _finding_row(item: object) -> str:
    return f"  {item.line}:{item.column}  {item.rule_id}  {item.severity:<7}  {item.message}"


def _header(report: object) -> list[str]:
    return [
        f"slopcheck  {report.version}",
        (
            f"scanned {report.files_scanned} files · {report.lines_scanned} lines · "
            f"{report.finding_count} findings"
        ),
        f"score  {report.score:>3} / 100  {score_bar(report.score)}  {report.label}",
    ]


Span = tuple[str, str]
Row = list[Span]


def _plain(text: str, color: str) -> Row:
    return [(text, color)]


def _score_rows(report: object) -> list[Row]:
    number = RED if report.score < 50 else GREEN
    label = EMBER if report.score < 50 else LIME
    return [
        [
            ("score  ", "#f4f6ef"),
            (str(report.score), number),
            (" / 100   ", "#f4f6ef"),
            (report.label, label),
        ],
        [(score_bar(report.score), number)],
    ]


def _dirty_rows(report: object) -> list[Row]:
    wanted = {"SLP001", "SLP010"}
    picked = []
    seen: set[str] = set()
    for item in report.findings:
        if item.rule_id in wanted and item.rule_id not in seen:
            if item.rule_id == "SLP010" and "requets" not in item.message:
                continue
            picked.append(item)
            seen.add(item.rule_id)
    rows: list[Row] = [
        [("$ ", LIME), ("uvx slopcheck demo", "#f4f6ef")],
        _plain(f"slopcheck  {report.version}", "#f4f6ef"),
        _plain(_header(report)[1], MUTED_DARK),
        *_score_rows(report),
        _plain("", "#f4f6ef"),
    ]
    for item in picked:
        rows.append(_plain(_finding_row(item), "#f4f6ef"))
    rows.append(_plain("", "#f4f6ef"))
    rows.append(_plain(f"{report.finding_count} findings · score {report.score} · {_status(report)}", RED))
    return rows


def _prompt_rows(report: object) -> list[Row]:
    lines = [line for line in render_prompt(report).splitlines() if line.strip()][:5]
    rows: list[Row] = [[("$ ", LIME), ("slopcheck prompt demo", "#f4f6ef")]]
    for line in lines:
        color = EMBER if "Slop score" in line else "#d7decc"
        rows.append(_plain(line, color))
    return rows


def _clean_rows(report: object) -> list[Row]:
    item = report.findings[0]
    return [
        [("$ ", LIME), ("slopcheck demo", "#f4f6ef")],
        _plain(f"slopcheck  {report.version}", "#f4f6ef"),
        _plain(_header(report)[1], MUTED_DARK),
        *_score_rows(report),
        _plain("", "#f4f6ef"),
        _plain(relative(item.path, report.root), "#f4f6ef"),
        _plain(_finding_row(item), "#d7decc"),
        _plain("", "#f4f6ef"),
        _plain(f"{report.finding_count} finding · score {report.score} · {_status(report)}", GREEN),
    ]


def _wrap(row: Row, face: ImageFont.FreeTypeFont, limit: int) -> list[Row]:
    flat: list[tuple[str, str]] = []
    for text, color in row:
        for char in text:
            flat.append((char, color))
    if not flat:
        return [row]
    lines: list[Row] = []
    current: Row = []
    width = 0
    for char, color in flat:
        advance = math.ceil(face.getlength(char))
        if width + advance > limit and current:
            lines.append(current)
            current = []
            width = 0
            if char == " ":
                continue
        if current and current[-1][1] == color:
            current[-1] = (current[-1][0] + char, color)
        else:
            current.append((char, color))
        width += advance
    if current:
        lines.append(current)
    return lines or [[]]


def _frame(
    rows: list[Row],
    *,
    body: ImageFont.FreeTypeFont,
    bold: ImageFont.FreeTypeFont,
    width: int,
    height: int,
    body_step: int,
    score_step: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), TERM)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=22, fill=TERM, outline="#2c3824", width=2)
    draw.rectangle((0, 0, width, 56), fill=TERM_BAR)
    draw.rectangle((0, 40, width, 56), fill=TERM_BAR)
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        cx = 22 + index * 26
        draw.ellipse((cx, 20, cx + 14, 34), fill=color)
    title = "slopcheck"
    title_face = font(SANS_MED, 18)
    draw.text(((width - text_width(draw, title, title_face)) // 2, 16), title, font=title_face, fill=MUTED_DARK)
    y = 78
    limit = width - 112
    for row in rows:
        face = bold if any(part.strip() in {"29", "94"} for part, _color in row) else body
        wrapped = _wrap(row, face, limit)
        for piece in wrapped:
            x = 28
            for part, color in piece:
                draw.text((x, y), part, font=face, fill=color)
                x += math.ceil(face.getlength(part))
            y += body_step if face is body else score_step
            if y > height - 24:
                return image
    return image


def _type_rows(command: str) -> list[list[Row]]:
    frames: list[list[Row]] = []
    for count in range(1, len(command) + 1):
        frames.append([[("$ ", LIME), (command[:count], "#f4f6ef"), ("█", LIME)]])
    frames.append([[("$ ", LIME), (command, "#f4f6ef")]])
    return frames


def _reveal(base: list[Row]) -> list[list[Row]]:
    frames: list[list[Row]] = []
    shown: list[Row] = []
    for row in base:
        shown.append(row)
        frames.append(list(shown))
    return frames


def gif(path: Path, dirty: object, clean: object) -> None:
    body = font(MONO, 30)
    bold = font(MONO_BOLD, 42)
    width, height = 840, 720
    body_step, score_step = 44, 58
    frames: list[Image.Image] = []
    typed = [_type_rows("uvx slopcheck demo"), _type_rows("slopcheck prompt demo"), _type_rows("slopcheck demo")]
    reveals = [
        _reveal(_dirty_rows(dirty)),
        _reveal(_prompt_rows(dirty)),
        _reveal(_clean_rows(clean)),
    ]
    for typed_frames, revealed, hold in zip(typed, reveals, (18, 12, 22), strict=True):
        clip = typed_frames + revealed
        for shot in clip:
            frames.append(
                _frame(
                    shot,
                    body=body,
                    bold=bold,
                    width=width,
                    height=height,
                    body_step=body_step,
                    score_step=score_step,
                )
            )
        last = frames[-1]
        frames.extend([last.copy() for _extra in range(hold)])
    folder = Path(tempfile.mkdtemp(prefix="slopcheck-frames-"))
    try:
        for index, frame in enumerate(frames):
            frame.save(folder / f"frame_{index:04d}.png")
        palette = folder / "palette.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "12",
                "-i",
                str(folder / "frame_%04d.png"),
                "-vf",
                "palettegen=reserve_transparent=0",
                str(palette),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                "12",
                "-i",
                str(folder / "frame_%04d.png"),
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=bayer:bayer_scale=2",
                "-loop",
                "0",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        shutil.rmtree(folder)


def shoot_report(path: Path) -> None:
    """Screenshot the HTML report. Headless Chrome writes the PNG and then lingers."""
    html = (DOCS / "demo-report.html").resolve()
    if not html.is_file():
        raise RuntimeError("docs/demo-report.html is missing; run scripts/render_assets.py first")
    started = time.time()
    if path.exists():
        path.unlink()
    with tempfile.TemporaryDirectory(prefix="slopcheck-chrome-", ignore_cleanup_errors=True) as raw:
        proc = subprocess.Popen(
            [
                "google-chrome",
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                "--window-size=760,560",
                f"--screenshot={path}",
                f"--user-data-dir={raw}",
                html.as_uri(),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            deadline = time.time() + 20
            while time.time() < deadline:
                ready = path.is_file() and path.stat().st_size > 5000 and path.stat().st_mtime >= started
                if ready or proc.poll() is not None:
                    time.sleep(0.4)
                    break
                time.sleep(0.2)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
    if not path.is_file() or path.stat().st_size < 5000:
        raise RuntimeError("chrome did not write the report screenshot")


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    dirty = scan([ROOT / "demo"])
    if dirty.score != 29:
        raise RuntimeError(f"demo score drifted from 29 to {dirty.score}")
    clean = cleaned_report()
    if clean.score != 94 or clean.version != __version__:
        raise RuntimeError(f"clean score {clean.score} version {clean.version}")
    hero(DOCS / "hero-dark.png", dark=True)
    hero(DOCS / "hero-light.png", dark=False)
    social(DOCS / "social-preview.png")
    before_after(DOCS / "before-after.png")
    gif(DOCS / "demo.gif", dirty, clean)
    shoot_report(DOCS / "report.png")
    print("wrote docs/hero-dark.png docs/hero-light.png docs/social-preview.png")
    print("wrote docs/before-after.png docs/demo.gif docs/report.png")


if __name__ == "__main__":
    main()
