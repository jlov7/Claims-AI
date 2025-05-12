import React, { useState } from 'react';
import {
  Card,
  CardHeader,
  CardBody,
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
  Tooltip,
  SkeletonText,
} from '@chakra-ui/react';
import { summarise, SummariseRequest } from '../services/summariseService.ts';
import ReactMarkdown from 'react-markdown';

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
    <Card shadow="md" borderWidth="2px" borderRadius="lg" w="100%" className="tour-highlightable" bg="white">
      <CardHeader>
        <Heading size="lg">Summarise Document</Heading>
      </CardHeader>
      <CardBody p={6}>
        <Text fontSize="md" color="gray.600" mb={4}>
          Get a quick AI-generated summary by document ID or pasted text.
        </Text>
        <FormControl isInvalid={!!error} mb={4}>
          <FormLabel htmlFor="tour-summarise-id" fontSize="md">Document ID</FormLabel>
          <Tooltip label="Enter the ID of an already uploaded and processed document (e.g., the .json filename)." placement="top-start" hasArrow>
            <Input
              id="tour-summarise-id"
              placeholder="e.g., my_doc.pdf.json"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              mb={3}
              size="lg"
              borderRadius="md"
              borderWidth="2px"
              borderColor="blue.300"
              bg="gray.50"
              fontSize="lg"
              p={4}
              _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 2px #3182ce' }}
            />
          </Tooltip>
          <FormLabel htmlFor="tour-summarise-content" fontSize="md">Or paste text</FormLabel>
          <Tooltip label="Alternatively, paste the raw text content you want to summarise directly here." placement="top-start" hasArrow>
            <Textarea
              id="tour-summarise-content"
              placeholder="Or paste text to summarise"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              size="lg"
              borderRadius="md"
              borderWidth="2px"
              borderColor="blue.300"
              bg="gray.50"
              fontSize="lg"
              p={4}
              _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 2px #3182ce' }}
            />
          </Tooltip>
          {error && <Text color="red.500" mt={2} fontSize="md">{error}</Text>}
        </FormControl>
        <Tooltip label="Click to generate a summary using the AI based on the provided Document ID or text." placement="bottom" hasArrow>
          <Button id="tour-summarise-button" onClick={handleSummarise} colorScheme="blue" isLoading={loading} mb={6} size="lg" px={8} py={6} fontSize="xl" borderRadius="md">
            Get Summary
          </Button>
        </Tooltip>
        {loading ? (
          <SkeletonText data-testid="summary-skeleton" mt={4} noOfLines={4} spacing="4" skeletonHeight="2" />
        ) : summary && (
          <Box 
            id="tour-summarise-results" 
            pt={4} 
            borderTop="2px solid" 
            borderColor="blue.200"
            sx={{ whiteSpace: 'pre-wrap' }}
            fontSize="lg"
          >
            <ReactMarkdown>{summary}</ReactMarkdown>
          </Box>
        )}
      </CardBody>
    </Card>
  );
};

export default SummarisePanel; 