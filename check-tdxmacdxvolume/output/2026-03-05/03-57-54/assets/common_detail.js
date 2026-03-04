
        let currentUrl = '';
        document.addEventListener('DOMContentLoaded', loadChecked);
        
        function loadChecked() {
            const checked = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            checked.forEach(code => {
                const cb = document.querySelector(`input[data-code="${code}"]`);
                if (cb) {
                    cb.checked = true;
                    cb.closest('tr').classList.add('checked');
                }
            });
            updateInfo();
        }
        
        function saveChecked() {
            const checked = [];
            document.querySelectorAll('.check:checked').forEach(cb => {
                checked.push(cb.dataset.code);
                cb.closest('tr').classList.add('checked');
            });
            document.querySelectorAll('.check:not(:checked)').forEach(cb => {
                cb.closest('tr').classList.remove('checked');
            });
            localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));
            updateInfo();
            try { window.parent.addSelectedStockFromChild(checked); } catch (e) {}
        }
        
        function updateSelectionFromParent(selectedCodes) {
            document.querySelectorAll('.check').forEach(cb => {
                const isChecked = selectedCodes.includes(cb.dataset.code);
                cb.checked = isChecked;
                cb.closest('tr').classList.toggle('checked', isChecked);
            });
            updateInfo();
        }
        
        function removeStockSelection(code) {
            const cb = document.querySelector(`input[data-code="${code}"]`);
            if (cb) {
                cb.checked = false;
                cb.closest('tr').classList.remove('checked');
            }
            saveChecked();
        }
        
        function updateInfo() {
            document.getElementById('checkedInfo').textContent = '已选 ' + document.querySelectorAll('.check:checked').length;
        }
        
        function selectAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = true); saveChecked(); }
        function clearAll() { document.querySelectorAll('.check').forEach(cb => cb.checked = false); saveChecked(); }
        
        function exportCSV() {
            const rows = [['代码', '名称']];
            document.querySelectorAll('.check:checked').forEach(cb => rows.push([cb.dataset.code, cb.closest('tr').cells[2].textContent]));
            if (rows.length === 1) { alert('请先选择股票'); return; }
            const csv = rows.map(r => r.join(',')).join('\n');
            const blob = new Blob(['\ufeff' + csv], {type: 'text/csv'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = STRATEGY_NAME + '.csv';
            a.click();
        }
        
        function filterTable(keyword) {
            keyword = keyword.toLowerCase();
            document.querySelectorAll('#tbody tr').forEach(tr => { tr.style.display = tr.textContent.toLowerCase().includes(keyword) ? '' : 'none'; });
        }
        
        function showStock(url) {
            currentUrl = url;
            document.getElementById('stockTitle').textContent = url.match(/([a-z]+\d+)\.html/)[1].toUpperCase();
            document.getElementById('openNew').style.display = 'inline';
            document.getElementById('placeholder').style.display = 'none';
            const frame = document.getElementById('stockFrame');
            frame.style.display = 'block';
            frame.src = url;
        }
        