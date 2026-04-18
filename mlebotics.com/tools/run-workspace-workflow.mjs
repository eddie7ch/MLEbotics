import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')
const nodeExec = process.execPath

const astroBin = 'apps/marketing/node_modules/astro/astro.js'
const nextConsoleBin = 'apps/console/node_modules/next/dist/bin/next'
const nextStudioBin = 'apps/studio/node_modules/next/dist/bin/next'
const nextDocsBin = 'apps/docs/node_modules/next/dist/bin/next'
const tscBin = 'node_modules/typescript/bin/tsc'

const workflows = {
  build: [
    { label: 'marketing', cwd: 'apps/marketing', script: astroBin, args: ['build'] },
    { label: 'console', cwd: 'apps/console', script: nextConsoleBin, args: ['build'] },
    { label: 'studio', cwd: 'apps/studio', script: nextStudioBin, args: ['build'] },
    { label: 'docs', cwd: 'apps/docs', script: nextDocsBin, args: ['build'] },
  ],
  lint: [
    { label: 'console', cwd: 'apps/console', script: nextConsoleBin, args: ['lint'] },
    { label: 'studio', cwd: 'apps/studio', script: nextStudioBin, args: ['lint'] },
  ],
  typecheck: [
    { label: 'console', cwd: 'apps/console', script: tscBin, args: ['--noEmit'] },
    { label: 'docs', cwd: 'apps/docs', script: tscBin, args: ['--noEmit'] },
    { label: 'studio', cwd: 'apps/studio', script: tscBin, args: ['--noEmit'] },
    { label: 'platform', cwd: 'platform', script: tscBin, args: ['--noEmit'] },
    { label: 'packages/api', cwd: 'packages/api', script: tscBin, args: ['--noEmit'] },
    { label: 'packages/sdk-js', cwd: 'packages/sdk-js', script: tscBin, args: ['--noEmit'] },
    { label: 'packages/ui', cwd: 'packages/ui', script: tscBin, args: ['--noEmit'] },
    { label: 'packages/utils', cwd: 'packages/utils', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/agents', cwd: 'robotics/agents', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/agents/edge-agent', cwd: 'robotics/agents/edge-agent', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/agents/robot-agent', cwd: 'robotics/agents/robot-agent', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/adapters/mqtt-bridge', cwd: 'robotics/adapters/mqtt-bridge', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/adapters/ros2-bridge', cwd: 'robotics/adapters/ros2-bridge', script: tscBin, args: ['--noEmit'] },
    { label: 'robotics/adapters/rtsp-bridge', cwd: 'robotics/adapters/rtsp-bridge', script: tscBin, args: ['--noEmit'] },
  ],
}

const workflowName = process.argv[2]
const commands = workflows[workflowName]

if (!commands) {
  console.error(`Unknown workflow: ${workflowName}`)
  process.exit(1)
}

function resolveScript(scriptPath) {
  const resolved = path.resolve(repoRoot, scriptPath)
  if (!fs.existsSync(resolved)) {
    throw new Error(`Missing CLI entrypoint: ${resolved}`)
  }
  return resolved
}

function findLintConfig(startDir) {
  const configNames = [
    'eslint.config.js',
    'eslint.config.cjs',
    'eslint.config.mjs',
    '.eslintrc',
    '.eslintrc.js',
    '.eslintrc.cjs',
    '.eslintrc.json',
    '.eslintrc.yaml',
    '.eslintrc.yml',
  ]

  let currentDir = startDir
  while (true) {
    for (const configName of configNames) {
      if (fs.existsSync(path.join(currentDir, configName))) {
        return true
      }
    }

    if (currentDir === repoRoot) {
      return false
    }

    const parentDir = path.dirname(currentDir)
    if (parentDir === currentDir) {
      return false
    }

    currentDir = parentDir
  }
}

function runCommand(command) {
  const script = resolveScript(command.script)
  const cwd = path.resolve(repoRoot, command.cwd)

  if (workflowName === 'lint' && !findLintConfig(cwd)) {
    console.log(`\n==> ${command.label}`)
    console.log('Skipping lint: no ESLint config found.')
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    console.log(`\n==> ${command.label}`)

    const child = spawn(nodeExec, [script, ...command.args], {
      cwd,
      stdio: 'inherit',
      env: {
        ...process.env,
        FORCE_COLOR: '1',
      },
    })

    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) {
        resolve()
        return
      }

      reject(new Error(`${command.label} failed with exit code ${code}`))
    })
  })
}

try {
  for (const command of commands) {
    await runCommand(command)
  }

  console.log(`\n${workflowName} complete.`)
} catch (error) {
  console.error(`\n${error.message}`)
  process.exit(1)
}