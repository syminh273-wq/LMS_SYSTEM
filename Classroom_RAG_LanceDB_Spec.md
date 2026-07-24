# Classroom RAG với LanceDB

## Mục tiêu

Chỉ tìm kiếm tài liệu thuộc **đúng Classroom** bằng cách filter
`classroom_id` trước khi thực hiện Vector Search.

## Luồng xử lý

``` text
User Question
      │
      ▼
Generate Embedding
      │
      ▼
LanceDB Search
      │
      ├─ Metadata Filter
      │      classroom_id = current_classroom
      │
      └─ Vector Similarity Search
              │
              ▼
          Top-K Chunks
              │
              ▼
        Build Prompt
              │
              ▼
             LLM
              │
              ▼
            Answer
```

## Metadata

  Field          Mô tả
  -------------- ------------------
  id             Chunk ID
  classroom_id   Lớp học
  document_id    Tài liệu nguồn
  chunk_index    Thứ tự chunk
  content        Nội dung
  embedding      Vector embedding

## Insert Flow

1.  Upload tài liệu.
2.  Parse nội dung.
3.  Chia thành các chunk.
4.  Sinh embedding.
5.  Lưu vào LanceDB kèm metadata (`classroom_id`, `document_id`, ...).

## Search Flow

1.  Người dùng gửi câu hỏi.
2.  Sinh embedding cho câu hỏi.
3.  Filter theo `classroom_id`.
4.  Thực hiện Vector Similarity Search.
5.  Lấy Top-K chunks.
6.  Ghép context và gửi vào LLM.

Ví dụ:

``` python
results = (
    table.search(query_embedding)
         .where(f"classroom_id = '{classroom_id}'")
         .limit(5)
)
```

## Lợi ích

-   Không rò rỉ dữ liệu giữa các Classroom.
-   Tăng độ chính xác của kết quả.
-   Hỗ trợ mở rộng thêm metadata như:
    -   lesson_id
    -   chapter_id
    -   tags
    -   language
    -   status
