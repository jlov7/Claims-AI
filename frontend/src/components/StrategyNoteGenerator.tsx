import React, { useState, useEffect, useCallback } from 'react';
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
  Collapse,
  useDisclosure,
  useColorModeValue,
  Alert,
  AlertIcon,
  Code,
  Tooltip,
} from '@chakra-ui/react';
import { draftStrategyNote } from '../services/draftService.ts';
import { DraftStrategyNoteRequest } from '../models/draft.ts';
import { saveAs } from 'file-saver';
import { FiDownload } from 'react-icons/fi';

export interface StrategyNoteGeneratorProps {
  documentIds: string[];
  chatHistory?: string; // Optional chat history context
  claimSummary?: string; 
}

const StrategyNoteGenerator: React.FC<StrategyNoteGeneratorProps> = ({ documentIds, chatHistory, claimSummary }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [criteria, setCriteria] = useState('');
  const [draftContent, setDraftContent] = useState<string | null>(null); // Store draft text
  const toast = useToast();
  const { isOpen: isPreviewOpen, onToggle: onPreviewToggle } = useDisclosure();

  const handleGenerateAndDownload = async () => {
    if (isLoading) return;
    setIsLoading(true);
    setDraftContent(null); // Clear preview

    const requestData: DraftStrategyNoteRequest = {
      documentIds: documentIds.length > 0 ? documentIds : undefined,
      claimSummary: claimSummary?.trim() || undefined,
      additionalCriteria: `Chat History: ${chatHistory || 'N/A'}\nUser Criteria: ${criteria || 'None'}`,
      outputFilename: 'Strategy_Note.docx' // Default filename
    };

    try {
      const blob = await draftStrategyNote(requestData);
      saveAs(blob, requestData.outputFilename);

      setDraftContent(`Generated note based on:\n- Docs: ${documentIds.join(', ') || 'N/A'}\n- Summary: ${claimSummary || 'N/A'}\n- Chat/Criteria: Provided\n\n(DOCX downloaded)`);
      if (!isPreviewOpen) onPreviewToggle(); // Show preview area after download

      toast({
        title: 'Draft Downloaded',
        description: `${requestData.outputFilename} downloaded successfully.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

    } catch (error: any) {
      console.error('Error generating/downloading draft:', error);
      setDraftContent(null); // Clear preview on error
      if (isPreviewOpen) onPreviewToggle(); // Hide preview on error
      toast({
        title: 'Draft Generation Failed',
        description: error.message || 'Could not generate or download the strategy note.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box p={4} shadow="md" borderWidth="1px" borderRadius="md">
      <Heading size="md" mb={1}>Generate Strategy Note (DOCX)</Heading>
      <Text fontSize="sm" color="gray.600" mb={3}>
        Draft a claim strategy note in Word format using AI context.
      </Text>
       <Tooltip 
         label="Click to generate a DOCX strategy note using the AI, based on the context of uploaded documents."
         placement="top"
         hasArrow
       >
        <Button 
          leftIcon={<FiDownload />} 
          colorScheme="teal"
          onClick={handleGenerateAndDownload} 
          isLoading={isLoading}
          loadingText="Generating & Downloading..."
          className="strategy-note-button"
          mt={2}
        >
          Generate & Download DOCX
        </Button>
      </Tooltip>

      <FormControl>
        <FormLabel htmlFor="strategy-criteria" fontSize="sm">Optional Criteria:</FormLabel>
        <Textarea 
          id="strategy-criteria" 
          value={criteria}
          onChange={(e) => setCriteria(e.target.value)}
          placeholder="Enter specific points or sections to include..."
          size="sm"
          rows={2}
        />
      </FormControl>

      <Collapse in={isPreviewOpen} animateOpacity>
        <Box mt={4} p={3} borderWidth="1px" borderRadius="md" bg={useColorModeValue('gray.50', 'gray.700')}>
          <Heading size="sm" mb={2}>Generated Note Context</Heading>
          <Textarea 
            value={draftContent || ''} 
            isReadOnly 
            height="150px"
            fontFamily="monospace"
            fontSize="xs"
            borderColor="gray.300"
          />
        </Box>
      </Collapse>
    </Box>
  );
};

export default StrategyNoteGenerator; 