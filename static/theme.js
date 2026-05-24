// theme.js - Run immediately in <head> to prevent flash of incorrect theme
(function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        // Default to light theme if no preference is saved
        document.documentElement.setAttribute('data-theme', 'light');
    }
    
    // Inject Logout logic once DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        const menuItems = document.querySelector('.menu-items');
        if (menuItems) {
            const logoutBtn = document.createElement('a');
            logoutBtn.href = '#';
            logoutBtn.className = 'menu-item';
            logoutBtn.style.color = 'var(--red)';
            logoutBtn.style.marginTop = 'auto';
            logoutBtn.style.fontWeight = 'bold';
            logoutBtn.innerHTML = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24" style="margin-right: 12px;"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>Logout';
            logoutBtn.onclick = async (e) => {
                e.preventDefault();
                await fetch('/api/logout', { method: 'POST' });
                window.location.href = '/login.html';
            };
            menuItems.appendChild(logoutBtn);
        }
    });
})();
