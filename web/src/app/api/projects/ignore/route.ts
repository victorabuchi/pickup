import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { readSession } from '@/lib/auth/session';

/** Hide a project from the dashboard without touching the machine it lives on. */
export async function POST(request: Request): Promise<NextResponse> {
  const session = await readSession();
  if (!session) return NextResponse.json({ error: 'not signed in' }, { status: 401 });

  const body = (await request.json().catch(() => ({}))) as { id?: string; ignored?: boolean };
  if (!body.id) return NextResponse.json({ error: 'id required' }, { status: 400 });

  await query(
    'UPDATE projects SET ignored = $1 WHERE id = $2 AND account_id = $3',
    [body.ignored !== false, body.id, session.accountId],
  );
  return NextResponse.json({ ok: true });
}
