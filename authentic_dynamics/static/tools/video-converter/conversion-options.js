// UI-independent engine options. A future WebCodecs adapter can accept the same values.
export const PRESETS = {
  smaller: {format: 'mp4', quality: 'smaller', resolution: '720', audio: 'keep'},
  website: {format: 'mp4', quality: 'balanced', resolution: '1080', audio: 'keep'},
  format: {format: 'mp4', quality: 'balanced', resolution: 'original', audio: 'keep'},
  resize: {format: 'mp4', quality: 'balanced', resolution: '720', audio: 'keep'},
  silent: {format: 'mp4', quality: 'balanced', resolution: 'original', audio: 'remove'},
  extract: {format: 'mp3', quality: 'balanced', resolution: 'original', audio: 'keep'},
  custom: {format: 'mp4', quality: 'balanced', resolution: 'original', audio: 'keep'},
};
export function buildArguments(options) {
  const choices = {format: ['mp4', 'webm', 'mp3', 'wav'], quality: ['smaller', 'balanced', 'higher'],
    resolution: ['original', '1080', '720', '480'], fps: ['original', '60', '30', '24'], audio: ['keep', 'remove']};
  for (const [key, values] of Object.entries(choices)) {
    if (!values.includes(options[key])) throw new Error('Invalid conversion option');
  }
  // Input is a fixed local path. Disable network protocols even for crafted playlists.
  const args = ['-protocol_whitelist', 'file', '-i', '/input', '-map_metadata', '-1'];
  if (['mp3', 'wav'].includes(options.format)) {
    args.push('-map', '0:a:0', '-vn', '-c:a', options.format === 'mp3' ? 'libmp3lame' : 'pcm_s16le');
    if (options.format === 'mp3') args.push('-b:a', {smaller: '96k', balanced: '160k', higher: '256k'}[options.quality]);
  } else {
    args.push('-map', '0:v:0');
    if (options.audio === 'keep') args.push('-map', '0:a:0?');
    else args.push('-an');
    let scale = 'scale=trunc(iw/2)*2:trunc(ih/2)*2';
    if (options.resolution !== 'original') {
      const short = Number(options.resolution), long = Math.round(short * 16 / 9);
      scale = `scale=w='min(iw,if(gte(iw,ih),${long},${short}))':h='min(ih,if(gte(iw,ih),${short},${long}))':force_original_aspect_ratio=decrease:force_divisible_by=2`;
    }
    args.push('-vf', scale, '-pix_fmt', 'yuv420p');
    if (options.fps !== 'original') args.push('-r', options.fps);
    const crf = options.format === 'mp4' ? {smaller: '30', balanced: '23', higher: '18'} : {smaller: '35', balanced: '20', higher: '10'};
    args.push('-c:v', options.format === 'mp4' ? 'libx264' : 'libvpx', '-crf', crf[options.quality], '-threads', '1');
    if (options.format === 'mp4') args.push('-preset', 'veryfast', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '128k');
    else args.push('-b:v', {smaller: '600k', balanced: '1500k', higher: '3000k'}[options.quality], '-deadline', 'realtime', '-cpu-used', '6', '-lag-in-frames', '0', '-c:a', 'libopus', '-b:a', '96k');
  }
  return [...args, '/output.' + options.format];
}
