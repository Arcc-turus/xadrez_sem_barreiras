import cv2
import numpy as np

class SegmentadorTabuleiro:
    def __init__(self, tamanho_tabuleiro=800):
        self.tamanho_tabuleiro = tamanho_tabuleiro
        self.tamanho_casa = tamanho_tabuleiro // 8
        self.limiar_movimento = 30 # Sensibilidade

    def fatiar_tabuleiro(self, imagem_tabuleiro):
        """Corta o tabuleiro em uma matriz 8x8 de sub-imagens."""
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
        """Compara os estados, funde a pontuação da cabeça com a base e retorna o Top 2."""
        mudancas_encontradas = []
        mapa_visual = np.zeros((self.tamanho_tabuleiro, self.tamanho_tabuleiro), dtype=np.uint8)

        for linha in range(8):
            for coluna in range(8):
                img1 = cv2.cvtColor(casas_anterior[linha][coluna], cv2.COLOR_BGR2GRAY)
                img2 = cv2.cvtColor(casas_atual[linha][coluna], cv2.COLOR_BGR2GRAY)
                
                diff = cv2.absdiff(img1, img2)
                
                # Visão Noturna: Sensibilidade extrema (10) para peças pretas na sombra
                _, thresh = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
                
                # Expandimos a zona para pegar quase a casa inteira (10% a 90%)
                inicio = int(self.tamanho_casa * 0.1)
                fim = int(self.tamanho_casa * 0.9)
                zona_segura = thresh[inicio:fim, inicio:fim] 
                
                pixels_mudaram = cv2.countNonZero(zona_segura)
                area_analisada = zona_segura.shape[0] * zona_segura.shape[1]
                
                # Nota de corte minúscula (0.5%) para capturar a base mais camuflada possível
                if pixels_mudaram > (area_analisada * 0.005): 
                    mudancas_encontradas.append({
                        'linha': linha,
                        'coluna': coluna,
                        'placar': pixels_mudaram,
                        'is_head': False
                    })

                y_offset = linha * self.tamanho_casa
                x_offset = coluna * self.tamanho_casa
                mapa_visual[y_offset:y_offset+self.tamanho_casa, x_offset:x_offset+self.tamanho_casa] = thresh

        # --- A MÁGICA DA FUSÃO ---
        for i in range(len(mudancas_encontradas)):
            candidato = mudancas_encontradas[i]
            for j in range(len(mudancas_encontradas)):
                base = mudancas_encontradas[j]
                # Se achou uma base exatamente na casa de baixo...
                if base['linha'] == candidato['linha'] + 1 and base['coluna'] == candidato['coluna']:
                    # Transfere os pontos e destrói a cabeça!
                    base['placar'] += candidato['placar']
                    candidato['is_head'] = True
                    break
        
        # Filtra as cabeças mortas e ranqueia os sobreviventes
        candidatos_validos = [m for m in mudancas_encontradas if not m['is_head']]
        candidatos_validos.sort(key=lambda x: x['placar'], reverse=True)

        casas_alteradas = [(m['linha'], m['coluna']) for m in candidatos_validos[:2]]

        return casas_alteradas, mapa_visual
    