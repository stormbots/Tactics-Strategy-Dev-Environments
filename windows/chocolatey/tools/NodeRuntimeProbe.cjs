// Fixed, read-only probe. Called only through an explicitly selected Node.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
try {
  const executable = fs.realpathSync(process.execPath);
  const result = { version: process.versions.node, executable };
  if (process.argv[2] === 'npm') {
    if (!/^24\.\d+\.\d+$/.test(result.version)) throw new Error('nodeFamily');
    // Derive the entry point from this interpreter; never resolve bare npm.
    const npmRoot = path.join(path.dirname(executable), 'node_modules', 'npm');
    const npmCli = path.join(npmRoot, 'bin', 'npm-cli.js');
    const packagePath = path.join(npmRoot, 'package.json');
    const metadata = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    if (metadata.name !== 'npm' || typeof metadata.version !== 'string' ||
        typeof metadata.engines?.node !== 'string') throw new Error('npmIdentity');
    const semver = createRequire(packagePath)('semver');
    if (!semver.valid(metadata.version) ||
        !semver.validRange(metadata.engines.node) || !semver.satisfies(result.version, metadata.engines.node) ||
        !fs.statSync(npmCli).isFile()) throw new Error('npmCompatibility');
    result.npmVersion = metadata.version;
    result.npmCli = npmCli;
  } else if (process.argv[2] !== 'identity') throw new Error('probeMode');
  process.stdout.write(JSON.stringify(result));
} catch {
  process.stderr.write('The selected Node/npm probe could not be verified.\n');
  process.exitCode = 1;
}
