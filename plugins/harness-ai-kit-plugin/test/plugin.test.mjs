import assert from 'node:assert/strict'

const indexUrl = new URL('../src/index.js', import.meta.url)
const mod = await import(indexUrl)

const registeredTools = []
const registeredSkills = []
const registeredProviders = []
const ctx = {
  tools: { register: (definition) => { registeredTools.push(definition); return () => {} } },
  skills: { register: (skill) => { registeredSkills.push(skill); return () => {} } },
  skills2: null,
}
ctx.skills.registerProvider = (create) => {
  registeredProviders.push(create({ signal: new AbortController().signal, invalidate: () => {} }))
  return () => {}
}

// Hermetic config: no reachable registry and a CLI command that is not on PATH,
// so every action degrades to a controlled failure without network or a real CLI.
const pluginConfig = {
  cliCommand: 'harness-ai-kit-cli-not-present',
  skillRegistryIndexUrl: '',
  cliRegistryIndexUrl: '',
  defaultProfile: 'web',
}

mod.apply(ctx, pluginConfig)

// --- registration & structure (hermetic) ---
assert.equal(mod.name, 'harness-ai-kit-plugin')
assert.deepEqual(mod.inject.sort(), ['skills', 'tools'])
assert.equal(registeredTools.length, 1)
assert.equal(registeredSkills.length, 1)
assert.equal(registeredProviders.length, 1)

const tool = registeredTools[0]
assert.equal(tool.name, 'harness-ai-kit')
assert.equal(tool.parameters.type, 'object')
assert.ok(Array.isArray(tool.parameters.properties.action.enum))
assert.equal(typeof tool.execute, 'function')
assert.equal(typeof tool.output.render, 'function')

const skill = registeredSkills[0]
assert.equal(skill.name, 'harness-ai-kit-ops')
assert.equal(skill.source, 'bundled')
assert.equal(skill.provider, 'harness-ai-kit-plugin')
assert.ok(skill.content.includes('harness-ai-kit'))
assert.equal(skill.resourceBase.kind, 'directory')

const provider = registeredProviders[0]
assert.equal(provider.name, 'harness-ai-kit-registry')
assert.equal(typeof provider.list, 'function')
assert.equal(typeof provider.get, 'function')

// --- render returns text content blocks (hermetic) ---
const blocks = tool.output.render({ action: 'list' }, { ok: true, output: [] })
assert.equal(blocks[0].type, 'text')

// --- no registry URL configured -> controlled failure via the guard (hermetic) ---
const listResult = await tool.execute({ action: 'list', assetType: 'skill' }, {})
assert.equal(listResult.ok, false)
assert.ok(typeof listResult.error === 'string')
assert.ok(listResult.error.includes('registry index URL'))

// --- install with no CLI on PATH and no registry -> controlled failure (hermetic) ---
const installResult = await tool.execute(
  { action: 'install', assetType: 'skill', assetId: 'harness-ai-kit-ops', runtime: 'dsh' },
  {},
)
assert.equal(installResult.ok, false)
assert.ok(typeof installResult.error === 'string')

console.log('plugin.test.mjs: OK (hermetic)')
