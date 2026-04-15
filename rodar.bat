@echo off
:: Painel COATE — inicializador Windows
:: Execute este arquivo na pasta raiz do painel_coate

echo Iniciando Painel COATE...]

pip install -r requirements.txt
pip install python-dotenv
pip install certifi
pip install -U openai
pip install --upgrade openai

streamlit run app.py --server.port 8501
pause
