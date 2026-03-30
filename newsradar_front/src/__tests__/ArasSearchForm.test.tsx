/**
 * Unit tests for ArasSearchForm component.
 *
 * Validates: Req 2.1 (renders all required fields),
 *            Req 2.6 (loading indicator during request)
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ArasSearchForm from "@/components/riesgos/ArasSearchForm";

// Mock the api module
jest.mock("@/lib/api", () => ({
  searchAras: jest.fn(),
}));

import { searchAras } from "@/lib/api";

const mockSearchAras = searchAras as jest.MockedFunction<typeof searchAras>;

describe("ArasSearchForm", () => {
  const defaultProps = {
    onResults: jest.fn(),
    onError: jest.fn(),
    onLoadingChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders all required fields (company, NIT, risk category, date from, date to)", () => {
    render(<ArasSearchForm {...defaultProps} />);

    // Company field
    expect(screen.getByLabelText("Empresa")).toBeInTheDocument();

    // NIT field
    expect(screen.getByLabelText("NIT")).toBeInTheDocument();

    // Risk category select
    expect(screen.getByLabelText("Tipo de riesgo")).toBeInTheDocument();

    // Date from
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();

    // Date to
    expect(screen.getByLabelText("Hasta")).toBeInTheDocument();

    // Submit button
    expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
  });

  it("shows loading indicator during request", async () => {
    // Make searchAras return a promise that we control
    let resolveSearch: (value: any) => void;
    mockSearchAras.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSearch = resolve;
        })
    );

    render(<ArasSearchForm {...defaultProps} />);

    // Fill in a field so the form can submit
    fireEvent.change(screen.getByLabelText("Empresa"), {
      target: { value: "Test Corp" },
    });

    // Submit the form
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));

    // Button should show loading text and be disabled
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Buscando..." })
      ).toBeDisabled();
    });

    // onLoadingChange should have been called with true
    expect(defaultProps.onLoadingChange).toHaveBeenCalledWith(true);

    // Resolve the promise
    resolveSearch!({
      run_id: "test",
      total_documents: 0,
      total_classified: 0,
      results: [],
      excel_url: null,
    });

    // After resolution, button should return to normal
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar" })).not.toBeDisabled();
    });

    expect(defaultProps.onLoadingChange).toHaveBeenCalledWith(false);
  });
});
