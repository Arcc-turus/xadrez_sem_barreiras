# Xadrez Sem Barreiras

Projeto em Python para acompanhar um tabuleiro físico de xadrez por câmera, detectar movimentos, atualizar o estado da partida em FEN e falar o lance realizado.

## O que o projeto faz

- Captura vídeo da webcam com OpenCV.
- Permite calibrar as 4 quinas do tabuleiro manualmente ou tentar calibração automática.
- Divide o tabuleiro em 8x8 casas.
- Detecta mudanças visuais nas casas.
- Usa `python-chess` para validar os lances.
- Suporta lances normais, en passant e roque.
- Salva o FEN da posição atual.
- Usa voz para falar a peça e a casa de destino.

## Estrutura do repositório

```text
xadrez-sem-barreiras/
├── src/xadrez_sem_barreiras/
│   ├── app.py
│   ├── camera.py
│   ├── segmentador.py
│   ├── tradutor.py
│   ├── voz.py
│   └── xadrez.py
├── tests/
├── data/
├── assets/
├── docs/
├── pyproject.toml
├── requirements.txt
├── run.py
├── .gitignore
└── README.md
```

## Instalação

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Como executar

Forma recomendada:

```bash
pip install -e .
xadrez-sem-barreiras --camera 1
```

Atalho simples:

```bash
python run.py --camera 1
```

Se a câmera não abrir, teste outros índices:

```bash
python run.py --camera 0
python run.py --camera 2
```

## Comandos dentro do programa

| Tecla | Função |
|---|---|
| `c` | Calibrar manualmente as quinas do tabuleiro |
| `v` | Tentar calibração automática |
| `s` | Salvar o estado visual atual como referência |
| `f` | Ligar/desligar voz |
| `z` | Desfazer o último lance |
| `r` | Reiniciar a partida |
| `q` | Sair |

## Arquivos gerados

Durante a execução, o programa salva arquivos dentro da pasta `data/`:

- `estado_partida.fen`: posição atual do tabuleiro em FEN.
- `estado_visual_pecas.jpg`: imagem retificada usada como referência visual.

Esses arquivos são ignorados pelo Git para não sujar o repositório.

## Voz no sistema

- Windows: usa o sintetizador nativo via PowerShell.
- Linux: tenta usar `spd-say` ou `espeak`.
- macOS: tenta usar `say`.

No Linux, instale um sintetizador se necessário:

```bash
sudo apt install speech-dispatcher espeak
```

ou, no Fedora:

```bash
sudo dnf install speech-dispatcher espeak
```

## Desenvolvimento

Verificar se os arquivos compilam:

```bash
python -m compileall src tests
```

Rodar testes simples:

```bash
pytest
```
