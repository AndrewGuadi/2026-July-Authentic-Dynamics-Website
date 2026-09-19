const MAX_BYTES = 5000000;
const ERROR = "We couldn't read that image. Please choose a PNG, JPG, or WebP file.";
export async function optimizeLogo(file) {
  if (file.size > MAX_BYTES) throw new Error('Logo must be 5 MB or smaller.');
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) throw new Error(ERROR);
  const header = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const png = [137, 80, 78, 71, 13, 10, 26, 10].every((value, i) => header[i] === value);
  const jpeg = header[0] === 255 && header[1] === 216 && header[2] === 255;
  const webp = String.fromCharCode(...header.slice(0, 4)) === 'RIFF' && String.fromCharCode(...header.slice(8, 12)) === 'WEBP';
  if (!({ 'image/png': png, 'image/jpeg': jpeg, 'image/webp': webp })[file.type]) throw new Error(ERROR);
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 40000000) throw new Error('Logo dimensions are too large. Use an image under 40 megapixels.');
    let scale = Math.min(1, 1200 / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    for (let attempt = 0; attempt < 8; attempt += 1) {
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext('2d');
      if (!context) throw new Error(ERROR);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const data = canvas.toDataURL('image/png');
      if (data.length <= 1500000) return { data, width: canvas.width, height: canvas.height };
      scale *= 0.75;
    }
    throw new Error('This image is too complex to store efficiently. Try a smaller logo.');
  } catch (error) {
    if (error instanceof Error && /dimensions|complex/.test(error.message)) throw error;
    throw new Error(ERROR);
  } finally { URL.revokeObjectURL(url); }
}
export async function checkImportedLogo(logo) {
  if (!logo) return null;
  // Decode only an embedded, schema-validated PNG. Never accept URLs or SVG.
  const bytes = Uint8Array.from(atob(logo.data.split(',')[1]), char => char.charCodeAt(0));
  return optimizeLogo(new File([bytes], 'imported-logo.png', { type: 'image/png' }));
}
