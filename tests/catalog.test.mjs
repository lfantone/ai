import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const read = (relativePath) => fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const install = (harness, names = "pokemon") => {
  const project = fs.mkdtempSync(path.join(os.tmpdir(), `ai-${harness}-`));
  execFileSync(
    process.execPath,
    [
      path.join(ROOT, "scripts/install.mjs"),
      "--harness",
      harness,
      "--project",
      project,
      "--names",
      names,
    ],
    { cwd: ROOT, stdio: "pipe" },
  );
  return project;
};

test("GitHub agents with MCP dependencies do not receive a restrictive tool list", () => {
  const project = install("github");
  const slowpoke = fs.readFileSync(
    path.join(project, ".github/agents/slowpoke.agent.md"),
    "utf8",
  );
  const ditto = fs.readFileSync(
    path.join(project, ".github/agents/ditto.agent.md"),
    "utf8",
  );

  assert.doesNotMatch(slowpoke, /^tools:/m);
  assert.doesNotMatch(ditto, /^tools:/m);
});

test("GitHub agents with portable tools retain a least-privilege tool list", () => {
  const project = install("github");
  const machop = fs.readFileSync(
    path.join(project, ".github/agents/machop.agent.md"),
    "utf8",
  );

  assert.match(machop, /^tools: \[.*"read".*"write".*\]$/m);
});

test("precise and fast plan authors install under both naming sets", () => {
  const pokemonProject = install("github");
  const norseProject = install("github", "norse");

  assert.ok(
    fs.existsSync(path.join(pokemonProject, ".github/agents/meowth.agent.md")),
  );
  assert.ok(
    fs.existsSync(path.join(norseProject, ".github/agents/hermod.agent.md")),
  );
});

test("all harnesses install the fast plan author", () => {
  const claudeProject = install("claude");
  const opencodeProject = install("opencode");

  assert.ok(fs.existsSync(path.join(claudeProject, ".claude/agents/meowth.md")));
  assert.ok(
    fs.existsSync(path.join(opencodeProject, ".opencode/agents/meowth.md")),
  );
});

test("canonical agent identities are unique and match filenames", () => {
  const files = fs
    .readdirSync(path.join(ROOT, "agents"))
    .filter((file) => file.endsWith(".md"));
  const names = [];
  const colors = [];

  for (const file of files) {
    const source = read(path.join("agents", file));
    const name = source.match(/^name: (.+)$/m)?.[1];
    const model = source.match(/^model: (.+)$/m)?.[1];
    const color = source.match(/^color: "(#[0-9A-F]{6})"$/m)?.[1];

    assert.equal(name?.toLowerCase(), file.replace(/\.md$/, ""));
    assert.ok(["haiku", "sonnet", "opus"].includes(model));
    assert.ok(color, `${file} must declare an uppercase hex color`);
    names.push(name);
    colors.push(color);
  }

  assert.equal(files.length, 17);
  assert.equal(new Set(names).size, names.length);
  assert.equal(new Set(colors).size, colors.length);
});

test("plan contracts distinguish exact and guided execution", () => {
  const mew = read("agents/mew.md");
  const meowth = read("agents/meowth.md");
  const magneton = read("agents/magneton.md");
  const plan = read("commands/plan-orchestrator.md");

  assert.match(mew, /Execution class.*exact/i);
  assert.match(mew, /replace_exact/);
  assert.match(mew, /Failure policy/i);
  assert.match(meowth, /Execution class.*guided/i);
  assert.match(plan, /--fast/);
  assert.match(plan, /Meowth/);
  assert.doesNotMatch(plan, /Approve this direction/);
  assert.match(magneton, /^model: haiku$/m);
  assert.doesNotMatch(magneton, /grep -c -F/);
});

test("implementation routes execution classes and preserves failed gate state", () => {
  const implement = read("commands/implement-orchestrator.md");
  const verify = read("commands/verify-orchestrator.md");
  const machop = read("agents/machop.md");
  const machoke = read("agents/machoke.md");

  assert.match(implement, /Execution class.*exact/i);
  assert.match(implement, /Execution class.*guided/i);
  assert.match(implement, /implementation-failed/);
  assert.match(verify, /implementation-failed/);
  assert.match(verify, /verification-failed.*re-verification/is);
  assert.match(verify, /diagnostic run.*preserves.*original status/is);
  assert.match(machop, /complete.*Before/i);
  assert.match(machoke, /guided/i);
});

test("review shares an ephemeral diff and refreshes material profile changes", () => {
  const review = read("commands/review-orchestrator.md");
  const kadabra = read("agents/kadabra.md");
  const mewtwo = read("agents/mewtwo.md");
  const alakazam = read("agents/alakazam.md");

  assert.match(review, /\$CACHE\/tmp\/review-<index>-<head_sha>\.diff/);
  assert.match(review, /delete.*temporary diff/i);
  assert.match(review, /material change/i);
  assert.match(kadabra, /DIFF_PATH/);
  assert.match(mewtwo, /DIFF_PATH/);
  assert.match(alakazam, /DIFF_PATH/);
});
