# 启动脚本更新说明

## 更新概述

根据长期记忆系统的实现，对开发环境的启动脚本进行了以下更新：

## 新增组件

### 1. 后台任务处理器 (Background Tasks)
- **作用**: 独立处理摘要生成、记忆提取、实体分析等任务
- **启动方式**: 集成在 `dev.sh` 中自动启动
- **日志**: `logs/orchestrator/background_tasks.log`
- **PID**: `logs/pids/background_tasks.pid`

## 更新的文件

### 1. `scripts/dev.sh`
**变更**:
- 新增后台任务处理器启动逻辑
- 更新服务列表显示
- 调整启动顺序（Orchestrator → 后台任务）

**启动顺序**:
```bash
1. Gateway (9301)
2. Orchestrator (9302)
3. Skills API (9303)
4. RAG Pipeline (9305)
5. Web UI (9300)
6. Background Tasks (独立进程)
```

### 2. `scripts/stop.sh`
**无需变更**:
- 自动通过PID文件停止后台任务处理器

### 3. 新增文件

#### `start_background_tasks.py`
- 独立启动后台任务处理器
- 独立日志记录
- 错误处理和监控

#### `scripts/BACKGROUND_TASKS.md`
- 后台任务处理器详细说明
- 功能介绍
- 故障排除指南

#### `scripts/test_services.sh`
- 测试所有服务状态
- 检查HTTP服务和后台进程
- 验证长期记忆功能

## 服务清单

| 服务 | 端口 | 作用 | 状态 |
|------|------|------|------|
| Web UI | 9300 | 前端界面 | ✅ |
| Gateway | 9301 | API网关 + Token监控 | ✅ |
| Orchestrator | 9302 | 对话编排 | ✅ |
| Skills API | 9303 | 技能注册 | ✅ |
| RAG Pipeline | 9305 | 知识库检索 | ✅ |
| Background Tasks | - | 长期记忆系统 | ✅ **新增** |

## 使用方法

### 启动所有服务
```bash
./scripts/dev.sh
```

### 停止所有服务
```bash
./scripts/stop.sh
```

### 测试服务状态
```bash
./scripts/test_services.sh
```

### 查看日志
```bash
# 后台任务处理器日志
tail -f logs/orchestrator/background_tasks.log

# 所有服务日志
tail -f logs/*/*.log
```

## 长期记忆系统

后台任务处理器负责以下功能：

1. **摘要生成**
   - 自动分析对话内容
   - 生成会话摘要
   - 触发条件: 4000 tokens

2. **记忆提取**
   - 提取实体信息
   - 构建用户画像
   - 支持长期记忆

3. **任务队列**
   - `queue:summary_tasks`: 摘要任务
   - `queue:memory_tasks`: 记忆任务

## 故障排除

### 1. 后台任务处理器未启动
```bash
# 检查PID文件
cat logs/pids/background_tasks.pid

# 检查进程
ps -p $(cat logs/pids/background_tasks.pid)

# 查看日志
tail -f logs/orchestrator/background_tasks.log
```

### 2. Redis连接问题
```bash
# 测试连接
redis-cli -h 192.168.1.248 -p 6379 ping
```

### 3. 长期记忆功能异常
```bash
# 运行测试
python test_memory_final.py
```

## 性能监控

### 查看队列状态
```bash
redis-cli -h 192.168.1.248 -p 6379
> LLEN queue:summary_tasks
> LLEN queue:memory_tasks
```

### 监控任务处理
```bash
# 查看后台任务日志
tail -f logs/orchestrator/background_tasks.log | grep -E "Processing|Error"
```

## 升级说明

### v2.0 新增特性
- ✅ 独立的后台任务处理器
- ✅ 改进的长期记忆系统
- ✅ Token监控功能
- ✅ 自动化服务管理

### 兼容性
- ✅ 向后兼容 v1.x
- ✅ 现有数据保持不变
- ✅ API接口无变化

## 联系信息

如有问题，请查看：
- `scripts/BACKGROUND_TASKS.md` - 后台任务详细说明
- `scripts/test_services.sh` - 服务状态测试
- 日志文件 - 故障排除参考