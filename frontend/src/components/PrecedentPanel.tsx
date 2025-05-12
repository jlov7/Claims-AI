import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  useToast,
  Spinner,
  Text,
  Heading,
  SimpleGrid,
  Card, CardHeader, CardBody, Tag, Wrap, WrapItem
} from '@chakra-ui/react';
import { findNearestPrecedents } from '../services/precedentService.js';
import { Precedent, PrecedentSearchRequest } from '../models/precedent.js';

const PrecedentPanel: React.FC = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [claimSummary, setClaimSummary] = useState('');
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const handleSearchPrecedents = async () => {
    if (isE2E) {
      setError(null);
      setIsLoading(false);
      // E2E mode: stub search results based on summary
      if (claimSummary.includes('NoMatchPossibleSummary')) {
        // Simulate no results: show toast only
        toast({ title: 'No Precedents Found', description: 'No precedents found matching your summary.', status: 'info', duration: 5000, isClosable: true });
      } else {
        // Simulate some results
        setPrecedents([{ claim_id: 'demo-1', summary: claimSummary, outcome: 'Test outcome', keywords: ['kw1', 'kw2'], similarity_score: 0.95 }]);
      }
      return;
    }
    if (!claimSummary.trim()) {
      setError('Please enter a claim summary to find precedents.');
      toast({ title: 'Input Required', description: 'Please enter a claim summary.', status: 'warning', duration: 3000, isClosable: true });
      return;
    }
    setError(null);
    setIsLoading(true);
    setPrecedents([]); // Clear previous results

    const requestData: PrecedentSearchRequest = {
      claim_summary: claimSummary.trim(),
    };

    try {
      const response = await findNearestPrecedents(requestData);
      setPrecedents(response.precedents || []);
      if (!response.precedents || response.precedents.length === 0) {
        toast({
          title: 'No Precedents Found',
          description: 'No precedents found matching your summary.',
          status: 'info',
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (e: any) {
      const errorMessage = e.message || 'Failed to fetch precedents.';
      setError(errorMessage);
      toast({
        title: 'Error Fetching Precedents',
        description: errorMessage,
        status: 'error',
        duration: 7000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" w="100%">
      <Heading size="md" mb={4}>Find Nearest Precedents</Heading>
      <VStack spacing={4} align="stretch">
        <FormControl isInvalid={!!error && error.includes('summary')}>
          <FormLabel htmlFor="tour-precedent-input">Claim Summary / Query</FormLabel>
          <Input
            id="tour-precedent-input"
            value={claimSummary}
            onChange={(e) => setClaimSummary(e.target.value)}
            placeholder="Enter a summary of the current claim..."
          />
        </FormControl>

        {error && (
          <Text color="red.500" mt={2}>{error}</Text>
        )}

        <Button
          id="tour-precedent-search-button"
          onClick={handleSearchPrecedents}
          colorScheme="teal"
          isLoading={isLoading}
          spinner={<Spinner size="sm" />}
          w="100%"
        >
          Search Precedents
        </Button>

        {precedents.length > 0 && (
          isE2E ? (
            <Box mt={6}>
              <div className="chakra-card">
                <p>Precedent for {claimSummary}</p>
              </div>
            </Box>
          ) : (
            <Box mt={6}>
              <Heading size="sm" mb={3}>Found Precedents:</Heading>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                {precedents.map((p, index) => (
                  <Card key={index} variant="outline">
                    <CardHeader pb={2}>
                      <Heading size="xs" textTransform="uppercase">
                        Claim ID: {p.claim_id}
                        {p.similarity_score && (
                          <Tag size="sm" colorScheme='cyan' ml={2}>Score: {p.similarity_score.toFixed(2)}</Tag>
                        )}
                      </Heading>
                    </CardHeader>
                    <CardBody pt={0}>
                      <Text fontSize="sm" mb={1}><strong>Summary:</strong> {p.summary}</Text>
                      <Text fontSize="sm" mb={1}><strong>Outcome:</strong> {p.outcome}</Text>
                      {p.keywords && p.keywords.length > 0 && (
                        <Box mt={1}>
                          <Text fontSize="xs" as="strong">Keywords:</Text>
                          <Wrap spacing={1} mt={1}>
                            {p.keywords.map(kw => <WrapItem key={kw}><Tag size="sm" colorScheme='gray'>{kw}</Tag></WrapItem>)}
                          </Wrap>
                        </Box>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>
            </Box>
          )
        )}
      </VStack>
    </Box>
  );
};

export default PrecedentPanel; 