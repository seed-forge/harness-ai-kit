#!/usr/bin/env node
/**
 * tools/dashboard.js — E2E 全局交付度视图（通用化版，纯文件操作，不拉浏览器、不连 DB）
 * 用法: node tools/dashboard.js
 * 数据源: registry/*.yaml（功能点级权威）+ registry/modules.yaml（模块元信息）
 *         reports/<module>/SUMMARY.md 仅用于交叉校验
 * 输出: docs/e2e-dashboard.md + stdout 摘要（自动生成，勿手改）
 */
'use strict';
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const E2E = path.resolve(__dirname, '..');
const OUT = path.resolve(E2E, '../../docs/e2e-dashboard.md');
const warnings = [];

function readFileSafe(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (e) { return null; }
}
function loadYamlSafe(p) {
  const raw = readFileSafe(p);
  if (raw === null) return { doc: null, raw: null, missing: true };
  try { return { doc: yaml.load(raw), raw }; }
  catch (e) {
    warnings.push(`YAML 解析失败: ${path.relative(E2E, p)} —— ${String(e.message).split('\n')[0]}`);
    return { doc: null, raw };
  }
}

// 从原始文本按 "- id:" 切块收集注释（js-yaml 会丢注释，blocked 根因多写在注释/执行注里）
function commentBlocks(raw) {
  const blocks = [];
  let cur = null;
  for (const line of (raw || '').split(/\r?\n/)) {
    const m = line.match(/^\s*-\s+id:\s*([\w.-]+)/);
    if (m) { cur = { id: m[1], comments: [] }; blocks.push(cur); continue; }
    if (!cur) continue;
    const cm = line.match(/#\s*(.+)$/);
    if (cm && !/^=+/.test(cm[1])) cur.comments.push(cm[1].trim());
  }
  return blocks;
}

// blocked 根因五分类（与五分类路由表对齐；按项目调整正则）
const CATEGORIES = [
  ['数据类', /数据|造数|seed|字典|建表|表缺|表未建|空表|档案/i],
  ['权限类', /权限|管理员|角色/i],
  ['环境类', /环境|网关|部署|schema|路由抖动|冷加载/i],
  ['后端类', /后端|500|ORA-|mapper|存储过程|假成功|接口|服务/i],
  ['前端类', /前端|框架|组件|TypeError|render|坏链/i],
];
function classify(text) {
  for (const [name, re] of CATEGORIES) if (re.test(text)) return name;
  return '其他';
}

// -------- 聚合 --------
const regDir = path.join(E2E, 'registry');
const modulesFile = path.join(regDir, 'modules.yaml');
const { doc: modulesDoc, raw: modulesRaw } = loadYamlSafe(modulesFile);
const modulesMeta = new Map();
for (const m of (modulesDoc && modulesDoc.modules) || []) modulesMeta.set(m.id, m);

const rows = [];
const totals = { pass: 0, fail: 0, blocked: 0, todo: 0 };
const blockedByCat = {};

for (const f of fs.readdirSync(regDir).filter(x => x.endsWith('.yaml') && !/^modules(-|$)/.test(x))) {
  const moduleId = f.replace(/\.yaml$/, '');
  const { doc, raw } = loadYamlSafe(path.join(regDir, f));
  if (!doc) continue;
  const feats = (doc.pages || []).flatMap(p => p.features || []);
  const cnt = { pass: 0, fail: 0, blocked: 0, todo: 0 };
  for (const ft of feats) {
    const s = ft.status || 'todo';
    cnt[s] = (cnt[s] || 0) + 1;
    totals[s] = (totals[s] || 0) + 1;
  }
  // blocked 根因分类：reason 字段 + 注释块
  const blocks = commentBlocks(raw);
  for (const ft of feats.filter(x => x.status === 'blocked')) {
    const blk = blocks.find(b => b.id === ft.id);
    const text = [ft.reason || '', ...(blk ? blk.comments : [])].join(' ');
    const cat = classify(text);
    blockedByCat[cat] = (blockedByCat[cat] || 0) + 1;
  }
  const meta = modulesMeta.get(moduleId) || {};
  rows.push({
    id: moduleId,
    name: doc.name || meta.name || moduleId,
    status: meta.status || '(未入总账)',
    priority: meta.priority || '-',
    ...cnt,
    total: feats.length,
    progress: meta.progress || '',
  });
}
// 总账中有但无 registry 文件的模块
for (const [id, m] of modulesMeta) {
  if (!rows.find(r => r.id === id)) {
    rows.push({ id, name: m.name || id, status: m.status, priority: m.priority || '-', pass: 0, fail: 0, blocked: 0, todo: 0, total: 0, progress: m.progress || '' });
  }
}

rows.sort((a, b) => (a.priority + a.id).localeCompare(b.priority + b.id));
const grandTotal = totals.pass + totals.fail + totals.blocked + totals.todo;
const pct = n => grandTotal ? (100 * n / grandTotal).toFixed(1) + '%' : '-';

// -------- 输出 --------
const L = [];
L.push('# E2E 深度验收全局视图（dashboard）');
L.push(`> 自动生成（node tools/dashboard.js），请勿手改。时间: ${new Date().toISOString().slice(0, 19).replace('T', ' ')}`);
L.push('');
L.push(`## 总览：${rows.length} 模块 / ${grandTotal} 功能点`);
L.push(`- pass ${totals.pass}（${pct(totals.pass)}）/ fail ${totals.fail} / blocked ${totals.blocked}（${pct(totals.blocked)}）/ todo ${totals.todo}`);
L.push('');
if (Object.keys(blockedByCat).length) {
  L.push('## blocked 根因分布');
  L.push('| 分类 | 数量 |');
  L.push('|------|------|');
  for (const [cat, n] of Object.entries(blockedByCat).sort((a, b) => b[1] - a[1])) L.push(`| ${cat} | ${n} |`);
  L.push('');
}
L.push('## 模块明细');
L.push('| 模块 | 状态 | 优先级 | 功能点 | pass | fail | blocked | todo | progress |');
L.push('|------|------|--------|--------|------|------|---------|------|----------|');
for (const r of rows) {
  L.push(`| ${r.id} | ${r.status} | ${r.priority} | ${r.total} | ${r.pass} | ${r.fail} | ${r.blocked} | ${r.todo} | ${(r.progress || '').replace(/\|/g, '\\|')} |`);
}
L.push('');
if (warnings.length) {
  L.push('## ⚠ 数据质量告警');
  warnings.forEach(w => L.push(`- ${w}`));
  L.push('');
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, L.join('\n'), 'utf8');
console.log(`[dashboard] ${rows.length} 模块 / ${grandTotal} 功能点：pass ${totals.pass} / fail ${totals.fail} / blocked ${totals.blocked} / todo ${totals.todo}`);
console.log(`[dashboard] blocked 根因: ${Object.entries(blockedByCat).map(([k, v]) => `${k}${v}`).join(' ') || '(无)'}`);
if (warnings.length) { console.warn(`[dashboard] ⚠ ${warnings.length} 条数据质量告警（详见输出文件）`); }
console.log(`[dashboard] → ${path.relative(process.cwd(), OUT)}`);
