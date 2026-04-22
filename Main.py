import cv2
from CapturarTabuleiro import BoardDetector
from Segmentador import SegmentadorTabuleiro
from Tradutor import TradutorXadrez

def executar_projeto():
    # Inicialização dos módulos
    olho = BoardDetector(camera_index=1) #lembrar de trocar dependendo da câmera a usar
    segmentador = SegmentadorTabuleiro()
    tradutor = TradutorXadrez(posicao_camera='brancas_esquerda')
    
    casas_referencia = None

    print("\n=== SISTEMA INICIADO ===")
    print("Aperte 'c' para calibrar as quinas.")
    print("Aperte 's' para salvar o estado inicial das peças.")
    print("Aperte 'q' para sair.")

    while True:
        frame = olho.capturar_frame()
        if frame is None: break

        cv2.imshow("Preview Real", frame)
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord('c'):
            olho.calibrar_com_mouse(frame)
        
        elif tecla == ord('s'):
            if olho.pontos_origem is not None:
                tab_ref = olho.retificar_tabuleiro(frame)
                casas_referencia = segmentador.fatiar_tabuleiro(tab_ref)
                print("\n📸 Estado das peças salvo! Pode mover.")
            else:
                print("\n❌ Calibre primeiro!")

        elif tecla == ord('q'):
            break

        # Processamento em tempo real
        if casas_referencia is not None:
            tab_atual = olho.retificar_tabuleiro(frame)
            casas_atuais = segmentador.fatiar_tabuleiro(tab_atual)
            
            tab_com_grade = olho.desenhar_grade_para_teste(tab_atual)
            cv2.imshow("Grade de Divisao", tab_com_grade)

            mudancas, mapa = segmentador.detectar_mudancas(casas_referencia, casas_atuais)
            cv2.imshow("O que o computador ve", mapa)
            
            if mudancas:
                traduzidas = [tradutor.para_notacao(l, c) for l, c in mudancas]
                print(f"Mudança em: {traduzidas}")

    olho.fechar()

if __name__ == "__main__":
    executar_projeto()