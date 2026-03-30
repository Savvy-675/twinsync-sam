const isAndroid = window.location.origin.includes('capacitor://') || window.location.origin.includes('http://localhost');
// 🌐 Hosted Fix: Use relative /api if in browser, fallback for Android/Local!
const API_BASE = (window.location.origin.includes('localhost') && !window.Capacitor?.isNativePlatform()) 
    ? '/api' 
    : (window.location.origin.startsWith('http') ? '/api' : 'https://twinsync-sam.onrender.com/api');

const SOCKET_BASE = (window.location.origin.includes('localhost') && !window.Capacitor?.isNativePlatform()) 
    ? window.location.origin 
    : (window.location.origin.startsWith('http') ? window.location.origin : 'https://twinsync-sam.onrender.com');

// DOM Elements
const views = document.querySelectorAll('.view-section');
const navItems = document.querySelectorAll('.nav-item');
const fabAdd = document.getElementById('fab-add');
const fabChat = document.getElementById('fab-chat');
const loader = document.getElementById('loading');
const authOverlay = document.getElementById('auth-overlay');
const appContainer = document.getElementById('app-container');
const authForm = document.getElementById('auth-form');
const btnAuthSubmit = document.getElementById('btn-auth-submit');
const userAvatar = document.getElementById('user-avatar');
const chatOverlay = document.getElementById('chat-overlay');
const closeChatBtn = document.querySelector('.close-chat');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat');

let socket;
let charts = {};
let calendarDate = new Date();
let currentCalView = 'month'; // 'month' or 'week'
let showCompletedTasks = false;

// -------- CORE AUTHENTICATION --------

function getToken() { return localStorage.getItem('jwt_token'); }
function setToken(t) { localStorage.setItem('jwt_token', t); }
function logout() { localStorage.removeItem('jwt_token'); window.location.reload(); }

async function apiFetch(endpoint, options = {}, retryOnAuth = true) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = "Bearer " + token.trim();
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        if (response.status === 401 || response.status === 422) {
            if (retryOnAuth) {
                localStorage.removeItem('jwt_token');
                return apiFetch(endpoint, options, false);
            }
            return { success: false, error: 'Auth failed' };
        }
        if (!response.ok) return { success: false };
        return response.json();
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// -------- RELATIVE TIME PARSER --------

function parseRelativeTime(input) {
    if (!input || input.trim() === '') return null;
    const now = new Date();
    const lower = input.toLowerCase().trim();

    // Try exact patterns first
    if (lower === 'today') return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59);
    if (lower === 'tomorrow') return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 23, 59);
    if (lower === 'this week') return new Date(now.getFullYear(), now.getMonth(), now.getDate() + (7 - now.getDay()), 23, 59);
    if (lower === 'next week') return new Date(now.getFullYear(), now.getMonth(), now.getDate() + (14 - now.getDay()), 23, 59);

    // "in X days/hours"
    const inMatch = lower.match(/in (\d+) (day|days|hour|hours|week|weeks)/);
    if (inMatch) {
        const n = parseInt(inMatch[1]);
        const unit = inMatch[2];
        const d = new Date(now);
        if (unit.startsWith('day')) d.setDate(d.getDate() + n);
        else if (unit.startsWith('hour')) d.setHours(d.getHours() + n);
        else if (unit.startsWith('week')) d.setDate(d.getDate() + n * 7);
        return d;
    }

    // "next Monday/Tuesday..."
    const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const nextDay = lower.match(/(?:next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)/);
    if (nextDay) {
        const targetDay = days.indexOf(nextDay[1]);
        const d = new Date(now);
        let diff = targetDay - d.getDay();
        if (diff <= 0) diff += 7;
        if (lower.includes('next')) diff += diff === 0 ? 7 : 0;
        d.setDate(d.getDate() + diff);
        d.setHours(23, 59, 0);
        return d;
    }

    // Try native Date parse as fallback
    const nativeParsed = new Date(input);
    if (!isNaN(nativeParsed)) return nativeParsed;

    return null;
}

function formatRelativePreview(date) {
    if (!date) return '';
    const now = new Date();
    const diffMs = date - now;
    const diffDays = Math.ceil(diffMs / 86400000);
    if (diffDays < 0) return '⚠️ This date is in the past';
    if (diffDays === 0) return '🔴 Due today — Critical';
    if (diffDays === 1) return '🟠 Due tomorrow — High Priority';
    if (diffDays <= 3) return `🟠 Due in ${diffDays} days — High Priority`;
    if (diffDays <= 7) return `🟡 Due in ${diffDays} days — Medium Priority`;
    return `🟢 Due in ${diffDays} days — Low Priority`;
}

// Live deadline preview
const deadlineInput = document.getElementById('task-deadline');
const deadlinePreview = document.getElementById('deadline-preview');
if (deadlineInput) {
    deadlineInput.addEventListener('input', () => {
        const parsed = parseRelativeTime(deadlineInput.value);
        deadlinePreview.textContent = parsed
            ? `📅 ${parsed.toLocaleString()} — ${formatRelativePreview(parsed)}`
            : deadlineInput.value ? '❓ Could not parse date' : '';
    });
}

// -------- NAVIGATION --------

navItems.forEach(item => {
    item.addEventListener('click', () => {
        navItems.forEach(ni => ni.classList.remove('active'));
        item.classList.add('active');
        const target = item.getAttribute('data-target');
        views.forEach(v => v.classList.remove('active'));
        document.getElementById(target).classList.add('active');
        fabAdd.style.display = target === 'view-tasks' ? 'flex' : 'none';
        if (target === 'view-insights') renderCharts();
        if (target === 'view-calendar') renderCalendar();
    });
});

// -------- AUTH --------

let isRegistrationMode = false;
const authToggleBtn = document.getElementById('auth-toggle-btn');
const authToggleText = document.getElementById('auth-toggle-text');
const signupFields = document.getElementById('auth-signup-fields');

if (authToggleBtn) {
    authToggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        isRegistrationMode = !isRegistrationMode;
        
        if (isRegistrationMode) {
            authToggleText.textContent = "Already have an account?";
            authToggleBtn.textContent = "Sign In instead";
            btnAuthSubmit.textContent = "Create Cloud Profile";
            signupFields.style.display = 'block';
        } else {
            authToggleText.textContent = "New to TwinSync?";
            authToggleBtn.textContent = "Create Cloud Profile";
            btnAuthSubmit.textContent = "Sign In to Sync";
            signupFields.style.display = 'none';
        }
    });
}

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    
    btnAuthSubmit.innerHTML = isRegistrationMode ? '<i class="fa-solid fa-spinner fa-spin"></i> Establishing Identity...' : '<i class="fa-solid fa-spinner fa-spin"></i> Syncing Cloud...';
    btnAuthSubmit.disabled = true;
    
    try {
        const endpoint = isRegistrationMode ? '/auth/register' : '/auth/login';
        const payload = { email, password };
        
        if (isRegistrationMode) {
            payload.name = document.getElementById('auth-name').value || "New Explorer";
            payload.working_hours_start = document.getElementById('auth-ob-start').value || "09:00";
            payload.working_hours_end = document.getElementById('auth-ob-end').value || "17:00";
            payload.daily_screen_time_goal = parseInt(document.getElementById('auth-ob-limit')?.value) || 120;
        }

        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if (data.success) {
            setToken(data.data.access_token);
            toast(isRegistrationMode ? 'Identity Established' : 'Cloud Verified', data.message, 'success');
            authOverlay.style.display = 'none';
            appContainer.style.display = 'block';
            await fetchAppData();
            initializeRealtime();
        } else {
            toast('Error', data.message, 'danger');
        }
    } catch (err) {
        toast('Error', "Cloud rejected connection.", 'danger');
    } finally {
        btnAuthSubmit.innerHTML = isRegistrationMode ? "Create Cloud Profile" : "Sign In to Sync";
        btnAuthSubmit.disabled = false;
    }
});

// -------- DATA SYNC --------

async function fetchAppData() {
    loader.style.display = 'block';
    const [tasksRes, analyticsRes] = await Promise.all([
        apiFetch('/tasks'),
        apiFetch('/analytics')
    ]);
    window.appData = {
        tasks: tasksRes.success ? (tasksRes.data.tasks || tasksRes.data) : [],
        analytics: analyticsRes.success ? analyticsRes.data : {}
    };
    renderDashboard();
    renderTasksList();
    renderProfile();
    if (document.getElementById('view-calendar').classList.contains('active')) renderCalendar();
    loader.style.display = 'none';
    updateAIStatus(analyticsRes);
    // Ensure socket room is joined now that user data is available
    if (socket && socket._joinUserRoom) socket._joinUserRoom();
}

function updateAIStatus(res) {
    const statusEl = document.querySelector('.ai-status');
    if (!statusEl) return;
    
    // Check if both the request succeeded AND the AI keys are configured
    const aiActive = res.success && res.data && res.data.ai_health;
    
    if (aiActive) {
        statusEl.innerHTML = '<span class="pulse-dot"></span> AI Pipeline: <span style="color:var(--success)">Online</span>';
        statusEl.style.opacity = '1';
    } else {
        statusEl.innerHTML = '<span class="pulse-dot" style="background:var(--danger)"></span> AI Pipeline: <span style="color:var(--danger)">Offline / Missing Keys</span>';
        statusEl.title = "The server is connected, but GROQ_API_KEY or GEMINI_API_KEY is missing in your hosting environment.";
    }
}

function renderDashboard() {
    const u = window.appData.analytics.user || {};
    if (u.name) userAvatar.textContent = u.name.charAt(0).toUpperCase();
    const score = Math.round(u.productivity_score || 0);
    const scoreEl = document.getElementById('score-text');
    if (scoreEl) {
        scoreEl.textContent = score;
        document.getElementById('score-circle').style.setProperty('--score', score);
    }
    const delayEl = document.getElementById('delay-text');
    if (delayEl) delayEl.textContent = (u.delay_rate || 0).toFixed(1) + '%';
    const mlAccEl = document.getElementById('ml-acc-text');
    if (mlAccEl) mlAccEl.textContent = Math.round(u.ml_accuracy || 0) + '%';
    renderTopTasks();
    renderProductivityInsights();
}


async function saveEmailSettings() {
    const imap = document.getElementById('prof-imap').value;
    const user = document.getElementById('prof-email-user').value;
    const pass = document.getElementById('prof-email-pass').value;
    
    if (!user || !pass) {
        toast('Incomplete', 'Email and App Password are required.', 'warning');
        return;
    }

    const res = await apiFetch('/user/email-config', {
        method: 'POST',
        body: JSON.stringify({
            imap_server: imap,
            email_user: user,
            email_pass: pass
        })
    });

    if (res.success) {
        toast('Cloud Sync', 'Mail credentials linked to Twin.', 'success');
        fetchAppData();
    } else {
        toast('Error', res.message || 'Sync failed.', 'danger');
    }
}

function renderTopTasks() {
    const container = document.getElementById('top-tasks-container');
    if (!container) return;
    const tasks = window.appData?.tasks || [];
    const pending = tasks.filter(t => t.status === 'pending');
    const top3 = pending.slice(0, 3);

    if (top3.length === 0) {
        container.innerHTML = '<p class="text-muted">No pending tasks for today!</p>';
        return;
    }

    container.innerHTML = top3.map(t => {
        const pScore = t.smart_priority_score || 0;
        return `
        <div class="card" style="margin-bottom:8px;padding:12px;border-left:4px solid ${getPriorityColor(t.priority)};">
            <div style="display:flex;justify-content:space-between;">
                <strong>${t.title}</strong>
                <span style="font-size:0.75rem;font-weight:bold;color:var(--accent-secondary);">${Math.round(pScore)} Score</span>
            </div>
            <p class="text-muted" style="font-size:0.8rem;margin-top:4px;">Due: ${t.deadline ? new Date(t.deadline).toLocaleDateString() : 'No deadline'}</p>
        </div>`;
    }).join('');
}

function getPriorityColor(priority) {
    const map = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e' };
    return map[priority] || '#8b5cf6';
}

function renderTasksList(filter = 'all') {
    const list = document.getElementById('tasks-list');
    let tasks = window.appData.tasks || [];
    if (filter !== 'all') tasks = tasks.filter(t => t.priority === filter);

    list.innerHTML = tasks.map(t => {
        const deadline = t.deadline ? new Date(t.deadline) : null;
        const daysLeft = deadline ? Math.ceil((deadline - new Date()) / 86400000) : null;
        const urgency = daysLeft !== null && daysLeft <= 1 ? '🔴' : daysLeft <= 3 ? '🟠' : daysLeft <= 7 ? '🟡' : '🟢';
        const deadlineStr = deadline ? deadline.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'No deadline';

        const checkboxHtml = `<div style="display:flex;align-items:center;margin-right:12px;">
            <input type="checkbox" ${t.status === 'completed' ? 'checked' : ''} onchange="toggleTaskStatus(${t.id}, '${t.status}')" style="transform:scale(1.2);cursor:pointer;accent-color:var(--success);">
        </div>`;
        const deleteHtml = `
        <button onclick="deleteTask(${t.id})" style="background:none;border:none;color:var(--danger);font-size:1rem;cursor:pointer;margin-left:10px;" title="Delete Task">
            <i class="fa-solid fa-trash-can"></i>
        </button>`;

        return `
        <div class="card task-card" style="margin-bottom:12px;display:flex;align-items:center;border-left:4px solid ${t.status === 'completed' ? 'var(--success)' : getPriorityColor(t.priority)}; opacity:${t.status === 'completed' ? '0.6' : '1'};">
            ${checkboxHtml}
            <div style="flex:1; text-decoration: ${t.status === 'completed' ? 'line-through' : 'none'};">
                <strong>${t.title}</strong>
                <p class="text-muted" style="font-size:0.78rem;margin-top:2px;">${t.category} • ${(t.priority || '').toUpperCase()} ${urgency} • Due: ${deadlineStr}</p>
            </div>
            <div style="display:flex;align-items:center;">
                <div class="status-tag ${t.status === 'completed' ? 'status-success' : 'status-info'}">${t.status}</div>
                ${deleteHtml}
            </div>
        </div>`;
    }).join('') || '<p class="text-muted" style="text-align:center;padding:30px;">No tasks found.</p>';
}

async function toggleTaskStatus(taskId, currentStatus) {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    const res = await apiFetch(`/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
    });
    if (res.success) {
        showToast(`Task marked as ${newStatus}`, 'success');
        await fetchAppData();
    } else {
        showToast('Failed to update task status.', 'danger');
    }
}

async function deleteTask(taskId) {
    if (!confirm("Are you sure you want to delete this task?")) return;
    const res = await apiFetch(`/tasks/${taskId}`, { method: 'DELETE' });
    if (res.success) {
        showToast('Task deleted successfully.', 'success');
        await fetchAppData();
    } else {
        showToast('Failed to delete task.', 'danger');
    }
}

document.getElementById('task-filter').addEventListener('change', (e) => {
    renderTasksList(e.target.value);
});

function renderProfile() {
    const u = window.appData.analytics.user || {};
    const tasks = window.appData.tasks || [];

    // Hero card
    const el = (id) => document.getElementById(id);
    if (el('profile-personality')) el('profile-personality').textContent = u.personality_type || 'High-Efficiency Architect';
    if (el('profile-name')) el('profile-name').textContent = u.name || '';
    if (el('profile-email')) el('profile-email').textContent = u.email || '';

    // Stat grid
    // Preferences
    if (el('pref-type')) el('pref-type').textContent = u.user_type || 'Student';
    if (el('pref-hours')) el('pref-hours').textContent = (u.working_hours_start || '09:00') + ' – ' + (u.working_hours_end || '17:00');
    if (el('pref-focus')) el('pref-focus').textContent = u.preferred_work_time || 'Morning';
    if (el('pref-duration')) el('pref-duration').textContent = (u.avg_duration_mins || 30) + ' mins';
    if (el('pref-goal')) el('pref-goal').textContent = (u.daily_goal || 3) + ' tasks/day';

    // Task summary breakdown
    const total = tasks.length;
    const completed = tasks.filter(t => t.status === 'completed').length;
    const pending = tasks.filter(t => t.status === 'pending').length;
    const critical = tasks.filter(t => t.priority === 'critical' && t.status === 'pending').length;
    const summaryEl = el('profile-task-summary');
    if (summaryEl) {
        summaryEl.innerHTML = [
            { label: '📋 Total Tasks', val: total, color: 'var(--text-primary)' },
            { label: '⏳ Pending', val: pending, color: 'var(--accent-secondary)' },
            { label: '✅ Completed', val: completed, color: 'var(--success)' },
            { label: '🔴 Critical (pending)', val: critical, color: 'var(--danger)' },
            { label: '📈 Completion Rate', val: total > 0 ? Math.round((completed / total) * 100) + '%' : '0%', color: 'var(--accent-primary)' },
        ].map(row => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                <span class="text-muted" style="font-size:0.82rem;">${row.label}</span>
                <strong style="font-size:0.88rem;color:${row.color};">${row.val}</strong>
            </div>`).join('');
    }
}

// -------- CALENDAR --------

function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    const label = document.getElementById('cal-month-label');
    const tasks = window.appData?.tasks || [];
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth();

    if (currentCalView === 'month') {
        label.textContent = calendarDate.toLocaleString('default', { month: 'long', year: 'numeric' });
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Build task-by-date index
        const tasksByDate = {};
        tasks.forEach(t => {
            if (!t.deadline || (!showCompletedTasks && t.status === 'completed')) return;
            const d = new Date(t.deadline);
            if (d.getFullYear() === year && d.getMonth() === month) {
                const key = d.getDate();
                if (!tasksByDate[key]) tasksByDate[key] = [];
                tasksByDate[key].push(t);
            }
        });

        let html = '<div class="cal-week-header"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div><div class="cal-days">';
        for (let i = 0; i < firstDay; i++) html += '<div class="cal-day empty"></div>';
        const today = new Date();
        for (let d = 1; d <= daysInMonth; d++) {
            const isToday = today.getDate() === d && today.getMonth() === month && today.getFullYear() === year;
            const dayTasks = tasksByDate[d] || [];
            const chips = dayTasks.slice(0, 2).map(t =>
                `<div class="cal-chip" style="background:${t.status === 'completed' ? 'rgba(16,185,129,0.2)' : getPriorityColor(t.priority) + '22'};border-left:2px solid ${t.status === 'completed' ? 'var(--success)' : getPriorityColor(t.priority)};font-size:0.6rem;padding:1px 4px;border-radius:3px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">${t.title}</div>`
            ).join('');
            const more = dayTasks.length > 2 ? `<div style="font-size:0.6rem;color:var(--text-muted);">+${dayTasks.length - 2} more</div>` : '';
            html += `<div class="cal-day ${isToday ? 'cal-today' : ''} ${dayTasks.length ? 'has-tasks' : ''}" onclick="showDayTasks(${d})">
                <span class="cal-date">${d}</span>
                ${chips}${more}
            </div>`;
        }
        html += '</div>';
        grid.innerHTML = html;
        document.getElementById('cal-day-tasks').innerHTML = '';

    } else {
        // Week View
        const today = new Date();
        const startOfWeek = new Date(calendarDate);
        startOfWeek.setDate(calendarDate.getDate() - calendarDate.getDay());
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);

        label.textContent = `${startOfWeek.toLocaleString('default', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleString('default', { month: 'short', day: 'numeric', year: 'numeric' })}`;

        let html = '<div class="cal-week-grid"><div class="cal-week-header-cell">Time</div>';

        // Headers
        for (let i = 0; i < 7; i++) {
            const d = new Date(startOfWeek);
            d.setDate(d.getDate() + i);
            const isToday = today.getDate() === d.getDate() && today.getMonth() === d.getMonth() && today.getFullYear() === d.getFullYear();
            html += `<div class="cal-week-header-cell ${isToday ? 'cal-today' : ''}">${d.toLocaleString('default', { weekday: 'short' })} <br/> ${d.getDate()}</div>`;
        }

        // Time blocks (9 AM to 6 PM)
        const startHour = 8;
        const endHour = 18;

        for (let h = startHour; h <= endHour; h++) {
            html += `<div class="cal-week-time-col"><div class="cal-time-slot">${h > 12 ? h - 12 : h} ${h >= 12 ? 'PM' : 'AM'}</div></div>`;
            for (let i = 0; i < 7; i++) {
                const colDate = new Date(startOfWeek);
                colDate.setDate(colDate.getDate() + i);

                // Find tasks falling in this hour
                const cellTasks = tasks.filter(t => {
                    if (!t.deadline || (!showCompletedTasks && t.status === 'completed')) return false;
                    const target = new Date(t.deadline);
                    return target.getDate() === colDate.getDate() && target.getMonth() === colDate.getMonth() && target.getHours() === h;
                });

                let blockHtml = '';
                if (cellTasks.length > 0) {
                    const blockColor = getPriorityColor(cellTasks[0].priority);
                    blockHtml = `<div class="cal-block-task" style="background:${blockColor};">${cellTasks[0].title}</div>`;
                }
                html += `<div class="cal-week-cell" onclick="showDayTasks(${colDate.getDate()}, ${colDate.getMonth()})">${blockHtml}</div>`;
            }
        }
        html += '</div>';
        grid.innerHTML = html;
        document.getElementById('cal-day-tasks').innerHTML = '';
    }
}

function showDayTasks(day, presetMonth = null) {
    const tasks = window.appData?.tasks || [];
    const year = calendarDate.getFullYear();
    const month = presetMonth !== null ? presetMonth : calendarDate.getMonth();
    const dayTasks = tasks.filter(t => {
        if (!t.deadline || (!showCompletedTasks && t.status === 'completed')) return false;
        const d = new Date(t.deadline);
        return d.getDate() === day && d.getMonth() === month && d.getFullYear() === year;
    });
    const container = document.getElementById('cal-day-tasks');
    if (!dayTasks.length) { container.innerHTML = ''; return; }
    const date = new Date(year, month, day).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    container.innerHTML = `<h3 style="margin-bottom:10px;font-size:1rem;">${date}</h3>` +
        dayTasks.map(t => `
        <div class="card" style="margin-bottom:8px;padding:10px 14px;border-left:3px solid ${t.status === 'completed' ? 'var(--success)' : getPriorityColor(t.priority)};">
            <div style="display:flex;justify-content:space-between;">
                <strong>${t.title}</strong>
                <span class="status-badge ${t.status === 'completed' ? 'badge-completed' : 'badge-pending'}">${t.status}</span>
            </div>
            <p class="text-muted" style="font-size:0.78rem;margin-top:4px;">${t.category} • ${(t.priority || '').toUpperCase()}</p>
        </div>`).join('');
}

const viewMonthBtn = document.getElementById('cal-view-month');
const viewWeekBtn = document.getElementById('cal-view-week');
const toggleCompletedBtn = document.getElementById('cal-toggle-completed');

if (viewMonthBtn) {
    viewMonthBtn.addEventListener('click', () => { currentCalView = 'month'; viewMonthBtn.classList.add('active-view'); viewWeekBtn.classList.remove('active-view'); renderCalendar(); });
    viewWeekBtn.addEventListener('click', () => { currentCalView = 'week'; viewWeekBtn.classList.add('active-view'); viewMonthBtn.classList.remove('active-view'); renderCalendar(); });
}

if (toggleCompletedBtn) {
    toggleCompletedBtn.addEventListener('click', () => {
        showCompletedTasks = !showCompletedTasks;
        toggleCompletedBtn.classList.toggle('active-view');
        renderCalendar();
    });
}

document.getElementById('cal-prev').addEventListener('click', () => {
    if (currentCalView === 'month') calendarDate.setMonth(calendarDate.getMonth() - 1);
    else calendarDate.setDate(calendarDate.getDate() - 7);
    renderCalendar();
});
document.getElementById('cal-next').addEventListener('click', () => {
    if (currentCalView === 'month') calendarDate.setMonth(calendarDate.getMonth() + 1);
    else calendarDate.setDate(calendarDate.getDate() + 7);
    renderCalendar();
});

// -------- PLANNER / ONBOARDING --------

const btnGenDay = document.getElementById('btn-generate-day');
const onboardModal = document.getElementById('onboard-modal');
const onboardForm = document.getElementById('onboard-form');

if (btnGenDay) {
    btnGenDay.addEventListener('click', () => {
        // Show onboarding modal
        onboardModal.classList.add('active');
    });
}

document.querySelector('.close-onboard')?.addEventListener('click', () => {
    onboardModal.classList.remove('active');
});

if (onboardForm) {
    onboardForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const type = document.getElementById('ob-type').value;
        const start = document.getElementById('ob-start').value;
        const end = document.getElementById('ob-end').value;
        const focus = document.getElementById('ob-focus').value;

        const btn = document.getElementById('btn-onboard-submit');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        const res = await apiFetch('/profile/onboard', {
            method: 'POST',
            body: JSON.stringify({
                user_type: type, 
                working_hours_start: start, 
                working_hours_end: end, 
                preferred_work_time: focus,
                daily_screen_time_goal: parseInt(document.getElementById('ob-limit')?.value) || 120
            })
        });

        if (res.success) {
            onboardModal.classList.remove('active');
            showToast('Smart Profile configured! Generating Plan...', 'success');
            setTimeout(() => renderSmartSchedule(), 1000);
        } else {
            showToast('Failed to save preferences.', 'danger');
            btn.innerHTML = 'Save & Generate Plan';
        }
    });
}

function renderSmartSchedule() {
    const list = document.getElementById('planner-timeline');
    if (!list) return;

    // We already have tasks sorted by smart priority in appData
    // We will render the top 3 high priority tasks in a timeline view for the day.
    const tasks = (window.appData?.tasks || []).filter(t => t.status === 'pending').slice(0, 3);

    if (tasks.length === 0) {
        list.innerHTML = `<p class="text-muted" style="text-align:center;">You have no urgent tasks pending. Take a break!</p>`;
        return;
    }

    list.innerHTML = tasks.map((t, index) => {
        // Mocking timeline hour based on index and preferred time could be done here.
        const hour = 9 + (index * 2);
        const timeLabel = `${hour > 12 ? hour - 12 : hour} ${hour >= 12 ? 'PM' : 'AM'}`;
        return `
        <div class="timeline-item">
            <div class="time-slot">${timeLabel}</div>
            <div class="timeline-box" style="border-left-color:${getPriorityColor(t.priority)}">
                <h4>${t.title}</h4>
                <p class="text-muted" style="font-size:0.8rem;margin-top:4px;">Estimated ${t.estimated_duration} mins • Score: ${Math.round(t.smart_priority_score || 0)}</p>
            </div>
        </div>
        `;
    }).join('');
}

// -------- CHARTS --------

function renderCharts() {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;
    if (charts.trend) { charts.trend.destroy(); charts.trend = null; }

    const weekly = window.appData?.analytics?.weekly || [];
    const labels = weekly.length ? weekly.map(d => d.label) : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const data = weekly.length ? weekly.map(d => d.count) : [0, 0, 0, 0, 0, 0, 0];

    const tasks = window.appData?.tasks || [];
    const completedByDay = {};
    tasks.filter(t => t.status === 'completed' && t.deadline).forEach(t => {
        const day = new Date(t.deadline).toLocaleDateString('en-US', { weekday: 'short' });
        completedByDay[day] = (completedByDay[day] || 0) + 1;
    });
    const completedData = labels.map(l => completedByDay[l] || 0);

    if (charts.trend) charts.trend.destroy();
    charts.trend = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Pending Tasks',
                    data,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139,92,246,0.08)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#8b5cf6',
                    pointRadius: 4
                },
                {
                    label: 'Completed',
                    data: completedData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16,185,129,0.06)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#10b981',
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true, labels: { color: '#94a3b8', font: { size: 11 } } }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

// -------- TASK MODAL --------

fabAdd.addEventListener('click', () => {
    document.getElementById('task-modal').classList.add('active');
    document.getElementById('task-title').focus();
});
document.querySelector('.close-modal').addEventListener('click', () => {
    document.getElementById('task-modal').classList.remove('active');
});

document.getElementById('add-task-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('task-title').value.trim();
    const category = document.getElementById('task-category').value;
    const deadlineRaw = document.getElementById('task-deadline').value;
    const priority = document.getElementById('task-priority').value || null;

    const parsedDeadline = parseRelativeTime(deadlineRaw);
    const deadlineISO = parsedDeadline ? parsedDeadline.toISOString() : null;

    const res = await apiFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify({ title, category, deadline: deadlineISO, priority })
    });

    if (res.success) {
        showToast('Task added to queue ✓', 'success');
        document.getElementById('task-modal').classList.remove('active');
        document.getElementById('add-task-form').reset();
        deadlinePreview.textContent = '';
        await fetchAppData();
    } else {
        showToast('Failed to sync task', 'danger');
    }
});

// -------- AI ASSISTANT --------

fabChat.addEventListener('click', () => chatOverlay.classList.toggle('active'));
closeChatBtn.addEventListener('click', () => chatOverlay.classList.remove('active'));

// Allow Enter key to send
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatBtn.click(); }
});

sendChatBtn.addEventListener('click', async () => {
    const msg = chatInput.value.trim();
    if (!msg) return;
    appendMessage('user', msg);
    chatInput.value = '';

    // Show typing indicator
    const typingId = 'typing-' + Date.now();
    appendMessage('assistant', '⏳ *Thinking...*', typingId);

    try {
        const res = await apiFetch('/chat', {
            method: 'POST',
            body: JSON.stringify({ message: msg })
        });

        document.getElementById(typingId)?.remove();

        if (res.success) {
            appendMessage('assistant', res.data.response);
            // If a task was created, refresh the task list and show notification
            if (res.data.task_created) {
                showToast(`✅ Task added: "${res.data.task_title}"`, 'success');
                await fetchAppData();
            }
        } else {
            appendMessage('assistant', "I'm having trouble reaching the AI cloud. Please check your connection.");
        }
    } catch (e) {
        document.getElementById(typingId)?.remove();
        appendMessage('assistant', "Network Error: API Pipeline disconnected.");
    }
});

function appendMessage(role, text, id = null) {
    const div = document.createElement('div');
    div.className = `msg ${role}-msg`;
    if (id) div.id = id;
    div.innerHTML = marked.parse(text);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// -------- EMAIL SYNC --------

document.getElementById('btn-email-sync').addEventListener('click', async () => {
    const btn = document.getElementById('btn-email-sync');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
    btn.disabled = true;
    try {
        const res = await apiFetch('/email-sync', { method: 'POST' });
        if (res.success) {
            const count = res.data.count;
            showToast(count > 0 ? `📧 ${count} new task(s) synced from Gmail!` : '📧 No new task emails found.', 'success');
            if (count > 0) await fetchAppData();
        } else {
            showToast('Email sync failed. Check your credentials.', 'danger');
        }
    } catch (e) {
        showToast('Email sync error.', 'danger');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-envelope-circle-check"></i> Sync Email';
        btn.disabled = false;
    }
});

// -------- TOAST UTILITIES --------

function showToast(m, type = 'info') {
    const c = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast status-${type}`;
    t.textContent = m;
    c.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

document.addEventListener('DOMContentLoaded', () => {
    if (getToken()) {
        authOverlay.style.display = 'none';
        appContainer.style.display = 'block';
        initializeRealtime();
        fetchAppData();
    }
    initScreenTimeTracker();
    initFocusMode();
    initIdleTracker();
});

// -------- FOCUS MODE (POMODORO) --------

function initFocusMode() {
    const fabFocus = document.getElementById('fab-focus');
    const overlay = document.getElementById('focus-overlay');
    const display = document.getElementById('focus-timer-display');
    const startBtn = document.getElementById('focus-start-btn');
    const resetBtn = document.getElementById('focus-reset-btn');
    const closeBtn = document.getElementById('focus-close-btn');
    if (!fabFocus) return;

    let totalSeconds = 25 * 60;
    let remaining = totalSeconds;
    let timerInterval = null;
    let running = false;
    let sessionsCompleted = 0;

    function fmt(s) {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    }

    function tick() {
        remaining--;
        display.textContent = fmt(remaining);
        if (remaining <= 0) {
            clearInterval(timerInterval);
            running = false;
            sessionsCompleted++;
            startBtn.textContent = '▶ Start';
            showToast(`🍅 Focus session complete! (${sessionsCompleted} done)`, 'success');
            display.textContent = '00:00';
            // Brief break: 5 min
            setTimeout(() => {
                remaining = 5 * 60;
                display.textContent = fmt(remaining);
                showToast('☕ 5-minute break started!', 'info');
            }, 1500);
        }
    }

    fabFocus.addEventListener('click', () => {
        overlay.style.display = overlay.style.display === 'none' ? 'block' : 'none';
    });

    startBtn.addEventListener('click', () => {
        if (!running) {
            if (remaining <= 0) remaining = totalSeconds;
            timerInterval = setInterval(tick, 1000);
            running = true;
            startBtn.textContent = '⏸ Pause';
            showToast('🍅 Focus session started! Stay locked in.', 'success');
        } else {
            clearInterval(timerInterval);
            running = false;
            startBtn.textContent = '▶ Resume';
        }
    });

    resetBtn.addEventListener('click', () => {
        clearInterval(timerInterval);
        running = false;
        remaining = totalSeconds;
        display.textContent = fmt(remaining);
        startBtn.textContent = '▶ Start';
    });

    closeBtn.addEventListener('click', () => {
        overlay.style.display = 'none';
    });
}

// -------- IDLE TRACKER --------

function initIdleTracker() {
    const IDLE_LIMIT_MS = 20 * 60 * 1000; // 20 minutes
    let lastActive = Date.now();
    let nudgeSent = false;

    function resetIdle() {
        lastActive = Date.now();
        nudgeSent = false;
    }

    ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'].forEach(ev => {
        document.addEventListener(ev, resetIdle, { passive: true });
    });

    setInterval(() => {
        const idle = Date.now() - lastActive;
        if (idle >= IDLE_LIMIT_MS && !nudgeSent) {
            nudgeSent = true;
            const mins = Math.round(idle / 60000);
            showToast(`⏰ You've been inactive for ${mins} minutes — time to return to your task!`, 'danger');
            // Try browser notification too
            if (Notification && Notification.permission === 'granted') {
                new Notification('TwinSync Nudge', {
                    body: `You've been inactive for ${mins} minutes. Return to your most important task!`,
                    icon: 'https://cdn-icons-png.flaticon.com/512/4712/4712139.png'
                });
            }
        }
    }, 60 * 1000); // check every minute

    // Request notification permission on load
    if (Notification && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}
// -------- SCREEN TIME TRACKER (ANDROID NATIVE + WEB FALLBACK) --------
let activeSeconds = 0;
let lastNativeUsage = 0;

async function initScreenTimeTracker() {
    console.log("Initializing Screen Time Intelligence...");
    
    // 🟠 WEB TRACKER: Track active tab time
    setInterval(() => {
        if (document.visibilityState === 'visible') activeSeconds++;
    }, 1000);

    // 🔴 NATIVE TRACKER: Fetch Phone Usage (UsageStatsManager)
    setInterval(async () => {
        let currentTotalSeconds = 0;
        const isNative = window.Capacitor && window.Capacitor.isNativePlatform();

        if (isNative) {
            try {
                // UsageStatsManager provides total time in ms since start of day
                const { UsageStatsManager } = Capacitor.Plugins;
                if (UsageStatsManager) {
                    const stats = await UsageStatsManager.queryUsageStats({ 
                        startTime: new Date().setHours(0,0,0,0), 
                        endTime: Date.now() 
                    });
                    // Sum all app usage (this is what the user wants: "phone screen time")
                    currentTotalSeconds = Math.round(Object.values(stats || {}).reduce((s, a) => s + (a.totalTimeInForeground || 0), 0) / 1000);
                }
            } catch (e) {
                console.warn("Native UsageStats failed (Permission missing?). Falling back to tab tracking.", e);
            }
        }

        // Sync with backend: If native worked, send the absolute total. If not, send the increment.
        const payload = isNative && currentTotalSeconds > 0 
            ? { total_seconds: currentTotalSeconds, is_absolute: true } 
            : { active_seconds: activeSeconds, is_absolute: false };

        if (activeSeconds > 0 || currentTotalSeconds > 0) {
            const res = await apiFetch('/screentime', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            if (res.success) {
                if (!isNative) activeSeconds = 0; // Reset tab tracker on success
                updateUrgencyDisplay(res.data);
            }
        }
    }, 60000); // Sync every minute
}

function updateUrgencyDisplay(data) {
    const usageEl = document.getElementById('usage-time-display');
    if (usageEl) {
        const mins = Math.floor(data.active_usage / 60);
        usageEl.textContent = `${mins}m Active Today`;
    }
    
    // Update Dashboard Focus Goal Card
    updateFocusGoalCard(data.active_usage);
    
    // Check if workload vs remaining time is risky
    checkWorkloadUrgency();
}

function updateFocusGoalCard(activeSeconds) {
    const u = window.appData?.analytics?.user || {};
    const goalMins = u.daily_screen_time_goal || 120; // Default 2h
    const currentMins = Math.floor(activeSeconds / 60);
    const pct = Math.min(Math.round((currentMins / goalMins) * 100), 100);
    
    const bar = document.getElementById('focus-goal-bar');
    const currentTxt = document.getElementById('focus-current-text');
    const percentTxt = document.getElementById('focus-percent-text');
    const goalTxt = document.getElementById('focus-goal-text');
    
    if (bar) {
        bar.style.width = pct + '%';
        if (pct >= 100) {
            bar.style.background = 'linear-gradient(90deg, #ef4444, #991b1b)';
            bar.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.4)';
        } else if (pct >= 80) {
            bar.style.background = 'linear-gradient(90deg, #f59e0b, #ef4444)';
        }
    }
    if (currentTxt) currentTxt.textContent = `${currentMins}m spent`;
    if (percentTxt) percentTxt.textContent = pct + '%';
    if (goalTxt) goalTxt.textContent = `Goal: ${Math.floor(goalMins/60)}h ${goalMins % 60}m`;
    
    const limitTxt = document.getElementById('pref-limit');
    if (limitTxt) limitTxt.textContent = `${goalMins} mins`;
}

function checkWorkloadUrgency() {
    const u = window.appData?.analytics?.user || {};
    const tasks = window.appData?.tasks || [];
    const pending = tasks.filter(t => t.status === 'pending');
    const activeSecs = window.appData?.analytics?.usage?.active_usage || 0;
    const goalMins = u.daily_screen_time_goal || 120;
    const currentMins = Math.floor(activeSecs / 60);
    
    const banner = document.getElementById('urgency-banner');
    if (!banner) return;

    // 1. Goal Overload Warning
    if (currentMins >= goalMins) {
        banner.style.display = 'block';
        banner.classList.add('critical');
        banner.innerHTML = `🚨 <strong>Focus Goal Reached!</strong> Phone usage: ${Math.floor(currentMins/60)}h ${currentMins%60}m limit exceeded. Take a break!`;
        return;
    } else {
        banner.classList.remove('critical');
    }

    // 2. Workload Pressure Warning
    const totalEstMins = pending.reduce((sum, t) => sum + (t.estimated_duration || 30), 0);
    const now = new Date();
    const endStr = u.working_hours_end || "17:00";
    const [endH, endM] = endStr.split(':').map(Number);
    const endTime = new Date();
    endTime.setHours(endH, endM, 0);
    
    const minsRemaining = (endTime - now) / 60000;
    
    if (minsRemaining > 0 && totalEstMins > minsRemaining) {
        banner.style.display = 'block';
        banner.style.background = 'linear-gradient(90deg, var(--warning), var(--danger))';
        banner.innerHTML = `⚠️ <strong>High Pressure!</strong> ${Math.round(totalEstMins/60)}h of work remains with only ${Math.round(minsRemaining/60)}h in workday.`;
    } else {
        banner.style.display = 'none';
    }
}

// -------- PRODUCTIVITY INSIGHTS --------

function renderProductivityInsights() {
    const tasks = window.appData?.tasks || [];
    const today = new Date();
    const todayStr = today.toDateString();

    const plannedToday = tasks.filter(t => {
        if (!t.deadline) return false;
        return new Date(t.deadline).toDateString() === todayStr;
    });
    const completedToday = plannedToday.filter(t => t.status === 'completed');
    const pct = plannedToday.length > 0
        ? Math.round((completedToday.length / plannedToday.length) * 100) : 0;

    const atRisk = tasks.filter(t => {
        if (t.status !== 'pending' || !t.deadline) return false;
        const daysLeft = (new Date(t.deadline) - today) / 86400000;
        return daysLeft <= 2;
    });

    const insightEl = document.getElementById('productivity-insights');
    if (!insightEl) return;

    insightEl.innerHTML = `
    <div class="card" style="margin-bottom:10px;padding:14px;border-left:4px solid var(--accent-primary);">
        <p style="font-size:0.85rem;margin-bottom:6px;">📊 <strong>Today's Completion Rate:</strong></p>
        <div style="background:var(--bg-primary);border-radius:8px;height:8px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,var(--success),var(--accent-secondary));transition:width 0.5s;"></div>
        </div>
        <p style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;">✅ ${completedToday.length} of ${plannedToday.length} planned tasks completed (${pct}%)</p>
    </div>
    ${atRisk.length > 0 ? `
    <div class="card" style="padding:14px;border-left:4px solid var(--danger);">
        <p style="font-size:0.85rem;margin-bottom:6px;">⚠️ <strong>Tasks at Risk (due in ≤2 days):</strong></p>
        ${atRisk.slice(0, 3).map(t => `
            <p style="font-size:0.8rem;color:var(--danger);margin:4px 0;">• ${t.title}</p>
        `).join('')}
    </div>` : '<p class="text-muted" style="font-size:0.85rem;">🎉 No tasks at risk today!</p>'}
    `;
}


// -------- REALTIME SYNC --------

function initializeRealtime() {
    if (socket) socket.disconnect();
    
    const token = getToken();
    if (!token) return;

    socket = io(SOCKET_BASE, {
        auth: { token: token },
        // Start with polling (always works through Render's proxy),
        // then attempt WebSocket upgrade. Prevents the WS-closed-before-connected error.
        transports: ['polling', 'websocket'],
        reconnection: true,
        reconnectionDelay: 2000,
        reconnectionAttempts: 5,
        timeout: 10000,
    });

    function joinUserRoom() {
        const user = window.appData?.analytics?.user;
        if (user && user.id) {
            socket.emit('join', { user_id: user.id });
            console.log(`Joined room: user_${user.id}`);
            return true;
        }
        return false;
    }

    socket.on('connect', () => {
        console.log('Connected to TwinSync Cloud Socket');
        // If appData is already loaded (reconnect scenario), join immediately
        if (!joinUserRoom()) {
            // Data not ready yet; will be joined after fetchAppData resolves
            console.log('Room join deferred — waiting for appData to load.');
        }
    });

    socket.on('task_updated', (data) => {
        showToast(data.message, 'success');
        fetchAppData();
    });

    socket.on('analytics_refreshed', () => {
        fetchAppData();
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Cloud Socket');
    });

    // Expose joiner so fetchAppData can call it after data resolves
    socket._joinUserRoom = joinUserRoom;
}

// -------- ON PAGE LOAD --------

window.addEventListener('DOMContentLoaded', async () => {
    const token = getToken();
    if (token) {
        authOverlay.style.display = 'none';
        appContainer.style.display = 'block';
        // Init socket first so it's ready to receive events
        initializeRealtime();
        await fetchAppData();
        // Now that appData is loaded, ensure we've joined the user room
        if (socket && socket._joinUserRoom) socket._joinUserRoom();
    } else {
        authOverlay.style.display = 'flex';
        appContainer.style.display = 'none';
    }
});

// -------- UTILS --------

function toast(title, message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const color = type === 'success' ? '#10b981' : (type === 'danger' ? '#ef4444' : '#f59e0b');
    const toast = document.createElement('div');
    toast.className = 'card toast-anim';
    toast.style.cssText = `margin-bottom:10px;padding:12px;border-left:4px solid ${color};min-width:200px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.4);border-radius:8px;`;
    toast.innerHTML = `<strong>${title}</strong><p style="margin:4px 0 0;font-size:0.8rem;color:var(--text-muted);">${message}</p>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 500); }, 3000);
}
