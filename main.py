import os
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from Bio import Entrez
from settings import PUBMED_EMAIL, PUBMED_API_KEY

Entrez.email = PUBMED_EMAIL
API_KEY = PUBMED_API_KEY if PUBMED_API_KEY else None

app = FastAPI(title="PaperFinding API", description="文献检索系统后端API")

# 添加中间件，在每个特定的路径操作处理每个请求之前运行，也会在返回每个响应之前运行
app.add_middleware(
    CORSMiddleware,           # 跨域资源共享，解决前端和后端不在同一源下时的通信问题
    allow_origins=["*"],      # 允许的源
    allow_credentials=True,   # 启用跨域请求时支持 cookies
    allow_methods=["*"],      # 允许所有 HTTP 方法
    allow_headers=["*"],      # 允许所有请求头
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 将位于 static 目录下的静态文件提供给前端访问
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

class Article(BaseModel):
    pmid: str
    title: str
    authors: List[str]
    journal: str
    pub_date: str
    abstract: Optional[str] = None
    doi: Optional[str] = None

class SearchResult(BaseModel):
    total_count: int
    articles: List[Article]

def search_pubmed(query: str, start: int = 0, max_results: int = 10) -> SearchResult:
    try:
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            retstart=start,
            sort="relevance",
            retmode="xml",
            api_key=API_KEY
        )
        
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record.get("IdList", [])
        total_count = int(record.get("Count", 0))
        
        if not id_list:
            return SearchResult(total_count=0, articles=[])
        
        articles = fetch_details_xml(id_list)
        
        return SearchResult(total_count=total_count, articles=articles)
        
    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return SearchResult(total_count=0, articles=[])

def fetch_details_xml(pmids: List[str]) -> List[Article]:
    articles = []
    
    if not pmids:
        return articles
    
    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmids),
            rettype="xml",
            retmode="xml",
            api_key=API_KEY
        )
        
        records = Entrez.read(handle)
        handle.close()
        
        for article in records.get('PubmedArticle', []):
            try:
                medline = article.get('MedlineCitation', {})
                
                pmid = str(medline.get('PMID', ''))
                article_data = medline.get('Article', {})
                title = article_data.get('ArticleTitle', 'No title')
                
                authors = []
                for author in article_data.get('AuthorList', []):
                    if isinstance(author, dict):
                        last_name = author.get('LastName', '')
                        fore_name = author.get('ForeName', '')
                        if last_name:
                            name = f"{fore_name} {last_name}".strip()
                            authors.append(name)
                
                journal_info = article_data.get('Journal', {})
                journal = journal_info.get('Title', '')
                
                journal_date = journal_info.get('JournalIssue', {}).get('PubDate', {})
                year = journal_date.get('Year', '')
                month = journal_date.get('Month', '')
                day = journal_date.get('Day', '')
                
                if year:
                    pub_date = f"{year}"
                    if month:
                        pub_date += f" {month}"
                    if day:
                        pub_date += f" {day}"
                else:
                    pub_date = ''
                
                abstract_data = article_data.get('Abstract', {})
                abstract_text = abstract_data.get('AbstractText', [])
                if isinstance(abstract_text, list):
                    abstract = ' '.join(abstract_text)
                else:
                    abstract = abstract_text
                
                id_list = article.get('PubmedData', {}).get('ArticleIdList', [])
                doi = None
                for id_item in id_list:
                    if hasattr(id_item, 'attributes') and id_item.attributes.get('IdType') == 'doi':
                        doi = str(id_item)
                        break
                
                articles.append(Article(
                    pmid=pmid,
                    title=title,
                    authors=authors,
                    journal=journal,
                    pub_date=pub_date,
                    abstract=abstract if abstract else None,
                    doi=doi
                ))
                
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue
        
    except Exception as e:
        print(f"Error fetching details: {e}")
        import traceback
        traceback.print_exc()
    
    return articles

def get_article_by_pmid(pmid: str) -> Optional[Article]:
    articles = fetch_details_xml([pmid])
    return articles[0] if articles else None

@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join(BASE_DIR, "templates", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/about", response_class=HTMLResponse)
async def about():
    with open(os.path.join(BASE_DIR, "templates", "about.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/article/{pmid}", response_class=HTMLResponse)
async def article_detail(pmid: str):
    with open(os.path.join(BASE_DIR, "templates", "article.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/search", response_model=SearchResult)
async def search(
    q: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=50, description="每页结果数")
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="搜索关键词不能为空")
    
    start = (page - 1) * per_page
    result = search_pubmed(q, start=start, max_results=per_page)
    return result

@app.get("/api/article/{pmid}")
async def get_article(pmid: str):
    article = get_article_by_pmid(pmid)
    if not article:
        raise HTTPException(status_code=404, detail="文献未找到")
    return article

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
