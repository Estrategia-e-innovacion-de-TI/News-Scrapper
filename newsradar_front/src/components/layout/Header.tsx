/**
 * Header — Banner section replicating the Framework_Innovacion header.
 *
 * Shows the full-width logo banner image.
 * Navigation tabs are handled by TabLayout, not here.
 *
 * Validates: Req 1.1 (header with logo banner)
 */
import React from "react";
import Link from "next/link";
import styles from "./Header.module.css";

export default function Header() {
  return (
    <header className={styles.header} data-testid="header">
      <div className={styles.brand}>
        <Link href="/" className={styles.brandLink}>
          <img
            src="/images/logo.png"
            alt="News Radar Banner"
            className={styles.bannerImg}
          />
        </Link>
      </div>
    </header>
  );
}
