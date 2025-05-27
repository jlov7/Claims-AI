// @ts-nocheck
import React from "react";
import { render, screen } from "@testing-library/react";
import StrategyNoteGenerator from "../components/StrategyNoteGenerator.tsx";
import { ChakraProvider } from "@chakra-ui/react";
import { describe, it, expect } from "vitest";

describe("StrategyNoteGenerator", () => {
  it("renders heading, criteria textarea, and generate button", () => {
    const mockDocumentIds = ["doc1.json", "doc2.json"];
    render(
      <ChakraProvider>
        <StrategyNoteGenerator documentIds={mockDocumentIds} />
      </ChakraProvider>,
    );
    // expect(screen.getByText(/^Strategy Note$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Optional Criteria:/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Generate & Download DOCX/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText(/e\.g\., StrategyNote_Claim123\.docx/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Generate Strategy Note \(DOCX\)/i),
    ).toBeInTheDocument();
  });
});
