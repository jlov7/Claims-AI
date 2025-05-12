import React, { useEffect, useState, useCallback, useRef } from 'react';
import Joyride, { Step, CallBackProps, STATUS, EVENTS } from 'react-joyride';
import { useToast } from '@chakra-ui/react';
import '../styles/joyride-custom.css';

// Export the interface
export interface GuidedTourProps {
    runTour: boolean;
    setRunTour: (run: boolean) => void;
}

const GuidedTour: React.FC<GuidedTourProps> = ({ runTour, setRunTour }) => {
  console.log("[GuidedTour] Component rendering, runTour:", runTour);
  const toast = useToast();
  const [stepIndex, setStepIndex] = useState(0);
  const joyrideRef = useRef<any>(null);
  
  // Reset step index when tour starts
  useEffect(() => {
    if (runTour) {
      setStepIndex(0);
    }
  }, [runTour]);
  
  // Enhanced tour steps with clearer, benefit-focused language
  const steps: Step[] = [
    {
      target: "#tour-health-status-display",
      content: "Let's start by checking the lights at the top! Green means everything is ready and you can use Claims-AI with confidence.",
      placement: "bottom",
      title: "Step 1: Welcome!",
      disableBeacon: true
    },
    {
      target: "#tour-file-uploader",
      content: "Simply drag and drop your claim files here, or click to browse. This is how you give the AI the information it needs to help you.",
      placement: "right",
      title: "Step 2: Upload Your Documents",
      disableBeacon: true
    },
    {
      target: "#tour-summarise-panel",
      content: "Want a quick summary? Enter a document ID or paste some text here, and the AI will give you a clear, simple summary in seconds.",
      placement: "left",
      title: "Step 3: Get a Quick Summary",
      disableBeacon: true
    },
    {
      target: "#tour-chat-panel",
      content: "This is your chat area. Ask any question about your documents—like \"What's the claim amount?\"—and the AI will find the answer for you.",
      placement: "top",
      title: "Step 4: Ask Anything",
      disableBeacon: true
    },
    {
      target: "#tour-chat-input-area",
      content: "Type your question here and press Send. The AI will search your documents and reply right away.",
      placement: "top",
      title: "Step 5: Type Your Question",
      disableBeacon: true
    },
    {
      target: "#tour-chat-panel .ai-message:last-of-type",
      content: "Here's where the AI's answers appear! Look for the confidence color (green is best) and click the play button to hear the answer out loud.",
      placement: "bottom",
      title: "Step 6: See & Hear Answers",
      disableBeacon: true
    },
    {
      target: "#tour-precedent-panel",
      content: "This panel shows similar past cases, so you can see what happened before in situations like yours.",
      placement: "left",
      title: "Step 7: See Similar Cases",
      disableBeacon: true
    },
    {
      target: "#tour-strategy-note-generator",
      content: "Ready to write up your findings? Click here to instantly create a professional Word document with your strategy notes.",
      placement: "top",
      title: "Step 8: Create a Strategy Note",
      disableBeacon: true
    },
    {
      target: "#tour-red-team-modal-button",
      content: "Want to see how robust the AI is? Click here to run some \"stress tests\" and see how it handles tricky questions.",
      placement: "top",
      title: "Step 9: Test the AI",
      disableBeacon: true
    },
    {
      target: "#tour-info-sidebar-button",
      content: "Need more info? Click here anytime to see how Claims-AI works behind the scenes.",
      placement: "bottom",
      title: "Step 10: Learn More",
      disableBeacon: true
    },
    {
      target: "#tour-restart-button",
      content: "You can restart this tour anytime by clicking here. Enjoy exploring Claims-AI!",
      placement: "bottom",
      title: "Step 11: Tour Complete!",
      disableBeacon: true
    }
  ];
  
  const handleJoyrideCallback = useCallback((data: CallBackProps) => {
    const { action, index, status, type } = data;
    console.log("[GuidedTour] Joyride callback:", { action, index, status, type });
    
    if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
      // Update step index when moving to next step
      if (typeof index === 'number') {
        setStepIndex(index + (action === 'next' ? 1 : -1));
      }
    } else if (type === EVENTS.TOUR_START) {
      console.log("[GuidedTour] Tour started!");
      setStepIndex(0);
    } else if (type === EVENTS.TOUR_END || status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      console.log("[GuidedTour] Tour ended with status:", status);
      
      // Cleanup all highlighted elements
      document.querySelectorAll('.joyride-highlighted').forEach(el => {
        el.classList.remove('joyride-highlighted');
      });
      document.body.classList.remove('tour-active');
      
      setRunTour(false);
      toast({ 
        title: 'Tour Complete', 
        description: 'You can restart the tour anytime!', 
        status: 'success', 
        duration: 4000 
      });
    }
  }, [setRunTour, toast]);

  // Add debug logging
  useEffect(() => {
    if (runTour) {
      console.log("[GuidedTour] Tour should be running now");
      // Reset to first step on tour restart
      setStepIndex(0);
      
      // Force react-joyride to reset by removing and re-adding to DOM
      if (joyrideRef.current) {
        try {
          joyrideRef.current.reset();
        } catch (e) {
          console.log("[GuidedTour] Reset error (non-critical):", e);
        }
      }
    } else {
      console.log("[GuidedTour] Tour is not running");
    }
  }, [runTour]);

  // When tour is not running, don't render Joyride at all to avoid any stale state
  if (!runTour) {
    return null;
  }

  return (
    <Joyride
      ref={joyrideRef}
      steps={steps}
      run={runTour}
      stepIndex={stepIndex}
      continuous={true}
      showProgress={true}
      showSkipButton={true}
      spotlightClicks={false}
      disableCloseOnEsc={false}
      disableOverlay={false}
      disableScrolling={true}
      hideBackButton={false}
      callback={handleJoyrideCallback}
      styles={{
        options: {
          zIndex: 10000,
          primaryColor: '#0061e6', // brand.500
          textColor: '#1A202C',
          overlayColor: 'rgba(0,0,0,0.5)',
          arrowColor: '#FFFFFF'
        },
        buttonClose: { display: 'none' },
        tooltip: { 
          backgroundColor: '#FFFFFF', 
          borderRadius: '8px',
          fontSize: '16px',
          padding: '20px'
        },
        tooltipContainer: { 
          textAlign: 'left'
        },
        tooltipTitle: { 
          fontWeight: 'bold',
          fontSize: '18px',
          marginBottom: '12px',
          color: '#0061e6'
        },
        buttonNext: { 
          backgroundColor: '#0061e6', 
          borderRadius: '6px',
          fontSize: '16px',
          padding: '10px 16px'
        },
        buttonBack: { 
          color: '#4A5568',
          marginRight: '12px'
        },
        buttonSkip: { 
          color: '#718096'
        },
        spotlight: {
          backgroundColor: 'transparent',
          borderRadius: '4px'
        },
        overlay: {
          backgroundColor: 'rgba(0,0,0,0.5)'
        }
      }}
    />
  );
};

export default GuidedTour; 