from langchain_google_alloydb_pg import AlloyDBEngine
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_alloydb_pg import AlloyDBVectorStore
import json, glob
from langchain_community.document_loaders import TextLoader, WebBaseLoader


PROJECT_ID = "redacted"  # @param {type:"string"}
REGION = "redacted"  # @param {type: "string"}
CLUSTER = "redacted"  # @param {type: "string"}
INSTANCE = "redacted"  # @param {type: "string"}
DATABASE = "redacted"  # @param {type: "string"}

TABLE_NAME_FAQ = "faq"  # @param {type: "string"}
TABLE_NAME_HS = "hscode"  # @param {type: "string"}

engine =  AlloyDBEngine.from_instance(
    project_id=PROJECT_ID,
    region=REGION,
    cluster=CLUSTER,
    instance=INSTANCE,
    database=DATABASE,
    user="redacted",
    password="redacted"
)


embedding = VertexAIEmbeddings(model_name="text-multilingual-embedding-002")


LOAD = False

try:
    engine.init_vectorstore_table(
    table_name=TABLE_NAME_FAQ,
    vector_size=768,  # Vector size for VertexAI model(textembedding-gecko@latest)
        )

    engine.init_vectorstore_table(
    table_name=TABLE_NAME_HS,
    vector_size=768,  # Vector size for VertexAI model(textembedding-gecko@latest)
    )


except :pass

store =  AlloyDBVectorStore.create_sync(
        
        engine=engine,
        table_name=TABLE_NAME_FAQ,
        embedding_service=embedding,
    )


store_hs =  AlloyDBVectorStore.create_sync(
        
        engine=engine,
        table_name=TABLE_NAME_HS,
        embedding_service=embedding,
    )


if LOAD:


       
    urls = []
    jsonl = open("dataset/urls.jsonl", "r", encoding="utf8").readlines()
    for i in jsonl:
        l = json.loads(i.replace(",", ""))
        urls.append(l['link'])
    urls = [x for x in urls if "https://www.beacukai.go.id/faq" in x]

    urls = set(urls)    
    urls = list(urls)    
    def load_document(url):
        print(url)
        return WebBaseLoader(url).load()

    print("load WebBaseLoader sources")
    docs_faq = []

    for url in urls:
        docs_faq.append(load_document(url))

    

    for i in docs_faq:
        store.add_documents(i)

    
    docs = []
    
    print("load JSON sources")
    print(glob.glob("insw/*.json"))
    for js in glob.glob("insw/*.json"):
        try:
            docs.append(
                TextLoader(file_path=js).load()
            )
        except Exception as e:  
            print(e)
            continue
    
    
    
        print(js)
        
    for d in docs:
        try:
            store_hs.add_documents(d)
        except:pass




        