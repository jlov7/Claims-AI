import React from 'react';
import Joyride, { type CallBackProps, type Step, EVENTS, ACTIONS, STATUS } from 'react-joyride';
import { safeLocalStorage } from '../utils/localStorage.js';

interface GuidedTourProps {
  run: boolean;
  setRun: (run: boolean) => void;
}

const TOUR_STEPS: Step[] = [
  {
    target: '#tour-file-uploader',
    content: 'Welcome to Claims-AI! Start by uploading your claim documents here. You can drag & drop or click to select files (PDF, DOCX, TIFF).',
    placement: 'bottom',
    disableBeacon: true,
  },
  {
    target: '#tour-chat-input',
    content: 'Once documents are processed (you\'ll see them appear in the chat), ask questions about them here. For example: "What is the date of loss?" or "Summarize the key events." ',
    placement: 'top',
  },
  {
    target: '#tour-chat-messages-area',
    content: 'Your conversation with the AI, including its answers and any extracted information, will appear here.',
    placement: 'bottom',
  },
  {
    target: '#tour-strategy-note-generator',
    content: 'Need a strategy note? Click here to generate one based on your uploaded documents and conversation. You can then download it as a DOCX file.',
    placement: 'bottom',
  },
  {
    target: '#tour-precedent-panel',
    content: 'See relevant past cases (precedents) here. The AI will automatically find similar precedents based on the current claim.',
    placement: 'left',
  },
  {
    target: '#tour-summarise-panel',
    content: 'Need a quick summary? Use this panel: enter a Document ID or paste text, then click "Get Summary" to see a concise summary of the document.',
    placement: 'left',
  },
  {
    target: '[id^="tour-voice-over-button-"]',
    content: 'For AI messages, you can click an icon like this to hear the response read out loud.',
    placement: 'right',
  },
  {
    target: '#tour-red-team-modal-button',
    content: 'Curious about the AI\'s robustness? Click here to run a series of test prompts and see how it responds.',
    placement: 'left',
  },
  {
    target: '#tour-info-sidebar-button',
    content: 'Click this icon anytime to see a diagram of how the system works and a brief explanation of its components.',
    placement: 'left',
  },
  {
    target: 'body',
    content: 'You\'re all set! Explore the features and let us know if you have any questions. You can restart this tour anytime from the main page.',
    placement: 'center',
  },
];

const GuidedTour: React.FC<GuidedTourProps> = ({ run, setRun }) => {
  const handleJoyrideCallback = (data: CallBackProps) => {
    const { action, status } = data;

    if (
      status === STATUS.FINISHED ||
      status === STATUS.SKIPPED ||
      action === ACTIONS.CLOSE ||
      action === ACTIONS.RESET 
    ) {
      setRun(false);
      safeLocalStorage?.setItem('claimsAiTourCompleted', 'true');
    }
  };

  return (
    <Joyride
      steps={TOUR_STEPS}
      run={run}
      callback={handleJoyrideCallback}
      continuous
      showProgress
      showSkipButton
      scrollToFirstStep
      styles={{
        options: {
          zIndex: 10000,
          primaryColor: '#3182ce',
        },
        buttonClose: {
          display: 'none',
        },
        buttonNext: {
          backgroundColor: '#3182ce',
          color: 'white',
          borderRadius: '0.375rem',
          padding: '0.5rem 1rem',
        },
        buttonBack: {
          color: '#3182ce',
          borderRadius: '0.375rem',
          padding: '0.5rem 1rem',
        },
        buttonSkip: {
          color: '#718096',
        },
      }}
    />
  );
};

export default GuidedTour; 