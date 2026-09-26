// E-16 DRIVER.
// Ejercita el RETRY RUNNER COMPARTIDO REAL de gh-aw v0.89.21 sin modificarlo.
// - resolveRetryConfig  : código upstream real (lee GH_AW_HARNESS_* del entorno)
// - runHarnessRetryLoop : código upstream real (máquina de estados de intentos/backoff)
// - runAttempt/handleFailure : callbacks, que upstream define como ESPECÍFICOS DE ENGINE
//   (ver comentario del propio runner: "Engine-specific argument selection, execution,
//    and failure classification remain callbacks").
// El proceso hijo es un stub determinista; el harness que lo relanza es real.
"use strict";
const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const { resolveRetryConfig } = require("./upstream/harness_retry_config.cjs");
const { runHarnessRetryLoop } = require("./upstream/harness_retry_runner.cjs");

const CASE = process.env.E16_CASE || "unknown";
const WS = process.env.E16_WORKSPACE;
const EXT = process.env.E16_EXTERNAL_LOG;
const OBS = process.env.E16_OBSERVATIONS;
const OUT = process.env.E16_RESULT;

const logLines = [];
const log = m => { logLines.push(String(m)); console.log("[e16-driver] " + m); };

// --- configuración resuelta por CÓDIGO UPSTREAM REAL ---
const cfg = resolveRetryConfig(process.env, log);
log("resolveRetryConfig => " + JSON.stringify(cfg));

const attemptRecords = [];

(async () => {
  const driverStartTime = Date.now();
  const result = await runHarnessRetryLoop({
    maxRetries: cfg.maxRetries,
    initialDelayMs: cfg.initialDelayMs,
    backoffMultiplier: cfg.backoffMultiplier,
    maxDelayMs: cfg.maxDelayMs,
    driverStartTime,
    harnessName: "e16-stub-harness",
    log,
    softTimeoutGuard: null,
    // sleepFn es un parámetro oficial e inyectable del runner; se acelera para no
    // consumir minutos de runner. No altera la máquina de estados.
    sleepFn: ms => { attemptRecords.push({ slept_ms_requested: ms }); return Promise.resolve(); },
    runAttempt: async attempt => {
      const r = cp.spawnSync(process.execPath, [path.join(__dirname, "e16_child_stub.js")], {
        encoding: "utf8",
        env: { ...process.env, E16_ATTEMPT_INDEX: String(attempt) },
      });
      attemptRecords.push({
        attempt_index: attempt,
        child_pid_reported: r.pid ?? null,
        exit_code: r.status,
        signal: r.signal,
        stdout: (r.stdout || "").trim().slice(0, 500),
        stderr: (r.stderr || "").trim().slice(0, 500),
      });
      log(`runAttempt(${attempt}) => exit=${r.status} pid=${r.pid}`);
      return { exitCode: r.status === null ? 1 : r.status, output: r.stdout || "", hasOutput: Boolean(r.stdout) };
    },
    handleFailure: ({ attempt, result, maxRetries }) => {
      // clasificación específica de engine: nuestro 42 es "retryable inducido"
      const retryable = result.exitCode === 42;
      log(`handleFailure(attempt=${attempt}, exit=${result.exitCode}, maxRetries=${maxRetries}) => ${retryable ? "retry" : "stop"}`);
      return { action: retryable ? "retry" : "stop" };
    },
  });

  const readLines = p => { try { return fs.readFileSync(p, "utf8").split("\n").filter(Boolean); } catch { return []; } };
  const extLines = readLines(EXT).map(l => JSON.parse(l));
  const obsLines = readLines(OBS).map(l => JSON.parse(l));
  const markerPath = path.join(WS, "e16_workspace_marker.txt");

  const out = {
    case: CASE,
    node_version: process.version,
    gh_aw_version_pinned: "v0.89.21",
    env_requested: {
      GH_AW_HARNESS_MAX_RETRIES: process.env.GH_AW_HARNESS_MAX_RETRIES ?? null,
      GH_AW_HARNESS_INITIAL_DELAY_MS: process.env.GH_AW_HARNESS_INITIAL_DELAY_MS ?? null,
      GH_AW_HARNESS_STARTUP_RETRIES: process.env.GH_AW_HARNESS_STARTUP_RETRIES ?? null,
    },
    resolved_config_from_upstream: cfg,
    loop_return_value: { exitCode: result.exitCode, attempts: result.attempts },
    attempt_records: attemptRecords,
    child_invocations_observed: extLines.length,
    external_effect_log: extLines,
    child_observations: obsLines,
    workspace_marker_final: (() => { try { return fs.readFileSync(markerPath, "utf8"); } catch { return null; } })(),
    distinct_child_pids: [...new Set(extLines.map(e => e.pid))],
    driver_log: logLines,
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2));
  console.log("=== RESUMEN " + CASE + " ===");
  console.log("  attempts (valor devuelto por el runner real): " + result.attempts);
  console.log("  child_invocations observadas               : " + extLines.length);
  console.log("  PIDs distintos del hijo                     : " + out.distinct_child_pids.join(", "));
  console.log("  exitCode final                              : " + result.exitCode);
})().catch(e => { console.error("DRIVER ERROR", e); process.exit(1); });
