document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('backups-body');
    const triggerBtn = document.getElementById('btn-trigger-backup');

    async function fetchLogs() {
        try {
            const res = await fetch('/api/backups/logs');
            if (!res.ok) throw new Error('Failed to fetch logs');
            const data = await res.json();
            
            tableBody.innerHTML = '';
            
            if (data.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 60px 20px;"><div style="font-size: 24px; margin-bottom: 10px;">🗄️</div><div style="color: var(--text3);">No backups have been generated yet.</div></td></tr>`;
                return;
            }
            
            data.forEach((log, index) => {
                const tr = document.createElement('tr');
                tr.className = 'fade-up';
                tr.style.animationDelay = `${index * 20}ms`;
                
                const statusClass = log.status === 'success' ? 'status-success' : 'status-failed';
                const uploadClass = log.upload_status === 'success' ? 'status-success' : 
                                    (log.upload_status === 'skipped' ? 'status-skipped' : 'status-failed');
                                    
                const errorText = log.error_message ? `<div style="font-size:10px; color:#f6465d; margin-top:4px;">${log.error_message}</div>` : '';
                
                // Extract filename from the long path for display
                const filePath = log.file_path || '';
                const fileName = filePath.substring(filePath.lastIndexOf('\\') + 1) || filePath.substring(filePath.lastIndexOf('/') + 1) || filePath;
                
                tr.innerHTML = `
                    <td data-label="ID" class="td-mono">${log.id}</td>
                    <td data-label="BACKUP DATE" style="font-weight: 500;">${log.backup_date}</td>
                    <td data-label="STATUS"><span class="status-badge ${statusClass}">${log.status.toUpperCase()}</span>${errorText}</td>
                    <td data-label="LOCAL FILE"><div class="filepath-cell" title="${filePath}">${fileName || '—'}</div></td>
                    <td data-label="CLOUD UPLOAD"><span class="status-badge ${uploadClass}">${(log.upload_status || 'UNKNOWN').toUpperCase()}</span></td>
                    <td data-label="TIMESTAMP" style="font-size: 11px; color: var(--text3); text-align: right;">${log.created_at}</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (err) {
            console.error(err);
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #f6465d; padding: 30px;">Error loading logs from server.</td></tr>`;
        }
    }

    triggerBtn.addEventListener('click', async () => {
        triggerBtn.disabled = true;
        triggerBtn.innerHTML = '<div class="spinner" style="width:14px;height:14px;border-width:2px;margin-right:8px;display:inline-block;vertical-align:middle;"></div> Triggering...';
        
        try {
            const res = await fetch('/api/backups/generate', { method: 'POST' });
            if (res.ok) {
                // Show a nice visual feedback
                triggerBtn.style.background = '#00d26a';
                triggerBtn.style.borderColor = '#00d26a';
                triggerBtn.innerHTML = '✓ Started';
                setTimeout(() => {
                    fetchLogs();
                    triggerBtn.disabled = false;
                    triggerBtn.style.background = '';
                    triggerBtn.style.borderColor = '';
                    triggerBtn.innerHTML = `<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24" style="vertical-align: text-bottom; margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg> Trigger Manual Backup`;
                }, 2500);
            } else {
                alert('Failed to trigger backup.');
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = 'Trigger Manual Backup';
            }
        } catch (err) {
            console.error(err);
            alert('Error triggering backup.');
            triggerBtn.disabled = false;
            triggerBtn.innerHTML = 'Trigger Manual Backup';
        }
    });

    fetchLogs();
});
