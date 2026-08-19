from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from langchain_core.documents import Document
from pypdf import PdfReader

from app.core.config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE, UPLOAD_DIR


class DocumentService:
    async def save_and_extract_pdf(
        self,
        file: UploadFile,
        owner_id: str | None = None,
    ) -> dict:
        self._validate_file_type(file)

        content = await file.read()
        self._validate_file_size(content)

        document_id = str(uuid4())
        original_filename = file.filename or "document.pdf"
        safe_filename = self._create_safe_filename(
            original_filename,
            document_id,
        )
        file_path = UPLOAD_DIR / safe_filename

        try:
            file_path.write_bytes(content)

            extracted_data = self._extract_pages(
                file_path=file_path,
                document_id=document_id,
                original_filename=original_filename,
                owner_id=owner_id,
            )
        except HTTPException:
            if file_path.exists():
                file_path.unlink()

            raise
        except Exception as error:
            if file_path.exists():
                file_path.unlink()

            raise HTTPException(
                status_code=422,
                detail=f"Unable to process PDF: {error}",
            ) from error

        return {
            "document_id": document_id,
            "filename": original_filename,
            "stored_filename": safe_filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "page_count": extracted_data["page_count"],
            "character_count": extracted_data["character_count"],
            "documents": extracted_data["documents"],
        }

    def _validate_file_type(self, file: UploadFile) -> None:
        filename = file.filename or ""

        if file.content_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Only PDF files are supported",
            )

        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=415,
                detail="File must have a .pdf extension",
            )

    def _validate_file_size(self, content: bytes) -> None:
        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF size cannot exceed 10 MB",
            )

    def _create_safe_filename(
        self,
        original_filename: str,
        document_id: str,
    ) -> str:
        filename = Path(original_filename).name
        filename = filename.replace(" ", "_")

        return f"{document_id}_{filename}"

    def _extract_pages(
        self,
        file_path: Path,
        document_id: str,
        original_filename: str,
        owner_id: str | None = None,
    ) -> dict:
        reader = PdfReader(str(file_path))

        documents: list[Document] = []
        character_count = 0

        for page_index, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            page_text = page_text.strip()

            if not page_text:
                continue

            character_count += len(page_text)

            documents.append(
                Document(
                    page_content=page_text,
                    metadata={
                        "document_id": document_id,
                        "filename": original_filename,
                        "page": page_index + 1,
                        "source": str(file_path),
                        "owner_id": owner_id or "legacy",
                    },
                )
            )

        if not documents:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text was found. "
                    "The PDF may be scanned or image-based."
                ),
            )

        return {
            "documents": documents,
            "page_count": len(reader.pages),
            "character_count": character_count,
        }


document_service = DocumentService()
