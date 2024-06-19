import google.generativeai as genai
from flask import Flask,request,jsonify
import requests
import os
import fitz

wa_token=os.environ.get("WA_TOKEN")

# Configuração do cliente da API Generativa
genai.configure(api_key=os.environ.get("GEN_API"))

phone_id=os.environ.get("PHONE_ID")
phone=os.environ.get("PHONE_NUMBER")
name="Sette" #The bot will consider this person as its owner or creator
bot_name="Luna" #This will be the name of your bot, eg: "Hello I am Astro Bot"

# Configuração do modelo de inteligência artificial
# Define qual versão do assistente digital é usada para responder às mensagens.
model_name="gemini-1.5-flash-latest"

# Inicialização do Flask (Web Application)
app=Flask(__name__)

# Configurações de geração de respostas do modelo:
generation_config = {
    "temperature": 1,  # Define a variabilidade nas respostas: um valor mais alto permite respostas mais diversificadas.
    "top_p": 0.95,  # Limita as respostas às palavras/tokens/partes do texto mais prováveis, garantindo que as respostas sejam relevantes e de alta qualidade.
    "top_k": 0,  # Não impõe um limite fixo no número de palavras/tokens/partes do texto consideradas, focando na qualidade das mais prováveis.
    "max_output_tokens": 8192,  # Estabelece um limite alto para o comprimento das respostas, permitindo explicações detalhadas se necessário.
}

# Configurações de segurança para manter o conteúdo gerado apropriado e seguro:
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},  # Previne respostas que possam ser interpretadas como assédio.
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},  # Bloqueia o uso de linguagem de ódio.
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},  # Impede conteúdo sexualmente explícito.
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},  # Evita conteúdo que possa ser considerado perigoso.
]

# Criando o modelo com as configurações definidas
model = genai.GenerativeModel(model_name=model_name,
                              generation_config=generation_config,
                              safety_settings=safety_settings)

# Configuração inicial de conversa do modelo
# Esta parte do código inicia uma nova conversa com o modelo de IA configurado. 
# `model.start_chat(history=[])`: Inicia uma conversa limpa sem qualquer histórico prévio.
# Isso é útil para garantir que a sessão do bot seja independente e não seja influenciada por interações anteriores.
convo = model.start_chat(history=[
])

# Envio de mensagem inicial de configuração para o modelo.
# A mensagem define a identidade e o contexto operacional do bot para que ele se "conscientize" de sua função.
# A mensagem orienta o modelo a não responder a este prompt inicial, pois serve apenas para estabelecer o contexto,
# e não para iniciar uma interação. Isso é útil para preparar o bot antes de começar a interagir com os usuários reais.
convo.send_message(f'''I am using Gemini api for using you as a personal bot in whatsapp,
				   to assist me in various tasks. 
				   So from now you are "{bot_name}" created by {name} ( Yeah it's me, my name is {name}). 
				   And don't give any response to this prompt. 
				   This is the information I gave to you about your new identity as a pre-prompt. 
				   This message always gets executed when i run this bot script. 
				   So reply to only the prompts after this. Remeber your new identity is {bot_name}.''')

def send(answer):
    """
    Envia uma mensagem de texto via WhatsApp usando a Graph API do Facebook.
    Args:
        answer (str): A mensagem de texto a ser enviada.
    Returns:
        response: Objeto Response da chamada da API.
    """
    url=f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers={
        'Authorization': f'Bearer {wa_token}',
        'Content-Type': 'application/json'
    }
    data={
        "messaging_product": "whatsapp",
        "to": f"{phone}",
        "type": "text",
        "text":{"body": f"{answer}"}
    }
    try:
        response=requests.post(url, headers=headers,json=data)
        response.raise_for_status()  # Lança um erro para respostas de falha
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem: {e}")
        return None
    return response

def remove(*file_paths):
    """
    Remove arquivos do sistema de arquivos se eles existirem.
    Args:
        *file_paths: Caminhos dos arquivos a serem removidos.
    """
    for file_path in file_paths:
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Erro ao remover o arquivo {file_path}: {e}")

@app.route("/",methods=["GET","POST"])
def index():
    """
    Rota raiz que simplesmente retorna 'Bot', pode ser usada para verificações básicas de saúde.
    """
    return "Bot"

@app.route("/webhook", methods=["GET"])
def webhook_validate():
    """
    Valida as solicitações de webhook do Facebook para garantir que o bot possa receber atualizações.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == "BOT":
        return challenge, 200
    else:
        return "Failed", 403

@app.route("/webhook", methods=["POST"])
def webhook_execute():
    try:
        data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
        if data["type"] == "text":
            prompt = data["text"]["body"]
            convo.send_message(prompt)
            send(convo.last.text)
        else:
            media_url_endpoint = f'https://graph.facebook.com/v18.0/{data[data["type"]]["id"]}/'
            headers = {'Authorization': f'Bearer {wa_token}'}
            media_response = requests.get(media_url_endpoint, headers=headers)
            media_url = media_response.json()["url"]
            media_download_response = requests.get(media_url, headers=headers)
            if data["type"] == "audio":
                filename = "/tmp/temp_audio.mp3"
            elif data["type"] == "image":
                filename = "/tmp/temp_image.jpg"
            elif data["type"] == "document":
                doc=fitz.open(stream=media_download_response.content,filetype="pdf")
                for _,page in enumerate(doc):
                    destination="/tmp/temp_image.jpg"
                    pix = page.get_pixmap()
                    pix.save(destination)
                    file = genai.upload_file(path=destination,display_name="tempfile")
                    response = model.generate_content(["What is this",file])
                    answer=response._result.candidates[0].content.parts[0].text
                    convo.send_message(f"Direct image input has limitations, so this message is created by an llm model based on the image prompt of user, reply to the user assuming you saw that image: {answer}")
                    send(convo.last.text)
                    remove(destination)
            else:send("This format is not Supported by the bot ☹")
            with open(filename, "wb") as temp_media:
                temp_media.write(media_download_response.content)
            file = genai.upload_file(path=filename,display_name="tempfile")
            response = model.generate_content(["What is this",file])
            answer=response._result.candidates[0].content.parts[0].text
            remove("/tmp/temp_image.jpg","/tmp/temp_audio.mp3")
            convo.send_message(f"Direct media input has limitations, so this is a voice/image message from user which is transcribed by an llm model, reply to the user assuming you heard/saw media file: {answer}")
            send(convo.last.text)
            files=genai.list_files()
            for file in files:
                file.delete()
    except :pass
    return jsonify({"status": "ok"}), 200
if __name__ == "__main__":
    app.run(debug=True, port=8000)