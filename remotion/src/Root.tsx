import React from 'react';
import {CalculateMetadataFunction, Composition, Still} from 'remotion';
import {EnhancedTalkingHead} from './compositions/EnhancedTalkingHead';
import {Explainer} from './compositions/Explainer';
import {Listicle} from './compositions/Listicle';
import {Thumbnail} from './compositions/Thumbnail';
import {SAMPLE_ASSETS, SAMPLE_SCRIPT} from './lib/fixtures';
import {SAMPLE_PLAN} from './lib/enhancement-fixture';
import {planDurationInFrames} from './lib/overlay-timeline';
import {totalDurationInFrames} from './lib/timing';
import {FPS, THUMB_HEIGHT, THUMB_WIDTH, VIDEO_HEIGHT, VIDEO_WIDTH} from './lib/theme';
import type {EnhancedProps} from './compositions/EnhancedTalkingHead';
import type {VideoProps} from './compositions/VideoBody';
import type {ThumbnailProps} from './compositions/Thumbnail';

// Preview props: fixture script, but strip non-live demo URLs so Studio/smoke
// renders don't try to fetch example.supabase.co. Real props come from the
// render server with live Supabase URLs.
const previewProps: VideoProps = {
  script: SAMPLE_SCRIPT,
  assets: {...SAMPLE_ASSETS, voiceover: {}, visuals: {}, thumbnail_base: null},
};

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({props}) => ({
  durationInFrames: totalDurationInFrames(props.script, props.assets, FPS),
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="Explainer"
      component={Explainer}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={30 * FPS}
      defaultProps={previewProps}
      calculateMetadata={calculateMetadata}
    />
    <Composition
      id="Listicle"
      component={Listicle}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={30 * FPS}
      defaultProps={previewProps}
      calculateMetadata={calculateMetadata}
    />
    <Still
      id="Thumbnail"
      component={Thumbnail}
      width={THUMB_WIDTH}
      height={THUMB_HEIGHT}
      defaultProps={{headline: SAMPLE_SCRIPT.topic, baseImageUrl: null} satisfies ThumbnailProps}
    />
    <Composition
      id="EnhancedTalkingHead"
      component={EnhancedTalkingHead}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={Math.round(SAMPLE_PLAN.source_duration_s * FPS)}
      defaultProps={{plan: {...SAMPLE_PLAN, source_video_url: ''}} satisfies EnhancedProps}
      calculateMetadata={({props}: {props: EnhancedProps}) => ({
        durationInFrames: planDurationInFrames(props.plan, FPS),
      })}
    />
  </>
);
