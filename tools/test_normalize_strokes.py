import unittest
import xml.etree.ElementTree as ET
from normalize_strokes import canonical, absolute

class StrokePreparationTests(unittest.TestCase):
    def test_inherited_presentation_is_explicit_and_container_is_unstroked(self):
        root = ET.fromstring(canonical('<svg stroke="black" stroke-width="2" fill="none"><g stroke-width="1"><path d="M2 3h4v5"/><circle r="2"/></g></svg>'))
        group = root[0]
        self.assertNotIn('stroke', root.attrib)
        self.assertNotIn('stroke-width', group.attrib)
        self.assertEqual(group[0].get('stroke'), 'black')
        self.assertEqual(group[0].get('stroke-width'), '1')
        self.assertEqual(group[0].get('d'), 'M2.0 3.0L6.0 3.0L6.0 8.0')
        self.assertEqual(group[1].get('stroke'), 'black')

    def test_child_stroke_override_is_preserved(self):
        root = ET.fromstring(canonical('<svg stroke="black"><path d="M0 0L1 1" stroke="none" fill="black"/></svg>'))
        self.assertEqual(root[0].get('stroke'), 'none')
        self.assertEqual(root[0].get('fill'), 'black')

    def test_relative_cubic_geometry_is_preserved(self):
        self.assertEqual(absolute('M2 3c1 2 3 4 5 6'), 'M2.0 3.0C3.0 5.0 5.0 7.0 7.0 9.0')

    def test_unsupported_curve_is_rejected(self):
        with self.assertRaises(ValueError):
            absolute('M0 0A2 2 0 0 1 4 4')


class PublishedGalleryTests(unittest.TestCase):
    def test_gallery_has_no_inherited_container_strokes_or_missing_assets(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        names = json.loads((root/'website/app/data/variable-width-library.json').read_text())
        for name in names:
            svg = ET.fromstring((root/'website/public/variable-width/variable-width-library'/f'{name}.svg').read_text())
            self.assertEqual(svg.get('stroke', 'none'), 'none', name)

    def test_rejected_icons_cannot_reappear_on_home_or_in_library(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/'tools/icon-quality-review.json').read_text())
        library = set(json.loads((root/'website/app/data/variable-width-library.json').read_text()))
        featured = set(json.loads((root/'website/app/data/variable-width-gallery.json').read_text()))
        self.assertFalse(library.intersection(report['excluded']))
        self.assertTrue(featured.issubset(library))
        self.assertTrue(set(report['corrected']).issubset(library))

if __name__ == '__main__':
    unittest.main()
