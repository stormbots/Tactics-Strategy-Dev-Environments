// Fixed, read-only probe, invoked through an explicitly selected Linux Node.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
try {
  const executable = fs.realpathSync(process.execPath);
  const result = { version: process.versions.node, executable };
  if (process.argv[2] === 'npm') {
    if (!/^24\.\d+\.\d+$/.test(result.version)) throw new Error('nodeFamily');
    const prefix = path.dirname(path.dirname(executable));
    if (path.basename(path.dirname(executable)) !== 'bin' || path.basename(executable) !== 'node') throw new Error('nodeLayout');
    // Official distributions and cached manager installations bundle npm here.
    // Debian's system Node/npm packages use a distinct, fixed shared layout.
    const roots = [path.join(prefix, 'lib/node_modules/npm')];
    if (executable === '/usr/bin/node') roots.push('/usr/share/nodejs/npm');
    const npmRoot = roots.find(root => fs.existsSync(path.join(root, 'package.json')));
    if (!npmRoot) throw new Error('npmMissing');
    const packagePath = path.join(npmRoot, 'package.json');
    const npmCli = path.join(npmRoot, 'bin/npm-cli.js');
    const metadata = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    if (metadata.name !== 'npm' || typeof metadata.version !== 'string' ||
        typeof metadata.engines?.node !== 'string') throw new Error('npmIdentity');
    const semver = createRequire(packagePath)('semver');
    if (!semver.valid(metadata.version) || !semver.validRange(metadata.engines.node) ||
        !semver.satisfies(result.version, metadata.engines.node) ||
        !fs.statSync(npmCli).isFile() ||
        fs.realpathSync(npmCli) !== path.join(fs.realpathSync(npmRoot), 'bin/npm-cli.js')) {
      throw new Error('npmCompatibility');
    }
    result.npmVersion = metadata.version;
    result.npmCli = npmCli;
  } else if (process.argv[2] !== 'identity') throw new Error('probeMode');
  process.stdout.write(JSON.stringify(result));
} catch {
  process.stderr.write('The selected Node/npm probe could not be verified.\n');
  process.exitCode = 1;
}
