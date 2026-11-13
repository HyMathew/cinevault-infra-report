import { lstat, mkdir, readFile, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';

const OWNER = 'cinevault-documentation-dist-v1';
const MARKER = '.cinevault-output.json';

async function portalDirectory(repoRoot) {
  const root = await realpath(path.resolve(repoRoot));
  const project = path.join(root, 'portal');
  const info = await lstat(project);
  if (!info.isDirectory() || info.isSymbolicLink() || await realpath(project) !== project) {
    throw new Error('Portal output parent must be a real repository directory');
  }
  return { root, project };
}

async function inspectDist(directory) {
  let info;
  try { info = await lstat(directory, { bigint: true }); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (info && (!info.isDirectory() || info.isSymbolicLink() || await realpath(directory) !== directory)) throw new Error('Static output must not be a link');
  return info;
}

async function ownerMarker(directory, { missing = false } = {}) {
  const marker = path.join(directory, MARKER);
  let info;
  try { info = await lstat(marker); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (!info && missing) return false;
  if (!info || !info.isFile() || info.isSymbolicLink() || info.size > 256 || info.nlink !== 1) throw new Error('Static output is not owned');
  let value;
  try { value = JSON.parse(await readFile(marker, 'utf8')); } catch { throw new Error('Static output is not owned'); }
  if (value.owner !== OWNER) throw new Error('Static output is not owned');
  return true;
}

/** Refuse unknown output before Astro can empty its contents. */
export async function claimDist(repoRoot) {
  const { root, project } = await portalDirectory(repoRoot);
  const directory = path.join(project, 'dist');
  let info = await inspectDist(directory);
  if (info) await ownerMarker(directory);
  else {
    // Non-recursive creation refuses a concurrent replacement instead of adopting it.
    await mkdir(directory);
    await writeFile(path.join(directory, MARKER), JSON.stringify({ owner: OWNER }) + '\n', { flag: 'wx' });
    info = await inspectDist(directory);
  }
  return { root, directory, device: info.dev, inode: info.ino };
}

/** Astro empties children, including our marker; restore it on success or failure. */
export async function sealDist(claim) {
  const { project } = await portalDirectory(claim.root);
  if (claim.directory !== path.join(project, 'dist')) throw new Error('Invalid static output claim');
  const info = await inspectDist(claim.directory);
  if (!info || info.dev !== claim.device || info.ino !== claim.inode) throw new Error('Static output directory was replaced during build');
  if (!await ownerMarker(claim.directory, { missing: true })) {
    await writeFile(path.join(claim.directory, MARKER), JSON.stringify({ owner: OWNER }) + '\n', { flag: 'wx' });
  }
}
