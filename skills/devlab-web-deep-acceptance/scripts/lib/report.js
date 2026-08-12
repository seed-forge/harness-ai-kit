/** lib/report.js — 报告生成：功能点级 + 模块级 SUMMARY。前 5 行必须是结论摘要 */
const fs = require('fs');
const path = require('path');
const REPORTS = path.join(__dirname, '..', 'reports');

/** result: {featureId, name, level, status:'pass'|'fail'|'blocked', reason, detail, exempted, screenshots} */
function writeFeature(moduleId, result) {
  const dir = path.join(REPORTS, moduleId);
  fs.mkdirSync(dir, { recursive: true });
  const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const lines = [
    `# ${result.featureId} — ${result.status.toUpperCase()}`,
    `- 功能点: ${result.name} (${result.level})`,
    `- 结论: ${result.status.toUpperCase()}${result.reason ? ' — ' + result.reason : ''}`,
    `- 时间: ${now}`,
    '',
    '## 详情', '',
    result.detail || '(无)', '',
  ];
  if (result.exempted && result.exempted.length) {
    lines.push('## 豁免统计', '');
    result.exempted.forEach(e => lines.push(`- ${e.status} ${e.url.split('?')[0]}（重试成功，已豁免）`));
    lines.push('');
  }
  (result.screenshots || []).forEach(s => lines.push(`![截图](${s})`));
  const file = path.join(dir, `${result.featureId}.md`);
  fs.writeFileSync(file, lines.join('\n'), 'utf-8');
  return file;
}

/** 模块级 SUMMARY：功能点结果表 + 豁免统计 */
function writeSummary(moduleId, moduleName, results, { exemptTotal = 0 } = {}) {
  const dir = path.join(REPORTS, moduleId);
  fs.mkdirSync(dir, { recursive: true });
  const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
  const cnt = s => results.filter(r => r.status === s).length;
  const lines = [
    `# ${moduleName || moduleId} — 深度验收 SUMMARY`,
    `- 时间: ${now}`,
    `- 总计: ${results.length} 项 — ${cnt('pass')} PASS / ${cnt('fail')} FAIL / ${cnt('blocked')} BLOCKED（豁免 ${exemptTotal}）`,
    '',
    '| 功能点 | 级别 | 状态 | 根因/说明 |',
    '|--------|------|------|-----------|',
  ];
  for (const r of results) {
    lines.push(`| ${r.featureId} | ${r.level} | ${r.status.toUpperCase()} | ${(r.reason || '').replace(/\|/g, '\\|')} |`);
  }
  lines.push('');
  const file = path.join(dir, 'SUMMARY.md');
  fs.writeFileSync(file, lines.join('\n'), 'utf-8');
  return file;
}

module.exports = { writeFeature, writeSummary };
