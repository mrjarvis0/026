import type { Metadata } from "next";
import { Inter, Instrument_Serif } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const instrument = Instrument_Serif({
  variable: "--font-instrument",
  weight: "400",
  style: "italic",
  subsets: ["latin"],
});
const pixelCode = localFont({
  src: "../public/fonts/PixelCode.woff2",
  variable: "--font-pixelcode",
});

export const metadata: Metadata = {
  title: "026 — Intelligence Engine OS",
  description:
    "Operator console for the 026 fleet: evidence-grade agents, one shared brain, one execution gate.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${instrument.variable} ${pixelCode.variable} antialiased`}
    >
      <body className="min-h-svh overflow-x-clip">
        <div className="backdrop" aria-hidden />
        {children}
      </body>
    </html>
  );
}
