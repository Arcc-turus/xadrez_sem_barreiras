(function () {
    "use strict";

    const socket = io();

    // Elementos de fase
    const phaseSelect = document.getElementById("phaseSelect");
    const phaseFeed = document.getElementById("phaseFeed");
    const cameraSelect = document.getElementById("cameraSelect");
    const btnSelectCamera = document.getElementById("btnSelectCamera");

    // Video
    const videoFeed = document.getElementById("videoFeed");
    const videoWrapper = document.getElementById("videoWrapper");
    const overlay = document.getElementById("overlay");
    const overlayContent = document.getElementById("overlayContent");
    const overlayText = document.getElementById("overlayText");
    const overlayHint = document.getElementById("overlayHint");
    const crosshairCursor = document.getElementById("crosshairCursor");
    const markersContainer = document.getElementById("markersContainer");

    // Mascara
    const maskFeed = document.getElementById("maskFeed");
    const maskWrapper = document.getElementById("maskWrapper");
    const btnToggleMask = document.getElementById("btnToggleMask");
    let showMask = false;

    // Controles por fase
    const controlsPreCal = document.getElementById("controlsPreCal");
    const controlsCalibrating = document.getElementById("controlsCalibrating");
    const controlsPostCal = document.getElementById("controlsPostCal");
    const controlsTracking = document.getElementById("controlsTracking");

    const btnCalibrate = document.getElementById("btnCalibrate");
    const calibrationStepInfo = document.getElementById("calibrationStepInfo");
    const btnUndoPoint = document.getElementById("btnUndoPoint");
    const btnResetCalibration = document.getElementById("btnResetCalibration");
    const btnSaveRef = document.getElementById("btnSaveRef");
    const btnCalibrateAgain = document.getElementById("btnCalibrateAgain");
    const btnStopTrack = document.getElementById("btnStopTrack");
    const btnVoice = document.getElementById("btnVoice");
    const btnVoiceConfig = document.getElementById("btnVoiceConfig");
    const btnUndoMove = document.getElementById("btnUndoMove");
    const btnResetGame = document.getElementById("btnResetGame");

    // Modal calibracao
    const calibrationModal = document.getElementById("calibrationModal");
    const btnManual = document.getElementById("btnManual");
    const btnAuto = document.getElementById("btnAuto");
    const btnCancelModal = document.getElementById("btnCancelModal");

    // Modal voz
    const voiceModal = document.getElementById("voiceModal");
    const cbVoiceActive = document.getElementById("cbVoiceActive");
    const cbPhonetic = document.getElementById("cbPhonetic");
    const voiceSlider = document.getElementById("voiceSlider");
    const voiceSpeedValue = document.getElementById("voiceSpeedValue");
    const btnTestVoice = document.getElementById("btnTestVoice");
    const btnCloseVoice = document.getElementById("btnCloseVoice");

    // Status
    const history = document.getElementById("history");
    const historyList = document.getElementById("historyList");
    const alertsDiv = document.getElementById("alerts");

    let calibrating = false;
    let calibrationMode = "";
    let clickCount = 0;
    let tracking = false;
    let referenceSaved = false;
    let calibrated = false;
    let voiceActive = true;
    let voiceSpeed = 1.0;
    let phonetic = false;
    let historico = [];
    let markerPositions = [];

    // ----- Cameras -----
    async function loadCameras() {
        try {
            const res = await fetch("/api/cameras");
            const data = await res.json();
            cameraSelect.innerHTML = "";

            if (data.cameras.length === 0) {
                cameraSelect.innerHTML = '<option value="">Nenhuma camera encontrada</option>';
                btnSelectCamera.disabled = true;
                return;
            }

            data.cameras.forEach(function (cam) {
                const opt = document.createElement("option");
                opt.value = cam.index;
                var label = cam.name + " (" + cam.width + "x" + cam.height + ")";
                opt.textContent = label;
                cameraSelect.appendChild(opt);
            });

            btnSelectCamera.disabled = false;
        } catch (err) {
            showAlert("Erro ao carregar cameras", "error");
        }
    }

    btnSelectCamera.addEventListener("click", async function () {
        const idx = cameraSelect.value;
        if (idx === "") return;

        try {
            const res = await fetch("/api/select_camera", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ index: parseInt(idx) }),
            });
            const data = await res.json();

            if (data.ok) {
                phaseSelect.style.display = "none";
                phaseFeed.style.display = "flex";
                showPhase("preCal");
                videoFeed.src = "/video_feed?t=" + Date.now();
                showAlert("Camera " + idx + " ativa", "success");
                loadStatus();
            }
        } catch (err) {
            showAlert("Erro de conexao", "error");
        }
    });

    // ----- Fases -----
    function showPhase(phase) {
        controlsPreCal.style.display = phase === "preCal" ? "flex" : "none";
        controlsCalibrating.style.display = phase === "calibrating" ? "flex" : "none";
        controlsPostCal.style.display = phase === "postCal" ? "flex" : "none";
        controlsTracking.style.display = phase === "tracking" ? "flex" : "none";
        history.style.display = (phase === "tracking") ? "" : "none";
    }

    // ----- Calibracao -----
    btnCalibrate.addEventListener("click", function () {
        calibrationModal.style.display = "flex";
    });

    btnManual.addEventListener("click", function () {
        calibrationModal.style.display = "none";
        startCalibration("manual");
    });

    btnAuto.addEventListener("click", function () {
        calibrationModal.style.display = "none";
        startCalibration("auto");
    });

    btnCancelModal.addEventListener("click", function () {
        calibrationModal.style.display = "none";
    });

    function startCalibration(modo) {
        calibrating = true;
        calibrationMode = modo;
        clickCount = 0;
        markerPositions = [];
        markersContainer.innerHTML = "";

        overlay.classList.add("active");
        showPhase("calibrating");
        updateCalibrationInfo();

        if (modo === "manual") {
            overlayContent.style.display = "block";
            overlayText.textContent = "Calibracao Manual";
            overlayHint.textContent = "Clique nos 4 cantos do tabuleiro";
            crosshairCursor.style.display = "block";
        } else {
            overlayContent.style.display = "none";
            doAutoCalibration();
        }

        fetch("/api/calibration/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ modo: modo }),
        });
    }

    function updateCalibrationInfo() {
        calibrationStepInfo.textContent = "Ponto " + clickCount + " de 4";
    }

    videoWrapper.addEventListener("mousemove", function (e) {
        if (!calibrating || calibrationMode !== "manual") return;

        const feedRect = videoFeed.getBoundingClientRect();

        if (
            e.clientX < feedRect.left ||
            e.clientX > feedRect.right ||
            e.clientY < feedRect.top ||
            e.clientY > feedRect.bottom
        ) {
            crosshairCursor.style.display = "none";
            return;
        }

        crosshairCursor.style.display = "block";
        const x = e.clientX - feedRect.left;
        const y = e.clientY - feedRect.top;
        crosshairCursor.style.left = x + "px";
        crosshairCursor.style.top = y + "px";
    });

    videoWrapper.addEventListener("mouseleave", function () {
        crosshairCursor.style.display = "none";
    });

    videoWrapper.addEventListener("click", function (e) {
        if (!calibrating || calibrationMode !== "manual") return;

        const feedRect = videoFeed.getBoundingClientRect();

        if (
            e.clientX < feedRect.left ||
            e.clientX > feedRect.right ||
            e.clientY < feedRect.top ||
            e.clientY > feedRect.bottom
        ) {
            return;
        }

        const clickX = e.clientX - feedRect.left;
        const clickY = e.clientY - feedRect.top;

        const scaleX = videoFeed.naturalWidth / feedRect.width;
        const scaleY = videoFeed.naturalHeight / feedRect.height;
        const realX = Math.round(clickX * scaleX);
        const realY = Math.round(clickY * scaleY);

        fetch("/api/calibration/manual_click", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x: realX, y: realY }),
        });

        clickCount++;
        markerPositions.push({ x: clickX, y: clickY });
        renderMarkers();
        updateCalibrationInfo();

        if (clickCount >= 4) {
            setTimeout(function () {
                finishCalibration("Calibracao manual concluida!", "success");
            }, 500);
        }
    });

    function renderMarkers() {
        markersContainer.innerHTML = "";
        for (let i = 0; i < markerPositions.length; i++) {
            addCrosshairMarker(markerPositions[i].x, markerPositions[i].y, i + 1);
        }
    }

    function addCrosshairMarker(x, y, num) {
        const marker = document.createElement("div");
        marker.className = "calibration-marker";
        marker.style.left = x + "px";
        marker.style.top = y + "px";

        marker.innerHTML =
            '<div class="line-h"></div>' +
            '<div class="line-v"></div>' +
            '<div class="dot"></div>' +
            '<div class="label">' + num + '</div>';

        markersContainer.appendChild(marker);
    }

    btnUndoPoint.addEventListener("click", function () {
        if (!calibrating || clickCount === 0) return;

        fetch("/api/calibration/undo_point", { method: "POST" });

        markerPositions.pop();
        clickCount--;
        renderMarkers();
        updateCalibrationInfo();
    });

    btnResetCalibration.addEventListener("click", function () {
        cancelCalibration();
    });

    function finishCalibration(msg, type) {
        overlay.classList.remove("active");
        overlayContent.style.display = "none";
        crosshairCursor.style.display = "none";
        calibrating = false;
        calibrated = true;
        markerPositions = [];
        markersContainer.innerHTML = "";
        showAlert(msg, type);
        showPhase("postCal");
        loadStatus();
    }

    function cancelCalibration() {
        fetch("/api/calibration/cancel", { method: "POST" });
        overlay.classList.remove("active");
        overlayContent.style.display = "none";
        crosshairCursor.style.display = "none";
        calibrating = false;
        clickCount = 0;
        markerPositions = [];
        markersContainer.innerHTML = "";
        showPhase("preCal");
    }

    async function doAutoCalibration() {
        try {
            const res = await fetch("/api/calibration/auto", { method: "POST" });
            const data = await res.json();

            if (data.ok) {
                finishCalibration("Calibracao automatica concluida", "success");
            } else {
                cancelCalibration();
                showAlert("Calibracao automatica falhou", "error");
            }
        } catch (err) {
            cancelCalibration();
            showAlert("Erro na calibracao automatica", "error");
        }
    }

    // ----- Pos-calibracao -----
    btnSaveRef.addEventListener("click", function () {
        fetch("/api/save_reference", { method: "POST" });
    });

    btnCalibrateAgain.addEventListener("click", function () {
        calibrated = false;
        referenceSaved = false;
        // Limpa pontos no servidor para voltar a imagem original da camera
        fetch("/api/calibration/reset_points", { method: "POST" });
        showPhase("preCal");
        showAlert("Pronto para recalibrar", "info");
    });

    // ----- Mascara de diferenca -----
    btnToggleMask.addEventListener("click", function () {
        showMask = !showMask;
        maskWrapper.style.display = showMask ? "" : "none";
        btnToggleMask.textContent = showMask ? "Esconder mascara" : "Mascara";
        if (showMask) {
            maskFeed.src = "/video_feed/mask?t=" + Date.now();
        } else {
            maskFeed.src = "";
        }
    });

    // ----- Rastreio -----
    socket.on("tracking_status", function (data) {
        if (data.status === "reference_saved") {
            referenceSaved = true;
            showAlert("Referencia salva! Faca seu lance.", "success");
            tracking = true;
            showPhase("tracking");
            loadStatus();
        } else if (data.status === "reference_needed") {
            referenceSaved = false;
            showAlert("Referencia limpa. Reposicione e salve novamente.", "info");
        } else if (data.status === "started") {
            tracking = true;
            showAlert("Rastreio iniciado!", "success");
            showPhase("tracking");
        } else if (data.status === "stopped") {
            tracking = false;
            showAlert("Rastreio parado.", "info");
            showPhase("postCal");
        }
    });

    btnStopTrack.addEventListener("click", function () {
        fetch("/api/tracking/stop", { method: "POST" });
    });

    // ----- Voz -----
    btnVoice.addEventListener("click", function () {
        fetch("/api/voice/toggle", { method: "POST" });
    });

    socket.on("voice_toggled", function (data) {
        voiceActive = data.ativo;
        btnVoice.textContent = voiceActive ? "Voz: ON" : "Voz: OFF";
        cbVoiceActive.checked = voiceActive;
        if (!voiceActive && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    });

    socket.on("voice_config_updated", function (data) {
        voiceActive = data.ativo;
        voiceSpeed = data.velocidade;
        phonetic = data.fonetica;
        btnVoice.textContent = voiceActive ? "Voz: ON" : "Voz: OFF";
        cbVoiceActive.checked = voiceActive;
        cbPhonetic.checked = phonetic;
        voiceSlider.value = voiceSpeed;
        voiceSpeedValue.textContent = voiceSpeed.toFixed(1);
    });

    btnVoiceConfig.addEventListener("click", function () {
        cbVoiceActive.checked = voiceActive;
        cbPhonetic.checked = phonetic;
        voiceSlider.value = voiceSpeed;
        voiceSpeedValue.textContent = voiceSpeed.toFixed(1);
        voiceModal.style.display = "flex";
    });

    btnCloseVoice.addEventListener("click", function () {
        voiceModal.style.display = "none";
    });

    cbVoiceActive.addEventListener("change", function () {
        voiceActive = cbVoiceActive.checked;
        if (!voiceActive && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
        sendVoiceConfig();
    });

    cbPhonetic.addEventListener("change", function () {
        phonetic = cbPhonetic.checked;
        sendVoiceConfig();
    });

    voiceSlider.addEventListener("input", function () {
        voiceSpeed = parseFloat(voiceSlider.value);
        voiceSpeedValue.textContent = voiceSpeed.toFixed(1);
        sendVoiceConfig();
    });

    function sendVoiceConfig() {
        fetch("/api/voice/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ativo: voiceActive,
                fonetica: phonetic,
                velocidade: voiceSpeed,
            }),
        });
    }

    btnTestVoice.addEventListener("click", function () {
        if (voiceActive) {
            speakText("Ola, este e um teste de voz.");
            showAlert("Teste de voz executado", "success");
        } else {
            showAlert("Ative a voz primeiro", "error");
        }
    });

    // ----- Jogadas -----
    socket.on("move_detected", function (data) {
        showAlert("Lance: " + data.lance + " - " + data.mensagem, "success");
        if (data.historico) {
            historico = data.historico;
            renderHistory();
        }
        if (data.voz && voiceActive) {
            speakText(data.voz);
        } else if (data.voz && !voiceActive) {
            console.log("[voz] Voz desativada, nao falando:", data.voz);
        }
    });

    function speakText(texto) {
        if (!("speechSynthesis" in window)) {
            console.log("[voz] SpeechSynthesis nao suportado");
            return;
        }
        console.log("[voz] Falando:", texto, "rate:", voiceSpeed);
        window.speechSynthesis.cancel();
        var utterance = new SpeechSynthesisUtterance(texto);
        utterance.lang = "pt-BR";
        utterance.rate = Math.max(0.1, Math.min(10, voiceSpeed));
        utterance.volume = 1.0;
        utterance.onend = function() { console.log("[voz] Terminou de falar"); };
        utterance.onerror = function(e) { console.log("[voz] Erro:", e); };
        window.speechSynthesis.speak(utterance);
    }

    socket.on("move_alert", function (data) {
        showAlert("Lance invalido: " + data.casas.join(", "), "error");
    });

    socket.on("move_undone", function (data) {
        showAlert("Lance desfeito: " + data.lance, "info");
        if (historico.length > 0) historico.pop();
        renderHistory();
    });

    btnUndoMove.addEventListener("click", function () {
        fetch("/api/undo", { method: "POST" });
    });

    btnResetGame.addEventListener("click", function () {
        fetch("/api/reset", { method: "POST" });
    });

    socket.on("game_reset", function (data) {
        showAlert("Partida reiniciada!", "info");
        historico = [];
        renderHistory();
    });

    socket.on("calibration_status", function (data) {
        if (data.status === "complete") {
            finishCalibration("Calibracao concluida!", "success");
        } else if (data.status === "failed") {
            cancelCalibration();
            showAlert("Nao foi possivel detectar o tabuleiro", "error");
        }
    });

    // ----- Helpers -----
    function renderHistory() {
        if (historico.length === 0) {
            historyList.innerHTML = '<p class="history-empty">Nenhuma jogada ainda.</p>';
            return;
        }

        historyList.innerHTML = "";

        for (let i = 0; i < historico.length; i += 2) {
            const row = document.createElement("div");
            row.style.display = "flex";
            row.style.gap = "8px";
            row.style.padding = "4px 0";
            row.style.fontSize = "0.85rem";

            const numSpan = document.createElement("span");
            numSpan.style.color = "#8b949e";
            numSpan.style.minWidth = "30px";
            numSpan.style.fontWeight = "600";
            numSpan.textContent = (Math.floor(i / 2) + 1) + ".";
            row.appendChild(numSpan);

            const move1 = document.createElement("span");
            move1.textContent = historico[i].lance;
            move1.style.color = "#c9d1d9";
            move1.style.fontFamily = "'Courier New', monospace";
            row.appendChild(move1);

            if (i + 1 < historico.length) {
                const move2 = document.createElement("span");
                move2.textContent = historico[i + 1].lance;
                move2.style.color = "#c9d1d9";
                move2.style.fontFamily = "'Courier New', monospace";
                move2.style.marginLeft = "8px";
                row.appendChild(move2);
            }

            historyList.appendChild(row);
        }

        historyList.scrollTop = historyList.scrollHeight;
    }

    async function loadStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            calibrated = data.calibrated;
            referenceSaved = data.reference_saved;
            tracking = data.tracking;
            voiceActive = data.voice_active;
            voiceSpeed = data.voice_speed;
            phonetic = data.voice_fonetica;
            if (data.historico) {
                historico = data.historico;
                renderHistory();
            }
            btnVoice.textContent = voiceActive ? "Voz: ON" : "Voz: OFF";
            cbVoiceActive.checked = voiceActive;
            cbPhonetic.checked = phonetic;
            voiceSlider.value = voiceSpeed;
            voiceSpeedValue.textContent = voiceSpeed.toFixed(1);

            if (tracking) {
                showPhase("tracking");
            } else if (calibrated) {
                showPhase("postCal");
            } else {
                showPhase("preCal");
            }
        } catch (err) {}
    }

    function showAlert(msg, type) {
        const el = document.createElement("div");
        el.className = "alert " + type;
        el.textContent = msg;
        alertsDiv.prepend(el);
        setTimeout(function () {
            el.style.opacity = "0";
            el.style.transition = "opacity 0.5s";
            setTimeout(function () { el.remove(); }, 500);
        }, 6000);
        while (alertsDiv.children.length > 5) {
            alertsDiv.lastChild.remove();
        }
    }

    loadCameras();
})();
