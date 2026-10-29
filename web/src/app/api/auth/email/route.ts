import { NextResponse } from 'next/server';
import { z } from 'zod';
import { query } from '@/lib/db';
import { secret } from '@/lib/ids';
import { LOGIN_TOKEN_MINUTES } from '@/lib/auth/constants';

const Body = z.object({ email: z.email().max(200) });

export async function POST(request: Request): Promise<NextResponse> {
  const parsed = Body.safeParse(await request.json().catch(() => null));
  // Never reveal whether an address is registered.
  if (!parsed.success) return NextResponse.json({ ok: true });

  const email = parsed.data.email.toLowerCase();
  const token = secret();
  await query(
    `INSERT INTO login_tokens (token, email, expires_at)
     VALUES ($1, $2, now() + ($3 || ' minutes')::interval)`,
    [token, email, String(LOGIN_TOKEN_MINUTES)],
  );

  const link = `${process.env['APP_URL'] ?? ''}/api/auth/verify?token=${token}`;
  if (process.env.NODE_ENV !== 'production') {
    console.log(`[pickup] sign-in link for ${email}: ${link}`);
  }
  // TODO: send `link` by email. Logged above in development.
  return NextResponse.json({ ok: true });
}
