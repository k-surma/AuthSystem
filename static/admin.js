// Proste "logowanie" po stronie frontend z hasłem "admin"
const ADMIN_PASSWORD = 'admin';
let isLoggedIn = false;

// Nagłówki autoryzacji – brak backendowej autoryzacji, zwracamy puste
function getAuthHeaders() {
    return {};
}

function showLoginForm() {
    const loginSection = document.getElementById('login-section');
    const adminPanel = document.getElementById('admin-panel');
    const logoutBtn = document.getElementById('logout-btn');

    if (loginSection) loginSection.style.display = 'block';
    if (adminPanel) adminPanel.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'none';

    const passwordInput = document.getElementById('admin-password');
    const errorDiv = document.getElementById('login-error');
    if (passwordInput) passwordInput.value = '';
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
}

// Pokazanie panelu admina i załadowanie danych
function showAdminPanel() {
    const loginSection = document.getElementById('login-section');
    const adminPanel = document.getElementById('admin-panel');
    const logoutBtn = document.getElementById('logout-btn');

    if (loginSection) loginSection.style.display = 'none';
    if (adminPanel) adminPanel.style.display = 'grid';
    if (logoutBtn) logoutBtn.style.display = 'inline-block';

    // Załaduj dane
    loadUsers();
    loadBadges();
    loadLogs();
}

function logout() {
    isLoggedIn = false;
    showLoginForm();
}

// Ładowanie użytkowników
async function loadUsers() {
    try {
        const response = await fetch('/api/users', {
            headers: getAuthHeaders()
        });
        const users = await response.json();
        
        const usersList = document.getElementById('users-list');
        const userSelect = document.getElementById('user-select');
        const badgeUserSelect = document.getElementById('badge-user-select');
        
        // Wyczyść listy
        usersList.innerHTML = '';
        userSelect.innerHTML = '<option value="">Wybierz użytkownika</option>';
        badgeUserSelect.innerHTML = '<option value="">Wybierz użytkownika</option>';
        
        users.forEach(user => {
            // Dodaj do listy wyświetlanej
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-info">
                    <strong>${user.first_name} ${user.last_name}</strong>
                    <span class="badge ${user.is_active ? 'active' : 'inactive'}">
                        ${user.is_active ? 'Aktywny' : 'Nieaktywny'}
                    </span>
                    <br>
                    <small>ID: ${user.id} | Face ID: ${user.face_id}</small>
                </div>
            `;
            usersList.appendChild(card);
            
            // Dodaj do selectów
            const option1 = document.createElement('option');
            option1.value = user.id;
            option1.textContent = `${user.first_name} ${user.last_name} (${user.face_id})`;
            userSelect.appendChild(option1);
            
            const option2 = option1.cloneNode(true);
            badgeUserSelect.appendChild(option2);
        });
    } catch (error) {
        console.error('Błąd ładowania użytkowników:', error);
    }
}

// Dodawanie użytkownika
document.getElementById('user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userData = {
        first_name: document.getElementById('first-name').value,
        last_name: document.getElementById('last-name').value,
        // face_id nie jest już wymagane - zostanie wygenerowane automatycznie przez backend
        is_active: document.getElementById('is-active').checked
    };
    
    try {
        const response = await fetch('/api/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(userData)
        });
        if (response.ok) {
            alert('Użytkownik dodany pomyślnie!');
            document.getElementById('user-form').reset();
            loadUsers();
        } else {
            alert('Błąd podczas dodawania użytkownika');
        }
    } catch (error) {
        console.error('Błąd:', error);
        alert('Błąd podczas dodawania użytkownika');
    }
});

// Zmienne dla kamery w panelu admin
let adminStream = null;
let adminCapturedImage = null;

// Uruchomienie kamery w panelu admin
async function startAdminCamera() {
    try {
        adminStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'user',
                width: { ideal: 640 },
                height: { ideal: 480 }
            } 
        });
        const video = document.getElementById('admin-video');
        video.srcObject = adminStream;
        
        document.getElementById('start-camera-btn').style.display = 'none';
        document.getElementById('capture-photo-btn').style.display = 'inline-block';
        document.getElementById('stop-camera-btn').style.display = 'inline-block';
        document.getElementById('camera-status').textContent = 'Kamera gotowa. Kliknij "Zrób zdjęcie"';
        document.getElementById('camera-status').style.color = '#4CAF50';
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        document.getElementById('camera-status').textContent = 'Błąd: Nie można uzyskać dostępu do kamery';
        document.getElementById('camera-status').style.color = '#f44336';
    }
}

// Zatrzymanie kamery w panelu admin
function stopAdminCamera() {
    if (adminStream) {
        adminStream.getTracks().forEach(track => track.stop());
        adminStream = null;
    }
    const video = document.getElementById('admin-video');
    if (video.srcObject) {
        video.srcObject = null;
    }
    document.getElementById('start-camera-btn').style.display = 'inline-block';
    document.getElementById('capture-photo-btn').style.display = 'none';
    document.getElementById('stop-camera-btn').style.display = 'none';
    document.getElementById('camera-status').textContent = '';
    adminCapturedImage = null;
}

// Wykonanie zdjęcia w panelu admin
function captureAdminPhoto() {
    const video = document.getElementById('admin-video');
    const canvas = document.getElementById('admin-canvas');
    const context = canvas.getContext('2d');
    
    if (!video.videoWidth || !video.videoHeight) {
        alert('Kamera nie jest jeszcze gotowa. Poczekaj chwilę.');
        return;
    }
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
        adminCapturedImage = blob;
        document.getElementById('camera-status').textContent = 'Zdjęcie wykonane! Możesz teraz zarejestrować twarz.';
        document.getElementById('camera-status').style.color = '#4CAF50';
    }, 'image/jpeg', 0.95);
}

// Rejestracja twarzy
document.getElementById('face-register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('user-select').value;
    const imageSource = document.querySelector('input[name="image-source"]:checked').value;
    
    if (!userId) {
        alert('Proszę wybrać użytkownika');
        return;
    }
    
    let imageFile = null;
    
    if (imageSource === 'file') {
        imageFile = document.getElementById('face-image').files[0];
        if (!imageFile) {
            alert('Proszę wybrać zdjęcie z komputera');
            return;
        }
    } else {
        if (!adminCapturedImage) {
            alert('Proszę najpierw wykonać zdjęcie');
            return;
        }
        // Konwertuj blob na File
        imageFile = new File([adminCapturedImage], 'photo.jpg', { type: 'image/jpeg' });
    }
    
    const formData = new FormData();
    formData.append('image', imageFile);
    
    try {
        const response = await fetch(`/api/users/${userId}/register-face`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            alert('Twarz zarejestrowana pomyślnie!');
            document.getElementById('face-register-form').reset();
            // Reset kamery
            stopAdminCamera();
            // Reset wyboru źródła
            document.querySelector('input[name="image-source"][value="file"]').checked = true;
            document.getElementById('file-upload-section').style.display = 'block';
            document.getElementById('camera-section').style.display = 'none';
        } else {
            alert('Błąd: ' + data.message);
        }
    } catch (error) {
        console.error('Błąd:', error);
        alert('Błąd podczas rejestracji twarzy');
    }
});

// Ładowanie przepustek
async function loadBadges() {
    try {
        const response = await fetch('/api/badges', {
            headers: getAuthHeaders()
        });
        const badges = await response.json();
        
        const badgesList = document.getElementById('badges-list');
        badgesList.innerHTML = '';
        
        for (const badge of badges) {
            // Pobierz informacje o użytkowniku
            const userResponse = await fetch(`/api/users/${badge.user_id}`, {
                headers: getAuthHeaders()
            });
            const user = await userResponse.json();
            
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-info">
                    <strong>Kod QR: ${badge.qr_code}</strong>
                    <br>
                    <small>Użytkownik: ${user.first_name} ${user.last_name}</small>
                    <br>
                    <small>Wygasa: ${badge.valid_until}</small>
                </div>
                <button onclick="generateQR(${badge.id})">Pobierz QR</button>
            `;
            badgesList.appendChild(card);
        }
    } catch (error) {
        console.error('Błąd ładowania przepustek:', error);
    }
}

// Generowanie QR
async function generateQR(badgeId) {
    try {
        const response = await fetch(`/api/badges/${badgeId}/qr`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        
        // Otwórz QR w nowym oknie
        const newWindow = window.open();
        newWindow.document.write(`
            <html>
                <head><title>Kod QR</title></head>
                <body style="text-align: center; padding: 50px;">
                    <h2>Kod QR: ${data.qr_code}</h2>
                    <img src="data:image/png;base64,${data.qr_image}" alt="QR Code" style="max-width: 500px;">
                    <p>Zeskanuj ten kod lub wprowadź ręcznie: <strong>${data.qr_code}</strong></p>
                </body>
            </html>
        `);
    } catch (error) {
        console.error('Błąd generowania QR:', error);
        alert('Błąd podczas generowania kodu QR');
    }
}

// Dodawanie przepustki
document.getElementById('badge-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const qrCode = document.getElementById('qr-code-input').value.trim();
    const userId = document.getElementById('badge-user-select').value;
    const validUntil = document.getElementById('valid-until').value;
    
    // Jeśli kod QR nie został podany, wygeneruj losowy
    const finalQrCode = qrCode || `QR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const badgeData = {
        qr_code: finalQrCode,
        valid_until: validUntil,
        user_id: parseInt(userId)
    };
    
    try {
        const response = await fetch('/api/badges', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(badgeData)
        });
        if (response.ok) {
            alert('Przepustka dodana pomyślnie!');
            document.getElementById('badge-form').reset();
            loadBadges();
        } else {
            alert('Błąd podczas dodawania przepustki');
        }
    } catch (error) {
        console.error('Błąd:', error);
        alert('Błąd podczas dodawania przepustki');
    }
});

// Ładowanie logów
async function loadLogs() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    let url = '/api/logs?limit=100';
    if (startDate) url += `&start_date=${startDate}T00:00:00`;
    if (endDate) url += `&end_date=${endDate}T23:59:59`;
    
    try {
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        const logs = await response.json();
        
        const logsList = document.getElementById('logs-list');
        logsList.innerHTML = '';
        
        if (logs.length === 0) {
            logsList.innerHTML = '<p>Brak logów w wybranym okresie</p>';
            return;
        }
        
        logs.forEach(log => {
            const timestamp = new Date(log.timestamp).toLocaleString('pl-PL');
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-info">
                    <strong>${timestamp}</strong>
                    <span class="badge ${log.result.toLowerCase()}">${log.result}</span>
                    <br>
                    <small>User ID: ${log.user_id || '-'} | Badge ID: ${log.badge_id || '-'}</small>
                    <br>
                    <small>Match Score: ${log.match_score !== null && log.match_score !== undefined ? (log.match_score * 100).toFixed(1) + '%' : '-'}</small>
                </div>
            `;
            logsList.appendChild(card);
        });
    } catch (error) {
        console.error('Błąd ładowania logów:', error);
    }
}

// Filtrowanie logów
document.getElementById('filter-logs-btn').addEventListener('click', loadLogs);

// Generowanie raportu
document.getElementById('generate-report-btn').addEventListener('click', async () => {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    let url = '/api/reports/generate';
    if (startDate) url += `?start_date=${startDate}T00:00:00`;
    if (endDate) url += `&end_date=${endDate}T23:59:59`;
    
    try {
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `raport_${startDate || 'all'}_${endDate || 'all'}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            alert('Raport wygenerowany pomyślnie!');
        } else {
            alert('Błąd podczas generowania raportu');
        }
    } catch (error) {
        console.error('Błąd:', error);
        alert('Błąd podczas generowania raportu');
    }
});

// Inicjalizacja przy załadowaniu strony
document.addEventListener('DOMContentLoaded', async () => {
    // Najpierw pokaż formularz logowania
    showLoginForm();
    
    // Ustaw domyślne daty (ostatnie 30 dni)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];

    // Obsługa formularza logowania (proste sprawdzenie hasła po stronie klienta)
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const password = document.getElementById('admin-password').value;
            const errorDiv = document.getElementById('login-error');

            if (password === ADMIN_PASSWORD) {
                isLoggedIn = true;
                if (errorDiv) {
                    errorDiv.style.display = 'none';
                    errorDiv.textContent = '';
                }
                showAdminPanel();
            } else {
                if (errorDiv) {
                    errorDiv.textContent = 'Nieprawidłowe hasło';
                    errorDiv.style.display = 'block';
                } else {
                    alert('Nieprawidłowe hasło');
                }
            }
        });
    }

    // Obsługa wylogowania
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    // Przełączanie między wyborem pliku a kamerą
    document.querySelectorAll('input[name="image-source"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const fileSection = document.getElementById('file-upload-section');
            const cameraSection = document.getElementById('camera-section');
            
            if (e.target.value === 'file') {
                fileSection.style.display = 'block';
                cameraSection.style.display = 'none';
                // Zatrzymaj kamerę jeśli była uruchomiona
                stopAdminCamera();
                adminCapturedImage = null;
            } else {
                fileSection.style.display = 'none';
                cameraSection.style.display = 'block';
                // Wyczyść wybór pliku
                document.getElementById('face-image').value = '';
            }
        });
    });
    
    // Event listeners dla kamery
    const startCameraBtn = document.getElementById('start-camera-btn');
    const stopCameraBtn = document.getElementById('stop-camera-btn');
    const capturePhotoBtn = document.getElementById('capture-photo-btn');
    
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startAdminCamera);
    }
    if (stopCameraBtn) {
        stopCameraBtn.addEventListener('click', stopAdminCamera);
    }
    if (capturePhotoBtn) {
        capturePhotoBtn.addEventListener('click', captureAdminPhoto);
    }
});

// Cleanup kamery przy zamknięciu strony
window.addEventListener('beforeunload', () => {
    stopAdminCamera();
});





