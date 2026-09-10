const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const standaloneDir = path.join(root, ".next", "standalone");
const standaloneNext = path.join(standaloneDir, ".next");
const staticSrc = path.join(root, ".next", "static");
const publicSrc = path.join(root, "public");

if (!fs.existsSync(standaloneDir)) {
  console.log("No standalone output; skipping asset copy.");
  process.exit(0);
}

if (!fs.existsSync(staticSrc)) {
  console.error("Missing .next/static after build.");
  process.exit(1);
}

fs.mkdirSync(standaloneNext, { recursive: true });
fs.cpSync(staticSrc, path.join(standaloneNext, "static"), { recursive: true });

if (fs.existsSync(publicSrc)) {
  fs.cpSync(publicSrc, path.join(standaloneDir, "public"), { recursive: true });
}

console.log("Copied standalone static assets.");
