#!/usr/bin/env node
/**
 * Catalog installer — builds the canonical agents/commands/skills for a harness and
 * installs them project-wise or globally. Zero dependencies.
 *
 *   ./scripts/install.mjs --harness <opencode|github|claude> [options]
 *
 * Options:
 *   --harness <name>      opencode | github (Copilot CLI/VS Code/coding agent) | claude
 *   --global              install to the user-level config dir (default: project)
 *   --project <dir>       target project dir for a project install (default: cwd)
 *   --names <set>         pokemon (default) | norse
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
    haiku: "github-copilot/claude-haiku-4.5",
    sonnet: "github-copilot/claude-sonnet-5",
    opus: "github-copilot/claude-opus-4.8",
  },
  github: {
    haiku: "claude-haiku-4.5",
    sonnet: "claude-sonnet-5",
    opus: "claude-opus-4.8",
  },
  claude: { haiku: "haiku", sonnet: "sonnet", opus: "opus" },
};

// color and temperature live in the canonical agent frontmatter (self-contained files —
// no name-keyed maps here, so renames/rebrands can never orphan them).

// Pokémon → Norse. Order matters: longest-overlapping first (Mewtwo before Mew).
const NORSE = [
  ["Slowbro", "Odin"],
  ["Mewtwo", "Mimir"],
  ["Mew", "Bragi"],
  ["Slowpoke", "Ratatoskr"],
  ["Kadabra", "Huginn"],
  ["Eevee", "Muninn"],
  ["Growlithe", "Heimdall"],
  ["Dugtrio", "Kraken"],
  ["Alakazam", "Tyr"],
  ["Porygon", "Urd"],
  ["Magneton", "Skuld"],
  ["Magnemite", "Verdandi"],
  ["Machop", "Brokkr"],
  ["Machoke", "Sindri"],
  ["Machamp", "Volund"],
  ["Abra", "Skadi"],
  ["Ditto", "Loki"],
];

// Where things land, per harness × scope. {p} = project dir, {h} = home.
const TARGETS = {
  opencode: {
    project: { agents: "{p}/.opencode/agents", commands: "{p}/.opencode/commands", skills: "{p}/.opencode/skills" },
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
    project: { agents: "{p}/.claude/agents", commands: "{p}/.claude/commands", skills: "{p}/.claude/skills" },
    global: { agents: "{h}/.claude/agents", commands: "{h}/.claude/commands", skills: "{h}/.claude/skills" },
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
const dryRun = has("dry-run");
const projectDir = path.resolve(opt("project", process.cwd()));

if (!TARGETS[harness]) {
  console.error(`usage: install.mjs --harness <opencode|github|claude> [--global] [--project <dir>] [--names <pokemon|norse>] [--dry-run]`);
  process.exit(1);
}
if (!["pokemon", "norse"].includes(names)) {
  console.error(`--names must be "pokemon" or "norse"`);
  process.exit(1);
}

const dirs = Object.fromEntries(
  Object.entries(TARGETS[harness][scope]).map(([k, v]) => [k, v.replace("{p}", projectDir).replace("{h}", os.homedir())]),
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
      .replaceAll(new RegExp(`\\b${poke.toLowerCase()}\\b`, "g"), norse.toLowerCase());
  }
  return text
    .replaceAll("named after a Pokémon", "named after a figure from Norse mythology")
    .replaceAll(/\bPokémon\b/g, "Norse mythology");
};

const transform = (text) => (names === "norse" ? norsify(text) : text);
const outName = (base) => transform(base);

const writes = [];
const emit = (file, content) => writes.push({ file, content });
const emitDir = (src, dest) => writes.push({ dir: src, file: dest });

const toolFlags = (tools) => ({
  bash: /(^|[ ,])Bash\b/.test(tools),
  write: /\b(Edit|Write)\b/.test(tools),
});

// ---------------------------------------------------------------------------
// Builders
// ---------------------------------------------------------------------------
const agents = fs.readdirSync(path.join(ROOT, "agents")).filter((f) => f.endsWith(".md"));
const commands = fs.readdirSync(path.join(ROOT, "commands")).filter((f) => f.endsWith(".md"));
const skills = fs.readdirSync(path.join(ROOT, "skills"), { withFileTypes: true }).filter((d) => d.isDirectory());

for (const f of agents) {
  const name = f.replace(/\.md$/, "");
  const { fm, body } = parseDoc(path.join(ROOT, "agents", f));
  const { bash, write } = toolFlags(fm.tools ?? "");
  let out = "";

  if (harness === "claude") {
    out = fs.readFileSync(path.join(ROOT, "agents", f), "utf8"); // canonical IS the Claude format
  } else if (harness === "opencode") {
    const lines = [
      `description: ${fm.description}`,
      `mode: subagent`,
      `model: ${MODEL_MAP.opencode[fm.model] ?? MODEL_MAP.opencode.sonnet}`,
      ...(fm.temperature ? [`temperature: ${fm.temperature}`] : []),
      ...(fm.reasoning ? [`reasoningEffort: ${fm.reasoning}`] : []),
      ...(fm.color ? [`color: ${fm.color}`] : []),
      `permission:`,
      `  edit: ${write ? "allow" : "deny"}`,
      `  bash: ${bash ? "allow" : "deny"}`,
      `  webfetch: deny`,
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  } else if (harness === "github") {
    // tools: dual vocabulary (CLI + VS Code aliases); unknown names are silently ignored.
    const tools = ['"read"', '"search"'];
    if (bash) tools.push('"shell"', '"runCommands"');
    if (write) tools.push('"write"', '"editFiles"');
    const lines = [
      `name: ${fm.name}`,
      `description: ${fm.description}`,
      `model: ${MODEL_MAP.github[fm.model] ?? MODEL_MAP.github.sonnet}`,
      `tools: [${tools.join(", ")}]`,
      `user-invocable: false`,
    ];
    out = `---\n${lines.join("\n")}\n---\n${body}`;
  }

  const suffix = harness === "github" ? ".agent.md" : ".md";
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
  } else if (harness === "github") {
    // VS Code/Copilot invoke workflows as skills → agentskills SKILL.md per command.
    const out = body
      .replaceAll(/`\$ARGUMENTS`|\$ARGUMENTS/g, "the user's request")
      .replaceAll("via the Agent tool", "as subagents")
      .replaceAll("the Agent tool", "your subagent mechanism")
      .replaceAll(/TaskCreate|TaskUpdate/g, "your task list");
    emit(
      path.join(dirs.skills, name, "SKILL.md"),
      transform(`---\nname: ${name}\ndescription: ${fm.description}\n---\n${out}`),
    );
  }
}

for (const d of skills) {
  emitDir(path.join(ROOT, "skills", d.name), path.join(dirs.skills, d.name));
}

// ---------------------------------------------------------------------------
// Install
// ---------------------------------------------------------------------------
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
      // skills bodies may reference agent names (e.g. repo-learnings mentions the profiler)
      for (const sk of fs.readdirSync(w.file, { recursive: true })) {
        const p = path.join(w.file, String(sk));
        if (p.endsWith(".md")) fs.writeFileSync(p, norsify(fs.readFileSync(p, "utf8")));
      }
    }
  } else {
    fs.mkdirSync(path.dirname(w.file), { recursive: true });
    fs.writeFileSync(w.file, w.content);
  }
  files++;
}

console.log(
  `${dryRun ? "[dry-run] " : ""}${harness} · ${scope}${scope === "project" ? ` (${projectDir})` : ""} · names=${names}` +
    `\n  agents: ${agents.length} → ${dirs.agents}` +
    (dirs.commands ? `\n  commands: ${commands.length} → ${dirs.commands}` : `\n  command-skills: ${commands.length} → ${dirs.skills}/<name>/`) +
    `\n  skills: ${skills.length} → ${dirs.skills}` +
    `\n  ${dryRun ? "planned" : "installed"}: ${files || writes.length} entries`,
);
if (harness === "github" && scope === "global") {
  console.log("note: verify your Copilot surface reads ~/.copilot/skills — global skill discovery varies by version.");
}
