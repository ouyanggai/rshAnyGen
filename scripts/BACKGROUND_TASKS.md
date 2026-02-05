# 后台任务处理器说明

## 概述

后台任务处理器是rshAnyGen系统中负责**长期记忆系统**的核心组件，独立于Orchestrator API服务运行。

## 功能

### 1. 摘要生成
- 自动分析聊天会话
- 提取关键信息和主题
- 生成简洁的会话摘要
- 存储在Redis中供后续查询

### 2. 记忆提取
- 提取用户对话中的实体（人名、公司、项目等）
- 分析对话内容和上下文
- 构建用户画像和长期记忆
- 支持语义记忆检索

### 3. 用户画像
- 维护用户标签系统
- 跟踪用户偏好和行为
- 支持个性化对话体验

## 启动方式

### 开发环境
```bash
# 自动启动（通过 dev.sh）
./scripts/dev.sh

# 手动启动
source venv/bin/activate
python start_background_tasks.py
```

### 生产环境
```bash
# 使用systemd或docker启动
docker run -d --name background_tasks rshanygen python start_background_tasks.py
```

## 日志

- 日志文件：`logs/orchestrator/background_tasks.log`
- PID文件：`logs/pids/background_tasks.pid`
- 日志级别：INFO, ERROR, DEBUG

## 监控

### 查看日志
```bash
tail -f logs/orchestrator/background_tasks.log
```

### 检查进程
```bash
cat logs/pids/background_tasks.pid
ps -p $(cat logs/pids/background_tasks.pid)
```

## 停止

```bash
# 自动停止（通过 stop.sh）
./scripts/stop.sh

# 手动停止
kill $(cat logs/pids/background_tasks.pid)
```

## 依赖服务

- **Redis**: 存储队列和记忆数据
  - 摘要任务队列: `queue:summary_tasks`
  - 记忆任务队列: `queue:memory_tasks`
- **Milvus**: 语义记忆存储（可选）

## 故障排除

### 1. 队列任务未处理
检查Redis连接：
```bash
redis-cli -h 192.168.1.248 -p 6379
> LLEN queue:summary_tasks
> LLEN queue:memory_tasks
```

### 2. 日志无输出
检查文件权限和日志配置

### 3. 内存占用过高
检查Redis中的数据量，必要时清理过期数据

## 性能优化

- 摘要生成：每4000 tokens触发
- 记忆提取：每次对话后触发
- 并发处理：支持多个任务并行执行
- 任务队列：避免阻塞主服务

## 升级说明

v2.0新增功能：
- 独立进程启动
- 改进的错误处理
- 更详细的日志记录
- 支持任务重试机制