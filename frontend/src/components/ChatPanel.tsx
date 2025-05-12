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
} from '@chakra-ui/react';
import { FaPlay, FaStop, FaSpinner } from 'react-icons/fa6';
import { FiMessageSquare, FiThumbsUp, FiThumbsDown, FiCopy, FiRefreshCw } from 'react-icons/fi';
import { askQuestion } from '../services/askService.js';
import { type AskRequest, type AskResponse, ChatMessage, SourceDocument } from '../models/chat.js';
import { generateSpeech } from '../services/speechService.js';
import { v4 as uuidv4 } from 'uuid';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// import ReactMarkdown from 'react-markdown'; // Will add later
// import remarkGfm from 'remark-gfm'; // Will add later

// Helper function to determine glow color based on confidence
const getConfidenceColor = (confidence: number | undefined): string => {
  if (confidence === undefined) return 'transparent';
  if (confidence >= 4) return 'green.500'; // High confidence
  if (confidence === 3) return 'yellow.500'; // Medium confidence
  if (confidence <= 2) return 'red.500'; // Low confidence
  return 'transparent';
};

const ChatPanel: React.FC = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
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

  const handleSend = async () => {
    if (!input.trim()) return;
    const currentInput = input.trim();
    setInput("");
    if (isE2E) {
      // E2E stub: add user and dummy AI response in one go
      const userMessage: ChatMessage = { id: uuidv4(), text: currentInput, sender: 'user' };
      const aiMessage: ChatMessage = {
        id: uuidv4(),
        text: 'This is a dummy answer.',
        sender: 'ai',
        sources: [{ file_name: 'sample.pdf', chunk_id: 0 }],
        confidence: 5,
        isLoading: false,
      };
      setMessages(prev => [...prev, userMessage, aiMessage]);
      return;
    }

    const userMessage: ChatMessage = {
      id: uuidv4(),
      text: currentInput,
      sender: "user",
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setIsSending(true);

    const aiLoadingMessageId = uuidv4();
    const aiLoadingMessage: ChatMessage = {
      id: aiLoadingMessageId,
      text: "",
      sender: "ai",
      isLoading: true,
    };
    setMessages((prevMessages) => [...prevMessages, aiLoadingMessage]);

    try {
      const response = await askQuestion(currentInput);
      const aiResponseMessage: ChatMessage = {
        id: aiLoadingMessageId,
        text: response.answer,
        sender: "ai",
        sources: response.sources,
        confidence: response.confidence_score,
        isLoading: false,
        // Placeholder: Logic to determine if self-healing is active
        // e.g., if (response.confidence_score < 3 && response.is_self_healing_attempted) {
        //   aiResponseMessage.isHealing = true; 
        //   // Optionally, you might want a different message text here, 
        //   // or the backend might send a specific "healing in progress" message.
        // }
      };
      setMessages((prevMessages) => 
        prevMessages.map(msg => msg.id === aiLoadingMessageId ? aiResponseMessage : msg)
      );
    } catch (error: any) {
      const errorMessage = error.message || "An unexpected error occurred.";
      toast({
        title: "Error fetching AI response.",
        description: errorMessage,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      const aiErrorMessage: ChatMessage = {
        id: aiLoadingMessageId,
        text: `Error: ${errorMessage}`,
        sender: "ai",
        isLoading: false,
        error: errorMessage,
      };
      setMessages((prevMessages) => 
        prevMessages.map(msg => msg.id === aiLoadingMessageId ? aiErrorMessage : msg)
      );
    } finally {
      setIsSending(false);
    }
  };

  // Temporary test functions
  const modifyLastAiMessage = (confidence: number, isHealing: boolean) => {
    setMessages(prevMessages => {
      const lastAiMsgIndex = prevMessages.slice().reverse().findIndex(m => m.sender === 'ai' && !m.isLoading);
      if (lastAiMsgIndex === -1) return prevMessages;
      const actualIndex = prevMessages.length - 1 - lastAiMsgIndex;
      
      const updatedMessages = [...prevMessages];
      updatedMessages[actualIndex] = {
        ...updatedMessages[actualIndex],
        confidence: confidence,
        isHealing: isHealing,
        // Ensure text is not empty for healing display
        text: updatedMessages[actualIndex].text || "(Test healing on empty message)", 
      };
      return updatedMessages;
    });
  };

  const handleTestLowConfidenceHealing = () => modifyLastAiMessage(1, true);
  const handleTestMediumConfidence = () => modifyLastAiMessage(3, false);
  const handleTestHighConfidence = () => modifyLastAiMessage(5, false);
  // End temporary test functions

  return (
    <VStack spacing={4} align="stretch" h="100%">
      <Box 
        id="tour-chat-messages-area" // ID for tour
        flex={1} 
        overflowY="auto" 
        p={4} 
        borderWidth="1px" 
        borderRadius="md"
      >
        {messages.map((message, index) => (
          <Box key={message.id || index} className={
              message.sender === 'ai' ? 'chat-message-ai' : 'chat-message-user'
            } w="100%" mb={3}>
            <Flex direction={message.sender === 'user' ? 'row-reverse' : 'row'}>
              <Box
                bg={message.sender === 'user' ? 'blue.500' : 'gray.100'}
                color={message.sender === 'user' ? 'white' : 'black'}
                px={4}
                py={2}
                borderRadius="lg"
                maxWidth="70%"
                borderColor={message.sender === 'ai' && message.confidence !== undefined ? getConfidenceColor(message.confidence) : 'transparent'}
                boxShadow={message.sender === 'ai' && message.confidence !== undefined ? `0 0 8px 1px ${getConfidenceColor(message.confidence)}` : 'none'}
                borderWidth={message.sender === 'ai' && message.confidence !== undefined ? "2px" : "0px"}
              >
                <Text whiteSpace="pre-wrap">{message.text}</Text>
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
                {message.sender === 'ai' && message.confidence !== undefined && (
                  <Text mt={1} fontSize="xs" color={getConfidenceColor(message.confidence)} fontWeight="medium">
                    Confidence: {message.confidence}/5
                  </Text>
                )}
                {message.sender === 'ai' && !message.isLoading && (
                    <IconButton 
                        aria-label={isPlayingAudio === message.id ? "Stop speech" : "Play speech"}
                        icon={isFetchingAudio === message.id ? <Spinner size="xs" /> : isPlayingAudio === message.id ? <FaStop /> : <FaPlay />}
                        size="xs"
                        variant="ghost"
                        onClick={() => handlePlayAudio(message)}
                        isDisabled={isFetchingAudio === message.id}
                        mt={1}
                        ml={1}
                        id={`tour-voice-over-button-${message.id}`} // Dynamic ID for tour, harder to target first one
                    />
                )}
              </Box>
            </Flex>
            {message.error && (
              <Text color="red.500" fontSize="sm" mt={1} textAlign={message.sender === 'user' ? "right" : "left"}>
                Error: {message.error}
              </Text>
            )}
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>
      <Flex mt={1} id="tour-chat-input-area"> {/* ID for tour */}
        <Textarea
          id="tour-chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents..."
          mr={2}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <Button onClick={handleSend} colorScheme="blue" isLoading={isSending}>
          Send
        </Button>
      </Flex>
      <audio ref={audioRef} />
    </VStack>
  );
};

export default ChatPanel; 