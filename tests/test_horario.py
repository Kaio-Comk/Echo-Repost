"""Testes de proximo_horario."""
from datetime import datetime, timedelta, timezone
import random
import pytest
from app.schedulers.horario import proximo_horario

TZ = timezone(timedelta(hours=-3))
GAP = 3.0


def dt(h, m=0, d=1):
    return datetime(2024, 6, d, h, m, tzinfo=TZ)


def janela(ini, fim):
    return dt(ini), dt(fim)


def test_manha_antes_abertura_sorteia_hoje():
    r = proximo_horario(dt(6), 0, 1, None, 8, 20, random.Random(1))
    assert dt(8, 5) <= r <= dt(20)
    assert r.tzinfo == TZ


def test_nunca_antes_de_agora_mais_5():
    for s in range(50):
        r = proximo_horario(dt(10, 30), 0, 1, None, 8, 20, random.Random(s))
        assert r >= dt(10, 35)


def test_respeita_gap_ultimo_mesmo_dia():
    u = dt(9)
    for s in range(50):
        r = proximo_horario(dt(9, 10), 0, 1, u, 8, 20, random.Random(s))
        assert r >= u + timedelta(hours=GAP)


def test_cota3_deixa_espaco():
    fim = dt(20)
    for s in range(50):
        r = proximo_horario(dt(8), 0, 3, None, 8, 20, random.Random(s))
        assert r <= fim - 2 * timedelta(hours=GAP)


def test_cota_feita_vai_amanha():
    r = proximo_horario(dt(10), 1, 1, None, 8, 20, random.Random(2))
    assert dt(8, d=2) <= r <= dt(20, d=2)
    assert r > dt(10)


def test_depois_fim_janela_vai_amanha():
    r = proximo_horario(dt(21), 0, 1, None, 8, 20, random.Random(3))
    assert dt(8, d=2) <= r <= dt(20, d=2)


def test_nao_cabe_mais_hoje_vai_amanha():
    r = proximo_horario(dt(20), 0, 3, None, 8, 20, random.Random(4))
    assert r >= dt(8, d=2)


def test_fim24():
    r = proximo_horario(dt(6), 0, 1, None, 8, 24, random.Random(5))
    assert dt(8, 5) <= r < dt(0, 0, 2)


@pytest.mark.parametrize("s", range(200))
def test_200_sorteios_dentro_janela(s):
    agora = dt(9)
    r = proximo_horario(agora, 0, 2, None, 8, 20, random.Random(s))
    assert dt(8) <= r <= dt(20)
    assert r > agora


def test_seeds_diferentes():
    a = proximo_horario(dt(6), 0, 1, None, 8, 20, random.Random(0))
    b = proximo_horario(dt(6), 0, 1, None, 8, 20, random.Random(1))
    assert a != b


@pytest.mark.parametrize("ini,fim", [(10, 10), (8, 25)])
def test_valueerror(ini, fim):
    with pytest.raises(ValueError):
        proximo_horario(dt(6), 0, 1, None, ini, fim, random.Random(0))


def test_mantem_tzinfo():
    r = proximo_horario(dt(6), 0, 1, None, 8, 20, random.Random(7))
    assert r.tzinfo == TZ
