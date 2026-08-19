import re
import sqlite3
from collections import Counter
from pathlib import Path
from threading import RLock

from langchain_core.documents import Document

from app.core.config import KNOWLEDGE_GRAPH_DATABASE_PATH


class KnowledgeGraphService:
    def __init__(self, database_path: str | Path = KNOWLEDGE_GRAPH_DATABASE_PATH) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS graph_entities (
                    owner_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    name TEXT NOT NULL COLLATE NOCASE,
                    mentions INTEGER NOT NULL,
                    PRIMARY KEY (owner_id, document_id, name)
                );
                CREATE TABLE IF NOT EXISTS graph_relations (
                    owner_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL COLLATE NOCASE,
                    target TEXT NOT NULL COLLATE NOCASE,
                    weight INTEGER NOT NULL,
                    PRIMARY KEY (owner_id, document_id, source, target)
                );
                """
            )

    def index_documents(self, documents: list[Document]) -> dict[str, int]:
        entities: Counter[str] = Counter()
        relations: Counter[tuple[str, str]] = Counter()
        if not documents:
            return {"entities": 0, "relations": 0}
        metadata = documents[0].metadata
        owner_id = str(metadata.get("owner_id", "legacy"))
        document_id = str(metadata["document_id"])

        for document in documents:
            page_entities = sorted(set(self.extract_entities(document.page_content)))
            entities.update(page_entities)
            for index, source in enumerate(page_entities):
                for target in page_entities[index + 1:]:
                    relations[(source, target)] += 1

        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM graph_entities WHERE owner_id = ? AND document_id = ?",
                (owner_id, document_id),
            )
            self._connection.execute(
                "DELETE FROM graph_relations WHERE owner_id = ? AND document_id = ?",
                (owner_id, document_id),
            )
            self._connection.executemany(
                "INSERT INTO graph_entities VALUES (?, ?, ?, ?)",
                [(owner_id, document_id, name, count) for name, count in entities.items()],
            )
            self._connection.executemany(
                "INSERT INTO graph_relations VALUES (?, ?, ?, ?, ?)",
                [
                    (owner_id, document_id, source, target, weight)
                    for (source, target), weight in relations.items()
                ],
            )
        return {"entities": len(entities), "relations": len(relations)}

    def extract_entities(self, text: str) -> list[str]:
        candidates = re.findall(
            r"\b(?:[A-Z][A-Za-z0-9+#.-]*)(?:\s+[A-Z][A-Za-z0-9+#.-]*){0,3}\b",
            text,
        )
        ignored = {"The", "This", "That", "These", "Those", "A", "An", "I"}
        return [value.strip(" .-") for value in candidates if value not in ignored]

    def query(
        self,
        query: str,
        owner_id: str,
        document_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        terms = [term.lower() for term in re.findall(r"[a-z0-9+#.-]+", query.lower())]
        clauses = ["owner_id = ?"]
        parameters: list[object] = [owner_id]
        if document_id:
            clauses.append("document_id = ?")
            parameters.append(document_id)
        where = " AND ".join(clauses)
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM graph_entities WHERE {where} ORDER BY mentions DESC",
                parameters,
            ).fetchall()
            matches = [
                dict(row) for row in rows
                if any(term in row["name"].lower() for term in terms)
            ][:limit]
            names = [row["name"] for row in matches]
            relations = []
            if names:
                placeholders = ",".join("?" for _ in names)
                relations = [
                    dict(row)
                    for row in self._connection.execute(
                        f"""SELECT * FROM graph_relations
                        WHERE {where} AND (source IN ({placeholders}) OR target IN ({placeholders}))
                        ORDER BY weight DESC LIMIT ?""",
                        [*parameters, *names, *names, limit],
                    ).fetchall()
                ]
        return {"entities": matches, "relations": relations}

    def stats(self) -> dict[str, int]:
        with self._lock:
            entities = self._connection.execute(
                "SELECT COUNT(*) AS count FROM graph_entities"
            ).fetchone()["count"]
            relations = self._connection.execute(
                "SELECT COUNT(*) AS count FROM graph_relations"
            ).fetchone()["count"]
        return {"entities": int(entities), "relations": int(relations)}

    def close(self) -> None:
        self._connection.close()


knowledge_graph_service = KnowledgeGraphService()
