// Área do dono: login, edição do cardápio e dos dados da loja.
// Tudo passa pelo /api, que repassa ao servidor via TLS. A tela é montada só com
// createElement/textContent (nunca innerHTML com dados), para evitar XSS.

const DIAS = [
  ["segunda", "Segunda"], ["terca", "Terça"], ["quarta", "Quarta"], ["quinta", "Quinta"],
  ["sexta", "Sexta"], ["sabado", "Sábado"], ["domingo", "Domingo"],
];
const formatoPreco = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

let itens = [];
let idEditando = null;

// ---------- comunicação ----------

async function api(acao, extras = {}) {
  const token = sessionStorage.getItem("token");
  const resposta = await fetch("/api", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ acao, ...(token ? { token } : {}), ...extras }),
  });
  const dados = await resposta.json();
  if (dados.login) {
    sessionStorage.removeItem("token");
    mostrarLogin(dados.erro);
  }
  if (!dados.ok) throw new Error(dados.erro || "Erro desconhecido");
  return dados.dados;
}

// ---------- utilidades de tela ----------

function el(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function botao(texto, classe, aoClicar) {
  const b = el("button", `botao ${classe}`, texto);
  b.type = "button";
  b.addEventListener("click", aoClicar);
  return b;
}

function mostrarAviso(id, mensagem) {
  const aviso = document.getElementById(id);
  aviso.textContent = mensagem || "";
  aviso.hidden = !mensagem;
}

function mostrarMensagem(id, texto, ok) {
  const span = document.getElementById(id);
  span.textContent = texto;
  span.className = `mensagem ${ok ? "sucesso" : "erro"}`;
}

function separarPorVirgula(texto) {
  return texto.split(",").map((parte) => parte.trim()).filter(Boolean);
}

function numeroOuNulo(texto) {
  return texto.trim() === "" ? null : Number(texto);
}

// ---------- login / logout ----------

function mostrarLogin(mensagem) {
  document.getElementById("tela-painel").hidden = true;
  document.getElementById("botao-sair").hidden = true;
  document.getElementById("tela-login").hidden = false;
  mostrarAviso("aviso-login", mensagem);
  document.getElementById("campo-senha").focus();
}

async function mostrarPainel() {
  document.getElementById("tela-login").hidden = true;
  document.getElementById("tela-painel").hidden = false;
  document.getElementById("botao-sair").hidden = false;
  mostrarAviso("aviso", "");
  try {
    await Promise.all([carregarItens(), carregarLoja()]);
  } catch (erro) {
    mostrarAviso("aviso", erro.message);
  }
}

async function entrar(evento) {
  evento.preventDefault();
  const campo = document.getElementById("campo-senha");
  try {
    const { token } = await api("login", { senha: campo.value });
    sessionStorage.setItem("token", token);
    campo.value = "";
    mostrarAviso("aviso-login", "");
    await mostrarPainel();
  } catch (erro) {
    mostrarAviso("aviso-login", erro.message);
  }
}

async function sair() {
  try {
    await api("logout");
  } catch {
    // mesmo se o servidor estiver fora, o token local é descartado
  }
  sessionStorage.removeItem("token");
  mostrarLogin("");
}

// ---------- itens ----------

async function carregarItens() {
  itens = await api("admin_listar");
  desenharItens();
}

function desenharItens() {
  const lista = document.getElementById("lista-itens");
  lista.replaceChildren();

  const grupos = new Map();
  for (const item of itens) {
    if (!grupos.has(item.categoria)) grupos.set(item.categoria, []);
    grupos.get(item.categoria).push(item);
  }

  const datalist = document.getElementById("lista-categorias");
  datalist.replaceChildren(...[...grupos.keys()].map((categoria) => {
    const opcao = el("option");
    opcao.value = categoria;
    return opcao;
  }));

  if (itens.length === 0) {
    lista.append(el("p", "vazio", "Nenhum item cadastrado."));
    return;
  }

  for (const [categoria, doGrupo] of grupos) {
    const secao = el("section", "grupo");
    secao.append(el("h2", "", categoria), ...doGrupo.map(desenharItem));
    lista.append(secao);
  }
}

function desenharItem(item) {
  const linha = el("article", item.disponivel ? "item" : "item esgotado");
  const info = el("div");
  info.append(el("div", "item-nome", item.nome));

  const custo = item.custo == null ? "—" : formatoPreco.format(item.custo);
  const extras = `Preço ${formatoPreco.format(item.preco)} · Custo ${custo} · Fornecedor ${item.fornecedor || "—"}`;
  info.append(el("div", "item-info", extras));

  const acoes = el("div", "item-acoes");
  acoes.append(
    botao(item.disponivel ? "Disponível" : "Esgotado", item.disponivel ? "alternador ligado" : "alternador",
      () => alternarDisponivel(item)),
    botao("Editar", "secundario", () => editar(item)),
    botao("Remover", "perigo", () => remover(item)),
  );
  linha.append(info, acoes);
  return linha;
}

async function executarNoItem(acao, extras) {
  try {
    await api(acao, extras);
    await carregarItens();
    mostrarAviso("aviso", "");
  } catch (erro) {
    mostrarAviso("aviso", erro.message);
  }
}

function alternarDisponivel(item) {
  return executarNoItem("disponibilidade", { id: item.id, disponivel: !item.disponivel });
}

function remover(item) {
  if (!confirm(`Remover "${item.nome}" do cardápio? Isso não pode ser desfeito.`)) return;
  if (idEditando === item.id) limparFormItem();
  return executarNoItem("remover_item", { id: item.id });
}

function editar(item) {
  const form = document.getElementById("form-item");
  idEditando = item.id;
  form.nome.value = item.nome;
  form.categoria.value = item.categoria;
  form.descricao.value = item.descricao || "";
  form.ingredientes.value = item.ingredientes.join(", ");
  form.preco.value = item.preco;
  form.custo.value = item.custo ?? "";
  form.fornecedor.value = item.fornecedor || "";
  form.disponivel.checked = item.disponivel;
  document.getElementById("titulo-form-item").textContent = `Editar item #${item.id}`;
  document.getElementById("botao-novo").hidden = false;
  mostrarMensagem("msg-item", "", true);
  form.scrollIntoView({ behavior: "smooth" });
  form.nome.focus();
}

function limparFormItem() {
  idEditando = null;
  document.getElementById("form-item").reset();
  document.getElementById("titulo-form-item").textContent = "Novo item";
  document.getElementById("botao-novo").hidden = true;
}

async function salvarItem(evento) {
  evento.preventDefault();
  const form = evento.target;
  const item = {
    nome: form.nome.value,
    categoria: form.categoria.value,
    descricao: form.descricao.value,
    ingredientes: separarPorVirgula(form.ingredientes.value),
    preco: numeroOuNulo(form.preco.value),
    custo: numeroOuNulo(form.custo.value),
    fornecedor: form.fornecedor.value,
    disponivel: form.disponivel.checked,
  };
  if (idEditando !== null) item.id = idEditando;

  try {
    const salvo = await api("salvar_item", { item });
    limparFormItem();
    mostrarMensagem("msg-item", `"${salvo.nome}" salvo.`, true);
    await carregarItens();
  } catch (erro) {
    mostrarMensagem("msg-item", erro.message, false);
  }
}

// ---------- dados da loja ----------

function montarDias() {
  const caixa = document.getElementById("dias");
  for (const [dia, nome] of DIAS) {
    const linha = el("div", "dia");
    linha.dataset.dia = dia;

    const fechado = el("input");
    fechado.type = "checkbox";
    fechado.className = "fechado";
    const rotuloFechado = el("label", "marcar");
    rotuloFechado.append(fechado, " Fechado");

    const abre = el("input");
    abre.type = "time";
    abre.className = "abre";
    abre.setAttribute("aria-label", `${nome}: abre`);
    const fecha = el("input");
    fecha.type = "time";
    fecha.className = "fecha";
    fecha.setAttribute("aria-label", `${nome}: fecha`);

    fechado.addEventListener("change", () => {
      abre.disabled = fecha.disabled = fechado.checked;
    });
    linha.append(el("span", "dia-nome", nome), rotuloFechado, abre, el("span", "", "às"), fecha);
    caixa.append(linha);
  }
}

async function carregarLoja() {
  const loja = await api("loja");
  const form = document.getElementById("form-loja");
  form.nome.value = loja.nome;
  form.endereco.value = loja.endereco || "";
  form.telefone.value = loja.telefone || "";
  form.instagram.value = loja.instagram || "";
  form.pagamentos.value = (loja.pagamentos || []).join(", ");

  for (const linha of document.querySelectorAll("#dias .dia")) {
    const horario = loja.funcionamento[linha.dataset.dia];
    const [fechado, abre, fecha] = ["fechado", "abre", "fecha"].map((c) => linha.querySelector(`.${c}`));
    fechado.checked = !horario;
    abre.value = horario ? horario.abre : "";
    fecha.value = horario ? horario.fecha : "";
    abre.disabled = fecha.disabled = !horario;
  }
}

async function salvarLoja(evento) {
  evento.preventDefault();
  const form = evento.target;
  const funcionamento = {};
  for (const linha of document.querySelectorAll("#dias .dia")) {
    const fechado = linha.querySelector(".fechado").checked;
    funcionamento[linha.dataset.dia] = fechado ? null : {
      abre: linha.querySelector(".abre").value,
      fecha: linha.querySelector(".fecha").value,
    };
  }
  const loja = {
    nome: form.nome.value,
    endereco: form.endereco.value,
    telefone: form.telefone.value,
    instagram: form.instagram.value,
    pagamentos: separarPorVirgula(form.pagamentos.value),
    funcionamento,
  };

  try {
    await api("atualizar_loja", { loja });
    mostrarMensagem("msg-loja", "Dados da loja salvos.", true);
    await carregarLoja();
  } catch (erro) {
    mostrarMensagem("msg-loja", erro.message, false);
  }
}

// ---------- início ----------

function iniciar() {
  montarDias();
  document.getElementById("form-login").addEventListener("submit", entrar);
  document.getElementById("botao-sair").addEventListener("click", sair);
  document.getElementById("form-item").addEventListener("submit", salvarItem);
  document.getElementById("botao-novo").addEventListener("click", limparFormItem);
  document.getElementById("form-loja").addEventListener("submit", salvarLoja);

  if (sessionStorage.getItem("token")) mostrarPainel();
  else mostrarLogin("");
}

iniciar();
