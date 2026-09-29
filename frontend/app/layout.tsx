import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./providers";

export const metadata: Metadata = {
  title: "Automação de Expedientes · Barros, Mariz & Rebouças Advogados",
  description: "Painel operacional para monitoramento de expedientes e prazos do PJe para Barros, Mariz & Rebouças Advogados.",
  icons: {
    icon: "/brand/logo-mark-light@2x.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning data-theme="light">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
