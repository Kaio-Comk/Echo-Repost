"""Edita legenda original de Reel para republicacao no NetHub."""
import re
import unicodedata
_RX_TEC = re.compile(r'^\s*Hashtags originais.*$', re.I | re.M)
_RX_EDIT = re.compile(r'[ \t]*\|[ \t]*EDIT[ \t]*\|[ \t]*', re.I)
_RX_TAGS = re.compile(r'\bTAGS:\s*', re.I)
_RX_URL = re.compile(r'https?://\S+|www\.\S+|\S+@\S+\.\S+', re.I)
_RX_HASH = re.compile(r'#\w+', re.UNICODE)
_RX_ESP = re.compile(r'[ \t]+$', re.M)
_RX_BL = re.compile(r'\n{3,}')
def _sem_acento(s: str) -> str:
    """Remove acentos para comparacao."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
def _linha_ruim(ln: str, u: str) -> bool:
    """Verifica se linha deve ser removida."""
    s = _sem_acento(ln).lower().strip()
    if u and ('@' + u.lower()) in ln.lower():
        return True
    for p in ('siga', 'segue', 'follow', 'marque', 'credito', 'creditos'):
        if s.startswith(p):
            return True
    if ln.lstrip().startswith('\U0001F4FA'):
        return True
    for p in ('onde assistir', 'assista na', 'assista no', 'disponivel na', 'disponivel no'):
        if s.startswith(p):
            return True
    return False
def _limpa(t: str) -> str:
    """Limpa espacos e linhas em branco."""
    t = _RX_ESP.sub('', t)
    t = _RX_BL.sub('\n\n', t)
    return t.strip()
def editar_legenda_original(texto: str, usuario_origem: str, cta: str, hashtags_extra: str = "", max_hashtags: int = 8) -> str:
    """Edita legenda original para republicacao."""
    t = _RX_TEC.sub('', texto)
    t = _RX_EDIT.sub('', t)
    t = _RX_TAGS.sub('', t)
    t = _RX_URL.sub('', t)
    linhas = [ln for ln in t.split('\n') if not _linha_ruim(ln, usuario_origem)]
    t = '\n'.join(linhas)
    vistas = set()
    ordem = []
    def _add(h: str):
        k = h.lower()
        if k not in vistas:
            vistas.add(k)
            ordem.append(h)
    for m in _RX_HASH.findall(t):
        if len([x for x in ordem]) < max_hashtags:
            _add(m)
    t = _RX_HASH.sub('', t)
    for m in _RX_HASH.findall(hashtags_extra or ''):
        _add(m)
    t = _limpa(t)
    if len(t) < 15:
        t = ''
    bloco = ' '.join(ordem)
    limite = max(0, 2200 - (len(cta) + 2) - (len(bloco) + 1 if bloco else 0))
    if len(t) > limite:
        t = re.sub(r'#\w*$', '', t[:limite]).rstrip()
    if 'bio' not in t.lower():
        t = (t + '\n\n' + cta).strip() if t else cta
    return (t + '\n' + bloco).strip() if bloco else t
