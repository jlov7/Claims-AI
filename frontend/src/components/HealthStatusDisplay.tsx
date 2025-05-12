import React from 'react';
import { Box, Heading, Spinner, Tag, Text } from '@chakra-ui/react';
import type { HealthStatus } from '../services/healthService.js';

interface HealthStatusDisplayProps {
  health: HealthStatus | null;
  loadingHealth: boolean;
}

const HealthStatusDisplay: React.FC<HealthStatusDisplayProps> = ({ health, loadingHealth }) => {
  return (
    <Box mb={4}>
      <Heading size="sm" mb={1} color="gray.600">System Status</Heading>
      {loadingHealth ? (
        <Spinner size="sm" />
      ) : health?.healthy ? (
        <Tag size="md" colorScheme="green">Healthy</Tag>
      ) : (
        <Tag size="md" colorScheme="red" title={health?.message || 'Check backend services.'}>
          {health?.status || 'Error'} 
          {health?.message && health.message.length > 50 ? `- ${health.message.substring(0,50)}...` : health?.message ? `- ${health.message}` : '(Check backend logs)'}
        </Tag>
      )}
    </Box>
  );
};

export default HealthStatusDisplay; 