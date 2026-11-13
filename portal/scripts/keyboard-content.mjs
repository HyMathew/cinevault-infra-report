import { lstat, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { parse, serialize } from 'parse5';

export function focusableContent(html) {
  const document = parse(html);
  function visit(node) {
    // These elements may scroll horizontally at narrow widths. Static tabindex
    // also works without client scripts and preserves native table/code semantics.
    if (node.tagName === 'table' || node.tagName === 'pre') {
      node.attrs = node.attrs.filter(item => item.name !== 'tabindex');
      node.attrs.push({ name: 'tabindex', value: '0' });
    }
    for (const child of node.childNodes ?? []) visit(child);
  }
  visit(document);
  return serialize(document);
}

export async function enableKeyboardContent(directory) {
  let pages = 0;
  for (const name of await readdir(directory)) {
    const target = path.join(directory, name);
    const item = await lstat(target);
    if (item.isSymbolicLink()) throw new Error('Unsupported link in static output');
    if (item.isDirectory()) pages += await enableKeyboardContent(target);
    else if (item.isFile() && name.endsWith('.html')) {
      await writeFile(target, focusableContent(await readFile(target, 'utf8')));
      pages += 1;
    }
  }
  return pages;
}
