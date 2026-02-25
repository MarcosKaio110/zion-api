from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn
import json
import os

app = FastAPI(title="Zion Gateway V2.1 - SNG Protocol")

# --- SISTEMA DE PERSISTÊNCIA (O DISCO RÍGIDO DA MATRIX) ---
DB_FILE = "zion_db.json"

def carregar_banco():
    """Carrega os dados do disco rígido. Se não existir, cria o Gênesis."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    # Estado inicial caso o ficheiro não exista
    return {
        "ledger": {"0xF497FFEB": 0.0},
        "aliases": {"@arquiteto": "0xF497FFEB"}
    }

def salvar_banco():
    """Guarda os dados no disco para sobreviverem ao reinício do servidor."""
    with open(DB_FILE, "w") as f:
        json.dump({"ledger": ledger, "aliases": aliases}, f, indent=4)

# Inicializa as variáveis puxando do disco
banco_dados = carregar_banco()
ledger = banco_dados["ledger"]
aliases = banco_dados["aliases"]

# --- MODELOS DE DADOS ---
class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario: str
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
    if arquiteto not in ledger:
        ledger[arquiteto] = 0.0
    ledger[arquiteto] += 1.0
    salvar_banco() # Salva a injeção
    print(f"[ZION CORE] 1.0 SNG injetado. Saldo Arquiteto: {ledger[arquiteto]}")

scheduler = BackgroundScheduler()
scheduler.add_job(genesis_yield, 'interval', hours=1)
scheduler.start()

# --- ENDPOINTS ---
@app.get("/")
def status_rede():
    return {"status": "Zion API V2.1 Online", "modules": ["PoHW", "Banking", "Persistence"]}

@app.get("/saldo/{wallet_hash}")
def consultar_saldo(wallet_hash: str):
    if wallet_hash not in ledger:
        ledger[wallet_hash] = 0.0
        salvar_banco()
    
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
    salvar_banco() # <-- SALVA NO DISCO
    
    print(f"[POHW VALIDADO] {req.recompensa} SNG para {req.wallet_hash}")
    return {"status": "Bloco Validado", "novo_saldo": ledger[req.wallet_hash]}

@app.post("/registrar_alias")
def registrar_alias(req: AliasRequest):
    username = req.username.strip().lower()
    if not username.startswith("@"): username = "@" + username
        
    if username in aliases and aliases[username] != req.wallet_hash:
        raise HTTPException(status_code=400, detail="Este Nome já pertence a outra pessoa.")
        
    aliases[username] = req.wallet_hash
    if req.wallet_hash not in ledger: ledger[req.wallet_hash] = 0.0
        
    salvar_banco() # <-- SALVA NO DISCO
    print(f"[REGISTRO] {req.wallet_hash} agora é {username}")
    return {"status": "Identidade Vinculada", "alias": username, "wallet": req.wallet_hash}

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    if req.quantidade <= 0:
        raise HTTPException(status_code=400, detail="Quantidade inválida.")
    if req.remetente_hash not in ledger or ledger[req.remetente_hash] < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    dest_hash = req.destinatario
    if req.destinatario.startswith("@"):
        busca = req.destinatario.lower()
        if busca not in aliases:
            raise HTTPException(status_code=404, detail="Operador não encontrado.")
        dest_hash = aliases[busca]

    if dest_hash not in ledger: ledger[dest_hash] = 0.0
        
    ledger[req.remetente_hash] -= req.quantidade
    ledger[dest_hash] += req.quantidade
    
    salvar_banco() # <-- SALVA NO DISCO
    print(f"[TRANSFERÊNCIA] {req.quantidade} SNG de {req.remetente_hash} para {dest_hash}")
    return {"status": "Aprovado", "enviado": req.quantidade, "para": dest_hash}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
