from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

app = FastAPI(title="Zion Gateway V2 - SNG Protocol")

# --- O BANCO DE DADOS (Ledger + Registro Civil) ---
ledger = {
    "0xF497FFEB": 0.0000  # Carteira Oficial
}

# Novo dicionário para mapear nomes de usuário para as carteiras
aliases = {
    "@arquiteto": "0xF497FFEB"
}

# --- MODELOS DE DADOS ---
class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario: str      # Agora pode receber '0xABC...' ou '@Nome'
    quantidade: float

class MineRequest(BaseModel):
    wallet_hash: str
    recompensa: float

class AliasRequest(BaseModel):
    wallet_hash: str
    username: str

# --- ROTINA DO ARQUITETO ---
def genesis_yield():
    arquiteto = "0xF497FFEB"
    if arquiteto in ledger:
        ledger[arquiteto] += 1.0
        print(f"[ZION CORE] 1.0 SNG injetado. Saldo Arquiteto: {ledger[arquiteto]}")

scheduler = BackgroundScheduler()
scheduler.add_job(genesis_yield, 'interval', hours=1)
scheduler.start()

# --- ENDPOINTS ---
@app.get("/")
def status_rede():
    return {"status": "Zion API V2 Online", "modules": ["PoHW", "Banking", "Aliases"]}

@app.get("/saldo/{wallet_hash}")
def consultar_saldo(wallet_hash: str):
    if wallet_hash not in ledger:
        ledger[wallet_hash] = 0.0
    
    # Procura se esta carteira tem um @Username registrado
    user_alias = "Desconhecido"
    for nome, h in aliases.items():
        if h == wallet_hash:
            user_alias = nome
            break
            
    return {"wallet": wallet_hash, "saldo": ledger[wallet_hash], "alias": user_alias}

@app.post("/minerar")
def registar_mineracao(req: MineRequest):
    if req.recompensa <= 0: raise HTTPException(status_code=400, detail="Recompensa inválida.")
    if req.wallet_hash not in ledger: ledger[req.wallet_hash] = 0.0
        
    ledger[req.wallet_hash] += req.recompensa
    return {"status": "Bloco Validado", "novo_saldo": ledger[req.wallet_hash]}

@app.post("/registrar_alias")
def registrar_alias(req: AliasRequest):
    username = req.username.strip().lower()
    
    # Garante que começa com @
    if not username.startswith("@"):
        username = "@" + username
        
    # Verifica se o nome já está em uso por OUTRA pessoa
    if username in aliases and aliases[username] != req.wallet_hash:
        raise HTTPException(status_code=400, detail="Este Nome de Operador já pertence a outra pessoa.")
        
    # Registra ou atualiza
    aliases[username] = req.wallet_hash
    if req.wallet_hash not in ledger:
        ledger[req.wallet_hash] = 0.0
        
    print(f"[REGISTRO] A carteira {req.wallet_hash} agora é conhecida como {username}")
    return {"status": "Identidade Vinculada", "alias": username, "wallet": req.wallet_hash}

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    if req.quantidade <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
    if req.remetente_hash not in ledger or ledger[req.remetente_hash] < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    destinatario_hash = req.destinatario
    
    # Se o remetente digitou um @Nome, o servidor converte para Hash
    if req.destinatario.startswith("@"):
        busca = req.destinatario.lower()
        if busca not in aliases:
            raise HTTPException(status_code=404, detail=f"O operador {req.destinatario} não existe.")
        destinatario_hash = aliases[busca]

    # Cria a carteira destino se for nova
    if destinatario_hash not in ledger:
        ledger[destinatario_hash] = 0.0
        
    # Executa a matemática do Ledger
    ledger[req.remetente_hash] -= req.quantidade
    ledger[destinatario_hash] += req.quantidade
    
    print(f"[TRANSFERÊNCIA] {req.quantidade} SNG de {req.remetente_hash} para {destinatario_hash}")
    return {"status": "Aprovado", "enviado": req.quantidade, "para": destinatario_hash}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
