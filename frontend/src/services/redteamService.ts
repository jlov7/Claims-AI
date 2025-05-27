import apiClient from "./apiClient.ts";
import { RedTeamRunResult } from "../models/redteam.ts";

export const runRedTeamEvaluation = async (): Promise<RedTeamRunResult> => {
  try {
    // The backend endpoint is GET /api/v1/redteam/run
    const response = await apiClient.get<RedTeamRunResult>("/redteam/run");
    return response.data;
  } catch (error: any) {
    console.error("Error running Red Team evaluation:", error);
    throw new Error(
      error.response?.data?.detail ||
        error.message ||
        "Failed to run Red Team evaluation.",
    );
  }
};
