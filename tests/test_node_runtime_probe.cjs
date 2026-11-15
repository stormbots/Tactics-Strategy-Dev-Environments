// Local files plus the prepared Node/npm dependency; no installation or manager commands.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const source = fs.readFileSync(path.join(__dirname, '../windows/chocolatey/tools/NodeRuntimeProbe.cjs'), 'utf8');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'sde node probe '));
const executable = path.join(root, 'node.exe');
const npmRoot = path.join(root, 'node_modules/npm');
const npmCli = path.join(npmRoot, 'bin/npm-cli.js');
const npmPackage = path.join(npmRoot, 'package.json');
const installedNpm = [path.join(path.dirname(process.execPath), 'node_modules/npm'), path.resolve(path.dirname(process.execPath), '../lib/node_modules/npm')].find(p => fs.existsSync(p));
assert(installedNpm, 'Prepared npm is required for real semver compatibility tests');
const installedRequire = createRequire(path.join(installedNpm, 'package.json'));
function probeRequire(id) {
  if (id === 'node:module') return { createRequire: origin => {
    assert.equal(origin, npmPackage, 'Dependency lookup must bind to the selected npm package');
    return installedRequire; // Exercise real semver with all of its real dependencies.
  }};
  return require(id);
}
let count = 0;
function check(mode = 'npm', version = '24.19.0') {
  const subject = { execPath: executable, versions: { node: version }, argv: ['node', 'probe', mode], stdout: { write: t => { subject.output = t; } }, stderr: { write: () => {} } };
  vm.runInNewContext(source, { require: probeRequire, process: subject });
  count++;
  return subject;
}
function metadata(engine = '^20.17.0 || >=22.9.0', name = 'npm', version = '11.9.0') {
  fs.writeFileSync(npmPackage, JSON.stringify({ name, version, engines: { node: engine } }));
}
try {
  fs.mkdirSync(path.dirname(npmCli), { recursive: true });
  fs.mkdirSync(path.join(npmRoot, 'node_modules'), { recursive: true });
  fs.writeFileSync(executable, 'fixture identity only');
  fs.writeFileSync(npmCli, "throw new Error('The metadata probe must not execute npm CLI');\n");
  metadata();
  let result = check();
  assert.equal(result.exitCode, undefined);
  assert.deepEqual(JSON.parse(result.output), { version: '24.19.0', executable, npmVersion: '11.9.0', npmCli });
  assert.equal(JSON.parse(check('identity', '26.1.0').output).version, '26.1.0');
  assert.equal(check('npm', '26.1.0').exitCode, 1);
  for (const engine of ['>=26', 'not a range', '<24']) { metadata(engine); assert.equal(check().exitCode, 1); }
  metadata('>=24', 'another-package'); assert.equal(check().exitCode, 1);
  metadata('>=24', 'npm', 'not-a-version'); assert.equal(check().exitCode, 1);
  metadata('>=24', 'npm', '12.0.0-beta.1'); assert.equal(JSON.parse(check().output).npmVersion, '12.0.0-beta.1');
  fs.unlinkSync(npmCli); assert.equal(check().exitCode, 1);
  assert.equal(check('arbitrary-command').exitCode, 1);
  console.log(`NODE_RUNTIME_PROBE_CONTRACTS_OK (${count} probe cases)`);
} finally { fs.rmSync(root, { recursive: true, force: true }); }
