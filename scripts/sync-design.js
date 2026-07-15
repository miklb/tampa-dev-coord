#!/usr/bin/env node
/* sync-design.js — one-way design-system sync: tm-static → this repo.
 *
 * tm-static (~/Sites/tm-static, the Monitor build home) is the source of truth
 * for the shared design system. This copies the shared CSS and font files over
 * VERBATIM, so run it whenever tm-static's design layer changes (or before
 * touching the site chrome here). Ported from ~/Sites/meetings, extended with
 * a fonts manifest (meetings doesn't self-host fonts; this Datasette does).
 * The contract that makes it safe:
 *
 *   - Synced files are pristine copies — never edit them in this repo.
 *   - Dev-coord-specific deviations live in dev-locations/static/css/theme.css,
 *     which is deliberately NOT wrapped in @layer — Datasette's own app.css is
 *     unlayered, and layered CSS can never override unlayered CSS.
 *
 * fonts.css references url("../fonts/*.woff2"); both repos keep css/ and
 * fonts/ as siblings, so it syncs with no path rewriting.
 *
 * Dev-time only — never runs on Heroku or in the GitHub Actions workflow.
 *
 * Usage:
 *   node scripts/sync-design.js            copy anything that drifted
 *   node scripts/sync-design.js --check    report drift without writing (exit 1 if any)
 *   ... --from <path>                      tm-static checkout somewhere other than ../tm-static
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");

// shared CSS, relative to tm-static's src/assets/css/ and dev-locations/static/css/
// (tm-static's reset.css is deliberately absent: Datasette's app.css ships its
// own Meyer reset, and layering ours above it would strip the margins app.css
// relies on for its UI rhythm.)
const CSS_FILES = [
  "tokens.css",
  "base.css",
  "layout.css",
  "fonts.css",
  "components/btn.css",
  "components/mainnav.css",
  "components/masthead.css",
  "components/site-footer.css",
];

// woff2 subsets, relative to tm-static's src/assets/fonts/ and dev-locations/static/fonts/
const FONT_FILES = [
  "libre-franklin-var-latin.woff2",
  "libre-franklin-var-latin-ext.woff2",
  "pt-serif-400-latin.woff2",
  "pt-serif-400-latin-ext.woff2",
  "pt-serif-400i-latin.woff2",
  "pt-serif-400i-latin-ext.woff2",
  "pt-serif-700-latin.woff2",
  "pt-serif-700-latin-ext.woff2",
];

const repoRoot = path.resolve(__dirname, "..");

const args = process.argv.slice(2);
const check = args.includes("--check");
const fromIdx = args.indexOf("--from");
const srcBase = fromIdx !== -1 ? path.resolve(args[fromIdx + 1]) : path.resolve(repoRoot, "..", "tm-static");

function syncSet(label, files, srcRoot, destRoot) {
  if (!fs.existsSync(srcRoot)) {
    console.error(`source not found: ${srcRoot}\n(point at a tm-static checkout with --from <path>)`);
    process.exit(1);
  }
  let drifted = 0;
  for (const file of files) {
    const src = path.join(srcRoot, file);
    const dest = path.join(destRoot, file);
    if (!fs.existsSync(src)) {
      console.error(`missing in tm-static: ${label}/${file} (removed there? update the manifest)`);
      process.exitCode = 1;
      continue;
    }
    const want = fs.readFileSync(src);
    const have = fs.existsSync(dest) ? fs.readFileSync(dest) : null;
    if (have && want.equals(have)) {
      console.log(`  up-to-date  ${label}/${file}`);
      continue;
    }
    drifted++;
    if (check) {
      console.log(`  DRIFTED     ${label}/${file}`);
    } else {
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.writeFileSync(dest, want);
      console.log(`  synced      ${label}/${file}${have ? "" : " (new)"}`);
    }
  }
  return drifted;
}

let drifted = 0;
drifted += syncSet(
  "css",
  CSS_FILES,
  path.join(srcBase, "src", "assets", "css"),
  path.join(repoRoot, "dev-locations", "static", "css")
);
drifted += syncSet(
  "fonts",
  FONT_FILES,
  path.join(srcBase, "src", "assets", "fonts"),
  path.join(repoRoot, "dev-locations", "static", "fonts")
);

if (check && drifted) {
  console.log(`\n${drifted} file(s) drifted from tm-static — run \`node scripts/sync-design.js\` to update.`);
  process.exit(1);
}
console.log(drifted ? `\nsynced ${drifted} file(s) from ${srcBase}` : "\neverything in sync");
