"""Inicialização do servidor Ollama.

Fornece utilitários para garantir que o servidor Ollama esteja disponível,
subindo-o localmente quando necessário.
"""

from __future__ import annotations

import os
import subprocess
import time
from urllib.parse import urlparse

import requests


def responde_padrao(base_url: str) -> bool:
    """Verifica se o servidor Ollama responde em base_url/api/version."""
    try:
        r = requests.get(base_url.rstrip("/") + "/api/version", timeout=3)
        return r.ok
    except requests.RequestException:
        return False


def iniciar_padrao(exe: str, models_dir: str) -> None:
    """Sobe o servidor Ollama via `exe serve` com OLLAMA_MODELS configurado."""
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = models_dir

    kwargs = {
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )

    subprocess.Popen([exe, "serve"], **kwargs)


def _host_local(base_url: str) -> bool:
    """Retorna True se o host de base_url for localhost ou 127.0.0.1."""
    try:
        host = urlparse(base_url).hostname
    except Exception:
        return False
    return host in ("localhost", "127.0.0.1")


def garantir_ollama(
    base_url: str,
    *,
    responde=None,
    iniciar=None,
    esperar_s: float = 45.0,
    intervalo_s: float = 1.0,
    relogio=time.monotonic,
    dormir=time.sleep,
) -> bool:
    """Garante que o servidor Ollama esteja atendendo em base_url.

    Se já responde, retorna True. Caso contrário, tenta subir o servidor
    (apenas para hosts locais) e aguarda até esperar_s segundos.
    """
    if responde is None:
        responde = lambda: responde_padrao(base_url)

    if responde():
        return True

    if not _host_local(base_url):
        return False

    if iniciar is None:
        return False

    try:
        iniciar()
    except (OSError, RuntimeError):
        return False

    inicio = relogio()
    while relogio() - inicio < esperar_s:
        dormir(intervalo_s)
        if responde():
            return True

    return False
