import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.schedulers.cota import cota_do_dia, contar_do_dia, RegistroPublicacoes


@pytest.mark.parametrize("dias,esperado", [(0, 1), (6, 1), (7, 2), (20, 2), (21, 3), (400, 3)])
def test_rampa(dias, esperado):
    hoje = date(2024, 1, 1)
    assert cota_do_dia(hoje - timedelta(days=dias), hoje) == esperado


def test_primeira_none():
    assert cota_do_dia(None, date(2024, 1, 1)) == 1


@pytest.mark.parametrize("teto,esperado", [(2, 2), (1, 1), (0, 0), (-5, 0)])
def test_teto(teto, esperado):
    hoje = date(2024, 1, 1)
    assert cota_do_dia(hoje - timedelta(days=400), hoje, teto) == esperado


def test_contar_do_dia():
    dia = date(2024, 3, 10)
    ms = [
        datetime(2024, 3, 10, 0, 0),
        datetime(2024, 3, 10, 23, 59, 59),
        datetime(2024, 3, 9, 23, 59),
        datetime(2024, 3, 11, 0, 0),
    ]
    assert contar_do_dia(ms, dia) == 2
    assert contar_do_dia([], dia) == 0


def test_ausente(tmp_path):
    r = RegistroPublicacoes(tmp_path / "x" / "r.json")
    assert r.momentos() == []
    assert r.primeiro_dia() is None


def test_persiste_ordena_primeiro(tmp_path):
    p = tmp_path / "r.json"
    r = RegistroPublicacoes(p)
    a = datetime(2024, 5, 2, 10, 0)
    b = datetime(2024, 5, 1, 8, 0)
    r.adicionar(a)
    r.adicionar(b)
    r2 = RegistroPublicacoes(p)
    assert r2.momentos() == [b, a]
    assert r2.primeiro_dia() == date(2024, 5, 1)


def test_corrompido(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{nao json", encoding="utf-8")
    r = RegistroPublicacoes(p)
    assert r.momentos() == []
    r.adicionar(datetime(2024, 1, 1, 12, 0))
    assert r.momentos() == [datetime(2024, 1, 1, 12, 0)]


def test_cria_pasta_e_sem_tmp(tmp_path):
    p = tmp_path / "sub" / "dir" / "r.json"
    r = RegistroPublicacoes(p)
    r.adicionar(datetime(2024, 2, 2, 2, 2))
    assert p.exists()
    assert not p.with_suffix(".tmp").exists()
    assert json.loads(p.read_text(encoding="utf-8")) == ["2024-02-02T02:02:00"]
