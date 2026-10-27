/**
 * BloodConnect Interactive Map Visualizer (Leaflet.js)
 */

let bloodMap = null;
let markersLayer = null;
let radiusCircle = null;
let userMarker = null;

function initBloodMap(containerId, centerLat = 28.6139, centerLng = 77.2090, zoom = 12) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    if (bloodMap) {
        bloodMap.remove();
        bloodMap = null;
    }

    bloodMap = L.map(containerId, {
        center: [centerLat, centerLng],
        zoom: zoom,
        zoomControl: true
    });

    // Clean OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors | BloodConnect'
    }).addTo(bloodMap);

    markersLayer = L.layerGroup().addTo(bloodMap);
    return bloodMap;
}

function plotBloodBanksOnMap(bloodBanks, searchCenter = null, radiusKm = 25) {
    if (!bloodMap || !markersLayer) return;
    markersLayer.clearLayers();

    // 1. Plot user search center
    if (searchCenter && searchCenter.lat && searchCenter.lng) {
        const userIcon = L.divIcon({
            className: 'user-pin',
            html: `<div class="w-6 h-6 bg-blue-600 rounded-full border-4 border-white shadow-lg flex items-center justify-center pulse-emergency"><div class="w-2 h-2 bg-white rounded-full"></div></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        userMarker = L.marker([searchCenter.lat, searchCenter.lng], { icon: userIcon })
            .bindPopup(`<strong>Your Approximate Location</strong><br>${searchCenter.resolved_name || 'Search Hub'}`)
            .addTo(markersLayer);

        // Search radius circle
        if (radiusKm) {
            radiusCircle = L.circle([searchCenter.lat, searchCenter.lng], {
                color: '#ef4444',
                fillColor: '#fee2e2',
                fillOpacity: 0.15,
                weight: 1.5,
                radius: radiusKm * 1000 // meters
            }).addTo(markersLayer);
        }
    }

    // 2. Plot Blood Banks
    const bounds = [];
    if (searchCenter && searchCenter.lat) bounds.push([searchCenter.lat, searchCenter.lng]);

    bloodBanks.forEach(bank => {
        if (!bank.lat || !bank.lng) return;

        bounds.push([bank.lat, bank.lng]);

        // Determine pin color based on status
        let pinColor = '#10b981'; // Green
        let statusBadge = `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">AVAILABLE</span>`;

        if (bank.is_outdated) {
            pinColor = '#f97316'; // Orange
            statusBadge = `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-orange-100 text-orange-800 border border-orange-300">DATA OUTDATED</span>`;
        } else if (bank.units_available === 0 || bank.availability_status === 'NOT AVAILABLE') {
            pinColor = '#ef4444'; // Red
            statusBadge = `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-800 border border-rose-300">NOT AVAILABLE</span>`;
        } else if (bank.units_available < 5 || bank.availability_status === 'LIMITED') {
            pinColor = '#eab308'; // Yellow
            statusBadge = `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-amber-100 text-amber-800 border border-amber-300">LIMITED</span>`;
        }

        const markerHtml = `
            <div style="background-color: ${pinColor};" class="w-8 h-8 rounded-full border-2 border-white shadow-xl flex items-center justify-center text-white font-bold text-xs">
                ${bank.units_available !== undefined ? bank.units_available : '🩸'}
            </div>
        `;

        const icon = L.divIcon({
            className: 'custom-bank-pin',
            html: markerHtml,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });

        const popupContent = `
            <div class="p-2 custom-map-popup max-w-xs text-slate-800">
                <div class="flex items-start justify-between gap-2 mb-1">
                    <h4 class="font-bold text-sm text-slate-900 leading-tight">${bank.name}</h4>
                </div>
                <div class="mb-2">${statusBadge}</div>
                <p class="text-xs text-slate-600 mb-1">📍 ${bank.address}, ${bank.city}</p>
                <p class="text-xs text-slate-600 mb-1">📏 Distance: <strong>${bank.distance_km ? bank.distance_km.toFixed(1) + ' km' : 'Nearby'}</strong></p>
                <p class="text-xs text-slate-600 mb-2">⏱ Hours: ${bank.operating_hours || '24/7'}</p>
                ${bank.emergency_helpline ? `<p class="text-xs font-bold text-red-600 mb-2">🚨 Helpline: <a href="tel:${bank.emergency_helpline}" class="underline">${bank.emergency_helpline}</a></p>` : ''}
                
                <div class="pt-2 border-t flex items-center justify-between">
                    <a href="tel:${bank.phone}" class="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold inline-flex items-center gap-1">
                        📞 Call Bank
                    </a>
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${bank.lat},${bank.lng}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded-md font-semibold inline-flex items-center gap-1">
                        🧭 Get Directions
                    </a>
                </div>
            </div>
        `;

        L.marker([bank.lat, bank.lng], { icon: icon })
            .bindPopup(popupContent)
            .addTo(markersLayer);
    });

    if (bounds.length > 0) {
        bloodMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
}
