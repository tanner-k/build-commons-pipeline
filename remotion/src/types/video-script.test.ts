import {describe, expect, it} from 'vitest';
import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from './video-script';

describe('contract mirror', () => {
  it('validates the shared script fixture (same file pytest validates)', () => {
    const script = videoScriptSchema.parse(sampleScript);
    expect(script.template).toBe('explainer');
    expect(script.segments).toHaveLength(3);
  });

  it('validates the shared assets fixture', () => {
    const assets = videoAssetsSchema.parse(sampleAssets);
    expect(assets.timings['hook']!.length).toBeGreaterThan(0);
  });

  it('rejects ai visuals without a prompt', () => {
    const bad = {
      id: 'x', text: 'x', visual_type: 'ai_broll', visual_prompt: null,
      duration_estimate_s: 3, caption_emphasis: [],
    };
    expect(() => videoScriptSchema.parse({...sampleScript, hook: bad})).toThrow(/visual_prompt/);
  });

  it('rejects ai visuals with whitespace-only prompt (parity with Python)', () => {
    const bad = {
      id: 'x', text: 'x', visual_type: 'ai_image', visual_prompt: '   ',
      duration_estimate_s: 3, caption_emphasis: [],
    };
    expect(() => videoScriptSchema.parse({...sampleScript, hook: bad})).toThrow(/visual_prompt/);
  });

  it('rejects empty words in timings (parity with Python)', () => {
    const badAssets = {
      ...sampleAssets,
      timings: {hook: [{word: '', start_s: 0, end_s: 0.5}]},
    };
    expect(() => videoAssetsSchema.parse(badAssets)).toThrow();
  });

  it('rejects out-of-range target duration', () => {
    expect(() => videoScriptSchema.parse({...sampleScript, target_duration_s: 20})).toThrow();
  });

  it('rejects duplicate segment ids', () => {
    const dup = {...sampleScript, cta: {...sampleScript.cta, id: 'seg-1'}};
    expect(() => videoScriptSchema.parse(dup)).toThrow(/unique/);
  });
});
