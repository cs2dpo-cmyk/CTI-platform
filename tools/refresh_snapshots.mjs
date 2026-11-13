/**
 * Refresh the KEV and EPSS snapshots and stamp their dates.
 *
 *   node tools/refresh_snapshots.mjs            # refresh EPSS for known CVEs
 *   node tools/refresh_snapshots.mjs --cves a.json   # extra CVEs to look up
 *
 * Node is used because it ships a working TLS stack on this host; the Python
 * side only reads the resulting files.
 */
import https from 'node:https';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.argv[1], '..', '..');
const DATA = path.join(ROOT, 'data');
const today = new Date().toISOString().slice(0, 10);

function get(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'cti-platform-refresh/1.0' } }, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error('HTTP ' + res.statusCode + ' ' + url));
        return;
      }
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(body)); } catch (error) { reject(error); }
      });
    }).on('error', reject);
  });
}

async function refreshKev() {
  const url = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json';
  const payload = await get(url);
  const ids = payload.vulnerabilities.map((item) => item.cveID.toUpperCase()).sort();
  fs.writeFileSync(
    path.join(DATA, 'kev_ids.json'),
    JSON.stringify({ generated: (payload.dateReleased || today).slice(0, 10), count: ids.length, ids })
  );
  return ids.length;
}

async function refreshEpss() {
  const file = path.join(DATA, 'epss.json');
  const existing = JSON.parse(fs.readFileSync(file, 'utf8'));
  const known = Object.keys(existing.scores || existing);
  const extra = process.argv.includes('--cves')
    ? JSON.parse(fs.readFileSync(process.argv[process.argv.indexOf('--cves') + 1], 'utf8'))
    : [];
  const cves = [...new Set([...known, ...extra])];

  const scores = {};
  for (let i = 0; i < cves.length; i += 100) {
    const chunk = cves.slice(i, i + 100);
    const payload = await get('https://api.first.org/data/v1/epss?cve=' + chunk.join(',') + '&limit=200');
    for (const row of payload.data || []) scores[row.cve] = Number(row.epss);
  }
  fs.writeFileSync(
    file,
    JSON.stringify({ generated: today, source: 'https://api.first.org/data/v1/epss', scores }, null, 1)
  );
  return Object.keys(scores).length;
}

async function main() {
  const kevCount = await refreshKev();
  const epssCount = await refreshEpss();

  const registryFile = path.join(DATA, 'snapshots.json');
  const registry = JSON.parse(fs.readFileSync(registryFile, 'utf8'));
  registry.kev = { ...(registry.kev || {}), generated: today };
  registry.epss = { ...(registry.epss || {}), generated: today };
  fs.writeFileSync(registryFile, JSON.stringify(registry, null, 2) + '\n');

  console.log('kev', kevCount, 'epss', epssCount, 'as of', today);
}

main().catch((error) => {
  console.error('refresh failed:', error.message);
  process.exit(1);
});
