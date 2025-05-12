import React, { useState } from 'react';
import {
  Box,
  Heading,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Button,
  useToast,
  Spinner,
  Text,
  Divider,
} from '@chakra-ui/react';
import { summarise, SummariseRequest } from '../services/summariseService.js';

const SummarisePanel: React.FC = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [documentId, setDocumentId] = useState('');
  const [content, setContent] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const handleSummarise = async () => {
    setError(null);
    setSummary('');
    if (!documentId.trim() && !content.trim()) {
      setError('Please enter a Document ID or text to summarise.');
      return;
    }
    try {
      setLoading(true);
      if (isE2E) {
        setSummary('This is a dummy summary.');
      } else {
        const req: SummariseRequest = {
          document_id: documentId.trim() || undefined,
          content: content.trim() || undefined,
        };
        const resp = await summarise(req);
        setSummary(resp.summary);
      }
    } catch (e: any) {
      console.error('Summarise error:', e);
      toast({ title: 'Error summarising', description: e.message || 'Could not fetch summary.', status: 'error', duration: 5000, isClosable: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" w="100%">
      <Heading size="md" mb={4}>Summarise Document</Heading>
      <FormControl isInvalid={!!error} mb={3}>
        <FormLabel htmlFor="tour-summarise-id">Document ID</FormLabel>
        <Input
          id="tour-summarise-id"
          placeholder="e.g., my_doc.pdf.json"
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
          mb={2}
        />
        <FormLabel htmlFor="tour-summarise-content">Or paste text</FormLabel>
        <Textarea
          id="tour-summarise-content"
          placeholder="Or paste text to summarise"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
        />
        {error && <Text color="red.500" mt={1}>{error}</Text>}
      </FormControl>
      <Button id="tour-summarise-button" onClick={handleSummarise} colorScheme="blue" isLoading={loading} mb={4}>
        Get Summary
      </Button>
      {summary && (
        <Box id="tour-summarise-results" pt={2} borderTop="1px solid" borderColor="gray.200">
          <Text whiteSpace="pre-wrap">{summary}</Text>
        </Box>
      )}
    </Box>
  );
};

export default SummarisePanel; 