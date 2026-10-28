"""A descoberta usa a sessão salva da conta descartável (cookie), não a senha, e acha o arquivo no Windows."""
import pickle

from app.sources import discovery


def test_le_o_sessionid_do_arquivo_padrao_do_instaloader(tmp_path, monkeypatch):
    arquivo = tmp_path / "session-conta"
    arquivo.write_bytes(pickle.dumps({"sessionid": "abc123", "csrftoken": "x"}))
    monkeypatch.setattr(discovery, "_arquivo_de_sessao", lambda usuario: arquivo)
    assert discovery._instaloader_sessionid("conta") == "abc123"


def test_sem_arquivo_devolve_none(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "_arquivo_de_sessao", lambda usuario: tmp_path / "nao-existe")
    assert discovery._instaloader_sessionid("conta") is None


def test_cliente_prefere_a_sessao_a_senha(tmp_path, monkeypatch):
    chamadas = []

    class FakeClient:
        def load_settings(self, _): pass
        def login(self, *a, **k): chamadas.append("senha")
        def login_by_sessionid(self, sid): chamadas.append("sessao:" + sid)
        def dump_settings(self, _): pass

    import sys, types
    monkeypatch.setitem(sys.modules, "instagrapi", types.SimpleNamespace(Client=FakeClient))
    monkeypatch.setenv("INSTALOADER_USER", "conta")
    monkeypatch.setenv("INSTALOADER_PASSWORD", "segredo")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.config import settings as cfg
    cfg.get_settings.cache_clear()
    monkeypatch.setattr(discovery, "_instaloader_sessionid", lambda usuario: "abc123")
    discovery.InstagrapiDiscovery()._client()
    assert chamadas == ["sessao:abc123"]
