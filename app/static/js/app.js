/**
 * BloodConnect Core Client Utilities
 */

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const bgColors = {
        success: 'bg-emerald-600 text-white',
        error: 'bg-rose-600 text-white',
        warning: 'bg-amber-500 text-white',
        info: 'bg-slate-800 text-white'
    };

    const icons = {
        success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        error: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>',
        info: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    };

    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl transition-all duration-300 transform translate-y-2 opacity-0 text-sm font-medium ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `
        <span>${icons[type] || icons.info}</span>
        <div class="flex-1">${message}</div>
        <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white">&times;</button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// Geolocation helper
function getUserCoordinates(onSuccess, onError) {
    if (!navigator.geolocation) {
        showToast("Geolocation is not supported by your browser. Using Central Delhi default.", "warning");
        if (onError) onError();
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            onSuccess({
                lat: position.coords.latitude,
                lng: position.coords.longitude
            });
        },
        (error) => {
            console.warn("Geolocation denied or unavailable:", error.message);
            showToast("Location access unavailable. Using Central Delhi coordinates.", "info");
            if (onError) onError();
        },
        { timeout: 8000, enableHighAccuracy: false }
    );
}

// Global quick simulation controllers (Callable from Simulator Modal & UI buttons)
async function triggerSimulateReceived(bankId = 1, group = 'O+', comp = 'RBC', units = 10) {
    try {
        const res = await fetch('/api/ingestion/simulate/received', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blood_bank_id: bankId, blood_group: group, component: comp, units: units })
        });
        const data = await res.json();
        showToast(`Demo: +${units} units of ${group} ${comp} received at ${data.event?.blood_bank_name || 'facility'}!`, 'success');
        return data;
    } catch (e) {
        showToast("Simulation error: " + e.message, "error");
    }
}

async function triggerSimulateIssued(bankId = 1, group = 'O+', comp = 'RBC', units = 3) {
    try {
        const res = await fetch('/api/ingestion/simulate/issued', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blood_bank_id: bankId, blood_group: group, component: comp, units: units })
        });
        const data = await res.json();
        showToast(`Demo: -${units} units of ${group} ${comp} issued to patient!`, 'warning');
        return data;
    } catch (e) {
        showToast("Simulation error: " + e.message, "error");
    }
}

async function triggerSimulateOutdated(bankId = 1, group = 'O+', comp = 'RBC') {
    try {
        const res = await fetch('/api/ingestion/simulate/outdated-warning', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blood_bank_id: bankId, blood_group: group, component: comp })
        });
        const data = await res.json();
        showToast("Demo: Stock backdated 26h. 'DATA OUTDATED' warning activated!", 'error');
        return data;
    } catch (e) {
        showToast("Simulation error: " + e.message, "error");
    }
}

// Logout helper
async function handleLogout() {
    try {
        const res = await fetch('/api/auth/logout', { method: 'POST' });
        const data = await res.json();
        window.location.href = data.redirect_url || '/login';
    } catch (e) {
        window.location.href = '/login';
    }
}
