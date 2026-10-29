FROM python:3.13.18-slim-trixie

# Utilisateur sans privilèges ; les volumes de données et du jeton lui appartiennent.
RUN useradd --uid 1000 --create-home console \
 && mkdir -p /data /run/console \
 && chown console:console /data /run/console

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py auth.py revocation.py ./
COPY static ./static

USER console
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
