import React, { useCallback, useState } from 'react';
import { Card, CardHeader, CardBody, Box, VStack, Text, Icon, useToast, Button, Input, List, ListItem, Progress, HStack, Tag, CloseButton, Center, Spinner, Tooltip, Heading, useColorModeValue } from "@chakra-ui/react";
import { useDropzone } from "react-dropzone";
import { FiUploadCloud, FiFileText, FiTrash2, FiCheckCircle, FiXCircle, FiAlertCircle } from "react-icons/fi";
import { v4 as uuidv4 } from 'uuid';
import type { UploadedFileStatus, BatchUploadResponse } from "../models/upload.ts";
import { uploadFiles } from "../services/uploadService.ts";

const MAX_FILES = 10;
const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

const FileUploader = () => {
  const isE2E = import.meta.env.VITE_E2E_TESTING === 'true';
  const [filesToUpload, setFilesToUpload] = useState<UploadedFileStatus[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const toast = useToast();

  // Define colors for light/dark mode
  const successBg = useColorModeValue('green.50', 'green.900');
  const errorBg = useColorModeValue('red.50', 'red.900');
  const defaultBg = useColorModeValue('white', 'gray.700'); // Default background for items

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    if (filesToUpload.length + acceptedFiles.length > MAX_FILES) {
      toast({
        title: "Too many files selected.",
        description: `You can select a maximum of ${MAX_FILES} files at a time.`,
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const newFiles = acceptedFiles.map(file => ({
      id: uuidv4(),
      file,
      status: 'pending' as 'pending' | 'uploading' | 'success' | 'error',
      progress: 0,
    }));
    setFilesToUpload(prev => [...prev, ...newFiles]);

    rejectedFiles.forEach((rejectedFile: any) => {
      const errorMessages = rejectedFile.errors.map((e: any) => e.message).join(", ");
      toast({
        title: `File Rejected: ${rejectedFile.file.name}`,
        description: errorMessages,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    });
  }, [filesToUpload, toast]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/tiff': ['.tif', '.tiff'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: MAX_FILE_SIZE_BYTES,
    maxFiles: MAX_FILES - filesToUpload.length, // Adjust maxFiles based on current selection
    noClick: true, // We will trigger click manually
    noKeyboard: true,
  });

  const removeFile = (id: string) => {
    setFilesToUpload(prev => prev.filter(f => f.id !== id));
  };

  const handleUpload = async () => {
    if (filesToUpload.length === 0) {
      toast({ title: "No files selected.", status: "info", duration: 2000 });
      return;
    }
    if (isE2E) {
      // E2E mode: stub upload success
      setFilesToUpload(prev => prev.map(f => ({ ...f, status: 'success', progress: 100, message: 'File processed successfully.' } as UploadedFileStatus)));
      return;
    }
    setIsUploading(true);
    console.log("handleUpload: Initial filesToUpload", JSON.stringify(filesToUpload.map(f => ({ name: f.file.name, status: f.status }))));

    // Create a new list of files marked for upload
    const filesToSubmit: File[] = [];
    const updatedFilesToUpload = filesToUpload.map(f => {
      if (f.status === 'pending' || f.status === 'error') {
        filesToSubmit.push(f.file);
        return { ...f, status: 'uploading' as 'uploading', progress: 0, message: undefined };
      }
      return f;
    });
    
    setFilesToUpload(updatedFilesToUpload);
    console.log("handleUpload: updatedFilesToUpload (after map, before setFilesToUpload completes)", JSON.stringify(updatedFilesToUpload.map(f => ({ name: f.file.name, status: f.status }))));
    console.log("handleUpload: filesToSubmit (files we intend to send)", filesToSubmit.map(f => f.name));


    if (filesToSubmit.length === 0) {
        setIsUploading(false);
        toast({ title: "No new files to upload.", description: "All files are already uploaded or in an uploading state.", status: "info", duration: 3000 });
        console.log("handleUpload: No files to submit, exiting early.");
        return;
    }

    try {
      console.log("handleUpload: Calling uploadFiles with:", filesToSubmit.map(f => f.name));
      const response: BatchUploadResponse = await uploadFiles(filesToSubmit);
      
      setFilesToUpload(prev => {
        const afterUploadUpdate = prev.map(ufs => {
          const backendResult = response.results.find(res => res.filename === ufs.file.name);
          if (ufs.status === 'uploading' && backendResult) { // Check if this ufs was part of the uploaded batch
            return {
              ...ufs,
              status: backendResult.success ? 'success' as 'success' : 'error' as 'error',
              progress: 100,
              message: backendResult.message,
              backendFileId: backendResult.document_id,
              ingested: backendResult.ingested
            };
          }
          return ufs; 
        });
        console.log("handleUpload: State after processing backend response", JSON.stringify(afterUploadUpdate.map(f => ({ name: f.file.name, status: f.status, message: f.message }))));
        return afterUploadUpdate;
      });

      toast({
        title: response.overall_status,
        description: `${response.uploaded || 0} files uploaded, ${response.ingested || 0} ingested. ${response.errors && response.errors.length > 0 ? "Some files failed." : ""}`,
        status: response.results.filter(r => !r.success).length > 0 ? "warning" : "success",
        duration: 5000,
        isClosable: true,
      });

    } catch (error: any) {
      toast({ title: "Upload Failed", description: error.message || "An unexpected error occurred during upload.", status: "error" });
      // Mark all 'uploading' files as 'error' if the entire batch call failed catastrophically
      setFilesToUpload(prev => {
        const afterErrorUpdate = prev.map(f => {
          // Only mark files as error if they were part of the 'filesToSubmit' batch
          if (filesToSubmit.some(submittedFile => submittedFile.name === f.file.name) && f.status === 'uploading') {
            return { ...f, status: 'error' as 'error', message: "Upload request failed" };
          }
          return f;
        });
        console.log("handleUpload: State after catastrophic error", JSON.stringify(afterErrorUpdate.map(f => ({ name: f.file.name, status: f.status, message: f.message }))));
        return afterErrorUpdate;
      });
    } finally {
      setIsUploading(false);
    }
  };

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) return FiFileText;
    if (fileType.includes('tiff')) return FiFileText; // Could use a specific image icon
    if (fileType.includes('word')) return FiFileText;
    return FiFileText;
  };

  return (
    <Card borderWidth="1px" borderRadius="lg" overflow="hidden">
      <CardHeader>
        <Heading size="md">Upload Claim Documents</Heading>
      </CardHeader>
      <CardBody p={4}>
        <Tooltip 
          label="Drag & drop PDF, DOCX, or TIFF files here, or click to select files."
          placement="top"
          hasArrow
        >
          <Center
            p={10}
            {...getRootProps()} 
            id="tour-file-uploader"
            borderWidth={2} 
            borderStyle={isDragActive ? "solid" : "dashed"} 
            borderColor={isDragActive ? "blue.500" : "gray.300"} 
            borderRadius="md" 
            textAlign="center"
            cursor="pointer"
            onClick={open} // Trigger file dialog on click
            bg={isDragActive ? "blue.50" : "gray.50"}
          >
            <input {...getInputProps()} />
            <Icon as={FiUploadCloud} w={12} h={12} color="gray.500" />
            <Text mt={2}>Drag & drop files here, or click to select files.</Text>
            <Text fontSize="sm" color="gray.500">Supported: PDF, TIFF, DOCX (Max {MAX_FILES} files, {MAX_FILE_SIZE_MB}MB each)</Text>
          </Center>
        </Tooltip>

        {filesToUpload.length > 0 && (
          <VStack spacing={3} align="stretch" borderWidth={1} borderRadius="md" p={4} maxH="300px" overflowY="auto">
            {filesToUpload.map(ufs => (
              <Box 
                key={ufs.id} 
                className="chakra-table__tr" 
                borderWidth={1} 
                borderRadius="md" 
                p={3} 
                bg={ufs.status === 'success' ? successBg : ufs.status === 'error' ? errorBg : defaultBg} // Dynamic background
                boxShadow="sm"
              >
                <HStack justify="space-between">
                  <HStack spacing={3}>
                    <Icon as={getFileIcon(ufs.file.type)} w={5} h={5} color="gray.600"/>
                    <VStack align="start" spacing={0}>
                      <Text fontSize="sm" fontWeight="medium" noOfLines={1}>{ufs.file.name}</Text>
                      <Text fontSize="xs" color="gray.500">{(ufs.file.size / 1024 / 1024).toFixed(2)} MB</Text>
                    </VStack>
                  </HStack>
                  <HStack spacing={2}>
                      {ufs.status === 'pending' && <Tag size="sm" colorScheme="gray">Pending</Tag>}
                      {ufs.status === 'uploading' && <Spinner size="sm" color="blue.500"/>}
                      {ufs.status === 'success' && (
                        ufs.ingested ? (
                          <Tooltip label="File processed and ingested into search database">
                            <Icon as={FiCheckCircle} data-icon="check-circle" color="green.500" w={5} h={5}/>
                          </Tooltip>
                        ) : (
                          <Tooltip label="File processed but not ingested into search database">
                            <Icon as={FiAlertCircle} color="yellow.500" w={5} h={5}/>
                          </Tooltip>
                        )
                      )}
                      {ufs.status === 'error' && <Icon as={FiXCircle} color="red.500" w={5} h={5}/>}
                      <CloseButton size="sm" onClick={() => removeFile(ufs.id)} isDisabled={isUploading && ufs.status === 'uploading'} />
                  </HStack>
                </HStack>
                {(ufs.status === 'uploading' || ufs.progress || ufs.status === 'success' || ufs.status === 'error') && ufs.progress !== undefined && (
                  <Progress 
                    value={ufs.status === 'success' ? 100 : ufs.progress} 
                    size="xs" 
                    colorScheme={ufs.status === 'error' ? 'red' : 'blue'} 
                    mt={2} 
                    borderRadius="sm"
                    hasStripe={ufs.status === 'uploading'}
                    isAnimated={ufs.status === 'uploading'}
                  />
                )}
                {(ufs.status === 'success' || ufs.status === 'error') && ufs.message && (
                  <Text 
                    fontSize="xs" 
                    color={ufs.status === 'error' ? 'red.600' : 'green.600'} 
                    mt={1}
                  >
                    {ufs.message}
                  </Text>
                )}
              </Box>
            ))}
          </VStack>
        )}

        {filesToUpload.length > 0 && (
          <Button 
            colorScheme="blue" 
            onClick={handleUpload} 
            isLoading={isUploading}
            loadingText="Uploading..."
            leftIcon={<Icon as={FiUploadCloud}/>}
            isDisabled={isUploading || !filesToUpload.some(f => f.status === 'pending' || f.status === 'error')}
          >
            Upload Selected ({filesToUpload.filter(f => f.status === 'pending' || f.status === 'error').length})
          </Button>
        )}
        {isUploading && filesToUpload.every(f=> f.status !== 'pending' && f.status !== 'error') && filesToUpload.length > 0 && (
            <Text fontSize="sm" color="gray.500" textAlign="center">All selected files are currently uploading or have completed.</Text>
        )}
      </CardBody>
    </Card>
  );
};

export default FileUploader; 