const { spawn, execSync } = require('child_process');
const path = require('path');

let child = null;
let restartCount = 0;
const MAX_RESTARTS = 1000;

function killExisting() {
  try {
    execSync('pkill -f "server.js" 2>/dev/null || true', { timeout: 2000 });
  } catch {}
  try {
    execSync('fuser -k 3000/tcp 2>/dev/null || true', { timeout: 2000 });
  } catch {}
}

function startServer() {
  if (restartCount >= MAX_RESTARTS) {
    console.error('Max restarts reached');
    process.exit(1);
  }
  restartCount++;
  
  killExisting();
  
  console.log(`[${new Date().toISOString()}] Starting server (attempt ${restartCount})...`);
  
  child = spawn('bun', ['.next/standalone/server.js'], {
    cwd: '/home/z/my-project',
    env: { 
      ...process.env, 
      HOSTNAME: '0.0.0.0',
      PORT: '3000'
    },
    stdio: 'inherit'
  });
  
  child.on('exit', (code, signal) => {
    console.log(`[${new Date().toISOString()}] Server exited (code=${code}, signal=${signal}). Restarting in 1s...`);
    child = null;
    setTimeout(startServer, 1000);
  });
  
  child.on('error', (err) => {
    console.error(`[${new Date().toISOString()}] Server error: ${err.message}. Restarting in 1s...`);
    child = null;
    setTimeout(startServer, 1000);
  });
}

// Handle supervisor shutdown
process.on('SIGTERM', () => {
  if (child) child.kill();
  process.exit(0);
});

process.on('SIGINT', () => {
  if (child) child.kill();
  process.exit(0);
});

startServer();
