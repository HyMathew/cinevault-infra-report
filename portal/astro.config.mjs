import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { satteri } from '@astrojs/markdown-satteri';
import { normalizeBase } from './scripts/prepare.mjs';

const site = new URL(process.env.DOCS_SITE ?? 'https://hymathew.github.io');
if (site.protocol !== 'https:' || site.username || site.password || site.search || site.hash || site.pathname !== '/') {
  throw new Error('DOCS_SITE must be an HTTPS origin without credentials or path');
}

export default defineConfig({
  site: site.origin,
  base: normalizeBase(process.env.DOCS_BASE ?? '/cinevault-infra-report') || '/',
  output: 'static',
  markdown: { processor: satteri({ features: { directive: true } }) },
  srcDir: './.generated/src',
  publicDir: './.generated/public',
  integrations: [starlight({
    title: 'CineVault · Documentation',
    description: 'Architecture, guides et preuves de qualification de CineVault. Version Enterprise2.1 en préparation ; référence v1 préservée.',
    locales: { root: { label: 'Français', lang: 'fr' } },
    customCss: ['./styles/tokens.css'],
    social: [{ icon: 'github', label: 'Sources du projet', href: 'https://github.com/HyMathew/cinevault-infra-report' }],
    sidebar: [
      { label: 'Commencer', items: [{ label: 'État du projet', slug: '' }, { label: 'Parcours et règles produit', slug: 'guides/product' }, { label: 'Conception', slug: 'guides/design' }] },
      { label: 'Guides et qualification', items: [{ autogenerate: { directory: 'guides', collapsed: true } }] },
      { label: 'Preuves historiques', items: [{ autogenerate: { directory: 'records/evidence', collapsed: true } }] },
      { label: 'Rapport versionné', items: [{ autogenerate: { directory: 'records/report', collapsed: true } }] },
    ],
    tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
    lastUpdated: false,
  })],
});
