from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

app = FastAPI(title="Zion Gateway - SNG Protocol")

# --- O BANCO DE DADOS (O Ledger em Memória) ---
# Num ambiente de produção, isto será substituído por um banco PostgreSQL.
ledger = {
    "0xF497FFEB": 0.0000  # A sua carteira oficial de Arquiteto
}

# --- MODELOS DE DADOS ---
class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario_hash: str
    quantidade: float

# --- ROTINA DO ARQUITETO (O GENESIS YIELD) ---
def genesis_yield():
    """Gera 1 SNG por hora para o Criador da Rede"""
    arquiteto = "0xF497FFEB"
    if arquiteto in ledger:
        ledger[arquiteto] += 1.0
        print(f"[ZION CORE] 1.0 SNG injetado no Genesis Block. Saldo Arquiteto: {ledger[arquiteto]}")

# Inicia o relógio do servidor (O Coração da Matrix)
scheduler = BackgroundScheduler()
scheduler.add_job(genesis_yield, 'interval', hours=1) # Configurador para 1 HORA
scheduler.start()

# --- ENDPOINTS (AS PORTAS DA API) ---

@app.get("/")
def status_rede():
    return {"status": "Zion API Online", "protocol": "PoHW"}

@app.get("/saldo/{wallet_hash}")
def consultar_saldo(wallet_hash: str):
    if wallet_hash not in ledger:
        ledger[wallet_hash] = 0.0 # Regista novas carteiras automaticamente
    return {"wallet": wallet_hash, "saldo": ledger[wallet_hash]}

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    # Regras de Negócio e Segurança (Ledger)
    if req.remetente_hash not in ledger or ledger[req.remetente_hash] < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente ou carteira inexistente.")
    if req.quantidade <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
        
    # Executa a Transferência
    if req.destinatario_hash not in ledger:
        ledger[req.destinatario_hash] = 0.0
        
    ledger[req.remetente_hash] -= req.quantidade
    ledger[req.destinatario_hash] += req.quantidade
    
    print(f"[TX APROVADA] {req.quantidade} SNG movidos de {req.remetente_hash} para {req.destinatario_hash}")
    
    return {
        "status": "Transacao Aprovada",
        "remetente": ledger[req.remetente_hash],
        "destinatario": ledger[req.destinatario_hash]
    }

if __name__ == "__main__":
    print("[!] Iniciando Zion Gateway...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
