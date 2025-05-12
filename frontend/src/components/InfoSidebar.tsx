import React from 'react';
import {
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  VStack,
  Text,
  Code,
  Heading,
  Box,
  Link,
  Icon
} from '@chakra-ui/react';
import MermaidChart from '../utils/Mermaid.tsx'; // Corrected relative path
import { ExternalLinkIcon } from '@chakra-ui/icons';

interface InfoSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// Define the Mermaid diagram chart text
const chart = `
graph TD
    subgraph User Interaction
        A[Browser: React + Chakra UI] --> B{FastAPI Backend Gateway};
    end

    subgraph Backend Services
        B --> C[PostgreSQL: Metadata];
        B --> D{RAG Orchestrator: LangChain};
        D --> E[ChromaDB: Vector Store];
        D --> F[LLM: Phi-4 via LM Studio];
        B --> G[Coqui TTS Service];
        G --> H[Minio: MP3 Audio];
        B --> I[Security/Eval Harness];
        B --> J[Minio: Docs/Summaries];
    end

    subgraph Data Stores
        C;
        E;
        H;
        J;
    end

    subgraph External Services
        F;
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px;
    style B fill:#ccf,stroke:#333,stroke-width:2px;
    style C fill:#dbf,stroke:#333,stroke-width:1px;
    style D fill:#cdf,stroke:#333,stroke-width:2px;
    style E fill:#bfd,stroke:#333,stroke-width:1px;
    style F fill:#ffd,stroke:#333,stroke-width:1px;
    style G fill:#dcf,stroke:#333,stroke-width:1px;
    style H fill:#fdb,stroke:#333,stroke-width:1px;
    style I fill:#fef,stroke:#333,stroke-width:1px;
    style J fill:#fdb,stroke:#333,stroke-width:1px;
`;

const InfoSidebar: React.FC<InfoSidebarProps> = ({ isOpen, onClose }) => {
  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="lg">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader borderBottomWidth="1px">
          About Claims-AI & Architecture
        </DrawerHeader>

        <DrawerBody>
          <VStack spacing={5} align="stretch">
            <Heading size="md">What is Claims-AI?</Heading>
            <Text>
              Claims-AI is a prototype demonstrating how AI can accelerate complex claims processing. 
              It uses open-source tools and a locally run AI model (Microsoft's Phi-4) to provide features like document understanding, Q&A, summarization, precedent finding, and strategy note drafting.
            </Text>

            <Heading size="md">Typical Workflow</Heading>
            <Text>1. 📄 **Upload:** Start by uploading claim documents (PDF, DOCX, etc.).</Text>
            <Text>2. 🧠 **Analyse:** Use the panels to summarise documents, ask specific questions (Chat), or find similar past claims (Precedents).</Text>
            <Text>3. ✨ **Generate:** Create outputs like strategy notes based on your analysis.</Text>
            <Text>4. 🧪 **Test:** Use the Red Team button to check the AI's robustness.</Text>

            <Heading size="md">How Key Features Work (ELI5)</Heading>
             <Box pl={4}>
                <Text>• **Uploader:** Reads documents using OCR (like scanning eyes) and prepares them for the AI.</Text>
                <Text>• **Summariser:** Asks the AI to give you a short version of a document.</Text>
                <Text>• **Chat (RAG):** Lets you ask questions. The AI looks through the documents (using a Vector DB 'filing cabinet') to find relevant info and gives you an answer with sources (citations).</Text>
                <Text>• **Precedents:** After the AI answers in the chat, this panel automatically shows similar past claims.</Text>
                <Text>• **Strategy Note:** Drafts a basic strategy note in Word format based on the available information.</Text>
                <Text>• **Confidence/Healing:** Shows how sure the AI is about its chat answers and tries to fix low-confidence ones automatically.</Text>
                <Text>• **Voice Over:** Reads the AI's chat answers aloud.</Text>
                <Text>• **Red Team:** Tests the AI with tricky questions to see how well it handles them.</Text>
            </Box>

            <Heading size="md">System Architecture</Heading>
            <Text fontSize="sm" color="gray.600">
                This diagram shows the main components. The <Code colorScheme='blue'>FastAPI Gateway</Code> is the main entry point. 
                <Code colorScheme='purple'>LangChain</Code> orchestrates the AI logic, using <Code colorScheme='green'>ChromaDB</Code> to find relevant text and the 
                <Code colorScheme='yellow'>Phi-4 LLM</Code> for understanding and generation. 
                <Code colorScheme='orange'>Minio</Code> stores files.
            </Text>
            <Box borderWidth="1px" borderRadius="lg" p={4} overflowX="auto">
                 <MermaidChart chart={chart} />
            </Box>

            <Heading size="md">Key Technologies</Heading>
            <Text> - **Frontend:** React, Chakra UI, Vite</Text>
            <Text> - **Backend:** Python, FastAPI, LangChain</Text>
            <Text> - **AI Model:** Microsoft Phi-4 (via LM Studio)</Text>
            <Text> - **Vector Database:** ChromaDB</Text>
            <Text> - **OCR:** Tesseract</Text>
            <Text> - **File Storage:** Minio (S3 compatible)</Text>
            <Text> - **Audio:** Coqui TTS</Text>
            <Text> - **Database:** PostgreSQL</Text>
            <Text> - **Containerization:** Docker</Text>

            <Heading size="md">Want to learn more?</Heading>
             <Link href="https://github.com/jasonlovell/Claims-AI/blob/main/project.md" isExternal color="blue.500">
              Read the Full Project Requirements <Icon as={ExternalLinkIcon} mx="2px" />
            </Link>
             <Link href="https://github.com/jasonlovell/Claims-AI/blob/main/explanations.txt" isExternal color="blue.500">
              Explore the Development Log (explanation.txt) <Icon as={ExternalLinkIcon} mx="2px" />
            </Link>
              <Link href="https://github.com/jasonlovell/Claims-AI" isExternal color="blue.500">
              View the Source Code on GitHub <Icon as={ExternalLinkIcon} mx="2px" />
            </Link>

          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
};

export default InfoSidebar; 