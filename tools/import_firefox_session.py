#!/usr/bin/env python3
"""Importa a sessão do Instagram do Firefox para o instaloader (conta DESCARTÁVEL de download).

POR QUE ISSO EXISTE
   O Instagram bloqueia login programático por usuário/senha ("Checkpoint required").
   O caminho confiável é reaproveitar a sessão de um navegador onde a conta já está logada.

COMO USAR (rode VOCÊ MESMO: lê os cookies do SEU Firefox)
   1) No Firefox, entre em https://www.instagram.com com a conta DESCARTÁVEL (nunca a do NetHub).
   2) Rode:  ./.venv/Scripts/python.exe tools/import_firefox_session.py
      (usa INSTALOADER_USER do .env; outro perfil do Firefox: --cookies "C:/.../cookies.sqlite")

O arquivo vai para o lugar padrão do instaloader (no Windows, %LOCALAPPDATA%/Instaloader), de onde o
InstaloaderSource o carrega sozinho. O valor da sessão nunca é impresso.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(_RAIZ), str(Path(__file__).resolve().parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from instagrapi_sessionid import achar_cookiefiles, ler_cookies  # noqa: E402  (mesma pasta tools/)


def main() -> int:
    import instaloader
    from instaloader.instaloader import get_default_session_filename

    ap = argparse.ArgumentParser()
    ap.add_argument("usuario", nargs="?", help="usuário da conta descartável (padrão: INSTALOADER_USER do .env)")
    ap.add_argument("--cookies", help="caminho do cookies.sqlite de um perfil específico do Firefox")
    args = ap.parse_args()

    from app.config.settings import get_settings

    esperado = (args.usuario or get_settings().instaloader_user or os.getenv("INSTALOADER_USER", "")).strip().lstrip("@")
    if not esperado:
        sys.exit("Informe o usuário: argumento ou INSTALOADER_USER no .env.")
    nethub = get_settings().instagrapi_user.strip().lower().lstrip("@")
    if esperado.lower() == nethub:
        sys.exit("Esta é a conta do NetHub. Para baixar, use SÓ a conta descartável.")

    candidatos = [args.cookies] if args.cookies else achar_cookiefiles()
    if not candidatos:
        sys.exit("cookies.sqlite do Firefox não encontrado. Entre no Instagram pelo Firefox antes.")

    vistos: list[str] = []
    for arquivo in candidatos:
        try:
            linhas = ler_cookies(arquivo)
        except Exception as exc:
            print(f"Pulei um perfil ({type(exc).__name__}).")
            continue
        if not any(n == "sessionid" and v for n, v in linhas):
            continue
        loader = instaloader.Instaloader(max_connection_attempts=1)
        loader.context._session.cookies.update(linhas)
        logado = loader.test_login()
        if not logado:
            continue
        if logado.lower() != esperado.lower():
            vistos.append(logado)
            continue
        loader.context.username = logado
        destino = get_default_session_filename(logado)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        loader.save_session_to_file(destino)
        print(f"OK: sessão de @{logado} salva em {destino}")
        return 0

    if vistos:
        sys.exit(f"O Firefox está logado como {', '.join('@' + v for v in vistos)}, não como @{esperado}. "
                 "Entre com a conta descartável e rode de novo.")
    sys.exit("Nenhuma sessão válida do Instagram no Firefox. Entre pelo site e rode de novo.")


if __name__ == "__main__":
    raise SystemExit(main())
