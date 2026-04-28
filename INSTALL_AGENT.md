# Agent Install Quickstart

Give the installing agent exactly one required fact: the path to this repository.

```bash
/path/to/second-brain-sdk/scripts/install.sh /path/to/second-brain-sdk
```

Server mode:

```bash
/path/to/second-brain-sdk/scripts/install.sh /path/to/second-brain-sdk --server
```

Create a server token for the current host:

```bash
/path/to/second-brain-sdk/scripts/install.sh /path/to/second-brain-sdk --server --token-for "$(hostname)"
```

The bootstrapper will:

1. Validate the supplied repo path.
2. Create or reuse `${SECOND_BRAIN_VENV:-~/.venvs/second-brain}`.
3. Install this repo in editable mode with the server extra.
4. Link `second-brain` into `~/.local/bin` and `~/bin`.
5. Delegate to `second-brain install <repo-path>` for agent detection, version checks, brain initialization, plugin setup, and verification.

Upgrade/reset behavior:

- If no copy is installed, it performs a fresh install.
- If an older copy is installed, it upgrades in place without touching existing brain data.
- If this same version is already installed and brain data exists, it makes no changes in non-interactive runs.
- In an interactive terminal, same-version installs ask whether to reset local brain state.
- To force a reset from an agent after explicit user approval, rerun with `--reset`; reset backs up the current brain before wiping active state.

```bash
/path/to/second-brain-sdk/scripts/install.sh /path/to/second-brain-sdk --reset
```

Equivalent direct CLI call after the package is already installed:

```bash
second-brain install /path/to/second-brain-sdk
```

If no repo path is provided to `second-brain install`, it preserves the legacy behavior: use or clone `~/second-brain-sdk`.
