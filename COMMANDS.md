# rshAnyGen 常用命令

## Git Remote 配置

```
origin     -> https://gitee.com/o_0o_0/rshAnyGen.git     (主仓库)
github     -> https://github.com/ouyanggai/rshAnyGen.git  (GitHub 镜像)
upstream   -> https://github.com/open-webui/open-webui.git (Open WebUI 上游)
```

---

## 日常开发命令

### 提交代码
```bash
# 查看修改状态
git status

# 添加所有修改
git add .

# 提交
git commit -m "feat: 描述信息"

# 推送到 Gitee
git push origin master

# 推送到 GitHub
git push github master
```

### 同时推送到两个仓库
```bash
git push origin master && git push github master
```

---

## 从 Open WebUI 升级前端

### 方式一：合并上游更新
```bash
# 1. 拉取上游最新代码
git fetch upstream

# 2. 查看上游更新
git log HEAD..upstream/main --oneline

# 3. 合并上游更新
git merge upstream/main

# 4. 解决冲突（如果有）
# 手动编辑冲突文件后：
git add .

# 5. 完成合并提交
git commit -m "chore: merge upstream updates"

# 6. 推送更新
git push origin master && git push github master
```

### 方式二：变基合并（保持线性历史）
```bash
# 1. 拉取上游
git fetch upstream

# 2. 变基到上游最新版本
git rebase upstream/main

# 3. 解决冲突（如果有）
git add .
git rebase --continue

# 4. 强制推送（因为 rebase 改写了历史）
git push origin master --force-with-lease
git push github master --force-with-lease
```

---

## 仅更新 Web UI 子目录

如果只想更新 `apps/web-ui` 目录，可以使用子模块或 subtree：

```bash
# 使用 git subtree 拉取更新
git subtree pull --prefix=apps/web-ui \
  https://github.com/open-webui/open-webui.git main \
  --squash
```

---

## 查看远程仓库信息
```bash
# 查看所有 remote
git remote -v

# 查看上游分支
git branch -r

# 查看上游最新提交
git log upstream/main -5 --oneline
```

---

## 回滚操作

### 回滚最近一次提交
```bash
# 保留修改
git reset --soft HEAD~1

# 完全删除（慎用）
git reset --hard HEAD~1
```

### 回滚已推送的提交
```bash
# 创建回滚提交
git revert HEAD

# 强制推送（谨慎使用）
git push origin master --force-with-lease
```

---

## 分支管理

### 创建功能分支
```bash
git checkout -b feature/新功能名称
```

### 合并功能分支
```bash
git checkout master
git merge feature/新功能名称
git push origin master
```

---

## 清理命令

### 清理未跟踪文件
```bash
# 查看未跟踪文件
git clean -n

# 删除未跟踪文件
git clean -f

# 删除未跟踪文件和目录
git clean -fd
```

### 清理构建产物
```bash
# 清理 web-ui 构建产物
cd apps/web-ui
rm -rf .svelte-kit build node_modules
```

---

## 快捷别名（可选）

在 `~/.gitconfig` 中添加：

```ini
[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    unstage = reset HEAD --
    last = log -1 HEAD
    pu = !(git push origin master && git push github master)
    up = !git fetch upstream && git merge upstream/main
```

使用方式：
```bash
git pu    # 推送到所有仓库
git up    # 拉取上游更新
```

---

## 代理设置（如果需要）

### 临时使用代理
```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
```

### Git 配置代理
```bash
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

### 取消代理
```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 常见问题

### Q: 推送失败，提示 "Updates were rejected"
```bash
# 先拉取远程更新
git pull origin master --rebase

# 然后再推送
git push origin master
```

### Q: 合并冲突怎么办？
```bash
# 1. 查看冲突文件
git status

# 2. 手动编辑冲突文件，搜索 <<<<<<<

# 3. 标记为已解决
git add 冲突文件

# 4. 完成合并
git commit
```

### Q: 如何只保留 web-ui 的前端代码？
更新时会删除后端相关文件：
```bash
# 合并后清理
rm -rf apps/web-ui/backend
rm -f apps/web-ui/docker-compose*.yaml
rm -f apps/web-ui/run*.sh
```
