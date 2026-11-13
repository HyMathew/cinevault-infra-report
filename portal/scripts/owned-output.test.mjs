import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { claimDist, sealDist } from './owned-output.mjs';

async function fixture(t) {
  const root = await mkdtemp(path.join(tmpdir(), 'cinevault-owned-output-test-'));
  await mkdir(path.join(root, 'portal'));
  t.after(async () => {
    assert.ok(root.startsWith(path.resolve(tmpdir()) + path.sep));
    await rm(root, { recursive: true, force: true });
  });
  return root;
}

test('unknown static output is preserved; only claimed output can be rebuilt', async t => {
  const root = await fixture(t);
  const dist = path.join(root, 'portal/dist');
  await mkdir(dist);
  await writeFile(path.join(dist, 'keep.txt'), 'user work');
  await assert.rejects(claimDist(root), /not owned/);
  assert.equal(await readFile(path.join(dist, 'keep.txt'), 'utf8'), 'user work');
});

test('a fresh claim survives Astro emptying its children and contains no machine path', async t => {
  const root = await fixture(t);
  const claim = await claimDist(root);
  await rm(path.join(claim.directory, '.cinevault-output.json'));
  await writeFile(path.join(claim.directory, 'index.html'), '<h1>Built</h1>');
  await sealDist(claim);
  const marker = await readFile(path.join(claim.directory, '.cinevault-output.json'), 'utf8');
  assert.deepEqual(JSON.parse(marker), { owner: 'cinevault-documentation-dist-v1' });
  assert.ok(!marker.includes(root));
  assert.equal((await claimDist(root)).inode, claim.inode);
});

test('a linked dist is refused even if its target has a matching owner marker', async t => {
  const root = await fixture(t);
  const outside = await fixture(t);
  const other = await claimDist(outside);
  await writeFile(path.join(other.directory, 'keep.txt'), 'outside');
  await symlink(other.directory, path.join(root, 'portal/dist'), process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(claimDist(root), /link/);
  assert.equal(await readFile(path.join(other.directory, 'keep.txt'), 'utf8'), 'outside');
});

test('a linked portal parent is refused before creating an output directory', async t => {
  const root = await fixture(t);
  const outside = await fixture(t);
  const parent = path.join(root, 'portal');
  assert.equal(path.relative(root, parent), 'portal');
  await rm(parent, { recursive: true });
  await symlink(path.join(outside, 'portal'), parent, process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(claimDist(root), /parent/);
  await assert.rejects(readFile(path.join(outside, 'portal/dist/.cinevault-output.json')), { code: 'ENOENT' });
});
