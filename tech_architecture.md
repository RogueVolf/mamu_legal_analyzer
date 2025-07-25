Data (Incoming) -> Modifications -> Data (Outgoing)

-- Step - 1: Building the context of the document

Approach - 1
Document -> Page -> LLM -> Summarise the Page -> Summaries -> Context of the Document

Approach - 2
Document -> Chunk (Recursive Chunker) -> Vector DB -> A retreival tool + Agent -> Context of the document


Final Approach:
Document + Legal Name of user as mentioned in Agreement -> Unstructured -> Semantic Chunks -> Pre-emptive search methodology to build CD from the chunks

Context of the Document:
Title - Title of the document
Type - Rent Agreement, Sale Deed, NDA, Employment Offer etc
Involved Parties - Who all are the entities in the document
Jurisdication - What country and region if applicable
Dates - Effective date
Duration - Duration of the agreement


10 chunks -> Aggregate -> CD complete ? Stop : Repeat with reduced keys

User Name + Document type + CD -> Risk factors relevant for user + Probable Topics/Clauses in the document

-- Step - 2: Creating Clause/Topics Descriptions
Semantic Chunks -> batch size 10 -> extract topics and clauses and risk factor tagging -> Final list of topics and clauses

Aggregate chunks of same topic and clauses into one window -> List of topics/clauses with aggregated data -> LLM -> Detailed descriptions of each topic/clause + Risk factors associated with each chunk/topic

-- Step - 3: Risk Analysis of the document
Aggregate chunks with common risk factors -> List of risk factors with aggregated chunks -> LLM -> Detailed risk factor analysis

-- Step - 4: Creating an overview layman explanation of the document
Summarise detailed topic/clause descriptions and risk factor analysis -> LLM -> Short summary & Detailed overview and explanation of the document