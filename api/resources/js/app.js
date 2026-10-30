document.addEventListener('DOMContentLoaded', async () => {
    const canvases = document.querySelectorAll('canvas[data-pdf-src]');
    if (canvases.length > 0) {
        // pdf.js is only downloaded on pages that show a document.
        const { renderPdfPages } = await import('./pdf-viewer.js');
        await renderPdfPages(canvases);
    }
});
