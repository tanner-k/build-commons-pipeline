import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';

/**
 * Time-proportional bar across the FULL composition. Must be rendered OUTSIDE
 * any <Sequence> (direct child of BrandFrame): inside a Sequence,
 * useVideoConfig().durationInFrames is the sequence window and the bar resets
 * per segment.
 */
export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 200}});
  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp',
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
