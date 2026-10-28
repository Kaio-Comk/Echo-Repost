"""Serviço de geração de legendas (orquestra a IA local + persistência)."""
from __future__ import annotations

from app.ai import CaptionGenerator
from app.config.settings import get_settings
from app.models.caption import Caption
from app.repositories import CaptionRepository, VideoRepository
from app.utils.logging_config import get_logger
from app.services.legenda_original import editar_legenda_original
from app.utils.validators import ensure_bio_cta

logger = get_logger(__name__)


class CaptionService:
    def __init__(self, session, generator: CaptionGenerator) -> None:
        self.session = session
        self.generator = generator
        self.videos = VideoRepository(session)
        self.captions = CaptionRepository(session)

    def generate_for_video(self, video_id: int, style: str | None = None) -> Caption:
        settings = get_settings()
        style = style or settings.default_caption_style

        video = self.videos.get(video_id)
        if video is None:
            raise ValueError(f"Vídeo {video_id} não encontrado.")

        original = (video.source_caption or "").strip()
        usuario = video.profile.username if video.profile else ""
        if settings.caption_mode == "editar_original" and len(original) >= 15:
            text = editar_legenda_original(original, usuario, settings.bio_cta, settings.caption_hashtags_extra)
            modelo = "original-editada"
        else:
            text = self.generator.generate(
                context=original or "(sem descrição original)",
                style=style,
                target_username=usuario,
            )
            text = ensure_bio_cta(text, settings.bio_cta)  # garante o CTA mesmo se a IA esquecer
            modelo = settings.ollama_model

        caption = self.captions.add(
            Caption(
                video_id=video.id,
                generated_caption=text,
                style=style,
                model=modelo,
                approved=not settings.require_manual_approval,  # auto-aprova se config permitir
            )
        )
        logger.info("Legenda gerada para vídeo %s (estilo=%s, %d chars).", video_id, style, len(text))
        return caption

    def regenerate(self, video_id: int, style: str | None = None) -> Caption:
        """Gera uma nova versão (mantém histórico das anteriores)."""
        return self.generate_for_video(video_id, style)
