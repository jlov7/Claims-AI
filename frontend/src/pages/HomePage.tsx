import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Text,
  Spinner,
  Tag,
  VStack,
  Divider,
  Button,
  useDisclosure,
  IconButton,
  Flex,
  Spacer,
  Grid,
  GridItem,
  Heading
} from '@chakra-ui/react';
import { getBackendHealth, type HealthStatus } from '../services/healthService.ts';
import FileUploader from '../components/FileUploader.tsx';
import ChatPanel from '../components/ChatPanel.tsx';
import StrategyNoteGenerator, { type StrategyNoteGeneratorProps } from '../components/StrategyNoteGenerator.tsx';
import PrecedentPanel, { type PrecedentPanelProps } from '../components/PrecedentPanel.tsx';
import RedTeamModal from '../components/RedTeamModal.tsx';
import InfoSidebar from '../components/InfoSidebar.tsx';
import HealthStatusDisplay from '../components/HealthStatusDisplay.tsx';
import { InfoIcon, QuestionOutlineIcon } from '@chakra-ui/icons';
import GuidedTour, { type GuidedTourProps } from '../components/GuidedTour.tsx';
import { safeLocalStorage } from '../utils/localStorage.ts';
import SummarisePanel from '../components/SummarisePanel.tsx';
import { type Precedent } from '../models/precedent.ts';
import { findNearestPrecedents } from '../services/precedentService.ts';

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
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [precedentsLoading, setPrecedentsLoading] = useState<boolean>(false);
  const [precedentsError, setPrecedentsError] = useState<string | null>(null);

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

    // Note: This effect might run twice in StrictMode, which is ok for fetching health
    // but we need to be careful with side effects like starting the tour.
  }, []); // Fetch health on initial mount

  // Separate effect for starting the tour, dependent on uiReady
  useEffect(() => {
    if (uiReady && !isE2E) {
      console.log('[HomePage Tour Effect] UI is ready, checking if tour should start.');
      const tourCompleted = safeLocalStorage?.getItem('claimsAiTourCompleted');
      if (tourCompleted !== 'true') {
        // Add a longer delay to allow all components to mount
        const timer = setTimeout(() => {
             console.log('[HomePage Tour Effect] Starting tour after delay.');
             setRunTour(true);
             // Optionally mark tour as started/completed immediately
             // safeLocalStorage?.setItem('claimsAiTourCompleted', 'true'); 
         }, 1500); // Increased delay
        return () => clearTimeout(timer); // Cleanup timeout on unmount
      } else {
         console.log('[HomePage Tour Effect] Tour already completed.');
      }
    }
  }, [uiReady, isE2E]); // Re-run this effect when uiReady changes

  const handleDocumentsUploaded = (newDocIds: string[]) => {
    setDocumentIds(newDocIds); 
    // Potentially trigger precedent search here or elsewhere
  };

  const handleSearchPrecedents = async (contextText: string) => {
     if (!contextText) return; // Don't search without context
     console.log('[HomePage] Searching precedents based on context:', contextText.substring(0, 50) + '...');
     setPrecedentsLoading(true);
     setPrecedentsError(null);
     try {
       const response = await findNearestPrecedents({ claim_summary: contextText });
       setPrecedents(response.precedents);
     } catch (err) {
       const errorMsg = err instanceof Error ? err.message : 'Failed to fetch precedents';
       console.error('[HomePage] Precedent search failed:', errorMsg);
       setPrecedentsError(errorMsg);
       setPrecedents([]); // Clear precedents on error
     } finally {
       setPrecedentsLoading(false);
     }
  };

  const startTour = () => {
    setRunTour(true);
  };

  console.log(`[HomePage] Rendering. uiReady: ${uiReady}`);

  return (
    <Container id={uiReady ? 'app-ready' : undefined} maxW="container.xl" py={5}>
      {import.meta.env.VITE_E2E_TESTING !== 'true' && <GuidedTour runTour={runTour} setRunTour={setRunTour} />}
      <VStack spacing={8} align="stretch">
         <Flex alignItems="center" mb={4}>
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
         
         {/* Section 1: Setup & Upload */} 
         <Heading size="lg" mt={6} mb={2}>Step 1: Upload & Prepare</Heading>
         <Box id="tour-health-status-display">
           <HealthStatusDisplay health={health} loadingHealth={loadingHealth} />
         </Box>
         <Box id="tour-file-uploader" mt={4}>
           <FileUploader />
         </Box>
         
         {/* Section 2: Analyse & Understand */} 
         <Heading size="lg" mt={8} mb={2}>Step 2: Analyse & Understand</Heading>
         <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={6}>
           {/* Summarise Panel */}
           <GridItem rowSpan={1} colSpan={{ base: 2, lg: 1 }} >
             <Box height="500px" overflowY="auto" borderWidth="1px" borderRadius="lg" p={4} className="summarise-panel-container">
               <SummarisePanel />
             </Box>
           </GridItem>

           {/* Chat Panel */}
           <GridItem rowSpan={1} colSpan={{ base: 2, lg: 1 }} >
             <Box height="500px" overflowY="auto" borderWidth="1px" borderRadius="lg" p={4} className="chat-panel-container">
               <ChatPanel onNewAiAnswer={handleSearchPrecedents} />
             </Box>
           </GridItem>
         </Grid>
         
         {/* Precedent Panel (Still part of Analysis) */} 
         <Heading size="md" mt={6} mb={2}>Find Similar Precedents</Heading>
         <Box id="tour-precedent-panel">
           <PrecedentPanel 
             precedents={precedents} 
             isLoading={precedentsLoading} 
             error={precedentsError}
           />
         </Box>

         {/* Section 3: Generate Outputs & Test */} 
         <Heading size="lg" mt={8} mb={2}>Step 3: Generate Outputs & Test</Heading>
         <Box id="tour-strategy-note-generator">
           <StrategyNoteGenerator documentIds={documentIds} />
         </Box>
         <Divider my={4} />
         <Button 
           id="tour-red-team-modal-button"
           onClick={onRedTeamModalOpen} 
           colorScheme="orange"
         >
           Run Red Team Evaluation
         </Button>
      </VStack>
      <InfoSidebar isOpen={isInfoSidebarOpen} onClose={onInfoSidebarClose} />
      <RedTeamModal isOpen={isRedTeamModalOpen} onClose={onRedTeamModalClose} />
    </Container>
  );
};

export default HomePage; 