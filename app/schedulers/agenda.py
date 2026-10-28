"""Agendamento de ciclos dentro de uma janela horária diária."""

from __future__ import annotations

import random
from datetime import datetime, timedelta


def dentro_da_janela(agora: datetime, inicio_h: int, fim_h: int) -> bool:
    """Retorna True se inicio_h <= agora.hour < fim_h (fim_h pode ser 24)."""
    if not (0 <= inicio_h <= 24) or not (0 <= fim_h <= 24):
        raise ValueError("inicio_h e fim_h devem estar em 0..24")
    if inicio_h >= fim_h:
        raise ValueError("inicio_h deve ser menor que fim_h")
    return inicio_h <= agora.hour < fim_h


def _inicio_do_dia(base: datetime, hora: int) -> datetime:
    """Retorna `base` com hora=hora, minuto/segundo/microssegundo zerados."""
    return base.replace(hour=hora, minute=0, second=0, microsecond=0)


def proximo_ciclo(
    agora: datetime,
    intervalo_s: int,
    inicio_h: int,
    fim_h: int,
    rng: random.Random,
    jitter_pct: float = 0.3,
    jitter_abertura_min: int = 45,
) -> datetime:
    """Calcula o próximo instante de execução respeitando a janela horária.

    - candidato = agora + intervalo_s * uniform(1 - jitter_pct, 1 + jitter_pct)
    - Se o candidato cai dentro da janela, retorna o candidato.
    - Se cai antes do início (mesmo dia), retorna o início do dia + atraso aleatório.
    - Se cai depois do fim (ou madrugada seguinte), retorna o início do dia seguinte
      + o mesmo atraso aleatório.
    - Mantém o tzinfo de `agora` e garante resultado >= candidato.
    """
    if not (0 <= inicio_h <= 24) or not (0 <= fim_h <= 24):
        raise ValueError("inicio_h e fim_h devem estar em 0..24")
    if inicio_h >= fim_h:
        raise ValueError("inicio_h deve ser menor que fim_h")
    if intervalo_s < 0:
        raise ValueError("intervalo_s deve ser >= 0")
    if jitter_pct < 0:
        raise ValueError("jitter_pct deve ser >= 0")
    if jitter_abertura_min < 0:
        raise ValueError("jitter_abertura_min deve ser >= 0")

    fator = rng.uniform(1.0 - jitter_pct, 1.0 + jitter_pct)
    candidato = agora + timedelta(seconds=intervalo_s * fator)

    if dentro_da_janela(candidato, inicio_h, fim_h):
        return candidato

    atraso = timedelta(minutes=rng.uniform(0, jitter_abertura_min))

    inicio_hoje = _inicio_do_dia(candidato, inicio_h)

    if candidato < inicio_hoje:
        # Antes da janela no mesmo dia.
        resultado = inicio_hoje + atraso
    else:
        # Depois do fim (ou madrugada seguinte): usa o início do dia seguinte.
        inicio_amanha = inicio_hoje + timedelta(days=1)
        resultado = inicio_amanha + atraso

    # Garantia: nunca retornar antes do candidato.
    if resultado < candidato:
        resultado = candidato
    return resultado
