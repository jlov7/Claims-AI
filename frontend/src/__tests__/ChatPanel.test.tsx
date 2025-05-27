import React from "react";
import { render, screen } from "@testing-library/react";
import ChatPanel from "../components/ChatPanel.tsx";
import { ChakraProvider } from "@chakra-ui/react";
import { describe, it, expect } from "vitest";

describe("ChatPanel", () => {
  it("renders input and send button", () => {
    render(
      <ChakraProvider>
        <ChatPanel />
      </ChakraProvider>,
    );
    const textarea = screen.getByPlaceholderText(
      /Ask a question about your documents.../i,
    );
    // @ts-ignore - jest-dom types
    expect(textarea).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /Send/i });
    // @ts-ignore - jest-dom types
    expect(button).toBeInTheDocument();
  });
});
