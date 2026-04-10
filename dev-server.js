const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const API_HOST = 'localhost';
const API_PORT = 8000;

const MIME = {
    '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
    '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
    '.woff2': 'font/woff2', '.woff': 'font/woff',
};

http.createServer((req, res) => {
    // Proxy /api/ to backend
    if (req.url.startsWith('/api/')) {
        const opts = { hostname: API_HOST, port: API_PORT, path: req.url, method: req.method, headers: req.headers };
        const proxy = http.request(opts, proxyRes => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        });
        proxy.on('error', () => { res.writeHead(502); res.end('Backend unavailable'); });
        req.pipe(proxy);
        return;
    }

    // Serve static files
    let filePath = path.join(__dirname, req.url === '/' ? 'index.html' : decodeURIComponent(req.url));
    fs.readFile(filePath, (err, data) => {
        if (err) { res.writeHead(404); res.end('Not found'); return; }
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        res.end(data);
    });
}).listen(PORT, () => console.log(`Dashboard: http://localhost:${PORT}`));
