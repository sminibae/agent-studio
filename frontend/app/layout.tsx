import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";

import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Studio",
  description: "Build, test, and understand agent workflows.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <AppHeader />
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
