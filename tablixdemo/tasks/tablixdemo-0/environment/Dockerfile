FROM python:3.11-slim
ENV PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
COPY repo /app/repo
# tablix/ dir contains __init__.py directly (package root = /opt/tablix/tablix)
COPY tablix /opt/tablix/tablix
# Remove any accidentally nested copy from the build context
RUN rm -rf /opt/tablix/tablix/tablix 2>/dev/null || true
ENV PYTHONPATH=/opt/tablix:/app/repo
WORKDIR /app/repo
# Agent container: no tests/expected, no oracle, no familiar library.
# Network: no-network (enforced by harness).
