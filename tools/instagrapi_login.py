#!/usr/bin/env python3
"""Login interativo do instagrapi (gera a sessão de publicação).

POR QUE
   Logar pela primeira vez pode exigir 2FA ou aprovação de "novo login" no app.
   Fazer isso UMA vez aqui (interativo) e salvar a sessão reduz bloqueios depois.

USO (rode VOCÊ MESMO — é a sua conta):
   ./venv/bin/python tools/instagrapi_login.py
   (usa INSTAGRAPI_USER/INSTAGRAPI_PASSWORD do .env; pede o código 2FA se preciso)

Resultado: salva a sessão em data/instagrapi_session.json, que o
InstagrapiPublisher reutiliza nas publicações.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Rodando `python tools/xxx.py` a raiz do projeto não está no sys.path: sem isto `import app` falha.
_RAIZ_DO_PROJETO = _Path(__file__).resolve().parents[1]
if str(_RAIZ_DO_PROJETO) not in _sys.path:
    _sys.path.insert(0, str(_RAIZ_DO_PROJETO))

import sys
import time

from app.config.settings import get_settings

ESPERA_CODIGO_S = 300


def esperar_codigo(arquivo: _Path, limite_s: int = ESPERA_CODIGO_S) -> str:
    """Lê o código de 6 dígitos de um arquivo, para quem roda sem teclado (terminal do `!`).
    Quem tem teclado pode simplesmente digitar: sem stdin interativo, o arquivo é usado."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.unlink(missing_ok=True)
    print(f"O Instagram pediu um codigo. Escreva os 6 digitos em: {arquivo}", flush=True)
    print(f"(ex.: echo 123456 > \"{arquivo.as_posix()}\"). Aguardando ate {limite_s} s...", flush=True)
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        if arquivo.exists():
            codigo = "".join(ch for ch in arquivo.read_text(encoding="utf-8", errors="ignore") if ch.isdigit())
            if len(codigo) == 6:
                arquivo.unlink(missing_ok=True)   # o código não fica guardado
                return codigo
        time.sleep(2)
    raise SystemExit("Tempo esgotado esperando o codigo. Rode o login de novo.")


def main() -> int:
    from instagrapi import Client
    from instagrapi.exceptions import TwoFactorRequired

    s = get_settings()
    user = s.instagrapi_user.strip()
    password = s.instagrapi_password.strip()
    if not user or not password:
        sys.exit("Configure INSTAGRAPI_USER e INSTAGRAPI_PASSWORD no .env antes.")

    session_path = s.instagrapi_session_path
    session_path.parent.mkdir(parents=True, exist_ok=True)
    arquivo_codigo = s.data_path / "codigo_2fa.txt"

    cl = Client()
    cl.challenge_code_handler = lambda _usuario, _escolha: esperar_codigo(arquivo_codigo)
    if session_path.exists():
        try:
            cl.load_settings(session_path)
            print("Sessao existente carregada, validando...")
        except Exception:
            pass

    if not session_path.exists():
        # Guarda a identidade do "aparelho" antes de logar: se o Instagram pedir aprovação no app,
        # a próxima tentativa reaparece como o MESMO aparelho já aprovado, em vez de um novo.
        cl.dump_settings(session_path)

    try:
        cl.login(user, password)
    except TwoFactorRequired:
        cl.login(user, password, verification_code=esperar_codigo(arquivo_codigo))

    cl.dump_settings(session_path)
    me = cl.account_info()
    print(f"OK: logado como @{me.username}. Sessao salva em {session_path}")
    print("Agora: PUBLISHER=instagrapi no .env e rode cli.py publish / scheduler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
