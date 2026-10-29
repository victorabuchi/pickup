import Link from 'next/link';
import styles from './page.module.css';
import CopyCommand from '@/components/CopyCommand';

export default function Landing() {
  return (
    <div className={styles.page}>
      <header className={styles.nav}>
        <div className={`${styles.wrap} ${styles.navInner}`}>
          <a className={styles.navLogo} href="/"><span className={styles.mark}>p</span>Pickup</a>
          <nav className={styles.navLinks}>
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#privacy">Privacy</a>
            <a href="#pricing">Pricing</a>
          </nav>
          <div className={styles.navActions}>
            <Link className={styles.btnGhost} href="/login">Sign in</Link>
            <Link className={styles.btnPrimary} href="/login?new=1">Get started</Link>
          </div>
        </div>
      </header>

      <section className={styles.hero}>
        <div className={`${styles.wrap} ${styles.heroInner}`}>
          <span className={styles.eyebrow}>For people with too many projects</span>
          <h1>Pick up <span>where you left off.</span></h1>
          <p className={styles.heroLede}>
            Every project on your machine, in one place — what state it's in, what you
            left uncommitted, and what you were actually trying to do. Not a commit
            message. Your own words.
          </p>
          <div className={styles.heroCtas}>
            <a className={styles.btnLight} href="/login?new=1">Start free</a>
            <a className={styles.btnOutline} href="#how">See how it works</a>
          </div>
          <CopyCommand className={styles.cmd} command="brew install pickup && pickup login" />
        </div>
      </section>

      <section className={styles.section} id="why">
        <div className={styles.wrap}>
          <div className={styles.head}>
            <h2>You don't forget projects. You forget where you were in them.</h2>
            <p>
              Twenty-eight folders. You open one and lose twenty minutes working out
              what it is, whether it still runs, and what you were in the middle of.
              The answer was always on your disk — just never in one place.
            </p>
          </div>
          <div className={styles.split}>
            <div>
              <h2>GitHub can't see this.</h2>
              <p>
                A commit says what you <em>finished</em>. Pickup shows what you were
                <em>in the middle of</em> — the four files you edited but never staged,
                the branch you forgot, the question you asked twenty minutes before
                you walked away.
              </p>
              <ul className={styles.ticks}>
                <li><span className={styles.tick}>✓</span> Uncommitted work, before it ever reaches a remote</li>
                <li><span className={styles.tick}>✓</span> Projects with no git at all</li>
                <li><span className={styles.tick}>✓</span> Your own prompts, quoted back with timestamps</li>
                <li><span className={styles.tick}>✓</span> Folders that have quietly been dead for months</li>
              </ul>
            </div>
            <div className={styles.shot}>
              <div className={styles.shotBar}><i></i><i></i><i></i></div>
              <div className={styles.shotRow}><span className={`${styles.shotDot} ${styles['sd-green']}`}></span><b>statiku</b> 39 commits <span className={styles.shotNote}>"why is the realtime count stuck at 0"</span></div>
              <div className={styles.shotRow}><span className={`${styles.shotDot} ${styles['sd-green']}`}></span><b>notchlight</b> 1 uncommitted <span className={styles.shotNote}>4d ago</span></div>
              <div className={styles.shotRow}><span className={`${styles.shotDot} ${styles['sd-amber']}`}></span><b>storeshell</b> 4 uncommitted <span className={styles.shotNote}>1mo ago</span></div>
              <div className={styles.shotRow}><span className={`${styles.shotDot} ${styles['sd-grey']}`}></span><b>protos</b> no git <span className={styles.shotNote}>dead · 120d</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.sectionAlt}`} id="how">
        <div className={styles.wrap}>
          <div className={styles.head}>
            <h2>Connected in about a minute</h2>
            <p>No per-repository setup. No webhooks. No pasting tokens into forms.</p>
          </div>
          <div className={styles.steps}>
            <div className={styles.step}>
              <div className={styles.stepNum}>1</div>
              <h3>Install the agent</h3>
              <p>A small command-line tool. It runs on your machine and reads your folders — nothing is uploaded yet.</p>
              <code>brew install pickup</code>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNum}>2</div>
              <h3>Sign in once</h3>
              <p>Opens your browser, you approve the device, done. The same flow as the GitHub CLI — no tokens to copy.</p>
              <code>pickup login</code>
            </div>
            <div className={styles.step}>
              <div className={styles.stepNum}>3</div>
              <h3>Choose what to sync</h3>
              <p>It finds your projects and asks which to include. Everything else stays invisible — and you can untrack any project later in one click.</p>
              <code>pickup connect ~/Projects</code>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section} id="features">
        <div className={styles.wrap}>
          <div className={styles.head}>
            <h2>Built for the way you actually work</h2>
            <p>Several machines, too many side projects, and a memory that resets every Monday.</p>
          </div>
          <div className={styles.features}>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>⌘</div>
              <h3>One view, every machine</h3>
              <p>Laptop, desktop, work machine. Projects from all of them in a single dashboard, merged and deduplicated.</p>
            </div>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>↩</div>
              <h3>Resume instantly</h3>
              <p>Open a project and see its last commits, the files you touched, and the exact questions you were asking. Context restored in seconds.</p>
            </div>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>⚑</div>
              <h3>Nothing slips</h3>
              <p>Uncommitted work and stale branches surfaced before they turn into a conflict you have to untangle.</p>
            </div>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>✕</div>
              <h3>Untrack anything</h3>
              <p>Experiments, clones, scratch folders. One click to stop tracking, one to bring it back. Your dashboard stays yours.</p>
            </div>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>◷</div>
              <h3>What did I do last week</h3>
              <p>A real answer, assembled from real activity. Useful for standups, invoices, and your own sanity.</p>
            </div>
            <div className={styles.feature}>
              <div className={styles.featureIcon}>⇄</div>
              <h3>Works without git</h3>
              <p>Design files, scratch directories, half-started ideas. If it's a folder you work in, it shows up.</p>
            </div>
          </div>
        </div>
      </section>

      <section className={`${styles.section} ${styles.sectionAlt}`} id="privacy">
        <div className={`${styles.wrap} ${styles.split}`}>
          <div>
            <h2>Your code never leaves your machine.</h2>
            <p>
              Pickup syncs facts <em>about</em> your work, not the work itself. File
              names and timestamps, commit subjects, counts. Never file contents,
              never a diff, never a key.
            </p>
            <ul className={styles.ticks}>
              <li><span className={styles.tick}>✓</span> Opt in per folder — nothing syncs until you say so</li>
              <li><span className={styles.tick}>✓</span> Prompt history stays local unless you switch it on</li>
              <li><span className={styles.tick}>✓</span> Data stored in the EU</li>
              <li><span className={styles.tick}>✓</span> Local-only mode: run the dashboard with no account at all</li>
              <li><span className={styles.tick}>✓</span> Delete everything with one command</li>
            </ul>
          </div>
          <div className={styles.shot}>
            <div className={styles.shotBar}><i></i><i></i><i></i></div>
            <div className={styles.shotRow}><b style={{ color: "#7f88b5" }}>sent</b> project name, status, counts</div>
            <div className={styles.shotRow}><b style={{ color: "#7f88b5" }}>sent</b> commit subjects, file paths</div>
            <div className={styles.shotRow}><b style={{ color: "#7f88b5" }}>never</b> file contents or diffs</div>
            <div className={styles.shotRow}><b style={{ color: "#7f88b5" }}>never</b> environment files or keys</div>
            <div className={styles.shotRow}><b style={{ color: "#7f88b5" }}>optional</b> your prompt history</div>
          </div>
        </div>
      </section>

      <section className={styles.section} id="pricing">
        <div className={styles.wrap}>
          <div className={styles.head}>
            <h2>Free for one machine, forever</h2>
            <p>The local dashboard needs no account at all. Pay only when you want it in more than one place.</p>
          </div>
          <div className={styles.prices}>
            <div className={styles.price}>
              <span className={styles.priceName}>Local</span>
              <div className={styles.priceTag}>€0</div>
              <ul>
                <li><span className={styles.tick}>✓</span> Full dashboard on one machine</li>
                <li><span className={styles.tick}>✓</span> Unlimited projects</li>
                <li><span className={styles.tick}>✓</span> No account required</li>
                <li><span className={styles.tick}>✓</span> Open source agent</li>
              </ul>
              <a className={styles.btnGhost} href="#how">Install</a>
            </div>
            <div className={`${styles.price} ${styles.mid}`}>
              <span className={styles.priceName}>Pro</span>
              <div className={styles.priceTag}>€6 <small>/ month</small></div>
              <ul>
                <li><span className={styles.tick}>✓</span> Every machine in one view</li>
                <li><span className={styles.tick}>✓</span> History and weekly recaps</li>
                <li><span className={styles.tick}>✓</span> Prompt search across projects</li>
                <li><span className={styles.tick}>✓</span> Stale work reminders</li>
              </ul>
              <a className={styles.btnPrimary} href="/login?new=1">Start free trial</a>
            </div>
            <div className={styles.price}>
              <span className={styles.priceName}>Team</span>
              <div className={styles.priceTag}>€9 <small>/ person</small></div>
              <ul>
                <li><span className={styles.tick}>✓</span> See what the team is mid-way through</li>
                <li><span className={styles.tick}>✓</span> Standups assembled automatically</li>
                <li><span className={styles.tick}>✓</span> Shared project directory</li>
                <li><span className={styles.tick}>✓</span> SSO and self-hosting</li>
              </ul>
              <a className={styles.btnGhost} href="/login?new=1">Talk to us</a>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.cta}>
        <div className={styles.wrap}>
          <h2>Stop re-reading your own code to remember what you meant.</h2>
          <p>Install it, open the dashboard, and see all of it at once.</p>
          <a className={styles.btnLight} href="/login?new=1">Get started free</a>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={`${styles.wrap} ${styles.footInner}`}>
          <a className={styles.navLogo} href="/" style={{ fontSize: 15 }}><span className={styles.mark} style={{ width: 22, height: 22, fontSize: 12 }}>p</span>Pickup</a>
          <span>© 2026</span>
          <nav>
            <a href="#privacy">Privacy</a>
            <a href="#pricing">Pricing</a>
            <a href="https://github.com/victorabuchi/pickup">GitHub</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
