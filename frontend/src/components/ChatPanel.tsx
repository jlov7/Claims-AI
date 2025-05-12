import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Button,
  Flex,
  Input,
  VStack,
  Text,
  useToast,
  Spinner,
  Tag,
  Textarea,
  Code,
  Wrap,
  WrapItem,
  IconButton,
  Icon,
  CircularProgress,
  TagLabel,
  TagLeftIcon,
  HStack,
  Tooltip,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Kbd,
  useClipboard,
  BoxProps,
  Collapse,
  Badge,
  useColorModeValue,
  Heading,
  Center,
} from '@chakra-ui/react';
import { FaPlay, FaStop, FaSpinner } from 'react-icons/fa6';
import { FiMessageSquare, FiThumbsUp, FiThumbsDown, FiCopy, FiRefreshCw, FiCheckCircle, FiAlertCircle, FiAlertTriangle, FiInfo, FiPlay as FiPlayCircle, FiStopCircle, FiLoader } from 'react-icons/fi';
import { askQuestion } from '../services/askService.ts';
import { type AskRequest, type AskResponse, ChatMessage, SourceDocument } from '../models/chat.ts';
import { generateSpeech } from '../services/speechService.js';
import { v4 as uuidv4 } from 'uuid';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from './CodeBlock.tsx';

// Helper function to determine glow color and icon based on confidence
const getConfidenceAttributes = (confidence: number | undefined): { color: string, icon: React.ElementType } => {
  if (confidence === undefined) return { color: 'transparent', icon: FiInfo }; // Default or no score
  if (confidence >= 4) return { color: 'green.500', icon: FiCheckCircle }; // High confidence
  if (confidence === 3) return { color: 'yellow.500', icon: FiAlertTriangle }; // Medium confidence
  if (confidence <= 2) return { color: 'red.500', icon: FiAlertCircle }; // Low confidence
  return { color: 'transparent', icon: FiInfo };
};

// Tooltip labels
const confidenceTooltip = "Confidence Score indicates the AI's certainty (1-5): Green=High (4-5), Yellow=Medium (3), Red=Low (1-2)";
const selfHealTooltip = "Self-Healed: The AI detected low confidence in its initial answer and attempted to correct it.";

export interface ChatPanelProps {
  onNewAiAnswer?: (answerText: string) => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onNewAiAnswer }) => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessageConfidence, setLastMessageConfidence] = useState<number | null>(null);
  const toast = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [activeAudioMessageId, setActiveAudioMessageId] = useState<string | null>(null);
  const [isFetchingAudio, setIsFetchingAudio] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const currentAudioRef = audioRef.current;
    const handleAudioEnd = () => setIsPlayingAudio(null);
    currentAudioRef?.addEventListener('ended', handleAudioEnd);
    currentAudioRef?.addEventListener('error', handleAudioEnd);

    return () => {
      currentAudioRef?.removeEventListener('ended', handleAudioEnd);
      currentAudioRef?.removeEventListener('error', handleAudioEnd);
    };
  }, [audioRef.current]);

  const handlePlayAudio = async (message: ChatMessage) => {
    if (!message.text || message.sender === 'user') return;

    if (isPlayingAudio === message.id && audioRef.current) {
      audioRef.current.pause();
      setIsPlayingAudio(null);
      return;
    }
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      setIsPlayingAudio(null);
    }

    setActiveAudioMessageId(message.id);

    if (message.audioUrl && audioRef.current) {
      audioRef.current.src = message.audioUrl;
      audioRef.current.play().catch(e => {
        console.error("Error playing audio:", e);
        toast({ title: 'Audio Playback Error', status: 'error', duration: 3000 });
        setIsPlayingAudio(null);
      });
      setIsPlayingAudio(message.id);
    } else {
      setIsFetchingAudio(message.id);
      try {
        const speechResponse = await generateSpeech({ text: message.text });
        setMessages(prevs => prevs.map(m => m.id === message.id ? { ...m, audioUrl: speechResponse.audio_url } : m));
        if (audioRef.current) {
          audioRef.current.src = speechResponse.audio_url;
          audioRef.current.play().catch(e => {
            console.error("Error playing audio:", e);
            toast({ title: 'Audio Playback Error', status: 'error', duration: 3000 });
            setIsPlayingAudio(null);
          });
          setIsPlayingAudio(message.id);
        }
      } catch (error) {
        console.error('Error fetching audio:', error);
        toast({ title: 'TTS Error', description: 'Could not generate audio.', status: 'error', duration: 3000 });
      } finally {
        setIsFetchingAudio(null);
      }
    }
  };

  const handleSendMessage = async () => {
    const userMessage = inputValue.trim();
    if (!userMessage || isLoading) return;

    // Add user message
    setMessages(prev => [...prev, { id: uuidv4(), text: userMessage, sender: 'user' }]);
    setInputValue('');
    setIsLoading(true);
    setError(null);
    setLastMessageConfidence(null); // Clear confidence before new message

    // Add temporary AI thinking message
    const thinkingMessageId = uuidv4(); // Use uuid for string id
    setMessages(prev => [
      ...prev,
      {
        text: '', // Placeholder for spinner/text
        sender: 'ai',
        isLoading: true,
        id: thinkingMessageId,
      },
    ]);

    try {
      const response = await askQuestion(userMessage); // Corrected: pass only the string

      // Update thinking message with actual response
      setMessages(prev =>
        prev.map(msg =>
          msg.id === thinkingMessageId // Comparison is now string vs string
            ? {
                ...msg,
                text: response.answer,
                sources: response.sources, // Use 'sources' from response
                confidence_score: response.confidence_score,
                self_heal_attempts: response.self_heal_attempts, // Add self-heal attempts
                isLoading: false, // Mark as loaded
              }
            : msg
        )
      );
      setLastMessageConfidence(response.confidence_score ?? null);
      if (onNewAiAnswer && response.answer) {
        onNewAiAnswer(response.answer);
      }
    } catch (err: any) {
      console.error('Error fetching RAG response:', err);
      setError('Failed to get response from the backend.');
       // Update thinking message to show error
       setMessages(prev =>
        prev.map(msg =>
          msg.id === thinkingMessageId // Comparison is now string vs string
            ? { ...msg, text: 'Error fetching response.', isLoading: false, error: true } // Use 'error' field, static text
            : msg
        )
      );
      setLastMessageConfidence(null);
      toast({ title: 'Error', description: err.message || 'Could not get answer.', status: 'error', duration: 3000, isClosable: true });
    } finally {
      // Remove isLoading flag from the specific message if it wasn't updated (e.g., error occurred before response)
      // Or ensure isLoading is set false in both try/catch blocks for the specific message
       setMessages(prev =>
        prev.map(msg =>
          msg.id === thinkingMessageId ? { ...msg, isLoading: false } : msg // Comparison is now string vs string
        )
      );
      setIsLoading(false); // Overall loading state
    }
  };

  const userMessageBg = useColorModeValue('blue.50', 'blue.900');
  const aiMessageBg = useColorModeValue('gray.100', 'gray.700');

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} height="500px" display="flex" flexDirection="column" id="tour-chat-panel">
      <Heading size="md" mb={1}>Ask About Documents (RAG)</Heading>
      <Text fontSize="sm" color="gray.600" mb={3}>
        Chat with the AI to get answers based on uploaded documents.
      </Text>
      <Box flexGrow={1} overflowY="auto" ref={messagesEndRef} mb={4} pr={2}>
        <VStack spacing={4} align="stretch">
          {messages.length === 0 && !isLoading && (
            <Center h="100%" flexDirection="column">
              <Icon as={FiMessageSquare} boxSize="40px" color="gray.400" mb={3} />
              <Text color="gray.500">Ask a question to start the chat.</Text>
            </Center>
          )}
          {messages.map((message, index) => (
            <Box
              key={message.id}
              alignSelf={message.sender === 'user' ? 'flex-end' : 'flex-start'}
              bg={message.sender === 'user' ? userMessageBg : aiMessageBg}
              p={3}
              borderRadius="lg"
              maxWidth="80%"
              boxShadow={message.sender === 'ai' ? getConfidenceAttributes(message.confidence_score).color : 'sm'}
              sx={{
                animation: message.sender === 'ai' ? `aiMessageFadeIn 0.5s ease-out` : 'none',
                '@keyframes aiMessageFadeIn': {
                  from: { opacity: 0, transform: 'translateY(10px)' },
                  to: { opacity: 1, transform: 'translateY(0)' },
                },
              }}
              className={message.sender === 'ai' ? 'ai-message' : 'user-message'}
            >
              <Flex direction={message.sender === 'user' ? 'row-reverse' : 'row'}>
                <Box
                  bg={message.sender === 'user' ? userMessageBg : aiMessageBg}
                  color={message.sender === 'user' ? 'white' : 'black'}
                  px={4}
                  py={2}
                  borderRadius="lg"
                  maxWidth="70%"
                  borderColor={message.sender === 'ai' ? (message.isHealing ? 'purple.500' : getConfidenceAttributes(message.confidence_score).color) : 'transparent'}
                  boxShadow={message.sender === 'ai' && (message.isHealing ? 'purple.500' : getConfidenceAttributes(message.confidence_score).color) !== 'transparent' ? `0 0 8px 1px ${message.isHealing ? 'purple.500' : getConfidenceAttributes(message.confidence_score).color}` : 'none'}
                  borderWidth={message.sender === 'ai' && (message.isHealing ? 'purple.500' : getConfidenceAttributes(message.confidence_score).color) !== 'transparent' ? '2px' : '0px'}
                >
                  <Box className="markdown-content" sx={{ '& p': { mb: 2 }, '& ul': { ml: 4, mb: 2 }, '& ol': { ml: 4, mb: 2 } }}>
                    <ReactMarkdown
                      children={message.text}
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code(props: any) { // Using any for simplicity, can refine later if needed
                          const { children, className, node, ...rest } = props;
                          const match = /language-(\w+)/.exec(className || '');
                          return match ? (
                            <CodeBlock language={match[1]} value={String(children).replace(/\n$/, '')} {...rest} />
                          ) : (
                            <Code className={className} {...rest}>
                              {children}
                            </Code>
                          );
                        },
                      }}
                    />
                  </Box>
                  {message.sender === 'ai' && message.sources && message.sources.length > 0 && (
                    <Box mt={2} fontSize="sm">
                      <Text fontWeight="bold">Sources:</Text>
                      {message.sources.map((source, idx) => (
                        <span className="chakra-tag" key={idx} title={`${source.file_name}, Chunk: ${source.chunk_id}`} style={{ margin: '0 4px 4px 0', padding: '0.25em 0.5em', backgroundColor: '#EDF2F7', borderRadius: '0.25em', fontSize: '0.75rem', display: 'inline-block' }}>
                          {source.file_name ? source.file_name.substring(0, 20) + '...' : 'Source ' + (idx + 1)}
                        </span>
                      ))}
                    </Box>
                  )}
                  {message.sender === 'ai' && message.confidence_score !== undefined && (
                    <Tooltip label={confidenceTooltip} placement="top" hasArrow>
                      <HStack mt={1} spacing={1} id={`tour-confidence-${message.id}`}>
                        <Icon as={getConfidenceAttributes(message.confidence_score).icon} color={getConfidenceAttributes(message.confidence_score).color} />
                        <Text fontSize="xs" color={getConfidenceAttributes(message.confidence_score).color} fontWeight="medium">
                          Confidence: {message.confidence_score}/5
                        </Text>
                      </HStack>
                    </Tooltip>
                  )}
                  {message.isHealing && (
                    <Tooltip label={selfHealTooltip} placement="top" hasArrow>
                      <Tag size="sm" colorScheme="purple" mt={2} variant="subtle">
                        <TagLeftIcon as={FiRefreshCw} />
                        <TagLabel>Self-healed {message.self_heal_attempts ? `(${message.self_heal_attempts})` : ''}</TagLabel>
                      </Tag>
                    </Tooltip>
                  )}
                  {message.sender === 'ai' && !message.isLoading && message.text && (
                    <IconButton 
                      aria-label={isPlayingAudio === message.id ? "Stop speech" : "Play speech"}
                      icon={isFetchingAudio === message.id ? <Spinner size="xs" /> : isPlayingAudio === message.id ? <FaStop /> : <FaPlay />}
                      size="xs"
                      variant="ghost"
                      onClick={() => handlePlayAudio(message)}
                      isDisabled={isFetchingAudio === message.id}
                      mt={1}
                      ml={1}
                      id={`tour-voice-over-button-${message.id}`}
                    />
                  )}
                </Box>
              </Flex>
              {message.error && (
                <Text color="red.500" fontSize="sm" mt={1} textAlign={message.sender === 'user' ? "right" : "left"}>
                  Error: Failed to load response.
                </Text>
              )}
            </Box>
          ))}
        </VStack>
      </Box>
      <Flex mt={1} id="tour-chat-input-area">
        <Tooltip label="Type your question about the uploaded documents here. Press Enter to send." placement="top" hasArrow>
          <Textarea
            id="tour-chat-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question about your documents..."
            mr={2}
            rows={1} // Keep it compact initially
            resize="none" // Prevent manual resize
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
        </Tooltip>
        <Tooltip label="Send your question to the AI." placement="top" hasArrow>
          <Button onClick={handleSendMessage} colorScheme="blue" isLoading={isLoading}>
            Send
          </Button>
        </Tooltip>
      </Flex>
      <audio ref={audioRef} />
    </Box>
  );
};

export default ChatPanel;
