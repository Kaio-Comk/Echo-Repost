"""Importação da sessão do Firefox para o instagrapi: o valor da sessão nunca vaza e a conta tem que ser a certa."""
import importlib.util
import shutil
import sqlite3
import sys
from pathlib import Path

CAMINHO = Path(__file__).resolve().parents[1] / "tools" / "instagrapi_sessionid.py"
spec = importlib.util.spec_from_file_location("instagrapi_sessionid", CAMINHO)
mod = importlib.util.module_from_spec(spec)
sys.modules["instagrapi_sessionid"] = mod
spec.loader.exec_module(mod)


def test_sessionid_vem_decodificado():
    linhas = [("csrftoken", "x"), ("sessionid", "123%3Aabc%3A28%3AAYd")]
    assert mod.extrair_sessionid(linhas) == "123:abc:28:AYd"


def test_sem_sessionid_devolve_none():
    assert mod.extrair_sessionid([("csrftoken", "x"), ("sessionid", "")]) is None
    assert mod.extrair_sessionid([]) is None


def test_usuario_confere_ignora_caixa_arroba_e_espacos():
    assert mod.usuario_confere("@NetHub_Filmes ", "nethub_filmes")
    assert not mod.usuario_confere("nethub_filmes", "conta_descartavel")
    assert not mod.usuario_confere("", "alguem")


def test_ler_cookies_filtra_so_instagram_e_nao_mexe_no_original(tmp_path):
    original = tmp_path / "cookies.sqlite"
    conn = sqlite3.connect(original)
    conn.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT)")
    conn.executemany("INSERT INTO moz_cookies VALUES (?,?,?)", [
        (".instagram.com", "sessionid", "a%3Ab"), (".outrosite.com", "sessionid", "nao"),
    ])
    conn.commit()
    conn.close()
    antes = original.read_bytes()
    assert mod.ler_cookies(str(original)) == [("sessionid", "a%3Ab")]
    assert original.read_bytes() == antes
