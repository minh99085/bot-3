"""STATE.md / LESSONS.md are gitignored runtime files; knowledge_path seeds them
from the committed curated template on a fresh checkout."""

from __future__ import annotations

import hermes.state_io as sio


def test_knowledge_path_seeds_from_template(monkeypatch, tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "LESSONS.template.md").write_text("# seed\nAVOID:osmani_lane\n", encoding="utf-8")
    (kn / "STATE.template.md").write_text("# state\n- **Pause Loop**: false\n", encoding="utf-8")
    monkeypatch.setattr(sio, "KNOWLEDGE", kn)

    for name, needle in (("LESSONS.md", "AVOID:osmani_lane"), ("STATE.md", "Pause Loop")):
        p = sio.knowledge_path(name)              # missing → seeded from template
        assert p.exists() and needle in p.read_text(encoding="utf-8")


def test_knowledge_path_does_not_clobber_existing(monkeypatch, tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    (kn / "LESSONS.template.md").write_text("SEED\n", encoding="utf-8")
    live = kn / "LESSONS.md"
    live.write_text("RUNTIME EDITS\n", encoding="utf-8")
    monkeypatch.setattr(sio, "KNOWLEDGE", kn)
    assert sio.knowledge_path("LESSONS.md").read_text(encoding="utf-8") == "RUNTIME EDITS\n"


def test_no_template_no_seed(monkeypatch, tmp_path):
    kn = tmp_path / "knowledge"
    kn.mkdir()
    monkeypatch.setattr(sio, "KNOWLEDGE", kn)
    p = sio.knowledge_path("STATE.md")            # no template → path returned, not created
    assert not p.exists()
