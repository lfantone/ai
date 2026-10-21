#!/usr/bin/env node
/**
 * Catalog installer — builds the canonical agents/commands/skills for a harness and
 * installs them project-wise or globally. A global install also maintains the
 * instructions/AGENTS.md block in the harness's user-level instructions file.
 * Zero dependencies.
 *
 *   ./scripts/install.mjs --harness <opencode|opencode-v2|github|claude|codex> [options]
 *
 * Options:
 *   --harness <name>      opencode | opencode-v2 | github (Copilot CLI/VS Code/coding agent) |
 *                         claude | codex
 *   --global              install to the user-level config dir (default: project);
 *                         Claude Code's is $CLAUDE_CONFIG_DIR when set, else ~/.claude
 *   --project <dir>       target project dir for a project install (default: cwd)
 *   --names <set>         pokemon (default) | norse
 *   --prefix <p>          namespace the commands and every reference to them (e.g. oct-)
 *   --skip <a,b>          leave these catalog entries out (e.g. tea-cli), or whole kinds
 *                         (`commands,skills` installs only the agents)
 *   --provider <name>     OpenCode (v1/v2) only: copilot (default) | claude | openai
 *   --dry-run             print what would be written, write nothing
 */
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// ---------------------------------------------------------------------------
// Maps (single source of truth for every harness)
// ---------------------------------------------------------------------------
const MODEL_MAP = {
  opencode: {
    copilot: {
      haiku: "github-copilot/claude-haiku-5.5",
      sonnet: "github-copilot/claude-sonnet-5.5",
      opus: "github-copilot/claude-opus-5.5",
    },
    claude: {
      haiku: "anthropic/claude-haiku-5-5",
      sonnet: "anthropic/claude-sonnet-5-5",
      opus: "anthropic/claude-opus-5-5",
    },
    openai: {
      haiku: "openai/gpt-5.4-mini",
      sonnet: "openai/gpt-5.3-codex-spark",
      opus: "openai/gpt-5.6-sol",
    },
  },
  github: {
    haiku: "claude-haiku-5.5",
    sonnet: "claude-sonnet-5.5",
    opus: "claude-opus-5.5",
  },
  codex: {
    haiku: "gpt-5.6-luna",
    sonnet: "gpt-5.6-terra",
    opus: "gpt-5.6-sol",
  },
};

// color and temperature live in the canonical agent frontmatter (self-contained files —
// no name-keyed maps here, so renames/rebrands can never orphan them).

// OpenCode v2 sends `request.body` verbatim and takes effort as a model variant (`#high`).
// Only the haiku-tier models accept sampling params. Checked with `opencode run` on 2.0.32
// (2026-10-20): Claude Haiku 5.5 takes `#low` together with `temperature`.
const V2_SAMPLING_TIERS = ["haiku"];

// Pokémon → Norse. Order matters: longest-overlapping first.
const NORSE = [
  ["Mewtwo", "Mimir"],
  ["Machop", "Brokkr"],
  ["Ditto", "Loki"],
];

// Where things land, per harness × scope. {p} = project dir, {h} = home,
// {c} = Claude Code's config dir.
const TARGETS = {
  opencode: {
    project: {
      agents: "{p}/.opencode/agents",
      commands: "{p}/.opencode/commands",
      skills: "{p}/.opencode/skills",
    },
    global: {
      agents: "{h}/.config/opencode/agents",
      commands: "{h}/.config/opencode/commands",
      skills: "{h}/.config/opencode/skills",
    },
  },
  github: {
    // .agents/skills is the cross-tool folder: Copilot, OpenCode, and Codex all read it.
    // OpenCode 2 no longer turns skills into slash commands: a thin command loads each one.
    project: {
      agents: "{p}/.github/agents",
      skills: "{p}/.agents/skills",
      opencodeCommands: "{p}/.opencode/commands",
    },
    global: { agents: "{h}/.copilot/agents", skills: "{h}/.copilot/skills" },
  },
  claude: {
    project: {
      agents: "{p}/.claude/agents",
      commands: "{p}/.claude/commands",
      skills: "{p}/.claude/skills",
    },
    global: {
      agents: "{c}/agents",
      commands: "{c}/commands",
      skills: "{c}/skills",
    },
  },
  codex: {
    project: {
      agents: "{p}/.codex/agents",
      skills: "{p}/.agents/skills",
      opencodeCommands: "{p}/.opencode/commands",
    },
    global: {
      agents: "{h}/.codex/agents",
      skills: "{h}/.agents/skills",
    },
  },
};
// v2 reads the same dirs as v1; only the agent frontmatter differs.
TARGETS["opencode-v2"] = TARGETS.opencode;

// Skill dirs a harness installed into before. Nothing goes there now, so a catalog name found
// there is our old copy, and Copilot would list it twice.
const LEGACY_SKILLS = { github: { project: "{p}/.github/skills" } };

// User-level instructions file per harness; global installs only — a project owns its own.
const INSTRUCTIONS = {
  opencode: "{h}/.config/opencode/AGENTS.md",
  github: "{h}/.copilot/copilot-instructions.md",
  claude: "{c}/CLAUDE.md",
  codex: "{h}/.codex/AGENTS.md",
};
INSTRUCTIONS["opencode-v2"] = INSTRUCTIONS.opencode;
const BLOCK_BEGIN = "<!-- ai-catalog-begin -->";
const BLOCK_END = "<!-- ai-catalog-end -->";

// Names earlier catalog versions installed and this one no longer ships (from git history,
// both naming sets). Every install removes them from its target dirs, which also clears
// installs that predate the manifest. Current names in the other naming set are derived.
const RETIRED = {
  agents: [
    ...["abra", "alakazam", "dugtrio", "eevee", "espeon", "growlithe", "hypno"],
    ...[
      "kadabra",
      "machamp",
      "magnemite",
      "magneton",
      "meowth",
      "mew",
      "pichu",
    ],
    ...["pikachu", "porygon", "porygon2", "raichu", "slowpoke", "machoke"],
    ...["bragi", "forseti", "heimdall", "hermod", "huginn", "kraken", "muninn"],
    ...[
      "ratatoskr",
      "skadi",
      "skuld",
      "tyr",
      "urd",
      "verdandi",
      "volund",
      "sindri",
    ],
  ],
  commands: [
    ...["feedback-orchestrator", "implement-orchestrator", "plan-orchestrator"],
    ...["review-orchestrator", "verify-orchestrator"],
    ...["ticket", "pr-review", "pr-feedback"],
  ],
  skills: ["repo-learnings"],
};
// The retired orchestrators' project caches. Matched by exact artifact name, never by
// directory: a harness may keep its own files there (e.g. ~/.claude/cache).
const RETIRED_CACHE_DIRS = [
  ".agents/cache",
  ".claude/cache",
  ".opencode/cache",
];
const RETIRED_CACHE_ENTRY =
  /^\.?(plan|review|feedback|impl-brief)-.+\.md$|^(repo-profile|security-profile|learnings)\.md$|^(tmp|bruno)$/;

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : fallback;
};
const has = (name) => args.includes(`--${name}`);

const harness = opt("harness");
const isOpencode = harness === "opencode" || harness === "opencode-v2";
const scope = has("global") ? "global" : "project";
const names = opt("names", "pokemon");
const prefix = opt("prefix", "") ?? "";
const skip = new Set(
  (opt("skip", "") ?? "")
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean),
);
const provider = opt("provider", isOpencode ? "copilot" : undefined);
const dryRun = has("dry-run");
const projectDir = path.resolve(opt("project", process.cwd()));

if (!TARGETS[harness]) {
  console.error(
    `usage: install.mjs --harness <opencode|opencode-v2|github|claude|codex> [--global] [--project <dir>] [--names <pokemon|norse>] [--prefix <p>] [--skip <a,b>] [--provider <copilot|claude|openai>] [--dry-run]`,
  );
  process.exit(1);
}
if (!["pokemon", "norse"].includes(names)) {
  console.error(`--names must be "pokemon" or "norse"`);
  process.exit(1);
}
if (!/^[a-z0-9-]*$/.test(prefix)) {
  console.error(`--prefix may only use lowercase letters, digits, and hyphens`);
  process.exit(1);
}
if (!isOpencode && has("provider")) {
  console.error(`--provider is only supported by the opencode harnesses`);
  process.exit(1);
}
if (isOpencode && !MODEL_MAP.opencode[provider]) {
  console.error(`--provider must be "copilot", "claude", or "openai"`);
  process.exit(1);
}

const modelMap = isOpencode ? MODEL_MAP.opencode[provider] : MODEL_MAP[harness];

// Claude Code relocates its whole config dir (agents, commands, skills, CLAUDE.md) to
// $CLAUDE_CONFIG_DIR when set.
const claudeHome = path.resolve(
  (process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude")).replace(
    /^~(?=$|\/)/,
    os.homedir(),
  ),
);
const expand = (template) =>
  template
    .replace("{p}", projectDir)
    .replace("{h}", os.homedir())
    .replace("{c}", claudeHome);

const resolveDirs = (h) =>
  Object.fromEntries(
    Object.entries(TARGETS[h][scope]).map(([k, v]) => [k, expand(v)]),
  );
const dirs = resolveDirs(harness);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const parseDoc = (file) => {
  const raw = fs.readFileSync(file, "utf8");
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?/);
  const fm = {};
  for (const line of (m?.[1] ?? "").split("\n")) {
    const kv = line.match(/^([a-z-]+):\s*(.*)$/);
    if (kv) fm[kv[1]] = kv[2].replace(/\s+#.*$/, "").trim();
  }
  return { fm, body: raw.slice(m?.[0].length ?? 0) };
};

const norsify = (text) => {
  for (const [poke, norse] of NORSE) {
    text = text
      .replaceAll(new RegExp(`\\b${poke}\\b`, "g"), norse)
      .replaceAll(
        new RegExp(`\\b${poke.toLowerCase()}\\b`, "g"),
        norse.toLowerCase(),
      );
  }
  return text
    .replaceAll(
      "named after a Pokémon",
      "named after a figure from Norse mythology",
    )
    .replaceAll(/\bPokémon\b/g, "Norse mythology");
};

// `/plan` → `/oct-plan`, but never a path (`docs/plan`, `plan.md`) or an already-prefixed name.
const commandNames = fs
  .readdirSync(path.join(ROOT, "commands"))
  .filter((f) => f.endsWith(".md"))
  .map((f) => f.replace(/\.md$/, ""));
const COMMAND_REF = new RegExp(
  `(?<![\\w./-])/(${commandNames.join("|")})(?![\\w-]|\\.md)`,
  "g",
);
const withPrefix = (text) =>
  prefix ? text.replace(COMMAND_REF, `/${prefix}$1`) : text;
const transform = (text) =>
  withPrefix(names === "norse" ? norsify(text) : text);
const outName = (base) => transform(base);

// JSON is a valid YAML subset, so JSON.stringify yields a safe double-quoted scalar for any
// re-emitted frontmatter value — handles a mid-sentence ": ", embedded quotes, and "#".
const yamlStr = (s) => JSON.stringify(s ?? "");
const tomlStr = (s) => JSON.stringify(s ?? "");

const writes = [];
const emit = (file, content) => writes.push({ file, content });
const emitDir = (src, dest) => writes.push({ dir: src, file: dest });

const PORTABLE_TOOLS = new Set([
  "Bash",
  "Read",
  "Grep",
  "Glob",
  "Edit",
  "Write",
  "LSP",
]);
const toolFlags = (tools) => {
  const names = tools
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);
  return {
    bash: names.includes("Bash"),
    lsp: names.includes("LSP"),
    write: names.some((name) => name === "Edit" || name === "Write"),
    external: names.some((name) => !PORTABLE_TOOLS.has(name)),
  };
};

// ---------------------------------------------------------------------------
// Builders
// ---------------------------------------------------------------------------
const allAgents = fs
  .readdirSync(path.join(ROOT, "agents"))
  .filter((f) => f.endsWith(".md"));
const allCommands = commandNames.map((name) => `${name}.md`);
const allSkills = fs
  .readdirSync(path.join(ROOT, "skills"), { withFileTypes: true })
  .filter(
    (d) =>
      d.isDirectory() &&
      fs.existsSync(path.join(ROOT, "skills", d.name, "SKILL.md")),
  );
const known = [
  ...allAgents.map((f) => f.replace(/\.md$/, "")),
  ...commandNames,
  ...allSkills.map((d) => d.name),
];
const KINDS = ["agents", "commands", "skills"];
const unknown = [...skip].filter(
  (name) => !known.includes(name) && !KINDS.includes(name),
);
if (unknown.length) {
  console.error(
    `--skip: unknown ${unknown.join(", ")} (catalog: ${known.join(", ")})`,
  );
  process.exit(1);
}
const kept = (kind) => (name) =>
  !skip.has(kind) && !skip.has(name.replace(/\.md$/, ""));
const agents = allAgents.filter(kept("agents"));
const commands = allCommands.filter(kept("commands"));
const skills = allSkills.filter((d) => kept("skills")(d.name));

for (const f of agents) {
  const name = f.replace(/\.md$/, "");
  const { fm, body } = parseDoc(path.join(ROOT, "agents", f));
  const { bash, lsp, write, external } = toolFlags(fm.tools ?? "");
  // An agent that omits `tools:` inherits every tool of its caller (including MCP servers whose
  // names differ per install); harnesses with an explicit allowlist must not narrow it.
  const inheritsAll = fm.tools === undefined;
  let out = "";

  if (harness === "claude") {
    out = fs.readFileSync(path.join(ROOT, "agents", f), "utf8");
  } else if (harness === "opencode") {
    const lines = [
      `description: ${yamlStr(fm.description)}`,
      `mode: subagent`,
      `model: ${modelMap[fm.model] ?? modelMap.sonnet}`,
      ...(fm.temperature ? [`temperature: ${fm.temperature}`] : []),
      ...(fm.effort ? [`reasoningEffort: ${fm.effort}`] : []),
      ...(fm.color ? [`color: ${fm.color}`] : []),
      `permission:`,
      `  edit: ${write ? "allow" : "deny"}`,
      `  bash: ${bash ? "allow" : "deny"}`,
      ...(lsp ? [`  lsp: allow`] : []),
      `  webfetch: deny`,
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  } else if (harness === "opencode-v2") {
    // Ordered rules, last match wins, on top of v2's allow-all base.
    const rule = (action, allowed) => [
      `  - action: ${action}`,
      `    resource: "*"`,
      `    effect: ${allowed ? "allow" : "deny"}`,
    ];
    const model = modelMap[fm.model] ?? modelMap.sonnet;
    const variant = fm.effort ? `#${fm.effort}` : "";
    const lines = [
      `description: ${yamlStr(fm.description)}`,
      `mode: subagent`,
      `model: ${model}${variant}`,
      ...(fm.color ? [`color: ${fm.color}`] : []),
      ...(fm.temperature && V2_SAMPLING_TIERS.includes(fm.model)
        ? [`request:`, `  body:`, `    temperature: ${fm.temperature}`]
        : []),
      `permissions:`,
      ...rule("edit", write),
      ...rule("shell", bash),
      ...(lsp ? rule("lsp", true) : []),
      ...rule("webfetch", false),
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  } else if (harness === "codex") {
    const lines = [
      `name = ${tomlStr(outName(name))}`,
      `description = ${tomlStr(fm.description)}`,
      `model = ${tomlStr(modelMap[fm.model] ?? modelMap.sonnet)}`,
      ...(fm.effort ? [`model_reasoning_effort = ${tomlStr(fm.effort)}`] : []),
      `sandbox_mode = ${tomlStr(write ? "workspace-write" : "read-only")}`,
      `developer_instructions = ${tomlStr(body)}`,
    ];
    out = lines.join("\n");
  } else if (harness === "github") {
    // tools: dual vocabulary (CLI + VS Code aliases); unknown names are silently ignored.
    const tools = ['"read"', '"search"'];
    if (bash) tools.push('"shell"', '"runCommands"');
    if (write) tools.push('"write"', '"editFiles"');
    const lines = [
      `name: ${fm.name}`,
      `description: ${yamlStr(fm.description)}`,
      `model: ${modelMap[fm.model] ?? modelMap.sonnet}`,
      // GitHub enables all configured tools when this property is omitted. External MCP
      // server names are installation-specific, so a generated restrictive list would
      // silently remove the Jira/browser tools these agents require.
      ...(!external && !inheritsAll ? [`tools: [${tools.join(", ")}]`] : []),
      `user-invocable: false`,
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  }

  const suffix =
    harness === "github" ? ".agent.md" : harness === "codex" ? ".toml" : ".md";
  emit(path.join(dirs.agents, outName(name) + suffix), transform(out));
}

for (const f of commands) {
  const name = f.replace(/\.md$/, "");
  const command = prefix + name;
  const raw = fs.readFileSync(path.join(ROOT, "commands", f), "utf8");
  const { fm, body } = parseDoc(path.join(ROOT, "commands", f));

  if (harness === "claude") {
    emit(path.join(dirs.commands, `${command}.md`), transform(raw));
  } else if (isOpencode) {
    // OpenCode commands take a provider model id and have no argument hint or effort.
    const front = raw
      .slice(0, raw.length - body.length)
      .replace(/^(argument-hint|effort):.*\n/gm, "")
      .replace(/^model: (\w+)$/m, (line, tier) => `model: ${modelMap[tier]}`);
    // v2 renamed the task tool to subagent.
    const out = (front + body)
      .replaceAll(
        "the Agent tool",
        harness === "opencode-v2" ? "the subagent tool" : "the task tool",
      )
      .replaceAll(/TaskCreate|TaskUpdate/g, "todowrite");
    emit(path.join(dirs.commands, `${command}.md`), transform(out));
  } else if (harness === "github" || harness === "codex") {
    // Copilot and Codex invoke workflows as skills → agentskills SKILL.md per command.
    // Copilot code review activates any repo skill that looks relevant, so a workflow skill
    // must say it is user-run and opt out of model invocation. OpenCode reads .agents/skills
    // too and never picks it on its own (autoinvoke); OpenCode 2 ignores `opencode/slash`, so a
    // project install also writes the command that loads the skill.
    const invoke = `${harness === "codex" ? "$" : "/"}${command}`;
    const out = body
      .replaceAll(/`\$ARGUMENTS`|\$ARGUMENTS/g, "the user's request")
      .replaceAll("via the Agent tool", "as subagents")
      .replaceAll("the Agent tool", "your subagent mechanism")
      .replaceAll(/TaskCreate|TaskUpdate/g, "your task list");
    const description = `Interactive workflow the user starts with ${invoke}; never activate it yourself. ${fm.description}`;
    emit(
      path.join(dirs.skills, command, "SKILL.md"),
      transform(
        `---\nname: ${command}\ndescription: ${yamlStr(description)}\ndisable-model-invocation: true\nmetadata:\n  opencode/slash: "true"\n  opencode/autoinvoke: "false"\n---\n${out}`,
      ),
    );
    if (dirs.opencodeCommands) {
      emit(
        path.join(dirs.opencodeCommands, `${command}.md`),
        `---\ndescription: ${yamlStr(fm.description)}\n---\n\nLoad the \`${command}\` skill with the skill tool and follow it exactly. The user's request: $ARGUMENTS\n`,
      );
    }
  }
}

for (const d of skills) {
  emitDir(path.join(ROOT, "skills", d.name), path.join(dirs.skills, d.name));
}

// Kept out of `writes` on purpose: the manifest cleanup must never delete a file the user owns.
const instructionsFile =
  scope === "global" ? expand(INSTRUCTIONS[harness]) : undefined;
const withBlock = (existing, block) => {
  const wrapped = `${BLOCK_BEGIN}\n${block.trim()}\n${BLOCK_END}`;
  const start = existing.indexOf(BLOCK_BEGIN);
  const end = existing.indexOf(BLOCK_END);
  if (start >= 0 && end > start)
    return (
      existing.slice(0, start) +
      wrapped +
      existing.slice(end + BLOCK_END.length)
    );
  return existing.trim()
    ? `${existing.trimEnd()}\n\n${wrapped}\n`
    : `${wrapped}\n`;
};

// ---------------------------------------------------------------------------
// Install
// ---------------------------------------------------------------------------
const installRoots = [
  ...new Set(
    Object.values(dirs)
      .filter(Boolean)
      .map((dir) => path.dirname(dir)),
  ),
];
const isWithinInstallRoot = (installRoot, file) => {
  const relative = path.relative(installRoot, file);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative);
};
const currentWrites = writes.map((write) => write.file);
const installStates = installRoots.map((installRoot) => {
  // An OpenCode install keeps its manifest in .opencode/ too: a Copilot or Codex install writing
  // commands there keeps its own, so neither run removes the other's files.
  const sharesOpencodeRoot =
    !isOpencode && path.basename(installRoot) === ".opencode";
  const manifestFile = path.join(
    installRoot,
    sharesOpencodeRoot
      ? `.ai-catalog-manifest.${harness}.json`
      : ".ai-catalog-manifest.json",
  );
  let previousWrites = [];
  try {
    const entries = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
    if (Array.isArray(entries)) {
      previousWrites = entries
        .filter((entry) => typeof entry === "string")
        .map((entry) => path.resolve(installRoot, entry))
        .filter((file) => isWithinInstallRoot(installRoot, file));
    }
  } catch {
    // Missing or invalid manifests do not block a fresh install.
  }
  const current = currentWrites.filter((file) =>
    isWithinInstallRoot(installRoot, file),
  );
  return {
    installRoot,
    manifestFile,
    current,
    cleanup: [...new Set([...previousWrites, ...current])],
  };
});

// lstat, not exists: the old deploy scripts left symlinks that now dangle.
const present = (file) => {
  try {
    fs.lstatSync(file);
    return true;
  } catch {
    return false;
  }
};
const bothSets = (name) => [...new Set([name, norsify(name)])];
// Where a catalog with these names would sit in harness `h` at this scope.
const catalogPaths = (
  h,
  { agents: agentNames, commands: commandNames, skills: skillNames },
) => {
  const d = resolveDirs(h);
  const legacy = LEGACY_SKILLS[h]?.[scope];
  const suffix = h === "github" ? ".agent.md" : h === "codex" ? ".toml" : ".md";
  return [
    ...agentNames.map((name) => path.join(d.agents, name + suffix)),
    // github/codex install commands as skills
    ...commandNames.map((name) =>
      d.commands
        ? path.join(d.commands, `${name}.md`)
        : path.join(d.skills, name),
    ),
    ...skillNames.map((name) => path.join(d.skills, name)),
    ...(legacy
      ? [...commandNames, ...skillNames].map((name) =>
          path.join(expand(legacy), name),
        )
      : []),
  ];
};
const everShipped = {
  agents: [
    ...RETIRED.agents,
    ...agents.map((f) => f.replace(/\.md$/, "")),
  ].flatMap(bothSets),
  // Current commands under this install's prefix only: a bare `plan` or `review` next to a
  // prefixed install may belong to the user, and the manifest already covers our old copies.
  commands: [
    ...RETIRED.commands,
    ...commands.map((f) => prefix + f.replace(/\.md$/, "")),
  ],
  skills: RETIRED.skills,
};
const retiredCaches =
  scope === "project"
    ? RETIRED_CACHE_DIRS.map((dir) => path.join(projectDir, dir))
    : [];
const written = new Set(currentWrites);
const stale = [
  ...new Set([
    // This harness: every name ever shipped that this install doesn't write.
    ...catalogPaths(harness, everShipped),
    // ...and the current skills in its old skill dir: they live in the new one now.
    ...(LEGACY_SKILLS[harness]?.[scope]
      ? allSkills.map((d) =>
          path.join(expand(LEGACY_SKILLS[harness][scope]), d.name),
        )
      : []),
    // Other harnesses: retired names only; their current entries belong to their own install.
    ...Object.keys(TARGETS)
      .filter((h) => h !== harness)
      .flatMap((h) => catalogPaths(h, RETIRED)),
    ...retiredCaches
      .filter((dir) => fs.existsSync(dir))
      .flatMap((dir) =>
        fs
          .readdirSync(dir)
          .filter((entry) => RETIRED_CACHE_ENTRY.test(entry))
          .map((entry) => path.join(dir, entry)),
      ),
  ]),
].filter((file) => !written.has(file) && present(file));

for (const { cleanup } of installStates) {
  for (const file of cleanup) {
    if (dryRun) console.log(`would remove ${file}`);
    else fs.rmSync(file, { recursive: true, force: true });
  }
}
for (const file of stale) {
  if (dryRun) console.log(`would remove stale ${file}`);
  else fs.rmSync(file, { recursive: true, force: true });
}
// A cache dir the old workflow emptied goes too; one holding anything else stays.
for (const dir of retiredCaches) {
  if (dryRun || !fs.existsSync(dir) || fs.readdirSync(dir).length) continue;
  fs.rmdirSync(dir);
}

let files = 0;
for (const w of writes) {
  if (dryRun) {
    console.log(`would write  ${w.file}${w.dir ? "/ (dir copy)" : ""}`);
    continue;
  }
  if (w.dir) {
    fs.mkdirSync(path.dirname(w.file), { recursive: true });
    fs.cpSync(w.dir, w.file, { recursive: true });
    if (names === "norse" || prefix) {
      // Skill bodies may reference agent or command names.
      for (const sk of fs.readdirSync(w.file, { recursive: true })) {
        const p = path.join(w.file, String(sk));
        if (p.endsWith(".md"))
          fs.writeFileSync(p, transform(fs.readFileSync(p, "utf8")));
      }
    }
  } else {
    fs.mkdirSync(path.dirname(w.file), { recursive: true });
    fs.writeFileSync(w.file, w.content);
  }
  files++;
}

if (instructionsFile) {
  const block = fs.readFileSync(
    path.join(ROOT, "instructions/AGENTS.md"),
    "utf8",
  );
  const existing = fs.existsSync(instructionsFile)
    ? fs.readFileSync(instructionsFile, "utf8")
    : "";
  if (dryRun)
    console.log(`would update ${BLOCK_BEGIN} block in ${instructionsFile}`);
  else {
    fs.mkdirSync(path.dirname(instructionsFile), { recursive: true });
    fs.writeFileSync(instructionsFile, withBlock(existing, transform(block)));
  }
}

if (!dryRun) {
  for (const { installRoot, manifestFile, current } of installStates) {
    fs.mkdirSync(installRoot, { recursive: true });
    fs.writeFileSync(
      manifestFile,
      `${JSON.stringify(current.map((file) => path.relative(installRoot, file)))}\n`,
    );
  }
}

console.log(
  `${dryRun ? "[dry-run] " : ""}${harness} · ${scope}${scope === "project" ? ` (${projectDir})` : ""} · names=${names}${prefix ? ` · prefix=${prefix}` : ""}${skip.size ? ` · skip=${[...skip].join(",")}` : ""}${provider ? ` · provider=${provider}` : ""}` +
    `\n  agents: ${agents.length} → ${dirs.agents}` +
    (dirs.commands
      ? `\n  commands: ${commands.length} → ${dirs.commands}`
      : `\n  command-skills: ${commands.length} → ${dirs.skills}/<name>/`) +
    `\n  skills: ${skills.length} → ${dirs.skills}` +
    (instructionsFile ? `\n  instructions: block → ${instructionsFile}` : "") +
    (stale.length
      ? `\n  stale: ${stale.length} ${dryRun ? "to remove" : "removed"}`
      : "") +
    `\n  ${dryRun ? "planned" : "installed"}: ${files || writes.length} entries`,
);
const setupDoc =
  { claude: "claude-code", "opencode-v2": "opencode", github: "copilot" }[
    harness
  ] ?? harness;
console.log(
  `note: workflow state lives in ~/.agents/work — allow it once: docs/${setupDoc}.md#state-folder`,
);
if (harness === "github" && scope === "global") {
  console.log(
    "note: verify your Copilot surface reads ~/.copilot/skills — global skill discovery varies by version.",
  );
}
