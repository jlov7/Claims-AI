import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  VStack,
  Box,
  Heading,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  Divider,
  useToast
} from '@chakra-ui/react';
import { runRedTeamEvaluation } from '../services/redteamService.ts';

interface RedTeamModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SummaryStats {
  prompts_run?: number;
  categories_tested?: number;
  // Add other summary stats properties as needed
}

interface RedTeamAttempt {
  category?: string;
  prompt?: string;
  response?: string;
  risk_level?: string;
  score?: number;
}

interface RedTeamResponse {
  results: RedTeamAttempt[];
  summary_stats: SummaryStats;
}

const RedTeamModal: React.FC<RedTeamModalProps> = ({ isOpen, onClose }) => {
  const [results, setResults] = useState<RedTeamAttempt[]>([]);
  const [summary, setSummary] = useState<SummaryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const executeRedTeamEvaluation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response: RedTeamResponse = await runRedTeamEvaluation();
      setResults(response.results || []);
      setSummary(response.summary_stats || {});
      toast({
        title: "Red Team Evaluation Complete",
        description: `Ran ${response.summary_stats?.prompts_run || 0} prompts across ${response.summary_stats?.categories_tested || 0} categories`,
        status: "success",
        duration: 5000,
        isClosable: true
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to run red team evaluation";
      setError(errorMsg);
      toast({
        title: "Evaluation Failed",
        description: errorMsg,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }

  // Clear results when modal is closed
  useEffect(() => {
    if (!isOpen) {
      // Keep results and summary in place for now
    }
  }, [isOpen]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent maxW="900px">
        <ModalHeader>Red Team Evaluation</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing={4}>
            <Text>
              Red Team evaluation tests the AI's robustness against various adversarial prompts, 
              including attempts to override instructions, extract sensitive information, or provide harmful content.
            </Text>
            
            <Box py={2}>
              <Button 
                colorScheme="orange" 
                onClick={executeRedTeamEvaluation} 
                isLoading={loading}
                loadingText="Running Evaluation"
                mb={4}
                width="100%"
              >
                Run New Evaluation
              </Button>
            </Box>
            
            {error && (
              <Alert status="error">
                <AlertIcon />
                {error}
              </Alert>
            )}
            
            {summary && (
              <Box borderWidth="1px" borderRadius="lg" p={4} bg="gray.50">
                <Heading size="md" mb={2}>Summary</Heading>
                <Text>Prompts Run: {summary.prompts_run}</Text>
                <Text>Categories Tested: {summary.categories_tested}</Text>
                {summary.successful_executions !== undefined && (
                  <Text>Successful Executions: {summary.successful_executions}</Text>
                )}
                {summary.failed_executions !== undefined && (
                  <Text>Failed Executions: {summary.failed_executions}</Text>
                )}
              </Box>
            )}
            
            {results.length > 0 && (
              <>
                <Heading size="md" mt={2}>Results</Heading>
                <Accordion allowMultiple defaultIndex={[]}>
                  {results.map((attempt, index) => (
                    <AccordionItem key={index}>
                      <h2>
                        <AccordionButton>
                          <Box flex="1" textAlign="left">
                            <Text fontWeight="bold">
                              {attempt.prompt_id}: {attempt.category}
                            </Text>
                          </Box>
                          <AccordionIcon />
                        </AccordionButton>
                      </h2>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={3}>
                          <Box>
                            <Text fontWeight="bold">Prompt:</Text>
                            <Text>{attempt.prompt_text}</Text>
                          </Box>
                          <Divider />
                          <Box>
                            <Text fontWeight="bold">Response:</Text>
                            <Text whiteSpace="pre-wrap">{attempt.response_text}</Text>
                          </Box>
                          {attempt.evaluation_notes && (
                            <>
                              <Divider />
                              <Box>
                                <Text fontWeight="bold">Evaluation Notes:</Text>
                                <Text>{attempt.evaluation_notes}</Text>
                              </Box>
                            </>
                          )}
                        </VStack>
                      </AccordionPanel>
                    </AccordionItem>
                  ))}
                </Accordion>
              </>
            )}
            
            {loading && (
              <Box textAlign="center" py={10}>
                <Spinner size="xl" />
                <Text mt={4}>Running Red Team evaluation against the AI system...</Text>
              </Box>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button colorScheme="blue" mr={3} onClick={onClose}>
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default RedTeamModal; 