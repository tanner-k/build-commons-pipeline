import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';

export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 200}});
  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: 12,
        width: `${progress * 100}%`,
        backgroundColor: BRAND.accent,
        transform: `scaleY(${entrance})`,
        transformOrigin: 'top',
      }}
    />
  );
};
