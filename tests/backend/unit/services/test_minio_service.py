import pytest
from minio.error import S3Error
from backend.services.minio_service import MinioService


class DummyClient:
    def __init__(self):
        self.buckets = set()
        self.puts = []

    def bucket_exists(self, bucket_name):
        return bucket_name in self.buckets

    def make_bucket(self, bucket_name):
        self.buckets.add(bucket_name)

    def put_object(self, bucket_name, object_name, data_stream, length, content_type):
        self.puts.append((bucket_name, object_name, data_stream, length, content_type))


@pytest.fixture
def service(monkeypatch):
    svc = MinioService()
    svc.client = DummyClient()
    return svc


def test_singleton():
    s1 = MinioService()
    s2 = MinioService()
    assert s1 is s2


def test_ensure_bucket_exists_creates(service):
    svc = service
    svc.client.buckets = set()
    svc.ensure_bucket_exists("mybucket")
    assert "mybucket" in svc.client.buckets


def test_ensure_bucket_exists_existing(service):
    svc = service
    svc.client.buckets = {"mybucket"}
    svc.ensure_bucket_exists("mybucket")
    assert "mybucket" in svc.client.buckets


def test_ensure_bucket_exists_no_client():
    svc = MinioService()
    svc.client = None
    with pytest.raises(RuntimeError):
        svc.ensure_bucket_exists("bucket")


def test_upload_file_success(service, monkeypatch):
    svc = service
    monkeypatch.setattr(svc, "ensure_bucket_exists", lambda bucket: None)
    url = svc.upload_file("bucket", "obj", b"data", content_type="ct")
    assert url == "http://localhost:9000/bucket/obj"
    assert service.client.puts[0][0] == "bucket"
    assert service.client.puts[0][1] == "obj"


def test_upload_file_no_client():
    svc = MinioService()
    svc.client = None
    with pytest.raises(RuntimeError):
        svc.upload_file("bucket", "obj", b"data")


def test_upload_file_error(service, monkeypatch):
    svc = service
    monkeypatch.setattr(svc, "ensure_bucket_exists", lambda bucket: None)

    def raise_s3(*args, **kwargs):
        raise S3Error("err")

    svc.client.put_object = raise_s3
    with pytest.raises(Exception):
        svc.upload_file("bucket", "obj", b"data")
