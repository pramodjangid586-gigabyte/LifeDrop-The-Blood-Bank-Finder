/**
 * BloodConnect Live Ingestion & Inventory Streamer (SSE)
 * Connects to /api/events/live and dynamically updates UI without page reloads.
 */

(function initLiveStream() {
    if (!window.EventSource) {
        console.warn("Server-Sent Events not supported in this browser.");
        return;
    }

    const evtSource = new EventSource('/api/events/live');

    evtSource.onopen = function() {
        console.log("Connected to BloodConnect Live Inventory Event Stream.");
        const indicator = document.getElementById('live-stream-indicator');
        if (indicator) {
            indicator.classList.remove('bg-gray-400');
            indicator.classList.add('bg-emerald-500', 'animate-pulse');
            indicator.title = "Live Automated Updates: Connected";
        }
    };

    evtSource.onmessage = function(e) {
        try {
            if (!e.data || e.data.startsWith(':')) return; // Ignore ping
            const event = JSON.parse(e.data);
            handleLiveEvent(event);
        } catch (err) {
            console.error("Error parsing live event:", err);
        }
    };

    evtSource.onerror = function() {
        console.warn("Live stream disconnected. Reconnecting in background...");
        const indicator = document.getElementById('live-stream-indicator');
        if (indicator) {
            indicator.classList.remove('bg-emerald-500', 'animate-pulse');
            indicator.classList.add('bg-amber-400');
            indicator.title = "Live Automated Updates: Reconnecting...";
        }
    };

    function handleLiveEvent(data) {
        console.log("Live Ingestion Event Received:", data);

        // 1. Toast banner
        const sign = data.quantity_change > 0 ? `+${data.quantity_change}` : `${data.quantity_change}`;
        const toastType = data.quantity_change > 0 ? 'success' : (data.quantity_change < 0 ? 'warning' : 'info');
        
        let msg = `<strong>${data.blood_bank_name || 'Blood Bank'}</strong>: `;
        if (data.event_type === 'BLOOD_RECEIVED') {
            msg += `<span class="text-emerald-300 font-bold">${sign} units</span> of ${data.blood_group} ${data.component} received! (Source: ${data.source_name})`;
        } else if (data.event_type === 'BLOOD_ISSUED') {
            msg += `<span class="text-amber-200 font-bold">${sign} units</span> of ${data.blood_group} ${data.component} issued! (Source: ${data.source_name})`;
        } else if (data.event_type === 'DATA_OUTDATED_WARNING') {
            msg += `<span class="text-rose-300 font-bold">Warning:</span> ${data.blood_group} ${data.component} stock flagged as DATA OUTDATED.`;
        } else {
            msg += `${data.event_type} (${sign} units)`;
        }

        if (typeof showToast === 'function') {
            showToast(msg, toastType);
        }

        // 2. Update search results table row if present
        const rowId = `stock-row-${data.blood_bank_id}-${data.blood_group}-${data.component}`;
        const row = document.getElementById(rowId);
        if (row) {
            const unitsEl = row.querySelector('.stock-units');
            const statusEl = row.querySelector('.stock-status');
            const timeEl = row.querySelector('.stock-time');
            const sourceEl = row.querySelector('.stock-source');

            if (unitsEl) unitsEl.textContent = data.resulting_units;
            if (timeEl) timeEl.textContent = "Just now";
            if (sourceEl && data.source_name) sourceEl.textContent = data.source_name;

            // Recalculate badge
            if (statusEl) {
                statusEl.className = 'px-2.5 py-1 text-xs font-semibold rounded-full border stock-status ';
                if (data.resulting_units >= 5) {
                    statusEl.classList.add('badge-available');
                    statusEl.textContent = 'AVAILABLE';
                } else if (data.resulting_units >= 1) {
                    statusEl.classList.add('badge-limited');
                    statusEl.textContent = 'LIMITED';
                } else {
                    statusEl.classList.add('badge-unavailable');
                    statusEl.textContent = 'NOT AVAILABLE';
                }
            }

            // Flash row animation
            row.classList.remove('flash-increase', 'flash-decrease');
            void row.offsetWidth; // Trigger reflow
            if (data.quantity_change > 0) {
                row.classList.add('flash-increase');
            } else if (data.quantity_change < 0) {
                row.classList.add('flash-decrease');
            }
        }

        // 3. Update Blood Bank Staff Dashboard live counts if on that page
        const staffUnitsEl = document.getElementById(`staff-units-${data.blood_group}-${data.component}`);
        if (staffUnitsEl) {
            staffUnitsEl.textContent = data.resulting_units;
            staffUnitsEl.classList.add(data.quantity_change > 0 ? 'text-emerald-600' : 'text-rose-600');
            setTimeout(() => staffUnitsEl.classList.remove('text-emerald-600', 'text-rose-600'), 2000);
        }

        // 4. Update Admin Audit Log if table exists
        const auditTbody = document.getElementById('admin-audit-tbody');
        if (auditTbody) {
            const tr = document.createElement('tr');
            tr.className = 'border-b hover:bg-slate-50 transition ' + (data.quantity_change > 0 ? 'bg-emerald-50/50' : 'bg-rose-50/50');
            tr.innerHTML = `
                <td class="p-3 font-mono text-xs text-slate-500">${data.event_id || 'evt-live'}</td>
                <td class="p-3 font-semibold text-slate-800">${data.blood_bank_name || 'Blood Bank'}</td>
                <td class="p-3 font-bold text-red-600">${data.blood_group} (${data.component})</td>
                <td class="p-3 font-mono font-bold ${data.quantity_change > 0 ? 'text-emerald-600' : 'text-rose-600'}">${sign}</td>
                <td class="p-3 font-semibold">${data.resulting_units}</td>
                <td class="p-3 text-xs">${data.source_name || 'Authorized Feed'}</td>
                <td class="p-3 text-xs text-slate-500">Just now</td>
            `;
            auditTbody.insertBefore(tr, auditTbody.firstChild);
        }
    }
})();
