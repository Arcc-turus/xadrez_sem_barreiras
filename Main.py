import time

import cv2

from CapturarTabuleiro import BoardDetector
from Segmentador import SegmentadorTabuleiro
from Tradutor import TradutorXadrez
from Xadrez import JogoXadrez


def executar_projeto():
    # Inicialização dos componentes do sistema
    olho = BoardDetector(camera_index=1)
    segmentador = SegmentadorTabuleiro()
    tradutor = TradutorXadrez(posicao_camera="brancas_esquerda")
    jogo = JogoXadrez()

    casas_referencia = None

    # --- VARIÁVEIS DE CONTROLE DE TEMPO ---
    tempo_confirmacao = (
        2.0  # Segundos que a imagem deve ficar estável sem a mão na frente
    )
    candidato_mudancas = None
    tempo_inicio_deteccao = 0
    cooldown_ativo_ate = 0
    # --------------------------------------

    print("\nSISTEMA DE RASTREAMENTO INICIADO")
    print(
        "Comandos: 'c' - Calibrar quinas | 's' - Salvar estado das pecas | 'q' - Sair"
    )
    print(jogo.imprimir_tabuleiro())

    while True:
        frame = olho.capturar_frame()
        if frame is None:
            break

        cv2.imshow("Captura de Video", frame)
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("c"):
            olho.calibrar_com_mouse(frame)

        elif tecla == ord("s"):
            if olho.pontos_origem is not None:
                tab_ref = olho.retificar_tabuleiro(frame)
                casas_referencia = segmentador.fatiar_tabuleiro(tab_ref)
                print("Estado de referencia salvo com sucesso.")
            else:
                print("Erro: Realize a calibracao antes de salvar o estado.")

        elif tecla == ord("q"):
            break

        if casas_referencia is not None:
            # Se estamos no tempo de "cooldown" após fazer um lance, ignora a análise
            if time.time() < cooldown_ativo_ate:
                continue

            tab_atual = olho.retificar_tabuleiro(frame)
            casas_atuais = segmentador.fatiar_tabuleiro(tab_atual)

            tab_com_grade = olho.desenhar_grade_para_teste(tab_atual)
            cv2.imshow("Grade de Divisao", tab_com_grade)

            mudancas, mapa = segmentador.detectar_mudancas(
                casas_referencia, casas_atuais
            )
            cv2.imshow("Mascara de Diferenca", mapa)

            if len(mudancas) == 2:
                # Ordena as mudanças para garantir que (A,B) seja tratado igual a (B,A)
                mudancas_ordenadas = sorted(mudancas)

                # Se o sistema continua vendo as MESMAS duas casas alteradas
                if candidato_mudancas == mudancas_ordenadas:
                    tempo_decorrido = time.time() - tempo_inicio_deteccao

                    # Se já passou o tempo necessário de estabilidade (2 segundos)
                    if tempo_decorrido >= tempo_confirmacao:
                        traduzidas = [
                            tradutor.para_notacao(l, c) for l, c in mudancas_ordenadas
                        ]

                        lance_uci, mensagem = jogo.inferir_lance(traduzidas)

                        if lance_uci:
                            print(f"\n--- ✅ LANCE EXECUTADO: {lance_uci} ---")
                            print(mensagem)
                            print(jogo.imprimir_tabuleiro())

                            # Atualiza a referência APENAS quando um lance válido é confirmado
                            casas_referencia = casas_atuais
                            print("Referência atualizada para o próximo lance.")

                            # Inicia o tempo de recarga de 1 segundo para o sistema respirar
                            cooldown_ativo_ate = time.time() + 1.0

                        else:
                            print(f"\n[ ❌ ALERTA DE MOVIMENTO ]")
                            print(
                                f"A movimentação detectada ({traduzidas[0]} e {traduzidas[1]}) não é um lance válido nas regras do xadrez!"
                            )
                            print(
                                "Por favor, retorne a peça para a posição original e tente novamente."
                            )

                            # Tenta emitir um bipe sonoro padrão do sistema operacional
                            print("\a", end="")

                            # Aplica um tempo de recarga maior (ex: 4 segundos) para dar tempo
                            # do jogador arrumar o tabuleiro antes da câmera voltar a analisar.
                            cooldown_ativo_ate = time.time() + 4.0

                            # Reseta o candidato (seja o lance legal ou ilegal) para começar de novo
                            candidato_mudancas = None

                        # Reseta o candidato (seja o lance legal ou ilegal) para começar de novo
                        candidato_mudancas = None

                # Se as casas alteradas forem diferentes das que estavam sendo analisadas
                else:
                    candidato_mudancas = mudancas_ordenadas
                    tempo_inicio_deteccao = time.time()
            else:
                # Se a mão do jogador cobriu 5 casas ou se nenhuma casa foi detectada, reseta a contagem
                candidato_mudancas = None

    olho.fechar()


if __name__ == "__main__":
    executar_projeto()
