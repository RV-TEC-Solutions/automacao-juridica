import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./providers";

export const metadata: Metadata = {
  title: "Automação de Expedientes",
  description: "Painel operacional para acompanhar expedientes e prazos do PJe.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="pt-BR" suppressHydrationWarning data-theme="light"><body className="min-h-full font-[family-name:var(--font-sans)] antialiased"><AuthProvider>{children}</AuthProvider></body></html>;
}
