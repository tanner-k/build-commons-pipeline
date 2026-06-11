import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BRAND} from '../lib/theme';

export const BrandFrame: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{backgroundColor: BRAND.bg, fontFamily: BRAND.fontFamily}}>
    {children}
    <div
      style={{
        position: 'absolute',
        bottom: 36,
        left: 0,
        right: 0,
        textAlign: 'center',
        color: BRAND.muted,
        fontSize: 28,
        fontWeight: 700,
        letterSpacing: '0.25em',
      }}
    >
      {BRAND.name}
    </div>
  </AbsoluteFill>
);
