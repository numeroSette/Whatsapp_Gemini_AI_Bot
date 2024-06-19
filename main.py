import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import google.generativeai as genai

# Configurações iniciais
wa_token = os.environ.get("WA_TOKEN")
genai.configure(api_key=os.environ.get("GEN_API"))
phone_id = os.environ.get("PHONE_ID")

# Dataset de vendas
def criar_dataset():
    data_inicial = datetime(2024, 6, 1)
    dias = [data_inicial + timedelta(days=i) for i in range(30)]
    produtos = ['Smartphone X1', 'Notebook Pro', 'Geladeira Plus', 'TV 50\' UHD']
    categorias = ['Eletrônicos', 'Eletrônicos', 'Eletrodomésticos', 'Eletrônicos']
    precos = [1200, 2300, 1500, 2200]
    regioes = ['Norte', 'Sul', 'Centro-Oeste', 'Sudeste']

    dados = []
    for dia in dias:
        for produto, categoria, preco, regiao in zip(produtos, categorias, precos, regioes):
            quantidade = np.random.randint(5, 21)  # quantidade vendida entre 5 e 20
            receita = quantidade * preco
            dados.append([dia.strftime('%Y-%m-%d'), produto, categoria, quantidade, preco, receita, regiao])

    colunas = ['Data da Venda', 'Produto', 'Categoria', 'Quantidade Vendida', 'Preço Unitário', 'Receita Total', 'Região de Venda']
    return pd.DataFrame(dados, columns=colunas)

df_vendas = criar_dataset()

app = Flask(__name__)

# Funções auxiliares
def send_message(answer, sender):
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {wa_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "messaging_product": "whatsapp",
        "to": sender,
        "type": "text",
        "text": {"body": answer}
    }
    response = requests.post(url, headers=headers, json=data)
    return response

@app.route("/query_vendas", methods=["POST"])
def query_vendas():
    content = request.json
    produto = content.get('produto')
    data = content.get('data')
    if produto:
        resultado = df_vendas[df_vendas['Produto'] == produto]
    elif data:
        resultado = df_vendas[df_vendas['Data da Venda'] == data]
    else:
        resultado = "Por favor, especifique um produto ou uma data para consultar."
    return jsonify({"resultado": resultado.to_dict(orient='records')})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    sender = "+" + data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    message = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    send_message(f"Recebi sua mensagem sobre: {message}", sender)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=8000)
