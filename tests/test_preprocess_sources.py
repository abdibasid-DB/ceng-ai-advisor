import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import preprocess_sources
from preprocess_sources import extract_embedded_listing, render_tables_with_headers


TABLE = """
<table><caption><span>Table 1.4 Occupations with the most job growth (Employment in thousands)</span></caption>
<thead><tr><th>Occupation title</th><th>Code</th><th>Employment, 2025</th><th>Median annual wage, dollars, 2025</th></tr></thead>
<tbody>
<tr><th scope="row"><p>Software developers</p></th><td>15-1252</td><td>1,717.8</td><td>135,980</td></tr>
<tr><th scope="row"><p>Registered nurses</p></th><td>29-1141</td><td>3,465.4</td><td>97,550</td></tr>
</tbody></table>
"""


class PreprocessSourcesTests(unittest.TestCase):
    def test_table_rows_keep_their_column_headers_and_caption(self):
        text = render_tables_with_headers(f"<p>Intro</p>{TABLE}<p>Footnote</p>")
        self.assertIn(
            "Table 1.4 Occupations with the most job growth (Employment in thousands) - Software developers: "
            "Code: 15-1252; Employment, 2025: 1,717.8; Median annual wage, dollars, 2025: 135,980.",
            text,
        )
        self.assertIn("Registered nurses: Code: 29-1141", text)
        self.assertIn("<p>Intro</p>", text)
        self.assertIn("<p>Footnote</p>", text)

    def test_table_without_header_row_is_left_alone(self):
        table = "<table><tr><td>a</td><td>b</td></tr></table>"
        self.assertEqual(render_tables_with_headers(table), table)

    def test_embedded_club_listing_is_extracted_by_category(self):
        raw = """<script>
        var CATS = {
          1:{tr:'Yazılım, YZ & Teknoloji',en:'Software, AI & Tech',c:'#5A4AE0'},
          2:{tr:'Spor & Rekreasyon',en:'Sports & Recreation',c:'#000'}
        };
        var COMM = [
          {n:'Yapay Zeka',c:1,g:'1',s:'yapay-zeka'},
          {n:'IEEE',c:1,g:'2',s:'ieee'},
          {n:'Voleybol',c:2,g:'3',s:'voleybol'}
        ];
        </script>"""
        text = extract_embedded_listing(raw)
        self.assertIn("3 communities in 2 categories", text)
        self.assertIn("Software, AI & Tech (Yazılım, YZ & Teknoloji) student communities: Yapay Zeka; IEEE.", text)
        self.assertIn("Sports & Recreation (Spor & Rekreasyon) student communities: Voleybol.", text)
        self.assertEqual(extract_embedded_listing("<p>No data</p>"), "")

    def test_partial_run_keeps_other_sources_in_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "processing_manifest.json"
            manifest.write_text(json.dumps({"records": [{"source_id": "src_001", "v": 1}, {"source_id": "src_002", "v": 1}]}), encoding="utf-8")

            class Record:
                pass

            with patch.object(preprocess_sources, "MANIFEST_PATH", manifest), patch.object(
                preprocess_sources, "asdict", side_effect=lambda record: record.row
            ):
                updated, added = Record(), Record()
                updated.row, added.row = {"source_id": "src_002", "v": 2}, {"source_id": "src_003", "v": 1}
                preprocess_sources.save_manifest([updated, added], merge=True)
            rows = json.loads(manifest.read_text(encoding="utf-8"))["records"]
        self.assertEqual(rows, [{"source_id": "src_001", "v": 1}, {"source_id": "src_002", "v": 2}, {"source_id": "src_003", "v": 1}])


if __name__ == "__main__":
    unittest.main()
