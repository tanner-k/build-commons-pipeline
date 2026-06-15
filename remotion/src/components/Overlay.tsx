import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import {resolveSourceSrc} from '../lib/overlay-timeline';
import type {Overlay as OverlayT} from '../types/enhancement';

const PlaceholderCard: React.FC<{label: string; tone?: string}> = ({label, tone}) => (
  <AbsoluteFill
    style={{
      backgroundColor: BRAND.surface,
      border: `4px dashed ${tone ?? BRAND.accent}`,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 64,
    }}
  >
    <div style={{color: tone ?? BRAND.accent, fontSize: 56, fontWeight: 800, textAlign: 'center'}}>
      {label}
    </div>
  </AbsoluteFill>
);

// Own component so its hooks are always called unconditionally (Rules of Hooks):
// Visual() has early returns, so hooks must never live in one of its branches.
const TextEffectVisual: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, mass: 0.5}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: 48}}>
      <div
        style={{
          color: BRAND.text,
          backgroundColor: 'rgba(11,18,32,0.72)',
          padding: '20px 32px',
          borderRadius: 18,
          fontSize: 64,
          fontWeight: 800,
          textAlign: 'center',
          transform: `scale(${0.9 + 0.1 * pop})`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Visual: React.FC<{overlay: OverlayT}> = ({overlay}) => {
  const url = overlay.asset_url ?? '';
  if (overlay.type === 'screen_recording') {
    return <PlaceholderCard label={`SCREEN REC:\n${overlay.text ?? ''}`} />;
  }
  if (overlay.type === 'text_effect') {
    return <TextEffectVisual text={overlay.text ?? ''} />;
  }
  if (!url) {
    return <PlaceholderCard label={`${overlay.type}:\n${overlay.prompt ?? ''}`} tone={BRAND.muted} />;
  }
  if (overlay.type === 'ai_broll') {
    return (
      <AbsoluteFill>
        <OffthreadVideo src={resolveSourceSrc(url)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <Img src={resolveSourceSrc(url)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};

/** Full-frame cutaway, or a picture-in-picture corner box. */
export const OverlayLayer: React.FC<{overlay: OverlayT}> = ({overlay}) => {
  if (overlay.placement === 'pip') {
    return (
      <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'flex-end', padding: 48}}>
        <div
          style={{
            width: '42%',
            aspectRatio: '4 / 5',
            borderRadius: 24,
            overflow: 'hidden',
            border: `6px solid ${BRAND.accent}`,
            boxShadow: '0 12px 48px rgba(0,0,0,0.5)',
            position: 'relative',
          }}
        >
          <Visual overlay={overlay} />
        </div>
      </AbsoluteFill>
    );
  }
  return <Visual overlay={overlay} />;
};
