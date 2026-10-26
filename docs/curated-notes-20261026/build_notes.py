"""Register the curated English notes of 2026-10-26 and their original pages.

The note texts are in knowledge_base/raw/text/src_137.txt ... src_149.txt. This
script adds their registry entries to knowledge_base/sources.json, together with
the original pages src_133-src_136 (saved on 2026-10-25, parked in
D:/ceng-ai-advisor-data/sources-pending-20261025). The raw BLS pages
src_134-src_136 are registered but excluded from chunking
(preprocess_sources.EXCLUDE_FROM_CHUNKING_AFTER_REVIEW); only their notes are
indexed. Then the normal preprocessing runs for these source IDs.

Usage: python docs/curated-notes-20261026/build_notes.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES_PATH = ROOT / "knowledge_base" / "sources.json"
PARKED_REGISTRY = Path("D:/ceng-ai-advisor-data/sources-pending-20261025/sources-with-src133-136.json")
DATE = "2026-10-26"

ORIGINAL_NOTES = {
    "src_133": "Indexed as a full page; the curated note src_140 holds the AI and jobs figures.",
    "src_134": "Registered but not indexed (excluded from chunking on 2026-10-26: page frame, navigation text and a financial-advisor passage that crowded out better passages in the 2026-10-25 test); the curated note src_137 is indexed instead.",
    "src_135": "Registered but not indexed (excluded from chunking on 2026-10-26: page frame and chart cells without column headers); the curated note src_138 is indexed instead.",
    "src_136": "Registered but not indexed (excluded from chunking on 2026-10-26: page frame and table cells without column headers); the curated note src_139 is indexed instead.",
}

# (note id, curated from, title, category, publisher fields taken from this source)
NOTES = [
    ("src_137", ["src_134"], "Curated English note of src_134: AI impacts in BLS employment projections (U.S. Bureau of Labor Statistics, 2025)", "artificial_intelligence", "src_134"),
    ("src_138", ["src_135"], "Curated English note of src_135: Artificial intelligence, information technology, and employment, 2024–34 (U.S. Bureau of Labor Statistics, 2026)", "employment", "src_135"),
    ("src_139", ["src_136"], "Curated English note of src_136: Computer and Information Technology Occupations, outlook, openings and wages (BLS Occupational Outlook Handbook)", "employment", "src_136"),
    ("src_140", ["src_133"], "Curated English note of src_133: Stack Overflow 2025 Developer Survey, developers' views on AI and their jobs", "artificial_intelligence", "src_133"),
    ("src_141", ["src_001", "src_002", "src_003", "src_005"], "Curated English note: OSTİM Technical University Department of Computer Engineering (English), aims and program facts", "department_information", "src_001"),
    ("src_142", ["src_107"], "Curated English note of src_107: OSTİM Technical University English preparatory school, levels, exemption and maximum duration", "student_life", "src_107"),
    ("src_143", ["src_104"], "Curated English note of src_104: OSTİM Technical University scholarships and tuition discounts", "department_information", "src_104"),
    ("src_144", ["src_105", "src_106"], "Curated English note of src_105 and src_106: OSTİM Technical University double major and minor eligibility", "curriculum", "src_105"),
    ("src_145", ["src_122", "src_112"], "Curated English note of src_122 and src_112: OSTİM Technical University student clubs, list and how to join", "student_life", "src_122"),
    ("src_146", ["src_116"], "Curated English note of src_116: OSTİM Technical University academic advising for students", "student_life", "src_116"),
    ("src_147", ["src_114"], "Curated English note of src_114: OSTİM Technical University computer laboratories, rules of use", "student_life", "src_114"),
    ("src_148", ["src_110", "src_109", "src_003", "src_004"], "Curated English note: OSTİM Technical University applied workplace courses instead of a compulsory internship", "internships", "src_109"),
    ("src_149", ["src_111", "src_088", "src_104"], "Curated English note of src_111 and src_088: OSTİM Technical University graduate (master's) programs in Computer Engineering", "graduate_studies", "src_088"),
]


def main() -> int:
    registry = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = {source["source_id"]: source for source in registry["sources"]}
    parked = {source["source_id"]: source for source in json.loads(PARKED_REGISTRY.read_text(encoding="utf-8"))["sources"]}

    new_ids = list(ORIGINAL_NOTES) + [note[0] for note in NOTES]
    for source_id, note in ORIGINAL_NOTES.items():
        entry = dict(parked[source_id])
        entry["notes"] = f"{entry['notes']} {note}"
        sources[source_id] = entry

    for note_id, curated_from, title, category, publisher_id in NOTES:
        publisher = sources[publisher_id]
        raw_path = ROOT / "knowledge_base" / "raw" / "text" / f"{note_id}.txt"
        first_line = raw_path.read_text(encoding="utf-8").splitlines()[0]
        if first_line != title:
            raise SystemExit(f"{note_id}: title line {first_line!r} differs from the registry title")
        names = ", ".join(f"{sid} ({sources[sid]['title']})" for sid in curated_from)
        sources[note_id] = {
            "source_id": note_id,
            "title": title,
            "source_name": publisher["source_name"],
            "source_type": publisher["source_type"],
            "url": publisher["url"],
            "publication_date": publisher.get("publication_date"),
            "date_accessed": DATE,
            "category": category,
            "language": "English",
            "reliability_note": (
                f"Curated English note of {names}. Facts only: exact quotes for English sources and a faithful, clearly labelled "
                "English translation (not an official one) for Turkish sources, with the source titles, URLs and dates; no advice or "
                f"conclusions of its own. {publisher.get('reliability_note') or ''}"
            ).strip(),
            "raw_file_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "notes": (
                f"Curated source note made on {DATE} from {', '.join(curated_from)}, because English questions did not retrieve "
                "the full sources well. The full sources stay registered under their own IDs."
            ),
            "curated_from": curated_from[0] if len(curated_from) == 1 else curated_from,
        }

    order = [source["source_id"] for source in registry["sources"]]
    order += [source_id for source_id in new_ids if source_id not in order]
    registry["sources"] = [sources[source_id] for source_id in order]
    SOURCES_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"registered {len(new_ids)} sources: {', '.join(new_ids)}")

    command = [sys.executable, str(ROOT / "scripts" / "preprocess_sources.py")]
    for source_id in new_ids:
        command += ["--source-id", source_id]
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
