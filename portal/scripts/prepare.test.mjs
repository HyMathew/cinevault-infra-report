import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, readFile, rm, writeFile, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { prepare, normalizeBase } from './prepare.mjs';

async function fixture(t, files) {
  const root = await mkdtemp(path.join(tmpdir(), 'cinevault-portal-test-'));
  t.after(async () => {
    assert.ok(path.resolve(root).startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(root, { recursive: true, force: true });
  });
  for (const [name, content] of Object.entries(files)) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), content);
  }
  await mkdir(path.join(root, 'portal'), { recursive: true });
  execFileSync('git', ['init', '-q'], { cwd: root });
  execFileSync('git', ['add', '--all'], { cwd: root });
  return root;
}

test('CRLF, tables, code and soft paragraphs retain their Markdown meaning', async t => {
  const root = await fixture(t, {
    'README.md': '# Accueil\r\n\r\n[Titre](#accueil)\r\n\r\nUne phrase\r\ncontinue.\r\n\r\n| Nom | Valeur |\r\n| --- | --- |\r\n| A | 1 |\r\n\r\n```sh\r\nprintf x\r\n```\r\n',
  });
  const manifest = await prepare({ repoRoot: root });
  const markdown = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(markdown, /Une phrase\ncontinue\./);
  assert.doesNotMatch(markdown, /\r/);
  assert.match(markdown, /\| Nom\s+\| Valeur/);
  assert.match(markdown, /```sh\nprintf x\n```/);
  assert.match(markdown, /\[Titre\]\(#_top\)/);
  assert.equal(manifest.pages.length, 1);
});

test('rewrites encoded spaces, heading fragments and reference-style assets under a base', async t => {
  const root = await fixture(t, {
    'README.md': '# Accueil\n\n[Guide](docs/Mon%20guide.md#mon-guide)\n\n![Vue][image]\n\n[image]: evidence/vue.svg\n',
    'docs/Mon guide.md': '# Mon guide\n\nTexte.\n',
    'evidence/vue.svg': '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
  });
  const manifest = await prepare({ repoRoot: root, base: '/cinevault/' });
  const content = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(content, /\/cinevault\/guides\/mon%20guide\/#_top/);
  assert.match(content, /\/cinevault\/sources\/evidence\/vue\.svg/);
  assert.equal(manifest.assets.length, 1);
  assert.equal((await readFile(path.join(root, 'portal/.generated/public/sources/evidence/vue.svg'), 'utf8')), '<svg xmlns="http://www.w3.org/2000/svg"></svg>');
  assert.match(manifest.assets[0].sha256, /^[a-f0-9]{64}$/);
});

test('refuses route collisions and missing or untracked local files', async t => {
  const root = await fixture(t, { 'README.md': '# Home', 'docs/A.md': '# A', 'docs/a.md': '# a' });
  if (process.platform !== 'win32') {
    await assert.rejects(prepare({ repoRoot: root }), /collision/i);
    await rm(path.join(root, 'docs/a.md'));
    execFileSync('git', ['add', '--all'], { cwd: root });
  }
  await writeFile(path.join(root, 'README.md'), '# Home\n\n[Lost](missing.txt)');
  await assert.rejects(prepare({ repoRoot: root }), /missing|untracked/i);
  await writeFile(path.join(root, 'private.txt'), 'must not be published');
  await writeFile(path.join(root, 'README.md'), '# Home\n\n[Private](private.txt)');
  await assert.rejects(prepare({ repoRoot: root }), /untracked/i);
});

test('refuses encoded escapes, unsafe schemes and executable source HTML', async t => {
  const root = await fixture(t, { 'README.md': '# Home' });
  for (const body of ['[Outside](..%2foutside.md)', '[Bad](javascript:alert)', '<script>alert(1)</script>']) {
    await writeFile(path.join(root, 'README.md'), '# Home\n\n' + body);
    await assert.rejects(prepare({ repoRoot: root }), /outside|scheme|HTML/i);
  }
  assert.equal(normalizeBase('/a/'), '/a');
  assert.equal(normalizeBase('/'), '');
  for (const base of ['https://host/a', '//host', '/a/../b', '/a?x', '/a#x']) {
    assert.throws(() => normalizeBase(base), /base/i);
  }
});

test('symlink escape is refused and only the fixed owned output can be refreshed', async t => {
  const root = await fixture(t, { 'README.md': '# Home' });
  const outside = await mkdtemp(path.join(tmpdir(), 'cinevault-portal-outside-'));
  t.after(async () => {
    assert.ok(path.resolve(outside).startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(outside, { recursive: true, force: true });
  });
  await writeFile(path.join(outside, 'secret.txt'), 'outside');
  await symlink(outside, path.join(root, 'link'), process.platform === 'win32' ? 'junction' : 'dir');
  await writeFile(path.join(root, 'README.md'), '# Home\n\n[Outside](link/secret.txt)');
  await assert.rejects(prepare({ repoRoot: root }), /outside/i);
  await writeFile(path.join(root, 'README.md'), '# Home');
  await mkdir(path.join(root, 'portal/.generated'), { recursive: true });
  await writeFile(path.join(root, 'portal/.generated/keep.txt'), 'user work');
  await assert.rejects(prepare({ repoRoot: root }), /owned/i);
  assert.equal(await readFile(path.join(root, 'portal/.generated/keep.txt'), 'utf8'), 'user work');
  await assert.rejects(prepare({ repoRoot: root, outputRoot: outside }), /output/i);
});

test('successful regeneration is deterministic and ignores untracked private plans', async t => {
  const root = await fixture(t, { 'README.md': '# Home', 'docs/guide.md': '# Guide' });
  await mkdir(path.join(root, 'docs/superpowers'), { recursive: true });
  await writeFile(path.join(root, 'docs/superpowers/private.md'), '# Private');
  const first = await prepare({ repoRoot: root });
  const second = await prepare({ repoRoot: root });
  assert.deepEqual(second, first);
  assert.equal(first.pages.length, 2);
});

test('tracked report and evidence Markdown remain navigable documents', async t => {
  const root = await fixture(t, {
    'README.md': '# Home\n\n[Proof](evidence/run/README.md) [Report](report/README.md) [Design](DESIGN.md)',
    'DESIGN.md': '# Design authority\n\nPreserved direction.',
    'evidence/run/README.md': '# Historical proof\n\nDated evidence.',
    'report/README.md': '# Report\n\nVersion preserved.',
  });
  const manifest = await prepare({ repoRoot: root });
  assert.equal(manifest.pages.length, 4);
  assert.equal(manifest.assets.length, 0);
  const markdown = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(markdown, /\/records\/evidence\/run\//);
  assert.match(markdown, /\/records\/report\//);
  assert.match(markdown, /\/guides\/design\//);
});

test('clean editorial data does not imply clean portal tooling', async t => {
  const root = await fixture(t, {
    'README.md': '# Home',
    'portal/generator.txt': 'original',
    '.gitignore': 'portal/.generated/\n',
  });
  execFileSync('git', ['-c', 'user.name=Portal test', '-c', 'user.email=portal@example.invalid', 'commit', '-qm', 'fixture'], { cwd: root });
  const clean = await prepare({ repoRoot: root });
  assert.equal(clean.source_clean, true);
  assert.equal(clean.tooling_clean, true);
  await writeFile(path.join(root, 'portal/generator.txt'), 'changed');
  const changed = await prepare({ repoRoot: root });
  assert.equal(changed.source_clean, true);
  assert.equal(changed.tooling_clean, false);
  await writeFile(path.join(root, 'portal/generator.txt'), 'original');
  await writeFile(path.join(root, 'portal/new-tool.txt'), 'untracked');
  assert.equal((await prepare({ repoRoot: root })).tooling_clean, false);
});

test('a linked portal parent cannot create new generated output outside the repository', async t => {
  const root = await fixture(t, { 'README.md': '# Home' });
  const outside = await mkdtemp(path.join(tmpdir(), 'cinevault-portal-parent-test-'));
  t.after(async () => {
    assert.ok(outside.startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(outside, { recursive: true, force: true });
  });
  const parent = path.join(root, 'portal');
  assert.equal(path.relative(root, parent), 'portal');
  await rm(parent, { recursive: true });
  await symlink(outside, parent, process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(prepare({ repoRoot: root }), /parent|link|owned/i);
  await assert.rejects(readFile(path.join(outside, '.generated/.owner.json')), { code: 'ENOENT' });
});

test('raw HTML cannot introduce events, srcdoc or active URLs into public Markdown', async t => {
  const root = await fixture(t, { 'README.md': '# Home' });
  for (const html of ['<img src="https://example.invalid/pixel" onerror="alert(1)">', '<iframe srcdoc="<script>alert(1)</script>"></iframe>', '<a href=javascript:alert(1)>Click</a>', '<br>']) {
    await writeFile(path.join(root, 'README.md'), '# Home\n\n' + html);
    await assert.rejects(prepare({ repoRoot: root }), /HTML/i);
  }
  await writeFile(path.join(root, 'README.md'), '# Home <br>');
  await assert.rejects(prepare({ repoRoot: root }), /HTML/i);
});

test('GFM-like malformed markup remains escaped literal text rather than an active element', async t => {
  const root = await fixture(t, { 'README.md': '# Home\n\n<img src=https://example.invalid/pixel onerror=alert(1)>' });
  await prepare({ repoRoot: root });
  const output = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(output, /\\<img src=/);
  assert.ok(!output.includes('<img src=https:'));
});

test('duplicate heading fragments preserve the intended heading after extracting the H1', async t => {
  const root = await fixture(t, {
    'README.md': '# Same\n\n[Title](#same) [Second](#same-1) [Third](#same-2) [Other](docs/guide.md#same-1)\n\n## Same\n\nText.\n\n### Same\n\nMore.',
    'docs/guide.md': '# Same\n\n## Same\n\n[Home third](../README.md#same-2)',
  });
  await prepare({ repoRoot: root, base: '/docs' });
  const home = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  const guide = await readFile(path.join(root, 'portal/.generated/src/content/docs/guides/guide.md'), 'utf8');
  assert.match(home, /\[Title\]\(#_top\)/);
  assert.match(home, /\[Second\]\(#same\)/);
  assert.match(home, /\[Third\]\(#same-1\)/);
  assert.match(home, /\[Other\]\(\/docs\/guides\/guide\/#same\)/);
  assert.match(guide, /\[Home third\]\(\/docs\/#same-1\)/);
});

test('heading targets follow the actual pinned renderer for punctuation and image text', async t => {
  const root = await fixture(t, {
    'README.md': '# Guide\n\n[Punctuation](#a----b) [Picture](#vue-image)\n\n## A -- B\n\n## ![Vue](x.svg) image\n',
    'x.svg': '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
  });
  await prepare({ repoRoot: root });
  const output = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(output, /\[Punctuation\]\(#a--b\)/);
  assert.match(output, /\[Picture\]\(#-image\)/);
});

test('a query-only local link keeps its query and resolves anchors on the current document', async t => {
  const root = await fixture(t, { 'README.md': '# Home\n\n[Current](?view=1#home)' });
  await prepare({ repoRoot: root, base: '/docs' });
  const output = await readFile(path.join(root, 'portal/.generated/src/content/docs/index.md'), 'utf8');
  assert.match(output, /\[Current\]\(\/docs\/\?view=1#_top\)/);
});
