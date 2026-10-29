'use client';

import { useState } from 'react';

export default function CopyCommand({ command, className }: { command: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <div className={className}>
      <span>$</span>
      <span>{command}</span>
      <button
        type="button"
        onClick={() => {
          navigator.clipboard?.writeText(command);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        }}
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}
