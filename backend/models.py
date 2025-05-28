from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    conint,
    constr,
    AliasChoices,
    model_validator,
)
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


class RAGQueryRequest(BaseModel):
    query: str


class SourceDocument(BaseModel):
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_content: str
    page_content: Optional[str] = None  # Added for frontend compatibility
    file_name: Optional[str] = None
    score: Optional[float] = None
    # Potentially add other metadata like page_number if available


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    confidence_score: Optional[int] = None
    self_heal_attempts: int = 0


class SummariseRequest(BaseModel):
    document_id: Optional[str] = None
    content: Optional[str] = None

    @model_validator(mode="after")
    def check_id_or_content_present(
        cls, values: "SummariseRequest"
    ) -> "SummariseRequest":
        if not values.document_id and not values.content:
            raise ValueError(
                "Either 'document_id' or 'content' must be provided for summarisation."
            )
        if values.document_id and values.content:
            raise ValueError(
                "Provide either 'document_id' or 'content' for summarisation, not both."
            )
        return values


class SummariseResponse(BaseModel):
    summary: str
    original_document_id: Optional[str] = None
    original_content_preview: Optional[str] = (
        None  # e.g., first 200 chars of content summarised
    )


class QAPair(BaseModel):
    question: str
    answer: str


class DraftStrategyNoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    claim_summary: Optional[str] = Field(default=None, alias="claimSummary")
    document_ids: Optional[List[str]] = Field(default=None, alias="documentIds")
    qa_history: Optional[List[QAPair]] = Field(default=None, alias="qaHistory")
    additional_criteria: Optional[str] = Field(default=None, alias="additionalCriteria")
    # output_filename is usually snake_case from frontend model, but alias for consistency if it changes
    output_filename: str = Field(
        alias="outputFilename",
        default_factory=lambda: f"StrategyNote_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.docx",
    )

    @model_validator(mode="before")
    def check_at_least_one_substantive_field(cls, data: Any) -> Any:
        if isinstance(data, dict):
            has_claim_summary = data.get("claim_summary") or data.get("claimSummary")
            has_document_ids = data.get("document_ids") or data.get("documentIds")
            has_qa_history = data.get("qa_history") or data.get("qaHistory")
            has_additional_criteria = data.get("additional_criteria") or data.get(
                "additionalCriteria"
            )
            if not (
                has_claim_summary
                or has_document_ids
                or has_qa_history
                or has_additional_criteria
            ):
                raise ValueError(
                    "At least one of 'claimSummary', 'documentIds', 'qaHistory', or 'additionalCriteria' must be provided."
                )
        return data


# No explicit DraftStrategyNoteResponse Pydantic model if returning FileResponse directly.


# --- Precedent Finder Models ---
class PrecedentQueryRequest(BaseModel):
    """
    Body model for POST /api/v1/precedents

    • Accepts both snake_case (claim_summary, top_k)
      and camelCase (claimSummary, topK) keys.
    • Validates that `claim_summary` is non‑blank.
    • Validates that `top_k` is 1 – 20 (defaults to 5).
    """

    claim_summary: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        validation_alias=AliasChoices("claim_summary", "claimSummary"),
        description="One‑sentence description of the claim.",
    )
    top_k: conint(ge=1, le=20) = Field(
        5,
        validation_alias=AliasChoices("top_k", "topK"),
        description="How many nearest precedents to return.",
    )

    # Allow "populate by name" so .claim_summary and .top_k work even if the
    # client sent camelCase; forbid extra fields so typos are caught.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PrecedentResultItem(BaseModel):
    claim_id: str
    summary: str
    outcome: Optional[str] = None
    keywords: Optional[str] = None
    distance: Optional[float] = None  # Similarity score or distance from ChromaDB


class PrecedentResponse(BaseModel):
    precedents: List[PrecedentResultItem]


class HealthCheckResponse(BaseModel):
    status: str
    detail: Optional[str] = None


# For P4.C Speech Endpoint
class SpeechRequest(BaseModel):
    text: str
    speaker_id: Optional[str] = None  # Model-specific speaker ID for Coqui TTS
    language_id: Optional[str] = None  # Model-specific language ID for Coqui TTS


class SpeechResponse(BaseModel):
    audio_url: str
    message: str
    filename: str


# Phase 4: Innovation - P4.D Red Teaming
class RedTeamPrompt(BaseModel):
    id: str
    category: str
    text: str
    expected_behavior: str


class RedTeamAttempt(BaseModel):
    prompt_id: str
    prompt_text: str
    category: str
    response_text: str
    rag_sources: Optional[List[SourceDocument]] = None
    rag_confidence: Optional[int] = None  # Changed from float to int for consistency with confidence_score
    evaluation_notes: Optional[str] = None


class RedTeamRunResult(BaseModel):
    results: List[RedTeamAttempt]
    summary_stats: Dict[str, Any]


# Models for File Upload API
class UploadResponseItem(BaseModel):
    filename: str
    message: str
    success: bool
    document_id: Optional[str] = (
        None  # ID of the processed document in the system (e.g., after OCR & DB insert)
    )
    error_details: Optional[str] = None
    ingested: bool = (
        False  # Added to track if document processing/ingestion was successful
    )


class BatchUploadResponse(BaseModel):
    overall_status: str  # e.g., "Completed", "Completed with errors", "Failed"
    results: List[UploadResponseItem]


# --- Drafting Service Specific Models (potentially for API layer) ---


class InitialDraftInputs(BaseModel):
    """Inputs that form the core request for initiating a draft."""

    session_id: str = Field(..., description="Session ID for context and logging.")
    summary: Optional[str] = Field(default=None, description="Claim summary text.")
    qa_history: Optional[List[QAPair]] = Field(
        default=None, description="List of question-answer pairs from RAG."
    )
    user_query: Optional[str] = Field(
        default=None, description="The user query that led to this draft request."
    )
    document_ids: Optional[List[str]] = Field(
        default=None, description="List of document IDs used for summary/QA."
    )
    initial_user_request: Optional[str] = Field(
        default=None,
        description="The original user request that started the interaction.",
    )
    # additional_criteria: Optional[str] = Field(default=None) # Already in DraftStrategyNoteRequest, consider if needed here separately


class CreateDraftRequest(BaseModel):
    """Request model for creating a new draft strategy note (v2)."""

    model_config = ConfigDict(populate_by_name=True)

    inputs: InitialDraftInputs = Field(
        ..., description="The core inputs for generating the draft."
    )
    output_filename: Optional[str] = Field(
        default=None,
        description="Optional desired filename for the output. If None, a default will be generated.",
        alias="outputFilename",
    )


class CreateDraftResponse(BaseModel):
    """Response model for a successful draft creation (v2)."""

    session_id: str
    message: str
    file_path: Optional[str] = None  # Path in Minio or local if applicable
    file_name: Optional[str] = None
    error: Optional[str] = None


model_config = ConfigDict(protected_namespaces=("settings_",))
