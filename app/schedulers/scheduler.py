"""Agendador 24/7: publica 1 vídeo por ciclo, sem repetir.

Lógica de cada ciclo (modo instaloader):
  1. Se NÃO há vídeo pendente de publicação, puxa UMA URL da fila
     (data/queue.txt), baixa e gera a legenda — criando 1 pendente.
  2. Publica EXATAMENTE 1 vídeo pendente (o mais antigo).

Com POLL_INTERVAL_SECONDS=3600 isso resulta em 1 post por hora. Não repete:
  - o banco tem UNIQUE(profile_id, source_post_id);
  - cada vídeo publicado vira published=True (sai da fila de pendentes);
  - cada URL processada é movida para data/queue.done.txt.

No modo manual, processa a pasta data/inbox e publica 1 por ciclo.
"""
from __future__ import annotations

import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from app.config.settings import get_settings
from app.db import init_db, session_scope
from app.models.video import Video
from app.schedulers.agenda import dentro_da_janela
from app.schedulers.cota import RegistroPublicacoes, contar_do_dia, cota_do_dia
from app.schedulers.horario import proximo_horario
from app.services.pipeline_service import PipelineService
from app.sources.instaloader_source import extract_shortcode
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _enrich_queue(settings) -> None:
    """Descoberta automática: busca Reels novos e adiciona à fila (sem repetir)."""
    if not settings.auto_discovery:
        return
    from app.sources.discovery import InstagrapiDiscovery

    urls = InstagrapiDiscovery().discover(settings.target_username)
    if not urls:
        return

    qpath = settings.url_queue_path
    done = qpath.with_suffix(".done.txt")

    # Já conhecidos: o que está na fila, no done e no banco.
    known: set = set()
    for p in (qpath, done):
        if p.exists():
            known.update(
                ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")
            )
    with session_scope() as session:
        db_codes = set(session.scalars(select(Video.source_post_id)))

    novos = []
    for u in urls:
        if u in known:
            continue
        if f"ig:{extract_shortcode(u)}" in db_codes:
            continue
        novos.append(u)

    if novos:
        qpath.parent.mkdir(parents=True, exist_ok=True)
        with open(qpath, "a", encoding="utf-8") as fh:
            fh.write("\n".join(novos) + "\n")
        logger.info("Descoberta adicionou %d Reel(s) novo(s) à fila.", len(novos))


def _pop_one_url(path: Path) -> Optional[str]:
    """Tira a primeira URL válida da fila, reescreve o arquivo e arquiva em .done."""
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    url, kept = None, []
    for ln in lines:
        s = ln.strip()
        if url is None and s and not s.startswith("#"):
            url = s
            continue
        kept.append(ln)
    if url is None:
        return None
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    done = path.with_suffix(".done.txt")
    with open(done, "a", encoding="utf-8") as fh:
        fh.write(url + "\n")
    return url


def _requeue_url(path: Path, url: str) -> None:
    """Devolve a URL ao topo da fila e tira do .done (a ingestão dela falhou)."""
    atual = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(url + "\n" + atual, encoding="utf-8")
    done = path.with_suffix(".done.txt")
    if done.exists():
        restantes = [ln for ln in done.read_text(encoding="utf-8").splitlines() if ln.strip() != url]
        done.write_text("\n".join(restantes) + ("\n" if restantes else ""), encoding="utf-8")


def _recently_posted(settings) -> bool:
    """True se o último post foi há menos que MIN_GAP_HOURS (evita rajadas depois de uma queda ou reinício)."""
    f = settings.data_path / "last_post.txt"
    if not f.exists():
        return False
    try:
        last = float(f.read_text(encoding="utf-8").strip())
    except Exception:
        return False
    return (time.time() - last) < settings.min_gap_hours * 3600


def _mark_posted(settings) -> None:
    (settings.data_path / "last_post.txt").write_text(str(time.time()), encoding="utf-8")
    _registro(settings).adicionar(datetime.now(ZoneInfo(settings.timezone)))


def _registro(settings) -> RegistroPublicacoes:
    return RegistroPublicacoes(settings.data_path / "publicacoes.json")


def _situacao_do_dia(settings):
    """(feitas hoje, cota de hoje, última publicação, cota de amanhã) conforme o registro de publicações."""
    registro = _registro(settings)
    momentos = registro.momentos()
    primeira = registro.primeiro_dia()
    hoje = datetime.now(ZoneInfo(settings.timezone)).date()
    amanha = hoje.fromordinal(hoje.toordinal() + 1)
    return (contar_do_dia(momentos, hoje), cota_do_dia(primeira, hoje, settings.max_posts_per_day),
            momentos[-1] if momentos else None, cota_do_dia(primeira, amanha, settings.max_posts_per_day))


def _tick() -> None:
    settings = get_settings()
    pipeline = PipelineService()
    logger.info("⏱️  Ciclo (origem=%s).", settings.source_provider)

    # 0) Descoberta automática enche a fila (se ligada).
    if settings.source_provider == "instaloader":
        _enrich_queue(settings)

    # 1) Garante que exista pelo menos 1 vídeo pendente de publicação.
    if pipeline.has_pending_publish() == 0:
        if settings.source_provider == "instaloader":
            url = _pop_one_url(settings.url_queue_path)
            if url:
                logger.info("Fila -> processando: %s", url)
                try:
                    pipeline.run_ingestion_urls([url])
                except Exception as exc:
                    # Sem isto a URL já saiu da fila e o Reel se perdia em silêncio.
                    logger.error("Ingestão da URL falhou (%s); devolvida à fila.", exc)
                    _requeue_url(settings.url_queue_path, url)
            else:
                logger.info("Sem pendentes e fila vazia (%s).", settings.url_queue_path)
        else:
            pipeline.run_ingestion()

    # 2) Publica exatamente 1 (se automático e respeitando o intervalo mínimo).
    if settings.require_manual_approval:
        logger.info("Aprovação manual ligada — publique pelo painel.")
        return

    # Renova o token proativamente (mesmo que não publique neste ciclo).
    if settings.publisher == "instagram_graph":
        from app.publishers.token_store import ensure_fresh

        ensure_fresh()

    feitas, cota, _ultimo, _amanha = _situacao_do_dia(settings)
    if feitas >= cota:
        logger.info("Cota de hoje atingida (%d de %d): sem publicar agora.", feitas, cota)
        return

    if _recently_posted(settings):
        logger.info("Post recente (< intervalo mínimo) — pulando publicação neste ciclo.")
        return

    report = pipeline.publish_one()
    for msg in report.messages:
        logger.info(msg)
    if report.published > 0:
        _mark_posted(settings)


def _agendar(scheduler, settings) -> None:
    """Sorteia o próximo horário de publicação: aleatório dentro da janela, respeitando a cota e o espaço mínimo."""
    agora = datetime.now(ZoneInfo(settings.timezone))
    feitas, cota, ultimo, cota_amanha = _situacao_do_dia(settings)
    quando = proximo_horario(agora, feitas, cota, ultimo, settings.window_start_hour, settings.window_end_hour,
                             random.Random(), gap_min_h=settings.min_gap_hours, cota_amanha=cota_amanha)
    scheduler.add_job(_ciclo, "date", run_date=quando, args=[scheduler, settings], id="auto_post",
                      replace_existing=True, misfire_grace_time=3600)
    logger.info("Hoje: %d de %d. Próximo ciclo sorteado: %s", feitas, cota, quando.isoformat(timespec="minutes"))


def _ciclo(scheduler, settings) -> None:
    try:
        agora = datetime.now(ZoneInfo(settings.timezone))
        if dentro_da_janela(agora, settings.window_start_hour, settings.window_end_hour):
            _tick()
        else:
            logger.info("Fora da janela %02dh-%02dh: nada a fazer agora.",
                        settings.window_start_hour, settings.window_end_hour)
    except Exception:
        logger.exception("Ciclo falhou; o próximo já está agendado.")
    finally:
        _agendar(scheduler, settings)


def run_scheduler() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    init_db()

    scheduler = BlockingScheduler(timezone=settings.timezone)
    logger.info("Scheduler 24/7 ativo: até %d por dia (sobe aos poucos), entre %02dh e %02dh (%s), horários sorteados.",
                settings.max_posts_per_day, settings.window_start_hour, settings.window_end_hour, settings.timezone)
    _agendar(scheduler, settings)  # não publica ao ligar: só no horário sorteado
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):  # pragma: no cover
        logger.info("Scheduler encerrado.")


if __name__ == "__main__":  # pragma: no cover
    run_scheduler()
