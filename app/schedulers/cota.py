import json
import os
from datetime import date, datetime
from pathlib import Path


def cota_do_dia(primeira: date | None, hoje: date, teto: int = 3) -> int:
    """Cota diaria de publicacoes."""
    if teto <= 0:
        return 0
    if primeira is None:
        return min(1, teto)
    d = (hoje - primeira).days
    if d < 7:
        v = 1
    elif d < 21:
        v = 2
    else:
        v = 3
    return min(v, teto)


def contar_do_dia(momentos: list[datetime], dia: date) -> int:
    """Conta momentos no dia."""
    return sum(1 for m in momentos if m.date() == dia)


class RegistroPublicacoes:
    """Registro persistente de publicacoes."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def adicionar(self, momento: datetime) -> None:
        ms = self.momentos()
        ms.append(momento)
        ms.sort()
        self._gravar(ms)

    def momentos(self) -> list[datetime]:
        try:
            txt = self.caminho.read_text(encoding="utf-8")
            dados = json.loads(txt)
            if not isinstance(dados, list):
                return []
            out = []
            for s in dados:
                try:
                    out.append(datetime.fromisoformat(s))
                except (ValueError, TypeError):
                    continue
            out.sort()
            return out
        except (OSError, ValueError, json.JSONDecodeError):
            return []

    def primeiro_dia(self) -> date | None:
        ms = self.momentos()
        return ms[0].date() if ms else None

    def _gravar(self, ms: list[datetime]) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.caminho.with_suffix(".tmp")
        dados = [m.isoformat() for m in ms]
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.caminho)
