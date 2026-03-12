const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    const pathParts = window.location.pathname.split('/');
    const pmid = pathParts[pathParts.length - 1];
    
    if (pmid) {
        loadArticle(pmid);
    }
});

async function loadArticle(pmid) {
    const loading = document.getElementById('loading');
    const articleContent = document.getElementById('articleContent');
    const errorMessage = document.getElementById('errorMessage');
    
    loading.style.display = 'block';
    articleContent.style.display = 'none';
    errorMessage.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/article/${pmid}`);
        
        if (!response.ok) {
            throw new Error('文献未找到');
        }
        
        const article = await response.json();
        
        loading.style.display = 'none';
        articleContent.style.display = 'block';
        
        document.getElementById('articleTitle').textContent = article.title;
        
        const authors = article.authors && article.authors.length > 0 
            ? article.authors.join(', ') 
            : 'Unknown';
        document.getElementById('articleAuthors').textContent = authors;
        
        document.getElementById('articleJournal').textContent = article.journal || 'Unknown';
        document.getElementById('articleDate').textContent = article.pub_date || 'Unknown';
        document.getElementById('articlePmid').textContent = article.pmid;
        
        if (article.doi) {
            const doiContainer = document.getElementById('doiContainer');
            const doiLink = document.getElementById('articleDoi');
            doiLink.textContent = article.doi;
            doiLink.href = `https://doi.org/${article.doi}`;
            doiContainer.style.display = 'block';
        }
        
        const abstractElement = document.getElementById('articleAbstract');
        if (article.abstract) {
            abstractElement.textContent = article.abstract;
        } else {
            abstractElement.textContent = '暂无摘要';
            abstractElement.classList.add('no-abstract');
        }
        
    } catch (error) {
        console.error('加载文献错误:', error);
        loading.style.display = 'none';
        errorMessage.style.display = 'block';
    }
}
