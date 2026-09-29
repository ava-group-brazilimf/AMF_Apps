import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_segmentation_preserves_all_relationships_and_passes_segments():
    report = json.loads((ROOT / 'projects/sophia/outputs/summary/compatibility/c4-component-segmentation-diagnostic.json').read_text(encoding='utf-8'))
    assert report['relationshipsDroppedCount'] == 0
    assert report['relationshipsPreservedCount'] == report['relationshipsTotalCount']
    assert report['publicationAllowed'] is True
    assert all(segment['renderStatus'] == 'PASS' for segment in report['segments'])


def test_segmentation_has_traceable_mapping():
    report = json.loads((ROOT / 'projects/sophia/outputs/summary/compatibility/c4-component-segmentation-diagnostic.json').read_text(encoding='utf-8'))
    assert len(report['relationshipMapping']) == report['relationshipsTotalCount']
    assert all(item['preserved'] for item in report['relationshipMapping'])
