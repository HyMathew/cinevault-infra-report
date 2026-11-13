import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, rename, rm, symlink, writeFile } from 'node:fs/promises';
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

test('canonicalizes an aliased project root before checking installed package paths', async t => {
  const root = await fixture(t);
  const alias = path.join(root, 'project-alias');
  await symlink(root, alias, process.platform === 'win32' ? 'junction' : 'dir');
  const result = await collectNotices(alias);
  assert.equal(result.catalogue.packages.find(item => item.name === 'pagefind').installed, true);
});

test('still refuses a linked installed package beneath a canonical project root', async t => {
  const root = await fixture(t);
  const directory = path.join(root, 'node_modules/pagefind');
  const target = path.join(root, 'node_modules/pagefind-real');
  await rename(directory, target);
  await symlink(target, directory, process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(collectNotices(root), /Unsupported installed package directory/);
});
