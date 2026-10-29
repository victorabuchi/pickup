import { NextResponse } from 'next/server';
import { one, query } from '@/lib/db';
import { createSession } from '@/lib/auth/session';
import { id } from '@/lib/ids';

/** Follow the emailed link: burn the token, make or find the account, sign in. */
export async function GET(request: Request): Promise<NextResponse> {
  const url = new URL(request.url);
  const token = url.searchParams.get('token') ?? '';
  const base = process.env['APP_URL'] ?? url.origin;

  const row = await one<{ email: string }>(
    `UPDATE login_tokens SET used_at = now()
      WHERE token = $1 AND used_at IS NULL AND expires_at > now()
      RETURNING email`,
    [token],
  );
  if (!row) return NextResponse.redirect(`${base}/login?error=expired`);

  let account = await one<{ id: string }>('SELECT id FROM accounts WHERE email = $1', [row.email]);
  if (!account) {
    const accountId = id();
    await query('INSERT INTO accounts (id, email) VALUES ($1, $2)', [accountId, row.email]);
    account = { id: accountId };
  }

  await createSession(account.id, row.email);
  const next = url.searchParams.get('code');
  return NextResponse.redirect(next ? `${base}/login?code=${next}` : `${base}/app`);
}
