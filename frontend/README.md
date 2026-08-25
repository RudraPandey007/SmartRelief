# Smart Relief — SIH Frontend (Fixed)

## What was fixed
Added `vite.config.js` with `base: "./"` so built asset paths are relative
instead of absolute. Without this, the built site only worked when served
from a domain root by Vite's dev server — opening it directly as a file,
or on another laptop/phone, resulted in a blank white screen because the
browser couldn't resolve `/assets/...` paths.

## Run locally (development)
```bash
npm install
npm run dev
```
Open the local URL Vite prints.

## Show it on your phone (same WiFi as your laptop)
```bash
npm run dev -- --host
```
Vite will print a "Network" URL like `http://192.168.x.x:5173` — open that
on your phone.

## Build for production / sharing
```bash
npm run build
npm run preview
```
`npm run preview` serves the built `dist` folder correctly over HTTP.
**Do not** double-click `dist/index.html` to open it directly in a browser —
ES module scripts are blocked under the `file://` protocol and it will show
a blank page.

## Best option for demo day
Deploy the `dist` folder to Vercel or Netlify (drag-and-drop works, no CLI
needed) for one public URL that works identically on any device.
