# 6. Prepare your development environment

**Goal:** Know what your tools do before using them.

Your development environment includes the editor, terminal, language tools and libraries needed for the task. Different projects need different combinations.

| Tool | Its job in SDE |
| --- | --- |
| VSCodium | Edit and inspect project files. |
| Terminal | Run commands and read their output. |
| Node.js | Run JavaScript tools used by the interface project. |
| npm | Get JavaScript dependencies and run the project's named scripts. |
| TypeScript | Check types in the interface code. |
| Vite | Serve the interface during development and build its production files. |
| Rust and Cargo | Build and test native Rust components. |
| Python | Run several repository utilities and backend tests. |
| PowerShell and Bash | Run platform-specific scripts. |

A **dependency** is software the project uses. A manifest lists dependencies and scripts. A lockfile records resolved dependency versions so another computer can reproduce the installation more closely.

SDE's interface manifest is `installer/package.json`. Its `scripts` section is the evidence for commands such as `npm test` and `npm run build`.

## Make an inventory first

On a prepared development computer, these commands read installed tool versions:

```bash
git --version
node --version
npm --version
```

An unavailable command tells you that the shell could not run it. It does not prove the software exists nowhere on the computer. Another installation or location may need inspection.

The real Python finding illustrates this distinction. The owner could run Python 3.14 even though another version was the default. PR #163 changed Windows verification to find and check the required interpreter and its pip together. It preserved the other installation and default choice.

## Install project dependencies deliberately

**Location:** `installer/` in a mentor-approved development clone, not the empty Git practice repository.

```bash
npm ci
```

This downloads the dependencies recorded in the lockfile and recreates `node_modules`. Dependency installation can run project or package setup scripts. Use reviewed source and the mentor-prepared environment. It does not install the SDE workstation baseline.

A downloaded dependency cache can save time. The project still needs its checks.

## Practice

Record your editor and the three version-command results. Open `installer/package.json` and find the commands behind `test`, `build` and `dev`. If a required tool is unavailable, record the result and ask your mentor for the supported setup path.

## Check your understanding

- What is the difference between a manifest and a lockfile?
- Why can a different default Python version coexist with the required version?

[Next: check locally](07-local-development.md)
