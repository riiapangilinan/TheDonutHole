document.addEventListener('DOMContentLoaded', function() {
    const flashMessage = document.getElementById('flash-message');
    if (flashMessage) {
        setTimeout(() => {
            flashMessage.classList.add('show');
        }, 100);

        setTimeout(() => {
            flashMessage.classList.remove('show');
        
            setTimeout(() => {
                if (flashMessage) {
                    flashMessage.remove();
                }
            }, 500);
        }, 5000);
    }
});