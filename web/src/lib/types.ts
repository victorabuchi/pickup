export type Status = 'active' | 'stalled' | 'dead';

export interface Commit { hash: string; subject: string; author: string; ago: string; date: string }
export interface Edit { path: string; ago: string }
export interface Prompt { text: string; ago: string }

export interface ProjectDetail {
  touched?: string;
  newestFile?: string;
  subject?: string;
  size?: string;
  filesCount?: number;
  firstCommit?: string;
  age?: string;
  history?: Commit[];
  edits?: Edit[];
  prompts?: Prompt[];
}

export interface Project {
  id: string;
  name: string;
  path: string;
  status: Status;
  summary: string;
  stack: string[];
  branch: string;
  commits: number;
  dirty: number;
  hasGit: boolean;
  note: string;
  noteIsYours: boolean;
  lastActivity: string | null;
  ignored: boolean;
  deviceName: string;
  detail: ProjectDetail;
}
