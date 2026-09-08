// State variables
let currentChartScope = 'today';
let categoryChartInstance = null;
let currentDigestText = '';
let currentSwitchTxId = null;
let currentEditingTxId = null;
let currentEditingCategory = null;
let loadedTransactionsMap = new Map();
const GENERIC_MERCHANTS_SET = new Set(['餐飲', '餐飲消費', '一般特店', '特約商店', '特店', '一般消費', '國泰特店消費', '日常花費', '其他']);

const CATEGORY_COLORS = {
  '飲食 (自己吃)': '#f97316',
  '飲食 (和女友吃)': '#f43f5e',
  '飲食 (和家人吃)': '#e11d48',
  '飲食 (其他)': '#fb923c',
  '飲食': '#f97316',
  '交通': '#0ea5e9',
  '購物': '#ec4899',
  '娛樂': '#8b5cf6',
  '居家帳單': '#10b981',
  '醫療保健': '#ef4444',
  '學習教育': '#eab308',
  '其他': '#64748b'
};

const CATEGORY_ICONS = {
  '飲食 (自己吃)': '🍽️',
  '飲食 (和女友吃)': '👩‍❤️‍👨',
  '飲食 (和家人吃)': '👨‍👩‍👧',
  '飲食 (其他)': '🍲',
  '飲食': '🍽️',
  '交通': '🚗',
  '購物': '🛍️',
  '娛樂': '🎬',
  '居家帳單': '🏠',
  '醫療保健': '💊',
  '學習教育': '📚',
  '其他': '📦'
};

document.addEventListener('DOMContentLoaded', () => {
  // Set default date for form
  const todayStr = new Date().toISOString().split('T')[0];
  document.getElementById('formDate').value = todayStr;
  document.getElementById('statTodayDate').innerText = todayStr;

  // Load initial data
  refreshAllData();
});

function refreshAllData() {
  loadTodayStats();
  loadMonthStats();
  loadTransactions();
  loadBudgets();
  loadRules();
}

function insertCompanionTag(tag) {
  const textarea = document.getElementById('naturalInput');
  const clean = textarea.value.replace(/^(🍽️ 自己吃 |👩‍❤️‍👨 和女友吃 |👨‍👩‍👧 和家人吃 |自己吃 |和女友吃 |和家人吃 )/, '');
  textarea.value = tag + clean;
  textarea.focus();
}

// --- Toast Notifications ---
function showToast(message, isError = false) {
  const toast = document.getElementById('toast');
  const msgEl = document.getElementById('toastMsg');
  const iconEl = document.getElementById('toastIcon');

  msgEl.innerText = message;
  if (isError) {
    iconEl.className = 'ph ph-warning-circle text-rose-400 text-xl';
  } else {
    iconEl.className = 'ph ph-check-circle text-emerald-400 text-xl';
  }

  toast.classList.remove('hidden');
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 3500);
}

// --- Tab Switching ---
function switchInputTab(tab) {
  const tabNat = document.getElementById('tabNatural');
  const tabFrm = document.getElementById('tabForm');
  const paneNat = document.getElementById('paneNatural');
  const paneFrm = document.getElementById('paneForm');

  if (tab === 'natural') {
    tabNat.className = 'pb-2 border-b-2 border-indigo-600 text-indigo-600 px-3 transition';
    tabFrm.className = 'pb-2 border-b-2 border-transparent text-slate-400 hover:text-slate-600 px-3 transition';
    paneNat.classList.remove('hidden');
    paneFrm.classList.add('hidden');
  } else {
    tabFrm.className = 'pb-2 border-b-2 border-indigo-600 text-indigo-600 px-3 transition';
    tabNat.className = 'pb-2 border-b-2 border-transparent text-slate-400 hover:text-slate-600 px-3 transition';
    paneFrm.classList.remove('hidden');
    paneNat.classList.add('hidden');
  }
}

// --- Stats Loading ---
async function loadTodayStats() {
  try {
    const res = await fetch('/api/stats/today');
    const data = await res.json();

    document.getElementById('statTodayTotal').innerText = `$${Math.round(data.total_amount).toLocaleString()}`;
    document.getElementById('statTodayCount').innerText = `${data.total_count} 筆`;
    document.getElementById('statCardTotal').innerText = `$${Math.round(data.credit_card_amount).toLocaleString()}`;
    document.getElementById('statCardCount').innerText = `${data.credit_card_count} 筆`;
    document.getElementById('statManualTotal').innerText = `$${Math.round(data.manual_amount).toLocaleString()}`;
    document.getElementById('statManualCount').innerText = `${data.manual_count} 筆`;

    if (currentChartScope === 'today') {
      renderCategoryChart(data.by_category);
    }
  } catch (err) {
    console.error('Error loading today stats:', err);
  }
}

async function loadMonthStats() {
  try {
    const res = await fetch('/api/stats/month');
    const data = await res.json();

    document.getElementById('statMonthTotal').innerText = `$${Math.round(data.total_amount).toLocaleString()}`;
    document.getElementById('statMonthCount').innerText = `${data.total_count} 筆`;
    document.getElementById('statMonthLabel').innerText = `${data.year_month} 月累積全部消費`;

    if (currentChartScope === 'month') {
      renderCategoryChart(data.by_category);
    }
  } catch (err) {
    console.error('Error loading month stats:', err);
  }
}

function switchChartScope(scope) {
  currentChartScope = scope;
  const btnToday = document.getElementById('btnChartToday');
  const btnMonth = document.getElementById('btnChartMonth');

  if (scope === 'today') {
    btnToday.className = 'px-2.5 py-1 rounded-lg bg-indigo-100 text-indigo-700 font-semibold';
    btnMonth.className = 'px-2.5 py-1 rounded-lg text-slate-500 hover:bg-slate-100';
    loadTodayStats();
  } else {
    btnMonth.className = 'px-2.5 py-1 rounded-lg bg-indigo-100 text-indigo-700 font-semibold';
    btnToday.className = 'px-2.5 py-1 rounded-lg text-slate-500 hover:bg-slate-100';
    loadMonthStats();
  }
}

// --- Chart.js Rendering ---
function renderCategoryChart(byCategory) {
  const canvas = document.getElementById('categoryChart');
  const noData = document.getElementById('noChartData');

  const labels = Object.keys(byCategory || {});
  const dataValues = Object.values(byCategory || {});

  if (labels.length === 0 || dataValues.reduce((a, b) => a + b, 0) === 0) {
    canvas.classList.add('hidden');
    noData.classList.remove('hidden');
    if (categoryChartInstance) {
      categoryChartInstance.destroy();
      categoryChartInstance = null;
    }
    return;
  }

  canvas.classList.remove('hidden');
  noData.classList.add('hidden');

  const backgroundColors = labels.map(label => CATEGORY_COLORS[label] || '#64748b');

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  categoryChartInstance = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: backgroundColors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 12,
            font: { size: 11, family: 'Noto Sans TC' },
            padding: 10
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const val = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percent = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${context.label}: $${Math.round(val).toLocaleString()} (${percent}%)`;
            }
          }
        }
      },
      cutout: '68%'
    }
  });
}

// --- Transactions List Loading ---
async function loadTransactions() {
  const source = document.getElementById('filterSource').value;
  const category = document.getElementById('filterCategory').value;
  const keyword = document.getElementById('searchKeyword').value.trim();

  let url = '/api/transactions?limit=200';
  if (source) url += `&source=${encodeURIComponent(source)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;
  if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    const items = data.transactions || [];
    loadedTransactionsMap.clear();
    items.forEach(it => loadedTransactionsMap.set(it.id, it));
    renderTransactionsList(items);
  } catch (err) {
    console.error('Error loading transactions:', err);
  }
}

function renderTransactionsList(items) {
  const container = document.getElementById('transList');
  document.getElementById('transTotalCountBadge').innerText = `${items.length} 筆`;

  if (items.length === 0) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 text-xs">
        <i class="ph ph-receipt text-3xl mb-1 text-slate-300"></i>
        <p>尚無符合條件的消費紀錄</p>
      </div>
    `;
    return;
  }

  container.innerHTML = items.map(item => {
    const isCredit = item.source === 'gmail';
    const badgeSource = isCredit
      ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200/60">💳 ${item.bank || '信用卡'}${item.card_last4 ? ` (*${item.card_last4})` : ''}</span>`
      : `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">💵 手動申報</span>`;

    const catColor = CATEGORY_COLORS[item.category] || '#64748b';
    const isGeneric = GENERIC_MERCHANTS_SET.has(item.merchant) || item.merchant === '餐飲' || item.merchant === '一般特店';

    const merchantHtml = isGeneric
      ? `<button type="button" onclick="openEditTxModal(${item.id})" class="text-left font-bold text-sm text-slate-800 hover:text-indigo-600 transition flex items-center space-x-1.5 truncate group/m cursor-pointer" title="銀行通知未提供店名，點此自訂實際店家">
           <span class="text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200/80 text-xs font-semibold">${escapeHtml(item.merchant)}</span>
           <span class="text-[10px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center space-x-0.5 bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded border border-indigo-200/70 transition">
             <i class="ph ph-pencil-simple text-[10px]"></i>
             <span>自訂店名</span>
           </span>
         </button>`
      : `<button type="button" onclick="openEditTxModal(${item.id})" class="text-left font-bold text-sm text-slate-800 hover:text-indigo-600 transition flex items-center space-x-1 truncate group/m cursor-pointer" title="點擊自訂店名、用餐對象或備註">
           <span class="truncate">${escapeHtml(item.merchant)}</span>
           <i class="ph ph-pencil-simple text-xs text-slate-300 group-hover/m:text-indigo-500 transition shrink-0 ml-0.5"></i>
         </button>`;

    return `
      <div class="py-3 px-2 flex items-center justify-between hover:bg-slate-50/80 rounded-xl transition group">
        <div class="flex items-center space-x-3 min-w-0">
          <div class="w-2 h-9 rounded-full shrink-0" style="background-color: ${catColor}"></div>
          <div class="min-w-0">
            <div class="flex items-center space-x-2 flex-wrap gap-y-1">
              ${merchantHtml}
              ${badgeSource}
              <button type="button" onclick="openCategorySwitchModal(${item.id}, '${escapeHtml(item.merchant).replace(/'/g, "\\'")}', '${escapeHtml(item.category || '其他')}')" class="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 border border-transparent transition cursor-pointer flex items-center space-x-1 shrink-0" title="點擊切換類別或用餐對象">
                <span>${CATEGORY_ICONS[item.category] || '🏷️'}</span>
                <span>${escapeHtml(item.category || '其他')}</span>
                <i class="ph ph-caret-down text-[9px] text-slate-400"></i>
              </button>
            </div>
            <div class="flex items-center space-x-2 text-xs text-slate-400 mt-0.5 truncate">
              <span>${item.trans_date} ${item.trans_time ? item.trans_time.substring(0, 5) : ''}</span>
              ${item.note ? `<span class="truncate">• ${escapeHtml(item.note)}</span>` : ''}
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2 shrink-0 ml-2">
          <span class="text-sm font-extrabold text-slate-900">$${Math.round(item.amount).toLocaleString()}</span>
          <div class="flex items-center space-x-1 sm:opacity-0 sm:group-hover:opacity-100 transition">
            <button onclick="openEditTxModal(${item.id})" class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition" title="自訂店家名稱與明細">
              <i class="ph ph-pencil-simple-line text-base"></i>
            </button>
            <button onclick="deleteTx(${item.id})" class="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition" title="刪除此筆">
              <i class="ph ph-trash text-base"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// --- Manual Expense Submissions ---
async function submitNaturalExpense() {
  const input = document.getElementById('naturalInput');
  const text = input.value.trim();
  if (!text) {
    showToast('請輸入消費內容，例如：午餐 120', true);
    return;
  }

  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const result = await res.json();
    if (res.ok && result.success) {
      input.value = '';
      showToast(`已成功記錄：${result.transaction.merchant} $${result.transaction.amount} [${result.transaction.category}]`);
      refreshAllData();
    } else {
      showToast(result.detail || '記帳失敗', true);
    }
  } catch (err) {
    showToast('連線失敗', true);
  }
}

async function submitFormExpense() {
  const amount = parseFloat(document.getElementById('formAmount').value);
  const category = document.getElementById('formCategory').value;
  const merchant = document.getElementById('formMerchant').value.trim();
  const date = document.getElementById('formDate').value;
  const note = document.getElementById('formNote').value.trim();

  if (!amount || amount <= 0) {
    showToast('請輸入有效金額', true);
    return;
  }

  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount,
        category,
        merchant: merchant || '日常支出',
        trans_date: date,
        note,
        source: 'manual'
      })
    });
    const result = await res.json();
    if (res.ok && result.success) {
      document.getElementById('formAmount').value = '';
      document.getElementById('formMerchant').value = '';
      document.getElementById('formNote').value = '';
      showToast(`已成功記錄：$${amount} 元 [${category}]`);
      refreshAllData();
    } else {
      showToast(result.detail || '新增失敗', true);
    }
  } catch (err) {
    showToast('連線失敗', true);
  }
}

async function deleteTx(id) {
  if (!confirm('確定要刪除這筆消費紀錄嗎？')) return;
  try {
    const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('已刪除消費紀錄');
      refreshAllData();
    }
  } catch (err) {
    showToast('刪除失敗', true);
  }
}

// --- Gmail Sync Modal & Execution ---
function openSyncModal() {
  const modal = document.getElementById('syncModal');
  modal.classList.remove('hidden');
  selectSyncPreset(7);
}

function closeSyncModal() {
  document.getElementById('syncModal').classList.add('hidden');
}

function selectSyncPreset(days) {
  const today = new Date();
  const past = new Date();
  past.setDate(today.getDate() - days);

  const format = d => d.toISOString().split('T')[0];
  document.getElementById('syncStartDate').value = format(past);
  document.getElementById('syncEndDate').value = format(today);

  // Update button highlights
  [7, 14, 30, 90].forEach(d => {
    const btn = document.getElementById(`presetBtn${d}`);
    if (btn) {
      if (d === days) {
        btn.className = 'py-2 px-1 rounded-xl border border-indigo-600 bg-indigo-50 text-indigo-700 font-bold text-center transition';
      } else {
        btn.className = 'py-2 px-1 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 text-center transition';
      }
    }
  });
}

function resetSyncToThisMonth() {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const format = d => d.toISOString().split('T')[0];

  document.getElementById('syncStartDate').value = format(firstDay);
  document.getElementById('syncEndDate').value = format(today);

  // Clear presets highlight
  [7, 14, 30, 90].forEach(d => {
    const btn = document.getElementById(`presetBtn${d}`);
    if (btn) {
      btn.className = 'py-2 px-1 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 text-center transition';
    }
  });
}

function onCustomDateChange() {
  [7, 14, 30, 90].forEach(d => {
    const btn = document.getElementById(`presetBtn${d}`);
    if (btn) {
      btn.className = 'py-2 px-1 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 text-center transition';
    }
  });
}

async function executeSyncWithRange() {
  const startDate = document.getElementById('syncStartDate').value;
  const endDate = document.getElementById('syncEndDate').value;

  const btn = document.getElementById('btnExecuteSync');
  const originalHtml = btn.innerHTML;

  btn.innerHTML = `<i class="ph ph-spinner animate-spin text-base"></i><span>同步掃描中...</span>`;
  btn.disabled = true;

  try {
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_date: startDate || undefined,
        end_date: endDate || undefined
      })
    });
    const data = await res.json();
    if (data.success) {
      const rangeText = (startDate && endDate) ? ` (${startDate} ~ ${endDate})` : '';
      showToast(`同步完成${rangeText}！新增 ${data.synced_count} 筆刷卡紀錄，略過 ${data.skipped_count} 筆重複信件`);
      closeSyncModal();
      refreshAllData();
    } else {
      showToast(data.error || 'Gmail 同步失敗', true);
    }
  } catch (err) {
    showToast('同步要求失敗，請檢視伺服器連線', true);
  } finally {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
  }
}

// --- Demo Data Seed ---
async function seedDemoData() {
  try {
    const res = await fetch('/api/seed-demo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`已載入 ${data.added} 筆示範信用卡與記帳資料！`);
      refreshAllData();
    }
  } catch (err) {
    showToast('載入失敗', true);
  }
}

async function clearDemoData() {
  try {
    const res = await fetch('/api/clear-demo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`已成功清除 ${data.deleted} 筆測試假資料！`);
      refreshAllData();
    }
  } catch (err) {
    showToast('清除失敗', true);
  }
}

async function clearAllData() {
  if (!confirm('⚠️ 確定要清空所有消費記錄嗎？此動作無法復原！')) return;
  try {
    const res = await fetch('/api/clear-all', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('已清空全部消費記錄，資料庫已重設！');
      refreshAllData();
    }
  } catch (err) {
    showToast('清空失敗', true);
  }
}

// --- Daily Digest & Reminder ---
async function triggerDigestModal() {
  const modal = document.getElementById('digestModal');
  const textEl = document.getElementById('digestTextContent');
  textEl.innerText = '正在彙整今日消費數據...';
  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/remind', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      currentDigestText = data.summary_text;
      textEl.innerText = data.summary_text;
      document.getElementById('telegramNoticeStatus').innerText = data.telegram_sent
        ? '✅ 已同步推播至 Telegram'
        : 'ℹ️ 未設定 Telegram 或未開啟推播 (已記錄於系統)';
    } else {
      textEl.innerText = '產生失敗';
    }
  } catch (err) {
    textEl.innerText = '連線失敗';
  }
}

function closeDigestModal() {
  document.getElementById('digestModal').classList.add('hidden');
}

function copyDigestText() {
  if (!currentDigestText) return;
  navigator.clipboard.writeText(currentDigestText).then(() => {
    showToast('已複製日報文字到剪貼簿！');
  });
}

async function triggerImmediateReminder() {
  showToast('正在發送通知...');
  try {
    const res = await fetch('/api/remind', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.telegram_sent ? '已推播至 Telegram！' : '日報已儲存 (如需推播請至設定配置 Telegram)');
    }
  } catch (err) {
    showToast('發送失敗', true);
  }
}

// --- Settings Modal & Rules ---
async function openSettingsModal() {
  const modal = document.getElementById('settingsModal');
  modal.classList.remove('hidden');

  try {
    const res = await fetch('/api/config');
    const cfg = await res.json();

    document.getElementById('cfgGmailUser').value = cfg.gmail_user || '';
    document.getElementById('cfgGmailPassword').value = cfg.gmail_app_password || '';
    document.getElementById('cfgReminderTime').value = cfg.reminder_time || '21:30';
    document.getElementById('cfgReminderEnabled').checked = cfg.reminder_enabled !== false;
    document.getElementById('cfgTelegramEnabled').checked = !!cfg.telegram_enabled;
    document.getElementById('cfgTelegramToken').value = cfg.telegram_bot_token || '';
    document.getElementById('cfgTelegramChatId').value = cfg.telegram_chat_id || '';

    const badgeGmail = document.getElementById('badgeGmailStatus');
    if (cfg.is_gmail_configured) {
      badgeGmail.className = 'text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold';
      badgeGmail.innerText = '已連線配置';
    } else {
      badgeGmail.className = 'text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-600';
      badgeGmail.innerText = '未設定';
    }

    loadRules();
  } catch (err) {
    console.error('Error fetching config:', err);
  }
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
}

async function saveSettings() {
  const gmail_user = document.getElementById('cfgGmailUser').value;
  const gmail_app_password = document.getElementById('cfgGmailPassword').value;
  const reminder_time = document.getElementById('cfgReminderTime').value;
  const reminder_enabled = document.getElementById('cfgReminderEnabled').checked;
  const telegram_enabled = document.getElementById('cfgTelegramEnabled').checked;
  const telegram_bot_token = document.getElementById('cfgTelegramToken').value;
  const telegram_chat_id = document.getElementById('cfgTelegramChatId').value;

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gmail_user,
        gmail_app_password,
        reminder_time,
        reminder_enabled,
        telegram_enabled,
        telegram_bot_token,
        telegram_chat_id
      })
    });
    const result = await res.json();
    if (res.ok) {
      showToast('設定已成功儲存！');
      closeSettingsModal();
    } else {
      showToast('儲存失敗', true);
    }
  } catch (err) {
    showToast('連線失敗', true);
  }
}

async function loadRules() {
  try {
    const res = await fetch('/api/rules');
    const data = await res.json();
    const container = document.getElementById('rulesListContainer');
    if (!container) return;

    container.innerHTML = (data.rules || []).slice(0, 30).map(r => `
      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-white border border-slate-200 text-slate-700 shadow-2xs">
        <span class="font-medium text-slate-800">${escapeHtml(r.keyword)}</span>
        <span class="mx-1 text-slate-300">→</span>
        <span class="text-indigo-600 font-semibold">${escapeHtml(r.category)}</span>
        <button onclick="deleteCustomRule(${r.id})" class="ml-1 text-slate-300 hover:text-rose-500 font-bold">&times;</button>
      </span>
    `).join('');
  } catch (err) {
    console.error('Error loading rules:', err);
  }
}

async function addCustomRule() {
  const kwInput = document.getElementById('newRuleKeyword');
  const catInput = document.getElementById('newRuleCategory');
  const keyword = kwInput.value.trim();
  const category = catInput.value;

  if (!keyword) {
    showToast('請輸入商家關鍵字', true);
    return;
  }

  try {
    const res = await fetch('/api/rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword, category })
    });
    if (res.ok) {
      kwInput.value = '';
      showToast(`已新增規則：${keyword} → ${category}`);
      loadRules();
    }
  } catch (err) {
    showToast('新增規則失敗', true);
  }
}

async function deleteCustomRule(ruleId) {
  try {
    const res = await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' });
    if (res.ok) {
      loadRules();
    }
  } catch (err) {
    showToast('刪除規則失敗', true);
  }
}

// --- Budget & Watermark Monitor Functions ---

let cachedBudgetsData = [];

async function loadBudgets() {
  try {
    const res = await fetch('/api/budgets');
    const data = await res.json();
    cachedBudgetsData = data.budgets || [];
    renderBudgets(cachedBudgetsData);
  } catch (err) {
    console.error('Error loading budgets:', err);
  }
}

function renderBudgets(budgets) {
  const container = document.getElementById('budgetItemsList');
  if (!container) return;

  let totalBudget = 0;
  let totalSpent = 0;
  let anyExceeded = false;
  let anyWarning = false;

  budgets.forEach(b => {
    totalBudget += b.monthly_budget;
    totalSpent += b.spent_amount;
    if (b.status === 'exceeded') anyExceeded = true;
    else if (b.status === 'warning') anyWarning = true;
  });

  // Overview Banner updates
  const sumTotalEl = document.getElementById('budgetSumTotal');
  const sumSpentEl = document.getElementById('budgetSumSpent');
  const overallBadgeEl = document.getElementById('budgetOverallBadge');

  if (sumTotalEl) sumTotalEl.innerText = `$${Math.round(totalBudget).toLocaleString()}`;
  if (sumSpentEl) sumSpentEl.innerText = `$${Math.round(totalSpent).toLocaleString()}`;
  if (overallBadgeEl) {
    if (anyExceeded) {
      overallBadgeEl.className = 'px-2 py-0.5 rounded-full font-bold text-[11px] bg-rose-100 text-rose-700';
      overallBadgeEl.innerText = '🚨 有類別超標';
    } else if (anyWarning) {
      overallBadgeEl.className = 'px-2 py-0.5 rounded-full font-bold text-[11px] bg-amber-100 text-amber-700';
      overallBadgeEl.innerText = '⚠️ 接近警戒線';
    } else {
      overallBadgeEl.className = 'px-2 py-0.5 rounded-full font-bold text-[11px] bg-emerald-100 text-emerald-700';
      overallBadgeEl.innerText = '🟢 水位正常';
    }
  }

  container.innerHTML = budgets.map(b => {
    const icon = CATEGORY_ICONS[b.category] || '🏷️';
    const percent = Math.min(b.percentage, 100);

    let barColor = 'bg-emerald-500';
    let badgeHtml = '';
    let textColor = 'text-slate-600';

    if (b.status === 'exceeded') {
      barColor = 'bg-rose-500';
      textColor = 'text-rose-600 font-bold';
      const over = b.spent_amount - b.monthly_budget;
      badgeHtml = `<span class="px-1.5 py-0.2 rounded font-bold text-[10px] bg-rose-100 text-rose-700">🚨 超標 ${b.percentage}% (超支 $${Math.round(over).toLocaleString()})</span>`;
    } else if (b.status === 'warning') {
      barColor = 'bg-amber-500';
      textColor = 'text-amber-600 font-semibold';
      badgeHtml = `<span class="px-1.5 py-0.2 rounded font-semibold text-[10px] bg-amber-100 text-amber-700">⚠️ 警戒 ${b.percentage}%</span>`;
    } else {
      badgeHtml = `<span class="text-[10px] text-slate-400">已用 ${b.percentage}% (剩餘 $${Math.max(0, Math.round(b.remaining_amount)).toLocaleString()})</span>`;
    }

    return `
      <div class="space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">${icon}</span>
            <span class="font-bold text-slate-800">${escapeHtml(b.category)}</span>
            ${badgeHtml}
          </div>
          <div class="${textColor}">
            <span>$${Math.round(b.spent_amount).toLocaleString()}</span>
            <span class="text-slate-400 font-normal"> / $${Math.round(b.monthly_budget).toLocaleString()}</span>
          </div>
        </div>
        <!-- Progress Bar Track -->
        <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden flex">
          <div class="${barColor} h-full rounded-full transition-all duration-500" style="width: ${percent}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function openBudgetModal() {
  const modal = document.getElementById('budgetModal');
  const container = document.getElementById('budgetInputsList');
  if (!modal || !container) return;

  container.innerHTML = cachedBudgetsData.map(b => {
    const icon = CATEGORY_ICONS[b.category] || '🏷️';
    return `
      <div class="budget-row p-3 bg-slate-50 rounded-xl border border-slate-200/60 flex items-center justify-between gap-3" data-category="${escapeHtml(b.category)}">
        <div class="flex items-center space-x-2 min-w-[140px]">
          <span class="text-base">${icon}</span>
          <span class="text-xs font-bold text-slate-800">${escapeHtml(b.category)}</span>
        </div>
        <div class="flex items-center space-x-3">
          <div class="flex items-center space-x-1">
            <span class="text-xs text-slate-400">月預算 $</span>
            <input type="number" value="${b.monthly_budget}" step="500" min="0" class="budget-amount-input w-24 text-xs rounded-lg border-slate-200 p-1.5 bg-white text-right font-bold text-slate-800 focus:border-indigo-500">
          </div>
          <div class="flex items-center space-x-1">
            <span class="text-xs text-slate-400">警戒</span>
            <input type="number" value="${b.warning_percent || 80}" step="5" min="10" max="100" class="budget-warning-input w-14 text-xs rounded-lg border-slate-200 p-1.5 bg-white text-right font-semibold text-slate-700 focus:border-indigo-500">
            <span class="text-xs text-slate-400">%</span>
          </div>
        </div>
      </div>
    `;
  }).join('');

  modal.classList.remove('hidden');
}

function closeBudgetModal() {
  const modal = document.getElementById('budgetModal');
  if (modal) modal.classList.add('hidden');
}

async function saveAllBudgets() {
  const rows = document.querySelectorAll('.budget-row');
  const payload = [];
  rows.forEach(row => {
    const category = row.getAttribute('data-category');
    const budgetInput = row.querySelector('.budget-amount-input');
    const warningInput = row.querySelector('.budget-warning-input');
    if (category && budgetInput && warningInput) {
      payload.push({
        category: category,
        monthly_budget: parseFloat(budgetInput.value) || 0,
        warning_percent: parseFloat(warningInput.value) || 80
      });
    }
  });

  try {
    const res = await fetch('/api/budgets/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budgets: payload })
    });
    const result = await res.json();
    if (res.ok && result.success) {
      showToast('預算設定已成功儲存！');
      closeBudgetModal();
      refreshAllData();
    } else {
      showToast(result.detail || '儲存預算失敗', true);
    }
  } catch (err) {
    showToast('連線失敗，請稍後再試', true);
  }
}

// --- Quick Category Switch Modal ---

function openCategorySwitchModal(txId, merchant, currentCat) {
  currentSwitchTxId = txId;
  const modal = document.getElementById('categorySwitchModal');
  const infoEl = document.getElementById('switchTxInfo');
  const optionsEl = document.getElementById('switchCategoryOptions');

  if (!modal || !optionsEl) return;

  infoEl.innerHTML = `<span class="font-bold text-slate-700">${escapeHtml(merchant)}</span> 當前類別：<span class="text-indigo-600 font-semibold">${escapeHtml(currentCat)}</span>`;

  const allCategories = [
    '飲食 (自己吃)',
    '飲食 (和女友吃)',
    '飲食 (和家人吃)',
    '飲食 (其他)',
    '交通',
    '購物',
    '娛樂',
    '居家帳單',
    '醫療保健',
    '學習教育',
    '其他'
  ];

  optionsEl.innerHTML = allCategories.map(cat => {
    const icon = CATEGORY_ICONS[cat] || '🏷️';
    const isSelected = cat === currentCat;
    const activeClass = isSelected
      ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-bold'
      : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-700';

    return `
      <button onclick="selectNewCategory('${cat}')" class="w-full p-2.5 rounded-xl border text-xs flex items-center justify-between transition ${activeClass}">
        <span class="flex items-center space-x-2">
          <span class="text-base">${icon}</span>
          <span>${cat}</span>
        </span>
        ${isSelected ? '<i class="ph ph-check text-indigo-600 font-bold text-sm"></i>' : ''}
      </button>
    `;
  }).join('');

  modal.classList.remove('hidden');
}

function closeCategorySwitchModal() {
  const modal = document.getElementById('categorySwitchModal');
  if (modal) modal.classList.add('hidden');
  currentSwitchTxId = null;
}

async function selectNewCategory(newCategory) {
  if (!currentSwitchTxId) return;
  try {
    const res = await fetch(`/api/transactions/${currentSwitchTxId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: newCategory })
    });
    if (res.ok) {
      showToast(`已更新類別為：${newCategory}`);
      closeCategorySwitchModal();
      refreshAllData();
    } else {
      showToast('更新類別失敗', true);
    }
  } catch (err) {
    showToast('連線失敗', true);
  }
}

// --- Edit Transaction & Custom Merchant Modal ---

function openEditTxModal(txId) {
  const item = loadedTransactionsMap.get(txId);
  if (!item) {
    showToast('找不到該筆交易', true);
    return;
  }
  currentEditingTxId = txId;
  currentEditingCategory = item.category || '飲食 (自己吃)';

  const modal = document.getElementById('editTxModal');
  const merchantInput = document.getElementById('editTxMerchant');
  const noteInput = document.getElementById('editTxNote');
  const amountInput = document.getElementById('editTxAmount');
  const noticeEl = document.getElementById('editTxNotice');
  const timeSourceEl = document.getElementById('editTxTimeAndSource');

  merchantInput.value = item.merchant || '';
  noteInput.value = item.note || '';
  amountInput.value = Math.round(item.amount) || item.amount || '';

  const isGeneric = GENERIC_MERCHANTS_SET.has(item.merchant) || item.merchant === '餐飲' || item.merchant === '一般特店';
  if (isGeneric) {
    noticeEl.classList.remove('hidden');
  } else {
    noticeEl.classList.add('hidden');
  }

  const sourceLabel = item.source === 'gmail'
    ? `💳 ${item.bank || '信用卡'}${item.card_last4 ? ` (*${item.card_last4})` : ''}`
    : '💵 手動申報';
  timeSourceEl.innerText = `${item.trans_date} ${item.trans_time ? item.trans_time.substring(0, 5) : ''} · ${sourceLabel}`;

  renderEditCategoryButtons(currentEditingCategory);

  modal.classList.remove('hidden');
  merchantInput.focus();
  merchantInput.select();
}

function closeEditTxModal() {
  const modal = document.getElementById('editTxModal');
  if (modal) modal.classList.add('hidden');
  currentEditingTxId = null;
  currentEditingCategory = null;
}

function setEditMerchantPreset(preset) {
  const merchantInput = document.getElementById('editTxMerchant');
  merchantInput.value = preset;
  if (!currentEditingCategory || !currentEditingCategory.startsWith('飲食')) {
    selectEditCategory('飲食 (自己吃)');
  }
  merchantInput.focus();
}

function selectEditCategory(category) {
  currentEditingCategory = category;
  renderEditCategoryButtons(category);
}

function renderEditCategoryButtons(selectedCategory) {
  const container = document.getElementById('editTxCategoryOptions');
  if (!container) return;

  const categories = [
    '飲食 (自己吃)',
    '飲食 (和女友吃)',
    '飲食 (和家人吃)',
    '飲食 (其他)',
    '交通',
    '購物',
    '娛樂',
    '居家帳單',
    '醫療保健',
    '學習教育',
    '其他'
  ];

  container.innerHTML = categories.map(cat => {
    const isSelected = cat === selectedCategory;
    const icon = CATEGORY_ICONS[cat] || '🏷️';
    const activeClass = isSelected
      ? 'bg-indigo-50 border-indigo-500 text-indigo-700 font-bold ring-2 ring-indigo-200'
      : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-700';

    return `
      <button type="button" onclick="selectEditCategory('${cat}')" class="p-2 rounded-xl border text-xs flex items-center justify-between transition cursor-pointer ${activeClass}">
        <span class="flex items-center space-x-1.5 truncate">
          <span class="text-sm">${icon}</span>
          <span class="truncate">${cat}</span>
        </span>
        ${isSelected ? '<i class="ph ph-check text-indigo-600 font-bold"></i>' : ''}
      </button>
    `;
  }).join('');
}

async function saveEditTx() {
  if (!currentEditingTxId) return;

  const merchant = document.getElementById('editTxMerchant').value.trim();
  const note = document.getElementById('editTxNote').value.trim();
  const amountStr = document.getElementById('editTxAmount').value;
  const amount = parseFloat(amountStr);

  if (!merchant) {
    showToast('請輸入店家名稱或項目', true);
    return;
  }
  if (isNaN(amount) || amount <= 0) {
    showToast('請輸入有效的金額', true);
    return;
  }

  const payload = {
    merchant: merchant,
    category: currentEditingCategory || '其他',
    note: note,
    amount: amount
  };

  try {
    const res = await fetch(`/api/transactions/${currentEditingTxId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast(`已成功自訂為「${merchant}」(${currentEditingCategory})`);
      closeEditTxModal();
      refreshAllData();
    } else {
      const errData = await res.json();
      showToast(errData.detail || '儲存失敗', true);
    }
  } catch (err) {
    showToast('連線失敗，請稍後再試', true);
  }
}
