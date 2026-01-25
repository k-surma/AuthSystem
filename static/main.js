let qrStream = null;
let faceStream = null;
let capturedImage = null;
let qrScanInterval = null;
let faceCaptureInterval = null;
let validatedQrCode = null;
let lastQrCode = null;
let verificationCompleted = false; // Flaga zapobiegająca dalszemu próbkowaniu po weryfikacji
let verificationInProgress = false; // Flaga zapobiegająca równoległym wywołaniom weryfikacji

// Uruchomienie skanowania QR
async function startQRScan() {
    try {
        // Sprawdź czy jsQR jest dostępne
        if (typeof jsQR === 'undefined') {
            updateQRStatus('Błąd: Biblioteka jsQR nie jest załadowana. Odśwież stronę.', 'error');
            return;
        }
        
        // Spróbuj najpierw tylnej kamery, potem przedniej
        let constraints = { 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 }
            } 
        };
        
        try {
            // Spróbuj tylnej kamery (dla QR kodów)
            constraints.video.facingMode = 'environment';
            qrStream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (e) {
            // Jeśli tylna kamera nie działa, użyj przedniej
            try {
                constraints.video.facingMode = 'user';
                qrStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (e2) {
                // Jeśli określenie facingMode nie działa, spróbuj bez niego
                delete constraints.video.facingMode;
                qrStream = await navigator.mediaDevices.getUserMedia(constraints);
            }
        }
        
        const video = document.getElementById('qr-video');
        if (!video) {
            throw new Error('Element video nie znaleziony');
        }
        
        video.srcObject = qrStream;
        video.style.display = 'block';
        
        // Poczekaj aż video będzie gotowe
        video.onloadedmetadata = () => {
            document.getElementById('start-qr-scan-btn').style.display = 'none';
            document.getElementById('stop-qr-scan-btn').style.display = 'inline-block';
            updateQRStatus('Skanowanie QR...', 'info');
            
            // Automatyczne skanowanie QR kilka razy na sekundę
            qrScanInterval = setInterval(scanQRCode, 200); // 5 razy na sekundę
        };
        
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        updateQRStatus('Błąd: Nie można uzyskać dostępu do kamery. ' + error.message, 'error');
    }
}

// Zatrzymanie skanowania QR
function stopQRScan() {
    if (qrStream) {
        qrStream.getTracks().forEach(track => track.stop());
        qrStream = null;
    }
    if (qrScanInterval) {
        clearInterval(qrScanInterval);
        qrScanInterval = null;
    }
    const video = document.getElementById('qr-video');
    if (video && video.srcObject) {
        video.srcObject = null;
    }
    if (video) {
        video.style.display = 'none';
    }
    document.getElementById('start-qr-scan-btn').style.display = 'inline-block';
    document.getElementById('stop-qr-scan-btn').style.display = 'none';
}

// Skanowanie kodu QR
function scanQRCode() {
    const video = document.getElementById('qr-video');
    const canvas = document.getElementById('qr-canvas');
    
    if (!video || !canvas) {
        return;
    }
    
    if (!video.videoWidth || !video.videoHeight || video.readyState !== video.HAVE_ENOUGH_DATA) {
        return;
    }
    
    // Sprawdź czy jsQR jest dostępne
    if (typeof jsQR === 'undefined') {
        console.error('jsQR nie jest załadowane');
        return;
    }
    
    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "dontInvert",
        });
        
        if (code && code.data && code.data !== lastQrCode) {
            lastQrCode = code.data;
            document.getElementById('qr-code').value = code.data;
            validateQRCode(code.data);
        }
    } catch (error) {
        console.error('Błąd podczas skanowania QR:', error);
    }
}

// Aktualizacja statusu QR
function updateQRStatus(message, type = 'info') {
    const statusEl = document.getElementById('qr-status');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    if (type === 'error') {
        statusEl.style.color = '#f44336';
    } else if (type === 'success') {
        statusEl.style.color = '#4CAF50';
    } else {
        statusEl.style.color = '#2196F3';
    }
}

// Walidacja kodu QR
async function validateQRCode(qrCode) {
    try {
        // Zapisujemy kod QR i przechodzimy do weryfikacji twarzy
        // Weryfikacja QR nastąpi podczas weryfikacji twarzy w endpoint /api/verify
        validatedQrCode = qrCode;
        updateQRStatus('✓ Kod QR zeskanowany. Przechodzenie do weryfikacji twarzy...', 'success');
        
        stopQRScan();
        
        // Przejdź do kroku 2 - weryfikacja twarzy
        setTimeout(() => {
            document.getElementById('qr-scan-section').style.display = 'none';
            document.getElementById('face-verify-section').style.display = 'block';
            startFaceVerification();
        }, 1000);
        
    } catch (error) {
        console.error('Błąd walidacji QR:', error);
        updateQRStatus('Błąd podczas sprawdzania kodu QR', 'error');
    }
}

// Uruchomienie weryfikacji twarzy
async function startFaceVerification() {
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'user',
                width: { ideal: 640 },
                height: { ideal: 480 }
            } 
        });
        const video = document.getElementById('video');
        video.srcObject = faceStream;
        
        updateStatus('Kamera gotowa. Wykrywanie twarzy...', 'info');
        
        // Automatyczne próbkowanie kilka razy na sekundę
        faceCaptureInterval = setInterval(captureAndVerifyFace, 500); // 2 razy na sekundę
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        updateStatus('Błąd: Nie można uzyskać dostępu do kamery', 'error');
    }
}

// Zatrzymanie weryfikacji twarzy
function stopFaceVerification() {
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
    if (faceCaptureInterval) {
        clearInterval(faceCaptureInterval);
        faceCaptureInterval = null;
    }
    const video = document.getElementById('video');
    if (video && video.srcObject) {
        video.srcObject = null;
    }
}

// Automatyczne przechwytywanie i weryfikacja twarzy
async function captureAndVerifyFace() {
    // Zatrzymaj próbkowanie jeśli weryfikacja już została ukończona lub jest w trakcie
    if (verificationCompleted || verificationInProgress) {
        return;
    }
    
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    
    if (!video || !canvas) {
        return;
    }
    
    if (!video.videoWidth || !video.videoHeight || video.readyState !== video.HAVE_ENOUGH_DATA) {
        return;
    }
    
    if (!validatedQrCode) {
        return;
    }
    
    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0);
        
        // Konwertuj canvas na blob
        canvas.toBlob(async (blob) => {
            if (blob && blob.size > 0 && !verificationCompleted && !verificationInProgress) {
                // Ustaw flagę przed rozpoczęciem weryfikacji
                verificationInProgress = true;
                capturedImage = blob;
                updateStatus('✓ Twarz wykryta. Weryfikacja w toku...', 'info');
                
                // Automatyczna weryfikacja
                await verifyAccess();
            }
        }, 'image/jpeg', 0.95);
    } catch (error) {
        console.error('Błąd podczas przechwytywania twarzy:', error);
        verificationInProgress = false; // Reset w przypadku błędu
    }
}

// Aktualizacja statusu
function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
}

// Weryfikacja dostępu
async function verifyAccess() {
    const qrCode = validatedQrCode || document.getElementById('qr-code').value.trim();
    const resultEl = document.getElementById('result');
    
    if (!qrCode) {
        resultEl.textContent = 'Proszę wprowadzić kod QR';
        resultEl.className = 'result-message error';
        verificationInProgress = false; // Reset flagi
        return;
    }
    
    if (!capturedImage) {
        verificationInProgress = false; // Reset flagi
        return; // Czekaj na zdjęcie
    }
    
    const formData = new FormData();
    formData.append('qr_code', qrCode);
    formData.append('image', capturedImage, 'photo.jpg');
    
    resultEl.textContent = 'Weryfikacja w toku...';
    resultEl.className = 'result-message';
    
    try {
        const response = await fetch('/api/verify', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Zatrzymaj automatyczne próbkowanie po weryfikacji
        if (faceCaptureInterval) {
            clearInterval(faceCaptureInterval);
            faceCaptureInterval = null;
        }
        
        // Zatrzymaj dalsze próbkowanie po pierwszej weryfikacji
        verificationCompleted = true;
        verificationInProgress = false; // Reset flagi po zakończeniu weryfikacji
        
        if (data.success) {
            const userName = data.first_name && data.last_name 
                ? `${data.first_name} ${data.last_name}` 
                : 'Użytkowniku';
            resultEl.textContent = `WITAJ ${userName.toUpperCase()}! ${data.message} (Score: ${(data.match_score * 100).toFixed(1)}%)`;
            resultEl.className = 'result-message success';
            updateStatus('Dostęp przyznany!', 'success');
        } else {
            if (data.result === 'SUSPICIOUS') {
                resultEl.textContent = `⚠ ${data.message}`;
                resultEl.className = 'result-message warning';
                updateStatus('Podejrzana sytuacja wykryta!', 'warning');
            } else {
                resultEl.textContent = `✗ ${data.message}`;
                resultEl.className = 'result-message error';
                updateStatus('Dostęp odrzucony', 'error');
            }
        }
        
        // Reset po 5 sekundach
        setTimeout(() => {
            resetVerification();
        }, 5000);
        
    } catch (error) {
        console.error('Błąd weryfikacji:', error);
        resultEl.textContent = 'Błąd podczas weryfikacji. Spróbuj ponownie.';
        resultEl.className = 'result-message error';
        verificationInProgress = false; // Reset flagi w przypadku błędu
        verificationCompleted = true; // Zatrzymaj próbkowanie nawet przy błędzie
    }
}

// Reset weryfikacji
function resetVerification() {
    capturedImage = null;
    validatedQrCode = null;
    lastQrCode = null;
    verificationCompleted = false; // Reset flagi dla następnej weryfikacji
    verificationInProgress = false; // Reset flagi dla następnej weryfikacji
    document.getElementById('qr-code').value = '';
    document.getElementById('result').textContent = '';
    document.getElementById('result').className = 'result-message';
    
    // Wróć do kroku 1
    stopFaceVerification();
    document.getElementById('face-verify-section').style.display = 'none';
    document.getElementById('qr-scan-section').style.display = 'block';
    updateQRStatus('Gotowe do skanowania QR', 'info');
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Event listeners dla skanowania QR
    const startQrScanBtn = document.getElementById('start-qr-scan-btn');
    const stopQrScanBtn = document.getElementById('stop-qr-scan-btn');
    
    if (startQrScanBtn) {
        startQrScanBtn.addEventListener('click', startQRScan);
    }
    if (stopQrScanBtn) {
        stopQrScanBtn.addEventListener('click', stopQRScan);
    }
    
    // Ręczne wprowadzanie kodu QR
    const qrCodeInput = document.getElementById('qr-code');
    if (qrCodeInput) {
        qrCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.value.trim()) {
                e.preventDefault();
                validateQRCode(e.target.value.trim());
            }
        });
        qrCodeInput.addEventListener('input', (e) => {
            if (e.target.value.trim() && e.target.value.trim() !== lastQrCode) {
                lastQrCode = e.target.value.trim();
                // Automatyczna walidacja po wprowadzeniu
                setTimeout(() => {
                    if (e.target.value.trim() === lastQrCode) {
                        validateQRCode(e.target.value.trim());
                    }
                }, 1000);
            }
        });
    }
    
    // Cleanup przy zamknięciu strony
    window.addEventListener('beforeunload', () => {
        stopQRScan();
        stopFaceVerification();
    });
});
