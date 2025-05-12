import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidProps {
  chart: string; // The Mermaid chart definition
}

// Initialize Mermaid once
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral', // Or choose another theme like 'default', 'forest', 'dark'
  securityLevel: 'loose', // Be mindful of security implications if chart definitions come from untrusted sources
  fontFamily: 'sans-serif',
});

const MermaidChart: React.FC<MermaidProps> = ({ chart }) => {
  const mermaidDivRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mermaidDivRef.current && chart) {
      // Clear previous render
      mermaidDivRef.current.innerHTML = '';
      // Insert the new chart definition
      mermaidDivRef.current.insertAdjacentHTML('beforeend', chart);
      try {
        // Render the chart
        mermaid.run({
          nodes: [mermaidDivRef.current],
        });
      } catch (e) {
        console.error('Error rendering Mermaid chart:', e);
        // Optionally display an error message in the div
        if (mermaidDivRef.current) {
            mermaidDivRef.current.innerHTML = 'Error rendering diagram.';
        }
      }
    }
  }, [chart]); // Re-run the effect if the chart definition changes

  return <div ref={mermaidDivRef} className="mermaid-diagram-container"></div>;
};

export default MermaidChart; 