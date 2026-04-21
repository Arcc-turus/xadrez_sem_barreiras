class TradutorXadrez:
    def __init__(self, posicao_camera='brancas_esquerda'):
        """
        Define de onde a câmera está olhando o tabuleiro na imagem 2D final.
        Opções:
        - 'brancas_abaixo': Visão do jogador de brancas (Padrão)
        - 'pretas_abaixo': Visão do jogador de pretas
        - 'brancas_esquerda': Visão lateral (Brancas na esquerda) -> COMO NA SUA FOTO
        - 'brancas_direita': Visão lateral (Brancas na direita)
        """
        self.posicao_camera = posicao_camera
        self.letras = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    def para_notacao(self, linha, coluna):
        """
        Converte as coordenadas da matriz [0-7, 0-7] da imagem para notação de xadrez (ex: 'e2').
        Lembrando que na matriz da imagem:
        - linha 0 é o TOPO, linha 7 é a BASE.
        - coluna 0 é a ESQUERDA, coluna 7 é a DIREITA.
        """
        # Proteção contra coordenadas inválidas
        if linha < 0 or linha > 7 or coluna < 0 or coluna > 7:
            return None

        if self.posicao_camera == 'brancas_abaixo':
            letra = self.letras[coluna]
            numero = str(8 - linha)
            
        elif self.posicao_camera == 'pretas_abaixo':
            letra = self.letras[7 - coluna]
            numero = str(linha + 1)
            
        elif self.posicao_camera == 'brancas_esquerda':
            # Visão da sua FOTO:
            # O eixo vertical (linha da matriz) representa as letras (a -> h)
            # O eixo horizontal (coluna da matriz) representa os números (1 -> 8)
            letra = self.letras[linha]
            numero = str(coluna + 1)
            
        elif self.posicao_camera == 'brancas_direita':
            # Visão lateral oposta:
            # O eixo vertical (linha da matriz) representa as letras (h -> a)
            # O eixo horizontal (coluna da matriz) representa os números (8 -> 1)
            letra = self.letras[7 - linha]
            numero = str(8 - coluna)
            
        else:
            return None
            
        return f"{letra}{numero}"


# --- ÁREA DE TESTES ---
if __name__ == "__main__":
    # Inicializando com a visão da foto que você mandou
    tradutor = TradutorXadrez(posicao_camera='brancas_esquerda')
    
    print("Testando Tradutor (Visão Lateral - Brancas na Esquerda):")
    
    # O Canto superior esquerdo da imagem (Topo, Esquerda)
    print(f"Matriz [0, 0] -> Xadrez: {tradutor.para_notacao(0, 0)} (Esperado: Torre Branca em a1)")
    
    # O Canto inferior esquerdo da imagem (Base, Esquerda)
    print(f"Matriz [7, 0] -> Xadrez: {tradutor.para_notacao(7, 0)} (Esperado: Torre Branca em h1)")
    
    # O Rei Branco na imagem (Um pouco abaixo do meio, Esquerda)
    print(f"Matriz [4, 0] -> Xadrez: {tradutor.para_notacao(4, 0)} (Esperado: Rei Branco em e1)")
    
    # O Rei Preto na imagem (Um pouco abaixo do meio, Direita)
    print(f"Matriz [4, 7] -> Xadrez: {tradutor.para_notacao(4, 7)} (Esperado: Rei Preto em e8)")