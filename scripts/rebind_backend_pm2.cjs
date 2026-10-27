#!/usr/bin/env node
"use strict";

// PM2's ecosystem CLI validates away pm_exec_path on existing apps. Its native
// restart RPC accepts current_conf, preserving the existing id and policy.
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const PROCESS_NAME = "ccf-backend-staging";

function buildRestartRequest(app) {
  if (app.name !== PROCESS_NAME || !Number.isInteger(app.pm_id) || app.pm_id < 0) {
    throw new Error("Invalid backend PM2 identity");
  }
  if (!path.isAbsolute(app.pm_exec_path) || !path.isAbsolute(app.pm_cwd)) {
    throw new Error("Backend launcher and runtime must use absolute paths");
  }
  // Update only these fields. Memory limits, restart policy, logs, interpreter,
  // counters and every other service stay in the daemon's existing config.
  return {
    id: app.pm_id,
    env: {
      current_conf: {
        pm_exec_path: app.pm_exec_path,
        pm_cwd: app.pm_cwd,
        env: { ...app.env, CCF_RUNTIME_DIR: app.pm_cwd },
      },
    },
  };
}

function loadPm2() {
  const configured = process.env.CCF_PM2_MODULE;
  if (configured) {
    if (!path.isAbsolute(configured)) throw new Error("CCF_PM2_MODULE must be absolute");
    return require(configured);
  }
  try {
    return require("pm2");
  } catch (error) {
    if (error.code !== "MODULE_NOT_FOUND") throw error;
    const globalRoot = execFileSync("npm", ["root", "-g"], {
      encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 10000,
    }).trim();
    if (!path.isAbsolute(globalRoot)) throw new Error("Invalid global module path");
    return require(path.join(globalRoot, "pm2"));
  }
}

function callbackPromise(operation) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("PM2 operation timed out")), 15000);
    try {
      operation((error, value) => {
        clearTimeout(timer);
        if (error) reject(error);
        else resolve(value);
      });
    } catch (error) {
      clearTimeout(timer);
      reject(error);
    }
  });
}

async function rebind(configPath, pm2) {
  if ((fs.statSync(configPath).mode & 0o077) !== 0) {
    throw new Error("PM2 config contains private environment and must have mode 0600");
  }
  const saved = JSON.parse(fs.readFileSync(configPath, "utf8"));
  if (!Array.isArray(saved.apps) || saved.apps.length !== 1) {
    throw new Error("Only one backend app may be rebound");
  }
  const app = saved.apps[0];
  const request = buildRestartRequest(app);
  try {
    await callbackPromise((done) => pm2.connect(done));
    const entries = await callbackPromise((done) => pm2.list(done));
    const existing = entries.find((entry) => entry.pm_id === request.id && entry.name === PROCESS_NAME);
    if (!existing || existing.pm2_env.pm_cwd !== app.pm_cwd) {
      throw new Error("Backend identity/runtime changed before rebind");
    }
    const expected = saved.expected_exec_paths || [saved.expected_exec_path];
    const acceptable = [...expected, app.pm_exec_path];
    if (!acceptable.includes(existing.pm2_env.pm_exec_path)) {
      throw new Error("Backend launcher changed before rebind");
    }
    await callbackPromise((done) => pm2.Client.executeRemote("restartProcessId", request, done));
  } finally {
    pm2.disconnect();
  }
}

module.exports = { buildRestartRequest, rebind, loadPm2 };

if (require.main === module) {
  Promise.resolve().then(() => rebind(process.argv[2], loadPm2())).catch(() => {
    // PM2 errors and the config can contain credentials. Report no raw payload.
    process.stderr.write("Backend PM2 launcher rebind failed; inspect private deployment state\n");
    process.exitCode = 1;
  });
}
