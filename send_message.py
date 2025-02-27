import urllib3
import json

def get_auth_token():
    url = "https://api.messaging.digitalcontact.cloud/auth/login"
    payload = json.dumps({
        "login": "sandbox.code7",
        "password": "YfAd95h4?Ek9"
    }).encode("utf-8")  # Converte para bytes

    headers = {
        "Content-Type": "application/json"
    }

    http = urllib3.PoolManager()
    try:
        response = http.request("POST", url, body=payload, headers=headers)
        
        if response.status == 200:
            token_data = json.loads(response.data.decode("utf-8"))
            return token_data.get("token")
        else:
            print(f"Erro {response.status}: {response.data.decode('utf-8')}")
            return None
    except urllib3.exceptions.HTTPError as e:
        print(f"Erro ao obter token: {e}")
        return None
    
def lambda_handler(event, context): 
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    body = event.get('body', '')
    body = body.encode('utf-8').decode('utf-8')  # Garante que seja UTF-8
    body = json.loads(body)
    fullname = body.get('nome', '')
    phone = body.get('telefone','')
    # Obtém o token de autenticação
    token = get_auth_token()
    
    if not token:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": "Falha ao obter o token de autenticação"})
        }
    url = "https://apiwhatsapp.messaging.digitalcontact.cloud/v1/message/send"
    # Payload da mensagem
    payload = json.dumps([{       
        "numberchip": "551135128704",
        "telephone": phone,
        "template": "67b85412e86c5b381ff33868",
        "field01": fullname
    }]).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-access-token": token
    }
    http = urllib3.PoolManager()
       
    try:
        response = http.request("POST", url, body=payload, headers=headers)
        if response.status == 200:
            resposta_json = json.loads(response.data.decode("utf-8"))
            return {
                'statusCode': 200,
                'body': json.dumps(resposta_json, ensure_ascii=False)
            }
        else:
            print(f"Erro {response.status}: {response.data.decode('utf-8')}")
            return {
                'statusCode': response.status,
                'body': response.data.decode("utf-8")
            }
    except urllib3.exceptions.HTTPError as e:
        print(f"Erro ao enviar mensagem: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }