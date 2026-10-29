import type { Metadata } from "next";
import "./globals.css";

// System fonts only: the demo must build and run with no internet (plan §3.3)

export const metadata: Metadata = {
  title: "Field Shift",
  description: "Climate-shift-aware crop rotation planning with NASA data",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
