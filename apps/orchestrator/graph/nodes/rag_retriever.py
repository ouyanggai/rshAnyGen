"""RAG Retriever Node"""
from apps.orchestrator.graph.state import AgentState
from apps.orchestrator.services.rag_pipeline import RAGPipelineClient

async def rag_retriever(state: AgentState):
    """Retrieve knowledge from RAG pipeline"""
    query = state.get("user_message")
    kb_ids = state.get("kb_ids", [])
    
    if not query:
        return {"retrieved_docs": []}

    client = RAGPipelineClient()
    try:
        results = await client.search(query, kb_ids=kb_ids)
        
        # Format for context
        docs = []
        for res in results:
            docs.append({
                "content": res.get("content"),
                "source": res.get("chunk_id"), # or metadata
                "score": res.get("score"),
                "metadata": res.get("metadata")
            })
            
        return {
            "retrieved_docs": docs,
            "citations": state.get("citations", []) # Append later
        }
    finally:
        await client.close()
