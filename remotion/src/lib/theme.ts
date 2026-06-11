import {isEmphasized} from './emphasis';

let cachedFontFamily: string | null = null;

export const loadBrandFont = (): string => {
  if (!cachedFontFamily) {
    // Dynamic import to avoid loading @remotion/google-fonts in test environment
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const {loadFont} = require('@remotion/google-fonts/Inter');
    const {fontFamily} = loadFont();
    cachedFontFamily = fontFamily;
  }
  return cachedFontFamily;
};

export const BRAND = {
  name: 'BUILD COMMONS',
  bg: '#0B1220',
  surface: '#141E33',
  text: '#F4F6FB',
  muted: '#8A94A8',
  accent: '#FFB224',
  fontFamily: 'Inter',
  framePadding: 48,
} as const;

export const FPS = 30;
export const VIDEO_WIDTH = 1080;
export const VIDEO_HEIGHT = 1920;
export const THUMB_WIDTH = 1280;
export const THUMB_HEIGHT = 720;

export {isEmphasized};
