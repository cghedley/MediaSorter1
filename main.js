// Media Sorter Pro - Main JavaScript
console.log("Media Sorter Pro loading...");

let isMonitoring = false;
let isConnected = false;
let aiEnabled = true;
let elements = {};

document.addEventListener('DOMContentLoaded', function() {
    initialize();
});

function initialize() {
    cacheElements();
    setupEventListeners();
    connectToBackend();
    setTimeout(showApp, 500);
}

function cacheElements() {
    elements = {
        app: document.getElementById('app'),
        loadingScreen: document.getElementById('loading-screen'),
        connectionStatus: document.getElementById('connection-status'),
        startBtn: document.getElementById('start-btn'),
        statusDot: document.getElementById('status-dot'),
        statusText: document.getElementById('status-text'),
        toggleAI: document.getElementById('toggle-ai'),
        logContainer: document.getElementById('log-container'),
        toastContainer: document.getElementById('toast-container'),
        ffmpegWarning: document.getElementById('ffmpeg-warning'), // FFmpeg Warning
        
        // Stats
        statTv: document.getElementById('stat-tv'),
        statMovies: document.getElementById('stat-movies'),
        statMusic: document.getElementById('stat-music'),
        statOther: document.getElementById('stat-other'),
        
        // Config inputs
        cfgMonitor: document.getElementById('cfg-monitor'),
        cfgTv: document.getElementById('cfg-tv'),
        cfgMovie: document.getElementById('cfg-movie'),
        cfgMusic: document.getElementById('cfg-music'),
        cfgOther: document.getElementById('cfg-other'),
        cfgApiKey: document.getElementById('cfg-api-key'),
        cfgAcoustidKey: document.getElementById('cfg-acoustid-key'),
        
        // System info
        sysMonitoringStatus: document.getElementById('sys-monitoring-status'),
        sysMissingLibs: document.getElementById('sys-missing-libs')
    };
}

function setupEventListeners() {
    if (elements.startBtn) {
        elements.startBtn.addEventListener('click', toggleMonitoring);
    }
    document.querySelectorAll('.input-field').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') saveConfig();
        });
    });
}

function connectToBackend() {
    console.log("Connecting to Python backend...");
    
    if (typeof eel === 'undefined') {
        updateConnectionStatus(false);
        showToast("Backend not connected", "error");
        return;
    }
    
    setTimeout(async () => {
        try {
            const test = await eel.test_connection()();
            updateConnectionStatus(true);
            
            const data = await eel.get_initial_data()();
            
            populateConfig(data.config || {});
            updateStats(data.stats || { tv: 0, movies: 0, music: 0, other: 0 });
            setMonitoringState(data.is_monitoring || false);
            
            if (elements.sysMissingLibs && data.missing_libs) {
                elements.sysMissingLibs.textContent = data.missing_libs.length;
            }

            // CHECK FFMPEG STATUS
            if (data.ffmpeg_installed === false && elements.ffmpegWarning) {
                elements.ffmpegWarning.classList.remove('hidden');
                addLog("FFmpeg not found - music fingerprinting disabled", "warning");
            } else if (elements.ffmpegWarning) {
                elements.ffmpegWarning.classList.add('hidden');
            }
            
            showToast("Connected to backend", "success");
            addLog("System initialized", "success");
            
        } catch (error) {
            console.error(error);
            updateConnectionStatus(false);
            showToast("Backend connection failed", "error");
        }
    }, 1000);
}

function updateConnectionStatus(connected) {
    isConnected = connected;
    const statusDot = elements.connectionStatus?.querySelector('.status-dot');
    const statusText = elements.connectionStatus?.querySelector('.status-text');
    
    if (connected) {
        if (statusDot) statusDot.style.backgroundColor = '#10b981';
        if (statusText) {
            statusText.textContent = 'Connected';
            statusText.style.color = '#10b981';
        }
    } else {
        if (statusDot) statusDot.style.backgroundColor = '#ef4444';
        if (statusText) {
            statusText.textContent = 'Disconnected';
            statusText.style.color = '#ef4444';
        }
    }
}

function showApp() {
    elements.loadingScreen.style.display = 'none';
    elements.app.classList.remove('hidden');
}

function populateConfig(config) {
    if (!config) return;
    
    if (elements.cfgMonitor) elements.cfgMonitor.value = config.monitor || '';
    if (elements.cfgTv) elements.cfgTv.value = config.tv || '';
    if (elements.cfgMovie) elements.cfgMovie.value = config.movie || '';
    if (elements.cfgMusic) elements.cfgMusic.value = config.music || '';
    if (elements.cfgOther) elements.cfgOther.value = config.other || '';
    if (elements.cfgApiKey) elements.cfgApiKey.value = config.api_key || '';
    if (elements.cfgAcoustidKey) elements.cfgAcoustidKey.value = config.acoustid_key || '';
    
    if (elements.toggleAI) {
        aiEnabled = config.use_ai_correction !== false;
        elements.toggleAI.classList.toggle('active', aiEnabled);
    }
}

function updateStats(stats) {
    if (!stats) return;
    if (elements.statTv) animateNumber(elements.statTv, stats.tv || 0);
    if (elements.statMovies) animateNumber(elements.statMovies, stats.movies || 0);
    if (elements.statMusic) animateNumber(elements.statMusic, stats.music || 0);
    if (elements.statOther) animateNumber(elements.statOther, stats.other || 0);
}

function animateNumber(element, newValue) {
    const current = parseInt(element.textContent) || 0;
    if (current === newValue) return;
    let currentValue = current;
    const increment = newValue > current ? 1 : -1;
    const interval = setInterval(() => {
        currentValue += increment;
        element.textContent = currentValue;
        if (currentValue === newValue) {
            clearInterval(interval);
        }
    }, 20);
}

function setMonitoringState(monitoring) {
    isMonitoring = monitoring;
    if (!elements.startBtn) return;
    
    if (monitoring) {
        elements.startBtn.textContent = "Stop Monitoring";
        elements.startBtn.classList.add('monitoring');
        if (elements.statusDot) elements.statusDot.className = 'status-dot active';
        if (elements.statusText) elements.statusText.textContent = 'Active';
        if (elements.sysMonitoringStatus) {
            elements.sysMonitoringStatus.textContent = 'Active';
            elements.sysMonitoringStatus.className = 'info-value status-badge active';
        }
    } else {
        elements.startBtn.textContent = "Start Monitoring";
        elements.startBtn.classList.remove('monitoring');
        if (elements.statusDot) elements.statusDot.className = 'status-dot idle';
        if (elements.statusText) elements.statusText.textContent = 'Idle';
        if (elements.sysMonitoringStatus) {
            elements.sysMonitoringStatus.textContent = 'Stopped';
            elements.sysMonitoringStatus.className = 'info-value status-badge stopped';
        }
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(tabId));
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabId}`);
    });
}

function toggleAI() {
    if (!elements.toggleAI) return;
    aiEnabled = !aiEnabled;
    elements.toggleAI.classList.toggle('active', aiEnabled);
    showToast(`AI Correction ${aiEnabled ? 'enabled' : 'disabled'}`, "info");
}

async function browseFolder(key) {
    if (!isConnected) return showToast("Not connected to backend", "error");
    try {
        const path = await eel.select_folder()();
        const input = elements[`cfg${key.charAt(0).toUpperCase() + key.slice(1)}`];
        if (path && input) {
            input.value = path;
            showToast(`Selected: ${path}`, "success");
        }
    } catch (error) { showToast("Failed to select folder", "error"); }
}

async function saveConfig() {
    if (!isConnected) return showToast("Not connected to backend", "error");
    const saveBtn = document.querySelector('button[onclick="saveConfig()"]');
    if (saveBtn) { saveBtn.textContent = "Saving..."; saveBtn.disabled = true; }
    
    try {
        const config = {
            monitor: elements.cfgMonitor?.value || '',
            tv: elements.cfgTv?.value || '',
            movie: elements.cfgMovie?.value || '',
            music: elements.cfgMusic?.value || '',
            other: elements.cfgOther?.value || '',
            api_key: elements.cfgApiKey?.value || '',
            acoustid_key: elements.cfgAcoustidKey?.value || '',
            use_ai_correction: aiEnabled
        };
        const result = await eel.save_config_from_js(config)();
        if (result.success) {
            showToast("Configuration saved", "success");
            addLog("Configuration saved", "success")
        } else { showToast("Save failed: " + result.message, "error"); }
    } catch (error) { showToast("Save failed", "error"); } 
    finally {
        if (saveBtn) { saveBtn.textContent = "Save Configuration"; saveBtn.disabled = false; }
    }
}

async function toggleMonitoring() {
    if (!isConnected) return showToast("Not connected to backend", "error");
    const btn = elements.startBtn;
    if (btn) btn.disabled = true;
    
    try {
        if (isMonitoring) {
            const result = await eel.stop_monitoring()();
            if (result.success) {
                setMonitoringState(false);
                showToast("Monitoring stopped", "warning");
                addLog("Monitoring stopped", "warning");
            }
        } else {
            await saveConfig();
            const result = await eel.start_monitoring()();
            if (result.success) {
                setMonitoringState(true);
                showToast("Monitoring started", "success");
                addLog("Monitoring started", "success");
            } else { showToast("Start failed: " + result.error, "error"); }
        }
    } catch (error) { showToast("Operation failed: " + error.message, "error"); } 
    finally { if (btn) btn.disabled = false; }
}

async function runMassImport() {
    if (!isConnected) return showToast("Not connected to backend", "error");
    try {
        const result = await eel.run_mass_import()();
        if (result.success) {
            showToast("Mass import started", "info");
            addLog("Mass import started", "info");
        } else { showToast("Import failed: " + result.message, "error"); }
    } catch (error) { showToast("Import failed", "error"); }
}

async function testParser() {
    const filename = document.getElementById('test-filename')?.value;
    if (!filename) return showToast("Enter a filename", "warning");
    if (!isConnected) return showToast("Not connected to backend", "error");
    
    try {
        const result = await eel.test_parser(filename)();
        if (result.success) {
            const output = document.getElementById('parser-output');
            const resultsDiv = document.getElementById('parser-results');
            if (output && resultsDiv) {
                output.textContent = JSON.stringify(result.result, null, 2);
                resultsDiv.classList.remove('hidden');
                showToast("Parser test completed", "success");
            }
        } else { showToast("Parser error: " + result.error, "error"); }
    } catch (error) { showToast("Parser test failed", "error"); }
}

function copyResults() {
    const output = document.getElementById('parser-output');
    if (output && output.textContent) {
        navigator.clipboard.writeText(output.textContent)
            .then(() => showToast("Results copied", "success"))
            .catch(() => showToast("Copy failed", "error"));
    }
}

function resetConfig() {
    if (confirm("Reset all settings to defaults?")) {
        populateConfig({
            monitor: '', tv: '', movie: '', music: '', other: '',
            api_key: '', acoustid_key: '', use_ai_correction: true
        });
        showToast("Settings reset", "info");
        addLog("Settings reset", "info");
    }
}

function clearLogs() {
    if (elements.logContainer) {
        elements.logContainer.innerHTML = `
            <div class="empty-log">
                <div>📝</div>
                <h4>Logs cleared</h4>
                <p>Activity logs will appear here</p>
            </div>`;
        showToast("Logs cleared", "info");
        addLog("Logs cleared", "info");
    }
}

function addLog(message, type = 'info') {
    if (!elements.logContainer) return;
    const empty = elements.logContainer.querySelector('.empty-log');
    if (empty) elements.logContainer.innerHTML = '';
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${time}]</span><span class="log-message">${message}</span>`;
    elements.logContainer.prepend(entry);
    
    const entries = elements.logContainer.querySelectorAll('.log-entry');
    if (entries.length > 50) entries[50].remove();
}

function showToast(message, type = 'info') {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-message">${message}</span>`;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== PYTHON CALLBACKS =====
eel.expose(js_add_log);
function js_add_log(message, type = "info") { addLog(message, type); }

eel.expose(js_update_stats);
function js_update_stats(tv, movies, music, other) { updateStats({ tv, movies, music, other }); }

eel.expose(js_show_toast);
function js_show_toast(message, type = "info") { showToast(message, type); }

// ===== GLOBAL EXPORTS =====
window.switchTab = switchTab;
window.toggleAI = toggleAI;
window.browseFolder = browseFolder;
window.saveConfig = saveConfig;
window.toggleMonitoring = toggleMonitoring;
window.runMassImport = runMassImport;
window.testParser = testParser;
window.copyResults = copyResults;
window.resetConfig = resetConfig;
window.clearLogs = clearLogs;