// @ts-nocheck
import React from "react";
import { render, screen } from "@testing-library/react";
import SummarisePanel from "../components/SummarisePanel.tsx";
import { ChakraProvider } from "@chakra-ui/react";
import { describe, it, expect } from "vitest";

describe("SummarisePanel", () => {
  it("renders heading, input fields, and button", () => {
    render(
      <ChakraProvider>
        <SummarisePanel />
      </ChakraProvider>,
    );
    expect(screen.getByText(/Summarise Document/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/e\.g\., my_doc\.pdf\.json/i),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Or paste text to summarise/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Get Summary/i }),
    ).toBeInTheDocument();
  });
});
