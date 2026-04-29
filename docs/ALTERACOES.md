# Alterações desta versão


1) Roque corrigido
------------------
Antes o sistema aceitava somente 2 casas alteradas. No roque, mudam 4 casas:
- rei: origem e destino
- torre: origem e destino

Agora o Main.py aceita 2, 3 ou 4 casas alteradas:
- 2 casas: lance normal
- 3 casas: en passant
- 4 casas: roque

O Xadrez.py compara as casas detectadas com todos os lances legais do python-chess.
Assim, se as casas e1, g1, h1 e f1 mudarem, ele entende como o lance e1g1.

2) Voz adicionada
-----------------
Foi criado o arquivo Voz.py.
Depois de cada lance válido, o programa fala a peça e a casa final, por exemplo:
- Peão para casa e 4.
- Cavalo para casa f 3.
- Rei para casa g 1. Roque pequeno.

Atalho novo:
- f: liga/desliga a voz

No Windows, a voz usa o sintetizador nativo via PowerShell/System.Speech.
No Linux, tenta usar spd-say ou espeak se estiver instalado.
No macOS, tenta usar o comando say.

3) Detecção visual ajustada para roque
--------------------------------------
O Segmentador.py não corta mais a lista para apenas 2 casas alteradas.
Ele retorna todas as casas candidatas, e o Main.py decide quando aceitar ou ignorar.
Se aparecerem mais de 4 casas, o sistema considera que provavelmente é mão/sombra/ruído e espera estabilizar.
