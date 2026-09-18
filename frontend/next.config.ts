import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: { useTypeScriptCli: false },
  // A API Django usa rotas com barra final. Sem isto, o Next remove a barra,
  // Django a recoloca e o navegador entra em loop de redirecionamentos.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8007/api/:path*/" }];
  },
};

export default nextConfig;
