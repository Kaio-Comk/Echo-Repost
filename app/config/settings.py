"""Configuração central da aplicação.

Usa pydantic-settings para carregar variáveis do ambiente / .env com
validação forte de tipos. É a única fonte de verdade de configuração —
nenhum módulo deve ler ``os.environ`` diretamente (SOLID: dependa de
abstrações, não de detalhes do ambiente).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (…/InstaRepost). Permite caminhos relativos no .env.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Banco ---
    database_url: str = "sqlite:///database/instarepost.db"

    # --- Logging ---
    log_level: str = "INFO"
    log_dir: str = "logs"

    # --- Diretórios ---
    download_dir: str = "downloads"
    data_dir: str = "data"

    # --- Ingestão ---
    source_provider: str = "manual"
    target_username: str = "perfil_autorizado"
    watch_dir: str = "data/inbox"

    # Login do instaloader (apenas se SOURCE_PROVIDER=instaloader).
    # ⚠️ Use uma conta DESCARTÁVEL — automação pode resultar em limitação/ban pela Meta.
    instaloader_user: str = ""
    # Opcional: se vazio, o adaptador usa uma sessão salva (recomendado, lida com 2FA).
    instaloader_password: str = ""
    instaloader_max_items: int = 6

    # --- Validação de download ---
    max_video_mb: float = 300.0
    min_video_mb: float = 0.05
    # Armazenado como CSV (pydantic-settings não faz JSON-parse de str). Use .allowed_extensions.
    allowed_extensions_raw: str = Field(default=".mp4,.mov", alias="ALLOWED_EXTENSIONS")

    # --- IA local ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"
    ollama_timeout: int = 120
    # Se preenchidos, o robô religa o Ollama sozinho quando ele estiver desligado (só em localhost).
    ollama_exe: str = ""
    ollama_models_dir: str = ""
    default_caption_style: str = "viral"
    # editar_original: reaproveita a legenda do Reel de origem (limpa, com CTA e hashtags do NetHub);
    # ia: gera uma legenda nova com o Ollama. Reel sem legenda cai na IA nos dois casos.
    caption_mode: str = "editar_original"
    caption_hashtags_extra: str = "#nethub"
    # CTA anexado automaticamente se a IA esquecer de citar o link na bio.
    bio_cta: str = "🎬 Link pra assistir na nossa bio!"

    # --- Aprovação ---
    require_manual_approval: bool = True

    # --- Publicação ---
    publisher: str = "dry_run"
    ig_user_id: str = ""
    ig_access_token: str = ""
    public_media_base_url: str = ""
    # Base da API oficial:
    #   Login por Instagram (recomendado): https://graph.instagram.com/v25.0
    #   Login por Facebook (clássico):     https://graph.facebook.com/v25.0
    ig_api_base: str = "https://graph.instagram.com/v25.0"

    # Publisher não-oficial (instagrapi) — publica na sua própria conta.
    # ⚠️ Viola ToS da Meta e arrisca ban. Use uma sessão salva p/ reduzir challenges.
    instagrapi_user: str = ""
    instagrapi_password: str = ""
    instagrapi_session_file: str = "data/instagrapi_session.json"

    # --- Scheduler ---
    poll_interval_seconds: int = 900
    # Janela diária de publicação (hora local) e fuso: fora dela o agendador só dorme.
    # Limite por dia com subida gradual (1 na 1a semana, 2 até a 3a, depois até o teto) e espaço mínimo entre posts.
    max_posts_per_day: int = 3
    min_gap_hours: float = 3.0
    window_start_hour: int = 8
    window_end_hour: int = 22
    timezone: str = "America/Sao_Paulo"
    # Fila de URLs consumida pelo scheduler (modo instaloader): 1 link por linha.
    url_queue_file: str = "data/queue.txt"
    # Descoberta automática: busca Reels novos do TARGET_USERNAME e enche a fila.
    auto_discovery: bool = False
    discovery_amount: int = 30  # quantos Reels buscar por ciclo (folga p/ não perder bursts)

    # --- Web ---
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    @property
    def allowed_extensions(self) -> List[str]:
        """Lista normalizada de extensões permitidas (a partir do CSV do .env)."""
        return [e.strip().lower() for e in self.allowed_extensions_raw.split(",") if e.strip()]

    # ---- Helpers de caminho absoluto ----
    def _abs(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else (BASE_DIR / p)

    @property
    def download_path(self) -> Path:
        return self._abs(self.download_dir)

    @property
    def data_path(self) -> Path:
        return self._abs(self.data_dir)

    @property
    def watch_path(self) -> Path:
        return self._abs(self.watch_dir)

    @property
    def log_path(self) -> Path:
        return self._abs(self.log_dir)

    @property
    def caption_styles_path(self) -> Path:
        return BASE_DIR / "app" / "config" / "caption_styles.yaml"

    @property
    def url_queue_path(self) -> Path:
        return self._abs(self.url_queue_file)

    @property
    def instagrapi_session_path(self) -> Path:
        return self._abs(self.instagrapi_session_file)

    def ensure_dirs(self) -> None:
        """Cria os diretórios de trabalho se ainda não existirem."""
        for p in (self.download_path, self.data_path, self.watch_path, self.log_path):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuração (cacheado para o ciclo de vida do processo)."""
    return Settings()
