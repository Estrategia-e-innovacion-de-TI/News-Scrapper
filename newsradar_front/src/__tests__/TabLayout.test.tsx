/**
 * Unit tests for TabLayout component.
 *
 * Validates: Req 1.1 (3 tabs with correct labels),
 *            Req 1.3 (Riesgos active by default),
 *            Req 1.2 (clicking tab shows corresponding content)
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import TabLayout, { TABS, TAB_RIESGOS } from "@/components/layout/TabLayout";

describe("TabLayout", () => {
  it("renders 3 tabs with correct labels", () => {
    render(<TabLayout>{(tab) => <div>{tab}</div>}</TabLayout>);

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveTextContent("Riesgos");
    expect(tabs[1]).toHaveTextContent("Vigilancia Tecnológica");
    expect(tabs[2]).toHaveTextContent("Trend Mapping");
  });

  it('"Riesgos" tab is active by default (aria-selected="true")', () => {
    render(<TabLayout>{(tab) => <div>{tab}</div>}</TabLayout>);

    const riesgosTab = screen.getByRole("tab", { name: "Riesgos" });
    expect(riesgosTab).toHaveAttribute("aria-selected", "true");

    const otherTabs = screen
      .getAllByRole("tab")
      .filter((t) => t.textContent !== "Riesgos");
    otherTabs.forEach((t) => {
      expect(t).toHaveAttribute("aria-selected", "false");
    });
  });

  it("clicking a tab shows corresponding content", () => {
    render(
      <TabLayout>
        {(activeTab) => <div data-testid="content">Content: {activeTab}</div>}
      </TabLayout>
    );

    // Default content is riesgos
    expect(screen.getByTestId("content")).toHaveTextContent("Content: riesgos");

    // Click Vigilancia tab
    fireEvent.click(
      screen.getByRole("tab", { name: "Vigilancia Tecnológica" })
    );
    expect(screen.getByTestId("content")).toHaveTextContent(
      "Content: vigilancia"
    );

    // Click Trend Mapping tab
    fireEvent.click(screen.getByRole("tab", { name: "Trend Mapping" }));
    expect(screen.getByTestId("content")).toHaveTextContent(
      "Content: trendmap"
    );

    // Click back to Riesgos
    fireEvent.click(screen.getByRole("tab", { name: "Riesgos" }));
    expect(screen.getByTestId("content")).toHaveTextContent("Content: riesgos");
  });

  it("TABS constant has the expected structure", () => {
    expect(TABS).toHaveLength(3);
    expect(TABS[0]).toEqual({ id: "riesgos", label: "Riesgos" });
    expect(TABS[1]).toEqual({
      id: "vigilancia",
      label: "Vigilancia Tecnológica",
    });
    expect(TABS[2]).toEqual({ id: "trendmap", label: "Trend Mapping" });
  });

  it("default tab id is riesgos", () => {
    expect(TAB_RIESGOS).toBe("riesgos");
  });
});
