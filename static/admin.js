// Ładowanie użytkowników
async function loadUsers() {
    try {
        const response = await fetch('/api/users');
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
        face_id: document.getElementById('face-id').value,
        is_active: document.getElementById('is-active').checked
    };
    
    try {
        const response = await fetch('/api/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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

// Rejestracja twarzy
document.getElementById('face-register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('user-select').value;
    const imageFile = document.getElementById('face-image').files[0];
    
    if (!userId || !imageFile) {
        alert('Proszę wybrać użytkownika i zdjęcie');
        return;
    }
    
    const formData = new FormData();
    formData.append('image', imageFile);
    
    try {
        const response = await fetch(`/api/users/${userId}/register-face`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Twarz zarejestrowana pomyślnie!');
            document.getElementById('face-register-form').reset();
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
        const response = await fetch('/api/badges');
        const badges = await response.json();
        
        const badgesList = document.getElementById('badges-list');
        badgesList.innerHTML = '';
        
        for (const badge of badges) {
            // Pobierz informacje o użytkowniku
            const userResponse = await fetch(`/api/users/${badge.user_id}`);
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
        const response = await fetch(`/api/badges/${badgeId}/qr`);
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
                'Content-Type': 'application/json'
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
        const response = await fetch(url);
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
                    <small>Match Score: ${log.match_score ? (log.match_score * 100).toFixed(1) + '%' : '-'}</small>
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
        const response = await fetch(url);
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
document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
    loadBadges();
    loadLogs();
    
    // Ustaw domyślne daty (ostatnie 30 dni)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];
});


