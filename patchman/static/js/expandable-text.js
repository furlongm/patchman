document.addEventListener('DOMContentLoaded', function() {
    const expandableTexts = document.querySelectorAll('.expandable-text');
    expandableTexts.forEach(text => {
        text.addEventListener('click', function() {
            this.classList.toggle('expanded');
        });
    });

    // Sidebar submenu state from localStorage
    const STORAGE_KEY = 'patchman_sidebar_state';
    const savedState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');

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
