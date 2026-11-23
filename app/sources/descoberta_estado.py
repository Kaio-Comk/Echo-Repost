"""Estado da descoberta de Reels: espera crescente depois de falha e cache do id do perfil.

Sem isso, cada ciclo refazia as consultas ao Instagram mesmo depois de 429 ou de sessao
derrubada, o que piora o bloqueio. A espera so vale para a descoberta; publicar o que ja
esta na fila continua normal.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

ESPERA_BASE_S = 3600          # 1 h na primeira falha, dobra a cada nova falha
ESPERA_MAX_S = 12 * 3600
ESPERA_SESSAO_S = 6 * 3600    # sessao derrubada: so o Kaio resolve, nao adianta insistir antes


class EstadoDescoberta:
    def __init__(self, caminho: Path, agora: Callable[[], float] = time.time) -> None:
        self.caminho = Path(caminho)
        self._agora = agora

    def _ler(self) -> dict:
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def _gravar(self, dados: dict) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_text(json.dumps(dados), encoding="utf-8")

    def pode_tentar(self) -> bool:
        return self._agora() >= float(self._ler().get("pausado_ate", 0))

    def segundos_de_espera(self) -> int:
        return max(0, int(float(self._ler().get("pausado_ate", 0)) - self._agora()))

    def falha(self, motivo: str) -> None:
        dados = self._ler()
        falhas = int(dados.get("falhas", 0)) + 1
        espera = min(ESPERA_BASE_S * 2 ** (falhas - 1), ESPERA_MAX_S)
        if motivo == "login_required":
            espera = max(espera, ESPERA_SESSAO_S)
        dados.update(falhas=falhas, motivo=motivo, pausado_ate=self._agora() + espera)
        self._gravar(dados)

    def sucesso(self) -> None:
        dados = self._ler()
        dados.update(falhas=0, motivo="", pausado_ate=0)
        self._gravar(dados)

    def uid_em_cache(self, username: str) -> str | None:
        uid = self._ler().get("uids", {}).get(username)
        return str(uid) if uid else None

    def guardar_uid(self, username: str, uid: str) -> None:
        dados = self._ler()
        dados.setdefault("uids", {})[username] = str(uid)
        self._gravar(dados)
