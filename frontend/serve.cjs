const http = require('http');
const fs = require('fs');
const path = require('path');
const DIST = path.join(__dirname, 'dist');
const MIME = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.ico':'image/x-icon'};
http.createServer((req, res) => {
  let fp = path.join(DIST, req.url === '/' ? 'index.html' : req.url);
  if (!fs.existsSync(fp)) fp = path.join(DIST, 'index.html');
  const ext = path.extname(fp);
  res.writeHead(200, {'Content-Type': MIME[ext]||'application/octet-stream'});
  fs.createReadStream(fp).pipe(res);
}).listen(5180, '127.0.0.1', () => console.log('Serving dist on :5180'));
