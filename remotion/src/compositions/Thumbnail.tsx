import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {brandFontFamily} from '../lib/font';
import {BRAND} from '../lib/theme';

export type ThumbnailProps = {
  headline: string;
  baseImageUrl: string | null;
};

export const Thumbnail: React.FC<ThumbnailProps> = ({headline, baseImageUrl}) => (
  <AbsoluteFill style={{backgroundColor: BRAND.bg, fontFamily: brandFontFamily}}>
    {baseImageUrl ? (
      <Img
        src={baseImageUrl}
        style={{width: '100%', height: '100%', objectFit: 'cover', opacity: 0.55}}
      />
    ) : null}
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: 64}}>
      <div
        style={{
          color: BRAND.text,
          fontSize: 96,
          fontWeight: 800,
          lineHeight: 1.05,
          textShadow: '0 6px 32px rgba(0,0,0,0.8)',
          maxWidth: '85%',
          // Long topics must never push the wordmark out of the 720px frame.
          maxHeight: 420,
          overflow: 'hidden',
        }}
      >
        {headline}
      </div>
      <div
        style={{
          marginTop: 28,
          color: BRAND.accent,
          fontSize: 32,
          fontWeight: 700,
          letterSpacing: '0.25em',
        }}
      >
        {BRAND.name}
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);
