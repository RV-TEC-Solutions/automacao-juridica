import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: { useTypeScriptCli: false },
  output: "standalone",
  // O cliente da aplicação chama as rotas locais com barra final.
  skipTrailingSlashRedirect: true,
};


export default nextConfig;
