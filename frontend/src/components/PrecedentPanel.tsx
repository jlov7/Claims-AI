import React from "react";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  useToast,
  Spinner,
  Text,
  Heading,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Tag,
  Wrap,
  WrapItem,
  Alert,
  AlertIcon,
  Stack,
  StackDivider,
  Progress,
  Badge,
  useColorModeValue,
  Flex,
  Center,
  Skeleton,
  SkeletonText,
  Icon,
} from "@chakra-ui/react";
import { FiInbox, FiSearch } from "react-icons/fi";
import { Precedent } from "../models/precedent.ts";

export interface PrecedentPanelProps {
  precedents: Precedent[] | null;
  isLoading: boolean;
  error: string | null;
}

const PrecedentPanel: React.FC<PrecedentPanelProps> = ({
  precedents,
  isLoading,
  error,
}) => {
  const cardBg = useColorModeValue("white", "gray.700");
  const scoreColor = (score: number): string => {
    if (score > 0.85) return "green";
    if (score > 0.75) return "yellow";
    return "orange";
  };

  return (
    <Box
      borderWidth="2px"
      borderRadius="lg"
      p={6}
      height="100%"
      overflowY="auto"
      bg="white"
    >
      <Heading size="lg" mb={3}>
        Similar Case Precedents
      </Heading>
      <Text fontSize="md" color="gray.600" mb={6}>
        AI automatically finds similar past cases to help inform your
        decision-making. Ask questions in the chat panel to find relevant
        precedents.
      </Text>

      {isLoading && (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          {[...Array(4)].map((_, i) => (
            <Skeleton
              key={i}
              data-testid="precedent-skeleton"
              height="180px"
              borderRadius="md"
            />
          ))}
        </SimpleGrid>
      )}

      {error && (
        <Alert status="error" borderRadius="md" variant="subtle">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {!isLoading && !error && precedents && precedents.length > 0 && (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          {precedents.map((precedent, index) => {
            // Calculate similarity score safely
            const similarityScore = precedent.similarity_score || 0;

            return (
              <Card
                key={index}
                bg={cardBg}
                boxShadow="md"
                borderRadius="lg"
                borderLeftWidth="4px"
                borderLeftColor={scoreColor(similarityScore)}
                transition="transform 0.2s"
                _hover={{ transform: "translateY(-3px)" }}
              >
                <CardHeader pb={2}>
                  <Flex justify="space-between" align="center">
                    <Heading size="sm" fontWeight="bold">
                      Case #{precedent.claim_id || index}
                    </Heading>
                    <Badge
                      colorScheme={scoreColor(similarityScore)}
                      fontSize="sm"
                      px={2}
                      py={1}
                      borderRadius="full"
                    >
                      {Math.round(similarityScore * 100)}% Match
                    </Badge>
                  </Flex>
                </CardHeader>
                <CardBody pt={1}>
                  <Text fontSize="sm" fontWeight="medium" mb={2}>
                    {precedent.summary
                      ? precedent.summary.substring(0, 40) + "..."
                      : "Untitled Case"}
                  </Text>
                  <Text noOfLines={3} fontSize="sm" color="gray.600">
                    {precedent.summary || "No summary available"}
                  </Text>
                  <Wrap mt={3} spacing={2}>
                    {precedent.keywords &&
                      Array.isArray(precedent.keywords) &&
                      precedent.keywords.map((tag: string, idx: number) => (
                        <WrapItem key={idx}>
                          <Tag
                            size="sm"
                            colorScheme="brand"
                            borderRadius="full"
                          >
                            {tag}
                          </Tag>
                        </WrapItem>
                      ))}
                  </Wrap>
                </CardBody>
              </Card>
            );
          })}
        </SimpleGrid>
      )}

      {!isLoading && !error && (!precedents || precedents.length === 0) && (
        <Center
          height="200px"
          flexDirection="column"
          bg="gray.50"
          borderRadius="md"
          p={8}
          borderWidth="1px"
          borderColor="gray.200"
          borderStyle="dashed"
        >
          <Icon as={FiSearch} boxSize={10} color="gray.400" mb={4} />
          <Heading size="sm" color="gray.500" mb={2}>
            No Precedents Found
          </Heading>
          <Text color="gray.500" textAlign="center">
            Upload documents and ask questions in the chat panel to find
            relevant precedents.
          </Text>
        </Center>
      )}
    </Box>
  );
};

export default PrecedentPanel;
