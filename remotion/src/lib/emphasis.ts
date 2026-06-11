const normalize = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

/** Should this caption word get the accent highlight? */
export const isEmphasized = (word: string, emphasis: string[]): boolean =>
  emphasis.some((e) => normalize(e) === normalize(word));
