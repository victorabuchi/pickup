import { cookies } from 'next/headers';
import { SESSION_COOKIE, SESSION_DAYS } from './constants';
import { decodeSession, encodeSession, type SessionPayload } from './token';

export function sessionSecret(): string {
  const value = process.env['SESSION_SECRET'];
  if (!value || value.length < 32) {
    throw new Error('SESSION_SECRET must be set (32+ characters)');
  }
  return value;
}

export async function createSession(accountId: string, email: string): Promise<void> {
  const maxAge = SESSION_DAYS * 24 * 60 * 60;
  const payload: SessionPayload = { accountId, email, exp: Date.now() + maxAge * 1000 };
  (await cookies()).set(SESSION_COOKIE, encodeSession(payload, sessionSecret()), {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge,
  });
}

export async function readSession(): Promise<SessionPayload | null> {
  const raw = (await cookies()).get(SESSION_COOKIE)?.value;
  return decodeSession(raw, sessionSecret(), Date.now());
}

export async function destroySession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}
