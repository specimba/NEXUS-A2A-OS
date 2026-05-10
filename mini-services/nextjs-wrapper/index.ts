import { spawn } from 'child_process'

console.log('[nextjs-wrapper] Starting Next.js dev server...')

const child = spawn('npx', ['next', 'dev', '-p', '3000'], {
  cwd: '/home/z/my-project',
  stdio: 'inherit',
  env: { ...process.env },
})

child.on('exit', (code) => {
  console.log(`[nextjs-wrapper] Next.js exited with code ${code}. Restarting in 3s...`)
  setTimeout(() => {
    spawn('npx', ['next', 'dev', '-p', '3000'], {
      cwd: '/home/z/my-project',
      stdio: 'inherit',
      env: { ...process.env },
    })
  }, 3000)
})

// Keep the process alive
setInterval(() => {
  // heartbeat
}, 60000)

console.log('[nextjs-wrapper] Wrapper started, PID:', process.pid)
