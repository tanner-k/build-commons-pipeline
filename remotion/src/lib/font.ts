import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont();

/** Brand font, registered via @font-face on import. Import only from React components. */
export const brandFontFamily = fontFamily;
