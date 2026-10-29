import { NextResponse } from 'next/server';
import { z } from 'zod';
import { query } from '@/lib/db';
import { id } from '@/lib/ids';
import { deviceFromRequest } from '@/lib/auth/agent';

const Project = z.object({
  name: z.string().min(1).max(200),
  path: z.string().min(1).max(600),
  status: z.enum(['active', 'stalled', 'dead']),
  summary: z.string().max(400).default(''),
  stack: z.array(z.string().max(30)).max(10).default([]),
  branch: z.string().max(120).default(''),
  commits: z.number().int().min(0).default(0),
  dirty: z.number().int().min(0).default(0),
  hasGit: z.boolean().default(false),
  note: z.string().max(600).default(''),
  noteIsYours: z.boolean().default(false),
  lastActivity: z.number().nullable().default(null),
  detail: z.record(z.string(), z.unknown()).default({}),
});

const Body = z.object({ projects: z.array(Project).max(500) });

/**
 * The agent reports what it found.
 *
 * Replaces this device's rows wholesale, so a project deleted on disk stops
 * appearing. Any ignore choice made in the dashboard is carried over, because
 * the agent has no idea what was hidden here.
 */
export async function POST(request: Request): Promise<NextResponse> {
  const device = await deviceFromRequest(request);
  if (!device) return NextResponse.json({ error: 'unknown device' }, { status: 401 });

  const parsed = Body.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ error: 'bad payload', detail: parsed.error.issues }, { status: 400 });
  }

  const previous = await query<{ path: string; ignored: boolean }>(
    'SELECT path, ignored FROM projects WHERE device_id = $1',
    [device.id],
  );
  const wasIgnored = new Map(previous.map((row) => [row.path, row.ignored]));

  await query('DELETE FROM projects WHERE device_id = $1', [device.id]);

  for (const project of parsed.data.projects) {
    await query(
      `INSERT INTO projects
         (id, account_id, device_id, name, path, status, summary, stack, branch,
          commits, dirty, has_git, note, note_is_yours, last_activity, detail, ignored)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)`,
      [
        id(), device.account_id, device.id, project.name, project.path, project.status,
        project.summary, project.stack, project.branch, project.commits, project.dirty,
        project.hasGit, project.note, project.noteIsYours,
        project.lastActivity ? new Date(project.lastActivity * 1000) : null,
        JSON.stringify(project.detail), wasIgnored.get(project.path) ?? false,
      ],
    );
  }

  return NextResponse.json({ ok: true, stored: parsed.data.projects.length });
}
