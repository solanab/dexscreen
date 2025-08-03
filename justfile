# Dexscreener Python SDK 测试运行器
# 使用: just <命令>

# 默认命令 - 显示帮助
default:
    @just --list

# 运行单元测试
test-unit:
    @echo "=== 运行单元测试 ==="
    uv run pytest tests/unit -v

# 运行集成测试
test-integration:
    @echo "=== 运行集成测试 ==="
    @echo "注意: 需要网络连接和真实 API 访问"
    uv run pytest tests/integration -v

# 运行所有测试
test-all:
    @echo "=== 运行所有测试 ==="
    uv run pytest tests -v

# 运行测试并生成覆盖率报告
test-coverage:
    @echo "=== 运行测试并生成覆盖率报告 ==="
    uv run pytest tests/unit --cov=dexscreen --cov-report=html --cov-report=term
    @echo "覆盖率报告已生成到 htmlcov/index.html"

# 快速测试（只运行快速的单元测试）
test-quick:
    @echo "=== 运行快速测试 ==="
    uv run pytest tests/unit -v -m "not slow"

# 运行特定测试文件
test-file FILE:
    @echo "=== 运行测试文件: {{FILE}} ==="
    uv run pytest {{FILE}} -v

# 运行特定测试函数
test-func FUNC:
    @echo "=== 运行测试函数: {{FUNC}} ==="
    uv run pytest -k {{FUNC}} -v

# 运行 linter
lint:
    @echo "=== 运行代码检查 ==="
    uv run ruff check .
    uv run pyright dexscreen/ tests/ examples/
    uv run yamllint .

# 格式化代码
format:
    @echo "=== 格式化代码 ==="
    uv run ruff format .
    uv run ruff check --fix .

# 检查代码格式
format-check:
    @echo "=== 检查代码格式 ==="
    uv run ruff format --check .
    uv run ruff check .

# 检查 YAML 文件
yaml-lint:
    @echo "=== 检查 YAML 文件 ==="
    uv run yamllint .

# 修复 YAML 文件格式问题
yaml-fix:
    @echo "=== 修复 YAML 文件格式 ==="
    uv run yamlfix .

# 检查 Markdown 文件格式
md-check:
    @echo "=== 检查 Markdown 文件格式 ==="
    pnpm prettier --check '**/*.md'

# 格式化 Markdown 文件
md-format:
    @echo "=== 格式化 Markdown 文件 ==="
    pnpm prettier --write '**/*.md'



# 清理临时文件
clean:
    @echo "=== 清理临时文件 ==="
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -exec rm -rf {} +
    find . -type d -name ".pyright" -exec rm -rf {} +
    rm -rf htmlcov/
    rm -rf .coverage

# 安装开发依赖
install:
    @echo "=== 安装开发依赖 ==="
    uv sync --all-extras
    pnpm install

# 运行示例
example NAME="01_async_basic_apis":
    @echo "=== 运行示例: {{NAME}} ==="
    uv run python examples/{{NAME}}.py

# 完整的 CI 检查（格式化、lint、测试）
ci:
    @echo "=== 运行完整 CI 检查 ==="
    just format-check
    just lint
    just test-unit
    just test-coverage

# 快速提交（跳过 pre-commit）
commit MSG:
    @echo "=== 快速提交 ==="
    git add -A
    git commit --no-verify -m "{{MSG}}"

# 格式化后提交
commit-format MSG:
    @echo "=== 格式化并提交 ==="
    just format
    git add -A
    git commit --no-verify -m "{{MSG}}"

# 文档相关命令
docs-serve:
    @echo "=== 停止文档服务器 ==="
    -lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "文档服务器未运行"
    @echo "=== 启动文档服务器 (后台运行) ==="
    nohup uv run mkdocs serve > mkdocs.log 2>&1 &
    @echo "文档服务器已在后台启动，日志输出到 mkdocs.log"
    @echo "访问: http://localhost:8000"

# 停止文档服务器（杀死端口 8000）
docs-stop:
    @echo "=== 停止文档服务器 ==="
    -lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "文档服务器未运行"

docs-build:
    @echo "=== 构建文档 ==="
    uv run mkdocs build

docs-deploy:
    @echo "=== 部署文档到 GitHub Pages ==="
    uv run mkdocs gh-deploy

# 版本管理
version-show:
    @echo "当前版本: $(uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"

# 发布预发布版本 (alpha/beta/rc)
publish-pre VERSION:
    @echo "=== 发布预发布版本 {{VERSION}} ==="
    @if [[ ! "{{VERSION}}" =~ (a|b|rc)[0-9]+$ ]]; then \
        echo "错误: 版本号必须以 a1, b1, rc1 等格式结尾"; \
        exit 1; \
    fi
    @echo "更新版本号到 {{VERSION}}..."
    @sed -i.bak '/^version = /s/version = ".*"/version = "{{VERSION}}"/' pyproject.toml && rm pyproject.toml.bak
    just build
    @if [ -f .pypi ]; then \
        export $(cat .pypi) && uv publish; \
    else \
        echo "错误: 请先创建 .pypi 文件并设置 UV_PUBLISH_TOKEN"; \
        exit 1; \
    fi
    @echo "预发布版本 {{VERSION}} 已发布!"

# 发布正式版本
publish-release VERSION:
    @echo "=== 发布正式版本 {{VERSION}} ==="
    @if [[ "{{VERSION}}" =~ (a|b|rc|dev)[0-9]+$ ]]; then \
        echo "错误: 正式版本号不能包含 a/b/rc/dev 后缀"; \
        exit 1; \
    fi
    @echo "更新版本号到 {{VERSION}}..."
    @sed -i.bak '/^version = /s/version = ".*"/version = "{{VERSION}}"/' pyproject.toml && rm pyproject.toml.bak
    just build
    @if [ -f .pypi ]; then \
        export $(cat .pypi) && uv publish; \
    else \
        echo "错误: 请先创建 .pypi 文件并设置 UV_PUBLISH_TOKEN"; \
        exit 1; \
    fi
    @echo "正式版本 {{VERSION}} 已发布!"
    @echo "建议: 创建 git tag v{{VERSION}} 并推送"

# 构建包
build:
    @echo "=== 构建 Python 包 ==="
    uv build

# 发布到 PyPI (需要先设置 token)
publish:
    @echo "=== 发布到 PyPI ==="
    @if [ -f .pypi ]; then \
        export $(cat .pypi) && uv publish; \
    else \
        echo "错误: 请先创建 .pypi 文件并设置 UV_PUBLISH_TOKEN"; \
        exit 1; \
    fi

# 构建并发布
build-publish: build publish
    @echo "=== 构建并发布完成 ==="



# 别名 - 更短的命令
alias t := test-unit
alias ta := test-all
alias tc := test-coverage
alias l := lint
alias f := format
alias c := commit
alias cf := commit-format
alias d := docs-serve
alias ds := docs-stop
alias db := docs-build
alias dd := docs-deploy
alias yl := yaml-lint
alias yf := yaml-fix
alias mc := md-check
alias mf := md-format
alias i := install
alias v := version-show
alias b := build
alias p := publish
alias bp := build-publish
alias rel := publish-release
alias pre := publish-pre
