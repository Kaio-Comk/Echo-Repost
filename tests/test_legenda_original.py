import pytest

from app.services.legenda_original import editar_legenda_original

CTA = "Link pra assistir na nossa bio!"
USUARIO = "cenasemfilmes"
EXTRA = "#nethub"

EXEMPLO = """Esse filme retrata o alzheimer de uma forma linda… | EDIT | 

🎥 O curioso caso de benjamin button 
📺 Netflix, HBO Max. 

🍿 Sinopse: O filme conta a história de um homem que nasce com a aparência de um idoso de 80 anos e vai rejuvenescendo.

TAGS: 
#ocuriosocasodebenjaminbutton #cenas #filme
Hashtags originais: ocuriosocasodebenjaminbutton cenas filme"""


def _editar(texto, **kwargs):
    params = dict(usuario_origem=USUARIO, cta=CTA, hashtags_extra=EXTRA)
    params.update(kwargs)
    return editar_legenda_original(texto, **params)


def test_exemplo_completo():
    out = _editar(EXEMPLO)
    assert "EDIT" not in out
    assert "TAGS" not in out
    assert "Hashtags originais" not in out
    assert "\U0001F4FA" not in out
    assert "Esse filme retrata o alzheimer de uma forma linda" in out
    assert "O curioso caso de benjamin button" in out
    assert "Sinopse" in out
    assert "rejuvenescendo" in out
    assert CTA in out
    linhas = [l for l in out.splitlines() if l.strip()]
    ultima = linhas[-1]
    for tag in ("#ocuriosocasodebenjaminbutton", "#cenas", "#filme", "#nethub"):
        assert tag in ultima
    assert out.index(CTA) < out.index("#ocuriosocasodebenjaminbutton")


def test_linha_usuario_origem_some_outro_fica():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "Siga @cenasemfilmes para mais!\n"
        "Cena editada por @outroperfil, que fez isso."
    )
    out = _editar(texto)
    assert "@cenasemfilmes" not in out
    assert "@outroperfil" in out


def test_url_some():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "Veja em https://exemplo.com/pagina e www.teste.com.br\n"
        "Contato: alguem@exemplo.com"
    )
    out = _editar(texto)
    assert "https://" not in out
    assert "www." not in out
    assert "alguem@exemplo.com" not in out


def test_linhas_segue_somem():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "Segue a gente pra mais conteudo\n"
        "Follow para nao perder\n"
        "Marque um amigo\n"
        "Siga o canal"
    )
    out = _editar(texto)
    low = out.lower()
    for linha in out.splitlines():
        s = linha.strip().lower()
        assert not s.startswith("segue")
        assert not s.startswith("siga")
        assert not s.startswith("follow")
        assert not s.startswith("marque")
    assert "Sinopse boa" in out


def test_hashtags_repetidas_caixas_diferentes():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "#Filme #filme #FILME #Cenas"
    )
    out = _editar(texto)
    linhas = [l for l in out.splitlines() if l.strip()]
    ultima = linhas[-1]
    assert ultima.lower().count("#filme") == 1
    assert ultima.lower().count("#cenas") == 1


def test_max_hashtags_corta_originais_mantem_extras():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "#um #dois #tres #quatro"
    )
    out = _editar(texto, max_hashtags=2)
    linhas = [l for l in out.splitlines() if l.strip()]
    ultima = linhas[-1]
    assert "#um" in ultima
    assert "#dois" in ultima
    assert "#tres" not in ultima
    assert "#quatro" not in ultima
    assert "#nethub" in ultima


def test_texto_so_hashtags_vira_cta_mais_hashtags():
    texto = "#filme #cinema"
    out = _editar(texto)
    assert CTA in out
    assert "#filme" in out
    assert "#cinema" in out
    assert "#nethub" in out


def test_ja_tem_bio_nao_duplica_cta():
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        "Link na bio para assistir."
    )
    out = _editar(texto)
    assert out.lower().count("bio") == 1
    assert CTA not in out


def test_limite_2200_e_hashtags_inteiras():
    corpo = "palavra " * 500
    texto = corpo + "\n#filme #cinema #nethub"
    out = _editar(texto)
    assert len(out) <= 2200
    linhas = [l for l in out.splitlines() if l.strip()]
    ultima = linhas[-1]
    for tag in ("#filme", "#cinema", "#nethub"):
        assert tag in ultima
    assert CTA in out


def test_idempotencia():
    out1 = _editar(EXEMPLO)
    out2 = _editar(out1)
    assert out1 == out2


@pytest.mark.parametrize(
    "linha",
    [
        "\U0001F4FA Assista na Netflix",
        "Onde assistir: Netflix",
        "Assista na HBO Max",
        "Assista no Prime Video",
        "Disponível na Netflix",
        "Disponivel no Globoplay",
    ],
)
def test_linhas_onde_assistir_somem(linha):
    texto = (
        "Sinopse boa e longa o suficiente para passar do limite minimo.\n"
        + linha
    )
    out = _editar(texto)
    assert linha not in out
    assert "Sinopse boa" in out


def test_marcador_edit_nao_cola_o_gancho_no_titulo():
    texto = "Esse filme retrata o alzheimer de uma forma linda… | EDIT | \n\n🎥 O curioso caso de benjamin button\n\nUma sinopse longa o bastante para passar."
    out = _editar(texto)
    assert "EDIT" not in out
    assert "linda…\n\n🎥 O curioso caso" in out
