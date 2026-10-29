'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Project } from '@/lib/types';
import styles from './dashboard.module.css';

type Filter = 'all' | 'active' | 'stalled' | 'dead' | 'dirty' | 'untracked';
type Tab = 'overview' | 'commits' | 'files' | 'prompts';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All projects' },
  { key: 'active', label: 'Active' },
  { key: 'stalled', label: 'Stalled' },
  { key: 'dead', label: 'Dead' },
  { key: 'dirty', label: 'Uncommitted' },
  { key: 'untracked', label: 'Not tracked' },
];

function ago(iso: string | null): string {
  if (!iso) return 'never';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

export default function Dashboard({
  email, projects, untracked,
}: { email: string; projects: Project[]; untracked: Project[] }) {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>('all');
  const [term, setTerm] = useState('');
  const [open, setOpen] = useState<Project | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [busy, setBusy] = useState<string | null>(null);

  const count = (key: Filter): number =>
    key === 'untracked' ? untracked.length
      : key === 'all' ? projects.length
        : key === 'dirty' ? projects.filter((p) => p.dirty > 0).length
          : projects.filter((p) => p.status === key).length;

  const rows = useMemo(() => {
    const source = filter === 'untracked' ? untracked : projects;
    const needle = term.trim().toLowerCase();
    return source.filter((p) => {
      if (filter === 'dirty' && p.dirty === 0) return false;
      if (filter !== 'all' && filter !== 'dirty' && filter !== 'untracked' && p.status !== filter) {
        return false;
      }
      if (!needle) return true;
      return `${p.name} ${p.summary} ${p.note} ${p.stack.join(' ')}`
        .toLowerCase().includes(needle);
    });
  }, [filter, term, projects, untracked]);

  async function setTracked(project: Project, ignored: boolean) {
    setBusy(project.id);
    await fetch('/api/projects/ignore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: project.id, ignored }),
    });
    setBusy(null);
    setOpen(null);
    router.refresh();
  }

  async function signOut() {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/');
  }

  const detail = open?.detail ?? {};
  const commits = detail.history ?? [];
  const edits = detail.edits ?? [];
  const prompts = detail.prompts ?? [];

  return (
    <div className={styles.shell}>
      <aside className={styles.side}>
        <div className={styles.brand}><span className={styles.mark}>p</span><b>Pickup</b></div>
        <nav className={styles.nav}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={styles.navItem}
              aria-current={filter === f.key}
              onClick={() => { setFilter(f.key); setOpen(null); }}
            >
              <span className={`${styles.swatch} ${styles[f.key] ?? ''}`} />
              {f.label}
              <span className={styles.n}>{count(f.key)}</span>
            </button>
          ))}
        </nav>
        <div className={styles.sideFoot}>
          <span>{email}</span>
          <button className={styles.signOut} onClick={signOut}>Sign out</button>
        </div>
      </aside>

      <div className={styles.top}>
        <div className={styles.search}>
          <input
            type="search" placeholder="Search projects, notes, stacks…"
            value={term} onChange={(e) => setTerm(e.target.value)}
          />
        </div>
      </div>

      <main className={styles.main}>
        {projects.length === 0 && untracked.length === 0 ? (
          <div className={styles.onboard}>
            <h2>No machine has reported yet</h2>
            <p>Install the agent and sign it in. It will send what it finds, and this page fills itself.</p>
            <code>brew install pickup &amp;&amp; pickup login</code>
          </div>
        ) : (
          <>
            <div className={styles.stats}>
              <div className={styles.stat} style={{ ['--tone' as string]: 'var(--brand-tint)' }}>
                <b>{projects.length}</b><span>Projects</span>
              </div>
              <div className={styles.stat} style={{ ['--tone' as string]: 'var(--green-bg)' }}>
                <b>{count('active')}</b><span>Active</span>
              </div>
              <div className={styles.stat} style={{ ['--tone' as string]: 'var(--orange-bg)' }}>
                <b>{count('stalled')}</b><span>Stalled</span>
              </div>
              <div className={styles.stat} style={{ ['--tone' as string]: 'var(--slate-bg)' }}>
                <b>{count('dead')}</b><span>Dead</span>
              </div>
              <div className={styles.stat} style={{ ['--tone' as string]: 'var(--blue-bg)' }}>
                <b>{count('dirty')}</b><span>Uncommitted</span>
              </div>
            </div>

            <h2 className={styles.heading}>
              {FILTERS.find((f) => f.key === filter)?.label} · {rows.length}
            </h2>

            <div className={styles.grid}>
              {rows.map((p, i) => (
                <div
                  key={p.id}
                  className={styles.card}
                  style={{ ['--d' as string]: `${Math.min(i * 22, 330)}ms` }}
                >
                  {filter === 'untracked' ? (
                    <>
                      <div className={styles.cardTop}>
                        <span className={`${styles.dot} ${styles.dead}`} />
                        <h3>{p.name}</h3>
                      </div>
                      <p className={styles.desc}>{p.summary || 'Not being tracked'}</p>
                      <button
                        className={styles.restore}
                        disabled={busy === p.id}
                        onClick={() => setTracked(p, false)}
                      >
                        {busy === p.id ? 'Restoring…' : 'Track again'}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className={styles.untrack}
                        title="Stop tracking"
                        onClick={(e) => { e.stopPropagation(); setTracked(p, true); }}
                      >
                        ✕
                      </button>
                      <button
                        className={styles.cardBody}
                        onClick={() => { setOpen(p); setTab('overview'); }}
                      >
                        <div className={styles.cardTop}>
                          <span className={`${styles.dot} ${styles[p.status] ?? ''}`} />
                          <h3>{p.name}</h3>
                          {p.stack[0] && <span className={styles.stackTag}>{p.stack[0]}</span>}
                        </div>
                        <p className={styles.desc}>{p.summary || 'No description'}</p>
                        <div className={styles.tags}>
                          <span className={styles.tag}>{ago(p.lastActivity)}</span>
                          {p.hasGit ? (
                            <>
                              <span className={styles.tag}>{p.commits} commits</span>
                              {p.dirty > 0 && (
                                <span className={`${styles.tag} ${styles.warn}`}>{p.dirty} uncommitted</span>
                              )}
                            </>
                          ) : (
                            <span className={`${styles.tag} ${styles.ghost}`}>no git</span>
                          )}
                          <span className={`${styles.tag} ${styles.ghost}`}>{p.deviceName}</span>
                        </div>
                        {p.note && (
                          <div className={`${styles.said} ${p.noteIsYours ? styles.you : ''}`}>{p.note}</div>
                        )}
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>

            {rows.length === 0 && (
              <div className={styles.empty}><b>Nothing matches</b>Try a different filter or search.</div>
            )}
          </>
        )}
      </main>

      {open && (
        <>
          <div className={styles.scrim} onClick={() => setOpen(null)} />
          <aside className={styles.drawer} role="dialog" aria-label={open.name}>
            <div className={styles.drawerHead}>
              <span className={`${styles.dot} ${styles[open.status] ?? ''}`} style={{ marginTop: 7 }} />
              <div style={{ minWidth: 0 }}>
                <h3>{open.name}</h3>
                <p className={styles.desc}>{open.summary || 'No description'}</p>
              </div>
              <button className={styles.close} onClick={() => setOpen(null)} aria-label="Close">✕</button>
            </div>

            <div className={styles.drawerBody}>
              <div className={styles.tabs}>
                {([['overview', 'Overview', 0], ['commits', 'Commits', commits.length],
                   ['files', 'Files', edits.length], ['prompts', 'You asked', prompts.length]] as const)
                  .map(([key, label, n]) => (
                    <button
                      key={key} className={styles.tab}
                      aria-selected={tab === key} onClick={() => setTab(key as Tab)}
                    >
                      {label}{n > 0 && <span className={styles.c}>{n}</span>}
                    </button>
                  ))}
              </div>

              {tab === 'overview' && (
                <>
                  <div className={styles.metrics}>
                    <div className={styles.metric}><b>{open.commits}</b><span>Commits</span></div>
                    <div className={styles.metric}><b>{detail.filesCount ?? 0}</b><span>Files</span></div>
                    <div className={styles.metric}><b>{detail.size ?? '—'}</b><span>On disk</span></div>
                    <div className={styles.metric}><b>{open.dirty}</b><span>Uncommitted</span></div>
                  </div>
                  <Field label="Machine" value={open.deviceName} />
                  <Field label="Path" value={open.path} mono />
                  <Field label="Last file edited" value={detail.newestFile} mono />
                  <Field label="File activity" value={detail.touched} />
                  {detail.age && <Field label="First commit" value={`${detail.firstCommit} · ${detail.age}`} />}
                  <Field label="Last commit" value={detail.subject} />
                </>
              )}

              {tab === 'commits' && (
                commits.length ? (
                  <div className={styles.log}>
                    {commits.map((c) => (
                      <div key={c.hash} className={styles.logRow}>
                        <span className={styles.sha}>{c.hash}</span>
                        <div className={styles.logMain}>
                          <div className={styles.logSubject}>{c.subject}</div>
                          <div className={styles.logMeta}>{c.author} · {c.date}</div>
                        </div>
                        <span className={styles.when}>{c.ago}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className={styles.none}>No git history here.</p>
              )}

              {tab === 'files' && (
                edits.length ? (
                  <div className={styles.log}>
                    {edits.map((e) => (
                      <div key={e.path} className={styles.logRow}>
                        <span className={styles.fpath}>{e.path}</span>
                        <span className={styles.when} style={{ marginLeft: 'auto' }}>{e.ago}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className={styles.none}>Nothing but ignored files.</p>
              )}

              {tab === 'prompts' && (
                prompts.length ? (
                  <ul className={styles.quotes}>
                    {prompts.map((q, i) => (
                      <li key={i}><span className={styles.quoteWhen}>{q.ago}</span>{q.text}</li>
                    ))}
                  </ul>
                ) : <p className={styles.none}>No prompt history synced for this project.</p>
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value?: string; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className={styles.field}>
      <span>{label}</span>
      <p className={mono ? styles.mono : undefined}>{value}</p>
    </div>
  );
}
