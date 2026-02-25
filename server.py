from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

app = FastAPI(title="Zion Gateway - SNG Protocol")

# --- O BANCO DE DADOS (O Ledger em Memória) ---
ledger = {
    "0xF497FFEB": 0.0000  # A sua carteira oficial de Arquiteto
}

# --- MODELOS DE DADOS ---
class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario_hash: str
    quantidade: float

class MineRequest(BaseModel):
    wallet_hash: str
    recompensa: float

# --- ROTINA DO ARQUITETO (O GENESIS YIELD) ---
def genesis_yield():
    """Gera 1 SNG por hora para o Criador da Rede"""
    arquiteto = "0xF497FFEB"
    if arquiteto in ledger:
        ledger[arquiteto] += 1.0
        print(f"[ZION CORE] 1.0 SNG injetado no Genesis Block. Saldo Arquiteto: {ledger[arquiteto]}")

scheduler = BackgroundScheduler()
scheduler.add_job(genesis_yield, 'interval', hours=1)
scheduler.start()

# --- ENDPOINTS (AS PORTAS DA API) ---

@app.get("/")
def status_rede():
    return {"status": "Zion API Online", "protocol": "PoHW"}

@app.get("/saldo/{wallet_hash}")
def consultar_saldo(wallet_hash: str):
    if wallet_hash not in ledger:
        ledger[wallet_hash] = 0.0
    return {"wallet": wallet_hash, "saldo": ledger[wallet_hash]}

# >>> NOVA PORTA DE ENTRADA: A MINERAÇÃO <<<
@app.post("/minerar")
def registar_mineracao(req: MineRequest):
    # Segurança básica
    if req.recompensa <= 0:
        raise HTTPException(status_code=400, detail="A recompensa deve ser maior que zero.")
        
    # Se a carteira não existir no servidor, cria-a agora
    if req.wallet_hash not in ledger:
        ledger[req.wallet_hash] = 0.0
        
    # Adiciona os SNGs minerados ao saldo!
    ledger[req.wallet_hash] += req.recompensa
    print(f"[POHW VALIDADO] {req.recompensa} SNG gerados para a carteira {req.wallet_hash}")
    
    return {
        "status": "Bloco Validado",
        "wallet": req.wallet_hash,
        "novo_saldo": ledger[req.wallet_hash]
    }

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    if req.remetente_hash not in ledger or ledger[req.remetente_hash] < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente ou carteira inexistente.")
    if req.quantidade <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
        
    if req.destinatario_hash not in ledger:
        ledger[req.destinatario_hash] = 0.0
        
    ledger[req.remetente_hash] -= req.quantidade
    ledger[req.destinatario_hash] += req.quantidade
    
    return {
        "status": "Transacao Aprovada",
        "remetente": ledger[req.remetente_hash],
        "destinatario": ledger[req.destinatario_hash]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
