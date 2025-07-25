import re
import json
import time
import asyncio
import logging
import hashlib
import json_repair
from datetime import datetime
from dataclasses import asdict
from collections import defaultdict
from typing import List, Dict, Optional

from utils.llm_utils import ask_llm
from models.model import SemanticChunk,DocumentContext,TopicClause,RiskFactor

json_pattern = r"json\s*(\{.*?\})\s*"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class DocumentAnalyzer:
    """Main class for legal document analysis using LLM-driven approach"""
    
    def __init__(self, chunk_size: int = 10):
        """
        Initialize the document analyzer
        
        Args:
            ask_llm: Async function to call LLM (user-provided)
            chunk_size: Number of chunks to process in each batch
        """
        self.ask_llm = ask_llm
        self.chunk_size = chunk_size
        self.semantic_chunks: List[SemanticChunk] = []
        self.document_context: Optional[DocumentContext] = None
        self.probable_topics_clauses: List[str] = []
        self.probable_risk_factors: List[str] = []
        
    async def extract_document_context(self, document_text: str, user_legal_name: str) -> DocumentContext:
        """
        Extract context information from the document using LLM
        
        Args:
            document_text: Raw document text
            user_legal_name: Legal name of the user from agreement
            
        Returns:
            DocumentContext object
        """
        # Get first page or first 2000 characters for context extraction
        first_page = document_text[:2000]
        
        # Extract parties using LLM
        parties_prompt = f"""
        Analyze this document excerpt and extract all party names involved in this legal agreement.
        The user's legal name is: {user_legal_name}
        
        Document excerpt:
        {first_page}
        
        Please return a JSON object with the following format:
        {{
            "parties": ["Name1", "Name2", "Name3"],
            "user_role": "tenant|landlord|buyer|seller|employee|employer|client|contractor|party1|party2"
        }}
        
        Include the user's name and all other parties mentioned in the document.
        """
        
        parties_response = await self.ask_llm(parties_prompt)
        match = re.search(json_pattern, parties_response, re.DOTALL)

        if match:
            parties_response = match.group(1) 
            
        parties_data = json_repair.loads(parties_response)
        
        # Extract title and document type using LLM
        title_type_prompt = f"""
        Analyze this document and determine its title and type.
        
        Document excerpt:
        {first_page}
        
        Please return a JSON object with the following format:
        {{
            "title": "Exact title of the document",
            "document_type": "Rent Agreement|Sale Deed|NDA|Employment Offer|Service Agreement|Loan Agreement|Partnership Agreement|General Agreement",
            "confidence": "high|medium|low"
        }}
        """
        
        title_type_response = await self.ask_llm(title_type_prompt)
        
        match = re.search(json_pattern, title_type_response, re.DOTALL)

        if match:
            title_type_response = match.group(1) 
            
        title_type_data = json_repair.loads(title_type_response)
            
        # Extract dates using LLM
        dates_prompt = f"""
        Extract important dates from this document.
        
        Document excerpt:
        {first_page}
        
        Please return a JSON object with the following format:
        {{
            "effective_date": "date string or null",
            "duration": "duration description or null",
            "expiry_date": "date string or null"
        }}
        """
        
        dates_response = await self.ask_llm(dates_prompt)
        
        match = re.search(json_pattern, dates_response, re.DOTALL)

        if match:
            dates_response = match.group(1) 
            
        dates_data = json_repair.loads(dates_response)
        
        # Extract jurisdiction using heuristic (as requested)
        jurisdiction = self._extract_jurisdiction_heuristic(document_text)
        
        context = DocumentContext(
            title=title_type_data.get("title", "Untitled Document"),
            document_type=title_type_data.get("document_type", "General Agreement"),
            involved_parties=parties_data.get("parties", [user_legal_name]),
            jurisdiction=jurisdiction,
            effective_date=dates_data.get("effective_date"),
            duration=dates_data.get("duration"),
            user_legal_name=user_legal_name,
            user_role =parties_data.get("user_role","")
        )
        
        self.document_context = context
        logger.info(f"Extracted context: {context.document_type} document with {len(context.involved_parties)} parties")
        return context
    
    def _extract_jurisdiction_heuristic(self, text: str) -> str:
        """Extract jurisdiction information using heuristic approach"""
        jurisdiction_json_patterns = [
            r"(?i)(?:governed by|jurisdiction|courts? of)\s+([A-Za-z\s,]+?)(?:\.|;|\n)",
            r"(?i)(?:state of|country of|laws of)\s+([A-Za-z\s]+?)(?:\.|;|\n)"
        ]
        
        for json_pattern in jurisdiction_json_patterns:
            match = re.search(json_pattern, text)
            if match:
                return match.group(1).strip()
        
        return "Not specified"
    
    def create_semantic_chunks(self, document_text: str) -> List[SemanticChunk]:
        """
        Create semantic chunks from the document
        
        Args:
            document_text: Raw document text
            
        Returns:
            List of SemanticChunk objects
        """
        sections = self._split_into_sections(document_text)
        chunks = []
        
        for i, section in enumerate(sections):
            chunk_id = hashlib.md5(f"{i}_{section[:50]}".encode()).hexdigest()[:8]
            
            chunk = SemanticChunk(
                id=chunk_id,
                content=section,
                topics=[],
                clauses=[],
                risk_factors=[],
                start_position=document_text.find(section),
                end_position=document_text.find(section) + len(section)
            )
            chunks.append(chunk)
        
        self.semantic_chunks = chunks
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split document into logical sections"""
        section_json_patterns = [
            r'\n\s*\d+\.\s+',  # Numbered sections
            r'\n\s*[A-Z][A-Z\s]+:',  # ALL CAPS headings
            r'\n\s*WHEREAS',  # Whereas clauses
            r'\n\s*NOW THEREFORE',  # Therefore clauses
            r'\n\s*ARTICLE\s+\w+',  # Article sections
        ]
        
        sections = []
        current_section = ""
        lines = text.split('\n')
        
        for line in lines:
            is_section_break = any(re.match(json_pattern, '\n' + line) for json_pattern in section_json_patterns)
            
            if is_section_break and current_section.strip():
                sections.append(current_section.strip())
                current_section = line
            else:
                current_section += '\n' + line
        
        if current_section.strip():
            sections.append(current_section.strip())
        
        # If no clear sections found, split by paragraphs
        if len(sections) <= 2:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            sections = [p for p in paragraphs if len(p) > 100]
        
        return sections
    
    
    async def _get_probable_elements(self):
        """Get probable topics, clauses, and risk factors using LLM"""
        context_info = ""
        if self.document_context:
            context_info = f"""
            Document Type: {self.document_context.document_type}
            User: {self.document_context.user_legal_name}
            User Role: {self.document_context.user_role}
            Parties: {', '.join(self.document_context.involved_parties)}
            Jurisdiction: {self.document_context.jurisdiction}
            """
        
        elements_prompt = f"""
        Based on the document context and user information, predict the most probable topics, clauses, and risk factors that should be analyzed in this document.
        
        {context_info}
        
        Please return a JSON object with the following format:
        {{
            "probable_topics": ["Payment Terms", "Termination", "Obligations", ...],
            "probable_clauses": ["Penalty Clause", "Non-Compete", "Indemnity", ...],
            "probable_risk_factors": ["Financial Risk", "Legal Risk", "Operational Risk", ...]
        }}
        
        Focus on elements most relevant to the user and document type. Include 8-12 items in each category.
        """
        
        elements_response = await self.ask_llm(elements_prompt)
        match = re.search(json_pattern, elements_response, re.DOTALL)

        if match:
            elements_response = match.group(1)
             
        elements_data = json_repair.loads(elements_response)
        
        self.probable_topics_clauses = elements_data.get("probable_topics", []) + elements_data.get("probable_clauses", [])
        self.probable_risk_factors = elements_data.get("probable_risk_factors", [])
        
        logger.info(f"Identified {len(self.probable_topics_clauses)} probable topics/clauses and {len(self.probable_risk_factors)} risk factors")
    
    async def _analyze_chunks_with_llm(self) -> List[Dict]:
        """Analyze chunks in parallel using LLM"""
        # Create tasks for parallel processing
        tasks = []
        results = []
        counter = 0
        for chunk in self.semantic_chunks:
            task = self._analyze_single_chunk(chunk)
            tasks.append(task)
            counter += 1
            
            if counter == 5:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                counter = 0
                
                time.sleep(3)
        
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            tasks = []
            counter = 0
        
        # Process chunks in parallel
        # for i in range(len(tasks)):
        #     tasks_to_do = []
        #     if i + 2 > len(tasks):
        #         tasks_to_do = tasks[i:]
        #     else:
        #         tasks_to_do = tasks[i:i+2]
                
        #     task_results = await asyncio.gather(*tasks_to_do)
        #     results.extend(task_results)
        
        # results = await asyncio.gather(*tasks)
        
        return results
    
    async def _analyze_single_chunk(self, chunk: SemanticChunk) -> Dict:
        """Analyze a single chunk using LLM"""
        context_info = ""
        if self.document_context:
            context_info = f"""
            Document Type: {self.document_context.document_type}
            User: {self.document_context.user_legal_name}
            """
        
        analysis_prompt = f"""
        Analyze this document chunk and tag it with appropriate topics, clauses, and risk factors.
        
        {context_info}
        
        Document Chunk:
        {chunk.content}
        
        Possible Topics/Clauses to consider:
        {', '.join(self.probable_topics_clauses)}
        
        Possible Risk Factors to consider:
        {', '.join(self.probable_risk_factors)}
        
        Please return a JSON object with the following format:
        {{
            "topics": ["relevant topics from the list above"],
            "clauses": ["relevant clauses from the list above"],
            "risk_factors": ["relevant risk factors from the list above"],
            "key_points": ["2-3 key points from this chunk"],
            "importance_score": 1-10
        }}
        
        Only include items that are actually relevant to this specific chunk.
        """
        
        response = await self.ask_llm(analysis_prompt)
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            response = match.group(1)
        analysis_data = json_repair.loads(response)
        
        # Update chunk with analysis
        chunk.topics = analysis_data.get("topics", [])
        chunk.clauses = analysis_data.get("clauses", [])
        chunk.risk_factors = analysis_data.get("risk_factors", [])
        
        return {
            "chunk_id": chunk.id,
            "topics": chunk.topics,
            "clauses": chunk.clauses,
            "risk_factors": chunk.risk_factors,
            "key_points": analysis_data.get("key_points", []),
            "importance_score": analysis_data.get("importance_score", 5),
            "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
        }
    
    def _calculate_completeness(self, cd: Dict) -> float:
        """Calculate completeness score of context dictionary"""
        total_chunks = len(self.semantic_chunks)
        analyzed_chunks = len(cd.get("chunk_analysis", []))
        
        if total_chunks == 0:
            return 0.0
        
        basic_completeness = analyzed_chunks / total_chunks
        
        # Bonus for rich analysis
        total_topics = sum(len(chunk.get("topics", [])) for chunk in cd.get("chunk_analysis", []))
        total_risks = sum(len(chunk.get("risk_factors", [])) for chunk in cd.get("chunk_analysis", []))
        
        richness_bonus = min(0.2, (total_topics + total_risks) / (total_chunks * 5))
        
        return min(1.0, basic_completeness + richness_bonus)
    
    def _reduce_keys(self, cd: Dict) -> Dict:
        """Focus on high-importance chunks for next iteration"""
        important_chunks = []
        
        for chunk_analysis in cd.get("chunk_analysis", []):
            importance_score = chunk_analysis.get("importance_score", 5)
            if importance_score >= 7:  # Focus on high-importance chunks
                important_chunks.append(chunk_analysis)
        
        cd["chunk_analysis"] = important_chunks
        return cd
    
    async def create_topic_clause_descriptions(self) -> List[TopicClause]:
        """
        Step 2: Create detailed descriptions using LLM analysis of aggregated chunks
        
        Returns:
            List of TopicClause objects with LLM-generated descriptions
        """
        # Group chunks by topics and clauses
        topic_groups = defaultdict(list)
        clause_groups = defaultdict(list)
        
        for chunk in self.semantic_chunks:
            for topic in chunk.topics:
                topic_groups[topic].append(chunk)
            for clause in chunk.clauses:
                clause_groups[clause].append(chunk)
        
        # Process topics and clauses in parallel
        tasks = []
        counter = 0
        results = []
        # Add topic analysis tasks
        for topic_name, chunks in topic_groups.items():
            task = self._analyze_topic_clause_group(topic_name, chunks, "topic")
            tasks.append(task)
            counter += 1
            
            if counter == 5:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                counter = 0
                time.sleep(3)
        
        # Add clause analysis tasks
        for clause_name, chunks in clause_groups.items():
            task = self._analyze_topic_clause_group(clause_name, chunks, "clause")
            tasks.append(task)
            counter += 1
            
            if counter == 5:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                counter = 0
                time.sleep(3)
        
        # Any remainder tasks
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            tasks = []
            counter = 0
        
        logger.info(f"Created descriptions for {len(results)} topics/clauses")
        return results
    
    async def _analyze_topic_clause_group(self, name: str, chunks: List[SemanticChunk], element_type: str) -> TopicClause:
        """Analyze a group of chunks for a specific topic or clause using LLM"""
        aggregated_content = "\n\n---CHUNK SEPARATOR---\n\n".join([chunk.content for chunk in chunks])
        all_risks = list(set([risk for chunk in chunks for risk in chunk.risk_factors]))
        
        context_info = ""
        if self.document_context:
            context_info = f"""
            Document Type: {self.document_context.document_type}
            User: {self.document_context.user_legal_name}
            User Role: Based on parties - {', '.join(self.document_context.involved_parties)}
            """
        
        analysis_prompt = f"""
        Analyze this {element_type} based on the aggregated content from multiple document chunks.
        
        {context_info}
        
        {element_type.title()}: {name}
        
        Associated Risk Factors: {', '.join(all_risks)}
        
        Aggregated Content:
        {aggregated_content[:3000]}{'...' if len(aggregated_content) > 3000 else ''}
        
        Please provide a comprehensive analysis in JSON format:
        {{
            "description": "Detailed explanation of this {element_type} in layman terms",
            "user_implications": "What this means specifically for {self.document_context.user_legal_name if self.document_context else 'the user'}",
            "importance_level": "High|Medium|Low",
            "key_obligations": ["list of key obligations or requirements"],
            "potential_consequences": ["list of potential consequences if not followed"],
            "practical_advice": ["actionable advice for the user"]
        }}
        
        Focus on practical implications for the user and explain legal terms in simple language.
        """
        
        response = await self.ask_llm(analysis_prompt)
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            response = match.group(1)
        analysis_data = json_repair.loads(response)
        
        return TopicClause(
            name=f"{name} ({'Clause' if element_type == 'clause' else 'Topic'})",
            description=analysis_data.get("description", ""),
            aggregated_content=aggregated_content[:1000] + "..." if len(aggregated_content) > 1000 else aggregated_content,
            risk_factors=all_risks,
            importance_level=analysis_data.get("importance_level", "Medium")
        )
    
    async def analyze_risk_factors(self) -> List[RiskFactor]:
        """
        Step 3: Comprehensive risk analysis using LLM
        
        Returns:
            List of RiskFactor objects with LLM-generated analysis
        """
        # Group chunks by risk factors
        risk_groups = defaultdict(list)
        
        for chunk in self.semantic_chunks:
            for risk in chunk.risk_factors:
                risk_groups[risk].append(chunk)
        
        # Process risk factors in parallel
        tasks = []
        results = []
        counter = 0
        
        for risk_name, chunks in risk_groups.items():
            task = self._analyze_risk_factor_group(risk_name, chunks)
            tasks.append(task)
            counter += 1
            
            if counter == 5:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                counter = 0
                time.sleep(3)
                
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            tasks = []
            counter = 0
        
        logger.info(f"Analyzed {len(results)} risk factors")
        return results
    
    async def _analyze_risk_factor_group(self, risk_name: str, chunks: List[SemanticChunk]) -> RiskFactor:
        """Analyze a group of chunks for a specific risk factor using LLM"""
        affected_chunk_ids = [chunk.id for chunk in chunks]
        aggregated_content = "\n\n---CHUNK SEPARATOR---\n\n".join([chunk.content for chunk in chunks])
        
        context_info = ""
        if self.document_context:
            context_info = f"""
            Document Type: {self.document_context.document_type}
            User: {self.document_context.user_legal_name}
            User Role: {self.document_context.user_role}
            """
        
        risk_prompt = f"""
        Analyze this risk factor based on the aggregated content from multiple document chunks.
        
        {context_info}
        
        Risk Factor: {risk_name}
        Number of affected sections: {len(chunks)}
        
        Aggregated Content:
        {aggregated_content[:3000]}{'...' if len(aggregated_content) > 3000 else ''}
        
        Please provide a comprehensive risk analysis in JSON format:
        {{
            "description": "Detailed explanation of this risk in context of the document",
            "severity": "Critical|High|Medium|Low",
            "likelihood": "Very High|High|Medium|Low|Very Low",
            "user_impact": "Specific impact on {self.document_context.user_legal_name if self.document_context else 'the user'}",
            "financial_implications": "Potential financial impact if any",
            "legal_consequences": "Potential legal consequences",
            "mitigation_suggestions": ["specific actionable steps to mitigate this risk"]
        }}
        
        Be specific about the severity and provide practical mitigation strategies.
        """
        
        response = await self.ask_llm(risk_prompt)
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            response = match.group(1)
        risk_data = json_repair.loads(response)
        
        return RiskFactor(
            name=risk_name,
            description=risk_data.get("description", ""),
            user_impact=risk_data.get("user_impact",""),
            severity=risk_data.get("severity", "Medium"),
            affected_chunks=affected_chunk_ids,
            mitigation_suggestions=risk_data.get("mitigation_suggestions", [])
        )
    
    async def create_layman_overview(self, topic_clauses: List[TopicClause], risk_factors: List[RiskFactor]) -> Dict[str, str]:
        """
        Step 4: Create comprehensive layman explanation using LLM
        
        Args:
            topic_clauses: List of analyzed topics and clauses
            risk_factors: List of analyzed risk factors
            
        Returns:
            Dictionary with short summary and detailed overview
        """
        # Prepare summaries for LLM input
        topics_summary = []
        for tc in topic_clauses:
            topics_summary.append({
                "name": tc.name,
                "importance": tc.importance_level,
                "description": tc.description[:300] + "..." if len(tc.description) > 300 else tc.description
            })
        
        risks_summary = []
        for rf in risk_factors:
            risks_summary.append({
                "name": rf.name,
                "severity": rf.severity,
                "user_impact": rf.user_impact[:300] + "..." if len(rf.user_impact) > 300 else rf.user_impact
            })
        
        context_info = ""
        if self.document_context:
            context_info = f"""
            Document Type: {self.document_context.document_type}
            Title: {self.document_context.title}
            User: {self.document_context.user_legal_name}
            User Role: {self.document_context.user_role}
            Parties: {', '.join(self.document_context.involved_parties)}
            Duration: {self.document_context.duration or 'Not specified'}
            Jurisdiction: {self.document_context.jurisdiction}
            """
        
        overview_prompt = f"""
        Create a comprehensive layman explanation of this legal document based on the analyzed topics and risk factors.
        
        {context_info}
        
        Analyzed Topics/Clauses:
        {json.dumps(topics_summary, indent=2)}
        
        Analyzed Risk Factors:
        {json.dumps(risks_summary, indent=2)}
        
        Please provide both a short summary and detailed overview in JSON format:
        {{
            "short_summary": "2-3 sentence executive summary for quick understanding",
            "detailed_overview": "Comprehensive explanation broken into sections covering: Document Purpose, Key Rights & Obligations, Major Risks, Important Deadlines/Terms, and Recommendations"
        }}
        
        Write in plain English that a non-lawyer can understand. Focus on practical implications for {self.document_context.user_legal_name if self.document_context else 'the user'}.
        """
        
        response = await self.ask_llm(overview_prompt)
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            response = match.group(1)
        overview_data = json_repair.loads(response)
        
        return {
            "short_summary": overview_data.get("short_summary", ""),
            "detailed_overview": overview_data.get("detailed_overview", "")
        }
    
    async def analyze_document(self, document_text: str, user_legal_name: str) -> Dict:
        """
        Complete analysis pipeline using LLM-driven approach
        
        Args:
            document_text: Raw document text
            user_legal_name: Legal name of the user
            
        Returns:
            Complete analysis results
        """
        logger.info("Starting LLM-driven document analysis pipeline")
        
        # Step 1: Extract context and create chunks
        context = await self.extract_document_context(document_text, user_legal_name)
        chunks = self.create_semantic_chunks(document_text)
        await self._get_probable_elements()
        tagged_chunks = await self._analyze_chunks_with_llm()
        time.sleep(10)
        # Step 2: Create topic/clause descriptions using LLM
        topic_clauses = await self.create_topic_clause_descriptions()
        time.sleep(10)
        # Step 3: Risk analysis using LLM
        risk_factors = await self.analyze_risk_factors()
        time.sleep(10)
        # Step 4: Layman overview using LLM
        overview = await self.create_layman_overview(topic_clauses, risk_factors)
        
        results = {
            "document_context": asdict(context),
            "context_dictionary": asdict(self.document_context),
            "semantic_chunks": [asdict(chunk) for chunk in chunks],
            "topic_clauses": [asdict(tc) for tc in topic_clauses],
            "risk_factors": [asdict(rf) for rf in risk_factors],
            "overview": overview,
            "analysis_metadata": {
                "total_chunks": len(chunks),
                "total_topics_clauses": len(topic_clauses),
                "total_risk_factors": len(risk_factors),
                "high_risk_items": len([rf for rf in risk_factors if rf.severity in ["Critical", "High"]]),
                "analysis_timestamp": datetime.now().isoformat(),
                "llm_calls_made": "Multiple async calls for parallel processing"
            }
        }
        
        logger.info("LLM-driven document analysis completed successfully")
        return results