const https = require('https');

function fetchHtml(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => resolve(data));
      })
      .on('error', reject);
  });
}

async function main() {
  const url = process.argv[2] || 'https://www.moboreels.com';
  const html = await fetchHtml(url);
  const start = html.indexOf('window.__NUXT__');
  if (start === -1) {
    console.log(JSON.stringify({ error: 'no __NUXT__' }));
    return;
  }
  const end = html.indexOf('</script>', start);
  let snippet = html.slice(start, end);
  snippet = snippet.replace(/^window\.__NUXT__\s*=\s*/, '').replace(/;?\s*$/, '');

  const window = {};
  window.__NUXT__ = null;
  const evaluator = new Function('window', `return (${snippet});`);
  const data = evaluator(window);
  const homeData = data?.data?.[0] || {};
  const summary = {
    homeListVO1_keys: homeData.homeListVO1 ? Object.keys(homeData.homeListVO1) : null,
    homeListVO1_listCount: Array.isArray(homeData.homeListVO1?.list) ? homeData.homeListVO1.list.length : null,
    homeListVO1_first: homeData.homeListVO1?.list?.[0] || null,
    homeListVO2_keys: homeData.homeListVO2 ? Object.keys(homeData.homeListVO2) : null,
    homeListVO2_first: homeData.homeListVO2?.list?.[0] || null,
    homeListVO3_keys: homeData.homeListVO3 ? Object.keys(homeData.homeListVO3) : null,
    homeListVO3_first: homeData.homeListVO3?.list?.[0] || null,
    state_recList_first: data?.state?.recList?.[0] || null,
    hotWord: data?.state?.hotWord || null,
  };
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
