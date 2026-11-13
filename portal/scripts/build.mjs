import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepare, normalizeBase } from './prepare.mjs';
import { checkSite } from './check-site.mjs';
import { writeNotices } from './notices.mjs';
import { enableKeyboardContent } from './keyboard-content.mjs';
import { claimDist, sealDist } from './owned-output.mjs';

const project = fileURLToPath(new URL('..', import.meta.url));
const repository = path.resolve(project, '..');
const base = normalizeBase(process.env.DOCS_BASE ?? '/cinevault-infra-report');
const distClaim = await claimDist(repository);
const manifest = await prepare({ repoRoot: repository, base: base || '/' });
const notices = await writeNotices(project);
const generated = path.join(project, '.generated');
await copyFile(path.join(project, 'src/content.config.ts'), path.join(generated, 'src/content.config.ts'));
await mkdir(path.join(generated, 'src/content/i18n'), { recursive: true });
await copyFile(path.join(project, 'src/i18n/fr.json'), path.join(generated, 'src/content/i18n/fr.json'));
await copyFile(path.join(project, 'src/favicon.svg'), path.join(generated, 'public/favicon.svg'));
// This page is generated metadata, not a second editorial copy of a source document.
await writeFile(path.join(generated, 'src/content/docs/404.md'), '---\ntitle: Page introuvable\n---\n\nCette page n’existe pas. Revenez à l’accueil ou utilisez la recherche.\n');
let result;
try {
  result = spawnSync(process.execPath, ['node_modules/astro/bin/astro.mjs', 'build'], {
    cwd: project, stdio: 'inherit',
    env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1', NODE_COMPILE_CACHE: path.join(project, '.cache/node') },
  });
} finally {
  await sealDist(distClaim);
}
if (result.error || result.status !== 0) throw new Error('Static documentation build failed');
const keyboardPages = await enableKeyboardContent(path.join(project, 'dist'));
const checked = await checkSite({
  distRoot: path.join(project, 'dist'), base: base || '/',
  privatePrefixes: [repository, process.env.USERPROFILE].filter(Boolean),
});
if (!checked.passed) {
  console.error(JSON.stringify(checked, null, 2));
  throw new Error('Built documentation failed local link or privacy checks');
}
const lock = await readFile(path.join(project, 'package-lock.json'));
const receipt = {
  schema: 1, scope: 'Static documentation build; no application or deployment qualification',
  node: process.version, base, package_lock_sha256: createHash('sha256').update(lock).digest('hex'),
  source_commit: manifest.source_commit, source_clean: manifest.source_clean,
  tooling_clean: manifest.tooling_clean, generator_sha256: manifest.generator_sha256,
  source_pages: manifest.pages.length, copied_assets: manifest.assets.length, checks: checked,
  dependency_notices: notices,
  keyboard_content_pages: keyboardPages,
};
await writeFile(path.join(project, 'dist/build-receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt));
