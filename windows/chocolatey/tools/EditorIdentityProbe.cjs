// Fixed read-only probe, run by the checked editor's bundled Electron runtime.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const files = ['resources/app/product.json', 'resources/app/package.json', 'resources/app/out/cli.js'];
function readMetadata(file) {
  const descriptor = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NONBLOCK || 0));
  try {
    const info = fs.fstatSync(descriptor);
    if (!info.isFile() || info.size > 1048576) throw new Error('inspectionLimit');
    const buffer = Buffer.alloc(1048577);
    let total = 0;
    while (total < buffer.length) {
      const count = fs.readSync(descriptor, buffer, total, buffer.length - total, null);
      if (!count) break;
      total += count;
    }
    if (total > 1048576) throw new Error('inspectionLimit');
    return buffer.subarray(0, total);
  } finally { fs.closeSync(descriptor); }
}
function hashFile(file, limit) {
  const descriptor = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NONBLOCK || 0));
  try {
    const info = fs.fstatSync(descriptor);
    if (!info.isFile() || info.size > limit) throw new Error('inspectionLimit');
    const hash = crypto.createHash('sha256');
    const buffer = Buffer.alloc(65536);
    let total = 0;
    for (;;) {
      const count = fs.readSync(descriptor, buffer, 0, buffer.length, null);
      if (!count) break;
      total += count;
      if (total > limit) throw new Error('inspectionLimit');
      hash.update(buffer.subarray(0, count));
    }
    return hash.digest('hex');
  } finally { fs.closeSync(descriptor); }
}
function snapshot(executable, electronVersion) {
  executable = fs.realpathSync(executable);
  const root = path.dirname(executable);
  if (path.basename(executable).toLowerCase() !== 'vscodium.exe' || !/^[A-Za-z]:\\/.test(executable) || /[\x00-\x1f\x7f|]/.test(executable)) throw new Error('unsupportedLayout');
  for (const relative of files) {
    const file = path.join(root, relative);
    if (fs.realpathSync(file) !== file) throw new Error('unsupportedLayout');
  }
  const productBytes = readMetadata(path.join(root, files[0]));
  const packageBytes = readMetadata(path.join(root, files[1]));
  const product = JSON.parse(productBytes.toString('utf8'));
  const metadata = JSON.parse(packageBytes.toString('utf8'));
  if (product.nameShort !== 'VSCodium' || product.applicationName !== 'codium' || product.quality !== 'stable' ||
      typeof metadata.version !== 'string' || !/^\d+\.\d+\.\d+(?:\.\d+)?$/.test(metadata.version)) throw new Error('wrongProduct');
  const digests = [hashFile(executable, 536870912), hashFile(path.join(root, files[0]), 1048576),
    hashFile(path.join(root, files[1]), 1048576), hashFile(path.join(root, files[2]), 16777216)];
  const selectionId = crypto.createHash('sha256').update(digests.join('\n') + '\n' + executable).digest('hex');
  return { schema: 1, component: 'VSCodium', platform: 'windows', status: 'candidate', reason: 'identityObserved',
    root, executable, cli: path.join(root, files[2]), version: metadata.version, electronVersion,
    selectionId, maintenanceEligibility: 'notEvaluated' };
}
module.exports = { snapshot };
if (require.main === module) {
  try {
    if (!/^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$/.test(process.versions.electron || '')) throw new Error('unsupportedLauncher');
    process.stdout.write(JSON.stringify(snapshot(process.execPath, process.versions.electron)));
  } catch {
    process.stderr.write('The editor identity could not be verified.\n');
    process.exitCode = 1;
  }
}
