import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface UploadedDocument {
  id: string;
  filename: string;
  uploadedAt: Date;
}

interface UploadContextType {
  recentUploads: UploadedDocument[];
  addUploadedDocument: (document: UploadedDocument) => void;
  clearUploads: () => void;
}

const UploadContext = createContext<UploadContextType | undefined>(undefined);

export const UploadProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [recentUploads, setRecentUploads] = useState<UploadedDocument[]>([]);

  console.log("UploadProvider state:", recentUploads);

  const addUploadedDocument = (document: UploadedDocument) => {
    // Add to the beginning of the array
    console.log("UploadProvider: Adding new document", document);
    setRecentUploads(prev => {
      // Check if document with this ID already exists
      const exists = prev.some(doc => doc.id === document.id);
      if (exists) {
        console.log(`Document with ID ${document.id} already exists, not adding duplicate`);
        return prev; // Return previous state unchanged
      }
      const newState = [document, ...prev];
      console.log("UploadProvider: New state will be", newState);
      return newState;
    });
  };

  const clearUploads = () => {
    setRecentUploads([]);
  };

  return (
    <UploadContext.Provider value={{ recentUploads, addUploadedDocument, clearUploads }}>
      {children}
    </UploadContext.Provider>
  );
};

export const useUpload = (): UploadContextType => {
  const context = useContext(UploadContext);
  if (context === undefined) {
    throw new Error('useUpload must be used within an UploadProvider');
  }
  return context;
}; 