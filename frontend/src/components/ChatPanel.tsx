import React, { useState, useRef, useEffect } from "react";
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
  Card,
  SkeletonText,
} from "@chakra-ui/react";
import { FaPlay, FaStop, FaSpinner } from "react-icons/fa6";
import {
  FiMessageSquare,
  FiThumbsUp,
  FiThumbsDown,
  FiCopy,
  FiRefreshCw,
  FiCheckCircle,
  FiAlertCircle,
  FiAlertTriangle,
  FiInfo,
  FiPlay as FiPlayCircle,
  FiStopCircle,
  FiLoader,
  FiUser,
  FiCpu,
} from "react-icons/fi";
import { askQuestion } from "../services/askService.ts";
import { generateSpeech } from "../services/speechService.ts";
import type { ChatMessage, SourceDocument } from "../models/chat.ts";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./CodeBlock.tsx";

// Helper function to determine glow color and icon based on confidence
const getConfidenceAttributes = (
  confidence: number | undefined,
): { color: string; icon: React.ElementType } => {
  if (confidence === undefined) return { color: "transparent", icon: FiInfo }; // Default or no score
  if (confidence >= 4) return { color: "green.500", icon: FiCheckCircle }; // High confidence
  if (confidence === 3) return { color: "yellow.500", icon: FiAlertTriangle }; // Medium confidence
  if (confidence <= 2) return { color: "red.500", icon: FiAlertCircle }; // Low confidence
  return { color: "transparent", icon: FiInfo };
};

// Tooltip labels
const confidenceTooltip =
  "Confidence Score indicates the AI's certainty (1-5): Green=High (4-5), Yellow=Medium (3), Red=Low (1-2)";
const selfHealTooltip =
  "Self-Healed: The AI detected low confidence in its initial answer and attempted to correct it.";

export interface ChatPanelProps {
  onNewAiAnswer?: (answerText: string) => void;
}

// Extend the interface locally for any missing fields
interface ExtendedChatMessage extends ChatMessage {
  isPlaying?: boolean;
  isHealing?: boolean;
  audioUrl?: string;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onNewAiAnswer }) => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === "true";
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessageConfidence, setLastMessageConfidence] = useState<
    number | null
  >(null);
  const toast = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [activeAudioMessageId, setActiveAudioMessageId] = useState<
    string | null
  >(null);
  const [isFetchingAudio, setIsFetchingAudio] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState<string | null>(null);

  const [showSourceForMessage, setShowSourceForMessage] = useState<
    string | null
  >(null);
  const { onCopy } = useClipboard("");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const currentAudioRef = audioRef.current;
    const handleAudioEnd = () => setIsPlayingAudio(null);
    currentAudioRef?.addEventListener("ended", handleAudioEnd);
    currentAudioRef?.addEventListener("error", handleAudioEnd);

    return () => {
      currentAudioRef?.removeEventListener("ended", handleAudioEnd);
      currentAudioRef?.removeEventListener("error", handleAudioEnd);
    };
  }, [audioRef.current]);

  const handlePlayAudio = async (message: ExtendedChatMessage) => {
    if (!message.text || message.sender === "user") return;

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
      audioRef.current.play().catch((e) => {
        console.error("Error playing audio:", e);
        toast({
          title: "Audio Playback Error",
          status: "error",
          duration: 3000,
        });
        setIsPlayingAudio(null);
      });
      setIsPlayingAudio(message.id);
    } else {
      setIsFetchingAudio(message.id);
      try {
        const speechResponse = await generateSpeech({ text: message.text });
        setMessages((prevs) =>
          prevs.map((m) =>
            m.id === message.id
              ? { ...m, audioUrl: speechResponse.audio_url }
              : m,
          ),
        );
        if (audioRef.current) {
          audioRef.current.src = speechResponse.audio_url;
          audioRef.current.play().catch((e) => {
            console.error("Error playing audio:", e);
            toast({
              title: "Audio Playback Error",
              status: "error",
              duration: 3000,
            });
            setIsPlayingAudio(null);
          });
          setIsPlayingAudio(message.id);
        }
      } catch (error) {
        console.error("Error fetching audio:", error);
        toast({
          title: "TTS Error",
          description: "Could not generate audio.",
          status: "error",
          duration: 3000,
        });
      } finally {
        setIsFetchingAudio(null);
      }
    }
  };

  const handleSendMessage = async () => {
    const userMessage = inputValue.trim();
    if (!userMessage || isLoading) return;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: uuidv4(), text: userMessage, sender: "user" },
    ]);
    setInputValue("");
    setIsLoading(true);
    setError(null);
    setLastMessageConfidence(null); // Clear confidence before new message

    // Add temporary AI thinking message
    const thinkingMessageId = uuidv4();
    setMessages((prev) => [
      ...prev,
      {
        text: "",
        sender: "ai",
        isLoading: true,
        id: thinkingMessageId,
      },
    ]);

    try {
      const response = await askQuestion(userMessage);

      // Update thinking message with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingMessageId
            ? {
                ...msg,
                text: response.answer,
                sources: response.sources,
                confidence_score: response.confidence_score,
                self_heal_attempts: response.self_heal_attempts,
                isLoading: false,
              }
            : msg,
        ),
      );
      setLastMessageConfidence(response.confidence_score ?? null);
      if (onNewAiAnswer && response.answer) {
        onNewAiAnswer(response.answer);
      }
    } catch (err: any) {
      console.error("Error fetching RAG response:", err);
      setError("Failed to get response from the backend.");
      // Update thinking message to show error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingMessageId
            ? {
                ...msg,
                text: "Error fetching response.",
                isLoading: false,
                error: true,
              }
            : msg,
        ),
      );
      setLastMessageConfidence(null);
      toast({
        title: "Error",
        description: err.message || "Could not get answer.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingMessageId ? { ...msg, isLoading: false } : msg,
        ),
      );
      setIsLoading(false);
    }
  };

  const userMessageBg = useColorModeValue("brand.500", "brand.300");
  const aiMessageBg = useColorModeValue("gray.50", "gray.700");
  const inputBg = useColorModeValue("white", "gray.700");
  const borderColor = useColorModeValue("gray.200", "gray.600");

  const stopSpeaking = (messageId: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlayingAudio(null);
    }
  };

  const speakText = (text: string, messageId: string) => {
    // Reuse existing handlePlayAudio function
    const message = messages.find((m) => m.id === messageId);
    if (message) {
      handlePlayAudio(message);
    }
  };

  const toggleSourcesForMessage = (messageId: string) => {
    if (showSourceForMessage === messageId) {
      setShowSourceForMessage(null);
    } else {
      setShowSourceForMessage(messageId);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const isAnySpeaking = isPlayingAudio !== null;

  return (
    <Card
      borderWidth="2px"
      borderRadius="lg"
      p={6}
      height="500px"
      display="flex"
      flexDirection="column"
      id="tour-chat-panel"
      className="tour-highlightable"
      bg="white"
      boxShadow="md"
    >
      <Heading size="lg" mb={4} color="brand.600">
        Ask About Documents
      </Heading>
      <Text fontSize="md" color="gray.600" mb={4}>
        Ask questions about your uploaded documents to get AI-powered insights
        and answers.
      </Text>

      {/* Add confidence score explainer */}
      <Alert status="info" mb={4} borderRadius="md" variant="subtle">
        <AlertIcon />
        <Box>
          <Text fontWeight="bold">Confidence Scoring System</Text>
          <Text fontSize="sm">
            AI answers include a confidence score (1-5) with color indicators:
            <Badge colorScheme="green" mx={1}>
              Green (4-5)
            </Badge>
            <Badge colorScheme="yellow" mx={1}>
              Yellow (3)
            </Badge>
            <Badge colorScheme="red" mx={1}>
              Red (1-2)
            </Badge>
            Low scores trigger automatic self-healing to improve answers.
          </Text>
        </Box>
      </Alert>

      <Flex direction="column" height="calc(100% - 130px)">
        {/* Messages container */}
        <Box
          flex="1"
          overflowY="auto"
          mb={4}
          p={3}
          borderWidth="1px"
          borderColor={borderColor}
          borderRadius="md"
          bg={aiMessageBg}
        >
          {messages.length === 0 ? (
            <Center height="100%" flexDirection="column">
              <Icon as={FiMessageSquare} boxSize={10} color="gray.300" mb={3} />
              <Text color="gray.500" fontWeight="medium">
                No messages yet
              </Text>
              <Text color="gray.400" fontSize="sm">
                Ask a question about your uploaded documents
              </Text>
            </Center>
          ) : (
            <VStack spacing={4} align="stretch">
              {messages.map((message: ExtendedChatMessage, index: number) => (
                <Box
                  key={message.id}
                  alignSelf={
                    message.sender === "user" ? "flex-end" : "flex-start"
                  }
                  maxWidth="85%"
                  className={
                    message.sender === "ai" ? "ai-message" : "user-message"
                  }
                >
                  <Flex
                    direction={
                      message.sender === "user" ? "row-reverse" : "row"
                    }
                    alignItems="flex-start"
                  >
                    {/* Message avatar/icon */}
                    <Box
                      mr={message.sender === "user" ? 0 : 2}
                      ml={message.sender === "user" ? 2 : 0}
                    >
                      <Icon
                        as={message.sender === "user" ? FiUser : FiCpu}
                        boxSize={6}
                        color={
                          message.sender === "user" ? "brand.500" : "gray.500"
                        }
                        bg={message.sender === "user" ? "white" : "white"}
                        p={1}
                        borderRadius="full"
                        borderWidth="1px"
                        borderColor={borderColor}
                      />
                    </Box>

                    {/* Message content */}
                    <Box
                      bg={message.sender === "user" ? userMessageBg : "white"}
                      color={message.sender === "user" ? "white" : "black"}
                      px={4}
                      py={3}
                      borderRadius="lg"
                      borderColor={
                        message.sender === "ai"
                          ? message.isHealing
                            ? "purple.500"
                            : getConfidenceAttributes(message.confidence_score)
                                .color
                          : "transparent"
                      }
                      boxShadow={
                        message.sender === "ai" &&
                        (message.isHealing
                          ? "purple.500"
                          : getConfidenceAttributes(message.confidence_score)
                              .color) !== "transparent"
                          ? `0 0 0 3px ${message.isHealing ? "purple.500" : getConfidenceAttributes(message.confidence_score).color}`
                          : "sm"
                      }
                    >
                      {/* Message text content */}
                      {message.sender === "ai" && (
                        <>
                          <Flex justify="space-between" mb={2}>
                            <Tooltip
                              label={confidenceTooltip}
                              aria-label="Confidence score tooltip"
                              placement="top"
                            >
                              <Tag
                                size="md"
                                colorScheme={
                                  message.confidence_score
                                    ? message.confidence_score >= 4
                                      ? "green"
                                      : message.confidence_score >= 3
                                        ? "yellow"
                                        : "red"
                                    : "gray"
                                }
                                px={3}
                                py={2}
                                borderRadius="md"
                              >
                                <TagLeftIcon
                                  boxSize="5"
                                  as={
                                    getConfidenceAttributes(
                                      message.confidence_score,
                                    ).icon
                                  }
                                />
                                <TagLabel fontWeight="bold">
                                  Confidence:{" "}
                                  {message.confidence_score || "N/A"}/5
                                </TagLabel>
                              </Tag>
                            </Tooltip>
                            <HStack>
                              {isPlayingAudio === message.id ? (
                                <IconButton
                                  aria-label="Stop speaking"
                                  icon={<FiStopCircle />}
                                  size="xs"
                                  onClick={() => stopSpeaking(message.id)}
                                  variant="ghost"
                                />
                              ) : (
                                <IconButton
                                  aria-label="Speak answer"
                                  icon={<FiPlayCircle />}
                                  size="xs"
                                  onClick={() =>
                                    speakText(message.text, message.id)
                                  }
                                  isDisabled={isAnySpeaking}
                                  variant="ghost"
                                />
                              )}
                              <IconButton
                                aria-label="Copy to clipboard"
                                icon={<FiCopy />}
                                size="xs"
                                onClick={() => onCopy(message.text)}
                                variant="ghost"
                              />
                            </HStack>
                          </Flex>

                          {message.self_heal_attempts &&
                            message.self_heal_attempts > 0 && (
                              <Tooltip
                                label={selfHealTooltip}
                                aria-label="Self healing tooltip"
                                placement="top"
                              >
                                <Alert
                                  status="info"
                                  size="sm"
                                  mb={3}
                                  borderRadius="md"
                                  variant="left-accent"
                                >
                                  <AlertIcon />
                                  <Text fontSize="sm">
                                    This answer was improved through{" "}
                                    {message.self_heal_attempts} self-healing
                                    attempt
                                    {message.self_heal_attempts !== 1
                                      ? "s"
                                      : ""}
                                  </Text>
                                </Alert>
                              </Tooltip>
                            )}
                        </>
                      )}

                      {/* Render text content with Markdown support */}
                      <Box className="message-content">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({
                              node,
                              inline,
                              className,
                              children,
                              ...props
                            }: any) {
                              const match = /language-(\w+)/.exec(
                                className || "",
                              );
                              return !inline && match ? (
                                <CodeBlock
                                  language={match[1]}
                                  value={String(children).replace(/\n$/, "")}
                                  {...props}
                                />
                              ) : (
                                <Code className={className} {...props}>
                                  {children}
                                </Code>
                              );
                            },
                          }}
                        >
                          {message.text}
                        </ReactMarkdown>
                      </Box>

                      {/* Show sources if available */}
                      {message.sender === "ai" &&
                        message.sources &&
                        message.sources.length > 0 && (
                          <Box mt={3}>
                            <Text
                              fontSize="xs"
                              fontWeight="bold"
                              color="gray.500"
                              mb={1}
                            >
                              Sources:
                            </Text>
                            <Collapse
                              in={showSourceForMessage === message.id}
                              animateOpacity
                            >
                              <VStack
                                spacing={2}
                                align="stretch"
                                mt={1}
                                fontSize="xs"
                              >
                                {message.sources.map((source, i) => (
                                  <Box
                                    key={i}
                                    p={2}
                                    borderRadius="md"
                                    bg="gray.50"
                                    fontSize="xs"
                                    borderWidth="1px"
                                    borderColor={borderColor}
                                  >
                                    <Text fontWeight="bold">
                                      {source.file_name || "Unknown"}{" "}
                                      {source.metadata?.score !== undefined &&
                                        `(Relevance: ${Math.round(source.metadata.score * 100)}%)`}
                                    </Text>
                                    <Text
                                      noOfLines={2}
                                      fontSize="xs"
                                      color="gray.600"
                                    >
                                      {source.page_content ||
                                        "No content available"}
                                    </Text>
                                  </Box>
                                ))}
                              </VStack>
                            </Collapse>
                            <Button
                              variant="link"
                              size="xs"
                              onClick={() =>
                                toggleSourcesForMessage(message.id)
                              }
                              mt={1}
                              color="brand.500"
                            >
                              {showSourceForMessage === message.id
                                ? "Hide Sources"
                                : "Show Sources"}
                            </Button>
                          </Box>
                        )}

                      {/* Self-healing note if applicable */}
                      {message.sender === "ai" && message.isHealing && (
                        <Alert status="info" size="sm" mt={2} borderRadius="md">
                          <AlertIcon />
                          <Text fontSize="xs">
                            This answer was improved using AI self-correction
                          </Text>
                        </Alert>
                      )}
                    </Box>
                  </Flex>
                </Box>
              ))}
            </VStack>
          )}
        </Box>

        {/* Input area */}
        <Box id="tour-chat-input-area" className="tour-highlightable">
          <form onSubmit={handleSubmit}>
            <Flex>
              <Input
                placeholder="Ask a question about your documents..."
                value={inputValue}
                onChange={handleInputChange}
                size="lg"
                borderRadius="md"
                bg={inputBg}
                focusBorderColor="brand.500"
                disabled={isLoading}
                mr={2}
                p={6}
              />
              <Button
                type="submit"
                isLoading={isLoading}
                loadingText=""
                colorScheme="brand"
                size="lg"
              >
                Send
              </Button>
            </Flex>
            {error && (
              <Alert status="error" mt={2} size="sm" borderRadius="md">
                <AlertIcon />
                {error}
              </Alert>
            )}
          </form>
        </Box>
      </Flex>
    </Card>
  );
};

export default ChatPanel;
