import type { Metadata } from "next";
import "./globals.css";
import { NotificationsProvider } from "./components/notifications";
import { AuthProvider } from "./providers";

export const metadata: Metadata = {
  title: "RYV Expedientes",
  description: "Painel operacional para monitoramento de expedientes e prazos do PJe para Barros, Mariz & Rebouças Advogados.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: "/icon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning data-theme="light">
      <body>
        <AuthProvider><NotificationsProvider>{children}</NotificationsProvider></AuthProvider>
      </body>
    </html>
  );
}
