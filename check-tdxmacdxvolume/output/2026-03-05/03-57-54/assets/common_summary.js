
        const STORAGE_KEY = 'selected_stocks';
        const NOTES_KEY = 'report_notes';
        
        document.addEventListener('DOMContentLoaded', () => {
            loadSelectedStocks();
            loadNotes();
            window.addEventListener('message', handleIframeMessage);
        });
        
        function handleIframeMessage(event) {
            if (event.data && event.data.type === 'selectionUpdate') {
                renderSelectedStocks(event.data.stocks);
            }
        }
        
        window.addSelectedStockFromChild = function(selectedCodes) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedCodes));
            renderSelectedStocks(selectedCodes);
            document.querySelectorAll('iframe').forEach(iframe => {
                try { iframe.contentWindow.updateSelectionFromParent(selectedCodes); } catch (e) {}
            });
        };
        
        function loadSelectedStocks() {
            const stocks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            renderSelectedStocks(stocks);
        }
        
        function renderSelectedStocks(stocks) {
            const container = document.getElementById('selectedList');
            const countEl = document.getElementById('selectedCount');
            countEl.textContent = stocks.length + '只';
            if (stocks.length === 0) {
                container.innerHTML = '<span style="color:#999;font-size:11px;">暂无</span>';
                return;
            }
            container.innerHTML = stocks.map(code => `
                <span class="selected-item" data-code="${code}">
                    ${code}
                    <span class="remove" onclick="removeStock('${code}')">×</span>
                </span>
            `).join('');
        }
        
        function removeStock(code) {
            let stocks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            stocks = stocks.filter(c => c !== code);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stocks));
            renderSelectedStocks(stocks);
            document.querySelectorAll('iframe').forEach(iframe => {
                try { iframe.contentWindow.removeStockSelection(code); } catch (e) {}
            });
        }
        
        function loadNotes() {
            document.getElementById('notesInput').value = localStorage.getItem(NOTES_KEY) || '';
        }
        
        document.getElementById('notesInput').addEventListener('input', function() {
            localStorage.setItem(NOTES_KEY, this.value);
        });
        
        function showStrategy(strategy) {
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.toggle('active', item.dataset.strategy === strategy);
            });
            if (availableStrategies.includes(strategy)) {
                document.getElementById('content').innerHTML = `<iframe src="${strategy}.html"></iframe>`;
            } else {
                document.getElementById('content').innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;text-align:center;">
                    <div><div style="font-size:48px;margin-bottom:16px;">📭</div><div style="font-size:16px;">暂无符合该策略的股票</div></div>
                </div>`;
            }
        }
        