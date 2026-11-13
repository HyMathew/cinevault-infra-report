import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = fileURLToPath(new URL('..', import.meta.url));
async function inventory(directory, prefix = '') {
  const records = [];
  for (const name of (await readdir(directory)).sort()) {
    const file = path.join(directory, name);
    const item = await lstat(file);
    if (item.isSymbolicLink()) throw new Error('Unexpected link in built output');
    const relative = prefix + name;
    if (item.isDirectory()) records.push(...await inventory(file, relative + '/'));
    else if (item.isFile()) records.push({ path: relative, sha256: createHash('sha256').update(await readFile(file)).digest('hex') });
  }
  return records;
}
function build() {
  const result = spawnSync(process.execPath, ['scripts/build.mjs'], { cwd: project, stdio: 'inherit' });
  if (result.error || result.status !== 0) throw new Error('Reproducibility build failed');
}
build();
const first = await inventory(path.join(project, 'dist'));
build();
const second = await inventory(path.join(project, 'dist'));
assert.deepEqual(second, first, 'Two builds on the same platform must produce identical file names and bytes');
const receipt = {
  schema: 1, passed: true, node: process.version, builds: 2,
  scope: 'Byte-for-byte repeatability on this machine with unchanged inputs; no cross-platform or independent builder claim',
  files: second,
};
await mkdir(path.join(project, '.cache'), { recursive: true });
await writeFile(path.join(project, '.cache/reproducibility.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({ reproducible: true, files: second.length, builds: 2 }));
