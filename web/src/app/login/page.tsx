'use client';

import { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import styles from './login.module.css';

type Pane = 'email' | 'device';

function LoginInner() {
  const params = useSearchParams();
  const isNew = params.has('new');
  const pendingCode = params.get('code') ?? '';

  const [pane, setPane] = useState<Pane>(pendingCode ? 'device' : 'email');
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [code, setCode] = useState(pendingCode);
  const [deviceState, setDeviceState] = useState<'idle' | 'working' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');

  async function sendLink(event: React.FormEvent) {
    event.preventDefault();
    await fetch('/api/auth/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    setSent(true);
  }

  async function approve() {
    setDeviceState('working');
    const res = await fetch('/api/device/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (res.ok) {
      setDeviceState('done');
      return;
    }
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    // 401 means the browser is not signed in yet — that is the usual first run.
    setMessage(res.status === 401
      ? 'Sign in first, then approve the device.'
      : body.error ?? 'That did not work.');
    setDeviceState('error');
  }

  return (
    <div className={styles.box}>
      <Link className={styles.back} href="/">&larr; Back</Link>
      <h1>{isNew ? 'Create your account' : 'Sign in to Pickup'}</h1>
      <p className={styles.sub}>
        {isNew ? 'Free on one machine. No card needed.' : 'Pick up where you left off, on every machine.'}
      </p>

      <div className={styles.tabs} role="tablist">
        <button
          className={styles.tab} role="tab" aria-selected={pane === 'email'}
          onClick={() => setPane('email')}
        >
          Email
        </button>
        <button
          className={styles.tab} role="tab" aria-selected={pane === 'device'}
          onClick={() => setPane('device')}
        >
          From terminal
        </button>
      </div>

      {pane === 'email' ? (
        sent ? (
          <div className={styles.done}>
            <strong>Check your email</strong>
            <p>We sent a sign-in link to {email}. It expires in 20 minutes.</p>
          </div>
        ) : (
          <form onSubmit={sendLink}>
            <label htmlFor="email">Your email</label>
            <input
              id="email" type="email" required autoComplete="email"
              placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)}
            />
            <button className={styles.btnPrimary} type="submit">Send sign-in link</button>
          </form>
        )
      ) : (
        <div>
          <div className={styles.hintRow}>
            Run <code>pickup login</code> in your terminal, then type the code it shows.
          </div>
          <label htmlFor="code">Device code</label>
          <input
            id="code" type="text" placeholder="ABCD-EFGH" className={styles.code}
            value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
          />
          {deviceState === 'done' ? (
            <div className={styles.done}>
              <strong>Device connected</strong>
              <p>Your terminal will finish on its own. You can close this tab.</p>
            </div>
          ) : (
            <button
              className={styles.btnPrimary} type="button"
              onClick={approve} disabled={deviceState === 'working' || code.length < 8}
            >
              {deviceState === 'working' ? 'Connecting…' : 'Connect this device'}
            </button>
          )}
          {deviceState === 'error' && <p className={styles.error}>{message}</p>}
          <p className={styles.fine}>
            The agent never sends your code or file contents — only the facts shown on
            your dashboard. You choose which folders are included.
          </p>
        </div>
      )}

      <p className={styles.fine}>
        By continuing you agree to the terms and privacy policy. Prefer no account?
        Run it locally instead — the dashboard works offline, free, forever.
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className={styles.shell}>
      <aside className={styles.aside}>
        <Link className={styles.logo} href="/"><span className={styles.mark}>p</span>Pickup</Link>
        <div className={styles.asideMid}>
          <h2>Everything you were in the middle of, waiting for you.</h2>
          <p>Sign in to bring every machine into one dashboard. The local agent keeps working either way.</p>
          <div className={styles.mini}>
            <div className={styles.miniRow}><span className={`${styles.d} ${styles.g}`} /><b>statiku</b>39 commits<span className={styles.note}>2d ago</span></div>
            <div className={styles.miniRow}><span className={`${styles.d} ${styles.g}`} /><b>notchlight</b>1 uncommitted<span className={styles.note}>4d ago</span></div>
            <div className={styles.miniRow}><span className={`${styles.d} ${styles.a}`} /><b>storeshell</b>4 uncommitted<span className={styles.note}>1mo ago</span></div>
            <div className={styles.miniRow}><span className={`${styles.d} ${styles.x}`} /><b>protos</b>no git<span className={styles.note}>dead</span></div>
          </div>
        </div>
        <div className={styles.asideFoot}>Your code never leaves your machine. Metadata only, stored in the EU.</div>
      </aside>

      <div className={styles.main}>
        <Suspense fallback={null}>
          <LoginInner />
        </Suspense>
      </div>
    </main>
  );
}
