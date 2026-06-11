import {describe, expect, it} from 'vitest';
import {isEmphasized} from './emphasis';

describe('isEmphasized', () => {
  it('matches case-insensitively ignoring punctuation', () => {
    expect(isEmphasized('Stop,', ['stop'])).toBe(true);
    expect(isEmphasized('2020.', ['2020'])).toBe(true);
    expect(isEmphasized('reading', ['stop'])).toBe(false);
  });
  it('handles empty emphasis list', () => {
    expect(isEmphasized('word', [])).toBe(false);
  });
});
