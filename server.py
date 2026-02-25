from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import uvicorn
import os
import uuid
import hashlib
from typing import Optional

# Sem passlib, sem bcrypt! Apenas o núcleo duro do Python.
SUPABASE_URL = "https://vnkmsteysjkqzeivhfij.supabase.co"
SUPABASE_KEY = "sb_publishable_ws-6h46BFv0RXGDPTjmjsA_nuk-79RO"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Zion Gateway V3.0")

class UserAuth(BaseModel):
    wallet_hash: Optional[str] = None
    username: str
    password: str

class MineRequest(BaseModel):
    wallet_hash: str
    recompensa: float

class TransferRequest(BaseModel):
    remetente_hash: str
    destinatario: str
    quantidade: float

# Nossa nova armadura de criptografia (sem limites de 72 bytes)
def pure_hash(password: str):
    return hashlib.sha256(password.encode('utf-8', errors='ignore')).hexdigest()

@app.post("/auth/register")
def register(user: UserAuth):
    clean_name = user.username.lower()
    if not clean_name.startswith("@"):
        clean_name = "@" + clean_name
        
    nova_wallet = "0x" + str(uuid.uuid4().hex)[:8].upper()

    try:
        senha_blindada = pure_hash(user.password)
        supabase.table("usuarios").insert({
            "wallet_hash": nova_wallet,
            "username": clean_name,
            "password_hash": senha_blindada,
            "saldo": 0.0
        }).execute()
        return {"status": "Registrado com sucesso!", "username": clean_name, "wallet_hash": nova_wallet}
    except Exception as e:
        # Mudamos a mensagem para "Erro Zion" para termos a prova visual do novo deploy
        raise HTTPException(status_code=400, detail=f"Erro Zion: {str(e)}")

@app.post("/auth/login")
def login(user: UserAuth):
    clean_name = user.username.lower()
    if not clean_name.startswith("@"):
        clean_name = "@" + clean_name

    res = supabase.table("usuarios").select("*").eq("username", clean_name).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    db_user = res.data[0]
    if pure_hash(user.password) != db_user["password_hash"]:
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    return {
        "wallet_hash": db_user["wallet_hash"],
        "username": db_user["username"],
        "saldo": float(db_user["saldo"])
    }

@app.post("/minerar")
def minerar(req: MineRequest):
    res = supabase.table("usuarios").select("saldo").eq("wallet_hash", req.wallet_hash).execute()
    if not res.data: raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    novo_saldo = float(res.data[0]["saldo"]) + req.recompensa
    supabase.table("usuarios").update({"saldo": novo_saldo}).eq("wallet_hash", req.wallet_hash).execute()
    return {"status": "Bloco validado", "novo_saldo": novo_saldo}

@app.post("/transferir")
def transferir_sng(req: TransferRequest):
    rem = supabase.table("usuarios").select("saldo").eq("wallet_hash", req.remetente_hash).execute()
    if not rem.data or float(rem.data[0]["saldo"]) < req.quantidade:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")
    
    target_hash = req.destinatario
    if req.destinatario.startswith("@"):
        dest_res = supabase.table("usuarios").select("wallet_hash").eq("username", req.destinatario.lower()).execute()
        if not dest_res.data: raise HTTPException(status_code=404, detail="Destinatário não existe.")
        target_hash = dest_res.data[0]["wallet_hash"]

    novo_saldo_rem = float(rem.data[0]["saldo"]) - req.quantidade
    dest_data = supabase.table("usuarios").select("saldo").eq("wallet_hash", target_hash).execute()
    if not dest_data.data: raise HTTPException(status_code=404, detail="Erro no destino.")
    novo_saldo_dest = float(dest_data.data[0]["saldo"]) + req.quantidade
    
    supabase.table("usuarios").update({"saldo": novo_saldo_rem}).eq("wallet_hash", req.remetente_hash).execute()
    supabase.table("usuarios").update({"saldo": novo_saldo_dest}).eq("wallet_hash", target_hash).execute()
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
