import chess


class JogoXadrez:
    def __init__(self):
        # Inicializa o tabuleiro virtual na posição inicial padrão
        self.tabuleiro = chess.Board()

    def inferir_lance(self, casas_alteradas):
        """
        Recebe uma lista com duas casas em notação algébrica (ex: ['e2', 'e4'])
        e tenta deduzir qual foi o lance real baseado nas regras do xadrez.
        """
        if not casas_alteradas or len(casas_alteradas) != 2:
            return (
                None,
                "São necessárias exatamente 2 casas alteradas para inferir um lance.",
            )

        casa_a, casa_b = casas_alteradas

        # Possibilidade 1: moveu da casa A para a casa B
        lance_opcao_1 = casa_a + casa_b
        # Possibilidade 2: moveu da casa B para a casa A
        lance_opcao_2 = casa_b + casa_a

        movimento_realizado = None

        # Verifica se a Opção 1 é um lance legal
        if chess.Move.from_uci(lance_opcao_1) in self.tabuleiro.legal_moves:
            movimento_realizado = chess.Move.from_uci(lance_opcao_1)

        # Verifica se a Opção 2 é um lance legal
        elif chess.Move.from_uci(lance_opcao_2) in self.tabuleiro.legal_moves:
            movimento_realizado = chess.Move.from_uci(lance_opcao_2)

        # Lógica para Promoção de Peão (se o lance normal não funcionou, tenta com promoção para Dama 'q')
        else:
            promocoes = ["q", "r", "b", "n"]
            for peca in promocoes:
                promocao_1 = chess.Move.from_uci(lance_opcao_1 + peca)
                if promocao_1 in self.tabuleiro.legal_moves:
                    movimento_realizado = promocao_1
                    break

                promocao_2 = chess.Move.from_uci(lance_opcao_2 + peca)
                if promocao_2 in self.tabuleiro.legal_moves:
                    movimento_realizado = promocao_2
                    break

        if movimento_realizado:
            # Aplica o lance no tabuleiro virtual
            self.tabuleiro.push(movimento_realizado)
            return movimento_realizado.uci(), "Lance válido e registrado!"
        else:
            return None, f"Lance ilegal ou não reconhecido entre {casa_a} e {casa_b}."

    def imprimir_tabuleiro(self):
        """Retorna uma representação em texto do tabuleiro atual para debug no terminal."""
        return str(self.tabuleiro)
