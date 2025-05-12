import React, { useEffect, useRef } from 'react';
import {
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  VStack,
  Text,
  Heading,
  Box,
} from '@chakra-ui/react';
import mermaid from 'mermaid';

interface InfoSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// Basic diagram based on project.md section 4
const mermaidChart = `
graph LR
    subgraph "User's Browser"
        A[React + Chakra UI on Vite]
    end

    subgraph "Backend Server (Docker)"
        B[FastAPI Gateway]
        C[Postgres - Metadata]
        D[RAG Orchestrator - LangChain]
        E[Chroma - Vector Store]
        F[Phi-4 via LM Studio]
        G[Coqui TTS]
        H[Minio - MP3 Storage]
        I[Security/Eval Harness]
    end

    A -- HTTPS --> B;
    B <--> C;
    B -- REST --> D;
    D --- E;
    D --- F;
    B --> G;
    G --> H;
    B --> I;

    style A fill:#f9f,stroke:#333,stroke-width:2px;
    style B fill:#bbf,stroke:#333,stroke-width:2px;
    style C fill:#ccf,stroke:#333,stroke-width:2px;
    style D fill:#bbf,stroke:#333,stroke-width:2px;
    style E fill:#ccf,stroke:#333,stroke-width:2px;
    style F fill:#ddf,stroke:#333,stroke-width:2px;
    style G fill:#bbf,stroke:#333,stroke-width:2px;
    style H fill:#ccf,stroke:#333,stroke-width:2px;
    style I fill:#bbf,stroke:#333,stroke-width:2px;
`;

const howItWorksText = `
Claims-AI is an open-source prototype designed to streamline claim file processing.
It leverages local Large Language Models (LLMs) and other open-source components to:

1.  **Upload & OCR:** Ingest claim files (PDF, TIFF, DOCX), extract text using Optical Character Recognition (OCR), and store it.
2.  **Vector Database:** Create "embeddings" (numerical representations) of the text and store them in a ChromaDB vector database for fast semantic search.
3.  **RAG Chat:** Allow users to ask questions about the claim documents. The system retrieves relevant text chunks from ChromaDB and uses the Phi-4 LLM (via LM Studio) to generate answers with citations.
4.  **Document Summaries:** Provide concise summaries of ingested documents.
5.  **Strategy Note Drafting:** Assist in drafting claim strategy notes in Word (DOCX) format based on claim data and user input.

**Innovation Features:**
-   **Nearest Precedent Finder:** Identifies similar past claims.
-   **Confidence Meter & Self-Healing Answers:** Rates answer confidence and attempts to improve low-confidence responses.
-   **Voice-Over Playback:** Converts AI chat responses to speech using Coqui TTS.
-   **Interactive Red-Team Button:** Allows testing the system's robustness against adversarial prompts.

The system is designed to run locally on a MacBook, with all core backend services containerized using Docker Compose.
`;

const InfoSidebar: React.FC<InfoSidebarProps> = ({ isOpen, onClose }) => {
  const mermaidDivRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'neutral', // or 'default', 'forest', 'dark', 'neutral'
      securityLevel: 'loose',
      fontFamily: 'sans-serif',
    });
  }, []);

  useEffect(() => {
    if (isOpen && mermaidDivRef.current) {
      mermaidDivRef.current.innerHTML = mermaidChart; // Set content before rendering
      try {
        mermaid.run({
          nodes: [mermaidDivRef.current],
        });
      } catch (e) {
        console.error("Error rendering mermaid chart:", e);
      }
    } else if (mermaidDivRef.current) {
        // Clear the content when the drawer is closed to avoid re-rendering issues
        mermaidDivRef.current.innerHTML = '';
    }
  }, [isOpen, mermaidChart]);

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="md">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px">About Claims-AI</DrawerHeader>
        <DrawerBody>
          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="md" mb={2}>
                System Architecture
              </Heading>
              <Box 
                ref={mermaidDivRef} 
                className="mermaid"
                key={new Date().getTime()} // Force re-render by changing key, helps with mermaid updates
              >
                {/* Mermaid chart will be rendered here by useEffect */}
              </Box>
            </Box>
            <Box>
              <Heading size="md" mb={2}>
                How It Works
              </Heading>
              <Text whiteSpace="pre-line">{howItWorksText}</Text>
            </Box>
          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};

export default InfoSidebar; 