/**
 * Footer — Replicates the Framework_Innovacion footer structure.
 *
 * Dark background (#2c2a29) with white text, copyright info.
 *
 * Validates: Req 1.4 (footer consistent with Framework_Innovacion)
 */
import React from "react";
import styles from "./Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer} data-testid="footer">
      <p className={styles.copyright}>
        © 2026 News Radar — Innovación y Tecnología
      </p>
    </footer>
  );
}
