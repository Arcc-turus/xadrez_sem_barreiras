class TradutorXadrez:
    def __init__(self, posicao_camera='brancas_esquerda'):
        self.posicao_camera = posicao_camera
        self.letras = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    def para_notacao(self, linha, coluna):
        if linha < 0 or linha > 7 or coluna < 0 or coluna > 7:
            return None

        if self.posicao_camera == 'brancas_esquerda':
            # Baseado na sua foto: vertical = letras, horizontal = números
            letra = self.letras[linha]
            numero = str(coluna + 1)
            return f"{letra}{numero}"
        
        # Outras orientações podem ser adicionadas aqui depois
        return f"({linha},{coluna})"