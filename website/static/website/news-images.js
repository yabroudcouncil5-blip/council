document.querySelectorAll('[data-news-image]').forEach((image) => {
    function handleUnavailableImage() {
        if (image.dataset.fallbackSrc) {
            image.src = image.dataset.fallbackSrc;
            delete image.dataset.fallbackSrc;
        } else {
            image.closest('.news-article-media, .news-detail-image').hidden = true;
        }
    }

    image.addEventListener('error', handleUnavailableImage);
    if (image.complete && !image.naturalWidth) {
        handleUnavailableImage();
    }
});
