import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence} from 'remotion';
import {BrandFrame} from '../components/BrandFrame';
import {OverlayLayer} from '../components/Overlay';
import {FPS} from '../lib/theme';
import {overlayWindow, resolveSourceSrc} from '../lib/overlay-timeline';
import {sortedOverlays, type EnhancementPlan} from '../types/enhancement';

export type EnhancedProps = {plan: EnhancementPlan};

export const EnhancedTalkingHead: React.FC<EnhancedProps> = ({plan}) => {
  const src = resolveSourceSrc(plan.source_video_url);
  return (
    <AbsoluteFill>
      {src ? (
        <OffthreadVideo src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      ) : (
        <BrandFrame>{null}</BrandFrame>
      )}
      {sortedOverlays(plan).map((overlay) => {
        const win = overlayWindow(overlay, FPS);
        return (
          <Sequence key={overlay.id} from={win.from} durationInFrames={win.durationInFrames} name={overlay.id}>
            <OverlayLayer overlay={overlay} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
