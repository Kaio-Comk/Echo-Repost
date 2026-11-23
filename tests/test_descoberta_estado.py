"""Estado da descoberta: espera crescente depois de falha e cache do id do perfil."""
from app.sources.descoberta_estado import EstadoDescoberta


class Relogio:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def _estado(tmp_path, rel):
    return EstadoDescoberta(tmp_path / "descoberta_estado.json", agora=rel)


def test_sem_falha_pode_tentar(tmp_path):
    assert _estado(tmp_path, Relogio()).pode_tentar()


def test_falha_pausa_e_a_espera_cresce(tmp_path):
    rel = Relogio()
    e = _estado(tmp_path, rel)
    e.falha("429")
    assert not e.pode_tentar()
    rel.t += 3600 + 1                       # 1a espera: 1 h
    assert e.pode_tentar()
    e.falha("429")
    rel.t += 3600 + 1
    assert not e.pode_tentar()              # 2a espera: 2 h
    rel.t += 3600
    assert e.pode_tentar()


def test_espera_tem_teto(tmp_path):
    rel = Relogio()
    e = _estado(tmp_path, rel)
    for _ in range(12):
        e.falha("429")
    rel.t += 12 * 3600 + 1
    assert e.pode_tentar()


def test_sessao_expirada_espera_mais_que_429(tmp_path):
    rel = Relogio()
    e = _estado(tmp_path, rel)
    e.falha("login_required")
    rel.t += 3600 + 1
    assert not e.pode_tentar()
    rel.t += 5 * 3600
    assert e.pode_tentar()


def test_sucesso_zera_a_espera(tmp_path):
    rel = Relogio()
    e = _estado(tmp_path, rel)
    e.falha("429")
    e.falha("429")
    e.sucesso()
    assert e.pode_tentar()
    e.falha("429")
    rel.t += 3600 + 1
    assert e.pode_tentar()                  # voltou a 1 h


def test_estado_sobrevive_a_reinicio_e_a_arquivo_corrompido(tmp_path):
    rel = Relogio()
    _estado(tmp_path, rel).falha("429")
    assert not _estado(tmp_path, rel).pode_tentar()
    (tmp_path / "descoberta_estado.json").write_text("{lixo", encoding="utf-8")
    assert _estado(tmp_path, rel).pode_tentar()


def test_cache_do_id_do_perfil(tmp_path):
    e = _estado(tmp_path, Relogio())
    assert e.uid_em_cache("perfil") is None
    e.guardar_uid("perfil", "123")
    assert _estado(tmp_path, Relogio()).uid_em_cache("perfil") == "123"
    assert e.uid_em_cache("outro") is None
