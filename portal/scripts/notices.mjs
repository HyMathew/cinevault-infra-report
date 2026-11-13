import { createHash } from 'node:crypto';
import { lstat, mkdir, readFile, readdir, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';

const digest = value => createHash('sha256').update(value).digest('hex');
const clientPackages = new Set(['astro', '@astrojs/starlight', 'astro-expressive-code', 'pagefind', '@pagefind/default-ui']);

/** Record the resolved build graph separately from the installed license texts.
 * This catalogue does not assert that every build dependency ships to browsers.
 */
export async function collectNotices(project) {
  const lock = JSON.parse(await readFile(path.join(project, 'package-lock.json'), 'utf8'));
  const provenance = JSON.parse(await readFile(path.join(project, 'licenses/provenance.json'), 'utf8'));
  const pagefindLicense = await readFile(path.join(project, 'licenses/pagefind-LICENSE'));
  if (digest(pagefindLicense) !== provenance['Pagefind/pagefind'].license_sha256) throw new Error('Pagefind license provenance mismatch');
  const texts = new Map();
  const packages = [];
  for (const [location, record] of Object.entries(lock.packages).sort(([a], [b]) => a.localeCompare(b, 'en'))) {
    if (location === '') continue;
    if (!/^node_modules\/(?:@[^/]+\/)?[^/]+(?:\/node_modules\/(?:@[^/]+\/)?[^/]+)*$/.test(location) || location.split('/').some(part => part === '.' || part === '..')) {
      throw new Error('Unsupported lock package location');
    }
    const directory = path.join(project, location);
    const name = location.split('node_modules/').at(-1);
    const entry = { name, version: record.version, license: record.license ?? null, integrity: record.integrity ?? null, installed: false, license_texts: [] };
    let stat;
    try { stat = await lstat(directory); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (stat) {
      if (!stat.isDirectory() || stat.isSymbolicLink() || await realpath(directory) !== path.resolve(directory)) throw new Error('Unsupported installed package directory');
      const installed = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8'));
      if (installed.version !== record.version) throw new Error('Installed package version differs from lock');
      entry.installed = true;
      async function licenseFile(filename, depth = 0) {
        const source = path.join(directory, filename);
        const file = await lstat(source);
        if (file.isSymbolicLink() || depth > 4) throw new Error('Unsupported package license file');
        if (file.isDirectory()) {
          for (const child of (await readdir(source)).sort()) await licenseFile(filename + '/' + child, depth + 1);
          return;
        }
        if (!file.isFile() || file.size > 512 * 1024 || entry.license_texts.length >= 1000) throw new Error('Unsupported package license file');
        const bytes = await readFile(source);
        const hash = digest(bytes);
        texts.set(hash, bytes);
        entry.license_texts.push({ filename, sha256: hash });
      }
      for (const filename of (await readdir(directory)).sort()) {
        if (!/^(?:licen[cs]e|copying|notice)(?:$|[._-])/i.test(filename)) continue;
        await licenseFile(filename);
      }
      if (name === 'pagefind' || name.startsWith('@pagefind/')) {
        const hash = digest(pagefindLicense);
        texts.set(hash, pagefindLicense);
        entry.license_texts.push({ filename: 'upstream/LICENSE', sha256: hash });
      }
      if (clientPackages.has(name) && entry.license_texts.length === 0) throw new Error('Missing client package license');
    }
    packages.push(entry);
  }
  return { catalogue: { schema: 1, scope: 'Resolved build dependencies and available installed upstream license texts; not a browser bundle inventory or legal certification', packages, upstream_license_provenance: provenance['Pagefind/pagefind'] }, texts };
}

export async function writeNotices(project) {
  const result = await collectNotices(project);
  const output = path.join(project, '.generated/public/third-party');
  await mkdir(path.join(output, 'licenses'), { recursive: true });
  for (const [hash, bytes] of result.texts) await writeFile(path.join(output, 'licenses', hash + '.txt'), bytes);
  await writeFile(path.join(output, 'packages.json'), JSON.stringify(result.catalogue, null, 2) + '\n');
  await writeFile(path.join(output, 'README.txt'), 'CineVault documentation dependencies\n\npackages.json records the locked build graph and available installed upstream license texts. Uninstalled optional platform packages are not redistributed here. The graph includes licenses other than MIT. This is not a complete browser bundle or symbol reachability audit. Each license_texts SHA-256 refers to licenses/<SHA-256>.txt. Pagefind license provenance is pinned in the catalogue.\n');
  return { resolved_packages: result.catalogue.packages.length, installed_packages: result.catalogue.packages.filter(item => item.installed).length, license_texts: result.texts.size };
}
