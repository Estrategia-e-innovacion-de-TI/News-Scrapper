/**
 * Unit tests for SubscriptionForm component.
 *
 * Validates: Req 4.1 (loads topics on mount),
 *            Req 4.2 (shows topic checkboxes after loading)
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import SubscriptionForm from "@/components/vigilancia/SubscriptionForm";

// Mock the api module
jest.mock("@/lib/api", () => ({
  fetchTopics: jest.fn(),
  subscribe: jest.fn(),
}));

import { fetchTopics } from "@/lib/api";

const mockFetchTopics = fetchTopics as jest.MockedFunction<typeof fetchTopics>;

const mockTopics = {
  topics: [
    { group_id: "ia_ml", display_name: "IA y Machine Learning", term_count: 24 },
    { group_id: "blockchain", display_name: "Blockchain", term_count: 18 },
    { group_id: "ciberseguridad", display_name: "Ciberseguridad", term_count: 32 },
  ],
};

describe("SubscriptionForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("loads topics on mount and shows loading state", async () => {
    let resolveTopics: (value: any) => void;
    mockFetchTopics.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveTopics = resolve;
        })
    );

    render(<SubscriptionForm />);

    // Should show loading text while fetching
    expect(screen.getByText("Cargando temas...")).toBeInTheDocument();

    // fetchTopics should have been called
    expect(mockFetchTopics).toHaveBeenCalledTimes(1);

    // Resolve the promise
    resolveTopics!(mockTopics);

    // After loading, checkboxes should appear
    await waitFor(() => {
      expect(screen.queryByText("Cargando temas...")).not.toBeInTheDocument();
    });
  });

  it("shows topic checkboxes after loading", async () => {
    mockFetchTopics.mockResolvedValue(mockTopics);

    render(<SubscriptionForm />);

    // Wait for topics to load
    await waitFor(() => {
      expect(screen.queryByText("Cargando temas...")).not.toBeInTheDocument();
    });

    // Each topic should have a checkbox with its display_name as aria-label
    for (const topic of mockTopics.topics) {
      const checkbox = screen.getByRole("checkbox", {
        name: topic.display_name,
      });
      expect(checkbox).toBeInTheDocument();
      expect(checkbox).not.toBeChecked();
    }

    // Verify the term count is displayed
    expect(screen.getByText(/24 términos/)).toBeInTheDocument();
    expect(screen.getByText(/18 términos/)).toBeInTheDocument();
    expect(screen.getByText(/32 términos/)).toBeInTheDocument();
  });
});
