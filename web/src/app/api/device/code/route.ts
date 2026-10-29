import { NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { deviceCode } from '@/lib/ids';
import { DEVICE_CODE_MINUTES } from '@/lib/auth/constants';

/** The agent asks for a code, then shows it to the person to type in a browser. */
export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json().catch(() => ({}))) as {
    deviceName?: string;
    platform?: string;
  };

  const code = deviceCode();
  await query(
    `INSERT INTO device_codes (code, device_name, platform, expires_at)
     VALUES ($1, $2, $3, now() + ($4 || ' minutes')::interval)`,
    [code, String(body.deviceName ?? 'this machine').slice(0, 80),
     String(body.platform ?? '').slice(0, 40), String(DEVICE_CODE_MINUTES)],
  );

  return NextResponse.json({
    code,
    verifyUrl: `${process.env['APP_URL'] ?? ''}/login?code=${encodeURIComponent(code)}`,
    expiresInMinutes: DEVICE_CODE_MINUTES,
  });
}
