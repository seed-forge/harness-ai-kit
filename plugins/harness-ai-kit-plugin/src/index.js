/**
 * harness-ai-kit dsh plugin (bundle).
 *
 * Registers one tool (`harness-ai-kit`) that delegates to the local CLI, with
 * an HTTP fallback that reads the registry index directly. Also registers the
 * packaged `harness-ai-kit-ops` skill through ctx.skills (source: bundled) so
 * `dsh plugin add` delivers both capability and knowledge in one step.
 *
 * Ships plain JavaScript + Markdown: no prepare/install scripts, no build step.
 */

import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const SKILL_FILE_URL = new URL('../skills/harness-ai-kit-ops/SKILL.md', import.meta.url)
const SKILL_FILE = fileURLToPath(SKILL_FILE_URL)
const SKILL_DIRECTORY = dirname(SKILL_FILE)
const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/
const VIRTUAL_SKILL_RANK = 650

export const name = 'harness-ai-kit-plugin'
export const inject = ['tools', 'skills']

function readFrontmatterScalar(frontmatter, key) {
  const line = frontmatter.split(/\r?\n/).find((candidate) => candidate.startsWith(`${key}:`))
  if (line === undefined) throw new Error(`harness-ai-kit-plugin: packaged SKILL.md has no ${key}`)
  const value = line.slice(key.length + 1).trim()
  if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replaceAll("''", "'")
  if (value.startsWith('"') && value.endsWith('"')) return JSON.parse(value)
  if (value === '') throw new Error(`harness-ai-kit-plugin: packaged SKILL.md has an empty ${key}`)
  return value
}

function readSkill() {
  const source = readFileSync(SKILL_FILE, 'utf8').replace(/^\uFEFF/, '')
  const match = FRONTMATTER.exec(source)
  if (match === null) throw new Error('harness-ai-kit-plugin: packaged SKILL.md has no valid frontmatter block')
  return {
    name: readFrontmatterScalar(match[1], 'name'),
    description: readFrontmatterScalar(match[1], 'description'),
    content: source.slice(match[0].length).replace(/^\r?\n/, ''),
  }
}

function runCli(cliCommand, args) {
  const proc = spawnSync(cliCommand, args, { encoding: 'utf8', timeout: 60000, windowsHide: true })
  if (proc.error) return { ok: false, error: String(proc.error.message || proc.error) }
  if (proc.status !== 0) {
    const detail = (proc.stderr || proc.stdout || '').trim().split('\n').slice(-3).join('\n')
    return { ok: false, error: detail || `exit ${proc.status}` }
  }
  try {
    return { ok: true, output: JSON.parse(proc.stdout) }
  } catch {
    return { ok: true, output: proc.stdout }
  }
}

async function readRegistryIndex(indexUrl) {
  const response = await fetch(indexUrl, { signal: AbortSignal.timeout(15000) })
  if (!response.ok) throw new Error(`registry index ${indexUrl} -> HTTP ${response.status}`)
  return response.json()
}

function filterEntries(entries, query) {
  const needle = String(query || '').toLowerCase()
  if (!needle) return entries
  return entries.filter((entry) =>
    [entry.id, entry.name, entry.summary, entry.description, entry.npm_name]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(needle)),
  )
}

async function listAssets(config, assetType) {
  if (assetType === 'cli' || assetType === 'plugin') {
    const index = await readRegistryIndex(config.cliRegistryIndexUrl)
    const section = assetType === 'plugin' ? index.plugins || [] : index.clis || []
    return section.map((entry) => ({
      id: entry.id,
      name: entry.name,
      version: entry.latest_version,
      status: entry.status,
      summary: entry.summary || '',
      package_type: entry.package_type || (assetType === 'plugin' ? 'plugin' : 'cli'),
    }))
  }
  const index = await readRegistryIndex(config.skillRegistryIndexUrl)
  const skills = index.skills || []
  return skills.map((entry) => ({
    id: entry.canonical_id || entry.id,
    name: entry.name || entry.canonical_id || entry.id,
    version: entry.latest_version,
    status: entry.status,
    summary: entry.summary || entry.description || '',
  }))
}

async function infoAsset(config, assetType, assetId) {
  const entries = await listAssets(config, assetType || 'skill')
  const hit = entries.find((entry) => entry.id === assetId)
  if (!hit) throw new Error(`${assetType || 'skill'} ${assetId} not found in registry`)
  return hit
}

async function executeAction(config, action, args) {
  switch (action) {
    case 'list': {
      const entries = await listAssets(config, args.assetType)
      return { ok: true, output: entries }
    }
    case 'search': {
      const entries = await listAssets(config, args.assetType)
      return { ok: true, output: filterEntries(entries, args.query) }
    }
    case 'info': {
      const entry = await infoAsset(config, args.assetType, args.assetId)
      return { ok: true, output: entry }
    }
    case 'install':
      return runCli(config.cliCommand, [
        'install',
        args.assetType || 'skill',
        args.assetId,
        '--runtime',
        args.runtime || 'codex',
        '--scope',
        args.scope || 'project',
        ...(args.profile ? ['--profile', args.profile] : []),
      ])
    case 'doctor':
      return runCli(config.cliCommand, ['doctor', args.subject || 'dsh'])
    default:
      throw new Error(`unknown action: ${action}`)
  }
}

function textBlock(text) {
  return [{ type: 'text', text: String(text) }]
}

function renderResult(args, value) {
  if (value && typeof value === 'object' && 'ok' in value) {
    if (value.ok) return textBlock(JSON.stringify(value.output, null, 2))
    return textBlock(`harness-ai-kit ${args.action} failed: ${value.error}`)
  }
  return textBlock(JSON.stringify(value, null, 2))
}

function extractSkillSummary(payload) {
  const frontmatter = FRONTMATTER.exec(payload)
  if (!frontmatter) return { name: '', description: '' }
  const block = frontmatter[1]
  const scalar = (key) => {
    const line = block.split(/\r?\n/).find((candidate) => candidate.startsWith(`${key}:`))
    if (line === undefined) return ''
    return line.slice(key.length + 1).trim().replace(/^['"]|['"]$/g, '')
  }
  return { name: scalar('name'), description: scalar('description') }
}

function createSkillProvider(config) {
  return {
    name: 'harness-ai-kit-registry',
    async list(options) {
      try {
        const index = await readRegistryIndex(config.skillRegistryIndexUrl)
        const skills = index.skills || []
        const candidates = []
        for (const entry of skills) {
          const canonical = entry.canonical_id || entry.id
          if (!canonical) continue
          candidates.push({
            name: canonical,
            description: entry.description || entry.summary || '',
            invocation: { modelInvocable: true, userInvocable: true },
            source: 'custom',
            provider: this.name,
            rank: VIRTUAL_SKILL_RANK,
            locator: { canonicalId: canonical, version: entry.latest_version },
            metadata: { virtual: true },
          })
        }
        return { candidates, complete: true }
      } catch (error) {
        // 网络/鉴权失败：返回空观测且不缓存（design.md 4.4 降级语义）
        return { candidates: [], complete: false }
      }
    },
    async get(candidate) {
      try {
        const locator = candidate.locator || {}
        const canonicalId = locator.canonicalId || candidate.name
        const version = locator.version || ''
        const index = await readRegistryIndex(config.skillRegistryIndexUrl)
        const skills = index.skills || []
        const entry = skills.find((item) => (item.canonical_id || item.id) === canonicalId)
        if (!entry) return undefined
        const versions = Array.isArray(entry.versions) ? entry.versions : []
        const selected = version ? versions.find((v) => v.version === version) : versions[versions.length - 1]
        const artifactUrl = selected && selected.artifact_url
        if (!artifactUrl) return undefined
        const response = await fetch(artifactUrl, { signal: AbortSignal.timeout(15000) })
        if (!response.ok) return undefined
        const payload = await response.text()
        const summary = extractSkillSummary(payload)
        return {
          name: summary.name || canonicalId,
          description: summary.description || entry.description || entry.summary || '',
          invocation: { modelInvocable: true, userInvocable: true },
          source: 'custom',
          provider: this.name,
          resourceBase: { kind: 'url', url: artifactUrl },
          content: payload,
          metadata: { virtual: true },
        }
      } catch {
        return undefined
      }
    },
  }
}

export function apply(ctx, pluginConfig = {}) {
  const config = {
    cliCommand: pluginConfig.cliCommand || 'harness-ai-kit',
    skillRegistryIndexUrl:
      pluginConfig.skillRegistryIndexUrl || 'https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/skills/index.json',
    cliRegistryIndexUrl:
      pluginConfig.cliRegistryIndexUrl || 'https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/clis/index.json',
    defaultProfile: pluginConfig.defaultProfile || 'web',
  }

  ctx.tools.register({
    name: 'harness-ai-kit',
    description:
      '查询与安装团队资产（skill/cli/plugin/loop/mcp/hook/subagent）。动作：list（列目录）、search（按关键词）、info（看详情）、install（安装）、doctor（环境检查）。优先委托本机 harness-ai-kit CLI；CLI 缺失时直读 registry index。',
    parameters: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['list', 'search', 'info', 'install', 'doctor'], description: '要执行的动作' },
        assetType: { type: 'string', enum: ['skill', 'cli', 'plugin', 'loop', 'mcp', 'hook', 'subagent'], description: '资产类型（list/search/info/install 使用）' },
        assetId: { type: 'string', description: '资产 ID（info/install 使用）' },
        query: { type: 'string', description: 'search 关键词' },
        runtime: { type: 'string', enum: ['codex', 'dsh', 'claude-code', 'kiro', 'cursor', 'opencode', 'qoder'], description: 'install 的目标 runtime' },
        scope: { type: 'string', enum: ['project', 'global'], description: 'install 的作用域' },
        profile: { type: 'string', description: 'install plugin 的 dsh profile' },
        subject: { type: 'string', description: 'doctor 检查项（dsh/versions/...）' },
      },
      required: ['action'],
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: renderResult,
    },
    execute: async (args) => {
      try {
        return await executeAction(config, args.action, args)
      } catch (error) {
        return { ok: false, error: String(error && error.message ? error.message : error) }
      }
    },
  })

  const skill = readSkill()
  ctx.skills.register({
    ...skill,
    source: 'bundled',
    provider: name,
    resourceBase: { kind: 'directory', path: SKILL_DIRECTORY },
    path: SKILL_FILE,
  })

  // Phase E：虚拟技能 SkillProvider（E0b 已确认 registerProvider 存在于 0.1.0-rc.6）
  // list 只回元数据（rank 650 < 本地根 → 本地优先），get 按需拉正文，不落盘。
  ctx.skills.registerProvider((control) => createSkillProvider(config))
}
