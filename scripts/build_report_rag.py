#!/usr/bin/env python3
"""Build page-aware RAG material from the Kimi World Cup report PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pypdf. Install it with `python3 -m pip install pypdf`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Downloads" / "Kimi_2026_World_Cup_Report.pdf"
DEFAULT_OUTPUT = ROOT / "data" / "rag" / "kimi-world-cup-report"
SOURCE_ID = "kimi-2026-world-cup-report"
REPORT_TITLE = "Kimi关于2026年世界杯赛事分析和预测报告"
REPORT_DATE = "2026-06-05"
TARGET_CHARS = 1200
OVERLAP_CHARS = 160

CHAPTER_RANGES = [
    (1, 1, "封面"),
    (2, 8, "目录"),
    (9, 9, "报告说明"),
    (10, 19, "第1章 赛事概览"),
    (20, 39, "第2章 研究方法论"),
    (40, 105, "第3章 争冠球队深度解剖"),
    (106, 133, "第4章 各小组出线形势与首轮预测"),
    (134, 146, "第5章 潜在爆冷场次"),
    (147, 165, "第6章 赛程、环境、后勤与外部变量"),
    (166, 175, "第7章 赛后复盘与动态迭代机制"),
    (176, 200, "第8章 结论、回测与不确定性"),
    (201, 202, "附录A 数据字典"),
    (203, 203, "附录B 模型技术细节"),
    (204, 205, "附录C 历史回测报告"),
]

KEYWORD_TAXONOMY = {
    "data_provenance": ["数据来源", "Provenance", "多源数据", "数据质量", "时效性"],
    "rating": ["ELO", "Elo", "FIFA排名", "FIFA SUM", "SPI"],
    "event_data": ["xG", "xGA", "xT", "PPDA", "射门", "传球", "触球"],
    "squad": ["阵容深度", "QDR", "核心依赖", "球员", "伤病", "停赛"],
    "tactics": ["战术", "相克", "阵型", "定位球", "高位逼抢"],
    "market": ["赔率", "市场", "隐含概率", "Polymarket", "Kalshi"],
    "environment": ["WBGT", "天气", "气候", "海拔", "湿度", "草皮"],
    "travel": ["旅行", "飞行距离", "时区", "疲劳", "恢复时间"],
    "simulation": ["蒙特卡洛", "Monte Carlo", "Poisson", "Dixon-Coles"],
    "agents": ["Agent", "智能体", "辩论", "共识", "Swarm"],
    "uncertainty": ["不确定性", "置信区间", "可信区间", "模型分歧"],
    "calibration": ["校准", "Brier", "RPS", "准确率", "回测"],
    "dynamic_update": ["贝叶斯", "动态更新", "模型漂移", "归因", "收敛"],
    "prediction": ["夺冠概率", "晋级概率", "比赛预测", "模型输出"],
}

SECTION_PATTERN = re.compile(
    r"^(?:(?:第\s*[一二三四五六七八九十0-9]+\s*章|Chapter\s+\d+|附录\s*[A-Z])"
    r"[^。\n]{0,60}|[1-9](?:\.\d{1,2}){1,2}\s+[^。\n]{2,80}|"
    r"表\d+(?:\.\d+)?\s*[^。\n]{2,80})",
    flags=re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-chars", type=int, default=TARGET_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=OVERLAP_CHARS)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").replace("\x00", "")
    replacements = {
        "K im i": "Kimi",
        "M ulti-Agent": "Multi-Agent",
        "ELO评 级": "ELO评级",
        "W BGT": "WBGT",
        "Poisson族": "Poisson族",
        "xG A": "xGA",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def chapter_for_page(page_number: int) -> str:
    for start, end, chapter in CHAPTER_RANGES:
        if start <= page_number <= end:
            return chapter
    return "未分类"


def section_for_text(text: str, chapter: str) -> str:
    candidates = SECTION_PATTERN.findall(text[:2200])
    if not candidates:
        return chapter
    candidate = re.sub(r"\s+", " ", candidates[-1]).strip()
    return candidate[:120]


def keywords_for_text(text: str) -> list[str]:
    lowered = text.lower()
    return [
        label
        for label, terms in KEYWORD_TAXONOMY.items()
        if any(term.lower() in lowered for term in terms)
    ]


def content_type(text: str) -> str:
    if re.search(r"表\d|字段|数据字典|特征名称|阈值", text):
        return "table_or_schema"
    if re.search(r"公式|模型|Poisson|ELO|蒙特卡洛", text, flags=re.IGNORECASE):
        return "methodology"
    if re.search(r"概率|预测|情景|风险", text):
        return "forecast_analysis"
    return "narrative"


def split_text(text: str, target_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= target_chars:
        return [text] if text else []

    units = re.split(r"(?<=[。！？；])\s*|\n+", text)
    units = [unit.strip() for unit in units if unit.strip()]
    chunks: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n{unit}".strip() if current else unit
        if current and len(candidate) > target_chars:
            chunks.append(current)
            overlap = current[-overlap_chars:] if overlap_chars else ""
            current = f"{overlap}\n{unit}".strip()
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"PDF source not found: {source}")
    if args.target_chars < 400:
        raise SystemExit("--target-chars must be at least 400")
    if not 0 <= args.overlap_chars < args.target_chars:
        raise SystemExit("--overlap-chars must be smaller than --target-chars")

    output.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(source)
    source_hash = sha256(source)
    generated_at = datetime.now(timezone.utc).isoformat()
    pages: list[dict] = []
    chunks: list[dict] = []
    section_index: dict[str, dict] = {}

    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        chapter = chapter_for_page(page_number)
        section = section_for_text(text, chapter)
        page_record = {
            "id": f"{SOURCE_ID}-p{page_number:03d}",
            "source_id": SOURCE_ID,
            "title": REPORT_TITLE,
            "report_date": REPORT_DATE,
            "page": page_number,
            "chapter": chapter,
            "section": section,
            "text": text,
            "keywords": keywords_for_text(text),
            "content_type": content_type(text),
            "citation": f"{REPORT_TITLE}, p.{page_number}",
            "source_sha256": source_hash,
        }
        pages.append(page_record)

        section_entry = section_index.setdefault(
            chapter,
            {"chapter": chapter, "page_start": page_number, "page_end": page_number, "sections": []},
        )
        section_entry["page_end"] = page_number
        if section not in section_entry["sections"]:
            section_entry["sections"].append(section)

        for chunk_number, chunk_text in enumerate(
            split_text(text, args.target_chars, args.overlap_chars),
            start=1,
        ):
            chunks.append(
                {
                    "id": f"{SOURCE_ID}-p{page_number:03d}-c{chunk_number:02d}",
                    "source_id": SOURCE_ID,
                    "title": REPORT_TITLE,
                    "report_date": REPORT_DATE,
                    "page_start": page_number,
                    "page_end": page_number,
                    "chapter": chapter,
                    "section": section,
                    "text": chunk_text,
                    "keywords": keywords_for_text(chunk_text),
                    "content_type": content_type(chunk_text),
                    "citation": f"{REPORT_TITLE}, p.{page_number}",
                    "source_sha256": source_hash,
                    "chunk_index": chunk_number,
                }
            )

    manifest = {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "title": REPORT_TITLE,
        "language": "zh-CN",
        "report_date": REPORT_DATE,
        "generated_at": generated_at,
        "source": {
            "filename": source.name,
            "path_at_generation": str(source),
            "sha256": source_hash,
            "page_count": len(reader.pages),
        },
        "artifacts": {
            "pages": "pages.jsonl",
            "chunks": "chunks.jsonl",
            "sections": "sections.json",
            "corpus": "corpus.md",
        },
        "chunking": {
            "strategy": "page-bounded semantic sentence chunks",
            "target_chars": args.target_chars,
            "overlap_chars": args.overlap_chars,
            "chunk_count": len(chunks),
        },
        "usage_notes": [
            "Treat quantitative claims as report assertions until independently verified.",
            "Use citation and page fields when presenting retrieved claims.",
            "Prefer chunks with data_provenance, uncertainty, or calibration keywords for model design questions.",
        ],
    }

    write_jsonl(output / "pages.jsonl", pages)
    write_jsonl(output / "chunks.jsonl", chunks)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "sections.json").write_text(
        json.dumps(list(section_index.values()), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    corpus_lines = [
        f"# {REPORT_TITLE}",
        "",
        f"- Source ID: `{SOURCE_ID}`",
        f"- Report date: {REPORT_DATE}",
        f"- Pages: {len(pages)}",
        f"- Source SHA-256: `{source_hash}`",
        "",
    ]
    current_chapter = None
    for page in pages:
        if page["chapter"] != current_chapter:
            current_chapter = page["chapter"]
            corpus_lines.extend([f"## {current_chapter}", ""])
        corpus_lines.extend(
            [
                f"### Page {page['page']}: {page['section']}",
                "",
                page["text"],
                "",
                f"Source: {page['citation']}",
                "",
            ]
        )
    (output / "corpus.md").write_text("\n".join(corpus_lines), encoding="utf-8")

    print(f"Built RAG corpus: {output}")
    print(f"- pages: {len(pages)}")
    print(f"- chunks: {len(chunks)}")
    print(f"- source sha256: {source_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
