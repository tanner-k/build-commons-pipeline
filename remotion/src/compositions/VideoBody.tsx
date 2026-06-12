import React from 'react';
import {Audio, Sequence} from 'remotion';
import {BrandFrame} from '../components/BrandFrame';
import {Captions} from '../components/Captions';
import {ProgressBar} from '../components/ProgressBar';
import {SegmentVisual} from '../components/SegmentVisual';
import {FPS} from '../lib/theme';
import {buildTimeline, wordsForSegment} from '../lib/timing';
import {allSegments, type VideoAssets, type VideoScript} from '../types/video-script';

export type VideoProps = {script: VideoScript; assets: VideoAssets};

/** Shared hook→segments→cta sequencing; templates wrap this with their own chrome. */
export const VideoBody: React.FC<
  VideoProps & {renderBadge?: (bodyIndex: number) => React.ReactNode}
> = ({script, assets, renderBadge}) => {
  const timeline = buildTimeline(script, assets, FPS);
  const segments = allSegments(script);
  const bodyIds = new Set(script.segments.map((s) => s.id));
  let bodyIndex = 0;

  return (
    <BrandFrame>
      {segments.map((segment, i) => {
        const window = timeline[i];
        if (!window) return null;
        const voice = assets.voiceover[segment.id];
        const badgeIndex = bodyIds.has(segment.id) ? bodyIndex++ : -1;
        return (
          <Sequence
            key={segment.id}
            from={window.from}
            durationInFrames={window.durationInFrames}
            name={segment.id}
          >
            <SegmentVisual segment={segment} assets={assets} />
            {voice ? <Audio src={voice} /> : null}
            <Captions segment={segment} words={wordsForSegment(segment, assets)} />
            {badgeIndex >= 0 && renderBadge ? renderBadge(badgeIndex) : null}
          </Sequence>
        );
      })}
      <ProgressBar />
    </BrandFrame>
  );
};
