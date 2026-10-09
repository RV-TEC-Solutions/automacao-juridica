import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Permite o HMR ao acessar o servidor de desenvolvimento pela rede do escritório.
  allowedDevOrigins: ["192.168.10.77"],
  experimental: { useTypeScriptCli: false },
  output: "standalone",
  // A API Django usa rotas com barra final. Sem isto, o Next remove a barra,
  // Django a recoloca e o navegador entra em loop de redirecionamentos.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8007";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*/` }];
  },
};


export default nextConfig;
