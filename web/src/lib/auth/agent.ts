import { one } from '../db';
import { hash } from '../ids';

export interface Device { id: string; account_id: string; name: string }

/**
 * Identify the machine behind an agent request.
 *
 * The token is only ever stored hashed, so a dump of the devices table cannot
 * be replayed against the API.
 */
export async function deviceFromRequest(request: Request): Promise<Device | null> {
  const header = request.headers.get('authorization') ?? '';
  const token = header.startsWith('Bearer ') ? header.slice(7).trim() : '';
  if (!token) return null;

  const device = await one<Device>(
    'SELECT id, account_id, name FROM devices WHERE token_hash = $1',
    [hash(token)],
  );
  if (device) {
    await one('UPDATE devices SET last_seen = now() WHERE id = $1', [device.id]);
  }
  return device;
}
