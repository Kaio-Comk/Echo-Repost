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


def _preparar(tmp_path, monkeypatch, buscar):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.config import settings as cfg
    cfg.get_settings.cache_clear()
    d = discovery.InstagrapiDiscovery()
    monkeypatch.setattr(d, "_buscar", buscar)
    return d


def test_falha_429_pausa_e_nao_insiste_no_proximo_ciclo(tmp_path, monkeypatch):
    chamadas = []

    def buscar(u):
        chamadas.append(u)
        raise RuntimeError("429 Too Many Requests")

    d = _preparar(tmp_path, monkeypatch, buscar)
    assert d.discover("perfil") == []
    assert d.discover("perfil") == []
    assert chamadas == ["perfil"]          # o 2o ciclo nem chamou o Instagram


def test_sessao_recusada_vira_mensagem_clara(tmp_path, monkeypatch, caplog):
    class LoginRequiredException(Exception):
        pass

    def buscar(u):
        raise LoginRequiredException("Redirected to login page")

    d = _preparar(tmp_path, monkeypatch, buscar)
    with caplog.at_level("ERROR"):
        assert d.discover("perfil") == []
    assert "import_firefox_session" in caplog.text


def test_sucesso_monta_as_urls_e_zera_a_pausa(tmp_path, monkeypatch):
    d = _preparar(tmp_path, monkeypatch, lambda u: ["ABC", "DEF"])
    assert d.discover("perfil") == ["https://www.instagram.com/reel/ABC/", "https://www.instagram.com/reel/DEF/"]
    assert d._estado().pode_tentar()


def test_buscar_so_devolve_reels_e_respeita_o_limite(tmp_path, monkeypatch):
    import sys
    import types

    class Post:
        def __init__(self, code, video, tipo):
            self.shortcode, self.is_video, self.product_type = code, video, tipo

    posts = [Post("FOTO", False, "feed"), Post("R1", True, "clips"), Post("VID", True, "feed"),
             Post("R2", True, "clips"), Post("R3", True, "clips")]

    class Perfil:
        def get_posts(self):
            return iter(posts)

    class Loader:
        context = object()
        def __init__(self, **k): pass
        def load_session_from_file(self, user): self.user = user

    fake = types.SimpleNamespace(
        Instaloader=Loader,
        Profile=types.SimpleNamespace(from_username=lambda ctx, u: Perfil()),
    )
    monkeypatch.setitem(sys.modules, "instaloader", fake)
    monkeypatch.setenv("INSTALOADER_USER", "conta")
    monkeypatch.setenv("DISCOVERY_AMOUNT", "2")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.config import settings as cfg
    cfg.get_settings.cache_clear()
    assert discovery.InstagrapiDiscovery()._buscar("perfil") == ["R1", "R2"]
