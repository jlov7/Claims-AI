export interface QAPair {
  question: string;
  answer: string;
}

export interface DraftStrategyNoteRequest {
  claimSummary?: string;
  documentIds?: string[];
  qaHistory?: QAPair[];
  additionalCriteria?: string;
  outputFilename: string;
}
