from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from pydantic import BaseModel, Field
import os
from typing import Optional, List, Dict, Any
import sys
import importlib
import traceback
import langsmith
# from langsmith import environment # type: ignore # Commenting out potentially problematic part
from core.config import settings
# from langserve.frontend import create_frontend # Import create_frontend # REMOVED

# Import with proper error handling
try:
    from langserve.playground import serve_playground 
    import langserve
    print(f"Successfully imported langserve. Version: {langserve.__version__}")
    print(f"AVAILABLE IN langserve.playground: {dir(langserve.playground)}")
except ImportError as e:
    print(f"Error importing langserve modules: {e}")
    # Fallback import for documentation visibility
    serve_playground = None

# Existing models
from models import (
    DraftStrategyNoteRequest as V2DraftStrategyNoteRequest,
    QAPair,  # ADDED IMPORT
)

# Services
from services.rag_service import get_rag_service, RAGService
from services.summarisation_service import (
    get_summarisation_service,
    SummarisationService,
)
from services.drafting_service import get_drafting_service, DraftingService
from services.minio_service import MinioService, get_minio_service # type: ignore

print(f"RUNTIME sys.path in langserve_app/app.py: {sys.path}")

importlib.invalidate_caches()

print(f"RUNTIME dir(langserve): {dir(langserve)}")

# --- V1 Models for LangServe Schema ---
class LangServeSourceDocument(BaseModel):
    document_id: str
    chunk_id: str
    file_name: str
    chunk_content: str
    score: Optional[float] = None


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[LangServeSourceDocument]
    confidence_score: Optional[int] = None
    self_heal_attempts: Optional[int] = 0


class SummariseLangServeResponse(BaseModel):
    summary: str
    original_document_id: Optional[str] = None
    original_content_preview: Optional[str] = None


# V1 QAPair model for LangServe request
class V1QAPair(BaseModel):
    question: str
    answer: str


# Create a FastAPI app for LangServe
# langserve_app = FastAPI(
#     title="Claims-AI LangServe",
#     version="1.0",
#     description="LangServe application for Claims-AI agentic workflows"
# )

# Add CORS middleware
# Configure this more strictly in production
# langserve_app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )


# --- RAG Query Route ---
class RAGQueryRequest(BaseModel):
    query: str


async def rag_query_logic(request_dict: dict) -> RAGQueryResponse:
    try:
        request = RAGQueryRequest.parse_obj(request_dict)
    except Exception as e:
        # Handle Pydantic validation error, etc.
        raise HTTPException(
            status_code=422, detail=f"Invalid input for RAG query: {e}"
        )

    rag_service: RAGService = get_rag_service()
    try:
        answer, sources_v2, confidence_score, self_heal_attempts = (
            await rag_service.query_rag(request.query)
        )

        # Convert V2SourceDocumentInternal list to LangServeSourceDocument list
        v1_sources_list: List[LangServeSourceDocument] = []
        for src_v2 in sources_v2:
            v1_sources_list.append(
                LangServeSourceDocument(
                    document_id=src_v2.document_id,
                    chunk_id=src_v2.chunk_id,
                    file_name=src_v2.file_name or "N/A",
                    chunk_content=src_v2.chunk_content or "N/A",
                    score=src_v2.score,
                )
            )

        return RAGQueryResponse(
            answer=answer,
            sources=v1_sources_list,
            confidence_score=confidence_score,
            self_heal_attempts=self_heal_attempts,
        )
    except Exception as e:
        # Log the exception here for better debugging
        print(f"Error in RAG query logic: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


rag_query_runnable = RunnableLambda(rag_query_logic).with_types(
    input_type=RAGQueryRequest, output_type=RAGQueryResponse
)

# --- RAG Collection Query Route ---
class RAGCollectionQueryLangServeRequest(RAGQueryRequest):
    collection_name: str


async def rag_collection_query_logic(request_dict: dict) -> RAGQueryResponse:
    try:
        request = RAGCollectionQueryLangServeRequest.parse_obj(request_dict)
    except Exception as e:
        # Handle Pydantic validation error, etc.
        raise HTTPException(
            status_code=422, detail=f"Invalid input for RAG collection query: {e}"
        )
    rag_service: RAGService = get_rag_service()
    try:
        answer, sources_v2, confidence_score, self_heal_attempts = (
            await rag_service.query_collection(request.collection_name, request.query)
        )
        v1_sources_list: List[LangServeSourceDocument] = []
        for src_v2 in sources_v2:
            v1_sources_list.append(
                LangServeSourceDocument(
                    document_id=src_v2.document_id,
                    chunk_id=src_v2.chunk_id,
                    file_name=src_v2.file_name or "N/A",
                    chunk_content=src_v2.chunk_content or "N/A",
                    score=src_v2.score,
                )
            )

        return RAGQueryResponse(
            answer=answer,
            sources=v1_sources_list,
            confidence_score=confidence_score,
            self_heal_attempts=self_heal_attempts,
        )
    except Exception as e:
        print(f"Error in RAG collection query logic: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))


rag_collection_query_runnable = RunnableLambda(rag_collection_query_logic).with_types(
    input_type=RAGCollectionQueryLangServeRequest, output_type=RAGQueryResponse
)

# --- Summarisation Route ---
class SummariseLangServeRequest(BaseModel):
    document_id: str = ""  # Non-Optional, default to empty string
    content: str = ""  # Non-Optional, default to empty string # Ensure default for playground


async def summarise_logic(request_dict: dict) -> SummariseLangServeResponse:
    try:
        request = SummariseLangServeRequest.parse_obj(request_dict)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid input for summarise request: {e}"
        )

    summarisation_service: SummarisationService = get_summarisation_service()
    text_to_summarise = ""
    original_content_preview = None
    doc_id_for_response: Optional[str] = None

    if request.content:
        text_to_summarise = request.content
        doc_id_for_response = None
        if len(text_to_summarise) > 200:
            original_content_preview = text_to_summarise[:200] + "..."
        else:
            original_content_preview = text_to_summarise
    elif request.document_id:
        doc_id_for_response = request.document_id
        try:
            text_to_summarise = await summarisation_service.get_content_from_id(
                request.document_id
            )
            if len(text_to_summarise) > 200:
                original_content_preview = text_to_summarise[:200] + "..."
            else:
                original_content_preview = text_to_summarise
        except HTTPException as http_exc:
            raise http_exc
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found for ID: {request.document_id}",
            )
        except Exception as e:
            print(f"Error retrieving document content: {type(e).__name__} - {e}")
            raise HTTPException(
                status_code=500, detail="Error retrieving document content"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'document_id' or 'content' must be provided.",
        )

    if not text_to_summarise.strip():
        raise HTTPException(
            status_code=400, detail="Content for summarisation is empty."
        )

    try:
        summary_text = await summarisation_service.summarise_text(text_to_summarise)
    except Exception as e:
        # Log the exception here
        print(f"Error during summarisation: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="Error during summarisation")

    return SummariseLangServeResponse(
        summary=summary_text,
        original_document_id=doc_id_for_response,
        original_content_preview=original_content_preview,
    )


summarise_runnable = RunnableLambda(summarise_logic).with_types(
    input_type=SummariseLangServeRequest, output_type=SummariseLangServeResponse
)

# --- Drafting Route (Strategy Note) ---
class DraftStrategyNoteLangServeRequest(BaseModel):
    claim_summary: str = ""  # Non-Optional
    key_document_ids: List[str] = Field(default_factory=list)
    qa_history: List[V1QAPair] = Field(default_factory=list)
    user_criteria: str = ""  # Non-Optional
    output_filename: str = "StrategyNote.docx" # Ensure default for playground


class DraftStrategyNoteLangServeResponse(BaseModel):
    file_path: str
    file_name: str


async def draft_logic(input_dict: dict) -> DraftStrategyNoteLangServeResponse:
    try:
        # Explicitly parse the input dictionary
        request_model = DraftStrategyNoteLangServeRequest.parse_obj(input_dict)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid input for draft request: {e}"
        )

    drafting_service: DraftingService = get_drafting_service()
    try:
        # Map to the V2 Pydantic model used by the service
        # Ensure field names match or handle discrepancies
        # V2DraftStrategyNoteRequest fields: claimSummary, document_ids, qa_history (List[QAPair]), additional_criteria, output_filename
        # request_model (DraftStrategyNoteLangServeRequest - V1) fields: claim_summary, key_document_ids, qa_history, user_criteria, output_filename
        v2_qa_history: Optional[List[QAPair]] = None
        if request_model.qa_history:
            v2_qa_history = [
                QAPair(question=item.question, answer=item.answer)
                for item in request_model.qa_history
            ]

        v2_service_request = V2DraftStrategyNoteRequest(
            claimSummary=request_model.claim_summary,
            document_ids=request_model.key_document_ids,  # Map key_document_ids to document_ids
            qa_history=v2_qa_history,  # Map qa_history to qa_history
            additional_criteria=request_model.user_criteria,  # Map user_criteria to additional_criteria
            output_filename=request_model.output_filename,
        )

        # Ensure DraftingService methods are called without await if they are synchronous.
        # _build_llm_context calls _get_content_from_doc_id, which uses DocumentLoaderService.
        # load_document_content_by_id (mocked in tests) is synchronous.
        # generate_strategy_note_text (mocked in tests, or real for full_llm_test) is synchronous (uses chain.invoke).
        # create_docx_from_text is synchronous.
        context = drafting_service._build_llm_context(v2_service_request)  # No await
        if not context:  # This check should ideally be in the service method
            raise HTTPException(
                status_code=400, detail="Insufficient context for drafting."
            )

        note_text_content = drafting_service.generate_strategy_note_text(
            context
        )  # No await
        if not note_text_content:  # This check should ideally be in the service method
            raise HTTPException(
                status_code=500, detail="LLM generated empty content for strategy note."
            )

        # Ensure output_filename from the parsed request_model is used
        docx_file_path_obj = drafting_service.create_docx_from_text(  # No await
            text=note_text_content, filename_suggestion=request_model.output_filename
        )
        if not os.path.exists(str(docx_file_path_obj)):
            raise HTTPException(
                status_code=500, detail="Failed to save or locate drafted DOCX file."
            )
        return DraftStrategyNoteLangServeResponse(
            file_path=str(docx_file_path_obj),
            file_name=docx_file_path_obj.name,
        )
    except (
        ValueError
    ) as ve:  # This is typically raised by DraftingService for validation
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as e:  # Re-raise known HTTPExceptions
        raise e
    except Exception as e:
        # Log the exception for debugging
        print(f"Unexpected error in draft_logic: {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=500, detail=f"Error drafting strategy note: {str(e)}"
        )


draft_runnable = RunnableLambda(draft_logic).with_types(
    input_type=DraftStrategyNoteLangServeRequest,
    output_type=DraftStrategyNoteLangServeResponse,
)

# print(f"LANGSERVE_APP_DIR: {LANGSERVE_APP_DIR}")
# print(f"TEMPLATES_DIR in langserve_app: {TEMPLATES_DIR}")

# langserve_router = APIRouter()


# def add_all_langserve_routes(app_to_configure: FastAPI) -> None:
#     """
#     Adds all LangServe routes to the provided FastAPI app or APIRouter.
#     Mounts a static directory for a custom global playground if specified.
#     """
#     add_routes(
#         app_to_configure,
#         rag_query_runnable,
#         path="/query",
#         input_type=RAGQueryRequest, # Redundant if using .with_types() but good for clarity
#         output_type=RAGQueryResponse,
#         playground_type="default", # Explicitly set playground type
#         enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
#         enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
#     )
#     add_routes(
#         app_to_configure,
#         rag_collection_query_runnable,
#         path="/query_collection",
#         input_type=RAGCollectionQueryLangServeRequest,
#         output_type=RAGQueryResponse,
#         playground_type="default",
#         enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
#         enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
#     )
#     add_routes(
#         app_to_configure,
#         summarise_runnable,
#         path="/summarise",
#         input_type=SummariseLangServeRequest,
#         output_type=SummariseLangServeResponse,
#         playground_type="default",
#         enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
#         enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
#     )
#     add_routes(
#         app_to_configure,
#         draft_runnable,
#         path="/draft",
#         input_type=DraftStrategyNoteLangServeRequest,
#         output_type=DraftStrategyNoteLangServeResponse,
#         playground_type="default",
#         enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
#         enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
#     )

#     # Attempt to serve a global playground
#     # This was the problematic part due to langserve.frontend change
#     # try:
#     #     # Mount the custom global playground HTML
#     #     # The path '/playground' will be relative to where this router is mounted
#     #     # So if router is at '/langserve', this becomes '/langserve/playground'
#     #     app_to_configure.get("/playground", response_class=HTMLResponse)(
#     #         lambda: create_frontend(
#     #             [
#     #                 ("/langserve/query", rag_query_runnable), # Adjust paths to be absolute from main app
#     #                 ("/langserve/query_collection", rag_collection_query_runnable),
#     #                 ("/langserve/summarise", summarise_runnable),
#     #                 ("/langserve/draft", draft_runnable),
#     #             ],
#     #             # Provide the path to the custom template
#     #             # template_path=str(TEMPLATES_DIR / "playground.html") # Ensure this path is correct
#     #         )
#     #     )
#     #     print("Successfully added custom global playground route.")
#     # except Exception as e:
#     #     print(f"Error adding custom global playground: {e}")


# Returns a FastAPI sub-app again
def add_all_langserve_routes() -> FastAPI:
    """
    Creates a new FastAPI sub-application, adds all LangServe routes
    (for query, summarise, draft, etc.) to it with their individual playgrounds.
    A custom endpoint at path '/' uses serve_playground for the main catalog.
    """
    sub_app = FastAPI(
        title="Claims-AI LangServe Sub-App"
        # We can let FastAPI/LangServe handle default OpenAPI/docs paths for the sub-app
    )

    from fastapi.middleware.cors import CORSMiddleware
    sub_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store runnables to pass to the main playground
    all_runnables_for_playground = []

    add_routes(
        sub_app,
        rag_query_runnable,
        path="/query", # Local path within sub_app
        playground_type="default", # This gives /query/playground/
        enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
        enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
    )
    all_runnables_for_playground.append(("/query", rag_query_runnable))

    add_routes(
        sub_app,
        rag_collection_query_runnable,
        path="/query_collection", # Local path within sub_app
        playground_type="default", # This gives /query_collection/playground/
        enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
        enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
    )
    all_runnables_for_playground.append(("/query_collection", rag_collection_query_runnable))

    add_routes(
        sub_app,
        summarise_runnable,
        path="/summarise", # Local path within sub_app
        playground_type="default", # This gives /summarise/playground/
        enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
        enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
    )
    all_runnables_for_playground.append(("/summarise", summarise_runnable))
    
    add_routes(
        sub_app,
        draft_runnable,
        path="/draft", # Local path within sub_app
        playground_type="default", # This gives /draft/playground/
        enable_feedback_endpoint=settings.LANGSERVE_ENABLE_FEEDBACK,
        enable_public_trace_link_endpoint=settings.LANGSERVE_ENABLE_PUBLIC_TRACE,
    )
    all_runnables_for_playground.append(("/draft", draft_runnable))

    # Remove the old RunnablePassthrough at "/"
    # add_routes(
    #     sub_app,
    #     RunnablePassthrough(),
    #     path="/",
    #     playground_type="default"  # This was not working for catalog
    # )

    # Add the main catalog playground at the root of the sub_app
    @sub_app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def get_main_playground():
        try:
            print(f"DEBUG: Serving playground with runnables: {[path for path, _ in all_runnables_for_playground]}")
            
            # If serve_playground is None (import failed), return a fallback HTML page
            if serve_playground is None:
                return HTMLResponse(content="""
                <html>
                <head><title>LangServe Fallback</title></head>
                <body>
                    <h1>LangServe Playground Not Available</h1>
                    <p>serve_playground function was not found in langserve.playground</p>
                    <p>Available runnables:</p>
                    <ul>
                        <li><a href="/langserve/query/playground">/langserve/query/playground</a></li>
                        <li><a href="/langserve/query_collection/playground">/langserve/query_collection/playground</a></li>
                        <li><a href="/langserve/summarise/playground">/langserve/summarise/playground</a></li>
                        <li><a href="/langserve/draft/playground">/langserve/draft/playground</a></li>
                    </ul>
                </body>
                </html>
                """)
                
            # Get the runnable for demonstration (test with just one for simplicity)
            test_runnable = rag_query_runnable
            
            # In langserve 0.3.1, serve_playground expects these parameters:
            # serve_playground(input_schema, output_schema, config_keys, base_url, file_path, 
            #                 feedback_enabled, public_trace_link_enabled, playground_type)
            
            # Extract schema information from the runnable
            from pydantic import create_model
            
            # Get input/output schemas from the runnable
            input_schema = test_runnable.input_schema.schema()
            output_schema = test_runnable.output_schema.schema()
            
            # Set default values for the other parameters
            config_keys = []  # No config keys
            base_url = "/query"  # Base URL for the runnable
            file_path = ""  # No file path
            feedback_enabled = settings.LANGSERVE_ENABLE_FEEDBACK
            public_trace_link_enabled = settings.LANGSERVE_ENABLE_PUBLIC_TRACE
            playground_type = "default"
            
            # Call serve_playground with all the required parameters
            return serve_playground(
                input_schema=input_schema,
                output_schema=output_schema,
                config_keys=config_keys,
                base_url=base_url,
                file_path=file_path,
                feedback_enabled=feedback_enabled,
                public_trace_link_enabled=public_trace_link_enabled,
                playground_type=playground_type
            )
            
        except Exception as e:
            # Capture detailed error information
            error_traceback = traceback.format_exc()
            error_msg = f"Error serving playground: {type(e).__name__}: {str(e)}\n\nTraceback:\n{error_traceback}"
            print(error_msg)
            
            # Return a simple HTML response with links to individual playgrounds 
            return HTMLResponse(
                content=f"""
                <html>
                <head>
                    <title>Claims-AI LangServe Catalog</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                        h1, h2 {{ color: #333; }}
                        ul {{ padding-left: 20px; }}
                        li {{ margin-bottom: 10px; }}
                        a {{ color: #0066cc; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                        .endpoint-box {{ 
                            border: 1px solid #ddd; 
                            padding: 15px; 
                            margin-bottom: 20px; 
                            border-radius: 5px;
                            background-color: #f9f9f9;
                        }}
                        .endpoint-title {{ 
                            margin-top: 0; 
                            color: #0066cc;
                        }}
                        .endpoint-paths {{ 
                            margin-left: 20px;
                            margin-bottom: 10px;
                        }}
                        code {{
                            background-color: #f0f0f0;
                            padding: 2px 5px;
                            border-radius: 3px;
                            font-family: monospace;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Claims-AI LangServe Catalog</h1>
                    <p>The following LangChain runnables are available:</p>
                    
                    <div class="endpoint-box">
                        <h2 class="endpoint-title">RAG Query</h2>
                        <div class="endpoint-paths">
                            <p><strong>Playground:</strong> <a href="/langserve/query/playground">/langserve/query/playground</a></p>
                            <p><strong>Invoke:</strong> <a href="/langserve/query/invoke">/langserve/query/invoke</a></p>
                            <p><strong>Docs:</strong> <a href="/langserve/query/docs">/langserve/query/docs</a></p>
                        </div>
                        <p>Execute semantic queries against documents with source retrieval and citations.</p>
                    </div>
                    
                    <div class="endpoint-box">
                        <h2 class="endpoint-title">Collection Query</h2>
                        <div class="endpoint-paths">
                            <p><strong>Playground:</strong> <a href="/langserve/query_collection/playground">/langserve/query_collection/playground</a></p>
                            <p><strong>Invoke:</strong> <a href="/langserve/query_collection/invoke">/langserve/query_collection/invoke</a></p>
                            <p><strong>Docs:</strong> <a href="/langserve/query_collection/docs">/langserve/query_collection/docs</a></p>
                        </div>
                        <p>Query a specific named collection of documents for targeted results.</p>
                    </div>
                    
                    <div class="endpoint-box">
                        <h2 class="endpoint-title">Summarisation</h2>
                        <div class="endpoint-paths">
                            <p><strong>Playground:</strong> <a href="/langserve/summarise/playground">/langserve/summarise/playground</a></p>
                            <p><strong>Invoke:</strong> <a href="/langserve/summarise/invoke">/langserve/summarise/invoke</a></p>
                            <p><strong>Docs:</strong> <a href="/langserve/summarise/docs">/langserve/summarise/docs</a></p>
                        </div>
                        <p>Generate concise summaries of document content with key fact extraction.</p>
                    </div>
                    
                    <div class="endpoint-box">
                        <h2 class="endpoint-title">Strategy Note Drafting</h2>
                        <div class="endpoint-paths">
                            <p><strong>Playground:</strong> <a href="/langserve/draft/playground">/langserve/draft/playground</a></p>
                            <p><strong>Invoke:</strong> <a href="/langserve/draft/invoke">/langserve/draft/invoke</a></p>
                            <p><strong>Docs:</strong> <a href="/langserve/draft/docs">/langserve/draft/docs</a></p>
                        </div>
                        <p>Create structured strategy notes based on document summaries, Q&A history, and customizable criteria.</p>
                    </div>
                    
                    <div class="endpoint-box">
                        <h2 class="endpoint-title">API Documentation</h2>
                        <p>For the full OpenAPI documentation, visit <a href="/langserve/docs">/langserve/docs</a>.</p>
                    </div>
                </body>
                </html>
                """
            )

    return sub_app

# Remove the old passthrough runnable if no longer needed for /hello
# add_routes(
#     langserve_app,
#     RunnablePassthrough(), # A simple passthrough
#     path="/hello",
# )


# To test this app directly (optional, for development):
# if __name__ == "__main__":
#     import uvicorn
#     # Create the app instance by calling the factory function
#     standalone_app = add_all_langserve_routes() 
#     # Note: Adjust port if 8000 is used by the main FastAPI app
#     uvicorn.run(standalone_app, host="0.0.0.0", port=8001, log_level="info")
