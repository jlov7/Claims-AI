// @ts-nocheck
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import PrecedentPanel from '../components/PrecedentPanel.tsx';
import { Precedent } from '../models/precedent.ts';
import { describe, it, expect } from 'vitest';

describe('PrecedentPanel', () => {
  it('renders heading and handles loading state', () => {
    render(
      <ChakraProvider>
        <PrecedentPanel precedents={null} isLoading={true} error={null} />
      </ChakraProvider>
    );
    // Check for the updated heading
    expect(screen.getByText(/Nearest Precedents/i)).toBeInTheDocument();
    // Check for loading indicator
    expect(screen.getByText(/Finding similar precedents.../i)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument(); // No error alert
  });

  it('renders heading and handles error state', () => {
    render(
      <ChakraProvider>
        <PrecedentPanel precedents={null} isLoading={false} error="Failed to fetch" />
      </ChakraProvider>
    );
    expect(screen.getByText(/Nearest Precedents/i)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Failed to fetch');
    expect(screen.queryByText(/Finding similar precedents.../i)).not.toBeInTheDocument();
  });

  it('renders heading and displays precedents when provided', () => {
    const mockPrecedents: Precedent[] = [
      { claim_id: 'P1', summary: 'Summary 1', outcome: 'Outcome 1', keywords: ['kw1'], similarity_score: 0.9 },
      { claim_id: 'P2', summary: 'Summary 2', outcome: 'Outcome 2', keywords: ['kw2'], similarity_score: 0.8 },
    ];
    render(
      <ChakraProvider>
        <PrecedentPanel precedents={mockPrecedents} isLoading={false} error={null} />
      </ChakraProvider>
    );
    expect(screen.getByText(/Nearest Precedents/i)).toBeInTheDocument();
    expect(screen.getByText(/Precedent ID: P1/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Summary Snippet/i).length).toBe(mockPrecedents.length);
    expect(screen.getByText(/Summary 1/i)).toBeInTheDocument();
    expect(screen.getByText(/90.0%/i)).toBeInTheDocument(); // Check score badge
    expect(screen.getByText(/Precedent ID: P2/i)).toBeInTheDocument();
    expect(screen.getByText(/Summary 2/i)).toBeInTheDocument();
    expect(screen.getByText(/80.0%/i)).toBeInTheDocument(); // Check score badge
  });

  it('renders heading and handles no precedents found state', () => {
    render(
      <ChakraProvider>
        <PrecedentPanel precedents={[]} isLoading={false} error={null} />
      </ChakraProvider>
    );
    expect(screen.getByText(/Nearest Precedents/i)).toBeInTheDocument();
    expect(screen.getByText(/No relevant precedents found/i)).toBeInTheDocument();
  });

}); 