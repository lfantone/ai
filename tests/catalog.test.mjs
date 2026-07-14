import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const read = (relativePath) => fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const agentFiles = () =>
  fs.readdirSync(path.join(ROOT, "agents")).filter((file) => file.endsWith(".md"));

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

test("installed and canonical agent descriptions are YAML-safe", () => {
  // Arrange
  const files = agentFiles();
  const opencode = install("opencode");
  const github = install("github");
  const descOf = (root, dir, name, suffix) =>
    fs
      .readFileSync(path.join(root, dir, name + suffix), "utf8")
      .match(/^description: (.*)$/m)?.[1];
  const isJsonString = (value) => {
    try {
      return typeof JSON.parse(value) === "string";
    } catch {
      return false;
    }
  };
  const isQuoted = (value) => /^".*"$/.test(value) || /^'.*'$/.test(value);

  // Act — opencode/github re-emit the description (installer JSON-quotes it); claude copies
  // canonical frontmatter verbatim, so the canonical value must itself be YAML-safe.
  const emitted = files.flatMap((file) => {
    const name = file.replace(/\.md$/, "");
    return [
      { id: `opencode/${name}`, value: descOf(opencode, ".opencode/agents", name, ".md") },
      { id: `github/${name}`, value: descOf(github, ".github/agents", name, ".agent.md") },
    ];
  });
  const canonical = files.map((file) => ({
    id: file,
    value: read(path.join("agents", file)).match(/^description: (.*)$/m)?.[1],
  }));

  // Assert — every re-emitted value parses as a JSON (== YAML double-quoted) string, and no
  // unquoted canonical value contains ": ", which YAML would read as a nested mapping key.
  assert.deepEqual(
    emitted.filter((entry) => !isJsonString(entry.value)).map((entry) => entry.id),
    [],
    "re-emitted descriptions must be quoted scalars",
  );
  assert.deepEqual(
    canonical
      .filter((entry) => !isQuoted(entry.value) && entry.value.includes(": "))
      .map((entry) => entry.id),
    [],
    'unquoted canonical descriptions must not contain ": "',
  );
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
