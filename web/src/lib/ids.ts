import { randomBytes, createHash } from 'node:crypto';

export const id = (): string => randomBytes(12).toString('hex');

/** Device codes are read aloud and retyped, so no 0/O or 1/I. */
export function deviceCode(): string {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const bytes = randomBytes(8);
  let out = '';
  for (let i = 0; i < 8; i += 1) {
    out += alphabet[bytes[i]! % alphabet.length];
    if (i === 3) out += '-';
  }
  return out;
}

export const secret = (): string => randomBytes(32).toString('base64url');
export const hash = (value: string): string =>
  createHash('sha256').update(value).digest('hex');
