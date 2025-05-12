import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidProps {
  chart: string;
}

let chartIdCounter = 0;

const MermaidChart: React.FC<MermaidProps> = ({ chart }) => {
  const ref = useRef<HTMLDivElement>(null);
  const chartId = useRef(`mermaid-chart-${chartIdCounter++}`);

  useEffect(() => {
    if (ref.current) {
      mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose', fontFamily: 'sans-serif' });
      mermaid.render(chartId.current, chart)
        .then(({ svg }) => {
          ref.current!.innerHTML = svg;
        })
        .catch((e) => {
          ref.current!.innerHTML = 'Error rendering diagram.';
          console.error('Error rendering Mermaid chart:', e);
        });
    }
  }, [chart]);

  return <div ref={ref} className="mermaid-diagram-container"></div>;
};

export default MermaidChart; 