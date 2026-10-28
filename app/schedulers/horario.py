from datetime import datetime, timedelta
import random

def proximo_horario(agora: datetime, feitas_hoje: int, cota_hoje: int, ultimo: datetime | None, inicio_h: int,
                    fim_h: int, rng: random.Random, gap_min_h: float = 3.0, cota_amanha: int | None = None) -> datetime:
    """Escolhe horario aleatorio para proxima publicacao na janela diaria."""
    if not (0 <= inicio_h < fim_h <= 24):
        raise ValueError("janela invalida")
    dia_ini = agora.replace(hour=inicio_h, minute=0, second=0, microsecond=0)
    dia_fim = dia_ini + timedelta(hours=fim_h - inicio_h)
    gap = timedelta(hours=gap_min_h)
    if feitas_hoje < cota_hoje and agora < dia_fim:
        restantes = cota_hoje - feitas_hoje
        mais_cedo = max(agora + timedelta(minutes=5), dia_ini)
        if ultimo is not None and ultimo.date() == agora.date():
            mais_cedo = max(mais_cedo, ultimo + gap)
        mais_tarde = dia_fim - (restantes - 1) * gap
        if mais_cedo < mais_tarde:
            d = (mais_tarde - mais_cedo).total_seconds()
            return mais_cedo + timedelta(seconds=rng.uniform(0, d))
    ini_amanha = dia_ini + timedelta(days=1)
    n = cota_amanha if cota_amanha is not None else max(cota_hoje, 1)
    fim_util = ini_amanha + timedelta(hours=fim_h - inicio_h) - (n - 1) * gap
    fim_util = max(fim_util, ini_amanha)
    d = (fim_util - ini_amanha).total_seconds()
    return ini_amanha + timedelta(seconds=rng.uniform(0, d))
