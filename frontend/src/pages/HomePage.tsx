import React, { useEffect, useState } from "react";
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
  Heading,
  Alert,
  useToast,
} from "@chakra-ui/react";
import {
  getBackendHealth,
  type HealthStatus,
} from "../services/healthService.ts";
import FileUploader from "../components/FileUploader.tsx";
import ChatPanel from "../components/ChatPanel.tsx";
import StrategyNoteGenerator, {
  type StrategyNoteGeneratorProps,
} from "../components/StrategyNoteGenerator.tsx";
import PrecedentPanel, {
  type PrecedentPanelProps,
} from "../components/PrecedentPanel.tsx";
import RedTeamModal from "../components/RedTeamModal.tsx";
import InfoSidebar from "../components/InfoSidebar.tsx";
import HealthStatusDisplay from "../components/HealthStatusDisplay.tsx";
import { InfoIcon, QuestionOutlineIcon } from "@chakra-ui/icons";
import GuidedTour, { type GuidedTourProps } from "../components/GuidedTour.tsx";
import { safeLocalStorage } from "../utils/localStorage.ts";
import SummarisePanel from "../components/SummarisePanel.tsx";
import { type Precedent } from "../models/precedent.ts";
import { findNearestPrecedents } from "../services/precedentService.ts";

console.log(
  `[HomePage Top Level] import.meta.env.VITE_E2E_TESTING: ${JSON.stringify(import.meta.env.VITE_E2E_TESTING)}`,
);
const isE2E = import.meta.env.VITE_E2E_TESTING === "true";
console.log(`[HomePage Top Level] isE2E variable initialized to: ${isE2E}`);

const HomePage: React.FC = () => {
  // E2E test detection
  const isE2E = import.meta.env.VITE_E2E_TESTING === "true";
  console.log(`[HomePage] E2E Testing mode enabled: ${isE2E}`);

  // App state
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [uiReady, setUiReady] = useState(false);
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [runTour, setRunTour] = useState(false);

  // Precedents state
  const [precedents, setPrecedents] = useState<Precedent[]>([]); // Initialize as empty array
  const [precedentsLoading, setPrecedentsLoading] = useState(false);
  const [precedentsError, setPrecedentsError] = useState<string | null>(null);

  // Modal controls
  const {
    isOpen: isInfoSidebarOpen,
    onOpen: onInfoSidebarOpen,
    onClose: onInfoSidebarClose,
  } = useDisclosure();
  const {
    isOpen: isRedTeamModalOpen,
    onOpen: onRedTeamModalOpen,
    onClose: onRedTeamModalClose,
  } = useDisclosure();

  const toast = useToast();

  useEffect(() => {
    if (isE2E) {
      // Skip network call; mark UI ready immediately and set default health
      console.log(
        "[HomePage] E2E mode detected, skipping health check and setting default health.",
      );
      setHealth({
        healthy: true,
        status: "OK (E2E Mock)",
        message: "Backend health check skipped for E2E tests.",
      });
      setLoadingHealth(false);
      setUiReady(true);
      return;
    }

    console.log("[HomePage] useEffect entered (non-E2E mode).");
    const fetchHealth = async () => {
      console.log("[HomePage] fetchHealth started.");
      try {
        setLoadingHealth(true); // Ensure loading state is true before fetch
        const healthStatus = await getBackendHealth();
        console.log("[HomePage] getBackendHealth resolved:", healthStatus);
        setHealth(healthStatus);
      } catch (error) {
        console.error("[HomePage] Failed to fetch backend health:", error);
        setHealth({
          healthy: false,
          status: "Error",
          message: "Could not connect to backend.",
        });
      } finally {
        console.log(
          "[HomePage] fetchHealth finally block. Setting loadingHealth false, uiReady true.",
        );
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
      // For demo: always clear the tour completed flag and start the tour
      safeLocalStorage?.removeItem("claimsAiTourCompleted");
      const timer = setTimeout(() => {
        setRunTour(true);
      }, 1500); // Delay to allow all components to mount
      return () => clearTimeout(timer);
    }
  }, [uiReady, isE2E]);

  useEffect(() => {
    console.log("[HomePage] useEffect: runTour changed:", runTour);
  }, [runTour]);

  const handleDocumentsUploaded = (newDocIds: string[]) => {
    setDocumentIds(newDocIds);
    // Potentially trigger precedent search here or elsewhere
  };

  const handleSearchPrecedents = async (contextText: string) => {
    if (!contextText || documentIds.length === 0) return; // Only search if we have uploaded documents
    console.log(
      "[HomePage] Searching precedents based on context:",
      contextText.substring(0, 50) + "...",
    );
    setPrecedentsLoading(true);
    setPrecedentsError(null);
    try {
      const response = await findNearestPrecedents({
        claim_summary: contextText,
      });
      setPrecedents(response.precedents);
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to fetch precedents";
      console.error("[HomePage] Precedent search failed:", errorMsg);
      setPrecedentsError(errorMsg);
      setPrecedents([]); // Clear precedents on error
    } finally {
      setPrecedentsLoading(false);
    }
  };

  const startTour = () => {
    console.log("[HomePage] Start Tour button clicked");

    // First ensure any previous tour is fully cleaned up
    document.body.classList.remove("tour-active");
    document.querySelectorAll(".joyride-highlighted").forEach((el) => {
      el.classList.remove("joyride-highlighted");
    });

    // Force tour to stop before starting again
    setRunTour(false);

    // Add delay to ensure DOM is ready and previous tour is fully stopped
    setTimeout(() => {
      // Add class to body for CSS styling during tour
      document.body.classList.add("tour-active");

      // Ensure all tour elements have proper z-index and add highlighting class
      document.querySelectorAll('[id^="tour-"]').forEach((el) => {
        console.log("[HomePage] Found tour target:", el.id);
        el.classList.add("joyride-highlighted");
      });

      toast({
        title: "Guided Tour Started",
        description: "Follow the steps to learn about Claims-AI!",
        status: "info",
        duration: 3000,
      });

      // Start the tour after a brief delay to ensure state is reset
      setTimeout(() => {
        setRunTour(true);
      }, 50);
    }, 500);
  };

  // Handle tour completion and cleanup
  useEffect(() => {
    if (!runTour) {
      document.body.classList.remove("tour-active");
      // Clean up highlights when tour is stopped
      document.querySelectorAll(".joyride-highlighted").forEach((el) => {
        el.classList.remove("joyride-highlighted");
      });
    }
  }, [runTour]);

  console.log(`[HomePage] Rendering. uiReady: ${uiReady}, runTour: ${runTour}`);

  return (
    <Container
      id={loadingHealth ? undefined : "app-ready"}
      maxW="container.xl"
      py={8}
      px={{ base: 4, md: 8 }}
      bgColor="white"
      boxShadow="sm"
      borderRadius="xl"
    >
      {/* Demo Mode Banner */}
      <Alert
        status="info"
        variant="left-accent"
        borderRadius="lg"
        mb={6}
        fontSize="lg"
        fontWeight="bold"
        boxShadow="sm"
      >
        🚀 Demo Mode: This is a guided, interactive demo of Claims-AI. Click
        "Start Tour" for a walkthrough!
      </Alert>

      {import.meta.env.VITE_E2E_TESTING !== "true" && (
        <GuidedTour runTour={runTour} setRunTour={setRunTour} />
      )}

      <VStack spacing={10} align="stretch">
        <Flex
          alignItems="center"
          justifyContent="space-between"
          mb={6}
          pb={4}
          borderBottom="1px"
          borderColor="gray.100"
        >
          <Heading size="lg" color="brand.600">
            Claims-AI Demo
          </Heading>
          <Flex>
            <Button
              leftIcon={<QuestionOutlineIcon />}
              onClick={startTour}
              variant="outline"
              size="md"
              mr={4}
              id="tour-restart-button"
              className="tour-highlightable"
              colorScheme="brand"
            >
              Start Tour
            </Button>
            <IconButton
              id="tour-info-sidebar-button"
              aria-label="Show Info"
              icon={<InfoIcon />}
              onClick={onInfoSidebarOpen}
              variant="outline"
              size="md"
              className="tour-highlightable"
              colorScheme="brand"
            />
          </Flex>
        </Flex>

        {/* Section 1: Setup & Upload */}
        <Box
          p={6}
          borderRadius="xl"
          borderWidth="1px"
          borderColor="gray.200"
          bg="white"
          boxShadow="sm"
        >
          <Heading size="lg" mb={4} color="brand.600">
            Step 1: Upload & Prepare
          </Heading>
          <Text fontSize="md" color="gray.600" mb={6}>
            Upload your claim documents here (PDF, TIFF, or DOCX). The app will
            OCR them and make their contents available for summarisation and
            AI-powered queries.
          </Text>
          <Box
            id="tour-health-status-display"
            className="tour-highlightable"
            p={5}
            mb={5}
            bg="gray.50"
            borderRadius="lg"
          >
            <HealthStatusDisplay
              health={health}
              loadingHealth={loadingHealth}
            />
          </Box>
          <Box
            id="tour-file-uploader"
            className="tour-highlightable"
            p={6}
            borderRadius="lg"
            boxShadow="md"
            bg="gray.50"
          >
            <FileUploader />
          </Box>
        </Box>

        {/* Section 2: Analyse & Understand */}
        <Box
          p={6}
          borderRadius="xl"
          borderWidth="1px"
          borderColor="gray.200"
          bg="white"
          boxShadow="sm"
        >
          <Heading size="lg" mb={4} color="brand.600">
            Step 2: Analyse & Understand
          </Heading>
          <Text fontSize="md" color="gray.600" mb={6}>
            Use the summarisation panel to get quick document summaries, or chat
            with the AI to ask specific questions based on your uploaded
            documents.
          </Text>
          <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={8}>
            {/* Summarise Panel */}
            <GridItem rowSpan={1} colSpan={{ base: 1, lg: 1 }}>
              <Box
                id="tour-summarise-panel"
                className="summarise-panel-container tour-highlightable"
                height="500px"
                overflowY="auto"
                borderWidth="1px"
                borderRadius="lg"
                p={6}
                bg="gray.50"
                boxShadow="sm"
              >
                <SummarisePanel />
              </Box>
            </GridItem>
            {/* Chat Panel */}
            <GridItem rowSpan={1} colSpan={{ base: 1, lg: 1 }}>
              <Box
                id="tour-chat-panel"
                height="500px"
                overflowY="auto"
                borderWidth="1px"
                borderRadius="lg"
                p={6}
                className="chat-panel-container tour-highlightable"
                bg="gray.50"
                boxShadow="sm"
              >
                <ChatPanel onNewAiAnswer={handleSearchPrecedents} />
              </Box>
            </GridItem>
          </Grid>

          {/* Precedent Panel (Still part of Analysis) */}
          <Box mt={8}>
            <Heading size="md" mb={4} color="brand.600">
              Find Similar Precedents
            </Heading>
            <Text fontSize="md" color="gray.600" mb={4}>
              Explore historical claim cases that are similar to your context,
              helping you benchmark past outcomes and inform your strategy
              decisions.
            </Text>
            <Box
              id="tour-precedent-panel"
              className="tour-highlightable"
              p={6}
              bg="gray.50"
              borderRadius="lg"
              borderWidth="1px"
              boxShadow="sm"
            >
              <PrecedentPanel
                precedents={precedents}
                isLoading={precedentsLoading}
                error={precedentsError}
              />
            </Box>
          </Box>
        </Box>

        {/* Section 3: Generate Outputs & Test */}
        <Box
          p={6}
          borderRadius="xl"
          borderWidth="1px"
          borderColor="gray.200"
          bg="white"
          boxShadow="sm"
        >
          <Heading size="lg" mb={4} color="brand.600">
            Step 3: Generate Outputs & Test
          </Heading>
          <Text fontSize="md" color="gray.600" mb={6}>
            Create a professional strategy note in Word format based on your AI
            insights, then run the Red Team evaluation to stress-test the AI's
            responses and validate robustness.
          </Text>
          <Box
            id="tour-strategy-note-generator"
            className="tour-highlightable"
            p={6}
            bg="gray.50"
            borderRadius="lg"
            borderWidth="1px"
            boxShadow="sm"
            mb={6}
          >
            <StrategyNoteGenerator documentIds={documentIds} />
          </Box>
          <Divider my={6} />
          <Button
            id="tour-red-team-modal-button"
            className="tour-highlightable"
            onClick={onRedTeamModalOpen}
            colorScheme="orange"
            size="lg"
            py={7}
            width="100%"
            fontWeight="bold"
            boxShadow="md"
          >
            Run Red Team Evaluation
          </Button>
        </Box>
      </VStack>
      <InfoSidebar isOpen={isInfoSidebarOpen} onClose={onInfoSidebarClose} />
      <RedTeamModal isOpen={isRedTeamModalOpen} onClose={onRedTeamModalClose} />
    </Container>
  );
};

export default HomePage;
