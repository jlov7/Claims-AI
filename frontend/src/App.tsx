import React, { useState, useEffect } from "react";
import {
  ChakraProvider,
  Box,
  Grid,
  GridItem,
  theme,
  VStack,
  Spinner,
  Text,
  Heading,
  IconButton,
  useDisclosure,
  Tooltip,
  Button,
} from "@chakra-ui/react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage.tsx";
import { getBackendHealth } from "./services/healthService.ts";
import { QuestionIcon, InfoIcon } from "@chakra-ui/icons";
import InfoSidebar from "./components/InfoSidebar.tsx";
import KafkaInspector from "./components/KafkaInspector/KafkaInspector.tsx";

const App = () => {
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const {
    isOpen: isInfoSidebarOpen,
    onOpen: onInfoSidebarOpen,
    onClose: onInfoSidebarClose,
  } = useDisclosure();
  const [showKafkaInspector, setShowKafkaInspector] = useState<boolean>(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await getBackendHealth();
        setBackendHealthy(
          health.healthy ??
            (health.status === "OK" ||
              health.status?.toLowerCase().includes("healthy")),
        );
      } catch (error) {
        console.error("Failed to fetch backend health:", error);
        setBackendHealthy(false);
      }
    };
    checkHealth();

    // For demo: always clear the tour completed flag and optionally start the tour
    localStorage.removeItem("claimsAiTourCompleted");
    // Uncomment to always start tour on app load:
    // setRunTour(true);
  }, []);

  return (
    <ChakraProvider theme={theme}>
      <BrowserRouter basename={import.meta.env.APP_BASE}>
        <InfoSidebar isOpen={isInfoSidebarOpen} onClose={onInfoSidebarClose} />
        <Box textAlign="center" fontSize="xl">
          <Grid
            minH="100vh"
            p={3}
            templateAreas={`"header header header"
                            "nav main aside"
                            "footer footer footer"`}
            gridTemplateRows={"auto 1fr auto"}
            gridTemplateColumns={"auto 1fr auto"}
            gap="1"
          >
            <GridItem
              pl="2"
              area={"header"}
              display="flex"
              justifyContent="space-between"
              alignItems="center"
            >
              <Heading size="md">Claims-AI Test</Heading>
              <Box>
                <Button
                  onClick={() => setShowKafkaInspector(!showKafkaInspector)}
                  size="sm"
                  variant="outline"
                  mr={2}
                  className="kafka-inspector-toggle-button-header"
                >
                  {showKafkaInspector ? "Hide" : "Show"} Kafka Log
                </Button>
                <Tooltip
                  label="Use the 'Start Tour' button on the main page to begin the Guided Tour."
                  aria-label="Start guided tour"
                >
                  <IconButton
                    aria-label="Start Guided Tour"
                    icon={<QuestionIcon />}
                    isDisabled={true}
                    variant="ghost"
                    mr={2}
                    className="guided-tour-button"
                  />
                </Tooltip>
                <Tooltip
                  label="Info & Architecture"
                  aria-label="Show info sidebar"
                >
                  <IconButton
                    aria-label="Show info sidebar"
                    icon={<InfoIcon />}
                    onClick={onInfoSidebarOpen}
                    variant="ghost"
                    mr={2}
                    className="info-sidebar-button"
                  />
                </Tooltip>
              </Box>
            </GridItem>

            {/* Removed Nav and Aside GridItems for simplicity in this example, assuming HomePage handles layout */}
            {/* <GridItem pl='2' area={'nav'}>Nav</GridItem> */}
            <GridItem pl="2" area={"main"}>
              {backendHealthy === null ? (
                <VStack
                  spacing={4}
                  justify="center"
                  align="center"
                  height="80vh"
                >
                  <Spinner size="xl" />
                  <Text>Connecting to backend...</Text>
                </VStack>
              ) : backendHealthy ? (
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  {/* Add other routes here */}
                </Routes>
              ) : (
                <VStack
                  spacing={4}
                  justify="center"
                  align="center"
                  height="80vh"
                >
                  <Text color="red.500" fontSize="lg">
                    Backend connection failed. Please ensure backend services
                    are running.
                  </Text>
                  <Text fontSize="sm">
                    Check console for details or try refreshing.
                  </Text>
                </VStack>
              )}
            </GridItem>
            {/* <GridItem pl='2' area={'aside'}>Aside</GridItem> */}

            <GridItem pl="2" area={"footer"} fontSize="sm">
              © {new Date().getFullYear()} Claims-AI Project. All rights
              reserved.
            </GridItem>
          </Grid>
        </Box>
        {showKafkaInspector && <KafkaInspector />}
      </BrowserRouter>
    </ChakraProvider>
  );
};

export default App;
