

let currentView = 'chatbot';


document.addEventListener('DOMContentLoaded', function() {
    setupNavigation();
    loadStats();
    initializeChatbot();
});


function setupNavigation() {
    document.querySelectorAll('[data-view]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const view = this.getAttribute('data-view');
            switchView(view);
        });
    });
}

function switchView(view) {
    
    document.querySelectorAll('[data-view]').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-view="${view}"]`).classList.add('active');

    
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.style.display = 'none';
    });

    
    document.getElementById(`${view}-view`).style.display = 'block';
    currentView = view;

    
    switch(view) {
        case 'trends':
            loadTrends();
            break;
        case 'clusters':
            loadClusters();
            break;
        case 'articles':
            loadArticles();
            break;
        case 'search':
            break;
        case 'chatbot':
            initializeChatbot();
            break;
    }
}


async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        document.getElementById('stats-badge').textContent = 
            `${data.total_articles} articles, ${data.total_clusters} clusters`;
        
        document.getElementById('stats-panel').innerHTML = `
            <p><strong>Total Articles:</strong> ${data.total_articles}</p>
            <p><strong>Total Clusters:</strong> ${data.total_clusters}</p>
            <p><strong>Total Embeddings:</strong> ${data.total_embeddings}</p>
        `;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}


async function loadTrends() {
    const loadingEl = document.getElementById('trends-loading');
    const contentEl = document.getElementById('trends-content');
    
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';

    try {
        const response = await fetch('/api/trends');
        const data = await response.json();

        if (data.error) {
            contentEl.innerHTML = `<div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${data.error}</p>
            </div>`;
        } else {
            
            document.getElementById('total-clusters').textContent = data.total_clusters || 0;
            document.getElementById('growing-clusters').textContent = data.growing_clusters?.length || 0;
            document.getElementById('new-clusters').textContent = data.new_clusters?.length || 0;
            document.getElementById('declining-clusters').textContent = data.declining_clusters?.length || 0;

            
            document.getElementById('growing-list').innerHTML = 
                renderTrendList(data.growing_clusters || [], 'growing');
            document.getElementById('new-list').innerHTML = 
                renderTrendList(data.new_clusters || [], 'new');
            document.getElementById('declining-list').innerHTML = 
                renderTrendList(data.declining_clusters || [], 'declining');
        }

        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
    } catch (error) {
        console.error('Error loading trends:', error);
        loadingEl.style.display = 'none';
        contentEl.innerHTML = `<div class="alert alert-danger">Error loading trends: ${error.message}</div>`;
    }
}

function renderTrendList(items, type) {
    if (items.length === 0) {
        return `<div class="empty-state">
            <i class="fas fa-inbox"></i>
            <p>No ${type} clusters</p>
        </div>`;
    }

    return items.map(item => `
        <div class="trend-item ${type}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${item.cluster_id}</strong>
                    <span class="badge bg-secondary ms-2">${item.document_count} articles</span>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="viewCluster('${item.cluster_id}')">
                    View Details
                </button>
            </div>
            <div class="mt-2">
                <small class="text-muted">
                    Created: ${new Date(item.created_at).toLocaleString()}
                </small>
            </div>
        </div>
    `).join('');
}


async function loadClusters() {
    const loadingEl = document.getElementById('clusters-loading');
    const contentEl = document.getElementById('clusters-content');
    
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';

    try {
        const response = await fetch('/api/clusters');
        const data = await response.json();

        if (data.clusters && data.clusters.length > 0) {
            contentEl.innerHTML = data.clusters.map(cluster => `
                <div class="card cluster-card" onclick="viewCluster('${cluster.cluster_id}')">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="card-title">${cluster.cluster_id}</h6>
                                <p class="card-text">
                                    <span class="badge bg-primary">${cluster.document_count || 0} articles</span>
                                    ${cluster.summary ? `<p class="mt-2">${cluster.summary}</p>` : ''}
                                </p>
                                ${cluster.topic_stats && cluster.topic_stats.top_keywords ? `
                                    <div class="mt-2">
                                        ${cluster.topic_stats.top_keywords.slice(0, 5).map(kw => 
                                            `<span class="keyword-tag">${kw.keyword} (${kw.frequency})</span>`
                                        ).join('')}
                                    </div>
                                ` : ''}
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); viewCluster('${cluster.cluster_id}')">
                                View
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            contentEl.innerHTML = `<div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No clusters found</p>
            </div>`;
        }

        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
    } catch (error) {
        console.error('Error loading clusters:', error);
        loadingEl.style.display = 'none';
        contentEl.innerHTML = `<div class="alert alert-danger">Error loading clusters: ${error.message}</div>`;
    }
}


async function loadArticles() {
    const loadingEl = document.getElementById('articles-loading');
    const contentEl = document.getElementById('articles-content');
    const clusterFilter = document.getElementById('cluster-filter').value;
    
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';

    try {
        const url = `/api/articles${clusterFilter ? `?cluster_id=${clusterFilter}` : ''}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.articles && data.articles.length > 0) {
            contentEl.innerHTML = data.articles.map(article => `
                <div class="card article-card">
                    <div class="card-body">
                        <h6 class="article-title">${article.title || 'No title'}</h6>
                        <div class="article-meta">
                            <span class="badge bg-secondary">${article.source || 'Unknown'}</span>
                            ${article.cluster_id ? `<span class="badge bg-info">${article.cluster_id}</span>` : ''}
                            ${article.published_date ? `<span class="text-muted ms-2">${article.published_date}</span>` : ''}
                        </div>
                        <p class="article-snippet">${(article.description || article.text || '').substring(0, 200)}...</p>
                        ${article.url ? `<a href="${article.url}" target="_blank" class="btn btn-sm btn-outline-primary">Read More</a>` : ''}
                    </div>
                </div>
            `).join('');
        } else {
            contentEl.innerHTML = `<div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No articles found</p>
            </div>`;
        }

        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
    } catch (error) {
        console.error('Error loading articles:', error);
        loadingEl.style.display = 'none';
        contentEl.innerHTML = `<div class="alert alert-danger">Error loading articles: ${error.message}</div>`;
    }
}


async function viewCluster(clusterId) {
    const modal = new bootstrap.Modal(document.getElementById('clusterModal'));
    const modalBody = document.getElementById('cluster-modal-body');
    
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    modal.show();

    try {
        const response = await fetch(`/api/clusters/${clusterId}`);
        const data = await response.json();

        if (data.error) {
            modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        } else {
            const cluster = data.cluster;
            const articles = data.articles || [];
            const topics = data.topic_stats || {};

            modalBody.innerHTML = `
                <h6>Cluster ID: ${cluster.cluster_id}</h6>
                <p><strong>Articles:</strong> ${cluster.document_count || 0}</p>
                ${cluster.summary ? `<p><strong>Summary:</strong> ${cluster.summary}</p>` : ''}
                
                ${topics.top_keywords ? `
                    <h6 class="mt-3">Top Keywords</h6>
                    <div>
                        ${topics.top_keywords.map(kw => 
                            `<span class="keyword-tag">${kw.keyword} (${kw.frequency})</span>`
                        ).join('')}
                    </div>
                ` : ''}

                <h6 class="mt-4">Articles (${articles.length})</h6>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${articles.map(article => `
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>${article.title || 'No title'}</h6>
                                <p class="text-muted small">${article.source || 'Unknown'} - ${article.published_date || ''}</p>
                                <p class="small">${(article.description || article.text || '').substring(0, 150)}...</p>
                                ${article.url ? `<a href="${article.url}" target="_blank" class="btn btn-sm btn-outline-primary">Read</a>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading cluster:', error);
        modalBody.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}


async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    const resultsEl = document.getElementById('search-results');

    if (!query) {
        resultsEl.innerHTML = '<div class="alert alert-warning">Please enter a search query</div>';
        return;
    }

    resultsEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border" role="status"></div></div>';

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.articles && data.articles.length > 0) {
            resultsEl.innerHTML = `
                <p class="text-muted">Found ${data.count} articles</p>
                ${data.articles.map(article => `
                    <div class="card article-card mb-3">
                        <div class="card-body">
                            <h6 class="article-title">${article.title || 'No title'}</h6>
                            <div class="article-meta">
                                <span class="badge bg-secondary">${article.source || 'Unknown'}</span>
                                ${article.cluster_id ? `<span class="badge bg-info">${article.cluster_id}</span>` : ''}
                            </div>
                            <p class="article-snippet">${(article.description || article.text || '').substring(0, 200)}...</p>
                            ${article.url ? `<a href="${article.url}" target="_blank" class="btn btn-sm btn-outline-primary">Read More</a>` : ''}
                        </div>
                    </div>
                `).join('')}
            `;
        } else {
            resultsEl.innerHTML = '<div class="empty-state"><i class="fas fa-search"></i><p>No articles found</p></div>';
        }
    } catch (error) {
        console.error('Error searching:', error);
        resultsEl.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-query');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});


function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

function initializeChatbot() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        setTimeout(() => chatInput.focus(), 100);
    }
}

function clearChatHistory() {
    const messagesContainer = document.getElementById('chat-messages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="chat-message bot-message">
                <div class="message-content">
                    <i class="fas fa-robot text-primary"></i>
                    <p>Hello! I'm your news intelligence assistant. Ask me about today's latest news, trends, or any questions about the articles we've analyzed. I'll provide answers with bullet points and source citations.</p>
                </div>
            </div>
        `;
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    const sendBtn = document.getElementById('chat-send-btn');
    const messagesContainer = document.getElementById('chat-messages');

    if (!question) {
        return;
    }

    
    input.disabled = true;
    sendBtn.disabled = true;

    
    addChatMessage(question, 'user');

    
    input.value = '';

    
    const loadingId = addLoadingMessage();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question })
        });

        const data = await response.json();

        
        removeLoadingMessage(loadingId);

        if (data.error) {
            addChatMessage(`Sorry, I encountered an error: ${data.error}`, 'bot');
        } else {
            addChatMessage(data.answer, 'bot', false, true, data.sources || []);
        }
    } catch (error) {
        removeLoadingMessage(loadingId);
        addChatMessage(`Sorry, I couldn't process your question. Please try again.`, 'bot');
        console.error('Chat error:', error);
    } finally {
        
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

function addChatMessage(text, type, isSmall = false, formatBullets = false, sources = []) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    if (isSmall) {
        messageDiv.style.fontSize = '0.85rem';
        messageDiv.style.opacity = '0.7';
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (type === 'bot') {
        let formattedText = escapeHtml(text);
        if (formatBullets) {
            formattedText = formatBulletPoints(formattedText, sources);
        }
        contentDiv.innerHTML = `<i class="fas fa-robot text-primary"></i>${formattedText}`;
    } else {
        contentDiv.textContent = text;
    }
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageDiv;
}

function formatBulletPoints(text, sources = []) {
    const lines = text.split('\n');
    let formatted = '';
    
    const sourceMap = {};
    sources.forEach(source => {
        sourceMap[source.id] = source;
    });
    
    let inList = false;
    let listDepth = 0;
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (!line) {
            if (inList) {
                formatted += '</div>';
                inList = false;
                listDepth = 0;
            }
            formatted += '<br>';
            continue;
        }
        
        let processedLine = line;
        
        processedLine = processedLine.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        processedLine = processedLine.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        processedLine = escapeHtml(processedLine);
        processedLine = processedLine.replace(/&lt;strong&gt;(.+?)&lt;\/strong&gt;/g, '<strong>$1</strong>');
        processedLine = processedLine.replace(/&lt;em&gt;(.+?)&lt;\/em&gt;/g, '<em>$1</em>');
        
        if (/^#{1,3}\s/.test(line)) {
            const level = line.match(/^(#{1,3})/)[1].length;
            const headerText = line.replace(/^#{1,3}\s+/, '');
            const headerSize = level === 1 ? '1.5rem' : level === 2 ? '1.3rem' : '1.1rem';
            const headerWeight = 'bold';
            const headerMargin = level === 1 ? '1.5rem 0 1rem 0' : level === 2 ? '1.2rem 0 0.8rem 0' : '1rem 0 0.6rem 0';
            formatted += `<div style="font-size: ${headerSize}; font-weight: ${headerWeight}; margin: ${headerMargin}; color: #212529; border-bottom: ${level === 1 ? '2px' : '1px'} solid #e9ecef; padding-bottom: 0.5rem;">${escapeHtml(headerText)}</div>`;
            continue;
        }
        
        processedLine = processedLine.replace(/\[Source\s+(\d+(?:\s*,\s*Source\s+\d+)*)\]/g, (match, sourcesText) => {
            const sourceIds = sourcesText.split(/,?\s*Source\s+/).map(id => parseInt(id.trim())).filter(id => !isNaN(id));
            const sourceLinks = sourceIds.map(id => {
                const source = sourceMap[id];
                if (source) {
                    const title = source.title || 'Source ' + id;
                    const url = source.url || '#';
                    const sourceText = title.length > 40 ? title.substring(0, 40) + '...' : title;
                    return `<a href="${escapeHtml(url)}" target="_blank" class="source-link" title="${escapeHtml(title)}">[${escapeHtml(sourceText)}]</a>`;
                }
                return `[Source ${id}]`;
            });
            return sourceLinks.join(' ');
        });
        
        const isBullet = line.startsWith('- ') || line.startsWith('• ') || line.startsWith('* ');
        const isNumbered = /^\d+\.\s/.test(line);
        const isSubBullet = /^\s{2,}([-•*]|\d+\.)\s/.test(line);
        
        if (isBullet || isNumbered) {
            if (!inList) {
                formatted += '<div style="margin-left: 0;">';
                inList = true;
            }
            const indent = isSubBullet ? '40px' : '20px';
            const marginBottom = i < lines.length - 1 && (lines[i + 1].trim().startsWith('- ') || /^\d+\.\s/.test(lines[i + 1].trim())) ? '6px' : '10px';
            formatted += `<div style="margin-left: ${indent}; margin-bottom: ${marginBottom}; line-height: 1.7; padding-left: 4px;">${processedLine}</div>`;
        } else {
            if (inList) {
                formatted += '</div>';
                inList = false;
            }
            const isBoldLine = /^\*\*/.test(line) && /\*\*$/.test(line);
            const style = isBoldLine ? 'font-weight: 600; margin: 0.8rem 0; color: #212529;' : 'margin-bottom: 0.6rem; line-height: 1.7;';
            formatted += `<div style="${style}">${processedLine}</div>`;
        }
    }
    
    if (inList) {
        formatted += '</div>';
    }
    
    return formatted;
}

function displaySources(sources) {
    const messagesContainer = document.getElementById('chat-messages');
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'chat-message bot-message';
    sourcesDiv.style.marginTop = '10px';
    sourcesDiv.style.borderTop = '1px solid #e0e0e0';
    sourcesDiv.style.paddingTop = '10px';
    
    const sourcesHeader = document.createElement('div');
    sourcesHeader.className = 'message-content';
    sourcesHeader.style.fontWeight = 'bold';
    sourcesHeader.style.marginBottom = '8px';
    sourcesHeader.innerHTML = '<i class="fas fa-book text-info"></i> <strong>Sources:</strong>';
    sourcesDiv.appendChild(sourcesHeader);
    
    const sourcesList = document.createElement('div');
    sourcesList.style.marginLeft = '25px';
    sourcesList.style.fontSize = '0.9rem';
    
    sources.forEach((source, index) => {
        const sourceItem = document.createElement('div');
        sourceItem.style.marginBottom = '6px';
        sourceItem.style.padding = '4px';
        sourceItem.style.backgroundColor = '#f8f9fa';
        sourceItem.style.borderRadius = '4px';
        
        let sourceText = `<strong>[Source ${source.id}]</strong> ${escapeHtml(source.title || 'Untitled')}<br>`;
        sourceText += `<small style="color: #666;">${escapeHtml(source.source || 'Unknown source')}`;
        if (source.date) {
            sourceText += ` • ${escapeHtml(source.date)}`;
        }
        sourceText += '</small>';
        
        if (source.url) {
            sourceText += ` <a href="${escapeHtml(source.url)}" target="_blank" style="color: #007bff; text-decoration: none; margin-left: 8px;"><i class="fas fa-external-link-alt"></i></a>`;
        }
        
        sourceItem.innerHTML = sourceText;
        sourcesList.appendChild(sourceItem);
    });
    
    sourcesDiv.appendChild(sourcesList);
    messagesContainer.appendChild(sourcesDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addLoadingMessage() {
    const messagesContainer = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message bot-message';
    loadingDiv.id = 'chat-loading';
    loadingDiv.innerHTML = `
        <div class="chat-loading">
            <span></span><span></span><span></span>
        </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return 'chat-loading';
}

function removeLoadingMessage(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

