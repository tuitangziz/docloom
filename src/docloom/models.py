from dataclasses import dataclass, field


@dataclass(frozen=True)
class Passage:
    id: str
    document_id: str
    filename: str
    location: str
    text: str


@dataclass
class Document:
    id: str
    filename: str
    kind: str
    byte_size: int
    passages: list[Passage]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float
    lexical_score: float
    char_score: float
    dense_score: float | None = None


@dataclass(frozen=True)
class Citation:
    label: str
    filename: str
    location: str
    quote: str
    passage_id: str


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    mode: str
    warnings: list[str] = field(default_factory=list)
    refused: bool = False
