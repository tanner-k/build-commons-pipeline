import type {Segment, VideoAssets, VideoScript, WordTiming} from '../types/video-script';
import {allSegments} from '../types/video-script';

export type SegmentWindow = {
  segmentId: string;
  from: number;
  durationInFrames: number;
};

/**
 * Real duration: last word end from ElevenLabs timings, else the script estimate.
 * Note: may be shorter than the actual MP3 (TTS adds trailing silence); the
 * Sequence cuts at last-word end by design — trailing silence is not missed.
 */
export const segmentDurationS = (segment: Segment, assets: VideoAssets): number => {
  const words = assets.timings[segment.id];
  if (words && words.length > 0) {
    return words[words.length - 1]!.end_s;
  }
  return segment.duration_estimate_s;
};

/** Contiguous frame windows for hook → segments → cta, starting at frame 0. */
export const buildTimeline = (
  script: VideoScript,
  assets: VideoAssets,
  fps: number,
): SegmentWindow[] => {
  const windows: SegmentWindow[] = [];
  let cursor = 0;
  for (const segment of allSegments(script)) {
    const durationInFrames = Math.max(1, Math.round(segmentDurationS(segment, assets) * fps));
    windows.push({segmentId: segment.id, from: cursor, durationInFrames});
    cursor += durationInFrames;
  }
  return windows;
};

export const totalDurationInFrames = (
  script: VideoScript,
  assets: VideoAssets,
  fps: number,
): number =>
  buildTimeline(script, assets, fps).reduce((acc, w) => acc + w.durationInFrames, 0);

/** Even-spacing caption fallback when ElevenLabs timings are missing. */
export const fallbackTimings = (text: string, durationS: number): WordTiming[] => {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const per = durationS / words.length;
  return words.map((word, i) => ({word, start_s: i * per, end_s: (i + 1) * per}));
};

/**
 * Index of the word to highlight at t seconds into the segment; -1 if no words
 * or before the first word starts (leading TTS silence — show no highlight).
 * During inter-word silence gaps the PREVIOUS word is held (karaoke convention:
 * never highlight a word before it is spoken).
 */
export const activeWordIndex = (words: WordTiming[], tS: number): number => {
  if (words.length === 0) return -1;
  for (let i = words.length - 1; i >= 0; i--) {
    if (tS >= words[i]!.start_s) return i;
  }
  return -1;
};

/** Words for a segment: real timings if present (copied), else even-spacing fallback. */
export const wordsForSegment = (segment: Segment, assets: VideoAssets): WordTiming[] => {
  const words = assets.timings[segment.id];
  if (words && words.length > 0) return [...words];
  return fallbackTimings(segment.text, segmentDurationS(segment, assets));
};
