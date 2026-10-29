import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { readSession } from '@/lib/auth/session';

export async function GET(request: Request): Promise<NextResponse> {
  const session = await readSession();
  if (!session) return NextResponse.json({ error: 'not signed in' }, { status: 401 });

  const ignored = new URL(request.url).searchParams.get('ignored') === '1';
  const rows = await query(
    `SELECT p.id, p.name, p.path, p.status, p.summary, p.stack, p.branch, p.commits,
            p.dirty, p.has_git, p.note, p.note_is_yours, p.last_activity, p.ignored,
            p.detail, d.name AS device_name
       FROM projects p
       JOIN devices d ON d.id = p.device_id
      WHERE p.account_id = $1 AND p.ignored = $2
      ORDER BY p.last_activity DESC NULLS LAST`,
    [session.accountId, ignored],
  );
  return NextResponse.json({ rows });
}
