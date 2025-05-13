import React, { useState, useEffect } from 'react';
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
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SkeletonText,
  Select,
} from '@chakra-ui/react';
import { summarise, SummariseRequest } from '../services/summariseService.ts';
import ReactMarkdown from 'react-markdown';
import { useUpload } from '../context/UploadContext.tsx';

const SummarisePanel: React.FC = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [documentId, setDocumentId] = useState('');
  const [content, setContent] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const toast = useToast();
  const { recentUploads } = useUpload();
  
  // Auto-select the most recently uploaded document and switch to document tab
  useEffect(() => {
    if (recentUploads.length > 0) {
      console.log("Auto-selecting document:", recentUploads[0]);
      setDocumentId(recentUploads[0].id);
      setActiveTab(0); // Switch to document tab
    }
  }, [recentUploads]);

  // Clear errors when changing inputs
  useEffect(() => {
    if (error) {
      setError(null);
    }
  }, [documentId, content, activeTab]);

  const handleSummarise = async () => {
    // Reset states
    setSummary('');
    setError(null);
    
    // Validation based on active tab
    if (activeTab === 0 && !documentId.trim()) {
      setError('Please select or enter a document ID.');
      return;
    }
    
    if (activeTab === 1 && !content.trim()) {
      setError('Please enter text to summarise.');
      return;
    }

    try {
      setLoading(true);
      if (isE2E) {
        setSummary('This is a dummy summary.');
      } else {
        // We now pass the documentId as-is to the backend
        // This is because our backend has been updated to handle all possible ID formats
        // including with or without extensions
        const req: SummariseRequest = activeTab === 0
          ? { document_id: documentId.trim() }  // Pass the document ID as stored in the context
          : { content: content.trim() };        // Or pass the content for direct summarization
        
        console.log("Sending summarize request with:", req);
        const resp = await summarise(req);
        setSummary(resp.summary);
      }
    } catch (e: any) {
      console.error('Summarise error:', e);
      setError(e.message || 'Could not fetch summary.');
      toast({ 
        title: 'Error summarising', 
        description: e.message || 'Could not fetch summary.', 
        status: 'error', 
        duration: 5000, 
        isClosable: true 
      });
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
          <Tabs variant="enclosed" colorScheme="blue" index={activeTab} onChange={setActiveTab}>
            <TabList>
              <Tab>Use Document ID</Tab>
              <Tab>Paste Text</Tab>
            </TabList>
            <TabPanels>
              <TabPanel>
                {recentUploads.length > 0 ? (
                  <>
                    <FormLabel htmlFor="document-select" fontSize="md">Select a document</FormLabel>
                    <Select
                      id="document-select"
                      value={documentId}
                      onChange={(e) => setDocumentId(e.target.value)}
                      mb={3}
                      size="lg"
                      borderRadius="md"
                      borderWidth="2px"
                      borderColor={documentId.trim() ? "green.300" : "blue.300"}
                      bg={documentId.trim() ? "green.50" : "gray.50"}
                      fontSize="lg"
                      p={2}
                      _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 2px #3182ce' }}
                    >
                      <option value="">-- Select a document --</option>
                      {recentUploads.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.filename} - {doc.id}
                        </option>
                      ))}
                    </Select>
                  </>
                ) : null}
                
                <FormLabel htmlFor="tour-summarise-id" fontSize="md">Document ID</FormLabel>
                <Input
                  id="tour-summarise-id"
                  placeholder="e.g., my_doc.pdf.json"
                  value={documentId}
                  onChange={(e) => setDocumentId(e.target.value)}
                  mb={3}
                  size="lg"
                  borderRadius="md"
                  borderWidth="2px"
                  borderColor={documentId.trim() ? "green.300" : "blue.300"}
                  bg={documentId.trim() ? "green.50" : "gray.50"}
                  fontSize="lg"
                  p={4}
                  _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 2px #3182ce' }}
                />
              </TabPanel>
              <TabPanel>
                <FormLabel htmlFor="tour-summarise-content" fontSize="md">Paste text</FormLabel>
                <Textarea
                  id="tour-summarise-content"
                  placeholder="Paste text to summarise"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={4}
                  size="lg"
                  borderRadius="md"
                  borderWidth="2px"
                  borderColor={content.trim() ? "green.300" : "blue.300"}
                  bg={content.trim() ? "green.50" : "gray.50"}
                  fontSize="lg"
                  p={4}
                  _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 2px #3182ce' }}
                />
              </TabPanel>
            </TabPanels>
          </Tabs>
          
          {error && <Text color="red.500" mt={2} fontSize="md">{error}</Text>}
        </FormControl>
        
        <Button 
          id="tour-summarise-button" 
          onClick={handleSummarise} 
          colorScheme="blue" 
          isLoading={loading} 
          mb={6} 
          size="lg" 
          px={8} 
          py={6} 
          fontSize="xl" 
          borderRadius="md"
        >
          Get Summary
        </Button>
        
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