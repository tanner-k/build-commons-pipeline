/**
 * Mirror of schemas/video_script.py (the source of truth — spec §6).
 * Change Python first, then this file, then the shared fixtures.
 */
import {z} from 'zod';

export const AI_VISUAL_TYPES = ['ai_broll', 'ai_image'] as const;

export const segmentSchema = z
  .object({
    id: z.string().min(1),
    text: z.string().min(1),
    visual_type: z.enum(['ai_broll', 'ai_image', 'screen_recording', 'text_card']),
    // null means "no prompt needed" (text_card / screen_recording); the key may
    // also be absent entirely (Python defaults it to None, and exclude_none dumps drop it).
    visual_prompt: z.string().nullable().optional(),
    duration_estimate_s: z.number().positive(),
    caption_emphasis: z.array(z.string()),
  })
  .refine(
    (s) =>
      !(AI_VISUAL_TYPES as readonly string[]).includes(s.visual_type) ||
      (s.visual_prompt ?? '').trim().length > 0,
    {message: 'visual_prompt is required for ai_broll/ai_image segments', path: ['visual_prompt']},
  );

export const videoScriptSchema = z
  .object({
    topic: z.string().min(1),
    template: z.enum(['explainer', 'tutorial', 'listicle', 'comparison']),
    hook: segmentSchema,
    segments: z.array(segmentSchema).min(1).max(5),
    cta: segmentSchema,
    target_duration_s: z.number().int().min(30).max(60),
    platform_captions: z.record(z.string()),
    hashtags: z.record(z.array(z.string())),
  })
  .refine(
    (s) => {
      const ids = [s.hook.id, ...s.segments.map((x) => x.id), s.cta.id];
      return new Set(ids).size === ids.length;
    },
    {message: 'segment ids must be unique across hook, segments, and cta'},
  );

export const wordTimingSchema = z
  .object({
    word: z.string().min(1),
    start_s: z.number().min(0),
    end_s: z.number(),
  })
  .refine((w) => w.end_s >= w.start_s, {message: 'end_s must be >= start_s'});

// Defaults to {} so partial asset objects (e.g. voiceover-only) parse successfully.
// Render compositions must guard lookups: const words = assets.timings[segId] ?? [];
export const videoAssetsSchema = z.object({
  voiceover: z.record(z.string()).default({}),
  visuals: z.record(z.string()).default({}),
  timings: z.record(z.array(wordTimingSchema)).default({}),
  thumbnail_base: z.string().nullable().default(null),
});

export type Segment = z.infer<typeof segmentSchema>;
export type VideoScript = z.infer<typeof videoScriptSchema>;
export type WordTiming = z.infer<typeof wordTimingSchema>;
export type VideoAssets = z.infer<typeof videoAssetsSchema>;

/** Hook, body segments, CTA — in playback order. */
export const allSegments = (script: VideoScript): Segment[] => [
  script.hook,
  ...script.segments,
  script.cta,
];
