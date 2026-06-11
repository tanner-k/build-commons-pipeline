import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import type {Segment, VideoAssets} from '../types/video-script';

const TextCard: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', padding: BRAND.framePadding * 2}}>
      <div
        style={{
          color: BRAND.text,
          fontSize: 88,
          fontWeight: 800,
          lineHeight: 1.15,
          textAlign: 'center',
          opacity: enter,
          transform: `translateY(${(1 - enter) * 60}px)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

export const SegmentVisual: React.FC<{segment: Segment; assets: VideoAssets}> = ({
  segment,
  assets,
}) => {
  const url = assets.visuals[segment.id];
  if (segment.visual_type === 'text_card' || !url) {
    return <TextCard text={segment.text} />;
  }
  if (segment.visual_type === 'ai_broll') {
    return (
      <AbsoluteFill>
        <OffthreadVideo src={url} style={{width: '100%', height: '100%', objectFit: 'cover'}} muted />
      </AbsoluteFill>
    );
  }
  // ai_image and screen_recording stills/uploads render as images
  return (
    <AbsoluteFill>
      <Img src={url} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};
