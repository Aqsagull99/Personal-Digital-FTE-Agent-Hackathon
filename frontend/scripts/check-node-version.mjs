const major = Number.parseInt(process.versions.node.split(".")[0] ?? "0", 10);

if (!Number.isFinite(major) || major < 18 || major >= 23) {
  console.error(
    `Unsupported Node.js version ${process.versions.node}. ` +
      "Use Node 20 LTS (recommended) or any version >=18.18 and <23 for Next.js 14."
  );
  process.exit(1);
}
