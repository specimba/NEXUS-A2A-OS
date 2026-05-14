const { spawn } = require('child_process');
const path = require('path');

function startServer() {
  console.log(`[${new Date().toISOString()}] Starting server...`);
  
  const child = spawn('node', ['.next/standalone/server.js'], {
    cwd: '/home/z/my-project',
    env: { 
      ...process.env, 
      NODE_OPTIONS: '--max-old-space-size=512',
      HOSTNAME: '0.0.0.0',
      PORT: '3000'
    },
    stdio: 'inherit'
  });
  
  child.on('exit', (code, signal) => {
    console.log(`[${new Date().toISOString()}] Server exited with code ${code}, signal ${signal}. Restarting in 2s...`);
    setTimeout(startServer, 2000);
  });
  
  child.on('error', (err) => {
    console.error(`[${new Date().toISOString()}] Server error: ${err.message}. Restarting in 2s...`);
    setTimeout(startServer, 2000);
  });
}

startServer();
