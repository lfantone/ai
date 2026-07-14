import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as yaml from "js-yaml";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const read = (relativePath) => fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const agentFiles = () =>
  fs.readdirSync(path.join(ROOT, "agents")).filter((file) => file.endsWith(".md"));

// The YAML parse error for a file's `---` frontmatter, or null when it parses cleanly.
const frontmatterError = (filePath) => {
  const block = fs.readFileSync(filePath, "utf8").match(/^---\n([\s\S]*?)\n---/)?.[1];
  if (block == null) return "no frontmatter block";
  try {
    yaml.load(block);
    return null;
  } catch (error) {
    return error.message.split("\n")[0];
  }
};

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
  // Arrange + Act
  const project = install("github");

  // Assert
  const slowpoke = fs.readFileSync(path.join(project, ".github/agents/slowpoke.agent.md"), "utf8");
  const ditto = fs.readFileSync(path.join(project, ".github/agents/ditto.agent.md"), "utf8");
  assert.doesNotMatch(slowpoke, /^tools:/m);
  assert.doesNotMatch(ditto, /^tools:/m);
});

test("GitHub agents with portable tools retain a least-privilege tool list", () => {
  // Arrange + Act
  const project = install("github");

  // Assert
  const machop = fs.readFileSync(path.join(project, ".github/agents/machop.agent.md"), "utf8");
  assert.match(machop, /^tools: \[.*"read".*"write".*\]$/m);
});

test("precise and fast plan authors install under both naming sets", () => {
  // Arrange + Act
  const pokemonProject = install("github");
  const norseProject = install("github", "norse");

  // Assert
  assert.ok(fs.existsSync(path.join(pokemonProject, ".github/agents/meowth.agent.md")));
  assert.ok(fs.existsSync(path.join(norseProject, ".github/agents/hermod.agent.md")));
});

test("all harnesses install the fast plan author", () => {
  // Arrange + Act
  const claudeProject = install("claude");
  const opencodeProject = install("opencode");

  // Assert
  assert.ok(fs.existsSync(path.join(claudeProject, ".claude/agents/meowth.md")));
  assert.ok(fs.existsSync(path.join(opencodeProject, ".opencode/agents/meowth.md")));
});

test("canonical agent identities are unique and match their filenames", () => {
  // Arrange
  const files = agentFiles();

  // Act — project each agent to the identity fields declared in its frontmatter.
  const rows = files.map((file) => {
    const source = read(path.join("agents", file));
    return {
      file: file.replace(/\.md$/, ""),
      name: source.match(/^name: (.+)$/m)?.[1],
      model: source.match(/^model: (.+)$/m)?.[1],
      color: source.match(/^color: "(#[0-9A-F]{6})"$/m)?.[1],
    };
  });
  const names = rows.map((row) => row.name);
  const colors = rows.map((row) => row.color);

  // Assert — offenders are collected into a list and that list must be empty.
  assert.equal(files.length, 17);
  assert.deepEqual(
    rows.filter((row) => row.name?.toLowerCase() !== row.file).map((row) => row.file),
    [],
    "every name must equal its filename",
  );
  assert.deepEqual(
    rows.filter((row) => !["haiku", "sonnet", "opus"].includes(row.model)).map((row) => row.file),
    [],
    "every model must be a known tier",
  );
  assert.deepEqual(
    rows.filter((row) => !row.color).map((row) => row.file),
    [],
    "every agent must declare an uppercase hex color",
  );
  assert.equal(new Set(names).size, names.length, "names must be unique");
  assert.equal(new Set(colors).size, colors.length, "colors must be unique");
});

test("canonical and installed agent frontmatter is valid YAML", () => {
  // Arrange — canonical files (copied verbatim for claude) plus the re-emitted output for
  // every harness; a mid-sentence ": ", stray quote, or bad indent would fail to parse.
  const files = agentFiles();
  const claude = install("claude");
  const opencode = install("opencode");
  const github = install("github");
  const targets = files.flatMap((file) => {
    const name = file.replace(/\.md$/, "");
    return [
      { id: `canonical/${name}`, path: path.join(ROOT, "agents", file) },
      { id: `claude/${name}`, path: path.join(claude, ".claude/agents", file) },
      { id: `opencode/${name}`, path: path.join(opencode, ".opencode/agents", `${name}.md`) },
      { id: `github/${name}`, path: path.join(github, ".github/agents", `${name}.agent.md`) },
    ];
  });

  // Act — parse each frontmatter block, keeping only the ones that failed.
  const failures = targets
    .map((target) => ({ id: target.id, error: frontmatterError(target.path) }))
    .filter((result) => result.error);

  // Assert
  assert.deepEqual(failures, [], "every agent frontmatter must parse as YAML");
});

test("plan contracts distinguish exact and guided execution", () => {
  // Arrange
  const mew = read("agents/mew.md");
  const meowth = read("agents/meowth.md");
  const magneton = read("agents/magneton.md");
  const plan = read("commands/plan-orchestrator.md");

  // Assert
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
  // Arrange
  const implement = read("commands/implement-orchestrator.md");
  const verify = read("commands/verify-orchestrator.md");
  const machop = read("agents/machop.md");
  const machoke = read("agents/machoke.md");

  // Assert
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
  // Arrange
  const review = read("commands/review-orchestrator.md");
  const kadabra = read("agents/kadabra.md");
  const mewtwo = read("agents/mewtwo.md");
  const alakazam = read("agents/alakazam.md");

  // Assert
  assert.match(review, /\$CACHE\/tmp\/review-<index>-<head_sha>\.diff/);
  assert.match(review, /delete.*temporary diff/i);
  assert.match(review, /material change/i);
  assert.match(kadabra, /DIFF_PATH/);
  assert.match(mewtwo, /DIFF_PATH/);
  assert.match(alakazam, /DIFF_PATH/);
});
