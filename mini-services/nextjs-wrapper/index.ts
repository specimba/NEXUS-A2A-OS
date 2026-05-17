import { spawn } from 'child_process'

// Use production mode to avoid OOM from dev server compilation
const USE_PROD = true

console.log(`[nextjs-wrapper] Starting NEXUS-OS Next.js ${USE_PROD ? 'production' : 'dev'} server...`)

function startServer() {
  const args = USE_PROD
    ? ['node_modules/.bin/next', 'start', '-p', '3000']
    : ['node_modules/.bin/next', 'dev', '-p', '3000']
  const child = spawn('node', args, {
    cwd: '/home/z/my-project',
    stdio: 'inherit',
    env: { ...process.env },
  })

  child.on('exit', (code, signal) => {
    console.log(`[nextjs-wrapper] Server exited (code=${code}, signal=${signal}). Restarting in 3s...`)
    setTimeout(startServer, 3000)
  })

  child.on('error', (err) => {
    console.log(`[nextjs-wrapper] Server error: ${err.message}. Restarting in 3s...`)
    setTimeout(startServer, 3000)
  })
}

startServer()

// Keep the process alive
setInterval(() => {
  // heartbeat
}, 60000)

console.log('[nextjs-wrapper] Wrapper started, PID:', process.pid)
