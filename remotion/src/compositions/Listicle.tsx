import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import {VideoBody, type VideoProps} from './VideoBody';

const NumberBadge: React.FC<{n: number}> = ({n}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 10, mass: 0.6}});
  return (
    <div
      style={{
        position: 'absolute',
        top: 96,
        left: BRAND.framePadding,
        width: 120,
        height: 120,
        borderRadius: 60,
        backgroundColor: BRAND.accent,
        color: BRAND.bg,
        fontSize: 64,
        fontWeight: 800,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `scale(${enter})`,
      }}
    >
      {n}
    </div>
  );
};

export const Listicle: React.FC<VideoProps> = (props) => (
  <VideoBody {...props} renderBadge={(i) => <NumberBadge n={i + 1} />} />
);
