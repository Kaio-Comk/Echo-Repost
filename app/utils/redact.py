"""Mascara segredos (tokens, senhas) antes de irem para logs e mensagens de erro."""
from __future__ import annotations

import logging
import re

_CHAVES = r"access_token|token|password|senha|client_secret"

# access_token=XYZ (query string) e "access_token": "XYZ" (JSON / repr de dict)
_QUERY = re.compile(rf"(?i)\b({_CHAVES})=([^&\s\"']+)")
_JSON = re.compile(rf"(?i)([\"']({_CHAVES})[\"']\s*:\s*[\"'])([^\"']+)")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_PREFIXO_IG = re.compile(r"\b(?:EAA|IGAA|IGQ)[A-Za-z0-9_-]{40,}")


def redact(texto: str) -> str:
    """Troca o valor de tokens e senhas por '***', mantendo o nome da chave."""
    texto = _QUERY.sub(r"\1=***", texto)
    texto = _JSON.sub(r"\1***", texto)
    texto = _BEARER.sub(r"\1***", texto)
    return _PREFIXO_IG.sub("***", texto)


class RedactingFilter(logging.Filter):
    """Aplica redact() na mensagem já formatada e no traceback do registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True
