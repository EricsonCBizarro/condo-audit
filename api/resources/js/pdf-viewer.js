import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

// <canvas data-pdf-src="..." data-pdf-page="3"> renders one page of a PDF.
export async function renderPdfPages(canvases) {
    for (const canvas of canvases) {
        const pdf = await pdfjsLib.getDocument(canvas.dataset.pdfSrc).promise;
        const page = await pdf.getPage(Number(canvas.dataset.pdfPage || 1));
        const viewport = page.getViewport({ scale: 1.5 });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
        canvas.dataset.rendered = 'true';
    }
}
