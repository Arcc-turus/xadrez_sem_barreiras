import cv2
from CapturarTabuleiro import BoardDetector
from Segmentador import SegmentadorTabuleiro
from Tradutor import TradutorXadrez

def executar_projeto():
    # Inicialização dos componentes do sistema
    olho = BoardDetector(camera_index=1)
    segmentador = SegmentadorTabuleiro()
    tradutor = TradutorXadrez(posicao_camera='brancas_esquerda')
    
    casas_referencia = None

    print("\nSISTEMA DE RASTREAMENTO INICIADO")
    print("Comandos: 'c' - Calibrar quinas | 's' - Salvar estado das pecas | 'q' - Sair")

    while True:
        frame = olho.capturar_frame()
        if frame is None:
            break

        cv2.imshow("Captura de Video", frame)
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('c'):
            olho.calibrar_com_mouse(frame)
        
        elif tecla == ord('s'):
            if olho.pontos_origem is not None:
                # Captura e armazena o estado atual como referência para futuras comparações
                tab_ref = olho.retificar_tabuleiro(frame)
                casas_referencia = segmentador.fatiar_tabuleiro(tab_ref)
                print("Estado de referencia salvo com sucesso.")
            else:
                print("Erro: Realize a calibracao antes de salvar o estado.")

        elif tecla == ord('q'):
            break

        # Processamento contínuo após a definição da referência
        if casas_referencia is not None:
            # Retificação da perspectiva e divisão do tabuleiro
            tab_atual = olho.retificar_tabuleiro(frame)
            casas_atuais = segmentador.fatiar_tabuleiro(tab_atual)
            
            # Interface visual para validação da grade de detecção
            tab_com_grade = olho.desenhar_grade_para_teste(tab_atual)
            cv2.imshow("Grade de Divisao", tab_com_grade)

            # Detecção de movimentação baseada na comparação de matrizes
            mudancas, mapa = segmentador.detectar_mudancas(casas_referencia, casas_atuais)
            cv2.imshow("Mascara de Diferenca", mapa)
            
            if mudancas:
                # Tradução das coordenadas de matriz para notação algébrica
                traduzidas = [tradutor.para_notacao(l, c) for l, c in mudancas]
                print(f"Movimentacao detectada entre as casas: {traduzidas}")

    olho.fechar()

if __name__ == "__main__":
    executar_projeto()