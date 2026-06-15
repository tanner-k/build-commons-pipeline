import {staticFile} from 'remotion';
import type {EnhancementPlan, Overlay} from '../types/enhancement';

export type FrameWindow = {from: number; durationInFrames: number};

export const overlayWindow = (overlay: Overlay, fps: number): FrameWindow => ({
  from: Math.round(overlay.start_s * fps),
  durationInFrames: Math.max(1, Math.round((overlay.end_s - overlay.start_s) * fps)),
});

export const planDurationInFrames = (plan: EnhancementPlan, fps: number): number =>
  Math.max(1, Math.round(plan.source_duration_s * fps));

/** http(s) urls pass through; relative paths resolve via staticFile (public/); empty stays empty. */
export const resolveSourceSrc = (url: string): string => {
  if (url === '') return '';
  if (/^https?:\/\//.test(url)) return url;
  return staticFile(url);
};
