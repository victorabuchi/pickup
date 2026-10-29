import { NextResponse } from 'next/server';
import { destroySession } from '@/lib/auth/session';

export async function POST(): Promise<NextResponse> {
  await destroySession();
  return NextResponse.json({ ok: true });
}
