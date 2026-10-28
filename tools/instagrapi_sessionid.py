#!/usr/bin/env python3
"""Cria a sessão do instagrapi a partir de um login já feito no Firefox (sem código de e-mail ou SMS).

POR QUE
   Conta sem e-mail cadastrado e sem SMS chegando: o desafio de login por senha não tem para onde ir.
   Logada no navegador (aprovando no celular), a sessão do site serve ao instagrapi.

COMO USAR (rode VOCÊ MESMO: lê os cookies do SEU Firefox)
   1) No Firefox, entre em https://www.instagram.com com a conta do NetHub (INSTAGRAPI_USER).
   2) Rode:  ./.venv/Scripts/python.exe tools/instagrapi_sessionid.py
      Outro perfil do Firefox:  ... --cookies "C:/caminho/cookies.sqlite"

SEGURANÇA
   O valor da sessão nunca é impresso. Só é aceita se a conta logada for a de INSTAGRAPI_USER:
   a conta descartável de download não pode virar a do NetHub por engano.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))


def extrair_sessionid(linhas: list[tuple[str, str]]) -> str | None:
    """De pares (nome, valor) de cookies do instagram.com, devolve o sessionid decodificado."""
    for nome, valor in linhas:
        if nome == "sessionid" and valor:
            return unquote(valor)
    return None


def usuario_confere(esperado: str, logado: str) -> bool:
    return bool(esperado) and esperado.strip().lower().lstrip("@") == (logado or "").strip().lower()


def achar_cookiefiles() -> list[str]:
    padroes = [
        os.path.expandvars(r"%APPDATA%/Mozilla/Firefox/Profiles/*/cookies.sqlite"),
        os.path.expanduser("~/.mozilla/firefox/*/cookies.sqlite"),
    ]
    achados = [f for p in padroes for f in glob.glob(p)]
    return sorted(achados, key=os.path.getmtime, reverse=True)


def ler_cookies(cookiefile: str) -> list[tuple[str, str]]:
    """Copia o banco (e o -wal, onde ficam os cookies mais novos) e lê a cópia: o Firefox trava o original."""
    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "cookies.sqlite"
        shutil.copy2(cookiefile, destino)
        for sufixo in ("-wal", "-shm"):
            if os.path.exists(cookiefile + sufixo):
                shutil.copy2(cookiefile + sufixo, str(destino) + sufixo)
        conn = sqlite3.connect(destino)
        try:
            return conn.execute(
                "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
            ).fetchall()
        finally:
            conn.close()


def main() -> int:
    from instagrapi import Client

    from app.config.settings import get_settings

    ap = argparse.ArgumentParser()
    ap.add_argument("--cookies", help="caminho do cookies.sqlite de um perfil específico do Firefox")
    args = ap.parse_args()

    s = get_settings()
    esperado = s.instagrapi_user.strip()
    if not esperado:
        sys.exit("Configure INSTAGRAPI_USER no .env antes.")
    candidatos = [args.cookies] if args.cookies else achar_cookiefiles()
    if not candidatos:
        sys.exit("Nenhum cookies.sqlite do Firefox encontrado. Entre no Instagram pelo Firefox primeiro.")

    session_path = s.instagrapi_session_path
    session_path.parent.mkdir(parents=True, exist_ok=True)
    vistos: list[str] = []
    for arquivo in candidatos:
        try:
            sessionid = extrair_sessionid(ler_cookies(arquivo))
        except (OSError, sqlite3.Error) as exc:
            print(f"Pulei um perfil ({type(exc).__name__}).")
            continue
        if not sessionid:
            continue
        cl = Client()
        if session_path.exists():
            try:
                cl.load_settings(session_path)      # mantém a identidade do aparelho já usada
            except Exception:
                pass
        try:
            cl.login_by_sessionid(sessionid)
            quem = cl.account_info().username
        except Exception as exc:
            print(f"Sessão de um perfil não funcionou ({type(exc).__name__}).")
            continue
        if not usuario_confere(esperado, quem):
            vistos.append(quem)
            continue
        cl.dump_settings(session_path)
        print(f"OK: sessão de @{quem} salva em {session_path}")
        print("Agora o PUBLISHER=instagrapi pode publicar. Não precisa de código nem de senha.")
        return 0

    if vistos:
        sys.exit(f"Os perfis do Firefox estão logados como {', '.join('@' + v for v in vistos)}, "
                 f"não como @{esperado}. Entre com a conta do NetHub e rode de novo.")
    sys.exit("Nenhuma sessão válida do Instagram no Firefox. Entre pelo site e rode de novo.")


if __name__ == "__main__":
    raise SystemExit(main())
