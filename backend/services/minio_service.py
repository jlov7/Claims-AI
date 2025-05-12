import logging
from minio import Minio
from minio.error import S3Error
from ..core.config import settings
import io
from urllib.parse import urlparse  # Added for parsing URL

logger = logging.getLogger(__name__)


class MinioService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MinioService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            minio_endpoint = settings.MINIO_URL
            # Ensure the endpoint is just host:port for the Minio client
            parsed_url = urlparse(
                f"http://{minio_endpoint}"
            )  # Add temp scheme for parsing if not present
            actual_endpoint = parsed_url.netloc  # This gives host:port

            self.client = Minio(
                endpoint=actual_endpoint,  # Use the parsed host:port
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,  # Assuming Minio is running over HTTP locally
            )
            logger.info(
                f"Minio client initialized for endpoint: {actual_endpoint} (original: {settings.MINIO_URL})"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Minio client with endpoint '{settings.MINIO_URL}' (parsed as '{actual_endpoint if 'actual_endpoint' in locals() else 'parse_failed'}'): {e}"
            )
            self.client = None
        self._initialized = True

    def ensure_bucket_exists(self, bucket_name: str):
        if not self.client:
            logger.error("Minio client not available. Cannot ensure bucket exists.")
            raise RuntimeError(
                "Minio client not initialized. Cannot ensure bucket exists."
            )
        try:
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logger.info(f"Bucket '{bucket_name}' created successfully.")
            else:
                logger.info(f"Bucket '{bucket_name}' already exists.")
        except S3Error as e:
            logger.error(f"Error checking or creating bucket '{bucket_name}': {e}")
            raise

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not self.client:
            logger.error("Minio client not available. Cannot upload file.")
            raise RuntimeError("Minio client not initialized. Cannot upload file.")

        self.ensure_bucket_exists(bucket_name)  # Ensure bucket exists before upload

        data_stream = io.BytesIO(data)
        data_len = len(data)

        try:
            self.client.put_object(
                bucket_name,
                object_name,
                data_stream,
                length=data_len,
                content_type=content_type,
            )
            logger.info(
                f"Successfully uploaded '{object_name}' to bucket '{bucket_name}'."
            )
            # Construct the URL. This might need adjustment based on Minio setup and public access.
            # For local dev, http://localhost:9000/bucket_name/object_name is common if port 9000 is mapped from Minio container
            # settings.MINIO_URL is 'minio:9000' from within Docker network. We need an externally accessible URL.
            # Assuming Minio is accessible on localhost:9000 for the user.
            # A more robust solution would involve constructing this based on a public Minio endpoint config.
            public_minio_url = f"http://localhost:9000/{bucket_name}/{object_name}"  # Host-accessible URL

            # To make files publicly readable by default (common for serving assets),
            # you might need to set a bucket policy on Minio itself.
            # Example policy for public read on a bucket:
            # {
            # "Version": "2012-10-17",
            # "Statement": [
            # {
            # "Effect": "Allow",
            # "Principal": {"AWS": "*"},
            # "Action": "s3:GetObject",
            # "Resource": "arn:aws:s3:::bucket-name/*"
            # }
            # ]
            # }
            # This usually needs to be set once on the bucket via Minio console or mc client.

            return public_minio_url
        except S3Error as e:
            logger.error(
                f"Error uploading file '{object_name}' to bucket '{bucket_name}': {e}"
            )
            raise


def get_minio_service() -> MinioService:
    return MinioService()


# Ensure __init__.py exists in services directory
# Create if not exists: backend/services/__init__.py
# with content:
# from .drafting_service import get_drafting_service, DraftingService
# from .rag_service import get_rag_service, RAGService
# from .summarisation_service import get_summarisation_service, SummarisationService
# from .minio_service import get_minio_service, MinioService
# from .speech_service import get_speech_service, SpeechService # will be added next
