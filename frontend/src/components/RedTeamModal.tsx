import React, { useMemo, useState } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton,
  Button, useDisclosure, Text, Spinner, VStack, Box, Heading, Accordion, AccordionItem,
  AccordionButton, AccordionPanel, AccordionIcon, Tag, Code, useToast,
  Table, Thead, Tbody, Tr, Th, Td, TableContainer, SimpleGrid,
} from '@chakra-ui/react';
import { runRedTeamEvaluation } from '../services/redteamService.js';
import { RedTeamRunResult, RedTeamAttempt, SummaryStats } from '../models/redteam.js';

interface RedTeamModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const RedTeamModal: React.FC<RedTeamModalProps> = ({ isOpen, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [runResult, setRunResult] = useState<RedTeamRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const handleRunEvaluation = async () => {
    setIsLoading(true);
    setError(null);
    setRunResult(null);
    try {
      const evalResults = await runRedTeamEvaluation();
      setRunResult(evalResults);
      toast({ title: "Red Team Evaluation Complete", status: "success", duration: 3000 });
    } catch (e: any) {
      const errorMessage = e.message || "Failed to run Red Team evaluation.";
      setError(errorMessage);
      toast({ title: "Red Team Error", description: errorMessage, status: "error", duration: 5000 });
    } finally {
      setIsLoading(false);
    }
  };

  // Clear results when modal is closed, so it's fresh next time
  const handleModalClose = () => {
    setRunResult(null);
    setError(null);
    onClose();
  };

  const attempts: RedTeamAttempt[] = useMemo(() => {
    if (!runResult) return [];
    // Access an array of attempts regardless of whether the key is 'results' or 'attempts'
    const actualAttempts = runResult.results || runResult.attempts || [];
    if (Array.isArray(actualAttempts)) return actualAttempts;
    return [];
  }, [runResult]);

  return (
    <Modal isOpen={isOpen} onClose={handleModalClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Red Team Evaluation</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            <Button onClick={handleRunEvaluation} isLoading={isLoading} colorScheme="orange" loadingText="Running Evaluation...">
              Run Full Red Team Evaluation
            </Button>
            {isLoading && <Spinner alignSelf="center" />}
            {error && <Text color="red.500">Error: {error}</Text>}
            
            {runResult && (
              <Box mt={4}>
                <Heading size="md" mb={2}>Summary Statistics</Heading>
                <SimpleGrid columns={{base: 1, md: 2}} spacing={2} mb={4}>
                    {Object.entries(runResult.summary_stats).map(([key, value]) => {
                        const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        return <Text key={key}><strong>{formattedKey}:</strong> {String(value)}</Text>;
                    })}
                </SimpleGrid>

                <Heading size="md" mb={2} mt={6}>Detailed Attempts</Heading>
                {attempts.length > 0 ? (
                  <Accordion allowMultiple defaultIndex={[]}>
                    {attempts.map((attempt, idx) => (
                      <AccordionItem key={idx}>
                        <h2>
                          <AccordionButton _expanded={{ bg: 'gray.100' }}>
                            <Box flex="1" textAlign="left">
                              <strong>{attempt.category}</strong>&nbsp;&mdash;&nbsp;
                              {attempt.prompt_text.slice(0, 60)}...
                            </Box>
                            <AccordionIcon />
                          </AccordionButton>
                        </h2>
                        <AccordionPanel pb={4}>
                          <VStack spacing={3} align="stretch">
                            <Box>
                              <Text as="strong">Prompt Category:</Text> <Tag>{attempt.category}</Tag>
                            </Box>
                            <Box>
                              <Text as="strong">Full Prompt:</Text>
                              <Text whiteSpace="pre-wrap" fontFamily="monospace" fontSize="sm" p={2} borderWidth="1px" borderRadius="md" bg="gray.50">{attempt.prompt_text}</Text>
                            </Box>
                            <Box>
                              <Text as="strong">AI Response:</Text>
                              <Text whiteSpace="pre-wrap" fontFamily="monospace" fontSize="sm" p={2} borderWidth="1px" borderRadius="md" bg="gray.50">{attempt.response_text}</Text>
                            </Box>
                            {attempt.evaluation_notes && (
                              <Text mt={2} fontStyle="italic" color="gray.600">
                                Notes: {attempt.evaluation_notes}
                              </Text>
                            )}
                          </VStack>
                        </AccordionPanel>
                      </AccordionItem>
                    ))}
                  </Accordion>
                ) : <Text>No attempts to display.</Text>}
              </Box>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button onClick={handleModalClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Helper function to map confidence score to color - can be extracted if used elsewhere
const getConfidenceColor = (confidence: number | undefined): string => {
    if (confidence === undefined) return 'gray';
    if (confidence >= 4) return 'green';
    if (confidence === 3) return 'yellow';
    return 'red';
  };

export default RedTeamModal; 