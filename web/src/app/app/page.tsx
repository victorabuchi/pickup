import { redirect } from 'next/navigation';
import { query } from '@/lib/db';
import { readSession } from '@/lib/auth/session';
import type { Project } from '@/lib/types';
import Dashboard from '@/components/Dashboard';

interface Row {
  id: string; name: string; path: string; status: Project['status'];
  summary: string; stack: string[]; branch: string; commits: number; dirty: number;
  has_git: boolean; note: string; note_is_yours: boolean;
  last_activity: Date | null; ignored: boolean; detail: Project['detail'];
  device_name: string;
}

function shape(row: Row): Project {
  return {
    id: row.id, name: row.name, path: row.path, status: row.status,
    summary: row.summary, stack: row.stack ?? [], branch: row.branch,
    commits: row.commits, dirty: row.dirty, hasGit: row.has_git,
    note: row.note, noteIsYours: row.note_is_yours,
    lastActivity: row.last_activity ? row.last_activity.toISOString() : null,
    ignored: row.ignored, deviceName: row.device_name, detail: row.detail ?? {},
  };
}

export default async function AppPage() {
  const session = await readSession();
  if (!session) redirect('/login');

  const sql = `SELECT p.id, p.name, p.path, p.status, p.summary, p.stack, p.branch,
                      p.commits, p.dirty, p.has_git, p.note, p.note_is_yours,
                      p.last_activity, p.ignored, p.detail, d.name AS device_name
                 FROM projects p
                 JOIN devices d ON d.id = p.device_id
                WHERE p.account_id = $1 AND p.ignored = $2
                ORDER BY p.last_activity DESC NULLS LAST`;

  const [tracked, hidden] = await Promise.all([
    query<Row>(sql, [session.accountId, false]),
    query<Row>(sql, [session.accountId, true]),
  ]);

  return (
    <Dashboard
      email={session.email}
      projects={tracked.map(shape)}
      untracked={hidden.map(shape)}
    />
  );
}
