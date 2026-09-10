import json
from datetime import datetime, timezone
from typing import Optional, List
from backend.app.core.database import get_db_connection
from backend.app.models.document import DocumentModel
from backend.app.core.logging import logger

class DocumentRepository:
    @staticmethod
    def save_or_update(doc: DocumentModel) -> DocumentModel:
        now_str = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check if document with document_name already exists
            cursor.execute(
                "SELECT id FROM documents WHERE document_name = ? ORDER BY id DESC LIMIT 1",
                (doc.document_name,)
            )
            existing = cursor.fetchone()

            if existing:
                doc_id = existing["id"]
                cursor.execute("""
                    UPDATE documents
                    SET document_type = ?,
                        processing_status = ?,
                        overall_confidence = ?,
                        file_validation = ?,
                        extracted_data = ?,
                        validation = ?,
                        processing_metadata = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    doc.document_type,
                    doc.processing_status,
                    doc.overall_confidence,
                    json.dumps(doc.file_validation),
                    json.dumps(doc.extracted_data),
                    json.dumps(doc.validation),
                    json.dumps(doc.processing_metadata),
                    now_str,
                    doc_id
                ))
                conn.commit()
                doc.id = doc_id
                doc.updated_at = now_str
                logger.info(f"Updated existing document: {doc.document_name} (ID: {doc_id})")
            else:
                cursor.execute("""
                    INSERT INTO documents (
                        document_name, document_type, processing_status,
                        overall_confidence, file_validation, extracted_data,
                        validation, processing_metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc.document_name,
                    doc.document_type,
                    doc.processing_status,
                    doc.overall_confidence,
                    json.dumps(doc.file_validation),
                    json.dumps(doc.extracted_data),
                    json.dumps(doc.validation),
                    json.dumps(doc.processing_metadata),
                    doc.created_at or now_str,
                    now_str
                ))
                conn.commit()
                doc.id = cursor.lastrowid
                doc.created_at = doc.created_at or now_str
                doc.updated_at = now_str
                logger.info(f"Inserted new document: {doc.document_name} (ID: {doc.id})")
            return doc

    @staticmethod
    def get_by_name(document_name: str) -> Optional[DocumentModel]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE document_name = ? ORDER BY id DESC LIMIT 1",
                (document_name,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return DocumentRepository._row_to_model(row)

    @staticmethod
    def get_by_id(doc_id: int) -> Optional[DocumentModel]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return DocumentRepository._row_to_model(row)

    @staticmethod
    def list_all() -> List[DocumentModel]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY id DESC")
            rows = cursor.fetchall()
            return [DocumentRepository._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> DocumentModel:
        return DocumentModel(
            id=row["id"],
            document_name=row["document_name"],
            document_type=row["document_type"],
            processing_status=row["processing_status"],
            overall_confidence=row["overall_confidence"],
            file_validation=json.loads(row["file_validation"]),
            extracted_data=json.loads(row["extracted_data"]),
            validation=json.loads(row["validation"]),
            processing_metadata=json.loads(row["processing_metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
