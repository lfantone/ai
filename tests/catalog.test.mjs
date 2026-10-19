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
  commands: { words: 450, description: 100 },
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

// The developer's own Claude config dir must never receive a test install.
const { CLAUDE_CONFIG_DIR: _developerClaudeHome, ...testEnv } = process.env;

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
      ...(options.args ?? []),
    ],
    {
      cwd: ROOT,
      stdio: "pipe",
      env: { ...testEnv, ...(options.env ?? {}) },
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
  const ditto = fs.readFileSync(
    path.join(project, ".codex/agents/ditto.toml"),
    "utf8",
  );
  assert.match(ditto, /^model = "gpt-5.6-terra"$/m);
  const mewtwo = fs.readFileSync(
    path.join(project, ".codex/agents/mewtwo.toml"),
    "utf8",
  );
  assert.match(mewtwo, /^model = "gpt-5.6-sol"$/m);
  assert.ok(
    fs.existsSync(path.join(project, ".agents/skills/gh-cli/SKILL.md")),
  );
  const investigateSkill = fs.readFileSync(
    path.join(project, ".agents/skills/investigate/SKILL.md"),
    "utf8",
  );
  assert.match(investigateSkill, /^name: investigate$/m);
  assert.doesNotMatch(investigateSkill, /\$ARGUMENTS/);
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
  const names = ["machop", "mewtwo"];

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

test("agents never pin an MCP server name, and the MCP agent stays read-only", () => {
  // Arrange — server names differ per install, so MCP access comes from inheriting tools
  const agents = agentFiles().map((file) => ({
    file,
    frontmatter: splitDoc(read(`agents/${file}`)).frontmatter,
  }));
  const ditto = agents.find(({ file }) => file === "ditto.md").frontmatter;

  // Act
  const pinned = agents.filter(({ frontmatter }) =>
    /mcp__/.test(
      `${frontmatter.tools ?? ""} ${frontmatter.disallowedTools ?? ""}`,
    ),
  );
  const denied = String(ditto.disallowedTools ?? "")
    .split(",")
    .map((name) => name.trim());

  // Assert
  assert.deepEqual(
    pinned.map(({ file }) => file),
    [],
    "no agent may name an MCP server in its tool lists",
  );
  assert.equal(
    ditto.tools,
    undefined,
    "Ditto inherits the session's MCP tools",
  );
  assert.deepEqual(
    ["Bash", "PowerShell", "Edit", "Write", "NotebookEdit"].filter(
      (tool) => !denied.includes(tool),
    ),
    [],
    "Ditto must not edit files or run commands",
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
  assert.equal(files.length, 3);
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
  const opencodeV2 = install("opencode-v2");
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
        id: `opencode-v2/${name}`,
        path: path.join(opencodeV2, ".opencode/agents", `${name}.md`),
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

test("installed Sonnet and Opus agents use the current model generation", () => {
  // Arrange — one agent per pinned tier, with the id each harness must emit
  const expected = [
    {
      dir: ".opencode/agents",
      suffix: ".md",
      agent: "ditto",
      model: "github-copilot/claude-sonnet-5.5",
    },
    {
      dir: ".opencode/agents",
      suffix: ".md",
      agent: "mewtwo",
      model: "github-copilot/claude-opus-5.5",
    },
    {
      dir: ".github/agents",
      suffix: ".agent.md",
      agent: "ditto",
      model: "claude-sonnet-5.5",
    },
    {
      dir: ".github/agents",
      suffix: ".agent.md",
      agent: "mewtwo",
      model: "claude-opus-5.5",
    },
  ];

  // Act
  const projects = {
    ".opencode/agents": install("opencode"),
    ".github/agents": install("github"),
  };
  const rows = expected.map((row) => ({
    ...row,
    source: fs.readFileSync(
      path.join(projects[row.dir], row.dir, row.agent + row.suffix),
      "utf8",
    ),
  }));

  // Assert
  assert.deepEqual(
    rows
      .filter(({ model, source }) => !source.includes(`\nmodel: ${model}\n`))
      .map(({ dir, agent, model }) => `${dir}/${agent} ≠ ${model}`),
    [],
    "every pinned tier must install the current Claude generation",
  );
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
      agent: "ditto",
      model: "anthropic/claude-sonnet-5-5",
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
      agent: "ditto",
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

test("command model pins: Claude keeps them, OpenCode maps them, command-skills drop them", () => {
  // Arrange — the commands that pin a tier, and OpenCode's default (Copilot) id per tier
  const copilot = {
    haiku: "github-copilot/claude-haiku-4.5",
    sonnet: "github-copilot/claude-sonnet-5.5",
    opus: "github-copilot/claude-opus-5.5",
  };
  const pinned = commandFiles()
    .map((file) => ({
      name: file.replace(/\.md$/, ""),
      canonical: splitDoc(read(`commands/${file}`)).frontmatter,
    }))
    .filter(({ canonical }) => canonical.model);
  const projects = {
    claude: install("claude"),
    opencode: install("opencode"),
    codex: install("codex"),
  };
  const frontmatterAt = (file) =>
    splitDoc(fs.readFileSync(file, "utf8")).frontmatter;

  // Act
  const rows = pinned.map(({ name, canonical }) => ({
    name,
    canonical,
    claude: frontmatterAt(
      path.join(projects.claude, ".claude/commands", `${name}.md`),
    ),
    opencode: frontmatterAt(
      path.join(projects.opencode, ".opencode/commands", `${name}.md`),
    ),
    codex: frontmatterAt(
      path.join(projects.codex, ".agents/skills", name, "SKILL.md"),
    ),
  }));

  // Assert
  assert.deepEqual(
    pinned.map(({ name }) => name).sort(),
    ["implement", "investigate", "plan"],
    "the phases that size their own model",
  );
  assert.deepEqual(
    rows
      .filter(
        ({ canonical, claude, opencode, codex }) =>
          !copilot[canonical.model] ||
          claude.model !== canonical.model ||
          claude.effort !== canonical.effort ||
          opencode.model !== copilot[canonical.model] ||
          "effort" in opencode ||
          "model" in codex ||
          "effort" in codex,
      )
      .map(({ name }) => name),
    [],
    "every pin must be a known tier that each harness keeps, maps, or drops",
  );
});

test("--prefix namespaces every command and every reference to one", () => {
  // Arrange — a bare `/plan`-style reference anywhere in the output means a missed rewrite
  const bareReference =
    /(?<![\w./-])\/(investigate|plan|implement|verify|ship|review)(?![\w-]|\.md)/;
  const options = { args: ["--prefix", "oct-"] };

  // Act
  const claude = install("claude", "pokemon", undefined, undefined, options);
  const github = install("github", "norse", undefined, undefined, options);
  const claudeFiles = [".claude/commands", ".claude/agents"].flatMap((dir) =>
    fs
      .readdirSync(path.join(claude, dir))
      .map((file) => path.join(claude, dir, file)),
  );
  const reviewSkill = splitDoc(
    fs.readFileSync(
      path.join(github, ".agents/skills/oct-review/SKILL.md"),
      "utf8",
    ),
  ).frontmatter;

  // Assert
  assert.deepEqual(fs.readdirSync(path.join(claude, ".claude/commands")), [
    "oct-implement.md",
    "oct-investigate.md",
    "oct-plan.md",
    "oct-review.md",
    "oct-ship.md",
    "oct-verify.md",
  ]);
  assert.deepEqual(
    claudeFiles
      .filter((file) => bareReference.test(fs.readFileSync(file, "utf8")))
      .map((file) => path.basename(file)),
    [],
    "every command reference must carry the prefix",
  );
  assert.equal(reviewSkill.name, "oct-review");
  assert.match(
    fs.readFileSync(path.join(github, ".github/agents/mimir.agent.md"), "utf8"),
    /Spawned by \/oct-review\./,
  );
});

test("Copilot and Codex workflow skills are user-run, never model-invoked", () => {
  // Arrange — Copilot code review activates any repo skill that looks relevant, and OpenCode
  // reads the same .agents/skills, so each tool needs its own opt-out
  const projects = { github: install("github"), codex: install("codex") };
  const skillDirs = { github: ".agents/skills", codex: ".agents/skills" };

  // Act
  const rows = Object.keys(projects).flatMap((harness) =>
    commandFiles().map((file) => {
      const name = file.replace(/\.md$/, "");
      return {
        id: `${harness}/${name}`,
        frontmatter: splitDoc(
          fs.readFileSync(
            path.join(projects[harness], skillDirs[harness], name, "SKILL.md"),
            "utf8",
          ),
        ).frontmatter,
      };
    }),
  );

  // Assert
  assert.deepEqual(
    rows
      .filter(
        ({ frontmatter }) =>
          frontmatter["disable-model-invocation"] !== true ||
          frontmatter.metadata?.["opencode/slash"] !== "true" ||
          frontmatter.metadata?.["opencode/autoinvoke"] !== "false" ||
          !/^Interactive workflow the user starts with [/$]/.test(
            frontmatter.description,
          ),
      )
      .map(({ id }) => id),
    [],
    "workflow skills must opt out of model invocation and say they are user-run",
  );
});

test("--skip leaves catalog entries out and rejects unknown names", () => {
  // Arrange
  const installer = path.join(ROOT, "scripts/install.mjs");

  // Act
  const project = install("github", "pokemon", undefined, undefined, {
    args: ["--skip", "tea-cli"],
  });
  const typo = spawnSync(
    process.execPath,
    [installer, "--harness", "github", "--skip", "tea-clie", "--dry-run"],
    { cwd: ROOT, encoding: "utf8", env: testEnv },
  );

  // Assert
  assert.equal(
    fs.existsSync(path.join(project, ".agents/skills/tea-cli")),
    false,
  );
  assert.ok(
    fs.existsSync(path.join(project, ".agents/skills/gh-cli/SKILL.md")),
  );
  assert.notEqual(typo.status, 0);
  assert.match(typo.stderr, /unknown tea-clie/);
});

test("--skip takes whole kinds: commands,skills installs only the agents", () => {
  // Arrange — OpenCode shares a Copilot install's .agents/skills and only needs its agents
  const options = { args: ["--skip", "commands,skills"] };

  // Act
  const project = install(
    "opencode-v2",
    "norse",
    undefined,
    undefined,
    options,
  );

  // Assert
  assert.deepEqual(
    fs.readdirSync(path.join(project, ".opencode/agents")).sort(),
    ["brokkr.md", "loki.md", "mimir.md"],
  );
  assert.deepEqual(
    [".opencode/commands", ".opencode/skills"].filter((dir) =>
      fs.existsSync(path.join(project, dir)),
    ),
    [],
  );
});

test("a Copilot install moves its old .github/skills copies and keeps the project's own", () => {
  // Arrange — an install from before the manifest, plus a skill the project owns
  const project = fs.mkdtempSync(path.join(os.tmpdir(), "ai-github-legacy-"));
  const seed = (relative) => {
    const file = path.join(project, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, "old");
  };
  seed(".github/skills/gh-cli/SKILL.md");
  seed(".github/skills/oct-plan/SKILL.md");
  seed(".github/skills/team-skill/SKILL.md");

  // Act
  install("github", "norse", undefined, project, {
    args: ["--prefix", "oct-"],
  });

  // Assert
  assert.deepEqual(
    [".github/skills/gh-cli", ".github/skills/oct-plan"].filter((relative) =>
      fs.existsSync(path.join(project, relative)),
    ),
    [],
    "catalog copies in the old dir would show twice in Copilot",
  );
  assert.ok(
    fs.existsSync(path.join(project, ".github/skills/team-skill/SKILL.md")),
  );
  assert.ok(
    fs.existsSync(path.join(project, ".agents/skills/gh-cli/SKILL.md")),
  );
  assert.ok(
    fs.existsSync(path.join(project, ".agents/skills/oct-plan/SKILL.md")),
  );
});

test("a GitHub-only install names no other forge and no other tool's instructions file", () => {
  // Arrange — a project that skips tea-cli must not point at Gitea, tea, or CLAUDE.md
  const project = install("github", "norse", undefined, undefined, {
    args: ["--prefix", "oct-", "--skip", "tea-cli"],
  });
  const files = (dir) =>
    fs
      .readdirSync(dir, { withFileTypes: true })
      .flatMap((entry) =>
        entry.isDirectory()
          ? files(path.join(dir, entry.name))
          : [path.join(dir, entry.name)],
      );

  // Act
  const installed = [".github", ".agents"].flatMap((dir) =>
    files(path.join(project, dir)),
  );

  // Assert
  assert.deepEqual(
    installed
      .filter((file) =>
        /tea-cli|gitea|\btea\b|CLAUDE\.md/i.test(fs.readFileSync(file, "utf8")),
      )
      .map((file) => path.relative(project, file)),
    [],
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
      { cwd: ROOT, encoding: "utf8", env: testEnv },
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

test("Claude global install honours CLAUDE_CONFIG_DIR", () => {
  // Arrange
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "ai-claude-home-"));
  const config = fs.mkdtempSync(path.join(os.tmpdir(), "ai-claude-config-"));
  const expected = [
    "agents/mewtwo.md",
    "commands/review.md",
    "skills/gh-cli/SKILL.md",
    "CLAUDE.md",
  ];

  // Act
  install("claude", "pokemon", undefined, undefined, {
    global: true,
    env: { HOME: home, CLAUDE_CONFIG_DIR: config },
  });

  // Assert
  assert.deepEqual(
    expected.filter((relative) => !fs.existsSync(path.join(config, relative))),
    [],
    "the catalog and the instructions block land in CLAUDE_CONFIG_DIR",
  );
  assert.equal(fs.existsSync(path.join(home, ".claude")), false);
});

test("every command resolves one shared work dir, never a per-worktree path", () => {
  // Arrange — the exact line, so every worktree and every command lands in the same folder
  const workDir =
    "W=~/.agents/work$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\\.git$||')";
  const commands = commandFiles().map((file) => ({
    file,
    source: read(`commands/${file}`),
  }));

  // Act
  const offenders = commands.filter(
    ({ source }) =>
      !source.includes(workDir) ||
      /(?<!~\/)\.agents\/work|info\/exclude/.test(source),
  );

  // Assert
  assert.deepEqual(
    offenders.map(({ file }) => file),
    [],
    "every command needs the shared W= line and no repo-relative state path",
  );
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
      file: "commands/investigate.md",
      requirements: [
        {
          name: "the ticket waits for approval",
          pattern: /Ticket — HARD STOP/,
        },
        { name: "investigation never edits code", pattern: /never edit code/ },
        {
          name: "tracker posts need a yes",
          pattern: /only on an explicit yes/,
        },
      ],
    },
    {
      file: "commands/plan.md",
      requirements: [
        { name: "the plan waits for approval", pattern: /Plan — HARD STOP/ },
        { name: "planning never edits code", pattern: /never edit code/ },
        {
          name: "the plan records the security surface",
          pattern: /- \*\*Security surface\*\* —/,
        },
      ],
    },
    {
      file: "commands/implement.md",
      requirements: [
        {
          name: "only an approved plan is implemented",
          pattern: /`plan\.md`\s+with\s+`Status: approved`/,
        },
        {
          name: "a changed decision stops for the user",
          pattern:
            /changes\s+a\s+decision\s+or\s+a\s+criterion\s+→\s+stop\s+and\s+ask/,
        },
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
        { name: "verification fixes nothing", pattern: /Fix nothing here/ },
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
      file: "commands/review.md",
      requirements: [
        {
          name: "publishing waits for a reply",
          pattern: /Publish — HARD STOP/,
        },
        {
          name: "replies need a yes",
          pattern: /reply\s+verbatim[^.]*post\s+on\s+yes/,
        },
        {
          name: "disagreements stay open",
          pattern: /Never\s+resolve\s+`disagree`\s+or\s+`question`/,
        },
        {
          name: "the reviewer gets the security surface",
          pattern: /criteria\s+and\s+security\s+surface/,
        },
        {
          name: "posted findings are not posted twice",
          pattern: /findings\s+without\s+a\s+comment\s+id/,
        },
      ],
    },
    {
      file: "agents/mewtwo.md",
      requirements: [
        {
          name: "review stays on the delta",
          pattern: /Never\s+audit\s+untouched\s+code/,
        },
        {
          name: "the given security surface is checked first",
          pattern: /the given\s+surface first/,
        },
        {
          name: "unlogged plan departures are flagged",
          pattern: /plan\s+departures\s+not\s+logged/,
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

test("OpenCode v2 agents use permission rules, effort variants, and only supported sampling", () => {
  // Arrange — expectations checked against `opencode debug agents` on OpenCode 2.0.20
  const expected = [
    {
      provider: "copilot",
      agent: "machop",
      model: "github-copilot/claude-haiku-4.5",
      temperature: 0.1,
    },
    {
      provider: "copilot",
      agent: "mewtwo",
      model: "github-copilot/claude-opus-5.5#high",
    },
    {
      provider: "copilot",
      agent: "ditto",
      model: "github-copilot/claude-sonnet-5.5",
    },
    {
      provider: "openai",
      agent: "machop",
      model: "openai/gpt-5.4-mini#low",
      temperature: 0.1,
    },
    { provider: "openai", agent: "mewtwo", model: "openai/gpt-5.6-sol#high" },
  ];
  const rules = {
    machop: ["edit=allow", "shell=allow", "lsp=allow", "webfetch=deny"],
    ditto: ["edit=deny", "shell=deny", "webfetch=deny"],
  };

  // Act
  const projects = {
    copilot: install("opencode-v2"),
    openai: install("opencode-v2", "pokemon", "openai"),
  };
  const frontmatter = (provider, agent) =>
    splitDoc(
      fs.readFileSync(
        path.join(projects[provider], ".opencode/agents", `${agent}.md`),
        "utf8",
      ),
    ).frontmatter;
  const rows = expected.map((row) => ({
    ...row,
    fm: frontmatter(row.provider, row.agent),
  }));
  const permissions = Object.keys(rules).map((agent) => ({
    agent,
    actual: frontmatter("copilot", agent).permissions.map(
      (rule) => `${rule.action}=${rule.effect}`,
    ),
  }));

  // Assert
  assert.deepEqual(
    rows
      .filter(
        ({ fm, model, temperature }) =>
          fm.model !== model || fm.request?.body?.temperature !== temperature,
      )
      .map(({ provider, agent }) => `${provider}/${agent}`),
    [],
    "effort maps to a variant only where the model has one; sampling only where supported",
  );
  assert.deepEqual(
    rows
      .filter(({ fm }) =>
        ["permission", "reasoningEffort", "temperature"].some(
          (key) => key in fm,
        ),
      )
      .map(({ provider, agent }) => `${provider}/${agent}`),
    [],
    "no v1 frontmatter keys in v2 agents",
  );
  assert.deepEqual(
    permissions
      .filter(({ agent, actual }) => actual.join() !== rules[agent].join())
      .map(({ agent }) => agent),
    [],
    "v2 permission rules mirror the canonical tools",
  );
});
