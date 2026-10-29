import { NextResponse } from 'next/server';
import { one, query } from '@/lib/db';

/** The agent polls until the browser has approved, then collects its token once. */
export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json().catch(() => ({}))) as { code?: string };
  const code = String(body.code ?? '').toUpperCase().trim();
  if (!code) return NextResponse.json({ error: 'code required' }, { status: 400 });

  const row = await one<{ secret: string | null; expires_at: string; claimed_at: string | null }>(
    'SELECT secret, expires_at, claimed_at FROM device_codes WHERE code = $1',
    [code],
  );
  if (!row) return NextResponse.json({ status: 'unknown' }, { status: 404 });
  if (row.claimed_at) return NextResponse.json({ status: 'already_claimed' }, { status: 410 });
  if (new Date(row.expires_at).getTime() < Date.now()) {
    return NextResponse.json({ status: 'expired' }, { status: 410 });
  }
  if (!row.secret) return NextResponse.json({ status: 'pending' });

  await query('UPDATE device_codes SET secret = NULL, claimed_at = now() WHERE code = $1', [code]);
  return NextResponse.json({ status: 'ready', token: row.secret });
}
