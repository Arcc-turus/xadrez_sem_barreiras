import cv2
import numpy as np

class BoardDetector:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            print("Erro: Não foi possível conectar à câmera. Verifique o índice ou a conexão.")
            
        self.tamanho_tabuleiro = 800
        
        self.pontos_destino = np.float32([
            [0, 0], 
            [self.tamanho_tabuleiro, 0], 
            [self.tamanho_tabuleiro, self.tamanho_tabuleiro], 
            [0, self.tamanho_tabuleiro]
        ])
        
        self.pontos_origem = None

    def capturar_frame(self):
        sucesso, frame = self.cap.read()
        return frame if sucesso else None

    def ordenar_pontos(self, pontos):
        """
        Garante que os pontos capturados estejam sempre na ordem padrão:
        Superior-Esquerdo, Superior-Direito, Inferior-Direito, Inferior-Esquerdo.
        """
        retangulo = np.zeros((4, 2), dtype="float32")
        
        soma = pontos.sum(axis=1)
        retangulo[0] = pontos[np.argmin(soma)]
        retangulo[2] = pontos[np.argmax(soma)]
        
        diff = np.diff(pontos, axis=1)
        retangulo[1] = pontos[np.argmin(diff)]
        retangulo[3] = pontos[np.argmax(diff)]
        
        return retangulo

    def calibrar_automatico(self, frame):
        """
        Tenta localizar o tabuleiro automaticamente processando as bordas da imagem.
        Para funcionar corretamente, o tabuleiro não deve ter peças em cima.
        """
        print("\nTentando calibração automática... Por favor, deixe o tabuleiro vazio.")
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        bordas = cv2.Canny(blur, 50, 150)
        
        contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
        
        for contorno in contornos:
            perimetro = cv2.arcLength(contorno, True)
            aproximacao = cv2.approxPolyDP(contorno, 0.02 * perimetro, True)
            
            if len(aproximacao) == 4:
                pontos = aproximacao.reshape(4, 2)
                self.pontos_origem = self.ordenar_pontos(pontos)
                
                print("Tabuleiro localizado automaticamente com sucesso.")
                return True
                
        print("Não foi possível localizar o tabuleiro automaticamente.")
        return False

    def calibrar_com_mouse(self, frame):
        """
        Calibração manual com lente de aumento e mira.
        """
        print("\n--- Modo de Calibração Manual ---")
        print("Clique nas quinas da área de jogo na seguinte ordem:")
        print("1. Superior Esquerda -> 2. Superior Direita -> 3. Inferior Direita -> 4. Inferior Esquerda")
        print("Pressione 'Z' no teclado para desfazer o último clique.")
        
        pontos_clicados = []
        frame_limpo = frame.copy()

        def clique_mouse(event, x, y, flags, param):
            frame_base = frame_limpo.copy()
            altura_img, largura_img = frame_base.shape[:2]

            # --- 1. MARCADORES DOS PONTOS SALVOS (Sem projeção de linhas) ---
            for pt in pontos_clicados:
                px, py = tuple(pt)
                cv2.drawMarker(frame_base, (px, py), (0, 0, 255), 
                               markerType=cv2.MARKER_CROSS, markerSize=15, thickness=1)
                cv2.circle(frame_base, (px, py), 1, (0, 255, 0), -1)

            frame_display = frame_base.copy()

            # --- 2. MIRA VERDE DO MOUSE ---
            cv2.line(frame_display, (x, 0), (x, altura_img), (0, 255, 0), 1)
            cv2.line(frame_display, (0, y), (largura_img, y), (0, 255, 0), 1)

            # --- 3. LÓGICA DA LENTE DE AUMENTO (ZOOM) ---
            raio_captura = 30
            fator_zoom = 4
            tamanho_lupa = (raio_captura * 2) * fator_zoom
            
            y1, y2 = max(0, y - raio_captura), min(altura_img, y + raio_captura)
            x1, x2 = max(0, x - raio_captura), min(largura_img, x + raio_captura)
            
            roi = frame_base[y1:y2, x1:x2].copy()
            
            topo = max(0, raio_captura - y)
            base = max(0, (y + raio_captura) - altura_img)
            esq = max(0, raio_captura - x)
            dir = max(0, (x + raio_captura) - largura_img)
            
            roi_preenchido = cv2.copyMakeBorder(roi, topo, base, esq, dir, cv2.BORDER_CONSTANT, value=[0, 0, 0])
            lupa = cv2.resize(roi_preenchido, (tamanho_lupa, tamanho_lupa), interpolation=cv2.INTER_NEAREST)
            
            centro_lupa = tamanho_lupa // 2
            cv2.line(lupa, (centro_lupa, 0), (centro_lupa, tamanho_lupa), (0, 255, 0), 1)
            cv2.line(lupa, (0, centro_lupa), (tamanho_lupa, centro_lupa), (0, 255, 0), 1)
            cv2.rectangle(lupa, (0, 0), (tamanho_lupa - 1, tamanho_lupa - 1), (255, 255, 255), 2)
            
            if x > largura_img // 2:
                pos_x_lupa = 20
            else:
                pos_x_lupa = largura_img - tamanho_lupa - 20
            pos_y_lupa = 20
            
            frame_display[pos_y_lupa:pos_y_lupa+tamanho_lupa, pos_x_lupa:pos_x_lupa+tamanho_lupa] = lupa

            # --- 4. REGISTRO DO CLIQUE ---
            if event == cv2.EVENT_LBUTTONDOWN:
                if len(pontos_clicados) < 4:
                    pontos_clicados.append([x, y])
                    print(f"Ponto {len(pontos_clicados)} registrado em: ({x}, {y})")

            cv2.imshow("Calibracao", frame_display)

        cv2.imshow("Calibracao", frame_limpo)
        cv2.setMouseCallback("Calibracao", clique_mouse)

        while len(pontos_clicados) < 4:
            tecla = cv2.waitKey(1) & 0xFF
            
            if tecla == ord('z') and len(pontos_clicados) > 0:
                removido = pontos_clicados.pop()
                print(f"Último ponto desfeito: {removido}")
                clique_mouse(0, 0, 0, 0, None)
                
        cv2.destroyWindow("Calibracao")
        
        self.pontos_origem = self.ordenar_pontos(np.float32(pontos_clicados))
        print("\nCalibração manual finalizada.")

    def retificar_tabuleiro(self, frame, margem_corte=0.0):
        """
        Ajusta a perspectiva da imagem para mostrar o tabuleiro em 2D perfeitamente plano.
        """
        if self.pontos_origem is None:
            return frame
            
        matriz = cv2.getPerspectiveTransform(self.pontos_origem, self.pontos_destino)
        tabuleiro_plano = cv2.warpPerspective(frame, matriz, (self.tamanho_tabuleiro, self.tamanho_tabuleiro))
        
        if margem_corte > 0.0:
            corte_pixels = int(self.tamanho_tabuleiro * margem_corte)
            tabuleiro_plano = tabuleiro_plano[corte_pixels : self.tamanho_tabuleiro - corte_pixels, 
                                              corte_pixels : self.tamanho_tabuleiro - corte_pixels]
            tabuleiro_plano = cv2.resize(tabuleiro_plano, (self.tamanho_tabuleiro, self.tamanho_tabuleiro))
            
        return tabuleiro_plano

    def desenhar_grade_para_teste(self, tabuleiro_plano):
        """
        Sobrepõe uma grade verde de 8x8 na imagem processada para validação visual.
        """
        imagem_teste = tabuleiro_plano.copy()
        tamanho = self.tamanho_tabuleiro // 8
        
        for i in range(1, 8):
            cv2.line(imagem_teste, (0, i * tamanho), (self.tamanho_tabuleiro, i * tamanho), (0, 255, 0), 2)
            cv2.line(imagem_teste, (i * tamanho, 0), (i * tamanho, self.tamanho_tabuleiro), (0, 255, 0), 2)
            
        return imagem_teste

    def fechar(self):
        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    olho = BoardDetector(camera_index=1) # Lembrar de ajustar o índice se necessário (0, 1, 2)
    frame_inicial = olho.capturar_frame()
    
    if frame_inicial is not None:
        print("\nPreparando calibração inicial...")
        olho.calibrar_com_mouse(frame_inicial)
            
        while True:
            frame_atual = olho.capturar_frame()
            if frame_atual is None:
                break

            tabuleiro = olho.retificar_tabuleiro(frame_atual, margem_corte=0.0)
            tabuleiro_com_grade = olho.desenhar_grade_para_teste(tabuleiro)
            
            cv2.imshow("Captura Original", frame_atual)
            cv2.imshow("Tabuleiro Processado", tabuleiro_com_grade)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    olho.fechar()