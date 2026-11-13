import { readdir, readFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'parse5';
import { normalizeBase } from './prepare.mjs';

const within = (root, target) => {
  const relative = path.relative(root, target);
  return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
};

export async function checkSite({ distRoot, base = '/', privatePrefixes = [] }) {
  const root = await realpath(path.resolve(distRoot));
  base = normalizeBase(base);
  const files = new Map();
  const documents = new Map();
  const errors = [];
  let checkedLinks = 0;
  const forbidden = privatePrefixes.filter(Boolean).flatMap(value => [
    value, value.replaceAll('\\', '/'), value.replaceAll('\\', '\\\\'),
  ]).map(value => Buffer.from(value.toLowerCase()));

  async function walk(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
      const absolute = path.join(directory, entry.name);
      const relative = path.relative(root, absolute).split(path.sep).join('/');
      if (entry.isSymbolicLink()) {
        errors.push({ file: relative, kind: 'symlink-output' });
      } else if (entry.isDirectory()) {
        await walk(absolute);
      } else if (entry.isFile()) {
        const bytes = await readFile(absolute);
        files.set(relative, bytes);
        // Include JSON-escaped and slash-normalized representations, without printing prefixes.
        const lowercase = Buffer.from(bytes.toString('utf8').toLowerCase());
        if (forbidden.some(prefix => lowercase.includes(prefix))) errors.push({ file: relative, kind: 'private-path' });
      }
    }
  }
  await walk(root);

  for (const [file, bytes] of files) {
    if (!file.endsWith('.html')) continue;
    const ids = new Set();
    const links = [];
    function visit(node) {
      const attributes = new Map((node.attrs ?? []).map(attribute => [attribute.name, attribute.value]));
      if ([...attributes.keys()].some(name => /^on/i.test(name) || name === 'srcdoc')) {
        errors.push({ file, kind: 'unsafe-html-attribute' });
      }
      if (attributes.has('id')) ids.add(attributes.get('id'));
      const fields = {
        a: ['href'], link: ['href'], img: ['src'], script: ['src'],
        source: ['src'], video: ['src', 'poster'], object: ['data'],
      }[node.tagName] ?? [];
      for (const field of fields) if (attributes.has(field)) links.push({ value: attributes.get(field), tag: node.tagName });
      for (const child of node.childNodes ?? []) visit(child);
    }
    visit(parse(bytes.toString('utf8')));
    documents.set(file, { ids, links });
  }

  for (const [file, document] of documents) {
    const virtual = file.endsWith('index.html') ? file.slice(0, -'index.html'.length) : file;
    const current = 'https://documentation.invalid' + base + '/' + virtual;
    for (const { value, tag } of document.links) {
      checkedLinks++;
      let url;
      try { url = new URL(value, current); } catch { errors.push({ file, kind: 'invalid-url' }); continue; }
      if (url.username || url.password) { errors.push({ file, kind: 'credentials-in-url' }); continue; }
      if (!['https:', 'http:', 'mailto:', 'tel:'].includes(url.protocol)) {
        if (tag === 'img' && url.protocol === 'data:' && /^data:image\//.test(value)) continue;
        errors.push({ file, kind: 'unsafe-url' });
        continue;
      }
      if (url.origin !== 'https://documentation.invalid') continue;
      let decoded;
      try { decoded = decodeURIComponent(url.pathname); } catch { errors.push({ file, kind: 'invalid-url' }); continue; }
      if (base && !decoded.startsWith(base + '/') && decoded !== base) { errors.push({ file, kind: 'outside-base' }); continue; }
      const relative = decoded.slice(base.length).replace(/^\//, '');
      const target = path.resolve(root, relative);
      if (!within(root, target)) { errors.push({ file, kind: 'outside-output' }); continue; }
      let candidate = path.relative(root, target).split(path.sep).join('/');
      if (!files.has(candidate)) candidate = candidate.replace(/\/$/, '') + (candidate ? '/' : '') + 'index.html';
      if (!files.has(candidate)) { errors.push({ file, kind: 'missing-target', target: relative }); continue; }
      if (url.hash && documents.has(candidate)) {
        let anchor;
        try { anchor = decodeURIComponent(url.hash.slice(1)); } catch { errors.push({ file, kind: 'invalid-anchor' }); continue; }
        if (!documents.get(candidate).ids.has(anchor)) errors.push({ file, kind: 'missing-anchor' });
      }
    }
  }
  return { passed: errors.length === 0, htmlPages: documents.size, checkedLinks, errors };
}
