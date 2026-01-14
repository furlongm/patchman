document.addEventListener('DOMContentLoaded', function() {
    const expandableTexts = document.querySelectorAll('.expandable-text');
    expandableTexts.forEach(text => {
        text.addEventListener('click', function() {
            this.classList.toggle('expanded');
        });
    });
});
