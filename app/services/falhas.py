# app/services/falhas.py
"""Armazena falhas de publicacao de videos em JSON com escrita atomica."""

from __future__ import annotations

import json
import os
import pathlib
import time


class FalhasStore:
    """Registra tentativas falhas de publicacao por video."""

    def __init__(self, path: pathlib.Path, max_tentativas: int = 3) -> None:
        self.path = pathlib.Path(path)
        self.max_tentativas = max_tentativas
        self._dados: dict[str, dict] = self._carregar()

    def _carregar(self) -> dict[str, dict]:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                return {}
            return dados
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return {}

    def _salvar(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._dados, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def registrar(self, video_id: int, erro: str) -> int:
        chave = str(video_id)
        entrada = self._dados.get(chave) or {"tentativas": 0}
        tentativas = int(entrada.get("tentativas", 0)) + 1
        self._dados[chave] = {
            "tentativas": tentativas,
            "ultimo_erro": str(erro)[:300],
            "ultima_em": time.time(),
        }
        self._salvar()
        return tentativas

    def limpar(self, video_id: int) -> None:
        chave = str(video_id)
        if chave in self._dados:
            del self._dados[chave]
            self._salvar()

    def em_quarentena(self, video_id: int) -> bool:
        return self.tentativas(video_id) >= self.max_tentativas

    def tentativas(self, video_id: int) -> int:
        entrada = self._dados.get(str(video_id))
        if not entrada:
            return 0
        try:
            return int(entrada.get("tentativas", 0))
        except (TypeError, ValueError):
            return 0
