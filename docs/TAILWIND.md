# Tailwind CSS v4 Build

This project uses the **Tailwind CSS v4 standalone CLI** (no Node/npm).

## Installation (once per machine)

Download the standalone CLI binary for your platform from
https://github.com/tailwindlabs/tailwindcss/releases (v4.x).

```bash
# Example for macOS ARM64:
curl -L -o tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.11/tailwindcss-macos-arm64
chmod +x tailwindcss
sudo mv tailwindcss /usr/local/bin/
```

Verify: `tailwindcss --version` should print `tailwindcss v4.x.x`.

## Build (development)

From the project root:

```bash
tailwindcss -i app/static/src/main.css -o app/static/dist/main.css --watch
```

## Build (production)

```bash
tailwindcss -i app/static/src/main.css -o app/static/dist/main.css --minify
```
