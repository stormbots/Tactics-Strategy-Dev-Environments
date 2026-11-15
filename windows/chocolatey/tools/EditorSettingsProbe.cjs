// Fixed read-only settings inspection. Neither settings nor project code executes.
const fs = require('node:fs');
const path = require('node:path');
const { TextDecoder } = require('node:util');
const recommendations = [
  ['editor.formatOnSave', true],
  ['editor.defaultFormatter', 'esbenp.prettier-vscode'],
  ['files.eol', '\n'],
];
const settingsPath = process.argv[2];
const result = { schema: 1, component: 'VSCodium', scope: 'standardUserFile',
  path: settingsPath || null, status: 'unavailable', reason: 'parserUnavailable', recommendations: [] };
let descriptor;
let phase = 'read';
try {
  if (!settingsPath || settingsPath.length > 4096 || !path.isAbsolute(settingsPath) || /[\x00-\x1f\x7f|]/.test(settingsPath)) {
    result.path = null;
    result.reason = 'locationUnavailable';
  } else {
    descriptor = fs.openSync(settingsPath, fs.constants.O_RDONLY | (fs.constants.O_NONBLOCK || 0));
    const info = fs.fstatSync(descriptor);
    if (!info.isFile()) {
      result.status = 'unreadable'; result.reason = 'readFailed';
    } else if (info.size > 1048576) {
      result.reason = 'inspectionLimit';
    } else {
      const bytes = Buffer.alloc(1048577);
      let length = 0;
      while (length < bytes.length) {
        const count = fs.readSync(descriptor, bytes, length, bytes.length - length, null);
        if (!count) break;
        length += count;
      }
      if (length > 1048576) {
        result.reason = 'inspectionLimit';
      } else {
        let text;
        try { text = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, length)); }
        catch { result.status = 'unavailable'; result.reason = 'encodingUnavailable'; }
        if (text !== undefined && /^24\.\d+\.\d+$/.test(process.versions.node)) {
          phase = 'parse';
          // Published jsonc-parser 3.3.1, unchanged and pinned with its license.
          // It is fault tolerant: a returned object alone does NOT mean valid.
          const { parse } = require('./jsonc-parser/parser.js');
          const errors = [];
          const value = parse(text, errors, { disallowComments: false, allowTrailingComma: true, allowEmptyContent: true });
          const settings = value === undefined && errors.length === 0 ? {} : value;
          if (errors.length || !settings || typeof settings !== 'object' || Array.isArray(settings)) {
            result.status = 'invalid'; result.reason = 'invalidContents';
          } else {
            result.status = 'read'; result.reason = 'verified';
            result.recommendations = recommendations.map(([key, recommended]) => {
              const present = Object.hasOwn(settings, key);
              const actual = present ? settings[key] : undefined;
              const visible = typeof actual === 'boolean' || (typeof actual === 'string' && actual.length <= 256);
              return { key, recommended, status: !present ? 'unset' : actual === recommended ? 'matches' : 'different',
                value: visible ? actual : null };
            });
          }
        }
      }
    }
  }
} catch (error) {
  if (phase === 'parse') { result.status = 'unavailable'; result.reason = error instanceof RangeError ? 'inspectionLimit' : 'parserUnavailable'; }
  else if (error.code === 'ENOENT') { result.status = 'missing'; result.reason = 'defaults'; }
  else if (error.code === 'EACCES' || error.code === 'EPERM') { result.status = 'unreadable'; result.reason = 'accessDenied'; }
  else if (error.code === 'MODULE_NOT_FOUND') { result.status = 'unavailable'; result.reason = 'parserUnavailable'; }
  else if (error instanceof RangeError) { result.status = 'unavailable'; result.reason = 'inspectionLimit'; }
  else { result.status = 'unreadable'; result.reason = 'readFailed'; }
} finally {
  if (descriptor !== undefined) {
    try { fs.closeSync(descriptor); }
    catch { result.status = 'unreadable'; result.reason = 'readFailed'; result.recommendations = []; }
  }
}
process.stdout.write(JSON.stringify(result));
