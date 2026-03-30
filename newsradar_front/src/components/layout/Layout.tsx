/**
 * Layout — Wraps all pages with Header → main content → Footer.
 *
 * Replicates the Framework_Innovacion layout pattern:
 * min-h-screen flex flex-col with sticky footer.
 *
 * Validates: Req 1.2 (header/content/footer layout)
 */
import React from "react";
import Header from "./Header";
import Footer from "./Footer";
import styles from "./Layout.module.css";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className={styles.layout} data-testid="layout">
      <Header />
      <main className={styles.main}>{children}</main>
      <Footer />
    </div>
  );
}
