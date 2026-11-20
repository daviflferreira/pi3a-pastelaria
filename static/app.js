// Interface do atendente: tudo passa pelo /api, que repassa ao servidor de consultas via TLS.

const NOMES_DIAS = {
  segunda: "Seg", terca: "Ter", quarta: "Qua", quinta: "Qui",
  sexta: "Sex", sabado: "Sáb", domingo: "Dom",
};
const formatoPreco = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

let itensAtuais = [];
let categoriaSelecionada = "Todas";

async function api(acao, extras = {}) {
  const resposta = await fetch("/api", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ acao, ...extras }),
  });
  const dados = await resposta.json();
  if (!dados.ok) throw new Error(dados.erro || "Erro desconhecido");
  return dados.dados;
}

function el(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function mostrarAviso(mensagem) {
  const aviso = document.getElementById("aviso");
  aviso.textContent = mensagem;
  aviso.hidden = !mensagem;
}

function resumirHorarios(funcionamento) {
  const abertos = Object.entries(funcionamento).filter(([, h]) => h);
  if (abertos.length === 0) return "";
  const { abre, fecha } = abertos[0][1];
  const mesmos = abertos.every(([, h]) => h.abre === abre && h.fecha === fecha);
  const dias = abertos.map(([dia]) => NOMES_DIAS[dia]);
  if (mesmos) return `${dias[0]} a ${dias[dias.length - 1]}, ${abre} às ${fecha}`;
  return abertos.map(([dia, h]) => `${NOMES_DIAS[dia]} ${h.abre}–${h.fecha}`).join(" · ");
}

async function carregarLoja() {
  const loja = await api("loja");
  document.getElementById("nome-loja").textContent = loja.nome;
  document.title = `${loja.nome} · Consulta`;
  const contato = [loja.telefone, loja.instagram, loja.endereco].filter(Boolean).join(" · ");
  document.getElementById("contato").textContent = contato;
  const pagamentos = loja.pagamentos.length ? ` · Pagamento: ${loja.pagamentos.join(", ")}` : "";
  document.getElementById("horarios").textContent = resumirHorarios(loja.funcionamento) + pagamentos;
}

async function atualizarStatus() {
  const status = await api("status");
  const etiqueta = document.getElementById("status");
  etiqueta.textContent = status.mensagem;
  etiqueta.className = `status ${status.aberto ? "aberto" : "fechado"}`;
}

function desenharCategorias() {
  const nav = document.getElementById("categorias");
  nav.replaceChildren();
  const categorias = ["Todas", ...new Set(itensAtuais.map((item) => item.categoria))];
  if (!categorias.includes(categoriaSelecionada)) categoriaSelecionada = "Todas";

  for (const categoria of categorias) {
    const botao = el("button", categoria === categoriaSelecionada ? "ativa" : "", categoria);
    botao.type = "button";
    botao.addEventListener("click", () => {
      categoriaSelecionada = categoria;
      desenharCategorias();
      desenharCardapio();
    });
    nav.append(botao);
  }
}

function desenharItem(item) {
  const linha = el("article", item.disponivel ? "item" : "item esgotado");
  const info = el("div");

  const nome = el("div", "item-nome", item.nome);
  if (!item.disponivel) nome.append(el("span", "etiqueta", "ESGOTADO"));
  info.append(nome);

  const detalhes = item.descricao || item.ingredientes.join(", ");
  if (detalhes) info.append(el("div", "item-info", detalhes));

  linha.append(info, el("div", "item-preco", formatoPreco.format(item.preco)));
  return linha;
}

function desenharCardapio() {
  const main = document.getElementById("cardapio");
  main.replaceChildren();

  const visiveis = itensAtuais.filter(
    (item) => categoriaSelecionada === "Todas" || item.categoria === categoriaSelecionada
  );
  document.getElementById("contagem").textContent = `${visiveis.length} itens`;

  if (visiveis.length === 0) {
    main.append(el("p", "vazio", "Nenhum item encontrado."));
    return;
  }

  const grupos = new Map();
  for (const item of visiveis) {
    if (!grupos.has(item.categoria)) grupos.set(item.categoria, []);
    grupos.get(item.categoria).push(item);
  }
  for (const [categoria, itens] of grupos) {
    const secao = el("section", "grupo");
    secao.append(el("h2", "", categoria), ...itens.map(desenharItem));
    main.append(secao);
  }
  // os cartões entram um depois do outro (só os primeiros, pra não demorar)
  main.querySelectorAll(".item").forEach((cartao, i) => cartao.style.setProperty("--ordem", Math.min(i, 14)));
}

async function buscar(termo) {
  try {
    itensAtuais = termo ? await api("buscar", { termo }) : await api("listar");
    mostrarAviso("");
  } catch (erro) {
    itensAtuais = [];
    mostrarAviso(erro.message);
  }
  desenharCategorias();
  desenharCardapio();
}

function iniciarBusca() {
  const campo = document.getElementById("campo-busca");
  let espera;
  campo.addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(() => buscar(campo.value.trim()), 250);
  });
}

async function iniciar() {
  iniciarBusca();
  try {
    await Promise.all([carregarLoja(), atualizarStatus(), buscar("")]);
  } catch (erro) {
    mostrarAviso(erro.message);
  }
  setInterval(() => atualizarStatus().catch(() => {}), 60_000);
}

iniciar();
