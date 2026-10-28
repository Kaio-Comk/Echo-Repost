# tests/test_falhas.py
"""Testes do FalhasStore."""

from __future__ import annotations

import json

from app.services.falhas import FalhasStore


def test_conta_tentativas(tmp_path):
    store = FalhasStore(tmp_path / "falhas.json")
    assert store.tentativas(1) == 0
    assert store.registrar(1, "erro a") == 1
    assert store.registrar(1, "erro b") == 2
    assert store.tentativas(1) == 2


def test_entra_em_quarentena_em_tres(tmp_path):
    store = FalhasStore(tmp_path / "falhas.json")
    store.registrar(7, "e1")
    store.registrar(7, "e2")
    assert store.em_quarentena(7) is False
    store.registrar(7, "e3")
    assert store.em_quarentena(7) is True


def test_limpar_tira_da_quarentena(tmp_path):
    store = FalhasStore(tmp_path / "falhas.json")
    for i in range(3):
        store.registrar(9, f"e{i}")
    assert store.em_quarentena(9) is True
    store.limpar(9)
    assert store.em_quarentena(9) is False
    assert store.tentativas(9) == 0


def test_persiste_entre_instancias(tmp_path):
    caminho = tmp_path / "falhas.json"
    a = FalhasStore(caminho)
    a.registrar(3, "falha")
    a.registrar(3, "falha2")
    b = FalhasStore(caminho)
    assert b.tentativas(3) == 2
    assert b.em_quarentena(3) is False


def test_arquivo_corrompido_nao_quebra(tmp_path):
    caminho = tmp_path / "falhas.json"
    caminho.write_text("{isso nao e json", encoding="utf-8")
    store = FalhasStore(caminho)
    assert store.tentativas(1) == 0
    assert store.registrar(1, "ok") == 1


def test_erro_longo_cortado_em_300(tmp_path):
    caminho = tmp_path / "falhas.json"
    store = FalhasStore(caminho)
    store.registrar(5, "x" * 1000)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert len(dados["5"]["ultimo_erro"]) == 300
