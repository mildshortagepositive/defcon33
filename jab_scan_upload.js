/**
 * Upload each PNG from jab_output to https://jabcode.org/scan/,
 * collect all decoded URLs from all 100 files.
 *
 * Run: node jab_scan_upload.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const JAB_OUTPUT = path.join(__dirname, 'jab_output');
const SCAN_URL = 'https://jabcode.org/scan/';

const PAGE_URLS = new Set([
  'https://github.com/jabcode/jabcode',
  'https://jabcode.org/',
  'https://jabcode.org/scan',
  'https://jabcode.org/create',
  'https://jabcode.org/contact',
]);

function getPngFiles() {
  const files = fs.readdirSync(JAB_OUTPUT).filter((f) => f.endsWith('.png'));
  return files.sort().map((f) => path.join(JAB_OUTPUT, f));
}

function extractUrls(text) {
  if (!text || typeof text !== 'string') return [];
  const urls = [];
  const re = /https?:\/\/[^\s"'<>)\]]+/gi;
  let m;
  while ((m = re.exec(text)) !== null) urls.push(m[0].replace(/[)\],]+$/, ''));
  return urls;
}

function decodedUrls(text, linkHrefs) {
  const fromText = extractUrls(text || '');
  const candidates = [...fromText, ...(linkHrefs || [])];
  const out = [];
  const seen = new Set();
  for (const u of candidates) {
    const norm = u.trim();
    if (norm && !PAGE_URLS.has(norm) && !norm.includes('jabcode.org') && !norm.includes('github.com/jabcode') && !seen.has(norm)) {
      seen.add(norm);
      out.push(norm);
    }
  }
  return out;
}

async function main() {
  const pngFiles = getPngFiles();
  console.log('Found', pngFiles.length, 'PNG files. Scanning all...\n');

  let browser;
  try {
    browser = await chromium.launch({ headless: true, channel: 'chrome' });
  } catch (_) {
    browser = await chromium.launch({ headless: true });
  }
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(SCAN_URL, { waitUntil: 'networkidle' });

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.waitFor({ state: 'attached' });

  const results = []; // { file, urls[] }
  const allUrlsSet = new Set();

  for (let i = 0; i < pngFiles.length; i++) {
    const file = pngFiles[i];
    const base = path.basename(file);
    process.stdout.write(`[${i + 1}/${pngFiles.length}] ${base} ... `);

    await fileInput.setInputFiles(file);
    await page.waitForTimeout(1500);

    const bodyText = await page.locator('body').textContent();
    const links = await page.locator('a[href^="http"]').all();
    const linkHrefs = [];
    for (const link of links) {
      const href = await link.getAttribute('href');
      if (href && (await link.isVisible())) linkHrefs.push(href);
    }
    const urls = decodedUrls(bodyText, linkHrefs);

    if (urls.length > 0) {
      console.log(urls.join(', '));
      results.push({ file: base, urls });
      urls.forEach((u) => allUrlsSet.add(u));
    } else {
      console.log('no URL');
    }
  }

  await browser.close();

  console.log('\n--- All decoded URLs ---');
  const allUrls = [...allUrlsSet].sort();
  if (allUrls.length === 0) {
    console.log('(none)');
  } else {
    allUrls.forEach((u) => console.log(u));
  }
  console.log('\n--- By file ---');
  results.forEach(({ file, urls }) => {
    console.log(file + ': ' + urls.join(', '));
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
