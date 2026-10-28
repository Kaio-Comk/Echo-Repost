"""Fila de URLs não perde item quando a ingestão falha; painel recusa POST de outro site."""
from __future__ import annotations

from app.schedulers.scheduler import _pop_one_url, _requeue_url


def test_url_volta_para_a_fila_depois_de_falha(tmp_path):
    fila = tmp_path / "queue.txt"
    fila.write_text("# comentario\nhttps://a/1\nhttps://a/2\n", encoding="utf-8")

    url = _pop_one_url(fila)
    assert url == "https://a/1"
    assert "https://a/1" in fila.with_suffix(".done.txt").read_text(encoding="utf-8")

    _requeue_url(fila, url)
    assert _pop_one_url(fila) == "https://a/1"  # voltou ao topo
    assert _pop_one_url(fila) == "https://a/2"


def test_requeue_sem_done_nem_fila(tmp_path):
    fila = tmp_path / "queue.txt"
    _requeue_url(fila, "https://a/9")
    assert fila.read_text(encoding="utf-8") == "https://a/9\n"
