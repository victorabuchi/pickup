import { createHmac, timingSafeEqual } from 'node:crypto';

export interface SessionPayload {
  accountId: string;
  email: string;
  exp: number;
}

const b64 = (value: Buffer | string): string =>
  Buffer.from(value).toString('base64url');

function sign(body: string, secret: string): string {
  return createHmac('sha256', secret).update(body).digest('base64url');
}

export function encodeSession(payload: SessionPayload, secret: string): string {
  const body = b64(JSON.stringify(payload));
  return `${body}.${sign(body, secret)}`;
}

export function decodeSession(
  raw: string | undefined,
  secret: string,
  now: number,
): SessionPayload | null {
  if (!raw) return null;
  const [body, signature] = raw.split('.');
  if (!body || !signature) return null;

  const expected = sign(body, secret);
  const a = Buffer.from(signature);
  const b = Buffer.from(expected);
  // Constant time: a length mismatch must not short-circuit the comparison.
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;

  try {
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString()) as SessionPayload;
    if (typeof payload.exp !== 'number' || payload.exp < now) return null;
    if (!payload.accountId || !payload.email) return null;
    return payload;
  } catch {
    return null;
  }
}
