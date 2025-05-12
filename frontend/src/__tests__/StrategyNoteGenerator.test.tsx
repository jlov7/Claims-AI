// @ts-nocheck
import React from 'react';
import { render, screen } from '@testing-library/react';
import StrategyNoteGenerator from '../components/StrategyNoteGenerator.tsx';
import { ChakraProvider } from '@chakra-ui/react';
import { describe, it, expect } from 'vitest';

describe('StrategyNoteGenerator', () => {
  it('renders heading, filename input, and download button', () => {
    render(
      <ChakraProvider>
        <StrategyNoteGenerator />
      </ChakraProvider>
    );
    expect(screen.getByText(/Generate Claim Strategy Note/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\., StrategyNote_Claim123\.docx/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Download Strategy Note/i })).toBeInTheDocument();
  });
}); 