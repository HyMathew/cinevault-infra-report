// Offline visual QA only: renders local SVGs; all network requests are blocked.
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const puppeteer = require('./.render-tools/node_modules/puppeteer-core');

(async () => {
  const root = process.argv[2] ? path.resolve(process.argv[2]) : __dirname;
  const previews = path.join(root, 'previews');
  fs.mkdirSync(previews, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--disable-background-networking', '--disable-component-update'],
  });
  const results = [];
  try {
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', request => {
      if (/^(file|data):/.test(request.url())) request.continue();
      else request.abort();
    });
    for (const name of fs.readdirSync(root).filter(n => n.endsWith('.svg')).sort()) {
      const source = fs.readFileSync(path.join(root, name), 'utf8');
      const box = source.match(/viewBox="(?:0 0 )?(\d+) (\d+)"/);
      if (!box) throw new Error('Missing root viewBox: ' + name);
      const width = Number(box[1]), height = Number(box[2]);
      await page.setViewport({ width, height: Math.min(height, 1000), deviceScaleFactor: 1 });
      await page.goto(pathToFileURL(path.join(root, name)).href);
      await page.evaluate(({ width, height }) => {
        const root = document.querySelector('svg');
        root.setAttribute('width', width);
        root.setAttribute('height', height);
        root.style.width = width + 'px';
        root.style.height = height + 'px';
      }, { width, height });
      await page.evaluate(() => document.fonts.ready);
      const metrics = await page.evaluate(() => {
        const svg = document.querySelector('svg');
        if (!svg || document.querySelector('parsererror')) throw new Error('Invalid SVG');
        const outer = svg.getBoundingClientRect();
        const text = [...document.querySelectorAll('text')];
        return {
          textElements: text.length,
          outsideRoot: text.filter(node => {
            const b = node.getBoundingClientRect();
            return b.left < outer.left - 1 || b.top < outer.top - 1 ||
              b.right > outer.right + 1 || b.bottom > outer.bottom + 1;
          }).length,
        };
      });
      await page.screenshot({ path: path.join(previews, name.replace(/\.svg$/, '.png')), fullPage: true });
      results.push({ name, width, height, ...metrics });
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(root, 'visual-qa.json'), JSON.stringify({
    mode: 'offline-local-svg-only', results,
  }, null, 2) + '\n');
  console.log(JSON.stringify(results));
})().catch(error => { console.error(error); process.exitCode = 1; });
