import assert from 'node:assert/strict';
import test from 'node:test';
import { parse } from 'parse5';
import { focusableContent } from './keyboard-content.mjs';

test('table and code scrolling enters natural Tab order without changing content or scripts', () => {
  const input = '<!doctype html><html lang="fr"><head><script>const value = "<table>";</script></head><body><h1 id="a">Guide</h1><table><tr><td>A &amp; B</td></tr></table><pre tabindex="-1"><code>&lt;movie&gt;</code></pre><a href="#a">Guide</a></body></html>';
  const output = focusableContent(input);
  assert.match(output, /<table tabindex="0">/);
  assert.match(output, /<pre tabindex="0">/);
  assert.match(output, /<script>const value = "<table>";<\/script>/);
  assert.match(output, /<code>&lt;movie&gt;<\/code>/);
  assert.match(output, /<td>A &amp; B<\/td>/);
  assert.deepEqual(parse(focusableContent(output)), parse(output));
});
