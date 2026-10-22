"""Turn the hand-written passage functions of rag_pipeline.py into curated source notes.

Each note is a verbatim excerpt of the processed source document the function
read from (no paraphrase), registered in knowledge_base/sources.json under its
own source ID with the original source's URL, publisher and source type, and
added to the processing manifest so the normal chunking and embedding steps
index it. Re-running replaces the notes with the same IDs.

Usage: python docs/handwritten-removal-20261022/build_curated_notes.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import preprocess_sources  # noqa: E402

DOCUMENTS = ROOT / "knowledge_base" / "processed" / "documents"
SOURCES_PATH = ROOT / "knowledge_base" / "sources.json"
MANIFEST_PATH = ROOT / "knowledge_base" / "processed" / "processing_manifest.json"
RAW_TEXT_DIR = ROOT / "knowledge_base" / "raw" / "text"
DATE_ACCESSED = "2026-10-22"

# Header/footer lines repeated on every page of the OSTIM syllabus PDFs.
PDF_FORM_LINE = re.compile(
    r"^(Page \d+|OTU Form No|Not: |İlk Yayın|Revizyon|FACULTY OF|COURSE SYLLABUS FORM|Doküman No|Sayfa No)"
)


def lines_between(source_id: str, start: str, end: str | None, *, include_end: bool = False) -> str:
    """Verbatim text from the line starting with `start` up to (not including) the line starting with `end`."""
    lines = (DOCUMENTS / f"{source_id}.txt").read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(lines) if line.strip().startswith(start))
    last = len(lines)
    if end is not None:
        last = next(i for i in range(first + 1, len(lines)) if lines[i].strip().startswith(end)) + (1 if include_end else 0)
    kept = [line for line in lines[first:last] if not PDF_FORM_LINE.match(line.strip())]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def paragraph(source_id: str, heading: str) -> str:
    """A course heading line and the paragraph that follows it, verbatim."""
    text = (DOCUMENTS / f"{source_id}.txt").read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.find("\n\n", start)
    return text[start : end if end != -1 else None].strip()


NOTES = [
    {
        "source_id": "src_126",
        "from": "src_004",
        "replaces": "programming_languages_passage",
        "title": "Course Contents: OSTIM Computer Engineering programming courses and programming languages (SENG116, CENG109, CENG110)",
        "category": "programming",
        # SENG116 first: it is the course that names languages, and it then shares a chunk with the title.
        "text": lambda: "\n\n".join(
            paragraph("src_004", heading)
            for heading in ("SENG116 Object Oriented Programming", "CENG109 Programming and Computation I", "CENG110 Programming and Computation II")
        ),
    },
    {
        "source_id": "src_127",
        "from": "src_033",
        "replaces": "gpa_screening_passage",
        "title": "Hiring Projections Level Off for the College Class of 2025: GPA screening and skills-based hiring",
        "category": "employment",
        "text": lambda: lines_between("src_033", "The use of the GPA as a candidate screening tool", "Just 11% of respondents"),
    },
    {
        "source_id": "src_128",
        "from": "src_042",
        "replaces": "computer_engineering_definition_passage",
        "title": "Curricular Guidance: the sub-disciplines of computing (computer engineering, computer science, software engineering, information technology)",
        "category": "common_misconceptions",
        "text": lambda: lines_between("src_042", "The Sub-Disciplines of Computing", "Security in the Computing Curricula"),
    },
    {
        "source_id": "src_129",
        "from": "src_063",
        "replaces": "future_technologies_passage",
        "title": "CENG 316 New Trends in Computer Engineering: course content and weekly topics",
        "category": "future_technologies",
        "text": lambda: lines_between("src_063", "Course Content", "Course Method/")
        + "\n\n"
        + lines_between("src_063", "Weekly Schedule", "15 Final exam", include_end=True),
    },
    {
        "source_id": "src_130",
        "from": "src_004",
        "replaces": "linux_operating_system_passage",
        "title": "Course Contents: CENG 303 Operating Systems Design & Construction (Linux or Windows)",
        "category": "curriculum",
        "text": lambda: paragraph("src_004", "CENG 303 Operating Systems Design & Construction"),
    },
    {
        "source_id": "src_131",
        "from": "src_043",
        "replaces": "specialization_areas_passage",
        "title": "Subdisciplines: specialization areas in Computer Engineering",
        "category": "specializations",
        "text": lambda: lines_between("src_043", "Specialization areas in Computer Engineering:", None).split("\nPage last")[0].strip(),
    },
]


def main() -> int:
    registry = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = {source["source_id"]: source for source in registry["sources"]}
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    note_ids = {note["source_id"] for note in NOTES}
    RAW_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    new_sources = []
    for note in NOTES:
        original = sources[note["from"]]
        excerpt = note["text"]()
        raw_path = RAW_TEXT_DIR / f"{note['source_id']}.txt"
        raw_path.write_text(f"{note['title']}\n\n{excerpt}\n", encoding="utf-8", newline="\n")
        new_sources.append(
            {
                "source_id": note["source_id"],
                "title": note["title"],
                "source_name": original["source_name"],
                "source_type": original["source_type"],
                "url": original["url"],
                "publication_date": original.get("publication_date"),
                "date_accessed": DATE_ACCESSED,
                "category": note["category"],
                "language": original["language"],
                "reliability_note": f"Curated verbatim excerpt of {note['from']} ({original['title']}); same publisher and URL. {original.get('reliability_note') or ''}".strip(),
                "raw_file_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "notes": (
                    f"Curated source note made on {DATE_ACCESSED} from {note['from']} to replace the hand-written "
                    f"{note['replaces']}() in backend/app/rag/rag_pipeline.py; the full source stays indexed as {note['from']}."
                ),
                "curated_from": note["from"],
            }
        )
        print(f"{note['source_id']} <- {note['from']} ({note['replaces']}): {len(excerpt.split())} words")

    registry["sources"] = [source for source in registry["sources"] if source["source_id"] not in note_ids] + new_sources
    SOURCES_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    records = [preprocess_sources.process_source(source) for source in new_sources]
    for record in records:
        # A focused excerpt can be legitimately short (src_131 is an 8-item list); accept it as
        # preprocess_sources.py does for its reviewed ACCEPT_VALID_SHORT_DOCUMENTS.
        if record.processing_status == "manual_review_required" and all("short" in w or "word count is very low" in w for w in record.warnings):
            record.processing_status = "success"
            record.chunking_eligible = True
            record.warnings.append("Curated excerpt: accepted as a valid short document")
        if record.processing_status not in {"success", "warning"}:
            raise SystemExit(f"{record.source_id}: {record.processing_status} {record.warnings}")
        record.extraction_method = "plain_text_read_curated_note"
    manifest["records"] = [record for record in manifest["records"] if record["source_id"] not in note_ids] + [asdict(record) for record in records]
    manifest["document_count"] = len(manifest["records"])
    manifest["generated_at"] = preprocess_sources.utc_now()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for record in records:
        print(f"{record.source_id}: {record.processing_status} {record.extracted_word_count} words {record.warnings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
