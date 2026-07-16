import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

import { verifyRuntime } from './verify-runtime.mjs'

function takeValue(argv, index, flag) {
  const value = argv[index + 1]
  if (!value || value.startsWith('--')) throw new Error(`${flag} requires a value`)
  return value
}

export function parseRuntimeArgs(argv) {
  const parsed = {
    port: 7350,
    bind: '127.0.0.1',
    config: null,
    enableLog: false,
    allowedOrigins: null,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index]
    if (flag === '--port') parsed.port = Number(takeValue(argv, index++, flag))
    else if (flag === '--bind') parsed.bind = takeValue(argv, index++, flag)
    else if (flag === '--config') parsed.config = resolve(takeValue(argv, index++, flag))
    else if (flag === '--allowed-origins') parsed.allowedOrigins = takeValue(argv, index++, flag)
    else if (flag === '--log') parsed.enableLog = true
    else if (flag === '--no-log') parsed.enableLog = false
    else if (flag === '--help' || flag === '-h') parsed.help = true
    else throw new Error(`Unknown argument: ${flag}`)
  }
  if (!Number.isInteger(parsed.port) || parsed.port < 1 || parsed.port > 65535) {
    throw new Error(`Invalid port: ${String(parsed.port)}`)
  }
  return parsed
}

function printHelp() {
  process.stdout.write([
    'NEXUS governed ModelRelay runtime',
    '',
    'Usage: node src/cli.mjs [--port 7350] [--bind 127.0.0.1] [--config PATH]',
    '       [--allowed-origins CSV] [--log|--no-log]',
    '',
    'A non-loopback bind requires MODELRELAY_BEARER_TOKEN.',
  ].join('\n') + '\n')
}

async function validateConfig(path) {
  if (!path) return
  if (!existsSync(path)) throw new Error(`Config file does not exist: ${path}`)
  const parsed = JSON.parse(await readFile(path, 'utf8'))
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`Config must contain a JSON object: ${path}`)
  }
}

export async function run(argv = process.argv.slice(2)) {
  const args = parseRuntimeArgs(argv)
  if (args.help) {
    printHelp()
    return
  }
  await validateConfig(args.config)
  await verifyRuntime()

  process.env.MODELRELAY_NEXUS_SAFE_RUNTIME = '1'
  process.env.MODELRELAY_DISABLE_AUTO_UPDATE = '1'
  process.env.MODELRELAY_BIND = args.bind
  if (args.config) process.env.MODELRELAY_CONFIG_PATH = args.config
  if (args.allowedOrigins != null) process.env.MODELRELAY_ALLOWED_ORIGINS = args.allowedOrigins

  // These modules read runtime policy and config paths during import.
  const [{ loadConfig }, { runServer }] = await Promise.all([
    import('modelrelay/lib/config.js'),
    import('modelrelay/lib/server.js'),
  ])
  await runServer(loadConfig(), args.port, args.enableLog, [])
}

run().catch(error => {
  process.stderr.write(`NEXUS ModelRelay failed closed: ${error.message}\n`)
  process.exitCode = 1
})
