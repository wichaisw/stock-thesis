import type { Metadata } from "next";
import { Noto_Sans_Thai } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const notoSansThai = Noto_Sans_Thai({ variable: "--font-thai", subsets: ["thai", "latin"] });

export const metadata: Metadata = {
  title: "Value stock shortlist",
  description: "หุ้น SET พื้นฐานดี ราคาต่ำกว่า fair value และ CDC ใกล้ cross",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" className={`${notoSansThai.variable} h-full antialiased`}>
      <body className="min-h-full">
        <header className="border-b border-zinc-200 dark:border-zinc-800">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <Link href="/" className="text-lg font-semibold">
              Value stock shortlist
            </Link>
            <form action="/search" className="flex gap-2">
              <label htmlFor="q" className="sr-only">
                ค้นหา symbol
              </label>
              <input
                id="q"
                name="q"
                required
                placeholder="ค้นหา symbol เช่น PTT"
                className="w-56 rounded-md border border-zinc-300 bg-transparent px-3 py-1.5 uppercase placeholder:normal-case dark:border-zinc-700"
              />
              <button className="rounded-md border border-zinc-300 px-3 py-1.5 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800">
                ค้นหา
              </button>
            </form>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
