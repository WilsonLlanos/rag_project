FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tudo (incluindo o app_principal.py e a pasta pages/)
COPY . .

EXPOSE 8501

# O Docker vai rodar a tela principal. O Streamlit acha as outras sozinho!
CMD ["streamlit", "run", "app_principal.py", "--server.port=8501", "--server.address=0.0.0.0"]