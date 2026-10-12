"""Structure-aware chunking preserving sections, tables, and units."""
import re
from typing import List, Dict, Any

def normalize_text(text: str) -> str:
    """Normalizes whitespace while preserving units, special symbols, and line breaks."""
    # Replace multiple empty lines with double line break
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip trailing whitespace on each line
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def create_chunks(
    parsed_sections: List[Dict[str, Any]],
    doc_id: str,
    product_id: int,
    customer_id: int | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """Splits extracted sections into structured chunks with rich metadata."""
    all_chunks = []
    chunk_counter = 0

    for section in parsed_sections:
        page_num = section.get("page_number", 1)
        sec_title = section.get("section_title", "General")
        raw_content = normalize_text(section.get("content", ""))

        if not raw_content:
            continue

        # If content contains table blocks, avoid breaking tables in awkward places
        paragraphs = raw_content.split('\n\n')
        current_chunk_text = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk_text) + len(para) < chunk_size:
                current_chunk_text += ("\n\n" if current_chunk_text else "") + para
            else:
                if current_chunk_text:
                    chunk_counter += 1
                    all_chunks.append({
                        "chunk_id": f"{doc_id}_c{chunk_counter}",
                        "product_id": product_id,
                        "customer_id": customer_id,
                        "chunk_index": chunk_counter,
                        "page_number": page_num,
                        "section_title": sec_title,
                        "content": current_chunk_text.strip(),
                        "token_count": len(current_chunk_text.split())
                    })
                    # Overlap with last portion if it's text
                    overlap_text = current_chunk_text[-chunk_overlap:] if len(current_chunk_text) > chunk_overlap else ""
                    current_chunk_text = (overlap_text + "\n" + para).strip()
                else:
                    # Single paragraph exceeds chunk_size, split by sentences or lines
                    lines = para.split('\n')
                    sub_buf = ""
                    for line in lines:
                        if len(sub_buf) + len(line) < chunk_size:
                            sub_buf += ("\n" if sub_buf else "") + line
                        else:
                            if sub_buf:
                                chunk_counter += 1
                                all_chunks.append({
                                    "chunk_id": f"{doc_id}_c{chunk_counter}",
                                    "product_id": product_id,
                                    "customer_id": customer_id,
                                    "chunk_index": chunk_counter,
                                    "page_number": page_num,
                                    "section_title": sec_title,
                                    "content": sub_buf.strip(),
                                    "token_count": len(sub_buf.split())
                                })
                            sub_buf = line
                    if sub_buf:
                        current_chunk_text = sub_buf

        if current_chunk_text.strip():
            chunk_counter += 1
            all_chunks.append({
                "chunk_id": f"{doc_id}_c{chunk_counter}",
                "product_id": product_id,
                "customer_id": customer_id,
                "chunk_index": chunk_counter,
                "page_number": page_num,
                "section_title": sec_title,
                "content": current_chunk_text.strip(),
                "token_count": len(current_chunk_text.split())
            })

    return all_chunks
