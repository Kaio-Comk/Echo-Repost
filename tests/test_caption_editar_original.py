"""No modo editar_original a legenda vem do Reel de origem (editada) e a IA só entra sem legenda."""
from __future__ import annotations

from tests.conftest import FakeCaptionGenerator


def _video(session, legenda):
    from app.models.profile import Profile
    from app.models.video import Video

    perfil = Profile(username="cenasemfilmes")
    session.add(perfil)
    session.flush()
    v = Video(profile_id=perfil.id, source_post_id="ig:X", source_caption=legenda)
    session.add(v)
    session.flush()
    return v


def test_usa_a_legenda_original_editada_sem_chamar_a_ia(session, monkeypatch):
    monkeypatch.setenv("CAPTION_MODE", "editar_original")
    from app.config import settings as cfg
    cfg.get_settings.cache_clear()
    from app.services.caption_service import CaptionService

    v = _video(session, "Cena linda do filme que emociona demais | EDIT |\n\nSiga @cenasemfilmes\n#filme #cenas")
    ia = FakeCaptionGenerator()
    cap = CaptionService(session, ia).generate_for_video(v.id)
    assert ia.calls == 0
    assert "EDIT" not in cap.generated_caption and "@cenasemfilmes" not in cap.generated_caption
    assert "bio" in cap.generated_caption.lower() and "#nethub" in cap.generated_caption
    assert cap.model == "original-editada"


def test_sem_legenda_na_origem_cai_na_ia(session, monkeypatch):
    monkeypatch.setenv("CAPTION_MODE", "editar_original")
    from app.config import settings as cfg
    cfg.get_settings.cache_clear()
    from app.services.caption_service import CaptionService

    v = _video(session, "   ")
    ia = FakeCaptionGenerator()
    CaptionService(session, ia).generate_for_video(v.id)
    assert ia.calls == 1
