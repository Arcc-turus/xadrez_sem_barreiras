import cv2
import numpy as np

class SegmentadorTabuleiro:
    def __init__(self, tamanho_tabuleiro=800):
        self.tamanho_tabuleiro = tamanho_tabuleiro
        self.tamanho_casa = tamanho_tabuleiro // 8

    def fatiar_tabuleiro(self, imagem_tabuleiro):
        """Divide a imagem retificada em uma matriz 8x8 de sub-imagens (casas)."""
        casas = []
        for linha in range(8):
            linha_casas = []
            for coluna in range(8):
                y1, y2 = linha * self.tamanho_casa, (linha + 1) * self.tamanho_casa
                x1, x2 = coluna * self.tamanho_casa, (coluna + 1) * self.tamanho_casa
                linha_casas.append(imagem_tabuleiro[y1:y2, x1:x2])
            casas.append(linha_casas)
        return casas

    def detectar_mudancas(self, casas_anterior, casas_atual):
        """
        Identifica movimentações comparando o estado atual com o estado de referência.
        Utiliza lógica de fusão para ignorar artefatos de perspectiva (cabeça das peças).
        """
        mudancas_encontradas = []
        mapa_visual = np.zeros((self.tamanho_tabuleiro, self.tamanho_tabuleiro), dtype=np.uint8)

        for linha in range(8):
            for coluna in range(8):
                # Conversão para tons de cinza para simplificar a comparação de intensidade
                img1 = cv2.cvtColor(casas_anterior[linha][coluna], cv2.COLOR_BGR2GRAY)
                img2 = cv2.cvtColor(casas_atual[linha][coluna], cv2.COLOR_BGR2GRAY)
                
                # Cálculo da diferença absoluta de pixels
                diff = cv2.absdiff(img1, img2)
                
                # Binarização com limiar sensível para detectar peças pretas em áreas sombreadas
                _, thresh = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
                
                # Definição de uma área central de interesse para reduzir ruídos de borda
                inicio = int(self.tamanho_casa * 0.1)
                fim = int(self.tamanho_casa * 0.9)
                zona_analise = thresh[inicio:fim, inicio:fim] 
                
                pixels_alterados = cv2.countNonZero(zona_analise)
                area_total = zona_analise.shape[0] * zona_analise.shape[1]
                
                # Filtro de densidade mínima de mudança para validar a detecção
                if pixels_alterados > (area_total * 0.005): 
                    mudancas_encontradas.append({
                        'linha': linha,
                        'coluna': coluna,
                        'score': pixels_alterados,
                        'is_artifact': False
                    })

                # Atualização do mapa visual para fins de depuração
                y_offset = linha * self.tamanho_casa
                x_offset = coluna * self.tamanho_casa
                mapa_visual[y_offset:y_offset+self.tamanho_casa, x_offset:x_offset+self.tamanho_casa] = thresh

        # Lógica de Fusão: Identifica se uma mudança é apenas a parte superior de uma peça
        # que invadiu visualmente a casa acima devido ao ângulo da câmera.
        for i in range(len(mudancas_encontradas)):
            item = mudancas_encontradas[i]
            for j in range(len(mudancas_encontradas)):
                base_potencial = mudancas_encontradas[j]
                # Se houver uma detecção na linha abaixo da atual na mesma coluna,
                # considera-se a detecção atual como um artefato da peça de baixo.
                if base_potencial['linha'] == item['linha'] + 1 and base_potencial['coluna'] == item['coluna']:
                    base_potencial['score'] += item['score']
                    item['is_artifact'] = True
                    break
        
        # Filtragem e ordenação das detecções mais relevantes
        candidatos_validos = [m for m in mudancas_encontradas if not m['is_artifact']]
        candidatos_validos.sort(key=lambda x: x['score'], reverse=True)

        # Retorna as duas coordenadas com maior índice de alteração (origem e destino)
        casas_alteradas = [(m['linha'], m['coluna']) for m in candidatos_validos[:2]]

        return casas_alteradas, mapa_visual