import { Pool, type QueryResultRow } from 'pg';

declare global {
  // Next reloads modules in dev; one pool per process, not per reload.
  // eslint-disable-next-line no-var
  var pickupPool: Pool | undefined;
}

function pool(): Pool {
  if (!globalThis.pickupPool) {
    const connectionString = process.env['DATABASE_URL'];
    if (!connectionString) throw new Error('DATABASE_URL must be set');
    globalThis.pickupPool = new Pool({
      connectionString,
      ssl: connectionString.includes('localhost') ? undefined : { rejectUnauthorized: false },
      max: 8,
    });
  }
  return globalThis.pickupPool;
}

export async function query<T extends QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const result = await pool().query<T>(text, params);
  return result.rows;
}

export async function one<T extends QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<T | null> {
  const rows = await query<T>(text, params);
  return rows[0] ?? null;
}
