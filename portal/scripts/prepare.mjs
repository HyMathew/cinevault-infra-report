import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, readFile, realpath, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkStringify from 'remark-stringify';
import remarkGfm from 'remark-gfm';
import { visit } from 'unist-util-visit';
import GithubSlugger from 'github-slugger';
import { createSatteriMarkdownProcessor } from '@astrojs/markdown-satteri';

const OWNER = 'cinevault-documentation-generated-v1';
const MAX_FILE = 32 * 1024 * 1024;
const MAX_TOTAL = 256 * 1024 * 1024;
const posix = value => value.split(path.sep).join('/');
const sha256 = value => createHash('sha256').update(value).digest('hex');
const within = (root, value) => {
  const relative = path.relative(root, value);
  return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
};

export function normalizeBase(base = '/') {
  if (typeof base !== 'string' || !/^\/(?:[A-Za-z0-9_-]+\/?)*$/.test(base) || base.startsWith('//')) {
    throw new Error('Invalid documentation base');
  }
  return base === '/' ? '' : base.replace(/\/$/, '');
}

const textOf = node => node.value ?? node.alt ?? (node.children ?? []).map(textOf).join('');
const urlPath = value => value.split('/').map(encodeURIComponent).join('/');

function routeFor(source) {
  if (source === 'README.md') return '';
  if (!source.includes('/')) return 'guides/' + source.replace(/\.md$/i, '').toLowerCase();
  const documentation = source.startsWith('docs/');
  const name = (documentation ? source.slice('docs/'.length) : source).replace(/\.md$/i, '').toLowerCase();
  return (documentation ? 'guides/' : 'records/') + name.replace(/(?:^|\/)readme$/, '').replace(/\/$/, '');
}

/** Only tracked public inputs are considered; ignored plans and secrets stay outside publication. */
export async function prepare({ repoRoot, outputRoot, base = '/' }) {
  const root = await realpath(path.resolve(repoRoot));
  const portal = path.join(root, 'portal');
  const parent = await lstat(portal);
  if (!parent.isDirectory() || parent.isSymbolicLink() || await realpath(portal) !== portal) {
    throw new Error('Generated output parent is not owned: portal must be a real repository directory');
  }
  const expectedOutput = path.join(root, 'portal', '.generated');
  const output = path.resolve(outputRoot ?? expectedOutput);
  if (output !== expectedOutput || !within(root, output)) throw new Error('Invalid generated output');
  base = normalizeBase(base);
  const tracked = new Set(execFileSync('git', ['ls-files', '-z'], { cwd: root, encoding: 'utf8' }).split('\0').filter(Boolean));
  const sources = [...tracked].filter(name => (!name.includes('/') && name.endsWith('.md') && name !== 'AGENTS.md') || (
    ['docs/', 'report/', 'evidence/'].some(prefix => name.startsWith(prefix)) && name.endsWith('.md') && !name.startsWith('docs/superpowers/') &&
    !name.split('/').some(segment => segment.startsWith('.'))
  )).sort();
  if (!sources.includes('README.md')) throw new Error('Missing tracked README.md');
  const parser = unified().use(remarkParse).use(remarkGfm).use(remarkStringify, { bullet: '-', fences: true });
  // Obtain IDs from the same pinned engine as Astro, rather than predicting
  // smart punctuation, image text or other rendered-heading transformations.
  const headingRenderer = await createSatteriMarkdownProcessor({ syntaxHighlight: false, features: { directive: true } });
  const pages = new Map();
  const routes = new Set();

  async function input(name) {
    const absolute = path.resolve(root, name);
    if (!within(root, absolute)) throw new Error('Input outside repository: ' + name);
    let canonical;
    try { canonical = await realpath(absolute); } catch { throw new Error('Missing local input: ' + name); }
    if (!within(root, canonical)) throw new Error('Input outside repository through symlink: ' + name);
    if (!tracked.has(name)) throw new Error('Untracked local input: ' + name);
    const stat = await lstat(absolute);
    if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('Unsupported local input: ' + name);
    if (stat.size > MAX_FILE) throw new Error('Input exceeds document size limit: ' + name);
    return readFile(absolute);
  }

  for (const source of sources) {
    const bytes = await input(source);
    const markdown = new TextDecoder('utf-8', { fatal: true }).decode(bytes).replace(/\r\n?/g, '\n');
    if (markdown.startsWith('---\n')) throw new Error('Source frontmatter requires explicit mapping: ' + source);
    const tree = parser.parse(markdown);
    visit(tree, 'html', () => { throw new Error('Raw HTML is not supported in public Markdown: ' + source); });
    const first = tree.children[0];
    const title = first?.type === 'heading' && first.depth === 1 ? textOf(first) : path.basename(source, '.md');
    const extractedTitle = first?.type === 'heading' && first.depth === 1 ? first : null;
    const sourceSlugs = new GithubSlugger();
    const anchors = new Map();
    const contentAnchors = [];
    visit(tree, 'heading', node => {
      const sourceAnchor = sourceSlugs.slug(textOf(node));
      if (node === extractedTitle) anchors.set(sourceAnchor, '_top');
      else contentAnchors.push(sourceAnchor);
    });
    if (first?.type === 'heading' && first.depth === 1) tree.children.shift();
    const rendered = await headingRenderer.render(parser.stringify(tree));
    if (rendered.metadata.headings.length !== contentAnchors.length) throw new Error('Unsupported heading transformation: ' + source);
    contentAnchors.forEach((anchor, index) => anchors.set(anchor, rendered.metadata.headings[index].slug));
    const route = routeFor(source);
    if (routes.has(route)) throw new Error('Documentation route collision: ' + route);
    routes.add(route);
    pages.set(source, { source, bytes, tree, title, route, anchors });
  }

  function fragmentFor(fragment, page) {
    if (!fragment) return '';
    let decoded;
    try { decoded = decodeURIComponent(fragment.slice(1)); } catch { throw new Error('Invalid encoded heading fragment: ' + page.source); }
    const target = page.anchors.get(decoded);
    return target === undefined ? fragment : '#' + encodeURIComponent(target);
  }

  const assets = new Map();
  let totalBytes = 0;
  for (const page of pages.values()) {
    const links = [];
    visit(page.tree, node => {
      if (node.type === 'link' || node.type === 'image' || node.type === 'definition') links.push(node);
    });
    for (const link of links) {
      const value = link.url;
      if (value === '') continue;
      if (value.startsWith('#')) {
        link.url = fragmentFor(value, page);
        continue;
      }
      const scheme = /^([A-Za-z][A-Za-z0-9+.-]*):/.exec(value);
      if (scheme) {
        if (!['https', 'http', 'mailto', 'tel'].includes(scheme[1].toLowerCase())) throw new Error('Unsafe link scheme: ' + page.source);
        continue;
      }
      if (value.startsWith('//')) throw new Error('Unsafe link scheme: ' + page.source);
      const match = /^([^?#]*)(\?[^#]*)?(#.*)?$/.exec(value);
      let decoded;
      try { decoded = decodeURIComponent(match[1]); } catch { throw new Error('Invalid encoded local link: ' + page.source); }
      if (decoded.includes('\\') || /[\x00-\x1f\x7f]/.test(decoded)) throw new Error('Invalid local link: ' + page.source);
      const target = decoded === '' ? path.resolve(root, page.source) : path.resolve(root, path.dirname(page.source), decoded);
      if (!within(root, target)) throw new Error('Link outside repository: ' + page.source);
      const relative = posix(path.relative(root, target));
      const bytes = await input(relative);
      let fragment = match[3] ?? '';
      const query = match[2] ?? '';
      if (pages.has(relative)) {
        const destination = pages.get(relative);
        fragment = fragmentFor(fragment, destination);
        link.url = base + '/' + (destination.route ? urlPath(destination.route) + '/' : '') + query + fragment;
      } else {
        if (!assets.has(relative)) {
          totalBytes += bytes.length;
          if (totalBytes > MAX_TOTAL) throw new Error('Published assets exceed total size limit');
          assets.set(relative, { bytes, sha256: sha256(bytes) });
        }
        link.url = base + '/sources/' + urlPath(relative) + query + fragment;
      }
    }
  }

  // Validate everything before deleting any old generated output. Never follow a replacement symlink.
  let previous;
  try { previous = await lstat(output); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (previous) {
    if (!previous.isDirectory() || previous.isSymbolicLink() || await realpath(output) !== expectedOutput) throw new Error('Generated output is not owned');
    let marker;
    try { marker = JSON.parse(await readFile(path.join(output, '.owner.json'), 'utf8')); } catch { throw new Error('Generated output is not owned'); }
    if (marker.owner !== OWNER || marker.repository !== root) throw new Error('Generated output is not owned');
    // expectedOutput is an explicit, resolved child of this repository, checked above.
    await rm(output, { recursive: true });
  }
  await mkdir(path.join(output, 'src/content/docs'), { recursive: true });
  await mkdir(path.join(output, 'public'), { recursive: true });
  await writeFile(path.join(output, '.owner.json'), JSON.stringify({ owner: OWNER, repository: root }));
  const manifest = {
    schema: 1, base, source_commit: null, source_clean: null, tooling_clean: null,
    generator_sha256: sha256(await readFile(new URL(import.meta.url))), pages: [], assets: [],
  };
  const commit = spawnSync('git', ['rev-parse', '--verify', 'HEAD'], { cwd: root, encoding: 'utf8' });
  if (commit.status === 0) {
    manifest.source_commit = commit.stdout.trim();
    const difference = spawnSync('git', ['diff', '--quiet', 'HEAD', '--', ...sources, ...assets.keys()], { cwd: root });
    if (difference.status !== 0 && difference.status !== 1) throw new Error('Cannot verify source state');
    manifest.source_clean = difference.status === 0;
    const tooling = spawnSync('git', ['status', '--porcelain=v1', '-z', '--untracked-files=all', '--', '.gitignore', 'portal'], { cwd: root, encoding: 'utf8' });
    if (tooling.status !== 0) throw new Error('Cannot verify portal tooling state');
    manifest.tooling_clean = tooling.stdout.length === 0;
  }
  for (const page of pages.values()) {
    const generated = '---\ntitle: ' + JSON.stringify(page.title) + '\n---\n\n' + parser.stringify(page.tree);
    const filename = page.route ? page.route + '.md' : 'index.md';
    const destination = path.join(output, 'src/content/docs', filename);
    await mkdir(path.dirname(destination), { recursive: true });
    await writeFile(destination, generated, 'utf8');
    manifest.pages.push({ source: page.source, route: page.route, source_sha256: sha256(page.bytes), rendered_markdown_sha256: sha256(generated) });
  }
  for (const [source, asset] of [...assets].sort(([a], [b]) => a.localeCompare(b, 'en'))) {
    const destination = path.join(output, 'public/sources', source);
    await mkdir(path.dirname(destination), { recursive: true });
    await writeFile(destination, asset.bytes);
    manifest.assets.push({ source, sha256: asset.sha256, bytes: asset.bytes.length });
  }
  await writeFile(path.join(output, 'public/source-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  return manifest;
}
