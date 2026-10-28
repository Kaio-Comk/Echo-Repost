"""Fixtures de teste: banco isolado, sessão e mock da IA local."""
from __future__ import annotations

import importlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


@pytest.fixture()
def engine():
    """Engine SQLite em memória, isolada por teste."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    sess = factory()
    try:
        yield sess
        sess.commit()
    finally:
        sess.close()


class FakeCaptionGenerator:
    """Mock determinístico do gerador de legendas (sem Ollama)."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy
        self.calls = 0

    def generate(self, context: str, style: str, target_username: str = "", extra: str = "") -> str:
        self.calls += 1
        return f"[{style}] legenda original #{self.calls} #reels #conteudo"

    def health_check(self) -> bool:
        return self._healthy


@pytest.fixture()
def fake_ai():
    return FakeCaptionGenerator()


@pytest.fixture()
def temp_app_env(tmp_path, monkeypatch):
    """Reconfigura settings/db para diretórios temporários e banco próprio.

    Usado por testes de integração que dependem dos singletons globais
    (session_scope, get_settings).
    """
    db_file = tmp_path / "test.db"
    watch = tmp_path / "inbox"
    downloads = tmp_path / "downloads"
    watch.mkdir()
    downloads.mkdir()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("WATCH_DIR", str(watch))
    monkeypatch.setenv("DOWNLOAD_DIR", str(downloads))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("SOURCE_PROVIDER", "manual")
    monkeypatch.setenv("PUBLISHER", "dry_run")
    monkeypatch.setenv("REQUIRE_MANUAL_APPROVAL", "false")

    # Limpa caches/singletons.
    from app.config import settings as settings_mod
    settings_mod.get_settings.cache_clear()

    import app.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    yield {"watch": watch, "downloads": downloads, "db": db_file}

    settings_mod.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _ambiente_isolado_do_env_real(monkeypatch):
    """Os testes nunca leem o .env real: variáveis de ambiente vencem o arquivo.
    Sem isto, PUBLISHER=instagrapi do .env de produção faria teste tentar logar na conta."""
    monkeypatch.setenv("PUBLISHER", "dry_run")
    monkeypatch.setenv("SOURCE_PROVIDER", "manual")
    monkeypatch.setenv("AUTO_DISCOVERY", "false")
    monkeypatch.setenv("OLLAMA_EXE", "")
    monkeypatch.setenv("INSTAGRAPI_USER", "")
    monkeypatch.setenv("INSTAGRAPI_PASSWORD", "")
    monkeypatch.setenv("INSTALOADER_USER", "")
    monkeypatch.setenv("INSTALOADER_PASSWORD", "")
    from app.config import settings as cfg
    if hasattr(cfg.get_settings, "cache_clear"):
        cfg.get_settings.cache_clear()
    yield
    if hasattr(cfg.get_settings, "cache_clear"):
        cfg.get_settings.cache_clear()
