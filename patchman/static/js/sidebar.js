document.addEventListener('DOMContentLoaded', function() {
    const STORAGE_KEY = 'patchman_sidebar_state';
    const COLLAPSED_KEY = 'patchman_sidebar_collapsed';
    const savedState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');

    const sidebarNav = document.querySelector('.sidebar-nav');
    const sidebarLayout = document.querySelector('.sidebar-layout');

    // Apply saved collapsed state
    if (localStorage.getItem(COLLAPSED_KEY) === 'true') {
        sidebarNav.classList.add('collapsed');
        sidebarLayout.classList.add('collapsed');
    }

    // Sidebar collapse toggle
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebarNav.classList.toggle('collapsed');
            sidebarLayout.classList.toggle('collapsed');
            localStorage.setItem(COLLAPSED_KEY, sidebarNav.classList.contains('collapsed'));
        });
    }

    // Apply saved state to submenus
    const submenuItems = document.querySelectorAll('.has-submenu');
    submenuItems.forEach((item, index) => {
        const menuId = item.querySelector('a').textContent.trim();
        if (savedState[menuId] !== undefined) {
            if (savedState[menuId]) {
                item.classList.add('open');
            } else {
                item.classList.remove('open');
            }
        }
    });

    // Toggle submenu and save state
    const submenuLinks = document.querySelectorAll('.has-submenu > a');
    submenuLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.parentElement;
            parent.classList.toggle('open');
            // Save state to localStorage
            const menuId = this.textContent.trim();
            const currentState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            currentState[menuId] = parent.classList.contains('open');
            localStorage.setItem(STORAGE_KEY, JSON.stringify(currentState));
        });
    });
});
