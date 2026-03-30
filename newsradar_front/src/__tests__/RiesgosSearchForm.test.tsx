/**
 * Unit tests for RiesgosSearchForm component.
 *
 * Validates: Req 3.1, 3.2 (renders all 5 presets correctly)
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import RiesgosSearchForm, {
  PRESETS,
} from "@/components/riesgos/RiesgosSearchForm";

// Mock the api module
jest.mock("@/lib/api", () => ({
  searchRiesgos: jest.fn(),
}));

describe("RiesgosSearchForm", () => {
  const defaultProps = {
    onResults: jest.fn(),
    onError: jest.fn(),
    onLoadingChange: jest.fn(),
  };

  it("renders all 5 presets correctly in the select dropdown", () => {
    render(<RiesgosSearchForm {...defaultProps} />);

    const select = screen.getByLabelText("Preset");
    expect(select).toBeInTheDocument();

    // The select should have 6 options (1 empty + 5 presets)
    const options = select.querySelectorAll("option");
    expect(options).toHaveLength(6);

    // Check the 5 actual presets (excluding the empty "— Sin preset —")
    expect(options[1]).toHaveTextContent("Cibernético");
    expect(options[2]).toHaveTextContent("Fraude");
    expect(options[3]).toHaveTextContent("Operacional");
    expect(options[4]).toHaveTextContent("Ambiental / Social");
    expect(options[5]).toHaveTextContent("Todos");
  });

  it("PRESETS constant is exported and contains the expected entries", () => {
    // Verify the PRESETS constant structure
    expect(PRESETS).toHaveLength(6); // includes the empty option

    const presetLabels = PRESETS.map((p) => p.label);
    expect(presetLabels).toContain("Cibernético");
    expect(presetLabels).toContain("Fraude");
    expect(presetLabels).toContain("Operacional");
    expect(presetLabels).toContain("Ambiental / Social");
    expect(presetLabels).toContain("Todos");
  });

  it("renders terms input and date fields", () => {
    render(<RiesgosSearchForm {...defaultProps} />);

    expect(
      screen.getByLabelText("Términos (separados por coma)")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
    expect(screen.getByLabelText("Hasta")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
  });
});
