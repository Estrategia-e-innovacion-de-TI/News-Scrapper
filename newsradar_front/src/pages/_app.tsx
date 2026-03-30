/**
 * Custom App — wraps all pages with the shared Layout (Header + Footer).
 *
 * Validates: Req 1.2 (all pages wrapped with header/content/footer layout)
 */
import type { AppProps } from "next/app";
import Layout from "@/components/layout/Layout";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}
