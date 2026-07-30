import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

NEWS = "news"
USERS = "user_profiles"


def _user_point_id(user_id: str) -> int:
    return int.from_bytes(hashlib.sha256(user_id.encode()).digest()[:8], "big")


class VectorStore:
    def __init__(self, path: str, dim: int = 1536):
        self.client = QdrantClient(path=path)
        self.dim = dim
        for name in (NEWS, USERS):
            if not self.client.collection_exists(name):
                self.client.create_collection(
                    name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))

    def upsert_news(self, message_id: str, vector, payload: dict) -> None:
        payload = {**payload, "message_id": message_id}
        self.client.upsert(NEWS, points=[
            PointStruct(id=int(message_id), vector=list(vector), payload=payload)])

    def update_news_payload(self, message_id: str, hearts: int, comment_count: int) -> None:
        self.client.set_payload(NEWS, payload={"hearts": hearts, "comment_count": comment_count},
                                points=[int(message_id)])

    def all_news(self):
        points, _ = self.client.scroll(NEWS, limit=1000, with_vectors=True, with_payload=True)
        return [(p.payload["message_id"], p.vector, p.payload) for p in points]

    def upsert_user(self, user_id: str, vector) -> None:
        self.client.upsert(USERS, points=[
            PointStruct(id=_user_point_id(user_id), vector=list(vector),
                        payload={"user_id": user_id})])

    def get_user(self, user_id: str):
        pts = self.client.retrieve(USERS, ids=[_user_point_id(user_id)], with_vectors=True)
        return pts[0].vector if pts else None
