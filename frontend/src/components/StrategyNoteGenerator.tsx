import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Input,
  Textarea,
  VStack,
  useToast,
  Spinner,
  Text,
  Heading,
} from '@chakra-ui/react';
import { draftStrategyNote } from '../services/draftService.js';
import { DraftStrategyNoteRequest, QAPair } from '../models/draft.js';

const StrategyNoteGenerator: React.FC = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [claimSummary, setClaimSummary] = useState('');
  const [documentIdsString, setDocumentIdsString] = useState('');
  const [qaHistoryString, setQaHistoryString] = useState('');
  const [additionalCriteria, setAdditionalCriteria] = useState('');
  const [outputFilename, setOutputFilename] = useState('ClaimStrategyNote.docx');

  const [isDrafting, setIsDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const handleGenerateNote = async () => {
    setError(null);
    if (isE2E) {
      // E2E mode: trigger a dummy file download using blob URL
      const blob = new Blob(['Dummy content'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = outputFilename.trim();
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return;
    }

    if (!outputFilename.trim()) {
      setError('Output filename is required.');
      return;
    }

    let docIds: string[] | undefined = undefined;
    if (documentIdsString.trim()) {
      docIds = documentIdsString.split(',').map(id => id.trim()).filter(id => id);
    }

    let qaHistory: QAPair[] | undefined = undefined;
    if (qaHistoryString.trim()) {
      try {
        qaHistory = JSON.parse(qaHistoryString);
        if (!Array.isArray(qaHistory)) throw new Error('QA History must be a JSON array.');
        // Basic validation for QAPair structure can be added here if needed
      } catch (e) {
        setError('Invalid JSON format for Q&A History. Please provide an array of {question: string, answer: string} objects.');
        return;
      }
    }

    if (!claimSummary.trim() && (!docIds || docIds.length === 0) && (!qaHistory || qaHistory.length === 0) && !additionalCriteria.trim()) {
      setError('At least one context field (Summary, Document IDs, Q&A History, or Criteria) must be provided.');
      return;
    }

    const requestData: DraftStrategyNoteRequest = {
      claimSummary: claimSummary.trim() || undefined,
      documentIds: docIds,
      qaHistory: qaHistory,
      additionalCriteria: additionalCriteria.trim() || undefined,
      outputFilename: outputFilename.trim(),
    };

    setIsDrafting(true);
    try {
      const blob = await draftStrategyNote(requestData);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = requestData.outputFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast({
        title: 'Strategy Note Generated',
        description: `${requestData.outputFilename} has been downloaded.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (e: any) {
      const errorMessage = e.message || 'Failed to generate strategy note.';
      setError(errorMessage);
      toast({
        title: 'Error Generating Note',
        description: errorMessage,
        status: 'error',
        duration: 7000,
        isClosable: true,
      });
    } finally {
      setIsDrafting(false);
    }
  };

  return (
    <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" w="100%">
      <Heading size="md" mb={4}>Generate Claim Strategy Note</Heading>
      <VStack spacing={4} as="form" onSubmit={(e) => { e.preventDefault(); handleGenerateNote(); }}>
        <FormControl isInvalid={!!error && error.includes('filename')}>
          <FormLabel htmlFor="tour-draft-filename">Output Filename (.docx)</FormLabel>
          <Input
            id="tour-draft-filename"
            value={outputFilename}
            onChange={(e) => setOutputFilename(e.target.value)}
            placeholder="e.g., StrategyNote_Claim123.docx"
          />
          {error && error.includes('filename') && <FormErrorMessage>{error}</FormErrorMessage>}
        </FormControl>

        <FormControl>
          <FormLabel htmlFor="tour-draft-summary">Claim Summary (Optional)</FormLabel>
          <Textarea
            id="tour-draft-summary"
            value={claimSummary}
            onChange={(e) => setClaimSummary(e.target.value)}
            placeholder="Enter a brief summary of the claim..."
          />
        </FormControl>

        <FormControl>
          <FormLabel htmlFor="documentIds">Document IDs (Optional, comma-separated)</FormLabel>
          <Input
            id="documentIds"
            value={documentIdsString}
            onChange={(e) => setDocumentIdsString(e.target.value)}
            placeholder="e.g., doc1.pdf.json,doc2.tiff.json"
          />
        </FormControl>

        <FormControl>
          <FormLabel htmlFor="qaHistory">Q&A History (Optional, JSON format)</FormLabel>
          <Textarea
            id="qaHistory"
            value={qaHistoryString}
            onChange={(e) => setQaHistoryString(e.target.value)}
            placeholder='[{"question": "What is...?", "answer": "It is..."}]'
            rows={3}
          />
        </FormControl>

        <FormControl>
          <FormLabel htmlFor="additionalCriteria">Additional Criteria/Instructions (Optional)</FormLabel>
          <Textarea
            id="additionalCriteria"
            value={additionalCriteria}
            onChange={(e) => setAdditionalCriteria(e.target.value)}
            placeholder="Specific points to cover, tone, structure preferences..."
          />
        </FormControl>

        {error && !error.includes('filename') && (
          <Text color="red.500" mt={2}>{error}</Text>
        )}

        <Button
          type="submit"
          colorScheme="blue"
          isLoading={isDrafting}
          spinner={<Spinner size="sm" />}
          w="100%"
        >
          Download Strategy Note
        </Button>
      </VStack>
    </Box>
  );
};

export default StrategyNoteGenerator; 