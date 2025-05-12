import React from 'react';
import Joyride, { type Step, type CallBackProps, STATUS } from 'react-joyride';
import { useDisclosure } from '@chakra-ui/react';

// Export the interface
export interface GuidedTourProps {
    runTour: boolean;
    setRunTour: (run: boolean) => void;
}

const GuidedTour: React.FC<GuidedTourProps> = ({ runTour, setRunTour }) => {
  // Enhanced tour steps with clearer, benefit-focused language
  const steps: Step[] = [
    {
      target: '#tour-health-status-display', 
      content: 'First, check the status lights! Green means all systems (AI, databases) are ready to go.',
      placement: 'bottom',
      title: 'Welcome to Claims-AI!',
    },
    {
      target: '#tour-file-uploader', 
      content: 'Start here! Drag & drop your claim files (PDF, DOCX, TIFF) or click to browse. This feeds the AI the information it needs.',
      placement: 'right',
      title: 'Step 1: Upload Documents',
    },
     {
      target: '#tour-summarise-panel', 
      content: 'Need a quick overview? Enter a document ID (from uploaded files) or paste text here to get a concise summary from the AI.',
      placement: 'left',
      title: 'Analyse: Get a Summary',
    },
    {
      target: '#tour-chat-panel', 
      content: 'This is the main Q&A area. Ask specific questions about the documents you uploaded (e.g., \'What was the date of loss?\').',
      placement: 'top',
      title: 'Analyse: Ask Questions (RAG)',
    },
    {
      target: '#tour-chat-input-area', 
      content: 'Type your question here and press Enter or click Send. The AI will search the documents for answers.',
      placement: 'top',
      title: 'Analyse: Ask Questions (RAG)',
      disableBeacon: true,
    },
    {
      // Targets the wrapper, assumes an AI message appears after asking
      target: '#tour-chat-panel .ai-message:last-of-type',
      content: 'AI answers appear here! Look for the colored border indicating confidence (Green=High, Red=Low) and click the ▶️ button to hear it read aloud.',
      placement: 'bottom',
      title: 'Analyse: Review AI Answers',
      disableBeacon: true, 
    },
    {
      target: '#tour-precedent-panel', 
      content: 'This panel automatically updates with similar past cases based on the latest AI chat answer, helping you find relevant history.',
      placement: 'left',
      title: 'Analyse: Find Similar Precedents',
    },
     {
      target: '#tour-strategy-note-generator', 
      content: 'Ready to draft? Click the button here to generate a basic Claim Strategy Note in DOCX format based on the documents and chat.',
      placement: 'top',
      title: 'Step 3: Generate Strategy Note',
    },
    {
      target: '#tour-red-team-modal-button', 
      content: 'Curious about AI safety? Click this to run pre-defined \'stress tests\' (adversarial prompts) and see how the AI responds.',
      placement: 'top',
      title: 'Test: Run Red Team Evaluation',
    },
    {
      target: '#tour-info-sidebar-button', 
      content: 'Need a refresher? Click this anytime to see the architecture diagram and learn more about how Claims-AI works.',
      placement: 'bottom',
      title: 'Learn More: Info Sidebar',
    },
     {
      target: '#tour-restart-button', 
      content: 'You can restart this tour anytime by clicking here!',
      placement: 'bottom',
      title: 'Tour Complete!',
    },
  ];

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status } = data;
    const finishedStatuses: string[] = [STATUS.FINISHED, STATUS.SKIPPED];

    if (finishedStatuses.includes(status)) {
      setRunTour(false); // Stop the tour when finished or skipped
    }
  };

  return (
    <Joyride
      steps={steps}
      run={runTour}
      continuous={true}
      showProgress={true}
      showSkipButton={true}
      callback={handleJoyrideCallback}
      styles={{
        options: {
          zIndex: 10000, // Ensure it's above other elements
          primaryColor: '#3182ce', // Chakra blue.500
          textColor: '#1A202C', // Chakra gray.800
        },
        buttonClose: {
            display: 'none', // Hide default close button if using skip/finish logic
        },
         tooltip: {
          backgroundColor: '#FFFFFF', // White background
          borderRadius: 'md', // Chakra medium border radius
        },
        tooltipContainer: {
          textAlign: 'left',
        },
        tooltipTitle: {
          fontWeight: 'bold', // Bold title
        },
        buttonNext: {
          backgroundColor: '#3182ce', // Chakra blue.500
          borderRadius: 'md',
        },
        buttonBack: {
           color: '#4A5568', // Chakra gray.600
        },
        buttonSkip: {
            color: '#718096', // Chakra gray.500
        },
      }}
    />
  );
};

export default GuidedTour; 