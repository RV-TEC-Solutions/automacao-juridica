import type { Metadata } from "next";
import "./globals.css";
import { NotificationsProvider } from "./components/notifications";
import { AuthProvider } from "./providers";

export const metadata: Metadata = {
  title: "Céleri Comunicações",
  description: "Ambiente de demonstração com dados fictícios para monitoramento de expedientes e prazos.",
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
