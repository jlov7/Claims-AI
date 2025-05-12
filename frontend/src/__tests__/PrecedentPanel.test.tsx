// @ts-nocheck
import React from 'react';
import { render, screen } from '@testing-library/react';
import PrecedentPanel from '../components/PrecedentPanel.tsx';
import { ChakraProvider } from '@chakra-ui/react';
import { describe, it, expect } from 'vitest';

describe('PrecedentPanel', () => {
  it('renders heading, input field, and search button', () => {
    render(
      <ChakraProvider>
        <PrecedentPanel />
      </ChakraProvider>
    );
    expect(screen.getByText(/Find Nearest Precedents/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter a summary of the current claim/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Search Precedents/i })).toBeInTheDocument();
  });
}); 