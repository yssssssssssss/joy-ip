// IP形象匹配系统前端交互逻辑

class ImageMatcherApp {
    constructor() {
        // 确保DOM已加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.init();
            });
        } else {
            this.init();
        }
    }

    init() {
         try {
             this.initializeElements();
             this.bindEvents();
             this.checkServerHealth();
             this.dimensionMappings = this.initializeDimensionMappings();
             // 初始化图表管理器
             this.chartInstances = new Map();
             // SSE日志流对象
             this.logEventSource = null;
         } catch (error) {
             console.error('应用初始化失败:', error);
             this.showError('应用初始化失败，请刷新页面重试');
         }
     }

    initializeElements() {
        // 获取DOM元素并检查是否存在
        const elements = {
            requirementInput: 'requirement-input',
            searchBtn: 'search-btn',
            headAnalysisSection: 'head-analysis-section',
            headAnalysisGrid: 'head-analysis-grid',
            headResultsSection: 'head-results-section',
            headResultsGrid: 'head-results-grid',
            bodyAnalysisSection: 'body-analysis-section',
            bodyAnalysisGrid: 'body-analysis-grid',
            bodyResultsSection: 'body-results-section',
            bodyResultsGrid: 'body-results-grid',
            errorSection: 'error-section',
            loadingSection: 'loading-section',
            errorText: 'error-text',
            imageModal: 'image-modal',
            modalImage: 'modal-image',
            modalTitle: 'modal-title',
            modalScore: 'modal-score',
            modalRequirementFeatures: 'modal-requirement-features'
        };

        // 初始化所有元素
        for (const [key, id] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (!element) {
                console.error(`找不到DOM元素: ${id}`);
                throw new Error(`必需的DOM元素不存在: ${id}`);
            }
            this[key] = element;
        }

        // 获取按钮内部元素
        this.btnText = this.searchBtn.querySelector('.btn-text');
        this.loadingSpinner = this.searchBtn.querySelector('.loading-spinner');
        
        if (!this.btnText || !this.loadingSpinner) {
            console.error('按钮内部元素不完整');
            throw new Error('按钮内部元素不完整');
        }
        this.modalImageFeatures = document.getElementById('modal-image-features');
        this.closeBtn = document.querySelector('.close-btn');
        this.processingSteps = document.getElementById('processing-steps');
    }

    initializeDimensionMappings() {
        return {
            head: {
                dimensions: ['眼睛形状', '嘴型', '表情', '脸部动态', '情感强度'],
                title: '推荐头像'
            },
            body: {
                dimensions: ['手部姿势', '腿部姿势', '整体姿势', '姿势意义', '情感偏向'],
                title: '推荐身体姿势'
            }
        };
    }

    bindEvents() {
        // 搜索按钮点击事件
        this.searchBtn.addEventListener('click', () => this.handleSearch());
        
        // 输入框回车事件
        this.requirementInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSearch();
            }
        });
        
        // 模态框关闭事件
        this.closeBtn.addEventListener('click', () => this.closeModal());
        this.imageModal.addEventListener('click', (e) => {
            if (e.target === this.imageModal) {
                this.closeModal();
            }
        });
        
        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    clearResults() {
        // 清空所有分析结果和搜索结果
        this.headAnalysisSection.style.display = 'none';
        this.headResultsSection.style.display = 'none';
        this.bodyAnalysisSection.style.display = 'none';
        this.bodyResultsSection.style.display = 'none';
        this.hideError();
    }

    async checkServerHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (!data.excel_loaded) {
                this.showError('警告：Excel数据未加载，请检查data/joy_head.xlsx文件是否存在');
            }
            
            console.log('服务器状态:', data);
        } catch (error) {
            console.error('服务器健康检查失败:', error);
            this.showError('无法连接到服务器，请确保后端服务正在运行');
        }
    }

    async handleSearch() {
        const requirement = this.requirementInput.value.trim();
        
        if (!requirement) {
            this.showError('请输入您的需求描述');
            return;
        }

        // 显示加载状态
        this.showLoading();
        this.setButtonLoading(true);

        // 启动SSE日志流
        const streamId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        this.startLogStream(streamId);

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    requirement: requirement,
                    stream_id: streamId
                })
            });

            const data = await response.json();

            if (data.success) {
                // 显示处理步骤
                if (data.processing_steps) {
                    this.updateProcessingSteps(data.processing_steps);
                }
                
                // 同时显示头像和身体姿势结果
                this.displayHeadResults(data.head_results, data.requirement);
                this.displayBodyResults(data.body_results, data.requirement);
                this.hideError();
            } else {
                this.showError(data.message || '搜索失败，请重试');
            }
        } catch (error) {
            console.error('搜索请求失败:', error);
            this.showError('网络请求失败，请检查网络连接或服务器状态');
        } finally {
            this.stopLogStream();
            this.hideLoading();
            this.setButtonLoading(false);
        }
    }

    displayHeadResults(results, requirement) {
        if (!results || results.length === 0) {
            console.log('未找到匹配的头像表情');
            return;
        }

        // 显示头像需求分析结果
        const firstResult = results[0];
        if (firstResult.requirement_features) {
            this.displayHeadAnalysis(firstResult.requirement_features);
        }

        // 清空之前的结果和图表实例
        this.clearChartsByType('head');
        this.headResultsGrid.innerHTML = '';

        // 显示匹配结果
        results.forEach((result, index) => {
            const resultItem = this.createResultItem(result, index + 1, 'head');
            this.headResultsGrid.appendChild(resultItem);
        });

        // 显示结果区域
        this.headResultsSection.style.display = 'block';
    }

    displayBodyResults(results, requirement) {
        if (!results || results.length === 0) {
            console.log('未找到匹配的身体姿势');
            return;
        }

        // 显示身体姿势需求分析结果
        const firstResult = results[0];
        if (firstResult.requirement_features) {
            this.displayBodyAnalysis(firstResult.requirement_features);
        }

        // 清空之前的结果和图表实例
        this.clearChartsByType('body');
        this.bodyResultsGrid.innerHTML = '';

        // 显示匹配结果
        results.forEach((result, index) => {
            const resultItem = this.createResultItem(result, index + 1, 'body');
            this.bodyResultsGrid.appendChild(resultItem);
        });

        // 显示结果区域
        this.bodyResultsSection.style.display = 'block';
        
        // 滚动到第一个结果区域
        this.headResultsSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }

    displayHeadAnalysis(features) {
        // 清空之前的分析结果
        this.headAnalysisGrid.innerHTML = '';
        
        // 获取头像维度
        const mapping = this.dimensionMappings['head'];
        
        // 动态创建分析结果项
        mapping.dimensions.forEach(dimension => {
            const analysisItem = document.createElement('div');
            analysisItem.className = 'analysis-item';
            analysisItem.innerHTML = `
                <span class="label">${dimension}：</span>
                <span class="value">${features[dimension] || '未识别'}</span>
            `;
            this.headAnalysisGrid.appendChild(analysisItem);
        });
        
        this.headAnalysisSection.style.display = 'block';
    }

    displayBodyAnalysis(features) {
        // 清空之前的分析结果
        this.bodyAnalysisGrid.innerHTML = '';
        
        // 获取身体姿势维度
        const mapping = this.dimensionMappings['body'];
        
        // 动态创建分析结果项
        mapping.dimensions.forEach(dimension => {
            const analysisItem = document.createElement('div');
            analysisItem.className = 'analysis-item';
            analysisItem.innerHTML = `
                <span class="label">${dimension}：</span>
                <span class="value">${features[dimension] || '未识别'}</span>
            `;
            this.bodyAnalysisGrid.appendChild(analysisItem);
        });
        
        this.bodyAnalysisSection.style.display = 'block';
    }

    createResultItem(result, rank, resultType = null) {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        // 创建评分颜色
        const scoreColor = this.getScoreColor(result.score);
        
        // 使用结果类型和rank生成唯一ID，避免头像和身体姿势ID冲突
        const type = resultType || result.type || 'unknown';
        const chartId = `radar-chart-${type}-${rank}`;
        
        item.innerHTML = `
            <img src="${result.image_url}" alt="${result.image_name}" class="result-image" 
                 onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTUwIiBoZWlnaHQ9IjE1MCIgdmlld0JveD0iMCAwIDE1MCAxNTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxNTAiIGhlaWdodD0iMTUwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik03NSA0MEMzNS44MTc2IDQwIDQwIDM1LjgxNzYgNDAgNzVTMzUuODE3NiAxMTAgNzUgMTEwUzExMCAxMDUuMTgyIDExMCA3NVM5NC4xODI0IDQwIDc1IDQwWiIgZmlsbD0iI0Q5REREQyIvPgo8L3N2Zz4K'">
            <div class="result-info">
                <h4>第${rank}名 - ${result.image_name}</h4>
                <div class="score-badge" style="background: ${scoreColor}">
                    综合匹配度: ${result.score}%
                </div>
                <div class="radar-container">
                    <canvas id="${chartId}" class="radar-chart"></canvas>
                </div>
                <div class="dimension-scores">
                    ${this.createDimensionScoresHTML(result.dimension_scores, type)}
                </div>
            </div>
        `;

        // 创建雷达图
        setTimeout(() => {
            this.createRadarChart(chartId, result.dimension_scores, type);
        }, 100);

        // 添加点击事件显示详细信息
        item.addEventListener('click', () => {
            this.showImageModal(result, rank);
        });

        return item;
    }

    createDimensionScoresHTML(dimensionScores, resultType) {
        const mapping = this.dimensionMappings[resultType || 'head'];
        return mapping.dimensions.map(dimension => `
            <div class="score-item">
                <span class="score-label">${dimension}：</span>
                <span class="score-value">${dimensionScores[dimension] || 0}%</span>
            </div>
        `).join('');
    }

    clearChartsByType(type) {
        // 清理指定类型的所有图表实例
        const keysToDelete = [];
        for (const [chartId, chart] of this.chartInstances) {
            if (chartId.includes(`radar-chart-${type}-`)) {
                try {
                    chart.destroy();
                    keysToDelete.push(chartId);
                } catch (error) {
                    console.warn('销毁图表时出错:', chartId, error);
                }
            }
        }
        
        // 从管理器中移除已销毁的图表
        keysToDelete.forEach(key => this.chartInstances.delete(key));
        
        console.log(`已清理 ${type} 类型的 ${keysToDelete.length} 个图表实例`);
    }

    createRadarChart(chartId, dimensionScores, resultType) {
        try {
            console.log('创建雷达图:', { chartId, dimensionScores, resultType });
            
            const canvas = document.getElementById(chartId);
            if (!canvas) {
                console.error('找不到canvas元素:', chartId);
                return;
            }

            // 检查Chart.js是否已加载
            if (typeof Chart === 'undefined') {
                console.error('Chart.js未加载');
                return;
            }

            const ctx = canvas.getContext('2d');
            const mapping = this.dimensionMappings[resultType || 'head'];
            
            if (!mapping) {
                console.error('未找到维度映射:', resultType);
                return;
            }

            const labels = mapping.dimensions;
            const data = labels.map(label => dimensionScores[label] || 0);

            console.log('雷达图数据:', { labels, data });

            // 销毁已存在的图表实例
            if (this.chartInstances.has(chartId)) {
                this.chartInstances.get(chartId).destroy();
                this.chartInstances.delete(chartId);
            }
            
            // 也检查Chart.js的全局注册表
            const existingChart = Chart.getChart(canvas);
            if (existingChart) {
                existingChart.destroy();
            }

            const chart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '匹配度',
                        data: data,
                        backgroundColor: 'rgba(102, 126, 234, 0.2)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                stepSize: 20,
                                font: {
                                    size: 10
                                }
                            },
                            pointLabels: {
                                font: {
                                    size: 11
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            },
                            angleLines: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        }
                    }
                }
            });

            // 将图表实例添加到管理器中
            this.chartInstances.set(chartId, chart);
            
            console.log('雷达图创建成功:', chartId);
            return chart;
        } catch (error) {
            console.error('创建雷达图时出错:', error);
        }
    }

    getScoreColor(score) {
        if (score >= 80) return 'linear-gradient(135deg, #48bb78 0%, #38a169 100%)';
        if (score >= 60) return 'linear-gradient(135deg, #ed8936 0%, #dd6b20 100%)';
        return 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    }

    showImageModal(result, rank) {
        this.modalImage.src = result.image_url;
        this.modalTitle.textContent = `第${rank}名 - ${result.image_name}`;
        this.modalScore.textContent = `${result.score}%`;
        this.modalScore.style.color = this.getScoreTextColor(result.score);

        // 显示需求特征
        this.modalRequirementFeatures.innerHTML = this.createFeaturesList(result.requirement_features);
        
        // 显示图片特征
        this.modalImageFeatures.innerHTML = this.createFeaturesList(result.features);

        this.imageModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    createFeaturesList(features) {
        return Object.entries(features).map(([key, value]) => `
            <div class="feature">
                <span class="feature-label">${key}：</span>
                ${value || '未识别'}
            </div>
        `).join('');
    }

    getScoreTextColor(score) {
        if (score >= 80) return '#48bb78';
        if (score >= 60) return '#ed8936';
        return '#667eea';
    }

    closeModal() {
        this.imageModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    showLoading() {
        this.hideError();
        this.loadingSection.style.display = 'block';
        // 重置处理步骤显示
        this.processingSteps.innerHTML = '<p>正在初始化...</p>';
        // 隐藏头像分析和结果区域
        this.headAnalysisSection.style.display = 'none';
        this.headResultsSection.style.display = 'none';
        // 隐藏身体姿势分析和结果区域
        this.bodyAnalysisSection.style.display = 'none';
        this.bodyResultsSection.style.display = 'none';
    }

    hideLoading() {
        this.loadingSection.style.display = 'none';
    }

    updateProcessingSteps(steps) {
        if (!steps || !Array.isArray(steps) || steps.length === 0) return;
        // 只展示最新一条
        const latest = steps[steps.length - 1];
        this.processingSteps.innerHTML = '';
        const stepElement = document.createElement('p');
        stepElement.textContent = latest;
        stepElement.style.margin = '5px 0';
        stepElement.style.opacity = '1';
        stepElement.style.fontWeight = 'bold';
        this.processingSteps.appendChild(stepElement);
    }

    // 启动SSE日志流
    startLogStream(streamId) {
        try {
            // 若已有连接，先关闭
            if (this.logEventSource) {
                this.logEventSource.close();
                this.logEventSource = null;
            }
            // 清空当前内容
            this.processingSteps.innerHTML = '';
            const es = new EventSource(`/api/logs/${encodeURIComponent(streamId)}`);
            this.logEventSource = es;
            es.onmessage = (e) => {
                const msg = e.data;
                if (!msg) return;
                if (msg === '__DONE__') {
                    this.stopLogStream();
                    return;
                }
                this.appendProcessingLog(msg);
            };
            es.onerror = (e) => {
                console.error('日志流错误:', e);
                // 连接失败时不立即关闭，允许自动重连
            };
        } catch (error) {
            console.error('启动日志流失败:', error);
        }
    }

    // 停止SSE日志流
    stopLogStream() {
        if (this.logEventSource) {
            try { this.logEventSource.close(); } catch (e) {}
            this.logEventSource = null;
        }
    }

    // 追加日志到处理步骤区域（改为仅显示最新一条）
    appendProcessingLog(message) {
        // 清空并只显示最新一条
        this.processingSteps.innerHTML = '';
        const stepElement = document.createElement('p');
        stepElement.textContent = message;
        stepElement.style.margin = '5px 0';
        stepElement.style.opacity = '1';
        stepElement.style.fontWeight = 'bold';
        this.processingSteps.appendChild(stepElement);
    }

    setButtonLoading(loading) {
        if (loading) {
            this.searchBtn.disabled = true;
            this.btnText.style.display = 'none';
            this.loadingSpinner.style.display = 'inline';
        } else {
            this.searchBtn.disabled = false;
            this.btnText.style.display = 'inline';
            this.loadingSpinner.style.display = 'none';
        }
    }

    showError(message) {
        this.errorText.textContent = message;
        this.errorSection.style.display = 'block';
        
        // 滚动到错误提示
        this.errorSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }

    hideError() {
        this.errorSection.style.display = 'none';
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    try {
        new ImageMatcherApp();
    } catch (error) {
        console.error('应用启动失败:', error);
        // 显示用户友好的错误信息
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #f56565; color: white; padding: 15px; border-radius: 8px; z-index: 9999;';
        errorDiv.textContent = '应用启动失败，请刷新页面重试';
        document.body.appendChild(errorDiv);
    }
});

// 添加一些实用的工具函数
window.ImageMatcherUtils = {
    // 复制文本到剪贴板
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('复制失败:', err);
            return false;
        }
    },

    // 下载图片
    downloadImage: (imageUrl, filename) => {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    // 格式化分数显示
    formatScore: (score) => {
        return Math.round(score * 10) / 10;
    }
};