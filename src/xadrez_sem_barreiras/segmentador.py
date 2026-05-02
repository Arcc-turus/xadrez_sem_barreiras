import cv2
import numpy as np


class SegmentadorTabuleiro:
    def __init__(self, tamanho_tabuleiro=800):
        self.tamanho_tabuleiro = tamanho_tabuleiro
        self.tamanho_casa = tamanho_tabuleiro // 8

        # Área realmente usada para decidir se uma casa mudou.
        # Em tabuleiros vistos pela câmera em ângulo, a cabeça da peça costuma
        # invadir a casa de cima ou a casa do lado. Por isso analisamos mais a
        # região central/baixa da casa, onde fica a base da peça.
        self.roi_x_inicio = 0.18
        self.roi_x_fim = 0.82
        self.roi_y_inicio = 0.35
        self.roi_y_fim = 0.96

        # Sensibilidade. Se detectar pouco, diminua um pouco o percentual.
        # Se detectar ruído/cabeça de peça, aumente um pouco.
        self.percentual_minimo_mudanca = 0.012

    def fatiar_tabuleiro(self, imagem_tabuleiro):
        """Divide a imagem retificada em uma matriz 8x8 de sub-imagens (casas)."""
        casas = []
        altura, largura = imagem_tabuleiro.shape[:2]

        # Usa linspace para não acumular erro de arredondamento caso a imagem não
        # esteja exatamente no tamanho esperado.
        cortes_x = np.linspace(0, largura, 9).round().astype(int)
        cortes_y = np.linspace(0, altura, 9).round().astype(int)

        for linha in range(8):
            linha_casas = []
            for coluna in range(8):
                y1, y2 = cortes_y[linha], cortes_y[linha + 1]
                x1, x2 = cortes_x[coluna], cortes_x[coluna + 1]
                linha_casas.append(imagem_tabuleiro[y1:y2, x1:x2])
            casas.append(linha_casas)
        return casas

    def _recortar_roi_peca(self, imagem):
        """Recorta só a região central/baixa da casa, ignorando vazamento da cabeça."""
        altura, largura = imagem.shape[:2]
        x1 = int(largura * self.roi_x_inicio)
        x2 = int(largura * self.roi_x_fim)
        y1 = int(altura * self.roi_y_inicio)
        y2 = int(altura * self.roi_y_fim)
        return imagem[y1:y2, x1:x2], (x1, y1, x2, y2)

    def detectar_mudancas(self, casas_anterior, casas_atual):
        """
        Identifica movimentações comparando o estado atual com o estado de referência.

        Correção principal:
        - antes o programa analisava quase a casa inteira;
        - agora ele analisa principalmente a base da peça;
        - a cabeça da peça pode aparecer em outro quadrante, mas não entra na
          contagem principal da mudança.
        """
        mudancas_encontradas = []
        mapa_visual = np.zeros((self.tamanho_tabuleiro, self.tamanho_tabuleiro), dtype=np.uint8)

        for linha in range(8):
            for coluna in range(8):
                img1 = cv2.cvtColor(casas_anterior[linha][coluna], cv2.COLOR_BGR2GRAY)
                img2 = cv2.cvtColor(casas_atual[linha][coluna], cv2.COLOR_BGR2GRAY)

                diff = cv2.absdiff(img1, img2)
                _, thresh = cv2.threshold(diff, 12, 255, cv2.THRESH_BINARY)

                # Limpeza leve para tirar ruído de câmera/reflexo.
                kernel = np.ones((3, 3), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

                zona_analise, (x1, y1, x2, y2) = self._recortar_roi_peca(thresh)

                pixels_alterados = cv2.countNonZero(zona_analise)
                area_total = zona_analise.shape[0] * zona_analise.shape[1]

                if pixels_alterados > (area_total * self.percentual_minimo_mudanca):
                    mudancas_encontradas.append({
                        "linha": linha,
                        "coluna": coluna,
                        "score": pixels_alterados,
                        "is_artifact": False,
                    })

                # Mapa visual: mostra APENAS a área que está sendo analisada.
                # Assim fica fácil confirmar se a cabeça da peça foi ignorada.
                y_offset = linha * self.tamanho_casa
                x_offset = coluna * self.tamanho_casa
                h, w = zona_analise.shape[:2]
                mapa_visual[y_offset + y1:y_offset + y1 + h, x_offset + x1:x_offset + x1 + w] = zona_analise

        # Segurança extra: se ainda sobrar uma mudança imediatamente acima de outra
        # na mesma coluna, a de cima costuma ser vazamento visual da peça de baixo.
        # Só aplica o filtro quando houver muitas mudanças (> 4), pois com 2-4 pode
        # ser um lance legítimo como en passant ou roque.
        if len(mudancas_encontradas) > 4:
            for item in mudancas_encontradas:
                for base_potencial in mudancas_encontradas:
                    if (
                        base_potencial["linha"] == item["linha"] + 1
                        and base_potencial["coluna"] == item["coluna"]
                        and base_potencial["score"] >= item["score"] * 0.8
                    ):
                        base_potencial["score"] += item["score"]
                        item["is_artifact"] = True
                        break

        candidatos_validos = [m for m in mudancas_encontradas if not m["is_artifact"]]
        candidatos_validos.sort(key=lambda x: x["score"], reverse=True)

        # Antes retornava somente as 2 casas mais fortes. Isso quebrava o roque,
        # porque o roque muda 4 casas visualmente: rei origem/destino e torre
        # origem/destino. Agora retornamos todas as casas detectadas.
        # O Main decide se aceita 2, 3 ou 4 casas e ignora quando houver ruído demais.
        casas_alteradas = [(m["linha"], m["coluna"]) for m in candidatos_validos]

        return casas_alteradas, mapa_visual
