import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { collectNotices } from './notices.mjs';

async function fixture(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'cinevault-notices-test-'));
  t.after(async () => {
    assert.ok(root.startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(root, { recursive: true, force: true });
  });
  await mkdir(path.join(root, 'licenses'));
  await writeFile(path.join(root, 'licenses/pagefind-LICENSE'), 'upstream');
  await writeFile(path.join(root, 'licenses/provenance.json'), JSON.stringify({ 'Pagefind/pagefind': { license_sha256: createHash('sha256').update('upstream').digest('hex') } }));
  await mkdir(path.join(root, 'node_modules/pagefind/LICENSE'), { recursive: true });
  await writeFile(path.join(root, 'node_modules/pagefind/package.json'), JSON.stringify({ name: 'pagefind', version: '1.6.0' }));
  await writeFile(path.join(root, 'node_modules/pagefind/LICENSE/LICENSE'), 'bundled license');
  await writeFile(path.join(root, 'node_modules/pagefind/LICENSE/LICENSE-other'), 'third party');
  await writeFile(path.join(root, 'package-lock.json'), JSON.stringify({ packages: { '': {}, 'node_modules/pagefind': { version: '1.6.0', license: 'MIT' }, 'node_modules/@pagefind/linux-x64': { version: '1.6.0', license: 'MIT' } } }));
  return root;
}

test('includes a bundled LICENSE directory and distinguishes absent optional binaries', async t => {
  const root = await fixture(t);
  const result = await collectNotices(root);
  const pagefind = result.catalogue.packages.find(item => item.name === 'pagefind');
  assert.equal(pagefind.installed, true);
  assert.deepEqual(pagefind.license_texts.map(item => item.filename), ['LICENSE/LICENSE', 'LICENSE/LICENSE-other', 'upstream/LICENSE']);
  assert.equal(result.texts.size, 3);
  assert.equal(result.catalogue.packages.find(item => item.name === '@pagefind/linux-x64').installed, false);
});

test('refuses changed upstream license text before publication', async t => {
  const root = await fixture(t);
  await writeFile(path.join(root, 'licenses/pagefind-LICENSE'), 'different');
  await assert.rejects(collectNotices(root), /provenance mismatch/);
});
