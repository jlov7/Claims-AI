import React from 'react';
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
  Card, CardHeader, CardBody, Tag, Wrap, WrapItem,
  Alert,
  AlertIcon,
  Stack,
  StackDivider,
  Progress,
  Badge,
  useColorModeValue,
  Flex,
  Center
} from '@chakra-ui/react';
import { Precedent } from '../models/precedent.ts';

export interface PrecedentPanelProps {
  precedents: Precedent[] | null;
  isLoading: boolean;
  error: string | null;
}

const PrecedentPanel: React.FC<PrecedentPanelProps> = ({ precedents, isLoading, error }) => {
  const cardBg = useColorModeValue('white', 'gray.700');
  const scoreColor = (score: number): string => {
    if (score > 0.85) return 'green';
    if (score > 0.75) return 'yellow';
    return 'orange';
  };

  return (
    <Box 
      borderWidth="1px" 
      borderRadius="lg" 
      p={4} 
      height="100%" 
      overflowY="auto"
      id="tour-precedent-panel"
    >
      <Heading size="md" mb={1}>Nearest Precedents (based on chat)</Heading>
      <Text fontSize="sm" color="gray.600" mb={3}>
        Automatically finds similar past claims based on the current chat context.
      </Text>
      {isLoading && (
        <VStack justify="center" align="center" height="100%">
          <Spinner size="lg" />
          <Text>Finding similar precedents...</Text>
        </VStack>
      )}
      {error && (
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      )}
      {!isLoading && !error && (!precedents || precedents.length === 0) && (
        <Center height="100px">
           <Text color="gray.500">No precedents available to display.</Text>
        </Center>
      )}
      {!isLoading && !error && precedents && precedents.length > 0 && (
        <VStack spacing={4} align="stretch">
          {precedents.map((p, index) => (
            <Card key={p.claim_id || index} variant="outline" bg={cardBg} size="sm">
              <CardHeader pb={1}> 
                <Heading size='xs' textTransform='uppercase'>
                  Precedent ID: {p.claim_id}
                </Heading>
              </CardHeader>
              <CardBody pt={1}>
                <Stack divider={<StackDivider />} spacing='3'>
                  <Box>
                    <Heading size='xs' textTransform='uppercase' mb={1}>
                      Similarity Score
                    </Heading>
                    <Flex align="center">
                      <Progress 
                        value={(p.similarity_score ?? 0) * 100} 
                        size='sm' 
                        colorScheme={scoreColor(p.similarity_score ?? 0)}
                        flexGrow={1}
                        mr={2}
                        borderRadius="md"
                        aria-label={`Similarity score: ${((p.similarity_score ?? 0) * 100).toFixed(1)}%`}
                      />
                      <Badge colorScheme={scoreColor(p.similarity_score ?? 0)} variant="solid" fontSize="xs">
                        {((p.similarity_score ?? 0) * 100).toFixed(1)}%
                      </Badge>
                    </Flex>
                  </Box>
                  <Box>
                    <Heading size='xs' textTransform='uppercase' mb={1}>
                      Summary Snippet
                    </Heading>
                    <Text pt='1' fontSize='sm' noOfLines={3}>
                      {p.summary || 'No summary available.'}
                    </Text>
                  </Box>
                  {p.keywords && p.keywords.length > 0 && (
                    <Box>
                      <Heading size='xs' textTransform='uppercase' mb={1}>
                        Keywords
                      </Heading>
                      <Wrap spacing={1} mt={1}>
                        {p.keywords.map((kw: string) => <WrapItem key={kw}><Tag size="sm" colorScheme='gray'>{kw}</Tag></WrapItem>)}
                      </Wrap>
                    </Box>
                  )}
                  {p.outcome && (
                    <Box>
                      <Heading size='xs' textTransform='uppercase' mb={1}>
                        Outcome
                      </Heading>
                      <Text pt='1' fontSize='sm'>{p.outcome}</Text>
                    </Box>
                  )}
                </Stack>
              </CardBody>
            </Card>
          ))}
        </VStack>
      )}
    </Box>
  );
};

export default PrecedentPanel; 