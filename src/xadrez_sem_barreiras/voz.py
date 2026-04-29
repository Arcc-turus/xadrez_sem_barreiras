import platform
import shutil
import subprocess
import threading


class LeitorVoz:
    """
    Faz o computador falar sem travar a câmera.

    Windows: usa a voz nativa do sistema via PowerShell/System.Speech.
    Linux: tenta spd-say ou espeak, se algum estiver instalado.
    macOS: tenta o comando say.
    """

    def __init__(self, ativo=True):
        self.ativo = ativo
        self._lock = threading.Lock()

    def alternar(self):
        self.ativo = not self.ativo
        return self.ativo

    def falar(self, texto):
        if not texto:
            return

        print(f"[voz] {texto}")

        if not self.ativo:
            return

        thread = threading.Thread(target=self._falar_bloqueante, args=(texto,), daemon=True)
        thread.start()

    def _falar_bloqueante(self, texto):
        with self._lock:
            sistema = platform.system().lower()

            try:
                if "windows" in sistema:
                    self._falar_windows(texto)
                    return

                if "darwin" in sistema and shutil.which("say"):
                    subprocess.run(["say", texto], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                if shutil.which("spd-say"):
                    subprocess.run(["spd-say", "-l", "pt-BR", texto], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                if shutil.which("espeak"):
                    subprocess.run(["espeak", "-v", "pt-br", texto], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                print("[voz] Nenhum sintetizador de voz encontrado neste sistema.")
            except Exception as erro:
                print(f"[voz] Não foi possível falar: {erro}")

    def _falar_windows(self, texto):
        texto_seguro = texto.replace("'", "''")
        comando = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Volume = 100; "
            "$s.Rate = 0; "
            f"$s.Speak('{texto_seguro}');"
        )

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
