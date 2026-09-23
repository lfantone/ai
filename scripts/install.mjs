#!/usr/bin/env node
/**
 * Catalog installer — builds the canonical agents/commands/skills for a harness and
 * installs them project-wise or globally. Zero dependencies.
 *
 *   ./scripts/install.mjs --harness <opencode|github|claude|codex> [options]
 *
 * Options:
 *   --harness <name>      opencode | github (Copilot CLI/VS Code/coding agent) | claude | codex
 *   --global              install to the user-level config dir (default: project)
 *   --project <dir>       target project dir for a project install (default: cwd)
 *   --names <set>         pokemon (default) | norse
 *   --provider <name>     OpenCode only: copilot (default) | claude | openai
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
      haiku: "github-copilot/claude-haiku-4.5",
      sonnet: "github-copilot/claude-sonnet-5",
      opus: "github-copilot/claude-opus-5.5",
    },
    claude: {
      haiku: "anthropic/claude-haiku-4-5",
      sonnet: "anthropic/claude-sonnet-5",
      opus: "anthropic/claude-opus-5-5",
    },
    openai: {
      haiku: "openai/gpt-5.4-mini",
      sonnet: "openai/gpt-5.3-codex-spark",
      opus: "openai/gpt-5.6-sol",
    },
  },
  github: {
    haiku: "claude-haiku-4.5",
    sonnet: "claude-sonnet-5",
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

// Pokémon → Norse. Order matters: longest-overlapping first (Mewtwo before Mew).
const NORSE = [
  ["Slowbro", "Odin"],
  ["Mewtwo", "Mimir"],
  ["Meowth", "Hermod"],
  ["Mew", "Bragi"],
  ["Slowpoke", "Ratatoskr"],
  ["Kadabra", "Huginn"],
  ["Eevee", "Muninn"],
  ["Growlithe", "Heimdall"],
  ["Dugtrio", "Kraken"],
  ["Alakazam", "Tyr"],
  ["Magneton", "Skuld"],
  ["Magnemite", "Verdandi"],
  ["Machop", "Brokkr"],
  ["Machoke", "Sindri"],
  ["Machamp", "Volund"],
  ["Abra", "Skadi"],
  ["Ditto", "Loki"],
  ["Hypno", "Forseti"],
];

// Where things land, per harness × scope. {p} = project dir, {h} = home.
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
    project: { agents: "{p}/.github/agents", skills: "{p}/.github/skills" },
    global: { agents: "{h}/.copilot/agents", skills: "{h}/.copilot/skills" },
  },
  claude: {
    project: {
      agents: "{p}/.claude/agents",
      commands: "{p}/.claude/commands",
      skills: "{p}/.claude/skills",
    },
    global: {
      agents: "{h}/.claude/agents",
      commands: "{h}/.claude/commands",
      skills: "{h}/.claude/skills",
    },
  },
  codex: {
    project: {
      agents: "{p}/.codex/agents",
      skills: "{p}/.agents/skills",
    },
    global: {
      agents: "{h}/.codex/agents",
      skills: "{h}/.agents/skills",
    },
  },
};

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
const scope = has("global") ? "global" : "project";
const names = opt("names", "pokemon");
const provider = opt(
  "provider",
  harness === "opencode" ? "copilot" : undefined,
);
const dryRun = has("dry-run");
const projectDir = path.resolve(opt("project", process.cwd()));

if (!TARGETS[harness]) {
  console.error(
    `usage: install.mjs --harness <opencode|github|claude|codex> [--global] [--project <dir>] [--names <pokemon|norse>] [--provider <copilot|claude|openai>] [--dry-run]`,
  );
  process.exit(1);
}
if (!["pokemon", "norse"].includes(names)) {
  console.error(`--names must be "pokemon" or "norse"`);
  process.exit(1);
}
if (harness !== "opencode" && has("provider")) {
  console.error(`--provider is only supported by the opencode harness`);
  process.exit(1);
}
if (harness === "opencode" && !MODEL_MAP.opencode[provider]) {
  console.error(`--provider must be "copilot", "claude", or "openai"`);
  process.exit(1);
}

const modelMap =
  harness === "opencode" ? MODEL_MAP.opencode[provider] : MODEL_MAP[harness];

const dirs = Object.fromEntries(
  Object.entries(TARGETS[harness][scope]).map(([k, v]) => [
    k,
    v.replace("{p}", projectDir).replace("{h}", os.homedir()),
  ]),
);

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

const transform = (text) => (names === "norse" ? norsify(text) : text);
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
const agents = fs
  .readdirSync(path.join(ROOT, "agents"))
  .filter((f) => f.endsWith(".md"));
const commands = fs
  .readdirSync(path.join(ROOT, "commands"))
  .filter((f) => f.endsWith(".md"));
const skills = fs
  .readdirSync(path.join(ROOT, "skills"), { withFileTypes: true })
  .filter(
    (d) =>
      d.isDirectory() &&
      fs.existsSync(path.join(ROOT, "skills", d.name, "SKILL.md")),
  );

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
      ...(fm.reasoning ? [`reasoningEffort: ${fm.reasoning}`] : []),
      ...(fm.color ? [`color: ${fm.color}`] : []),
      `permission:`,
      `  edit: ${write ? "allow" : "deny"}`,
      `  bash: ${bash ? "allow" : "deny"}`,
      ...(lsp ? [`  lsp: allow`] : []),
      `  webfetch: deny`,
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  } else if (harness === "codex") {
    const lines = [
      `name = ${tomlStr(outName(name))}`,
      `description = ${tomlStr(fm.description)}`,
      `model = ${tomlStr(modelMap[fm.model] ?? modelMap.sonnet)}`,
      ...(fm.reasoning
        ? [`model_reasoning_effort = ${tomlStr(fm.reasoning)}`]
        : []),
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
  const raw = fs.readFileSync(path.join(ROOT, "commands", f), "utf8");
  const { fm, body } = parseDoc(path.join(ROOT, "commands", f));

  if (harness === "claude") {
    emit(path.join(dirs.commands, f), transform(raw));
  } else if (harness === "opencode") {
    const out = raw
      .replace(/^argument-hint:.*\n/m, "")
      .replaceAll("the Agent tool", "the task tool")
      .replaceAll(/TaskCreate|TaskUpdate/g, "todowrite");
    emit(path.join(dirs.commands, f), transform(out));
  } else if (harness === "github" || harness === "codex") {
    // Copilot and Codex invoke workflows as skills → agentskills SKILL.md per command.
    const out = body
      .replaceAll(/`\$ARGUMENTS`|\$ARGUMENTS/g, "the user's request")
      .replaceAll("via the Agent tool", "as subagents")
      .replaceAll("the Agent tool", "your subagent mechanism")
      .replaceAll(/TaskCreate|TaskUpdate/g, "your task list");
    emit(
      path.join(dirs.skills, name, "SKILL.md"),
      transform(
        `---\nname: ${name}\ndescription: ${yamlStr(fm.description)}\n---\n${out}`,
      ),
    );
  }
}

for (const d of skills) {
  emitDir(path.join(ROOT, "skills", d.name), path.join(dirs.skills, d.name));
}

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
// Pre-manifest catalog releases installed Porygon without recording its path.
// Match its unique body markers so unrelated agents remain untouched.
const legacyPorygon = path.join(
  dirs.agents,
  `porygon${harness === "github" ? ".agent.md" : ".md"}`,
);
const legacyWrites = (() => {
  try {
    const content = fs.readFileSync(legacyPorygon, "utf8");
    return content.includes("# Porygon — Verify line anchors") &&
      content.includes(
        "Mechanical and precise. Your only job: make each finding's",
      )
      ? [legacyPorygon]
      : [];
  } catch {
    return [];
  }
})();
const installStates = installRoots.map((installRoot) => {
  const manifestFile = path.join(installRoot, ".ai-catalog-manifest.json");
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
    cleanup: [
      ...new Set([
        ...previousWrites,
        ...current,
        ...legacyWrites.filter((file) =>
          isWithinInstallRoot(installRoot, file),
        ),
      ]),
    ],
  };
});

for (const { cleanup } of installStates) {
  for (const file of cleanup) {
    if (dryRun) console.log(`would remove ${file}`);
    else fs.rmSync(file, { recursive: true, force: true });
  }
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
    if (names === "norse") {
      // Skill bodies may reference agent names.
      for (const sk of fs.readdirSync(w.file, { recursive: true })) {
        const p = path.join(w.file, String(sk));
        if (p.endsWith(".md"))
          fs.writeFileSync(p, norsify(fs.readFileSync(p, "utf8")));
      }
    }
  } else {
    fs.mkdirSync(path.dirname(w.file), { recursive: true });
    fs.writeFileSync(w.file, w.content);
  }
  files++;
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
  `${dryRun ? "[dry-run] " : ""}${harness} · ${scope}${scope === "project" ? ` (${projectDir})` : ""} · names=${names}${provider ? ` · provider=${provider}` : ""}` +
    `\n  agents: ${agents.length} → ${dirs.agents}` +
    (dirs.commands
      ? `\n  commands: ${commands.length} → ${dirs.commands}`
      : `\n  command-skills: ${commands.length} → ${dirs.skills}/<name>/`) +
    `\n  skills: ${skills.length} → ${dirs.skills}` +
    `\n  ${dryRun ? "planned" : "installed"}: ${files || writes.length} entries`,
);
if (harness === "github" && scope === "global") {
  console.log(
    "note: verify your Copilot surface reads ~/.copilot/skills — global skill discovery varies by version.",
  );
}
