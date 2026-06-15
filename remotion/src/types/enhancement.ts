/**
 * Mirror of schemas/enhancement.py (source of truth). Change Python first,
 * then this file, then the shared fixture sample_enhancement_plan.json.
 */
import {z} from 'zod';

const AI_TYPES = ['ai_broll', 'ai_image'] as const;
const TEXT_TYPES = ['text_effect', 'screen_recording'] as const;

export const overlaySchema = z
  .object({
    id: z.string().min(1),
    start_s: z.number().min(0),
    end_s: z.number(),
    type: z.enum(['ai_broll', 'ai_image', 'screen_recording', 'text_effect']),
    placement: z.enum(['fullframe', 'pip']),
    prompt: z.string().nullable().optional(),
    text: z.string().nullable().optional(),
    rationale: z.string().min(1),
    asset_url: z.string().nullable().optional(),
  })
  .refine((o) => o.end_s > o.start_s, {message: 'end_s must be > start_s', path: ['end_s']})
  .refine(
    (o) => !(AI_TYPES as readonly string[]).includes(o.type) || (o.prompt ?? '').trim().length > 0,
    {message: 'prompt is required for ai_broll/ai_image', path: ['prompt']},
  )
  .refine(
    (o) => !(TEXT_TYPES as readonly string[]).includes(o.type) || (o.text ?? '').trim().length > 0,
    {message: 'text is required for text_effect/screen_recording', path: ['text']},
  );

export const enhancementPlanSchema = z
  .object({
    source_video_url: z.string().min(1),
    source_duration_s: z.number().positive(),
    overlays: z.array(overlaySchema).default([]),
    platform_captions: z.record(z.string()),
    hashtags: z.record(z.array(z.string())),
  })
  .refine(
    (p) => new Set(p.overlays.map((o) => o.id)).size === p.overlays.length,
    {message: 'overlay ids must be unique'},
  )
  .refine(
    (p) => p.overlays.every((o) => o.end_s <= p.source_duration_s),
    {message: 'an overlay ends past source_duration_s'},
  )
  .refine((p) => {
    const ordered = [...p.overlays].sort((a, b) => a.start_s - b.start_s);
    return ordered.every((o, i) => i === 0 || o.start_s >= ordered[i - 1]!.end_s);
  }, {message: 'overlays overlap in time'});

export type Overlay = z.infer<typeof overlaySchema>;
export type EnhancementPlan = z.infer<typeof enhancementPlanSchema>;

/** Overlays sorted by start time. */
export const sortedOverlays = (plan: EnhancementPlan): Overlay[] =>
  [...plan.overlays].sort((a, b) => a.start_s - b.start_s);
