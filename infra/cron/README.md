# infra/cron — CCF Plataforma scheduled jobs

This directory holds **declarative cron entries** (and any future systemd
timer units) for the CCF Plataforma project. Crontab files here are
**declarative**: they describe *what* should run, not *what is currently
running on a host*. Activation is a separate manual step because cron is
per-host local state.

## Files

- `ccf-platform` — main nightly regression loop (02:00 UTC daily).

## Install

As the user account that owns the project's runtime (commonly `root` or a
dedicated `ccf` user):

```bash
# Option A — install the whole table (REPLACES your current crontab):
crontab infra/cron/ccf-platform

# Option B — visually edit and paste (preserves existing entries):
crontab -l > /tmp/cron.current
cat infra/cron/ccf-platform | grep -v '^#' >> /tmp/cron.current
crontab /tmp/cron.current
```

Both paths put the scheduler in charge. Verify with `crontab -l`.

## Requirements (operating)

1. `/var/log/ccf/` exists and is writable by the cron user:
   ```bash
   sudo mkdir -p /var/log/ccf
   sudo chown $(id -un):adm /var/log/ccf
   sudo chmod 0755 /var/log/ccf
   ```
2. `/root/ccf/scripts/nightly_regression.sh` is executable (`chmod +x`).
3. The project's Python venv lives at `/root/ccf/venv/`
   (`scripts/run_ci.sh` resolves `./venv/bin/python` first).
4. Cron does not inherit the user's interactive `PATH`; the scripts
   intentionally use **absolute paths** to all binaries, so rerun
   should work without `PATH` tweaks.

## Verify a single nightly run

Without waiting for the cron tick:

```bash
/root/ccf/scripts/nightly_regression.sh 2>&1 | tee /tmp/nightly-dry.log
```

The script is idempotent: re-running it costs another full nightly cycle
(~10-15 min depending on suite size) but does not corrupt state.

## Log rotation

See `infra/logrotate/ccf-platform` (future — deploy with the regular
`logrotate(8)` package on the host). Until then, `/var/log/ccf/nightly.log`
grows unbounded.

## Exit discipline

- `>>` (append) not `>` (overwrite) — preserves the prior log so triage
  doesn't lose history the first time cron fails.
- `2>&1` — captures stderr alongside stdout so a `pytest` traceback
  ends up in the same file, not a separate orphan.
- Exit status of `nightly_regression.sh` (non-zero on failure) is NOT
  explicitly mailed here. Add `MAILTO="ops@example.com"` if you want
  cron-native notifications on non-zero exit.
