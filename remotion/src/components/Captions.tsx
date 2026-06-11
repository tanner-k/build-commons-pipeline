import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {activeWordIndex} from '../lib/timing';
import {isEmphasized} from '../lib/emphasis';
import {BRAND} from '../lib/theme';
import type {Segment, WordTiming} from '../types/video-script';

const GROUP_SIZE = 4;

export const Captions: React.FC<{segment: Segment; words: WordTiming[]}> = ({
  segment,
  words,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const tS = frame / fps;
  const active = activeWordIndex(words, tS);
  if (active === -1) return null;

  const groupStart = Math.floor(active / GROUP_SIZE) * GROUP_SIZE;
  const group = words.slice(groupStart, groupStart + GROUP_SIZE);
  const first = group[0];
  if (!first) return null;
  const groupStartFrame = Math.round(first.start_s * fps);
  const pop = spring({frame: frame - groupStartFrame, fps, config: {damping: 12, mass: 0.5}});

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 320,
        left: BRAND.framePadding,
        right: BRAND.framePadding,
        textAlign: 'center',
        transform: `scale(${0.9 + 0.1 * pop})`,
      }}
    >
      {group.map((w, i) => {
        const idx = groupStart + i;
        const isActive = idx === active;
        const emphasized = isEmphasized(w.word, segment.caption_emphasis);
        return (
          <span
            key={`${idx}-${w.word}`}
            style={{
              fontSize: 64,
              fontWeight: 800,
              lineHeight: 1.3,
              margin: '0 10px',
              color: emphasized ? BRAND.accent : BRAND.text,
              opacity: isActive ? 1 : 0.65,
              textShadow: '0 4px 24px rgba(0,0,0,0.6)',
            }}
          >
            {w.word}
          </span>
        );
      })}
    </div>
  );
};
