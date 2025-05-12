import '@testing-library/jest-dom';

declare global {
  namespace Vi {
    interface JestAssertion {
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

// This file is a module and needs to have at least one export
export {}; 