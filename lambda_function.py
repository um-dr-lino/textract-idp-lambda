import boto3
import json
import os
import re
import base64
import urllib3
from typing import Dict, Any, Optional
import traceback

# Initialize clients
textract = boto3.client('textract', region_name='us-east-1')
http = urllib3.PoolManager()

# SOAP API Configuration
url = "https://isc.softexpert.com/apigateway/se/ws/wf_ws.php"
authorization = "eyJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MzkyOTk0NTAsImV4cCI6MTg5NzA2NTg1MCwiaWRsb2dpbiI6ImFsaW5vIn0.UY5DZHix28g_pr-V8A-rJYpOCU9MPta6Lc3uKkoGxqw"
entityID = "idpforms"
headers = {
    "Authorization": authorization,
    "SOAPAction": "urn:workflow#editEntityRecord",
    "Content-Type": "text/xml;charset=utf-8"
}

# Lambda Handler
def lambda_handler(event, context):
    try:
        print("[DEBUG] Lambda function started")
        print(f"[DEBUG] Event received: {json.dumps(event, indent=2)}")
        
        # Handle both direct invocation and API Gateway event structures
        if 'body' in event and isinstance(event['body'], str):
            # API Gateway format - body is a JSON string
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse body as JSON: {str(e)}")
                return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON in request body'})}
        else:
            # Direct invocation - event is the body itself
            body = event
        
        print(f"[DEBUG] Processed body: {json.dumps(body, indent=2)}")
        
        # Extract parameters
        workflow = body.get('novo_workflow', '')
        docrg = body.get('docrg', '')
        doccnh = body.get('doccnh', '')
        docproof = body.get('docproof', '')
        
        print(f"[DEBUG] Workflow: {workflow}")
        print(f"[DEBUG] Document URLs - RG: {docrg}, CNH: {doccnh}, Proof: {docproof}")
        
        nome_rg = os.path.basename(docrg) if docrg else ''
        nome_cnh = os.path.basename(doccnh) if doccnh else ''
        nome_proof = os.path.basename(docproof) if docproof else ''
        
        base64_rg = get_base64_from_url(docrg)
        base64_cnh = get_base64_from_url(doccnh)
        base64_proof = get_base64_from_url(docproof)
            
        print(f"[DEBUG] Verificando base64 CNH: {base64_rg[:50]}...")
        print(f"[DEBUG] Document names - RG: {nome_rg}, CNH: {nome_cnh}, Proof: {nome_proof}")
        
        # Process documents and extract information
        extracted_info = process_documents(docrg, doccnh, docproof)
        
        rg_number = extracted_info.get('rg_number', '')
        street_name = extracted_info.get('street_name', '')
        zip_code = extracted_info.get('zip_code', '')
        state = extracted_info.get('state')
        neighborhood = extracted_info.get('neighborhood')
        
        # Criar o payload XML garantindo UTF-8
        payload = f"""<?xml version="1.0" encoding="utf-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:workflow">
        <soapenv:Header/>
        <soapenv:Body>
            <urn:editEntityRecord>
                <urn:WorkflowID>{workflow}</urn:WorkflowID>
                <urn:EntityID>{entityID}</urn:EntityID>
                <urn:EntityAttributeList>
                    <urn:EntityAttribute>
                    <urn:EntityAttributeID>texto4</urn:EntityAttributeID>
                    <urn:EntityAttributeValue>{rg_number}</urn:EntityAttributeValue>
                    </urn:EntityAttribute>
                    <urn:EntityAttribute>
                    <urn:EntityAttributeID>texto6</urn:EntityAttributeID>
                    <urn:EntityAttributeValue>{street_name}</urn:EntityAttributeValue>
                    </urn:EntityAttribute>
                    <urn:EntityAttribute>
                    <urn:EntityAttributeID>texto10</urn:EntityAttributeID>
                    <urn:EntityAttributeValue>{zip_code}</urn:EntityAttributeValue>
                    </urn:EntityAttribute>
                    <urn:EntityAttribute>
                    <urn:EntityAttributeID>texto7</urn:EntityAttributeID>
                    <urn:EntityAttributeValue>{state}</urn:EntityAttributeValue>
                    </urn:EntityAttribute>
                    <urn:EntityAttribute>
                    <urn:EntityAttributeID>texto8</urn:EntityAttributeID>
                    <urn:EntityAttributeValue>{neighborhood}</urn:EntityAttributeValue>
                    </urn:EntityAttribute>
                </urn:EntityAttributeList>
                <urn:EntityAttributeFileList>
                    <urn:EntityAttributeFile>
                    <urn:EntityAttributeID>arquivo1</urn:EntityAttributeID>
                    <urn:FileName>{nome_rg}</urn:FileName>
                    <urn:FileContent>{base64_rg}</urn:FileContent>
                    </urn:EntityAttributeFile>
                    <urn:EntityAttributeFile>
                    <urn:EntityAttributeID>arquivo2</urn:EntityAttributeID>
                    <urn:FileName>{nome_cnh}</urn:FileName>
                    <urn:FileContent>{base64_cnh}</urn:FileContent>
                    </urn:EntityAttributeFile>
                    <urn:EntityAttributeFile>
                    <urn:EntityAttributeID>arquivo3</urn:EntityAttributeID>
                    <urn:FileName>{nome_proof}</urn:FileName>
                    <urn:FileContent>{base64_proof}</urn:FileContent>
                    </urn:EntityAttributeFile>
                </urn:EntityAttributeFileList>
            </urn:editEntityRecord>
        </soapenv:Body>
        </soapenv:Envelope>"""

        # Fazer a requisição usando urllib3
        req = http.request('POST', url, headers=headers, body=payload.encode('utf-8'))

        print(f"[DEBUG] SOAP API response status: {req.status}")
        print(f"[DEBUG] SOAP API response data: {req.data.decode('utf-8')}")
        
        print(f"[DEBUG] Extracted information: {json.dumps(extracted_info, indent=2)}")
        
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'extracted_info': extracted_info,
                'workflow': workflow,
                'document_names': {
                    'rg': nome_rg,
                    'cnh': nome_cnh,
                    'proof': nome_proof
                }
            })
        }
        
        print(f"[DEBUG] Returning result: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }

# Function to convert file from URL to Base64
def get_base64_from_url(url: str) -> Optional[str]:
    try:
        print(f"[DEBUG] Fetching content from URL: {url}")
        response = http.request('GET', url)
        print(f"[DEBUG] URL response status: {response.status}")
        
        if response.status == 200:
            encoded = base64.b64encode(response.data).decode('utf-8')
            print(f"[DEBUG] Successfully encoded content from URL (first 50 chars): {encoded[:50]}...")
            return encoded
        else:
            print(f"[ERROR] Failed to fetch URL. Status: {response.status}")
            return None
    except Exception as e:
        print(f"[ERROR] Exception in get_base64_from_url: {str(e)}")
        return None

# Function to extract text from document using AWS Textract
def get_full_text(document_bytes: bytes) -> str:
    try:
        print(f"[DEBUG] Sending document to Textract (size: {len(document_bytes)} bytes)")
        response = textract.detect_document_text(Document={'Bytes': document_bytes})
        
        text_blocks = [item.get('Text', '') for item in response.get('Blocks', []) if item.get('BlockType') == 'LINE']
        full_text = " ".join(text_blocks)
        
        print(f"[DEBUG] Extracted text (first 100 chars): {full_text[:100]}...")
        return full_text
    except Exception as e:
        print(f"[ERROR] Textract error: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return ""

# Pattern extraction functions
def extract_rg(text: str) -> Optional[str]:
    match = re.search(r'\b\d{1}\.\d{3}\.\d{3}\b', text)  # Padrão tradicional de RG
    if not match:
        match = re.search(r'\b\d{3}\.\d{3}\.\d{3}-\d{1}\b', text)  
    
    result = match.group(0) if match else None
    print(f"[DEBUG] RG extraction result: {result}")
    return result


def extract_cpf(text: str) -> Optional[str]:
    match = re.search(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', text)
    result = match.group(0) if match else None
    print(f"[DEBUG] CPF extraction result: {result}")
    return result

def extract_zip_code(text: str) -> Optional[str]:
    matches = re.findall(r'\b\d{5}[-.]?\d{3}\b', text)  
    result = matches[1] if len(matches) > 1 else matches[0] if matches else None
    print(f"[DEBUG] ZIP code extraction result: {result}")
    return result

def extract_street_name(text: str) -> Optional[str]:
    matches = re.findall(r'\b(?:Rua|R\.|Avenida|Travessa|Estrada|Alameda|Rodovia)\s+([A-Za-zÀ-ÿ\s]+)', text, re.IGNORECASE)
    result = matches[1] if len(matches) > 1 else matches[0] if matches else None
    print(f"[DEBUG] Street name extraction result: {result}")
    return result

def extract_neighborhood(text: str) -> Optional[str]:
    match = re.search(r'\b(Bairro|Setor|Vila|Jardim|Parque|Residencial|Loteamento)\s+[A-Za-zÀ-ÿ\s]+', text, re.IGNORECASE)
    result = match.group(0) if match else None
    print(f"[DEBUG] Neighborhood extraction result: {result}")
    return result

def extract_state(text: str) -> Optional[str]:
    estados = [
        "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Distrito Federal",
        "Espírito Santo", "Goiás", "Maranhão", "Mato Grosso", "Mato Grosso do Sul",
        "Minas Gerais", "Pará", "Paraíba", "Paraná", "Pernambuco", "Piauí",
        "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia",
        "Roraima", "Santa Catarina", "São Paulo", "Sergipe", "Tocantins"
    ]
    siglas = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
              "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR",
              "SC", "SP", "SE", "TO"]

    regex_pattern = r'\b(' + '|'.join(estados + siglas) + r')\b'

    match = re.search(regex_pattern, text, re.IGNORECASE)
    result = match.group(0) if match else None
    print(f"[DEBUG] State extraction result: {result}")
    return result


# Main document processing function
def process_documents(docrg: str, doccnh: str, docproof: str) -> Dict[str, str]:
    extracted_info = {}
    
    # Process RG document
    if docrg:
        try:
            print(f"[DEBUG] Processing RG document: {docrg}")
            response = http.request('GET', docrg)
            
            if response.status == 200:
                print(f"[DEBUG] Successfully downloaded RG document ({len(response.data)} bytes)")
                full_text = get_full_text(response.data)
                extracted_info['rg_number'] = extract_rg(full_text) or ''
            else:
                print(f"[ERROR] Failed to download RG document. Status: {response.status}")
        except Exception as e:
            print(f"[ERROR] Exception processing RG document: {str(e)}")
    # Process CNH document
    if doccnh:
        try:
            print(f"[DEBUG] Processing CNH document: {doccnh}")
            response = http.request('GET', doccnh)
            
            if response.status == 200:
                print(f"[DEBUG] Successfully downloaded CNH document ({len(response.data)} bytes)")
                full_text = get_full_text(response.data)
                extracted_info['cpf_number'] = extract_cpf(full_text) or ''
            else:
                print(f"[ERROR] Failed to download CNH document. Status: {response.status}")
        except Exception as e:
            print(f"[ERROR] Exception processing CNH document: {str(e)}")
    
    # Process address proof document
    if docproof:
        try:
            print(f"[DEBUG] Processing proof document: {docproof}")
            response = http.request('GET', docproof)
            
            if response.status == 200:
                print(f"[DEBUG] Successfully downloaded proof document ({len(response.data)} bytes)")
                full_text = get_full_text(response.data)
                extracted_info['street_name'] = extract_street_name(full_text) or ''
                extracted_info['zip_code'] = extract_zip_code(full_text) or ''
                extracted_info['neighborhood'] = extract_neighborhood(full_text) or ''
                extracted_info['state'] = extract_state(full_text) or ''
            else:
                print(f"[ERROR] Failed to download proof document. Status: {response.status}")
        except Exception as e:
            print(f"[ERROR] Exception processing proof document: {str(e)}")
   
    return extracted_info

