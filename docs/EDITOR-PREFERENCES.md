# VSCodium preferences: preservation and inspection for #161

## What this increment changes

SDE keeps the user's settings file exactly as it finds it. Install and Repair no
longer merge recommendations, replace an empty file or create a missing file.
The reference defaults remain in the installed package. Existing extension
installation remains part of the approved full operation.

Validation checks the editor command and required extensions separately from
preferences. The command must return a version successfully. A failed extension
listing cannot supply a pass from partial output. An unreadable required
extension list leaves that required check incomplete and produces a failure.

Formatting on save, the chosen formatter and line endings are recommendations.
Different or unset values produce information, not readiness warnings or a
Repair requirement. Reading preferences never proves that VSCodium's required
features work.

## What SDE reads

The fixed check reads the standard user settings file under Windows APPDATA or
the Linux XDG configuration directory. Without XDG_CONFIG_HOME, Linux uses
`~/.config/VSCodium/User/settings.json`. Project, language and alternate-profile
settings can override it. SDE does not claim these three observations describe
every project's effective settings.

The helper emits schema-1 `preferences` data for VSCodium. It records the file,
scope, outcome and three bounded recommendation values. Other settings and the
full file contents are not exported. This data grants no installation, settings
change or native execution permission.

| Outcome | Meaning | Validation effect |
| --- | --- | --- |
| `read` | Supported JSONC was read, including comments and allowed trailing commas. Empty/comment-only files use empty preferences. | Information only, including custom choices. |
| `missing` | The file was not found. VSCodium can use defaults. | Information only. |
| `unreadable` | A file read failed. `accessDenied` is used only for confirmed permission denial; other causes remain unknown. | Optional check warning; required editor results stay separate. |
| `invalid` | UTF-8 contents have confirmed JSONC errors or a root value that is not a settings object. | Optional check warning; no rewrite or inferred Repair. |
| `unavailable` | The parser could not run, the location/encoding is unsupported or an inspection limit was reached. | Incomplete inspection; never called missing or damaged. |

The parser uses the explicitly selected Node 24 from runtime observation. It
does not resolve a default Node or npm. A verified Node can inspect settings
even when its npm check failed. If no suitable interpreter is available, SDE can
still establish file absence or a read-access problem; it does not guess the
contents. No installation, manager switch or project code runs.

The file limit is 1 MiB. Only a fixed child probe runs, using the existing
sanitized temporary-directory adapter and a 2.5-second deadline. UTF-8 with a
BOM is supported. Other encodings stay unverified. Required editor CLI checks
retain their existing execution path; this deadline applies to the new settings
probe, not every editor operation.

## Pinned parser

The two platforms carry unchanged parser/scanner files and the MIT license from
Microsoft's published `jsonc-parser` **3.3.1** package. The published UMD files are
used; current upstream HEAD documentation may describe a different module format.

- [Versioned npm metadata](https://registry.npmjs.org/jsonc-parser/3.3.1).
- [Upstream project](https://github.com/microsoft/node-jsonc-parser).
- Source archive: `https://registry.npmjs.org/jsonc-parser/-/jsonc-parser-3.3.1.tgz`.
- Archive integrity: `sha512-HUgH65KyejrUFPvHFPbqOY0rsFip3Bo5wb4ngvdi1EpCYWUQDC5V+Y7mZws+DLkr4M//zQJoanu1SP+87Dv1oQ==`.

`lib/umd/impl/parser.js`, `lib/umd/impl/scanner.js` and `LICENSE.md` were copied
without changes into each backend's `jsonc-parser` directory. Git attributes
preserve their exact bytes on Windows and Linux. Tests pin their SHA-256 hashes
and verify that the platform copies match. The Linux integrity manifest covers
the installed helpers and vendored files. Windows copies use the existing
protected maintenance-file ACL, with a protected directory that rejects links.
The application resource bundle includes both backends and the license.

Parsing explicitly allows comments, trailing commas and empty content. The
parser is fault tolerant, so SDE always checks its error list before accepting a
result. A partially recovered object cannot supply a successful inspection.
There is no runtime download or new npm installation step.
An exact development dependency also places this version under the existing
CI dependency-audit gate; it does not supply the application's parser at runtime.

## Evidence and remaining work

Local tests exercise real parsing, unchanged bytes, absent/empty files, comments,
trailing commas, bounded values, inherited-property rejection, malformed content,
denied access, unavailable parsing and failed extension output. Native profile
fixtures require strict JSON/JSONC bytes, empty files and missing files to remain
unchanged alongside the existing Git, identity and project requirements.

Installed-package verification requires the helper/parser files. Native Windows
CI must additionally prove denied access and Windows PowerShell 5.1 behavior.
Existing Mint profile checks prove preservation; they do not by themselves prove
every editor inspection on an owner's Mint desktop.

Runtime/preference events are data, not validation success or collection-time
evidence. Only actual validation events update that clock. Existing summary,
exit, failure and native safety requirements remain unchanged.

The accepted cards, recommendation Details, access troubleshooting and in-place
recheck flow still need integration under #161. This backend increment does not
provide an automatic settings writer or complete that issue. Human signing,
owner UAT of the exact authenticated candidate and separate promotion approval
remain required.
