import {describe, expect, it} from 'vitest';
import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema, overlaySchema} from './enhancement';

describe('enhancement contract mirror', () => {
  it('validates the shared fixture (same file pytest validates)', () => {
    const plan = enhancementPlanSchema.parse(samplePlan);
    expect(plan.source_duration_s).toBe(48);
    expect(plan.overlays.length).toBeGreaterThanOrEqual(3);
  });

  it('rejects ai overlay without a prompt', () => {
    const bad = {
      id: 'x', start_s: 0, end_s: 2, type: 'ai_broll', placement: 'fullframe',
      prompt: '  ', text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow(/prompt/);
  });

  it('rejects text_effect without text', () => {
    const bad = {
      id: 'x', start_s: 0, end_s: 2, type: 'text_effect', placement: 'pip',
      prompt: null, text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow(/text/);
  });

  it('rejects end before start', () => {
    const bad = {
      id: 'x', start_s: 3, end_s: 3, type: 'ai_image', placement: 'pip',
      prompt: 'p', text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow();
  });

  it('rejects overlapping overlays at plan level', () => {
    const plan = {...samplePlan, overlays: [
      {...samplePlan.overlays[0], id: 'a', start_s: 0, end_s: 4},
      {...samplePlan.overlays[0], id: 'b', start_s: 2, end_s: 6},
    ]};
    expect(() => enhancementPlanSchema.parse(plan)).toThrow(/overlap/);
  });
});
