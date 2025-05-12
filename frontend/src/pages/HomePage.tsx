import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  Spinner,
  Tag,
  VStack,
  Divider,
  Button,
  useDisclosure,
  IconButton,
  Flex,
  Spacer
} from '@chakra-ui/react';
import { getBackendHealth, type HealthStatus } from '../services/healthService.js';
import FileUploader from '../components/FileUploader.js';
import ChatPanel from '../components/ChatPanel.js';
import StrategyNoteGenerator from '../components/StrategyNoteGenerator.js';
import PrecedentPanel from '../components/PrecedentPanel.js';
import RedTeamModal from '../components/RedTeamModal.js';
import InfoSidebar from '../components/InfoSidebar.js';
import HealthStatusDisplay from '../components/HealthStatusDisplay.js';
import { InfoIcon, QuestionOutlineIcon } from '@chakra-ui/icons';
import GuidedTour from '../components/GuidedTour.js';
import { safeLocalStorage } from '../utils/localStorage.js';
import SummarisePanel from '../components/SummarisePanel.js';

console.log(`[HomePage Top Level] import.meta.env.VITE_E2E_TESTING: ${JSON.stringify(import.meta.env.VITE_E2E_TESTING)}`);
const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
console.log(`[HomePage Top Level] isE2E variable initialized to: ${isE2E}`);

const HomePage: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [uiReady, setUiReady] = useState(false);
  const { isOpen: isRedTeamModalOpen, onOpen: onRedTeamModalOpen, onClose: onRedTeamModalClose } = useDisclosure();
  const { isOpen: isInfoSidebarOpen, onOpen: onInfoSidebarOpen, onClose: onInfoSidebarClose } = useDisclosure();

  const [runTour, setRunTour] = useState(false);

  useEffect(() => {
    if (isE2E) {
      // Skip network call; mark UI ready immediately and set default health
      console.log('[HomePage] E2E mode detected, skipping health check and setting default health.');
      setHealth({ healthy: true, status: 'OK (E2E Mock)', message: 'Backend health check skipped for E2E tests.' });
      setLoadingHealth(false);
      setUiReady(true);
      return;
    }

    console.log('[HomePage] useEffect entered (non-E2E mode).');
    const fetchHealth = async () => {
      console.log('[HomePage] fetchHealth started.');
      try {
        setLoadingHealth(true); // Ensure loading state is true before fetch
        const healthStatus = await getBackendHealth();
        console.log('[HomePage] getBackendHealth resolved:', healthStatus);
        setHealth(healthStatus);
      } catch (error) {
        console.error('[HomePage] Failed to fetch backend health:', error);
        setHealth({ healthy: false, status: 'Error', message: 'Could not connect to backend.' });
      } finally {
        console.log('[HomePage] fetchHealth finally block. Setting loadingHealth false, uiReady true.');
        setLoadingHealth(false);
        setUiReady(true);
      }
    };
    fetchHealth();

    // Conditional tour logic remains, but outside the E2E fast path.
    // Note: VITE_E2E_TESTING check here is redundant if isE2E is used above for the main logic,
    // but kept for clarity on tour specifically if it needs to be different.
    // For now, let's align it: if it's E2E, tour also doesn't auto-start.
    if (!isE2E) {
      const tourCompleted = safeLocalStorage?.getItem('claimsAiTourCompleted');
      if (tourCompleted !== 'true') {
        setTimeout(() => setRunTour(true), 1000);
      }
    }
    console.log('[HomePage] useEffect finished (non-E2E mode).');
  }, []); // Empty dependency array ensures this runs once on mount

  const startTour = () => {
    setRunTour(true);
  };

  console.log(`[HomePage] Rendering. uiReady: ${uiReady}`);

  return (
    <Container id={uiReady ? 'app-ready' : undefined} maxW="container.xl" py={5}>
      {import.meta.env.VITE_E2E_TESTING !== 'true' && <GuidedTour run={runTour} setRun={setRunTour} />}
      <VStack spacing={8} align="stretch">
        <Flex alignItems="center" mb={4}>
          <Heading as="h1" size="xl">
            Claims-AI MVP
          </Heading>
          <Spacer />
          <Button 
            leftIcon={<QuestionOutlineIcon />} 
            onClick={startTour} 
            variant="outline"
            size="sm"
            mr={2} 
            id="tour-restart-button"
          >
            Start Tour
          </Button>
          <IconButton
            id="tour-info-sidebar-button"
            aria-label="Show Info"
            icon={<InfoIcon />}
            onClick={onInfoSidebarOpen}
            variant="outline"
            size="sm"
          />
        </Flex>
        
        <Box id="tour-health-status-display">
          <HealthStatusDisplay health={health} loadingHealth={loadingHealth} />
        </Box>

        <Box>
          <FileUploader />
        </Box>
        <Divider my="2" />
        <Box id="tour-strategy-note-generator">
          <StrategyNoteGenerator />
        </Box>
        <Divider my={2} />
        <Box id="tour-precedent-panel">
          <PrecedentPanel />
        </Box>
        <Divider my={2} />
        <Box id="tour-summarise-panel">
          <SummarisePanel />
        </Box>
        <Divider my={2} />
        <Box h="600px" display="flex" flexDirection="column">
          <ChatPanel />
        </Box>
      </VStack>
      <Button 
        id="tour-red-team-modal-button"
        onClick={onRedTeamModalOpen} 
        colorScheme="orange"
      >
        Run Red Team Evaluation
      </Button>
      <InfoSidebar isOpen={isInfoSidebarOpen} onClose={onInfoSidebarClose} />
      <RedTeamModal isOpen={isRedTeamModalOpen} onClose={onRedTeamModalClose} />
    </Container>
  );
};

export default HomePage; 