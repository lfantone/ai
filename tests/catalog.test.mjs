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

const commandFiles = () =>
  fs
    .readdirSync(path.join(ROOT, "commands"))
    .filter((file) => file.endsWith(".md"));

const skillDirs = () =>
  fs
    .readdirSync(path.join(ROOT, "skills"), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);

// Frontmatter object + body text of a catalog Markdown file.
const splitDoc = (source) => {
  const match = source.match(/^---\n([\s\S]*?)\n---\n?/);
  return {
    frontmatter: match ? yaml.load(match[1]) : {},
    body: source.slice(match?.[0].length ?? 0),
  };
};

// lstat-based: a dangling symlink still counts as present.
const isLink = (file) => {
  try {
    return fs.lstatSync(file).isSymbolicLink();
  } catch {
    return false;
  }
};

const wordCount = (text) => text.split(/\s+/).filter(Boolean).length;

// Size budgets: descriptions load in every session, bodies on every activation.
const BUDGETS = {
  agents: { words: 300, description: 160 },
  commands: { words: 450, description: 160 },
  skills: { words: 600, description: 300 },
};
const INSTRUCTIONS_WORD_BUDGET = 120;

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
  options = {},
) => {
  const providerArgs = provider ? ["--provider", provider] : [];
  const scopeArgs = options.global ? ["--global"] : ["--project", project];
  execFileSync(
    process.execPath,
    [
      path.join(ROOT, "scripts/install.mjs"),
      "--harness",
      harness,
      "--names",
      names,
      ...scopeArgs,
      ...providerArgs,
    ],
    {
      cwd: ROOT,
      stdio: "pipe",
      env: { ...process.env, ...(options.env ?? {}) },
    },
  );
  return project;
};

test("GitHub agents with MCP dependencies do not receive a restrictive tool list", () => {
  // Arrange + Act
  const project = install("github");

  // Assert
  const ditto = fs.readFileSync(
    path.join(project, ".github/agents/ditto.agent.md"),
    "utf8",
  );
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
    fs.existsSync(path.join(project, ".opencode/agents/ditto.md")),
    false,
  );
  assert.ok(fs.existsSync(path.join(project, ".opencode/agents/loki.md")));
});

test("Codex installs TOML agents and skills in Codex discovery roots", () => {
  // Arrange
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-codex-"));

  // Act
  install("codex", "pokemon", undefined, project);

  // Assert
  const machop = fs.readFileSync(
    path.join(project, ".codex/agents/machop.toml"),
    "utf8",
  );
  assert.match(machop, /^name = "machop"$/m);
  assert.match(machop, /^description = /m);
  assert.match(machop, /^model = "gpt-5.6-luna"$/m);
  assert.match(machop, /^model_reasoning_effort = "low"$/m);
  assert.match(machop, /^sandbox_mode = "workspace-write"$/m);
  assert.match(machop, /^developer_instructions = /m);
  assert.doesNotMatch(machop, /^---$/m);
  const machoke = fs.readFileSync(
    path.join(project, ".codex/agents/machoke.toml"),
    "utf8",
  );
  assert.match(machoke, /^model = "gpt-5.6-terra"$/m);
  const mewtwo = fs.readFileSync(
    path.join(project, ".codex/agents/mewtwo.toml"),
    "utf8",
  );
  assert.match(mewtwo, /^model = "gpt-5.6-sol"$/m);
  assert.ok(
    fs.existsSync(path.join(project, ".agents/skills/gh-cli/SKILL.md")),
  );
  const ticketSkill = fs.readFileSync(
    path.join(project, ".agents/skills/ticket/SKILL.md"),
    "utf8",
  );
  assert.match(ticketSkill, /^name: ticket$/m);
  assert.doesNotMatch(ticketSkill, /\$ARGUMENTS/);
  assert.equal(fs.existsSync(path.join(project, ".codex/commands")), false);
});

test("Codex global install uses ~/.codex for agents and ~/.agents for skills", () => {
  // Arrange
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "ai-codex-home-"));
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-codex-project-"));

  // Act
  install("codex", "pokemon", undefined, project, {
    global: true,
    env: { HOME: home },
  });

  // Assert
  assert.ok(fs.existsSync(path.join(home, ".codex/agents/machop.toml")));
  assert.ok(fs.existsSync(path.join(home, ".agents/skills/gh-cli/SKILL.md")));
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
          // the retired orchestrator that spawned Porygon goes with it
          fs.existsSync(review),
      )
      .map(({ harness }) => harness),
    [],
  );
});

test("code-aware agents receive LSP access and navigation guidance", () => {
  // Arrange
  const project = install("opencode");
  const names = ["machoke", "machop", "mewtwo"];

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
  assert.equal(files.length, 4);
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
  assert.match(opencodeAgent, /^model: github-copilot\/claude-opus-5\.5$/m);
  assert.match(githubAgent, /^model: claude-opus-5\.5$/m);
});

test("OpenCode providers map every capability tier", () => {
  // Arrange
  const expected = [
    {
      provider: "claude",
      agent: "machop",
      model: "anthropic/claude-haiku-4-5",
    },
    {
      provider: "claude",
      agent: "machoke",
      model: "anthropic/claude-sonnet-5",
    },
    {
      provider: "claude",
      agent: "mewtwo",
      model: "anthropic/claude-opus-5-5",
    },
    {
      provider: "openai",
      agent: "machop",
      model: "openai/gpt-5.4-mini",
    },
    {
      provider: "openai",
      agent: "machoke",
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

test("catalog text stays within its size budgets", () => {
  // Arrange
  const docs = [
    ...agentFiles().map((file) => ({ kind: "agents", id: `agents/${file}` })),
    ...commandFiles().map((file) => ({
      kind: "commands",
      id: `commands/${file}`,
    })),
    ...skillDirs().map((dir) => ({
      kind: "skills",
      id: `skills/${dir}/SKILL.md`,
    })),
  ];

  // Act
  const rows = docs.map(({ kind, id }) => {
    const { frontmatter, body } = splitDoc(read(id));
    return {
      id,
      kind,
      words: wordCount(body),
      description: String(frontmatter.description ?? "").length,
    };
  });
  const instructionsWords = wordCount(read("instructions/AGENTS.md"));

  // Assert
  assert.deepEqual(
    rows
      .filter((row) => row.words > BUDGETS[row.kind].words)
      .map((row) => `${row.id}: ${row.words} words`),
    [],
    "every body must fit its word budget",
  );
  assert.deepEqual(
    rows
      .filter(
        (row) =>
          row.description === 0 ||
          row.description > BUDGETS[row.kind].description,
      )
      .map((row) => `${row.id}: ${row.description} chars`),
    [],
    "every description must exist and fit its character budget",
  );
  assert.ok(
    instructionsWords <= INSTRUCTIONS_WORD_BUDGET,
    `instructions/AGENTS.md: ${instructionsWords} words`,
  );
});

test("commands reference only shipped agents and every agent has a caller", () => {
  // Arrange
  const agents = agentFiles().map(
    (file) => splitDoc(read(`agents/${file}`)).frontmatter.name,
  );

  // Act — backticked capitalised words in a command are agent spawns.
  const referenced = [
    ...new Set(
      commandFiles().flatMap((file) =>
        [...read(`commands/${file}`).matchAll(/`([A-Z][a-z]+)`/g)].map(
          (match) => match[1],
        ),
      ),
    ),
  ];

  // Assert
  assert.deepEqual(
    referenced.filter((name) => !agents.includes(name)),
    [],
    "every agent a command names must exist in agents/",
  );
  assert.deepEqual(
    agents.filter((name) => !referenced.includes(name)),
    [],
    "every agent must be spawned by some command",
  );
});

test("global install maintains one instructions block and keeps user content", () => {
  // Arrange
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "ai-instructions-home-"));
  const file = path.join(home, ".claude/CLAUDE.md");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, "# Mine\n\nKeep me.\n");
  const options = { global: true, env: { HOME: home } };

  // Act — installing twice must replace the block, not append a second one.
  install("claude", "pokemon", undefined, undefined, options);
  install("claude", "pokemon", undefined, undefined, options);
  const content = fs.readFileSync(file, "utf8");

  // Assert
  assert.match(content, /^# Mine\n\nKeep me\.\n/);
  assert.equal(content.split("<!-- ai-catalog-begin -->").length - 1, 1);
  assert.ok(content.includes(read("instructions/AGENTS.md").trim()));
});

test("project installs leave instruction files to the project", () => {
  // Arrange + Act
  const project = install("claude");

  // Assert
  assert.equal(fs.existsSync(path.join(project, "CLAUDE.md")), false);
  assert.equal(fs.existsSync(path.join(project, ".claude/CLAUDE.md")), false);
});

test("installs remove retired catalog entries even without a manifest", () => {
  // Arrange — a pre-manifest install: retired names, a kept agent under the other naming
  // set, a dangling symlink from the old deploy scripts, and one external agent.
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-retired-"));
  const at = (relative) => path.join(project, ".opencode", relative);
  const seed = (relative) => {
    fs.mkdirSync(path.dirname(at(relative)), { recursive: true });
    fs.writeFileSync(at(relative), "old");
  };
  seed("agents/abra.md");
  seed("agents/brokkr.md");
  seed("agents/cavecrew-builder.md");
  seed("commands/plan-orchestrator.md");
  seed("skills/repo-learnings/SKILL.md");
  fs.symlinkSync(
    "../../.agents/.opencode/agents/kadabra.md",
    at("agents/kadabra.md"),
  );

  // Act
  install("opencode", "pokemon", undefined, project);

  // Assert
  const leftovers = [
    "agents/abra.md",
    "agents/brokkr.md",
    "agents/kadabra.md",
    "commands/plan-orchestrator.md",
    "skills/repo-learnings",
  ].filter((relative) => fs.existsSync(at(relative)) || isLink(at(relative)));
  assert.deepEqual(leftovers, [], "retired entries must be removed");
  assert.equal(
    fs.readFileSync(at("agents/cavecrew-builder.md"), "utf8"),
    "old",
  );
  assert.ok(fs.existsSync(at("agents/machop.md")));
});

test("project installs clear the retired workflow caches and keep unknown files", () => {
  // Arrange
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-caches-"));
  const seed = (relative) => {
    const file = path.join(project, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "old");
  };
  seed(".claude/cache/plan-IE-1.md");
  seed(".claude/cache/.plan-draft.md");
  seed(".claude/cache/review-7.md");
  seed(".claude/cache/impl-brief-7-abc.md");
  seed(".claude/cache/tmp/review-7-abc.diff");
  seed(".claude/cache/notes.txt");
  seed(".agents/cache/repo-profile.md");

  // Act
  install("claude", "pokemon", undefined, project);

  // Assert
  assert.deepEqual(fs.readdirSync(path.join(project, ".claude/cache")), [
    "notes.txt",
  ]);
  assert.equal(fs.existsSync(path.join(project, ".agents/cache")), false);
});

test("global installs leave the harness's own cache alone", () => {
  // Arrange
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "ai-global-cache-"));
  const cache = path.join(home, ".claude/cache");
  fs.mkdirSync(cache, { recursive: true });
  fs.writeFileSync(path.join(cache, "changelog.md"), "harness");
  fs.writeFileSync(path.join(cache, "plan-notes.md"), "harness");

  // Act
  install("claude", "pokemon", undefined, undefined, {
    global: true,
    env: { HOME: home },
  });

  // Assert
  assert.deepEqual(fs.readdirSync(cache).sort(), [
    "changelog.md",
    "plan-notes.md",
  ]);
});

test("an install clears retired names from every harness's dirs", () => {
  // Arrange — retired entries under two other harnesses, plus a current opencode agent
  // that belongs to that harness's own install.
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-cross-harness-"));
  const seed = (relative) => {
    const file = path.join(project, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "old");
  };
  seed(".opencode/agents/abra.md");
  seed(".opencode/agents/machop.md");
  seed(".github/agents/tyr.agent.md");
  seed(".github/skills/plan-orchestrator/SKILL.md");

  // Act
  install("claude", "pokemon", undefined, project);

  // Assert
  assert.deepEqual(
    [
      ".opencode/agents/abra.md",
      ".github/agents/tyr.agent.md",
      ".github/skills/plan-orchestrator",
    ].filter((relative) => fs.existsSync(path.join(project, relative))),
    [],
    "retired names must go from every harness",
  );
  assert.equal(
    fs.readFileSync(path.join(project, ".opencode/agents/machop.md"), "utf8"),
    "old",
  );
});

test("commands and the reviewer retain their explicit safety gates", () => {
  // Arrange
  const guardrails = [
    {
      file: "commands/ticket.md",
      requirements: [
        { name: "the plan waits for approval", pattern: /Plan — HARD STOP/ },
        { name: "no edits before approval", pattern: /No edits before that/ },
        { name: "never commits", pattern: /Never commit\./ },
      ],
    },
    {
      file: "commands/verify.md",
      requirements: [
        {
          name: "environment is confirmed",
          pattern: /Environment — HARD STOP/,
        },
        {
          name: "shared environments are not disposable",
          pattern: /Never assume a shared environment is disposable/,
        },
        { name: "ticket posts need a yes", pattern: /only on an explicit yes/ },
      ],
    },
    {
      file: "commands/ship.md",
      requirements: [
        { name: "commit needs a yes", pattern: /Commit on yes/ },
        { name: "push needs a yes", pattern: /origin HEAD` on yes/ },
        { name: "PR creation needs a yes", pattern: /create on yes/ },
        { name: "merge stays manual", pattern: /Merging stays with the user/ },
      ],
    },
    {
      file: "commands/pr-review.md",
      requirements: [
        {
          name: "publishing waits for a reply",
          pattern: /Publish — HARD STOP/,
        },
        { name: "human threads stay open", pattern: /never human threads/ },
      ],
    },
    {
      file: "commands/pr-feedback.md",
      requirements: [
        { name: "verdicts are confirmed", pattern: /Checkpoint — HARD STOP/ },
        {
          name: "replies are confirmed",
          pattern: /Reply and resolve — HARD STOP/,
        },
        {
          name: "disagreements stay open",
          pattern: /Never resolve `disagree`/,
        },
      ],
    },
    {
      file: "agents/mewtwo.md",
      requirements: [
        {
          name: "review stays on the delta",
          pattern: /Never audit untouched code/,
        },
      ],
    },
  ].map((guardrail) => ({ ...guardrail, source: read(guardrail.file) }));

  // Act
  const missing = guardrails.flatMap(({ file, requirements, source }) =>
    requirements
      .filter(({ pattern }) => !pattern.test(source))
      .map(({ name }) => `${file}: ${name}`),
  );

  // Assert
  assert.deepEqual(
    missing,
    [],
    "every workflow must keep its explicit safety gates",
  );
});

test("every agent installs under a Norse name with --names norse", () => {
  // Arrange
  const canonical = agentFiles().map((file) => file.replace(/\.md$/, ""));

  // Act
  const project = install("opencode", "norse");
  const installed = fs
    .readdirSync(path.join(project, ".opencode/agents"))
    .map((file) => file.replace(/\.md$/, ""));

  // Assert
  assert.deepEqual(
    installed.filter((name) => canonical.includes(name)),
    [],
    "every agent needs a NORSE entry in scripts/install.mjs",
  );
  assert.equal(installed.length, canonical.length);
});
