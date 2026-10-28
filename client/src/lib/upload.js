// Leave room for multipart fields below Vercel's 4.5 MB request-body limit.
export const MAX_PDF_BYTES = 4 * 1024 * 1024

export function pdfUploadError(file) {
  return file && file.size > MAX_PDF_BYTES
    ? 'Choose a PDF no larger than 4 MiB, or paste your notes.'
    : ''
}
