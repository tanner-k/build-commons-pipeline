import {execFile} from 'node:child_process';
import {mkdtemp, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {promisify} from 'node:util';
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {videoAssetsSchema, videoScriptSchema} from '../../src/types/video-script';
import {uploadRender, type VideoRow} from './supabase';

const execFileAsync = promisify(execFile);

const COMPOSITION_BY_TEMPLATE: Record<VideoRow['template'], string> = {
  explainer: 'Explainer',
  tutorial: 'Explainer', // Tutorial.tsx is Phase 6 — falls back to Explainer until then
  listicle: 'Listicle',
  comparison: 'Listicle', // Comparison.tsx is Phase 6
};

let bundlePromise: Promise<string> | null = null;
const getBundle = (): Promise<string> => {
  bundlePromise ??= bundle({
    entryPoint: new URL('../../src/index.ts', import.meta.url).pathname,
  });
  return bundlePromise;
};

/** ffmpeg -crf 28 -preset slow (spec §7 Stage 3 post-process, ~80% size cut). */
const compress = async (input: string, output: string): Promise<void> => {
  await execFileAsync('ffmpeg', [
    '-y',
    '-i',
    input,
    '-c:v',
    'libx264',
    '-crf',
    '28',
    '-preset',
    'slow',
    '-c:a',
    'copy',
    output,
  ]);
};

export type RenderResult = {renderUrl: string; thumbnailUrl: string};

export const renderVideoJob = async (video: VideoRow): Promise<RenderResult> => {
  const script = videoScriptSchema.parse(video.script_json);
  const assets = videoAssetsSchema.parse(video.asset_urls ?? {});
  const inputProps = {script, assets};

  const serveUrl = await getBundle();
  const workDir = await mkdtemp(join(tmpdir(), `render-${video.id}-`));
  try {
    const composition = await selectComposition({
      serveUrl,
      id: COMPOSITION_BY_TEMPLATE[video.template],
      inputProps,
    });

    const rawPath = join(workDir, 'raw.mp4');
    const finalPath = join(workDir, 'final.mp4');
    const thumbPath = join(workDir, 'thumb.png');

    await renderMedia({
      composition,
      serveUrl,
      codec: 'h264',
      outputLocation: rawPath,
      inputProps,
    });
    await compress(rawPath, finalPath);

    const thumbProps = {headline: script.topic, baseImageUrl: assets.thumbnail_base};
    const thumbComposition = await selectComposition({
      serveUrl,
      id: 'Thumbnail',
      inputProps: thumbProps,
    });
    await renderStill({
      composition: thumbComposition,
      serveUrl,
      output: thumbPath,
      inputProps: thumbProps,
    });

    const [renderUrl, thumbnailUrl] = await Promise.all([
      uploadRender(`${video.id}/final.mp4`, await readFile(finalPath), 'video/mp4'),
      uploadRender(`${video.id}/thumbnail.png`, await readFile(thumbPath), 'image/png'),
    ]);
    return {renderUrl, thumbnailUrl};
  } finally {
    await rm(workDir, {recursive: true, force: true});
  }
};
