import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'; // Choose a style
import { Box, IconButton, useClipboard, Tooltip } from '@chakra-ui/react';
import { FiCopy } from 'react-icons/fi';

interface CodeBlockProps {
  language: string;
  value: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, value }) => {
  const { hasCopied, onCopy } = useClipboard(value);

  return (
    <Box position="relative" my={4}>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        showLineNumbers={false} // Optional: show line numbers
        customStyle={{ 
          borderRadius: '0.375rem', // Match Chakra md border radius
          padding: '1rem', 
          margin: 0, // Remove default margin
          fontSize: '0.875em' // Slightly smaller font
        }}
        wrapLines={true}
        wrapLongLines={true}
      >
        {value}
      </SyntaxHighlighter>
      <Tooltip label={hasCopied ? 'Copied!' : 'Copy code'} placement="top" hasArrow>
        <IconButton
          aria-label="Copy code"
          icon={<FiCopy />}
          size="sm"
          position="absolute"
          top="0.5rem"
          right="0.5rem"
          onClick={onCopy}
          variant="ghost"
          color="gray.400"
          _hover={{ color: 'white', bg: 'rgba(255,255,255,0.1)' }}
        />
      </Tooltip>
    </Box>
  );
};

// Default export might not be needed if named export is used consistently
// export default CodeBlock; 