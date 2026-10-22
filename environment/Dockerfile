FROM python:3.12.7-slim-bookworm@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 解题与参考解的身份由 task.toml 的 [agent] user = "runner" 指定。
# 容器默认用户保持 root：Harbor 的保活进程随默认用户运行，评分前清理 runner
# 进程时不能把它一起结束。
RUN useradd --create-home --uid 1000 runner

# 容器里跑交互式解题工具时要现装 nodejs，默认 Debian 源在本机很慢（实测 25 分钟），
# 这里只把源换成国内镜像：写配置文件，构建阶段不联网。
COPY mirror/debian.sources /etc/apt/sources.list.d/debian.sources

WORKDIR /app
COPY app/ /app/
RUN chown -R runner:runner /app
