import { spawn } from 'child_process';

function startServer() {
  const log = (msg) => console.log(`[${new Date().toISOString()}] ${msg}`);
  
  log('Starting NEXUS-OS lightweight server...');
  
  const child = spawn('node', ['lightweight-server.mjs'], {
    cwd: '/home/z/my-project',
    env: { ...process.env, PORT: '3000' },
    stdio: ['ignore', 'inherit', 'inherit']
  });
  
  child.on('exit', (code, signal) => {
    log(`Server exited (code=${code}, signal=${signal}). Restarting in 1s...`);
    setTimeout(startServer, 1000);
  });
  
  child.on('error', (err) => {
    log(`Server error: ${err.message}. Restarting in 1s...`);
    setTimeout(startServer, 1000);
  });
}

startServer();
