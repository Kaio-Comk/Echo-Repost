import logging

from app.utils.redact import RedactingFilter, redact


def test_query_string():
    assert redact("GET https://x/y?access_token=SEGREDO123&a=1") == "GET https://x/y?access_token=***&a=1"


def test_json_e_repr_de_dict():
    assert redact('{"access_token": "SEGREDO123", "ok": 1}') == '{"access_token": "***", "ok": 1}'
    assert "SEGREDO123" not in redact("{'password': 'SEGREDO123'}")


def test_bearer():
    assert redact("Authorization: Bearer abc.DEF-123") == "Authorization: Bearer ***"


def test_prefixo_de_token_da_meta():
    token = "EAA" + "a" * 50
    assert token not in redact(f"falhou com {token} no corpo")


def test_texto_sem_segredo_fica_igual():
    assert redact("Publicado vídeo 3: 1789") == "Publicado vídeo 3: 1789"


def test_filtro_mascara_mensagem_e_traceback():
    rec = logging.LogRecord(
        "t", logging.ERROR, "f", 1, "falha %s", ("https://x/y?access_token=SEGREDO123&a=1",), None
    )
    try:
        raise RuntimeError("erro em ?token=SEGREDO123")
    except RuntimeError:
        import sys

        rec.exc_info = sys.exc_info()
    assert RedactingFilter().filter(rec) is True
    assert "SEGREDO123" not in rec.msg
    assert "SEGREDO123" not in rec.exc_text
