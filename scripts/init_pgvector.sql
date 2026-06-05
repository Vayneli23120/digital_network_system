-- PostgreSQL pgvector 扩展初始化脚本
-- 在 PostgreSQL 数据库中执行此脚本以启用向量检索功能

-- 1. 创建 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 验证扩展已安装
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. 创建向量索引（可选，提高检索性能）
-- 在 ai_knowledge_documents 表创建后执行：
-- CREATE INDEX idx_ai_knowledge_embedding ON ai_knowledge_documents
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 说明：
-- - pgvector 支持向量存储和相似度检索
-- - ivfflat 索引适用于中等规模数据（< 100万向量）
-- - vector_cosine_ops 使用余弦相似度计算
-- - lists = 100 表示聚类中心数量，可根据数据规模调整

-- 如需重新创建扩展（谨慎操作）：
-- DROP EXTENSION IF EXISTS vector CASCADE;
-- CREATE EXTENSION vector;