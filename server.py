from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from supabase import create_client, Client
import uvicorn
import os

# --- CONFIGURAÇÃO DE SEGURANÇA (LGPD) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONEXÃO SUPABASE ---
SUPABASE_URL = "https://vnkmsteysjkqzeivhfij.supabase.co"
SUPABASE_KEY = "sb_publishable_ws-6h46BFv0RXGDPTjmjsA_nuk-79RO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Zion Gateway V3.0 - Persistência Imortal")

# --- MODELOS DE DADOS ---
class UserAuth(BaseModel):
    wallet_hash: str
    username: str
    password: str

class MineRequest(BaseModel):
    wallet_hash: str
    recompensa: float

class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario: str # Pode ser @Username ou 0xHash
    quantidade: float

# --- FUNÇÕES AUXILIARES ---
def hash_pass(password: str): 
    return pwd_context.hash(password)

def verify_pass(plain, hashed): 
    return pwd_context.verify(plain, hashed)

# --- ROTAS DE AUTENTICAÇÃO ---
@app.post("/auth/register")
def register(user: UserAuth):
    clean_name = user.username.lower()
    if not clean_name.startswith("@"): 
        clean_name = "@" + clean_name
    
    try:
        supabase.table("usuarios").insert({
            "wallet_hash": user.wallet_hash,
            "username": clean_name,
            "password_hash": hash_pass(user.password),
            "saldo": 0.0
        }).execute()
        return {"status": "Registrado com sucesso!", "username": clean_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Username ou Wallet já existem.")

@app.post("/auth/login")
def login(user: UserAuth):
    clean_name = user.username.lower()
    if not clean_name.startswith("@"): 
        clean_name = "@" + clean_name

    res = supabase.table("usuarios").select("*").eq("username", clean_name).execute()
    if not res.data: 
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    db_user = res.data[0]
    if not verify_pass(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    
    return {
        "wallet_hash": db_user["wallet_hash"],
        "username": db_user["username"],
        "saldo": float(db_user["saldo"])
    }

# --- ROTAS DE ECONOMIA ---
@app.post("/minerar")
def minerar(req: MineRequest):
    res = supabase.table("usuarios").select("saldo").eq("wallet_hash", req.wallet_hash).execute()
    if not res.data: 
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    novo_saldo = float(res.data[0]["saldo"]) + req.recompensa
    supabase.table("usuarios").update({"saldo": novo_saldo}).eq("wallet_hash", req.wallet_hash).execute()
    return {"status": "Bloco validado", "novo_saldo": novo_saldo}

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    # 1. Validar Remetente
    rem = supabase.table("usuarios").select("saldo").eq("wallet_hash", req.remetente_hash).execute()
    if not rem.data or float(rem.data[0]["saldo"]) < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    # 2. Identificar Destinatário
    target_hash = req.destinatario
    if req.destinatario.startswith("@"):
        dest_res = supabase.table("usuarios").select("wallet_hash").eq("username", req.destinatario.lower()).execute()
        if not dest_res.data: 
            raise HTTPException(status_code=404, detail="Destinatário não existe.")
        target_hash = dest_res.data[0]["wallet_hash"]

    # 3. Executar Transferência
    novo_saldo_rem = float(rem.data[0]["saldo"]) - req.quantidade
    
    dest_data = supabase.table("usuarios").select("saldo").eq("wallet_hash", target_hash).execute()
    if not dest_data.data: 
        raise HTTPException(status_code=404, detail="Erro no destino.")
    novo_saldo_dest = float(dest_data[0]["saldo"]) + req.quantidade

    supabase.table("usuarios").update({"saldo": novo_saldo_rem}).eq("wallet_hash", req.remetente_hash).execute()
    supabase.table("usuarios").update({"saldo": novo_saldo_dest}).eq("wallet_hash", target_hash).execute()

    return {"status": "Transferência Concluída", "de": req.remetente_hash, "para": target_hash}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
