/**
 * Property-based tests for form validation.
 *
 * Feature: newsradar-frontend
 * Uses fast-check for property-based testing with minimum 100 iterations.
 */
import React from "react";
import { render, screen, fireEvent, waitFor, cleanup, within } from "@testing-library/react";
import * as fc from "fast-check";
import RiesgosSearchForm from "@/components/riesgos/RiesgosSearchForm";
import SubscriptionForm from "@/components/vigilancia/SubscriptionForm";

// Mock the API module
jest.mock("@/lib/api", () => ({
  searchRiesgos: jest.fn(),
  fetchTopics: jest.fn().mockResolvedValue({
    topics: [
      { group_id: "ia_ml", display_name: "IA y ML", term_count: 24 },
      { group_id: "blockchain", display_name: "Blockchain", term_count: 18 },
      { group_id: "ciber", display_name: "Ciberseguridad", term_count: 32 },
    ],
  }),
  subscribe: jest.fn(),
}));

const api = require("@/lib/api");

// ── Property 7: Riesgos form rejects empty criteria ─────────────────
// Feature: newsradar-frontend, Property 7: Riesgos form rejects empty criteria
// Validates: Requirements 3.5

describe("P7: Riesgos form rejects empty criteria", () => {
  it("for any form state where both terms and preset are empty, submission shows validation message without API call", () => {
    fc.assert(
      fc.property(
        // Generate whitespace-only or empty strings for terms
        fc.stringOf(fc.constantFrom(" ", "\t", "\n", ""), { maxLength: 10 }),
        (emptyTerms) => {
          const onResults = jest.fn();
          const onError = jest.fn();
          const onLoadingChange = jest.fn();
          (api.searchRiesgos as jest.Mock).mockClear();
          cleanup();

          const { container, unmount } = render(
            <RiesgosSearchForm
              onResults={onResults}
              onError={onError}
              onLoadingChange={onLoadingChange}
            />
          );
          const view = within(container);

          // Set terms to whitespace/empty (preset is already empty by default)
          const termsInput = view.getByLabelText(/términos/i);
          fireEvent.change(termsInput, { target: { value: emptyTerms } });

          // Submit the form
          const submitButton = view.getByRole("button", { name: /buscar/i });
          fireEvent.click(submitButton);

          // Validation message should appear
          expect(view.getByRole("alert")).toHaveTextContent(
            /preset|términos|búsqueda/i
          );

          // API should NOT have been called
          expect(api.searchRiesgos).not.toHaveBeenCalled();

          unmount();
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ── Property 9: Subscription form rejects incomplete data ────────────
// Feature: newsradar-frontend, Property 9: Subscription form rejects incomplete data
// Validates: Requirements 4.5

describe("P9: Subscription form rejects incomplete data", () => {
  it("for any form state missing email, name, or topics, submission shows validation message", async () => {
    // We test 3 scenarios: missing email, missing name, missing topics
    const scenarios = fc.constantFrom<"no_email" | "no_name" | "no_topics">(
      "no_email",
      "no_name",
      "no_topics"
    );

    await fc.assert(
      fc.asyncProperty(scenarios, async (scenario) => {
        (api.subscribe as jest.Mock).mockClear();
        cleanup();

        const { container, unmount } = render(<SubscriptionForm />);
        const view = within(container);

        // Wait for topics to load
        await waitFor(() => {
          expect(view.getByText(/suscribirse/i)).toBeInTheDocument();
        });

        const emailInput = view.getByLabelText(/email/i);
        const nameInput = view.getByLabelText(/nombre/i);

        // Fill fields based on scenario
        if (scenario !== "no_email") {
          fireEvent.change(emailInput, { target: { value: "test@example.com" } });
        }
        if (scenario !== "no_name") {
          fireEvent.change(nameInput, { target: { value: "Test User" } });
        }
        if (scenario !== "no_topics") {
          // Select the first topic checkbox
          const checkboxes = view.getAllByRole("checkbox");
          if (checkboxes.length > 0) {
            fireEvent.click(checkboxes[0]);
          }
        }

        // Submit the form directly (bypasses HTML5 required validation in jsdom)
        const form = view.getByRole("form", { name: /suscripción/i });
        fireEvent.submit(form);

        // Validation error should appear
        await waitFor(() => {
          expect(view.getByTestId("subscription-error")).toBeInTheDocument();
        });

        // API should NOT have been called
        expect(api.subscribe).not.toHaveBeenCalled();

        unmount();
      }),
      { numRuns: 100 }
    );
  });
});
