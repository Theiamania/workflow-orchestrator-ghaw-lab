#!/usr/bin/env node
// E-16 CHILD STUB — proceso agente determinista.
// NO reimplementa el harness. Es el proceso hijo que el harness real relanza.
"use strict";
const fs = require("fs");
const path = require("path");

const WS = process.env.E16_WORKSPACE;
const EXT = process.env.E16_EXTERNAL_LOG;
const OBS = process.env.E16_OBSERVATIONS;
const marker = path.join(WS, "e16_workspace_marker.txt");

// --- locus 2: efecto EXTERNO al workspace (append-only, sin idempotencia) ---
let priorExternal = 0;
try { priorExternal = fs.readFileSync(EXT, "utf8").split("\n").filter(Boolean).length; } catch {}
const invocation = priorExternal + 1;
fs.appendFileSync(EXT, JSON.stringify({
  child_invocation: invocation,
  timestamp: new Date().toISOString(),
  pid: process.pid,
  ppid: process.ppid,
  argv: process.argv.slice(2),
  claude_session_env: process.env.CLAUDE_SESSION_ID || null,
}) + "\n");

// --- locus 1: estado DENTRO del workspace ---
const markerExisted = fs.existsSync(marker);
const markerContentBefore = markerExisted ? fs.readFileSync(marker, "utf8").trim() : null;

const obs = {
  child_invocation: invocation,
  pid: process.pid,
  ppid: process.ppid,
  workspace_marker_existed: markerExisted,
  workspace_marker_content_before: markerContentBefore,
  external_log_lines_before: priorExternal,
  env_sample: {
    GH_AW_HARNESS_MAX_RETRIES: process.env.GH_AW_HARNESS_MAX_RETRIES ?? null,
    GH_AW_HARNESS_STARTUP_RETRIES: process.env.GH_AW_HARNESS_STARTUP_RETRIES ?? null,
  },
};

if (!markerExisted) {
  // primera invocación: produce estado material y falla de forma retryable
  fs.writeFileSync(marker, "attempt=1\n");
  obs.action = "wrote_marker_then_failed";
  obs.exit_code = 42;
  fs.appendFileSync(OBS, JSON.stringify(obs) + "\n");
  process.exit(42);
} else {
  // segunda invocación: observa el estado previo y termina con éxito
  fs.appendFileSync(marker, "attempt=" + invocation + "\n");
  obs.action = "observed_prior_state_then_succeeded";
  obs.exit_code = 0;
  fs.appendFileSync(OBS, JSON.stringify(obs) + "\n");
  process.exit(0);
}
