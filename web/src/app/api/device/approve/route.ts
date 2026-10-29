import { NextResponse } from 'next/server';
import { one, query } from '@/lib/db';
import { readSession } from '@/lib/auth/session';
import { hash, id, secret } from '@/lib/ids';

/** The signed-in browser approves a code the agent is waiting on. */
export async function POST(request: Request): Promise<NextResponse> {
  const session = await readSession();
  if (!session) return NextResponse.json({ error: 'not signed in' }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as { code?: string };
  const code = String(body.code ?? '').toUpperCase().trim();
  if (!code) return NextResponse.json({ error: 'code required' }, { status: 400 });

  const pending = await one<{ code: string; device_name: string; platform: string }>(
    `SELECT code, device_name, platform FROM device_codes
     WHERE code = $1 AND claimed_at IS NULL AND expires_at > now()`,
    [code],
  );
  if (!pending) {
    return NextResponse.json({ error: 'that code has expired or was already used' }, { status: 404 });
  }

  const deviceId = id();
  const token = secret();
  await query(
    `INSERT INTO devices (id, account_id, name, platform, token_hash)
     VALUES ($1, $2, $3, $4, $5)`,
    [deviceId, session.accountId, pending.device_name, pending.platform, hash(token)],
  );
  // The secret waits here until the agent collects it, then it is wiped.
  await query(
    `UPDATE device_codes SET account_id = $1, device_id = $2, secret = $3 WHERE code = $4`,
    [session.accountId, deviceId, token, code],
  );

  return NextResponse.json({ ok: true, device: pending.device_name });
}
