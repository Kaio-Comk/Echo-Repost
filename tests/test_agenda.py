import random
from datetime import datetime, timedelta, timezone

import pytest

from app.schedulers.agenda import dentro_da_janela, proximo_ciclo


TZ = timezone(timedelta(hours=-3))


def _dt(hour, minute=0, second=0, tz=TZ):
    return datetime(2024, 6, 10, hour, minute, second, tzinfo=tz)


# ---------- dentro_da_janela ----------

@pytest.mark.parametrize(
    "hora, inicio_h, fim_h, esperado",
    [
        (8, 8, 22, True),    # borda inferior inclusa
        (22, 8, 22, False),  # borda superior exclusa
        (23, 8, 24, True),   # fim_h = 24 (ate meia-noite)
        (0, 8, 24, False),   # antes do inicio
        (7, 8, 22, False),
        (21, 8, 22, True),
    ],
)
def test_dentro_da_janela_bordas(hora, inicio_h, fim_h, esperado):
    assert dentro_da_janela(_dt(hora), inicio_h, fim_h) is esperado


# ---------- proximo_ciclo: dentro da janela ----------

def test_proximo_ciclo_dentro_da_janela_fica_no_intervalo():
    agora = _dt(10, 0, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, 8, 22, rng)

    assert agora + timedelta(seconds=0.7 * 600) <= resultado <= agora + timedelta(seconds=1.3 * 600)


def test_proximo_ciclo_dentro_da_janela_mantem_tzinfo():
    agora = _dt(10, 0, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, 8, 22, rng)

    assert resultado.tzinfo == agora.tzinfo


# ---------- proximo_ciclo: depois do fim -> dia seguinte ----------

def test_proximo_ciclo_depois_do_fim_vira_dia_seguinte():
    agora = _dt(21, 59, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, 8, 22, rng)

    inicio_dia_seguinte = datetime(2024, 6, 11, 8, 0, 0, tzinfo=TZ)
    assert inicio_dia_seguinte <= resultado <= inicio_dia_seguinte + timedelta(minutes=45)
    assert resultado.tzinfo == agora.tzinfo


def test_proximo_ciclo_madrugada_seguinte_vira_dia_seguinte():
    agora = _dt(23, 30, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, 8, 22, rng)

    inicio_dia_seguinte = datetime(2024, 6, 11, 8, 0, 0, tzinfo=TZ)
    assert inicio_dia_seguinte <= resultado <= inicio_dia_seguinte + timedelta(minutes=45)


# ---------- proximo_ciclo: antes do inicio -> mesmo dia ----------

def test_proximo_ciclo_antes_do_inicio_fica_no_mesmo_dia():
    agora = _dt(6, 0, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, 8, 22, rng)

    inicio_mesmo_dia = datetime(2024, 6, 10, 8, 0, 0, tzinfo=TZ)
    assert inicio_mesmo_dia <= resultado <= inicio_mesmo_dia + timedelta(minutes=45)
    assert resultado.day == agora.day
    assert resultado.tzinfo == agora.tzinfo


# ---------- determinismo ----------

def test_proximo_ciclo_determinismo_com_seed_fixa():
    agora = _dt(10, 0, 0)
    r1 = proximo_ciclo(agora, 600, 8, 22, random.Random(7))
    r2 = proximo_ciclo(agora, 600, 8, 22, random.Random(7))
    assert r1 == r2


# ---------- nunca menor que agora + 0.7*intervalo ----------

@pytest.mark.parametrize(
    "hora, inicio_h, fim_h",
    [
        (10, 8, 22),   # dentro
        (6, 8, 22),    # antes do inicio
        (21, 8, 22),   # depois do fim
        (23, 8, 22),   # madrugada seguinte
    ],
)
def test_proximo_ciclo_nunca_menor_que_limite_inferior(hora, inicio_h, fim_h):
    agora = _dt(hora, 0, 0)
    rng = random.Random(7)
    resultado = proximo_ciclo(agora, 600, inicio_h, fim_h, rng)
    assert resultado >= agora + timedelta(seconds=0.7 * 600)


# ---------- ValueError para janela invalida ----------

@pytest.mark.parametrize(
    "inicio_h, fim_h",
    [
        (10, 10),
        (8, 25),
    ],
)
def test_proximo_ciclo_janela_invalida(inicio_h, fim_h):
    agora = _dt(10, 0, 0)
    rng = random.Random(7)
    with pytest.raises(ValueError):
        proximo_ciclo(agora, 600, inicio_h, fim_h, rng)


def test_fim_24_com_candidato_antes_da_abertura_nao_quebra():
    """Janela ate a meia-noite (fim_h=24): candidato de madrugada vira a abertura do mesmo dia."""
    import random
    from datetime import datetime, timedelta, timezone

    from app.schedulers.agenda import proximo_ciclo

    tz = timezone(timedelta(hours=-3))
    agora = datetime(2026, 10, 28, 3, 0, tzinfo=tz)
    r = proximo_ciclo(agora, 3600, 8, 24, random.Random(3))
    assert r.date() == agora.date() and 8 <= r.hour < 9
