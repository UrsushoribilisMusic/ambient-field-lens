"""Only exact retrieved text may supply non-geometric correction instructions."""
import re


def retrieved(chunks,chunk_id,quote):
    if not isinstance(quote,str) or not quote.strip() or len(quote)>240:
        raise ValueError('bounded_exact_source_quote_required')
    matches=[c for c in chunks if c.get('id')==chunk_id]
    if len(matches)!=1:raise ValueError('unique_retrieved_chunk_required')
    chunk=matches[0]
    if quote not in chunk['text'] or not re.fullmatch('[a-f0-9]{64}',chunk.get('source_sha256','')):
        raise ValueError('correction_not_supported_by_retrieved_source')
    return {'text':quote,'chunk_id':chunk_id,'source_sha256':chunk['source_sha256'],'origin':'exact_retrieved_passage'}
