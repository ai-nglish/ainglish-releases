import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
# Release 4 (2026-09-19): the current human deposit sheets describe ainglish-training-v4, bound to
# ainglish-core-v4 (register 0.53.0, 32 constructs). Release 3 sheets are superseded, not kept.
CORE = json.loads((ROOT / "ainglish-core-v4" / "MANIFEST.json").read_text(encoding="utf-8"))
PACK = json.loads((ROOT / "ainglish-training-v4" / "MANIFEST.json").read_text(encoding="utf-8"))


def test_current_human_deposit_sheets_match_release_4_identity_and_counts():
    mozilla = (ROOT / "deposits" / "mozilla-data-collective.md").read_text(encoding="utf-8")
    clarin = (ROOT / "deposits" / "clarin-vlo.md").read_text(encoding="utf-8")
    common_pile = (ROOT / "deposits" / "common-pile.md").read_text(encoding="utf-8")

    for document in (mozilla, clarin):
        assert f"Ainglish training pack v{PACK['version']}" in document
        assert f"{PACK['counts']['constructs']} ratified" in document
        assert f"{PACK['counts']['parallel']} reviewed" in document
        assert CORE["register_digest"] in document

    for count_name in ("constructs", "parallel", "instruction", "pretrain_documents"):
        assert str(PACK["counts"][count_name]) in mozilla
    assert "release-4 training companion" in common_pile
    assert f"{PACK['counts']['constructs']} ratified" in common_pile
    assert f"{PACK['counts']['parallel']} reviewed" in common_pile
    assert f"{PACK['counts']['instruction']} instruction" in common_pile
    assert "ainglish-training-v4" in common_pile
    assert "ainglish-training-v0.35.0" not in common_pile


def test_hugging_face_handoff_names_the_live_release_4_configs_and_counts():
    handoff = (ROOT / "deposits" / "hugging-face.md").read_text(encoding="utf-8")
    expected = {
        "parallel": PACK["counts"]["parallel"],
        "instruction": PACK["counts"]["instruction"],
        "pretrain": PACK["counts"]["pretrain_documents"],
        "register": PACK["counts"]["register"],
    }

    for config, rows in expected.items():
        assert f'"training_{config}_v4": {rows}' in handoff
        assert f"config_name: training_{config}_v4" in handoff
        assert f"data_files: ainglish-training-v4/data/{'pretrain_documents' if config == 'pretrain' else config}.jsonl" in handoff
    assert "upload step is\ncomplete" in handoff
