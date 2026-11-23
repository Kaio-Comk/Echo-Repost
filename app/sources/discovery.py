"""Descoberta automática de Reels novos pela API web do instaloader.

Usa a SESSÃO do navegador da conta descartável (arquivo do instaloader), a mesma que o
download já usa. Antes usava o instagrapi, que finge ser o app de celular: com cookie de
navegador o Instagram derrubava a sessão em segundos (403 login_required, 29/10/2026).
O instaloader fala a API web, que combina com esse cookie.

⚠️ NÃO-oficial: pode violar o ToS da Meta e estressar a conta usada. Opt-in, por sua conta e risco.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

from app.config.settings import get_settings
from app.sources.descoberta_estado import EstadoDescoberta
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _arquivo_de_sessao(user: str) -> Path:
    """Onde o instaloader guarda a sessão (no Windows, %LOCALAPPDATA%/Instaloader)."""
    from instaloader.instaloader import get_default_session_filename

    return Path(get_default_session_filename(user))


def _instaloader_sessionid(user: str) -> Optional[str]:
    """Extrai o cookie `sessionid` da sessão salva pelo instaloader."""
    path = _arquivo_de_sessao(user)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as fh:
            cookies = pickle.load(fh)
        return cookies.get("sessionid")
    except Exception as exc:  # pragma: no cover - sessão corrompida
        logger.warning("Não consegui ler sessionid do instaloader: %s", exc)
        return None


def _sessao_expirada(exc: Exception) -> bool:
    """True quando o Instagram recusou a sessao (login_required), nao quando so limitou o ritmo (429)."""
    nome = type(exc).__name__
    texto = str(exc).lower()
    return nome in ("LoginRequired", "LoginRequiredException") or "login_required" in texto or "redirected to login" in texto or "login required" in texto


class InstagrapiDiscovery:
    """Nome mantido por compatibilidade com o agendador; a implementação é do instaloader."""

    def __init__(self) -> None:
        s = get_settings()
        self.session_user = s.instaloader_user.strip()
        self.amount = s.discovery_amount

    def _buscar(self, username: str) -> List[str]:
        """Shortcodes dos Reels mais recentes do perfil (mais novo primeiro). Levanta se o Instagram recusar."""
        import instaloader

        loader = instaloader.Instaloader(
            download_pictures=False, download_videos=False, download_video_thumbnails=False,
            download_comments=False, save_metadata=False, quiet=True,
            max_connection_attempts=1,          # sem retentativa interna: quem decide esperar é o EstadoDescoberta
        )
        if not self.session_user:
            raise RuntimeError("Sem INSTALOADER_USER: crie a sessão com tools/import_firefox_session.py.")
        loader.load_session_from_file(self.session_user)
        perfil = instaloader.Profile.from_username(loader.context, username)
        codigos: List[str] = []
        for post in perfil.get_posts():
            if len(codigos) >= self.amount:
                break
            if not post.is_video:
                continue
            tipo = getattr(post, "product_type", "") or "clips"
            if tipo != "clips":
                continue
            codigos.append(post.shortcode)
        return codigos

    def _estado(self) -> EstadoDescoberta:
        return EstadoDescoberta(get_settings().data_path / "descoberta_estado.json")

    def discover(self, username: str) -> List[str]:
        """Retorna URLs dos Reels mais recentes do perfil (mais novo primeiro).

        Depois de uma falha (429, sessão derrubada) fica em pausa com espera crescente: insistir a
        cada ciclo só piora o bloqueio.
        """
        estado = self._estado()
        if not estado.pode_tentar():
            logger.info("Descoberta em pausa por mais %d min (falha anterior).", estado.segundos_de_espera() // 60)
            return []
        try:
            codigos = self._buscar(username)
        except Exception as exc:
            sessao = _sessao_expirada(exc)
            estado.falha("login_required" if sessao else "erro")
            if sessao:
                logger.error(
                    "Descoberta: o Instagram recusou a sessão da conta de download (%s). Entre nessa conta no "
                    "Firefox e rode tools/import_firefox_session.py %s. Nova tentativa em %d h.",
                    exc, self.session_user or "<usuario>", estado.segundos_de_espera() // 3600,
                )
            else:
                logger.error("Descoberta falhou: %s. Nova tentativa em %d min.", exc, estado.segundos_de_espera() // 60)
            return []

        estado.sucesso()
        urls = [f"https://www.instagram.com/reel/{c}/" for c in codigos]
        logger.info("Descoberta: %d Reel(s) de @%s.", len(urls), username)
        return urls
