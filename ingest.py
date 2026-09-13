"""Phase 1-②③: vault 위키 노트를 읽어 청크로 쪼개고 임베딩해서 Chroma에 저장한다.
1회 실행하는 배치 스크립트. 다시 실행하면 기존 컬렉션을 지우고 새로 만든다.
"""

import os
import glob

import frontmatter
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()

VAULT_WIKI_PATH = os.environ.get(
    "VAULT_WIKI_PATH", "/Users/yijun/Obsidian Vault/llm-wiki/wiki"
)
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "mentor_wiki"

HEADER_SPLIT = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("##", "section")], strip_headers=False
)
CHUNK_SPLIT = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def load_notes() -> list[Document]:
    documents = []
    paths = sorted(glob.glob(os.path.join(VAULT_WIKI_PATH, "*.md")))
    skipped = []
    for path in paths:
        try:
            post = frontmatter.load(path)
        except Exception as e:
            skipped.append((os.path.basename(path), str(e)))
            continue
        title = post.get("title", os.path.basename(path))
        tags = post.get("tags", [])
        note_type = post.get("type", "")
        source = post.get("source", "")
        slug = os.path.splitext(os.path.basename(path))[0]

        sections = HEADER_SPLIT.split_text(post.content)
        for section in sections:
            for chunk in CHUNK_SPLIT.split_text(section.page_content):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "slug": slug,
                            "title": title,
                            "tags": ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags),
                            "type": note_type,
                            "source": source,
                            "section": section.metadata.get("section", ""),
                        },
                    )
                )
    if skipped:
        print(f"WARNING: skipped {len(skipped)} file(s) with invalid frontmatter:")
        for name, err in skipped:
            print(f"  - {name}: {err}")
    return documents


def main():
    print(f"reading notes from: {VAULT_WIKI_PATH}")
    docs = load_notes()
    print(f"loaded {len(docs)} chunks from wiki notes")

    embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
    )
    print(f"saved to chroma at: {PERSIST_DIR}")


if __name__ == "__main__":
    main()
