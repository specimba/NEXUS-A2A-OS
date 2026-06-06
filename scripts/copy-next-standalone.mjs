import { cpSync, mkdirSync } from 'fs';
import { join } from 'path';

const projectRoot = join(import.meta.dirname, '..');
const standaloneDir = join(projectRoot, '.next', 'standalone');
const nextDir = join(standaloneDir, '.next');

// Ensure .next/standalone/.next exists
mkdirSync(nextDir, { recursive: true });

// Copy static files
cpSync(join(projectRoot, '.next', 'static'), join(nextDir, 'static'), { recursive: true });

// Copy public folder
cpSync(join(projectRoot, 'public'), join(standaloneDir, 'public'), { recursive: true });

// Copy prisma schema and db
try {
  cpSync(join(projectRoot, 'prisma'), join(standaloneDir, 'prisma'), { recursive: true });
} catch {}

// Copy db folder
try {
  cpSync(join(projectRoot, 'db'), join(standaloneDir, 'db'), { recursive: true });
} catch {}

// Copy .env
try {
  cpSync(join(projectRoot, '.env'), join(standaloneDir, '.env'));
} catch {}

console.log('✓ Standalone files copied successfully');
