import type { ReactNode } from "react";

import AppNavigation from "../components/AppNavigation";

import "./globals.css";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppNavigation />
        {children}
      </body>
    </html>
  );
}
