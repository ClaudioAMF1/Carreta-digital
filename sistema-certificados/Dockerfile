FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando de entrada
CMD ["python", "app.py"]