import { readdir, readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import pg from 'pg';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'migrations');
const url = process.env.DATABASE_URL;
if (!url) {
  console.error('DATABASE_URL must be set');
  process.exit(1);
}

const client = new pg.Client({ connectionString: url });
await client.connect();
for (const file of (await readdir(dir)).filter((f) => f.endsWith('.sql')).sort()) {
  process.stdout.write(`  ${file} … `);
  await client.query(await readFile(join(dir, file), 'utf8'));
  console.log('ok');
}
await client.end();
console.log('\n  migrations applied\n');
