from dataclasses import dataclass
from typing import List, Optional, Callable

@dataclass
class DocumentContext:
    """Context information extracted from the document"""
    title: str
    document_type: str
    involved_parties: List[str]
    jurisdiction: str
    effective_date: Optional[str]
    duration: Optional[str]
    user_legal_name: str
    user_role: str

@dataclass
class SemanticChunk:
    """Represents a semantic chunk of the document"""
    id: str
    content: str
    topics: List[str]
    clauses: List[str]
    risk_factors: List[str]
    start_position: int
    end_position: int

@dataclass
class TopicClause:
    """Detailed description of a topic or clause"""
    name: str
    description: str
    aggregated_content: str
    risk_factors: List[str]
    importance_level: str  # High, Medium, Low

@dataclass
class RiskFactor:
    """Risk factor analysis"""
    name: str
    description: str
    severity: str  # Critical, High, Medium, Low
    user_impact:  str
    affected_chunks: List[str]
    mitigation_suggestions: List[str]
    
    