# tests/test_ollama_boot.py
import time

import pytest

from app.ai.ollama_boot import garantir_ollama


class RelogioFalso:
    """Relogio que avanca somente quando dormir() e chamado."""

    def __init__(self, inicio: float = 0.0) -> None:
        self.t = inicio

    def __call__(self) -> float:
        return self.t

    def dormir(self, segundos: float) -> None:
        self.t += segundos


def test_ja_responde_nao_chama_iniciar():
    relogio = RelogioFalso()
    chamadas_iniciar = []

    def responde():
        return True

    def iniciar():
        chamadas_iniciar.append(1)

    resultado = garantir_ollama(
        "http://localhost:11434",
        responde=responde,
        iniciar=iniciar,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is True
    assert chamadas_iniciar == []


def test_cai_e_volta_apos_tres_consultas():
    relogio = RelogioFalso()
    chamadas_iniciar = []
    respostas = iter([False, False, False, False, True])

    def responde():
        return next(respostas)

    def iniciar():
        chamadas_iniciar.append(1)

    resultado = garantir_ollama(
        "http://localhost:11434",
        responde=responde,
        iniciar=iniciar,
        esperar_s=45.0,
        intervalo_s=1.0,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is True
    assert len(chamadas_iniciar) == 1


def test_nunca_responde_devolve_false_apos_esperar_s():
    relogio = RelogioFalso()
    chamadas_iniciar = []

    def responde():
        return False

    def iniciar():
        chamadas_iniciar.append(1)

    resultado = garantir_ollama(
        "http://localhost:11434",
        responde=responde,
        iniciar=iniciar,
        esperar_s=5.0,
        intervalo_s=1.0,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is False
    assert len(chamadas_iniciar) == 1
    assert relogio.t >= 5.0


def test_base_url_remota_devolve_false_sem_iniciar():
    relogio = RelogioFalso()
    chamadas_iniciar = []

    def responde():
        return False

    def iniciar():
        chamadas_iniciar.append(1)

    resultado = garantir_ollama(
        "http://10.0.0.5:11434",
        responde=responde,
        iniciar=iniciar,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is False
    assert chamadas_iniciar == []


def test_iniciar_levanta_oserror_devolve_false():
    relogio = RelogioFalso()

    def responde():
        return False

    def iniciar():
        raise OSError("falha ao subir")

    resultado = garantir_ollama(
        "http://localhost:11434",
        responde=responde,
        iniciar=iniciar,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is False


def test_iniciar_levanta_runtimeerror_devolve_false():
    relogio = RelogioFalso()

    def responde():
        return False

    def iniciar():
        raise RuntimeError("falha ao subir")

    resultado = garantir_ollama(
        "http://localhost:11434",
        responde=responde,
        iniciar=iniciar,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is False


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:11434", "http://127.0.0.1:11434"],
)
def test_hosts_locais_sao_permitidos(base_url):
    relogio = RelogioFalso()
    chamadas_iniciar = []
    respostas = iter([False, True])

    def responde():
        return next(respostas)

    def iniciar():
        chamadas_iniciar.append(1)

    resultado = garantir_ollama(
        base_url,
        responde=responde,
        iniciar=iniciar,
        relogio=relogio,
        dormir=relogio.dormir,
    )

    assert resultado is True
    assert len(chamadas_iniciar) == 1
