// @ts-nocheck
import React from "react";
import { render, screen } from "@testing-library/react";
import FileUploader from "../components/FileUploader.tsx";
import { ChakraProvider } from "@chakra-ui/react";
import { describe, it, expect } from "vitest";

describe("FileUploader", () => {
  it("renders dropzone area", () => {
    render(
      <ChakraProvider>
        <FileUploader />
      </ChakraProvider>,
    );
    expect(
      screen.getByText(/Drag & drop files here, or click to select files/i),
    ).toBeInTheDocument();
  });

  it("does not show upload button when no files are selected", () => {
    render(
      <ChakraProvider>
        <FileUploader />
      </ChakraProvider>,
    );
    expect(
      screen.queryByRole("button", { name: /Upload Selected/i }),
    ).toBeNull();
  });
});
