from xadrez_sem_barreiras.tradutor import TradutorXadrez


def test_traduz_coordenadas_para_notacao():
    tradutor = TradutorXadrez(posicao_camera="brancas_esquerda")

    assert tradutor.para_notacao(0, 0) == "a1"
    assert tradutor.para_notacao(4, 3) == "e4"
    assert tradutor.para_notacao(7, 7) == "h8"


def test_coordenada_invalida_retorna_none():
    tradutor = TradutorXadrez()

    assert tradutor.para_notacao(-1, 0) is None
    assert tradutor.para_notacao(0, 8) is None
