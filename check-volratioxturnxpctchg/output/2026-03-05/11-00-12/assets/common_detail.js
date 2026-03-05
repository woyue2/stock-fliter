
    let currentUrl = '';
    let isPriceFilterActive = false; /* 默认不激活，以免初始隐藏过多 */
    let isHideChuangKeActive = false; /* 默认不隐藏创科 */
    let currentSearchKeyword = '';

    document.addEventListener('DOMContentLoaded', () => {
      loadChecked();
      
      // 取消按钮默认 active 状态
      document.getElementById('priceFilterBtn').classList.remove('active');
      document.getElementById('hideChuangKeBtn').classList.remove('active');
      
      applyFilters();
    });

    function togglePriceFilter() {
      isPriceFilterActive = !isPriceFilterActive;
      const btn = document.getElementById('priceFilterBtn');
      if (isPriceFilterActive) { btn.classList.add('active'); } else { btn.classList.remove('active'); }
      applyFilters();
    }

    function toggleHideChuangKe() {
      isHideChuangKeActive = !isHideChuangKeActive;
      const btn = document.getElementById('hideChuangKeBtn');
      if (isHideChuangKeActive) { btn.classList.add('active'); } else { btn.classList.remove('active'); }
      applyFilters();
    }

    function filterTable(keyword) {
      currentSearchKeyword = keyword.toLowerCase();
      applyFilters();
    }

    function applyFilters() {
      const industryCounts = {};
      let visibleCount = 0;

      document.querySelectorAll('#tbody tr').forEach(tr => {
        const price = parseFloat(tr.dataset.price || 0);
        const text = tr.textContent.toLowerCase();
        const b = tr.dataset.board || '';
        const i = tr.dataset.industry || '';
        
        const matchesSearch = text.includes(currentSearchKeyword);
        const matchesPrice = !isPriceFilterActive || price < 10;
        const isChuangKe = b === '创业板' || b === '科创板';
        const matchesChuangKe = !isHideChuangKeActive || !isChuangKe;
        
        if (matchesSearch && matchesPrice && matchesChuangKe) {
          tr.style.display = '';
          visibleCount++;
          if (i && i !== 'nan') industryCounts[i] = (industryCounts[i] || 0) + 1;
        } else {
          tr.style.display = 'none';
        }
      });

      renderStats('boardStatsContainer', industryCounts);
      
      const countEl = document.getElementById('visibleCount');
      if (countEl) countEl.textContent = '共 ' + visibleCount + ' 只';
    }

    function renderStats(containerId, countsObj) {
      const container = document.getElementById(containerId);
      if (!container) return;
      const sorted = Object.entries(countsObj).sort((a, b) => b[1] - a[1]).slice(0, 10);
      container.innerHTML = sorted.map(item => `<span class="tag">${item[0]} ${item[1]}</span>`).join('\n');
    }

    function loadChecked() {
      const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      checked.forEach(code => {
        const cb = document.querySelector(`input[data-code="${code}"]`);
        if (cb) { cb.checked = true; cb.closest('tr').classList.add('checked'); }
      });
      updateInfo();
    }

    function saveChecked() {
      const checked = [];
      document.querySelectorAll('.check:checked').forEach(cb => { checked.push(cb.dataset.code); cb.closest('tr').classList.add('checked'); });
      document.querySelectorAll('.check:not(:checked)').forEach(cb => { cb.closest('tr').classList.remove('checked'); });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
      updateInfo();
    }

    function updateInfo() {
      const count = document.querySelectorAll('.check:checked').length;
      document.getElementById('checkedInfo').textContent = '已选 ' + count;
    }

    function selectAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = true); saveChecked(); }
    function clearAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = false); saveChecked(); }

    function showStock(url) {
      currentUrl = url;
      const match = url.match(/([a-z]+\d+)\.html/);
      if(match) {
          const code = match[1];
          document.getElementById('stockTitle').textContent = code.toUpperCase();
      }
      document.getElementById('openNew').style.display = 'inline';
      document.getElementById('placeholder').style.display = 'none';
      document.getElementById('frameWrapper').style.display = 'block';
      const frame = document.getElementById('stockFrame');
      frame.src = url;
    }
    