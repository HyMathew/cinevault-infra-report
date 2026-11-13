import { spawnSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = fileURLToPath(new URL('..', import.meta.url));
if (!process.env.npm_execpath) throw new Error('Run this command through npm run sbom');
const result = spawnSync(process.execPath, [process.env.npm_execpath, 'sbom', '--sbom-format', 'cyclonedx'], { cwd: project, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
if (result.error || result.status !== 0) throw new Error('npm SBOM generation failed');
const sbom = JSON.parse(result.stdout);
if (sbom.bomFormat !== 'CycloneDX' || !Array.isArray(sbom.components)) throw new Error('Invalid npm SBOM');
await mkdir(path.join(project, '.cache'), { recursive: true });
await writeFile(path.join(project, '.cache/sbom.cdx.json'), JSON.stringify(sbom, null, 2) + '\n');
console.log(JSON.stringify({ bomFormat: sbom.bomFormat, components: sbom.components.length }));
