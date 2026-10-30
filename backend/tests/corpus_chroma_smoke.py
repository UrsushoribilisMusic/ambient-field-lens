import json,tempfile
from pathlib import Path
import chromadb
from chromadb.api.types import EmbeddingFunction
from providers.corpus_versions import BASELINE,manifest,read_snapshot,stage_repair,database_path,guarded_collection
class Embed(EmbeddingFunction):
 def __init__(self): pass
 def __call__(self,input): return [[1.0,0.0] for _ in input]
 @staticmethod
 def name(): return 'synthetic-repair-smoke'
 @staticmethod
 def get_config(): return {}
 @staticmethod
 def build_from_config(config): return Embed()
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);embed=Embed();client=chromadb.PersistentClient(path=str(root/'chroma'))
 coll=client.create_collection(BASELINE,embedding_function=embed)
 meta={'source':'synthetic','source_sha256':'a'*64,'source_commit':'test'}
 coll.add(ids=['old-'+str(i) for i in range(38)],documents=['Synthetic old manual '+str(i) for i in range(38)],metadatas=[meta]*38,embeddings=[[.25,.75]]*38)
 report={'collection':BASELINE,'records':38,'fingerprint':'b'*64}
 (root/'ingestion-report.json').write_text(json.dumps(report));pins={BASELINE:manifest(report,read_snapshot(coll))}
 result=stage_repair(client,root,embed,'Synthetic authored repair passage.','test-wiki/page','test-revision','test-reviewer',pins)
 pin=result['candidate_pin'];name=pin['collection']
 assert stage_repair(client,root,embed,'Synthetic authored repair passage.','test-wiki/page','test-revision','test-reviewer',pins)==result
 new=guarded_collection(chromadb.PersistentClient(path=str(database_path(root,name))),name,root,embed,{**pins,name:pin})
 assert new.count()==39 and coll.count()==38
 assert read_snapshot(coll)['embeddings']==[[.25,.75]]*38
 print(json.dumps({'actual_chromadb_version':chromadb.__version__,'baseline_count':coll.count(),'staged_count':new.count(),'idempotent':True,'baseline_vectors_preserved':True,'network_embeddings':False,'gpu':False}))
