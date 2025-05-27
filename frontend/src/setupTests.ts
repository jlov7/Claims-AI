import "@testing-library/jest-dom";

// Explicitly declare types for the jest-dom extensions
declare global {
  namespace Vi {
    interface Assertion {
      toBeInTheDocument(): void;
      toBeVisible(): void;
      toHaveTextContent(text: string): void;
      toHaveClass(className: string): void;
      toHaveAttribute(attr: string, value?: string): void;
      toBeDisabled(): void;
      toBeEnabled(): void;
      toBeChecked(): void;
      toHaveValue(value: string | string[] | number | null): void;
    }
  }
}

// Stub scrollIntoView since jsdom does not implement it
window.HTMLElement.prototype.scrollIntoView = function () {};

/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
