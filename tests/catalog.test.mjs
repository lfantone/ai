import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import * as yaml from "js-yaml";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const agentFiles = () =>
  fs
    .readdirSync(path.join(ROOT, "agents"))
    .filter((file) => file.endsWith(".md"));

// The YAML parse error for a file's `---` frontmatter, or null when it parses cleanly.
const frontmatterError = (filePath) => {
  const block = fs
    .readFileSync(filePath, "utf8")
    .match(/^---\n([\s\S]*?)\n---/)?.[1];
  if (block == null) return "no frontmatter block";
  try {
    yaml.load(block);
    return null;
  } catch (error) {
    return error.message.split("\n")[0];
  }
};

const install = (
  harness,
  names = "pokemon",
  provider,
  project = fs.mkdtempSync(path.join(os.tmpdir(), `ai-${harness}-`)),
) => {
  const providerArgs = provider ? ["--provider", provider] : [];
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
      ...providerArgs,
    ],
    { cwd: ROOT, stdio: "pipe" },
  );
  return project;
};

test("GitHub agents with MCP dependencies do not receive a restrictive tool list", () => {
  // Arrange + Act
  const project = install("github");

  // Assert
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

test("installer refreshes catalog entries without removing external entries", () => {
  // Arrange
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-install-clean-"));
  install("opencode", "pokemon", undefined, project);
  const external = path.join(project, ".opencode/skills/external/SKILL.md");
  fs.mkdirSync(path.dirname(external), { recursive: true });
  fs.writeFileSync(external, "external");

  // Act
  install("opencode", "norse", undefined, project);

  // Assert
  assert.equal(fs.readFileSync(external, "utf8"), "external");
  assert.equal(
    fs.existsSync(path.join(project, ".opencode/agents/abra.md")),
    false,
  );
  assert.ok(fs.existsSync(path.join(project, ".opencode/agents/skadi.md")));
});

test("installer removes legacy Porygon agents without removing external agents", () => {
  // Arrange
  const cases = [
    { harness: "claude", dir: ".claude" },
    { harness: "opencode", dir: ".opencode" },
  ].map(({ harness, dir }) => {
    const project = fs.mkdtempSync(path.join(os.tmpdir(), `ai-${harness}-`));
    const agentsDir = path.join(project, dir, "agents");
    const legacy = path.join(agentsDir, "porygon.md");
    const external = path.join(agentsDir, "external.md");
    const review = path.join(project, dir, "commands/review-orchestrator.md");
    fs.mkdirSync(agentsDir, { recursive: true });
    fs.writeFileSync(
      legacy,
      "# Porygon — Verify line anchors\nMechanical and precise. Your only job: make each finding's\n",
    );
    fs.writeFileSync(external, "external");
    fs.mkdirSync(path.dirname(review), { recursive: true });
    fs.writeFileSync(review, "Spawn Porygon");
    return { harness, project, legacy, external, review };
  });

  // Act
  cases.forEach(({ harness, project }) =>
    install(harness, "pokemon", undefined, project),
  );

  // Assert
  assert.deepEqual(
    cases
      .filter(
        ({ legacy, external, review }) =>
          fs.existsSync(legacy) ||
          !fs.existsSync(external) ||
          fs.readFileSync(review, "utf8").includes("Porygon"),
      )
      .map(({ harness }) => harness),
    [],
  );
});

test("code-aware agents receive LSP access and navigation guidance", () => {
  // Arrange
  const project = install("opencode");
  const names = [
    "abra",
    "alakazam",
    "dugtrio",
    "eevee",
    "growlithe",
    "hypno",
    "machamp",
    "machoke",
    "machop",
    "meowth",
    "mew",
    "mewtwo",
  ];

  // Act
  const rows = names.map((name) => ({
    name,
    canonical: read(`agents/${name}.md`),
    installed: fs.readFileSync(
      path.join(project, ".opencode/agents", `${name}.md`),
      "utf8",
    ),
  }));

  // Assert
  assert.deepEqual(
    rows
      .filter(
        ({ canonical, installed }) =>
          !/^tools: .*\bLSP\b/m.test(canonical) ||
          !/^## Code navigation$/m.test(canonical) ||
          !/^  lsp: allow$/m.test(installed),
      )
      .map(({ name }) => name),
    [],
    "every code-aware agent must prefer and receive LSP access",
  );
});

test("GitHub agents with portable tools retain a least-privilege tool list", () => {
  // Arrange + Act
  const project = install("github");

  // Assert
  const machop = fs.readFileSync(
    path.join(project, ".github/agents/machop.agent.md"),
    "utf8",
  );
  assert.match(machop, /^tools: \[.*"read".*"write".*\]$/m);
});

test("precise and fast plan authors install under both naming sets", () => {
  // Arrange + Act
  const pokemonProject = install("github");
  const norseProject = install("github", "norse");

  // Assert
  assert.ok(
    fs.existsSync(path.join(pokemonProject, ".github/agents/meowth.agent.md")),
  );
  assert.ok(
    fs.existsSync(path.join(norseProject, ".github/agents/hermod.agent.md")),
  );
});

test("all harnesses install the fast plan author", () => {
  // Arrange + Act
  const claudeProject = install("claude");
  const opencodeProject = install("opencode");

  // Assert
  assert.ok(
    fs.existsSync(path.join(claudeProject, ".claude/agents/meowth.md")),
  );
  assert.ok(
    fs.existsSync(path.join(opencodeProject, ".opencode/agents/meowth.md")),
  );
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
    rows
      .filter((row) => row.name?.toLowerCase() !== row.file)
      .map((row) => row.file),
    [],
    "every name must equal its filename",
  );
  assert.deepEqual(
    rows
      .filter((row) => !["haiku", "sonnet", "opus"].includes(row.model))
      .map((row) => row.file),
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
      {
        id: `opencode/${name}`,
        path: path.join(opencode, ".opencode/agents", `${name}.md`),
      },
      {
        id: `github/${name}`,
        path: path.join(github, ".github/agents", `${name}.agent.md`),
      },
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

test("orchestrators omit stale memory and redundant verification stages", () => {
  // Arrange
  const commandFiles = fs
    .readdirSync(path.join(ROOT, "commands"))
    .filter((file) => file.endsWith(".md"));

  // Act
  const commandCorpus = commandFiles
    .map((file) => read(`commands/${file}`))
    .join("\n");
  const agentCorpus = agentFiles()
    .map((file) => read(`agents/${file}`))
    .join("\n");
  const plan = read("commands/plan-orchestrator.md");
  const installedProject = install("opencode");

  // Assert
  assert.doesNotMatch(
    commandCorpus,
    /repo-learnings|learnings\.md|\bPorygon\b/,
  );
  assert.doesNotMatch(
    agentCorpus,
    /repo-learnings|learnings\.md|\bPorygon\b|relevant learnings/i,
  );
  assert.doesNotMatch(plan, /\bDugtrio\b/);
  assert.equal(fs.existsSync(path.join(ROOT, "agents/porygon.md")), false);
  assert.equal(
    fs.existsSync(path.join(ROOT, "skills/repo-learnings/SKILL.md")),
    false,
  );
  assert.equal(
    fs.existsSync(
      path.join(installedProject, ".opencode/skills/repo-learnings"),
    ),
    false,
  );
});

test("every orchestrator accounts for delegated output", () => {
  // Arrange
  const commandFiles = fs
    .readdirSync(path.join(ROOT, "commands"))
    .filter((file) => file.endsWith(".md"));

  // Act
  const missing = commandFiles.filter(
    (file) => !/Never silently omit a sub-agent/.test(read(`commands/${file}`)),
  );

  // Assert
  assert.deepEqual(
    missing,
    [],
    "every orchestrator must account for every delegated item",
  );
});

test("installed Opus agents use the current model generation", () => {
  // Arrange
  const agent = "mewtwo";

  // Act
  const opencodeProject = install("opencode");
  const githubProject = install("github");
  const opencodeAgent = fs.readFileSync(
    path.join(opencodeProject, ".opencode/agents", `${agent}.md`),
    "utf8",
  );
  const githubAgent = fs.readFileSync(
    path.join(githubProject, ".github/agents", `${agent}.agent.md`),
    "utf8",
  );

  // Assert
  assert.match(opencodeAgent, /^model: github-copilot\/claude-opus-5$/m);
  assert.match(githubAgent, /^model: claude-opus-5$/m);
});

test("OpenCode providers map every capability tier", () => {
  // Arrange
  const expected = [
    {
      provider: "claude",
      agent: "magneton",
      model: "anthropic/claude-haiku-4-5",
    },
    {
      provider: "claude",
      agent: "dugtrio",
      model: "anthropic/claude-sonnet-5",
    },
    {
      provider: "claude",
      agent: "mewtwo",
      model: "anthropic/claude-opus-5",
    },
    {
      provider: "openai",
      agent: "magneton",
      model: "openai/gpt-5.4-mini",
    },
    {
      provider: "openai",
      agent: "dugtrio",
      model: "openai/gpt-5.3-codex-spark",
    },
    {
      provider: "openai",
      agent: "mewtwo",
      model: "openai/gpt-5.6-sol",
    },
  ];

  // Act
  const projects = Object.fromEntries(
    ["claude", "openai"].map((provider) => [
      provider,
      install("opencode", "pokemon", provider),
    ]),
  );
  const rows = expected.map(({ provider, agent, model }) => ({
    provider,
    agent,
    model,
    source: fs.readFileSync(
      path.join(projects[provider], ".opencode/agents", `${agent}.md`),
      "utf8",
    ),
  }));

  // Assert
  assert.deepEqual(
    rows
      .filter(({ model, source }) => !source.includes(`model: ${model}`))
      .map(({ provider, agent }) => `${provider}/${agent}`),
    [],
    "every provider must map all abstract tiers",
  );
});

test("installer rejects unsupported provider combinations", () => {
  // Arrange
  const installer = path.join(ROOT, "scripts/install.mjs");
  const cases = [
    { harness: "opencode", provider: "unknown", message: "must be" },
    { harness: "github", provider: "openai", message: "only supported" },
    { harness: "claude", provider: "openai", message: "only supported" },
  ];

  // Act
  const rows = cases.map(({ harness, provider, message }) => {
    const result = spawnSync(
      process.execPath,
      [installer, "--harness", harness, "--provider", provider, "--dry-run"],
      { cwd: ROOT, encoding: "utf8" },
    );
    return { harness, message, result };
  });

  // Assert
  assert.deepEqual(
    rows
      .filter(
        ({ message, result }) =>
          result.status === 0 || !result.stderr.includes(message),
      )
      .map(({ harness }) => harness),
    [],
    "unsupported model families must fail with an actionable error",
  );
});
