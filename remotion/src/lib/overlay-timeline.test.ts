import {describe, expect, it} from 'vitest';
import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema} from '../types/enhancement';
import {overlayWindow, planDurationInFrames, resolveSourceSrc} from './overlay-timeline';

const plan = enhancementPlanSchema.parse(samplePlan);
const FPS = 30;

describe('overlayWindow', () => {
  it('maps seconds to a frame window', () => {
    const w = overlayWindow(plan.overlays[0]!, FPS); // 3.0-9.0s
    expect(w.from).toBe(90);
    expect(w.durationInFrames).toBe(180);
  });
  it('always at least one frame', () => {
    const w = overlayWindow({...plan.overlays[0]!, start_s: 1.0, end_s: 1.001}, FPS);
    expect(w.durationInFrames).toBeGreaterThan(0);
  });
});

describe('planDurationInFrames', () => {
  it('rounds source duration to frames', () => {
    expect(planDurationInFrames(plan, FPS)).toBe(Math.round(48 * FPS));
  });
});

describe('resolveSourceSrc', () => {
  it('passes http urls through', () => {
    expect(resolveSourceSrc('https://x/v.mp4')).toBe('https://x/v.mp4');
  });
  it('wraps relative paths for staticFile lookup', () => {
    expect(resolveSourceSrc('smoke-base.mp4')).toMatch(/smoke-base\.mp4$/);
  });
  it('empty stays empty (composition shows brand bg)', () => {
    expect(resolveSourceSrc('')).toBe('');
  });
});
