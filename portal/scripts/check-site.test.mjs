import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { checkSite } from './check-site.mjs';

async function site(t, files) {
  const root = await mkdtemp(path.join(tmpdir(), 'cinevault-site-test-'));
  t.after(async () => {
    assert.ok(path.resolve(root).startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(root, { recursive: true, force: true });
  });
  for (const [name, content] of Object.entries(files)) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), content);
  }
  return root;
}

test('validates actual HTML targets, encoded names, anchors and static resources under a base', async t => {
  const root = await site(t, {
    'index.html': '<a href="/docs/guide/#échéance">Guide</a><img src="/docs/a%20b.svg"><script src="/docs/app.js"></script>',
    'guide/index.html': '<h1 id="échéance">Guide</h1><a href="../">Accueil</a><a href="https://example.org">Source</a>',
    'a b.svg': '<svg/>',
    'app.js': '/* local script */',
  });
  const result = await checkSite({ distRoot: root, base: '/docs/' });
  assert.equal(result.passed, true);
  assert.equal(result.htmlPages, 2);
  assert.equal(result.checkedLinks, 5);
});

test('missing files, missing anchors, base escapes and unsafe URL schemes fail the gate', async t => {
  const root = await site(t, {
    'index.html': '<h1 id="_top">Home</h1><a href="missing/">Lost</a><a href="#absent">Missing anchor</a><a href="/other/">Outside base</a><a href="javascript:alert(1)">Bad</a>',
  });
  const result = await checkSite({ distRoot: root, base: '/docs' });
  assert.equal(result.passed, false);
  assert.equal(result.errors.length, 4);
  assert.ok(result.errors.some(error => error.kind === 'missing-target'));
  assert.ok(result.errors.some(error => error.kind === 'missing-anchor'));
  assert.ok(result.errors.some(error => error.kind === 'outside-base'));
  assert.ok(result.errors.some(error => error.kind === 'unsafe-url'));
});

test('rejects private build paths and credentials without echoing their values', async t => {
  const root = await site(t, {
    'index.html': '<a href="https://user:secret@example.org">Source</a>',
    'app.js': 'const leaked="C:\\Users\\Synthetic\\workspace";',
  });
  const result = await checkSite({ distRoot: root, privatePrefixes: ['C:\\Users\\Synthetic'] });
  assert.equal(result.passed, false);
  assert.ok(result.errors.some(error => error.kind === 'private-path'));
  assert.ok(result.errors.some(error => error.kind === 'credentials-in-url'));
  assert.ok(!JSON.stringify(result).includes('secret'));
  assert.ok(!JSON.stringify(result).includes('Synthetic'));
});

test('rejects HTML event handlers and srcdoc including unquoted attributes', async t => {
  const root = await site(t, { 'index.html': '<img src=https://example.invalid/pixel onerror=alert(1)><iframe srcdoc="bad"></iframe>' });
  const result = await checkSite({ distRoot: root });
  assert.equal(result.passed, false);
  assert.equal(result.errors.filter(item => item.kind === 'unsafe-html-attribute').length, 2);
});
