import {describe, expect, it} from 'vitest';
import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from '../types/video-script';
import {
  activeWordIndex,
  buildTimeline,
  fallbackTimings,
  segmentDurationS,
  totalDurationInFrames,
} from './timing';

const script = videoScriptSchema.parse(sampleScript);
const assets = videoAssetsSchema.parse(sampleAssets);
const FPS = 30;

describe('segmentDurationS', () => {
  it('uses last word end when timings exist', () => {
    expect(segmentDurationS(script.hook, assets)).toBeCloseTo(2.6);
  });
  it('falls back to duration_estimate_s without timings', () => {
    expect(segmentDurationS(script.segments[0]!, assets)).toBeCloseTo(6.0);
  });
});

describe('buildTimeline', () => {
  it('covers hook + body + cta in order, contiguous from frame 0', () => {
    const tl = buildTimeline(script, assets, FPS);
    expect(tl.map((w) => w.segmentId)).toEqual(['hook', 'seg-1', 'seg-2', 'seg-3', 'cta']);
    expect(tl[0]!.from).toBe(0);
    for (let i = 1; i < tl.length; i++) {
      expect(tl[i]!.from).toBe(tl[i - 1]!.from + tl[i - 1]!.durationInFrames);
    }
  });
  it('every window has at least 1 frame', () => {
    for (const w of buildTimeline(script, assets, FPS)) {
      expect(w.durationInFrames).toBeGreaterThan(0);
    }
  });
});

describe('totalDurationInFrames', () => {
  it('equals the sum of all windows', () => {
    const tl = buildTimeline(script, assets, FPS);
    const sum = tl.reduce((acc, w) => acc + w.durationInFrames, 0);
    expect(totalDurationInFrames(script, assets, FPS)).toBe(sum);
  });
});

describe('fallbackTimings', () => {
  it('spreads words evenly across the duration', () => {
    const words = fallbackTimings('one two three four', 4);
    expect(words).toHaveLength(4);
    expect(words[0]).toEqual({word: 'one', start_s: 0, end_s: 1});
    expect(words[3]!.end_s).toBeCloseTo(4);
  });
  it('handles single-word text', () => {
    expect(fallbackTimings('hello', 2)).toEqual([{word: 'hello', start_s: 0, end_s: 2}]);
  });
});

describe('activeWordIndex', () => {
  const words = fallbackTimings('a b c d', 4); // 1s per word
  it('returns the word containing t', () => {
    expect(activeWordIndex(words, 0.5)).toBe(0);
    expect(activeWordIndex(words, 2.5)).toBe(2);
  });
  it('clamps before start and after end', () => {
    expect(activeWordIndex(words, -1)).toBe(0);
    expect(activeWordIndex(words, 99)).toBe(3);
  });
  it('returns -1 for empty word list', () => {
    expect(activeWordIndex([], 1)).toBe(-1);
  });
});
