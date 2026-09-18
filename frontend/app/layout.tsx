import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./providers";

export const metadata: Metadata = {
  title: "Painel de Expedientes",
  description: "Acompanhe novidades e prazos dos seus expedientes do PJe.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      suppressHydrationWarning
      data-theme="light"
      className="h-full antialiased"
    >
      <body className="flex min-h-full flex-col bg-bg text-text max-[760px]:pb-[62px]"><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
