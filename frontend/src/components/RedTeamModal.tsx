import React, { useState, useMemo } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter, ModalBody, ModalCloseButton,
  Button, useDisclosure, Box, Text, Spinner, VStack, Heading, Alert, AlertIcon,
  Table, Thead, Tbody, Tr, Th, Td, TableContainer, Badge, Icon, HStack, useColorModeValue, SimpleGrid
} from '@chakra-ui/react';
import { runRedTeamEvaluation } from '../services/redteamService.ts';
import { RedTeamRunResult, RedTeamAttempt } from '../models/redteam.ts';

interface RedTeamModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const RedTeamModal: React.FC<RedTeamModalProps> = ({ isOpen, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [runResult, setRunResult] = useState<RedTeamRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const theadBg = useColorModeValue("gray.50", "gray.700");

  const handleRunEvaluation = async () => {
    setIsLoading(true);
    setError(null);
    setRunResult(null);
    try {
      const response = await runRedTeamEvaluation();
      setRunResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to run red team evaluation.');
    } finally {
      setIsLoading(false);
    }
  };

  const attempts = useMemo((): RedTeamAttempt[] => {
     if (!runResult) return [];
     return runResult.results || runResult.attempts || [];
  }, [runResult]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Red Team Evaluation</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            <Text>Run a set of adversarial prompts against the system to test its robustness and safety.</Text>
            <Button 
                onClick={handleRunEvaluation} 
                isLoading={isLoading} 
                colorScheme="red" 
                loadingText="Running Tests..."
                className="red-team-button"
                id="tour-red-team-modal-button"
                width="100%"
            >
              Run Evaluation
            </Button>
            {isLoading && (
                <VStack justify="center" align="center" py={5}>
                    <Spinner size="lg" />
                    <Text mt={2}>Running tests...</Text>
                </VStack>
            )}
            {error && (
              <Alert status="error">
                <AlertIcon />
                {error}
              </Alert>
            )}
            {runResult && (
              <Box mt={4}>
                <Heading size="sm" mb={2}>Summary Statistics:</Heading>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={1} mb={4} fontSize="sm">
                     {Object.entries(runResult.summary_stats).map(([key, value]) => {
                         const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                         return <Text key={key}><strong>{formattedKey}:</strong> {String(value)}</Text>;
                     })}
                 </SimpleGrid>

                <Heading size="sm" mb={2}>Detailed Attempts:</Heading>
                <TableContainer borderWidth="1px" borderRadius="md">
                  <Table variant="simple" size="sm">
                    <Thead bg={theadBg}>
                      <Tr>
                        <Th>Category</Th>
                        <Th>Prompt</Th>
                        <Th>Response</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {attempts.map((attempt: RedTeamAttempt, index) => {
                        return (
                          <Tr key={index}>
                            <Td><Badge variant="subtle">{attempt.category || 'General'}</Badge></Td>
                            <Td><Text noOfLines={2} title={attempt.prompt_text}>{attempt.prompt_text}</Text></Td>
                            <Td><Text noOfLines={2} title={attempt.response_text}>{attempt.response_text || 'N/A'}</Text></Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default RedTeamModal; 