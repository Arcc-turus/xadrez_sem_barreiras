from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import chess
import cv2
import numpy as np
from flask import Flask, Response, render_template, jsonify, request
from flask_socketio import SocketIO, emit

try:
    import subprocess
    _HAS_V4L2 = True
except ImportError:
    _HAS_V4L2 = False


def _get_camera_name(idx: int) -> str:
    """Tenta obter o nome do dispositivo de camera pelo sysfs ou v4l2-ctl."""
    name_path = Path(f"/sys/class/video4linux/video{idx}/name")
    if name_path.exists():
        try:
            return name_path.read_text().strip()
        except Exception:
            pass
    if _HAS_V4L2:
        try:
            out = subprocess.check_output(
                ["v4l2-ctl", "--list-devices"],
                stderr=subprocess.DEVNULL, text=True, timeout=3
            )
            lines = out.splitlines()
            for i, line in enumerate(lines):
                if f"/dev/video{idx}" in line or f"video{idx}" in line:
                    if i > 0:
                        return lines[i - 1].strip()
                    return f"Camera {idx}"
        except Exception:
            pass
    return f"Camera {idx}"


VENV_ROOT = Path(__file__).resolve().parent.parent / ".venv"
VENV_SITE = VENV_ROOT / "lib"
if VENV_SITE.exists():
    for d in VENV_SITE.iterdir():
        sp = d / "site-packages"
        if sp.is_dir() and str(sp) not in sys.path:
            sys.path.insert(0, str(sp))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xadrez_sem_barreiras.camera import BoardDetector
from xadrez_sem_barreiras.segmentador import SegmentadorTabuleiro
from xadrez_sem_barreiras.tradutor import TradutorXadrez
from xadrez_sem_barreiras.xadrez import JogoXadrez
from xadrez_sem_barreiras.voz import LeitorVoz

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "xadrez_sem_barreiras"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

_detector: BoardDetector | None = None
_segmentador = SegmentadorTabuleiro()
_tradutor = TradutorXadrez(posicao_camera="brancas_esquerda")
_jogo = JogoXadrez(fonetica=False)
_voz = LeitorVoz(ativo=True, velocidade=1.0)

_frame: np.ndarray | None = None
_frame_lock = threading.Lock()

_mask_frame: np.ndarray | None = None
_mask_lock = threading.Lock()

_stream_running = False
_track_running = False
_track_thread: threading.Thread | None = None

_calibrando = False
_mouse_points: list = []
_referencia_salva = False
_historico: list = []
_calibrated_points: list | None = None


def _stream_loop():
    global _stream_running, _frame
    cap = _detector.cap if _detector is not None else None
    if cap is None or not cap.isOpened():
        _stream_running = False
        return

    _stream_running = True
    while _stream_running:
        ret, frame = cap.read()
        if not ret:
            break
        with _frame_lock:
            if _detector is not None and _detector.pontos_origem is not None:
                tab = _detector.retificar_tabuleiro(frame)
                tab_grade = _detector.desenhar_grade_para_teste(tab)
                _frame = tab_grade
            else:
                out = frame.copy()
                if _calibrando and _mouse_points:
                    for i, (px, py) in enumerate(_mouse_points):
                        try:
                            cv2.circle(out, (px, py), 10, (0, 255, 0), -1)
                            cv2.putText(out, str(i + 1), (px + 14, py + 4),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        except Exception:
                            pass
                _frame = out
        time.sleep(0.033)

    _stream_running = False


def _start_stream(idx: int):
    global _stream_running, _frame
    _frame = None
    _stream_running = False
    time.sleep(0.1)
    t = threading.Thread(target=_stream_loop, daemon=True)
    t.start()
    time.sleep(0.5)


def _stop_stream():
    global _stream_running
    _stream_running = False


def _get_frame() -> np.ndarray | None:
    with _frame_lock:
        if _frame is None:
            return None
        return _frame.copy()


def _tracking_loop():
    global _track_running, _referencia_salva, _mask_frame

    casas_referencia = None
    candidato_mudancas = None
    tempo_inicio = 0.0
    cooldown_ate = 0.0

    while _track_running:
        frame = _get_frame()
        if frame is None or _detector is None or _detector.pontos_origem is None:
            time.sleep(0.1)
            continue

        tab_atual = _detector.retificar_tabuleiro(frame)
        casas_atuais = _segmentador.fatiar_tabuleiro(tab_atual)

        if not _referencia_salva:
            casas_referencia = casas_atuais
            _referencia_salva = True
            # Salva referencia em data/
            estado_visual_path = DATA_DIR / "estado_visual_pecas.jpg"
            cv2.imwrite(str(estado_visual_path), tab_atual)
            _jogo.salvar_estado_fen(str(DATA_DIR / "estado_partida.fen"))
            emit("tracking_status", {"status": "reference_saved"})
            time.sleep(0.2)
            continue

        if time.time() < cooldown_ate:
            tab_grade = _detector.desenhar_grade_para_teste(tab_atual)
            with _frame_lock:
                _frame = tab_grade
            time.sleep(0.05)
            continue

        mudancas, mapa = _segmentador.detectar_mudancas(casas_referencia, casas_atuais)

        with _mask_lock:
            _mask_frame = mapa

        if 2 <= len(mudancas) <= 4:
            mudancas_ord = sorted(mudancas)

            if candidato_mudancas == mudancas_ord:
                if time.time() - tempo_inicio >= 2.0:
                    traduzidas = [_tradutor.para_notacao(l, c) for l, c in mudancas_ord]
                    lance_uci, mensagem, frase_voz = _jogo.inferir_lance(traduzidas)

                    if lance_uci:
                        historico_entry = {
                            "lance": lance_uci,
                            "turn": "brancas" if _jogo.tabuleiro.turn == chess.BLACK else "pretas",
                        }
                        _historico.append(historico_entry)

                        estado_visual_path = DATA_DIR / "estado_visual_pecas.jpg"
                        cv2.imwrite(str(estado_visual_path), tab_atual)
                        _jogo.salvar_estado_fen(str(DATA_DIR / "estado_partida.fen"))

                        emit("move_detected", {
                            "lance": lance_uci,
                            "mensagem": mensagem,
                            "voz": frase_voz,
                            "fen": _jogo.tabuleiro.fen(),
                            "historico": _historico,
                        })
                        if frase_voz and _voz.ativo:
                            _voz.falar(frase_voz)
                        casas_referencia = casas_atuais
                        cooldown_ate = time.time() + 1.0
                    else:
                        emit("move_alert", {
                            "casas": traduzidas,
                            "mensagem": mensagem,
                        })
                        cooldown_ate = time.time() + 4.0

                    candidato_mudancas = None
            else:
                candidato_mudancas = mudancas_ord
                tempo_inicio = time.time()
        else:
            candidato_mudancas = None

        tab_grade = _detector.desenhar_grade_para_teste(tab_atual)
        with _frame_lock:
            _frame = tab_grade

        time.sleep(0.1)


# ---------- Rotas ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = _get_frame()
            if frame is None:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                ret, buf = cv2.imencode(".jpg", blank)
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                time.sleep(0.1)
                continue

            ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            time.sleep(0.033)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/video_feed/mask")
def video_feed_mask():
    def generate():
        while True:
            with _mask_lock:
                mask = _mask_frame
            if mask is None:
                blank = np.zeros((480, 480), dtype=np.uint8)
                blank_colored = cv2.cvtColor(blank, cv2.COLOR_GRAY2BGR)
                ret, buf = cv2.imencode(".jpg", blank_colored)
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                time.sleep(0.2)
                continue

            mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            ret, buf = cv2.imencode(".jpg", mask_colored, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            time.sleep(0.1)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/cameras", methods=["GET"])
def api_cameras():
    disponiveis = []
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                name = _get_camera_name(i)
                disponiveis.append({
                    "index": i,
                    "width": w,
                    "height": h,
                    "name": name,
                })
            cap.release()
    return jsonify({"cameras": disponiveis})


@app.route("/api/select_camera", methods=["POST"])
def api_select_camera():
    global _detector
    data = request.json
    idx = int(data.get("index", 0))
    _stop_stream()
    time.sleep(0.2)
    _detector = BoardDetector(camera_index=idx)
    if _detector.cap.isOpened():
        _detector.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        _detector.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        _detector.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    _start_stream(idx)
    return jsonify({"ok": True, "camera": idx})


@app.route("/api/calibration/start", methods=["POST"])
def api_calibration_start():
    global _calibrando, _mouse_points
    data = request.json
    modo = data.get("modo", "manual")
    _calibrando = True
    _mouse_points = []
    socketio.emit("calibration_status", {"status": "started", "modo": modo})
    return jsonify({"ok": True})


@app.route("/api/calibration/manual_click", methods=["POST"])
def api_calibration_manual_click():
    global _mouse_points, _detector, _calibrated_points
    data = request.json
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    _mouse_points.append((x, y))

    socketio.emit("click_registered", {"count": len(_mouse_points), "total": 4})

    if len(_mouse_points) == 4:
        _calibrated_points = _mouse_points[:]
        if _detector is not None:
            _detector.pontos_origem = np.array(_mouse_points, dtype=np.float32)
            ultimo = _detector.tamanho_tabuleiro - 1
            _detector.pontos_destino = np.array([
                [0, 0], [ultimo, 0], [ultimo, ultimo], [0, ultimo]
            ], dtype=np.float32)
        _calibrando = False
        socketio.emit("calibration_status", {"status": "complete"})

    return jsonify({"ok": True})


@app.route("/api/calibration/auto", methods=["POST"])
def api_calibration_auto():
    frame = _get_frame()
    if frame is not None and _detector is not None:
        sucesso = _detector.calibrar_automatico(frame)
        if sucesso:
            socketio.emit("calibration_status", {"status": "complete"})
            return jsonify({"ok": True})

    socketio.emit("calibration_status", {"status": "failed"})
    return jsonify({"ok": False})


@app.route("/api/calibration/cancel", methods=["POST"])
def api_calibration_cancel():
    global _calibrando, _mouse_points, _calibrated_points
    _calibrando = False
    _mouse_points = []
    _calibrated_points = None
    socketio.emit("calibration_status", {"status": "cancelled"})
    return jsonify({"ok": True})


@app.route("/api/calibration/undo_point", methods=["POST"])
def api_calibration_undo_point():
    global _mouse_points
    if len(_mouse_points) > 0:
        _mouse_points.pop()
    return jsonify({"ok": True, "count": len(_mouse_points)})


@app.route("/api/calibration/reset_points", methods=["POST"])
def api_calibration_reset_points():
    global _detector, _calibrated_points
    if _detector is not None:
        _detector.pontos_origem = None
    _calibrated_points = None
    return jsonify({"ok": True})


@app.route("/api/save_reference", methods=["POST"])
def api_save_reference():
    global _referencia_salva
    _referencia_salva = False
    socketio.emit("tracking_status", {"status": "reference_needed"})
    return jsonify({"ok": True})


@app.route("/api/tracking/start", methods=["POST"])
def api_tracking_start():
    global _track_running, _track_thread
    _track_running = True
    _track_thread = threading.Thread(target=_tracking_loop, daemon=True)
    _track_thread.start()
    socketio.emit("tracking_status", {"status": "started"})
    return jsonify({"ok": True})


@app.route("/api/tracking/stop", methods=["POST"])
def api_tracking_stop():
    global _track_running
    _track_running = False
    socketio.emit("tracking_status", {"status": "stopped"})
    return jsonify({"ok": True})


@app.route("/api/undo", methods=["POST"])
def api_undo():
    global _referencia_salva
    lance, sucesso = _jogo.desfazer_lance()
    if sucesso:
        _referencia_salva = False
        if _historico:
            _historico.pop()
        # Salva estado apos desfazer
        _jogo.salvar_estado_fen(str(DATA_DIR / "estado_partida.fen"))
        socketio.emit("move_undone", {"lance": lance, "fen": _jogo.tabuleiro.fen()})
        return jsonify({"ok": True, "lance": lance})
    return jsonify({"ok": False, "error": "Nao ha lances para desfazer"})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global _referencia_salva, _historico
    _jogo.reiniciar_jogo()
    _referencia_salva = False
    _historico = []
    _jogo.salvar_estado_fen(str(DATA_DIR / "estado_partida.fen"))
    socketio.emit("game_reset", {"fen": _jogo.tabuleiro.fen()})
    return jsonify({"ok": True})


@app.route("/api/voice/toggle", methods=["POST"])
def api_voice_toggle():
    ativo = _voz.alternar()
    socketio.emit("voice_toggled", {"ativo": ativo})
    return jsonify({"ok": True, "ativo": ativo})


@app.route("/api/voice/config", methods=["POST"])
def api_voice_config():
    data = request.json
    if "velocidade" in data:
        _voz.velocidade = max(1.0, min(4.0, float(data["velocidade"])))
    if "fonetica" in data:
        _jogo.fonetica = bool(data["fonetica"])
    socketio.emit("voice_config_updated", {
        "velocidade": _voz.velocidade,
        "fonetica": _jogo.fonetica,
        "ativo": _voz.ativo,
    })
    return jsonify({"ok": True})


@app.route("/api/voice/test", methods=["POST"])
def api_voice_test():
    frase = request.json.get("frase", "Ola, este e um teste de voz.") if request and request.is_json else "Ola, este e um teste de voz."
    if _voz.ativo:
        _voz.falar(frase)
    return jsonify({"ok": True})


@app.route("/api/status", methods=["GET"])
def api_status():
    frame = _get_frame()
    size = None
    if frame is not None:
        size = {"width": frame.shape[1], "height": frame.shape[0]}
    calibrated = _calibrated_points is not None or (
        _detector is not None and _detector.pontos_origem is not None
    )
    return jsonify({
        "camera_active": _stream_running,
        "calibrated": calibrated,
        "reference_saved": _referencia_salva,
        "tracking": _track_running,
        "voice_active": _voz.ativo,
        "voice_speed": _voz.velocidade,
        "voice_fonetica": _jogo.fonetica,
        "historico": _historico,
        "frame_size": size,
    })


@app.route("/api/board", methods=["GET"])
def api_board():
    return jsonify({
        "fen": _jogo.tabuleiro.fen(),
        "turn": "white" if _jogo.tabuleiro.turn else "black",
        "board": str(_jogo.tabuleiro),
    })


def main():
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
