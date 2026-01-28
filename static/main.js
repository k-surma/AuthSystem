let qrStream = null;
let faceStream = null;
let capturedImage = null;
let qrScanInterval = null;
let faceCaptureInterval = null;
let validatedQrCode = null;
let lastQrCode = null;
let verificationCompleted = false;
let verificationInProgress = false;
let capturedImages = [];
let captureSessionActive = false;

async function startQRScan() {
    try {
        if (typeof jsQR === 'undefined') {
            updateQRStatus('Błąd: Biblioteka jsQR nie jest załadowana. Odśwież stronę.', 'error');
            return;
        }
        
        let constraints = { 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 }
            } 
        };
        
        try {
            constraints.video.facingMode = 'environment';
            qrStream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (e) {
            try {
                constraints.video.facingMode = 'user';
                qrStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (e2) {
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
        
        video.onloadedmetadata = () => {
            document.getElementById('start-qr-scan-btn').style.display = 'none';
            document.getElementById('stop-qr-scan-btn').style.display = 'inline-block';
            updateQRStatus('Skanowanie QR...', 'info');
            
            qrScanInterval = setInterval(scanQRCode, 200);
        };
        
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        updateQRStatus('Błąd: Nie można uzyskać dostępu do kamery. ' + error.message, 'error');
    }
}

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

function scanQRCode() {
    const video = document.getElementById('qr-video');
    const canvas = document.getElementById('qr-canvas');
    
    if (!video || !canvas) {
        return;
    }
    
    if (!video.videoWidth || !video.videoHeight || video.readyState !== video.HAVE_ENOUGH_DATA) {
        return;
    }
    
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

async function validateQRCode(qrCode) {
    try {
        validatedQrCode = qrCode;
        updateQRStatus('✓ Kod QR zeskanowany. Przechodzenie do weryfikacji twarzy...', 'success');
        
        stopQRScan();
        
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
        
        faceCaptureInterval = setInterval(captureAndVerifyFace, 800);
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        updateStatus('Błąd: Nie można uzyskać dostępu do kamery', 'error');
    }
}

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

async function captureAndVerifyFace() {
    if (verificationCompleted || verificationInProgress || captureSessionActive) {
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
        captureSessionActive = true;
        capturedImages = [];

        updateStatus('Ustaw twarz na środku i mrugnij (zbieranie próbek)...', 'info');

        const maxFrames = 6;
        const intervalMs = 350;
        const maxDurationMs = 2500;
        const startTs = Date.now();

        const grabFrame = async () => {
            if (verificationCompleted || verificationInProgress) return;

            context.drawImage(video, 0, 0);
            await new Promise((resolve) => {
                canvas.toBlob((blob) => {
                    if (blob && blob.size > 0) capturedImages.push(blob);
                    resolve();
                }, 'image/jpeg', 0.95);
            });
        };

        while (
            capturedImages.length < maxFrames &&
            (Date.now() - startTs) < maxDurationMs &&
            !verificationCompleted &&
            !verificationInProgress
        ) {
            await grabFrame();
            await new Promise((r) => setTimeout(r, intervalMs));
        }

        if (capturedImages.length === 0) {
            captureSessionActive = false;
            return;
        }

        verificationInProgress = true;
        capturedImage = capturedImages[0];
        updateStatus('✓ Weryfikacja w toku...', 'info');

        await verifyAccess();
        captureSessionActive = false;
    } catch (error) {
        console.error('Błąd podczas przechwytywania twarzy:', error);
        verificationInProgress = false;
        captureSessionActive = false;
    }
}

function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
}

async function verifyAccess() {
    const qrCode = validatedQrCode || document.getElementById('qr-code').value.trim();
    const resultEl = document.getElementById('result');
    
    if (!qrCode) {
        resultEl.textContent = 'Proszę wprowadzić kod QR';
        resultEl.className = 'result-message error';
        verificationInProgress = false;
        return;
    }
    
    if (!capturedImage && (!capturedImages || capturedImages.length === 0)) {
        verificationInProgress = false;
        return;
    }
    
    const formData = new FormData();
    formData.append('qr_code', qrCode);
    if (capturedImages && capturedImages.length >= 2) {
        capturedImages.slice(0, 6).forEach((b, idx) => {
            formData.append('images', b, `frame${idx + 1}.jpg`);
        });
    } else {
        formData.append('image', capturedImage, 'photo.jpg');
    }
    
    resultEl.textContent = 'Weryfikacja w toku...';
    resultEl.className = 'result-message';
    
    try {
        const response = await fetch('/api/verify', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (faceCaptureInterval) {
            clearInterval(faceCaptureInterval);
            faceCaptureInterval = null;
        }
        
        verificationCompleted = true;
        verificationInProgress = false;
        
        if (data.success) {
            const userName = data.first_name && data.last_name 
                ? `${data.first_name} ${data.last_name}` 
                : 'Użytkowniku';
            resultEl.textContent = `WITAJ ${userName.toUpperCase()}! ${data.message}`;
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
        
        setTimeout(() => {
            resetVerification();
        }, 5000);
        
    } catch (error) {
        console.error('Błąd weryfikacji:', error);
        resultEl.textContent = 'Błąd podczas weryfikacji. Spróbuj ponownie.';
        resultEl.className = 'result-message error';
        verificationInProgress = false;
        verificationCompleted = true;
        captureSessionActive = false;
    }
}

function resetVerification() {
    capturedImage = null;
    capturedImages = [];
    validatedQrCode = null;
    lastQrCode = null;
    verificationCompleted = false;
    verificationInProgress = false;
    document.getElementById('qr-code').value = '';
    document.getElementById('result').textContent = '';
    document.getElementById('result').className = 'result-message';
    
    stopFaceVerification();
    document.getElementById('face-verify-section').style.display = 'none';
    document.getElementById('qr-scan-section').style.display = 'block';
    updateQRStatus('Gotowe do skanowania QR', 'info');
}

document.addEventListener('DOMContentLoaded', () => {
    const startQrScanBtn = document.getElementById('start-qr-scan-btn');
    const stopQrScanBtn = document.getElementById('stop-qr-scan-btn');
    
    if (startQrScanBtn) {
        startQrScanBtn.addEventListener('click', startQRScan);
    }
    if (stopQrScanBtn) {
        stopQrScanBtn.addEventListener('click', stopQRScan);
    }
    
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
                setTimeout(() => {
                    if (e.target.value.trim() === lastQrCode) {
                        validateQRCode(e.target.value.trim());
                    }
                }, 1000);
            }
        });
    }
    
    window.addEventListener('beforeunload', () => {
        stopQRScan();
        stopFaceVerification();
    });
});


