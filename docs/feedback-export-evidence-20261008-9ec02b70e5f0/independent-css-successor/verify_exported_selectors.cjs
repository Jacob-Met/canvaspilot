'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');
const [beforePath, afterPath, jsdomPath] = process.argv.slice(2);
const { JSDOM, VirtualConsole } = require(jsdomPath);
const sha256 = b => crypto.createHash('sha256').update(b).digest('hex');
function check(value, message) { if (!value) throw new Error(message); }
function inspect(file) {
  const bytes = fs.readFileSync(file);
  const diagnostics = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', e => diagnostics.push(String(e)));
  // Omitted resources and runScripts disable subresource loads and scripts.
  const dom = new JSDOM(bytes.toString('utf8'), { virtualConsole });
  try {
    const d = dom.window.document;
    check(d.styleSheets.length === 1, 'expected one embedded stylesheet');
    check(d.querySelectorAll('script,link,img,iframe,object,embed').length === 0,
      'unexpected resource element');
    const selectors = [];
    function visit(rules, context = []) {
      for (const rule of rules) {
        if (rule.type === 1) {
          const row = { selector: rule.selectorText, context };
          try {
            const found = d.querySelectorAll(rule.selectorText);
            Object.assign(row, { accepted: true, matches: found.length,
              matchesRoot: found.length === 1 && found[0] === d.documentElement });
          } catch (e) { Object.assign(row, { accepted: false, error: { name: e.name, message: e.message } }); }
          selectors.push(row);
        }
        if (rule.cssRules) visit(rule.cssRules, [...context, rule.conditionText || rule.cssText.split('{')[0].trim()]);
      }
    }
    visit(d.styleSheets[0].cssRules);
    const style = d.styleSheets[0].cssRules[0].style;
    return { file, bytes: bytes.length, sha256: sha256(bytes),
      css: d.querySelector('style').textContent, selectors, diagnostics,
      declarations: { color: style.getPropertyValue('color'), background: style.getPropertyValue('background'),
        colorScheme: style.getPropertyValue('color-scheme') } };
  } finally { dom.window.close(); }
}
const before = inspect(beforePath), after = inspect(afterPath);
const oldInvalid = before.selectors.filter(x => !x.accepted), newInvalid = after.selectors.filter(x => !x.accepted);
check(before.css.startsWith('+:root') && after.css === before.css.slice(1), 'actual CSS differs beyond the single plus');
check(oldInvalid.length === 1 && oldInvalid[0].selector === '+:root' && oldInvalid[0].error.name === 'SyntaxError',
  'predecessor did not reproduce exactly the known invalid selector');
check(newInvalid.length === 0, 'successor has an invalid selector');
check(after.selectors[0].selector === ':root' && after.selectors[0].matchesRoot, 'repaired selector does not target root');
check(before.selectors.length === after.selectors.length, 'rule count changed');
check(JSON.stringify(before.declarations) === JSON.stringify(after.declarations), 'root declarations changed');
check(['#182a3a', 'rgb(24, 42, 58)'].includes(after.declarations.color) &&
  ['#f3f5f6', 'rgb(243, 245, 246)'].includes(after.declarations.background) &&
  after.declarations.colorScheme === 'light', 'root declarations missing');
delete before.css; delete after.css;
const pkg = path.join(jsdomPath, 'package.json');
process.stdout.write(JSON.stringify({ schema: 'independent-exported-css-selector.v1', passed: true,
  node: process.version, parser: { name: 'jsdom', version: require(pkg).version,
    packagePath: pkg, packageSha256: sha256(fs.readFileSync(pkg)) },
  browserAllocations: 0, scriptsEnabled: false, subresourcesEnabled: false,
  renderedPrintLayoutClaim: false, onlyStylesheetDifference: 'one leading plus removed', before, after }, null, 2) + '\n');
