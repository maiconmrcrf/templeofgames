/* ============ TEMPLE OF GAMES - APP ============ */
var SESSION_KEY = "temple_session_v5";
var VALOR_MINIMO = 5.00;
var CFG = null;
var _pollTimer = null;

/* ---------- HELPERS ---------- */
function getSession() { return localStorage.getItem(SESSION_KEY); }
function setSession(e) { localStorage.setItem(SESSION_KEY, e); }
function clearSession() { localStorage.removeItem(SESSION_KEY); }
function BRL(v) {
  return "R$ " + Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function mostrarView(id) {
  document.querySelectorAll(".view").forEach(function(v){ v.classList.remove("ativo"); });
  document.getElementById(id).classList.add("ativo");
  window.scrollTo({ top: 0, behavior: "instant" });
}
function setMsg(id, txt, tipo) {
  var el = document.getElementById(id);
  el.textContent = txt;
  el.className = "auth-msg" + (tipo ? " " + tipo : "");
}
function mascaraCPF(inp) {
  var v = inp.value.replace(/\D/g, "").slice(0, 11);
  v = v.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  inp.value = v;
}
function escapar(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

/* ---------- CARREGAR CONFIG ---------- */
async function carregarConfig() {
  try { CFG = await (await fetch("/api/config")).json(); }
  catch(e) { CFG = null; }
  if (!CFG) return;

  var emp = CFG.empresa || {};
  var nome = emp.nome || "Temple of Games";
  var logo = emp.logo_emoji || "🏛️";
  var partes = nome.split(" ");

  var elSplash = document.getElementById("splashLogo");
  if (elSplash) elSplash.textContent = logo;
  var elSplashNome = document.getElementById("splashNome");
  if (elSplashNome) elSplashNome.innerHTML = partes[0].toUpperCase() + "<span>" + partes.slice(1).join(" ").toUpperCase() + "</span>";
  var elLogin = document.getElementById("loginLogo");
  if (elLogin) elLogin.textContent = logo;
  var elCad = document.getElementById("cadLogo");
  if (elCad) elCad.textContent = logo;
  var elTop = document.getElementById("topLogo");
  if (elTop) elTop.innerHTML = partes[0].toUpperCase() + ' <span class="logo-icon">' + logo + '</span> ' + partes.slice(1).join(" ").toUpperCase();
  var elFoot = document.getElementById("footNome");
  if (elFoot) elFoot.textContent = nome;
  var elBanner = document.getElementById("bannerApp");
  if (elBanner && CFG.banner) elBanner.textContent = CFG.banner;

  if (CFG.cores) {
    var root = document.documentElement.style;
    if (CFG.cores.dourado) root.setProperty("--dourado", CFG.cores.dourado);
    if (CFG.cores.dourado_claro) root.setProperty("--dourado2", CFG.cores.dourado_claro);
  }

  // Renderiza jogos
  var grid = document.getElementById("gameGrid");
  if (!grid) return;
  var lista = CFG.jogos || [];
  var html = "";
  for (var i = 0; i < lista.length; i++) {
    var j = lista[i];
    var btn;
    if (j.vip) {
      btn = '<button class="btn-jogar btn-vip" onclick="abrirVIP()">Ver Mais</button>';
    } else {
      btn = '<button class="btn-jogar" onclick="abrirJogo(\'' + escapar(j.link || "#") + '\')">▶ Jogar</button>';
    }
    html += '<div class="game-card">' +
      '<img src="' + escapar(j.imagem || "") + '" alt="' + escapar(j.nome || "") + '">' +
      '<span>' + escapar(j.nome || "") + '</span>' +
      btn +
      '</div>';
  }
  grid.innerHTML = html;
}

/* ---------- CADASTRO ---------- */
async function fazerCadastro(e) {
  e.preventDefault();
  var nome = document.getElementById("cadNome").value.trim();
  var nasc = document.getElementById("cadNasc").value;
  var cpf = document.getElementById("cadCpf").value.trim();
  var email = document.getElementById("cadEmail").value.trim().toLowerCase();
  var senha = document.getElementById("cadSenha").value;
  var senha2 = document.getElementById("cadSenha2").value;

  if (nome.split(" ").filter(Boolean).length < 2) return setMsg("msgCadastro", "Informe nome e sobrenome.", "erro");
  if (!nasc) return setMsg("msgCadastro", "Informe a data de nascimento.", "erro");
  if (cpf.replace(/\D/g, "").length !== 11) return setMsg("msgCadastro", "CPF deve ter 11 dígitos.", "erro");
  if (senha.length < 6) return setMsg("msgCadastro", "Senha mín. 6 caracteres.", "erro");
  if (senha !== senha2) return setMsg("msgCadastro", "As senhas não coincidem.", "erro");

  setMsg("msgCadastro", "Criando conta...", "");
  try {
    var r = await fetch("/api/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: nome, nasc: nasc, cpf: cpf, email: email, senha: senha })
    });
    var d = await r.json();
    if (!r.ok) return setMsg("msgCadastro", "❌ " + (d.erro || "Erro"), "erro");
    setMsg("msgCadastro", "✅ Conta criada!", "ok");
    setTimeout(function(){ setSession(email); abrirApp(); }, 900);
  } catch (err) { setMsg("msgCadastro", "❌ " + err.message, "erro"); }
}

/* ---------- LOGIN ---------- */
async function fazerLogin(e) {
  e.preventDefault();
  var email = document.getElementById("loginEmail").value.trim().toLowerCase();
  var senha = document.getElementById("loginSenha").value;
  setMsg("msgLogin", "Verificando...", "");
  try {
    var r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, senha: senha })
    });
    var d = await r.json();
    if (!r.ok) return setMsg("msgLogin", "❌ " + (d.erro || "Erro"), "erro");
    setSession(email);
    setMsg("msgLogin", "✅ Bem-vindo!", "ok");
    setTimeout(abrirApp, 400);
  } catch (err) { setMsg("msgLogin", "❌ " + err.message, "erro"); }
}

function sair() {
  if (!confirm("Deseja realmente sair da conta?")) return;
  clearSession();
  fecharMenu();
  mostrarView("view-splash");
  document.getElementById("loginEmail").value = "";
  document.getElementById("loginSenha").value = "";
  document.getElementById("msgLogin").textContent = "";
}

/* ---------- ABRIR APP ---------- */
async function abrirApp() {
  var email = getSession();
  if (!email) return mostrarView("view-splash");
  try {
    var r = await fetch("/api/usuarios/" + encodeURIComponent(email));
    if (!r.ok) { clearSession(); return mostrarView("view-splash"); }
    var u = await r.json();
    document.getElementById("saldoApp").textContent = BRL(u.saldo || 0);
    document.getElementById("sbSaldo").textContent = BRL(u.saldo || 0);
    document.getElementById("sbNome").textContent = u.nome;
    document.getElementById("sbEmail").textContent = u.email;
    mostrarView("view-app");
  } catch(e) { clearSession(); mostrarView("view-splash"); }
}

async function atualizarSaldo() {
  var email = getSession();
  if (!email) return;
  try {
    var r = await fetch("/api/usuarios/" + encodeURIComponent(email));
    var u = await r.json();
    document.getElementById("saldoApp").textContent = BRL(u.saldo || 0);
    document.getElementById("sbSaldo").textContent = BRL(u.saldo || 0);
  } catch(e) {}
}

/* ---------- MENU / MODAL ---------- */
function abrirMenu() {
  document.getElementById("sidebar").classList.add("ativo");
  document.getElementById("overlay").classList.add("ativo");
}
function fecharMenu() {
  document.getElementById("sidebar").classList.remove("ativo");
  document.getElementById("overlay").classList.remove("ativo");
}
function abrirModal(titulo, corpo) {
  document.getElementById("modalTitulo").textContent = titulo;
  document.getElementById("modalCorpo").innerHTML = corpo;
  document.getElementById("modal").classList.add("ativo");
  fecharMenu();
}
function fecharModal() {
  document.getElementById("modal").classList.remove("ativo");
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

/* ---------- PERFIL ---------- */
async function abrirPerfil() {
  var r = await fetch("/api/usuarios/" + encodeURIComponent(getSession()));
  var u = await r.json();
  abrirModal("Meu Perfil",
    '<label>Nome completo</label><div class="modal-info">' + escapar(u.nome) + '</div>' +
    '<label>Data de nascimento</label><div class="modal-info">' + escapar(u.nasc || "—") + '</div>' +
    '<label>CPF</label><div class="modal-info">' + escapar(u.cpf || "—") + '</div>' +
    '<label>E-mail</label><div class="modal-info">' + escapar(u.email) + '</div>' +
    '<label>Saldo atual</label><div class="modal-info"><strong>' + BRL(u.saldo || 0) + '</strong></div>');
}

/* ---------- DEPOSITO ---------- */
function abrirDeposito() {
  abrirModal("Depositar via PIX",
    '<p style="font-size:.85rem;color:#9ca3af;margin-bottom:10px;">Informe o valor. Uma cobrança PIX será gerada.</p>' +
    '<label>Valor do depósito (mín. ' + BRL(VALOR_MINIMO) + ')</label>' +
    '<input type="number" id="depValor" placeholder="0,00" min="' + VALOR_MINIMO + '" step="0.01" />' +
    '<button class="btn-gold" onclick="confirmarDeposito()">Gerar QR Code PIX</button>');
}

async function confirmarDeposito() {
  var v = parseFloat(document.getElementById("depValor").value) || 0;
  if (v < VALOR_MINIMO) return alert("❌ Valor mínimo: " + BRL(VALOR_MINIMO));
  var email = getSession();
  document.getElementById("modalCorpo").innerHTML =
    '<p style="text-align:center;color:#9ca3af;padding:24px 0;"><span class="spinner"></span> Gerando QR Code PIX...</p>';
  try {
    var r = await fetch("/api/criar-pix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ valor: v, email: email })
    });
    var data = await r.json();
    if (data.erro) {
      document.getElementById("modalCorpo").innerHTML =
        '<p class="pix-status erro">❌ ' + data.erro + '</p><button class="btn-gold" onclick="abrirDeposito()">Tentar novamente</button>';
      return;
    }
    document.getElementById("modalCorpo").innerHTML =
      '<p style="font-size:.85rem;color:#9ca3af;margin-bottom:10px;text-align:center;">Depósito de <strong style="color:#d4af37;">' + BRL(v) + '</strong></p>' +
      '<label>PIX Copia e Cola</label>' +
      '<textarea class="pix-payload" readonly onclick="this.select()">' + data.payload + '</textarea>' +
      '<button class="btn-gold" onclick="copiarPix()">📋 Copiar Código PIX</button>' +
      '<p class="pix-status" id="pixStatus"><span class="spinner"></span> Aguardando pagamento...</p>';
    iniciarPolling(data.payment_id);
  } catch (err) {
    document.getElementById("modalCorpo").innerHTML =
      '<p class="pix-status erro">❌ ' + err.message + '</p><button class="btn-gold" onclick="abrirDeposito()">Tentar novamente</button>';
  }
}

function copiarPix() {
  var ta = document.querySelector(".pix-payload");
  if (!ta) return;
  ta.select();
  try { document.execCommand("copy"); alert("✅ Copiado!"); }
  catch(e) { navigator.clipboard.writeText(ta.value).then(function(){ alert("✅ Copiado!"); }, function(){ alert("Copie manualmente."); }); }
}

function iniciarPolling(payment_id) {
  if (_pollTimer) clearInterval(_pollTimer);
  var tentativas = 0;
  _pollTimer = setInterval(async function(){
    tentativas++;
    if (tentativas > 120) {
      clearInterval(_pollTimer); _pollTimer = null;
      var el = document.getElementById("pixStatus");
      if (el) { el.className = "pix-status erro"; el.textContent = "⏱️ Tempo esgotado."; }
      return;
    }
    try {
      var r = await fetch("/api/verificar-pagamento/" + payment_id);
      var d = await r.json();
      if (["RECEIVED","CONFIRMED","RECEIVED_IN_CASH"].indexOf(d.status) !== -1) {
        clearInterval(_pollTimer); _pollTimer = null;
        await atualizarSaldo();
        var el = document.getElementById("pixStatus");
        if (el) { el.className = "pix-status ok"; el.textContent = "✅ Pagamento confirmado!"; }
        setTimeout(function(){ fecharModal(); alert("✅ Pagamento confirmado!"); }, 1200);
      }
    } catch(e) {}
  }, 5000);
}

/* ---------- SAQUE ---------- */
function mascararCPF(cpf) {
  var limpo = (cpf || "").replace(/\D/g, "");
  if (limpo.length !== 11) return "xxx.xxx.xxx-xx";
  return limpo.substring(0,3) + ".xxx.xxx-" + limpo.substring(9,11);
}

async function abrirSaque() {
  var email = getSession();
  var u = {};
  try { u = await (await fetch("/api/usuarios/" + encodeURIComponent(email))).json(); } catch(e) {}
  abrirModal("Sacar",
    '<p style="font-size:.72rem;color:#666;margin-bottom:14px;text-align:center;line-height:1.5;">' +
      escapar(u.nome || "Usuário") + ' &nbsp;·&nbsp; <span style="font-family:monospace;color:#888;">' + mascararCPF(u.cpf) + '</span>' +
    '</p>' +
    '<label>Valor do saque</label>' +
    '<input type="number" id="saqValor" placeholder="0,00" min="1" step="0.01" />' +
    '<button class="btn-gold" onclick="confirmarSaque()">Solicitar Saque</button>');
}

async function confirmarSaque() {
  var v = parseFloat(document.getElementById("saqValor").value) || 0;
  if (v <= 0) return alert("Informe um valor válido.");
  var email = getSession();
  try {
    var r = await fetch("/api/usuarios/" + encodeURIComponent(email) + "/saldo", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta: -v, motivo: "Saque" })
    });
    var d = await r.json();
    if (!r.ok) return alert("❌ " + (d.erro || "Erro"));
    if (d.saldo < 0) {
      await fetch("/api/usuarios/" + encodeURIComponent(email) + "/saldo", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delta: v, motivo: "Estorno saque" })
      });
      return alert("❌ Saldo insuficiente.");
    }
    await atualizarSaldo();
    fecharModal();
    alert("✅ Saque de " + BRL(v) + " solicitado!");
  } catch(err) { alert("Erro: " + err.message); }
}

/* ---------- HISTORICO ---------- */
async function abrirHistorico() {
  var r = await fetch("/api/usuarios/" + encodeURIComponent(getSession()) + "/historico");
  var h = await r.json();
  var html = !h.length
    ? '<div class="hist-empty">Nenhuma movimentação.</div>'
    : h.map(function(item){
        var dt = new Date(item.data).toLocaleString("pt-BR");
        var cls = item.valor >= 0 ? "val-pos" : "val-neg";
        var sinal = item.valor >= 0 ? "+" : "−";
        return '<div class="hist-item"><span>' + escapar(item.tipo) + '<br><small style="color:#666">' + dt + '</small></span>' +
               '<span class="' + cls + '">' + sinal + ' ' + BRL(Math.abs(item.valor)) + '</span></div>';
      }).join("");
  abrirModal("Histórico", html);
}

/* ---------- JOGOS E VIP ---------- */
async function abrirJogo(url) {
  var email = getSession();
  if (!email) return alert("Faça login para jogar.");
  try {
    var u = await (await fetch("/api/usuarios/" + encodeURIComponent(email))).json();
    var saldo = u.saldo || 0;
    if (saldo <= 0) {
      abrirModal("Saldo Insuficiente",
        '<div style="text-align:center;padding:10px 0;">' +
          '<div style="font-size:3rem;margin-bottom:10px;">🔒</div>' +
          '<p style="font-size:1rem;color:#d4af37;font-weight:700;margin-bottom:10px;">Você está sem saldo!</p>' +
          '<p style="font-size:.85rem;color:#9ca3af;line-height:1.5;margin-bottom:20px;">' +
            'Faça um depósito para liberar o acesso aos jogos.' +
          '</p>' +
          '<button class="btn-gold" onclick="fecharModal();abrirDeposito()" style="width:100%;">💰 Depositar Agora</button>' +
          '<button class="btn-ghost" onclick="fecharModal()" style="width:100%;margin-top:8px;">Depois</button>' +
        '</div>');
      return;
    }
    window.open(url, "_blank");
  } catch(e) { alert("Erro ao verificar saldo."); }
}

function abrirVIP() {
  abrirModal("Área VIP",
    '<div style="text-align:center;padding:14px 0;">' +
      '<div style="font-size:2.6rem;margin-bottom:10px;">🔒</div>' +
      '<p style="font-size:1rem;color:#d4af37;font-weight:800;margin-bottom:10px;">Área VIP Bloqueada</p>' +
      '<p style="font-size:.85rem;color:#9ca3af;line-height:1.6;margin-bottom:20px;">' +
        'Faça <strong style="color:#d4af37;">2 depósitos</strong> no mínimo<br>para liberar' +
      '</p>' +
      '<button class="btn-gold" onclick="fecharModal();abrirDeposito()" style="width:100%;">💰 Depositar Agora</button>' +
    '</div>');
}

/* ---------- SUPORTE ---------- */
function abrirSuporte() {
  abrirModal("Suporte",
    '<label>E-mail</label><div class="modal-info">suporte@templeofgames.demo</div>' +
    '<label>WhatsApp</label><div class="modal-info">+55 (11) 99999-0000</div>' +
    '<label>Horário</label><div class="modal-info">24h / 7 dias</div>');
}

/* ---------- INIT ---------- */
(async function init() {
  await carregarConfig();
  if (getSession()) setTimeout(abrirApp, 300);
})();
