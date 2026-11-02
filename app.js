(function () {
  const DOMINIO_PUBLICO = "https://vitrine-express-ten.vercel.app";

  let listaProdutos = Array.isArray(window.PRODUTOS_INICIAIS) ? [...window.PRODUTOS_INICIAIS] : [];
  let categoriaAtiva = "todos";
  let plataformaAtiva = "todas";
  let termoBusca = "";
  let produtoVideoAtualId = null;
  let produtoClienteModalAtual = null;

  const isModoAdmin =
    location.hostname === "localhost" ||
    location.hostname === "127.0.0.1" ||
    location.protocol === "file:" ||
    location.search.includes("admin=1");

  const gridEl = document.getElementById("productsGrid");
  const emptyStateEl = document.getElementById("emptyState");
  const countEl = document.getElementById("resultsCount");
  const searchInput = document.getElementById("searchInput");
  const clearSearchBtn = document.getElementById("clearSearchBtn");
  const quickNumbersEl = document.getElementById("quickNumbers");
  const adminHeaderActions = document.getElementById("adminHeaderActions");

  if (!isModoAdmin && adminHeaderActions) {
    adminHeaderActions.style.display = "none";
  }

  async function sincronizarProdutosDoServidor() {
    if (location.protocol === "file:") return;
    try {
      const resp = await fetch("/api/produtos", { cache: "no-store" });
      if (resp.ok) {
        const dados = await resp.json();
        if (Array.isArray(dados.produtos)) {
          listaProdutos = dados.produtos;
          renderizarAtalhosNumeros(listaProdutos);
          renderizarCatalogo();
          verificarParametroProdutoNaUrl();
        }
      }
    } catch (e) {
      // Sem servidor Python ativo (ex: site estático na Vercel), usa window.PRODUTOS_INICIAIS
    }
  }

  function formatarMoeda(valor) {
    return Number(valor).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL"
    });
  }

  function calcularDesconto(antigo, atual) {
    if (!antigo || antigo <= atual) return 0;
    return Math.round(((antigo - atual) / antigo) * 100);
  }

  function obterNomeCategoria(slug) {
    const mapa = {
      casa: "Casa & Cozinha",
      eletronicos: "Eletrônicos",
      beleza: "Beleza & Cuidados",
      ferramentas: "Ferramentas & Auto"
    };
    return mapa[slug] || "Ofertas";
  }

  function obterNomePlataforma(slug) {
    const mapa = {
      mercadolivre: "Mercado Livre",
      shopee: "Shopee",
      amazon: "Amazon"
    };
    return mapa[slug] || "Loja Oficial";
  }

  function montarLinkDiretoProduto(p) {
    return `${DOMINIO_PUBLICO}/?p=${encodeURIComponent(p.codigo)}`;
  }

  function compartilharNoWhatsApp(p) {
    const linkDireto = montarLinkDiretoProduto(p);
    const nomePlat = p.plataformaNome || obterNomePlataforma(p.plataforma);
    const texto =
      `🔥 *Olha esse achadinho em promoção no ${nomePlat}!*\n\n` +
      `📦 ${p.titulo}\n` +
      `💰 Por *${formatarMoeda(p.precoAtual)}*\n\n` +
      `👇 *Assista ao vídeo e compre no link oficial abaixo:*\n` +
      `${linkDireto}`;

    const urlWa = `https://api.whatsapp.com/send?text=${encodeURIComponent(texto)}`;
    window.open(urlWa, "_blank", "noopener,noreferrer");
  }

  // Modal Público de Vídeo + Botão Gigante de Compra
  const clienteOfertaModal = document.getElementById("clienteOfertaModal");
  const closeClienteOfertaBtn = document.getElementById("closeClienteOfertaBtn");
  const clienteOfertaCodigo = document.getElementById("clienteOfertaCodigo");
  const clienteVideoPlayer = document.getElementById("clienteVideoPlayer");
  const clienteFotoFallback = document.getElementById("clienteFotoFallback");
  const clienteOfertaTitulo = document.getElementById("clienteOfertaTitulo");
  const clientePrecoAntigo = document.getElementById("clientePrecoAntigo");
  const clientePrecoAtual = document.getElementById("clientePrecoAtual");
  const clienteBtnComprarGigante = document.getElementById("clienteBtnComprarGigante");
  const clienteBtnZapShare = document.getElementById("clienteBtnZapShare");

  function abrirModalOfertaCliente(p) {
    if (!p) return;
    produtoClienteModalAtual = p;
    const nomePlat = (p.plataformaNome || obterNomePlataforma(p.plataforma)).toUpperCase();

    clienteOfertaCodigo.textContent = `🔥 OFERTA #${p.codigo} • ${nomePlat}`;
    clienteOfertaTitulo.textContent = p.titulo;

    if (p.precoAntigo && p.precoAntigo > p.precoAtual) {
      clientePrecoAntigo.textContent = `De ${formatarMoeda(p.precoAntigo)}`;
      clientePrecoAntigo.style.display = "inline";
    } else {
      clientePrecoAntigo.style.display = "none";
    }

    clientePrecoAtual.textContent = `Por ${formatarMoeda(p.precoAtual)}`;
    clienteBtnComprarGigante.href = p.linkAfiliado;
    clienteBtnComprarGigante.textContent = `🛒 COMPRAR NO ${nomePlat} (${formatarMoeda(p.precoAtual)}) ➔`;

    if (p.video) {
      clienteFotoFallback.style.display = "none";
      clienteVideoPlayer.style.display = "block";
      clienteVideoPlayer.src = p.video;
      clienteVideoPlayer.play().catch(() => {});
    } else {
      clienteVideoPlayer.pause();
      clienteVideoPlayer.style.display = "none";
      clienteFotoFallback.src = p.imagem;
      clienteFotoFallback.style.display = "block";
    }

    clienteOfertaModal.classList.add("open");
  }

  function fecharModalOfertaCliente() {
    clienteVideoPlayer.pause();
    clienteOfertaModal.classList.remove("open");
  }

  closeClienteOfertaBtn.addEventListener("click", fecharModalOfertaCliente);
  clienteOfertaModal.addEventListener("click", (e) => {
    if (e.target === clienteOfertaModal) fecharModalOfertaCliente();
  });

  clienteBtnZapShare.addEventListener("click", () => {
    if (produtoClienteModalAtual) {
      compartilharNoWhatsApp(produtoClienteModalAtual);
    }
  });

  function renderizarAtalhosNumeros(produtos) {
    const destaques = produtos.slice(0, 7);
    const botoesHtml = destaques
      .map(
        (p) =>
          `<button type="button" class="num-pill" data-code="${p.codigo}">#${p.codigo}</button>`
      )
      .join("");

    quickNumbersEl.innerHTML = `
      <span class="quick-numbers-title">🎬 Viu no vídeo? Clique no número:</span>
      ${botoesHtml}
    `;

    quickNumbersEl.querySelectorAll(".num-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        const codigo = btn.getAttribute("data-code");
        const prodAchado = listaProdutos.find((item) => String(item.codigo) === String(codigo));
        if (prodAchado) {
          abrirModalOfertaCliente(prodAchado);
        }
      });
    });
  }

  function filtrarProdutos(produtos) {
    return produtos.filter((p) => {
      const bateCategoria = categoriaAtiva === "todos" || p.categoria === categoriaAtiva;
      const batePlataforma = plataformaAtiva === "todas" || p.plataforma === plataformaAtiva;

      if (!termoBusca.trim()) {
        return bateCategoria && batePlataforma;
      }

      const buscaLimpa = termoBusca.trim().toLowerCase().replace(/^#/, "");
      const codigoLimpo = String(p.codigo).toLowerCase();
      const codigoSemZero = codigoLimpo.replace(/^0+/, "");
      const buscaSemZero = buscaLimpa.replace(/^0+/, "");

      const bateCodigo =
        codigoLimpo.includes(buscaLimpa) ||
        (buscaSemZero && codigoSemZero === buscaSemZero);

      const bateTexto =
        p.titulo.toLowerCase().includes(buscaLimpa) ||
        (p.categoriaNome && p.categoriaNome.toLowerCase().includes(buscaLimpa)) ||
        (p.plataformaNome && p.plataformaNome.toLowerCase().includes(buscaLimpa));

      return bateCategoria && batePlataforma && (bateCodigo || bateTexto);
    });
  }

  async function excluirProduto(id, titulo) {
    if (!confirm(`Deseja remover da vitrine o produto:\n"${titulo}"?`)) return;

    try {
      const resp = await fetch(`/api/produtos?id=${encodeURIComponent(id)}`, {
        method: "DELETE"
      });
      if (resp.ok) {
        const dados = await resp.json();
        listaProdutos = dados.produtos;
        renderizarAtalhosNumeros(listaProdutos);
        renderizarCatalogo();
        return;
      }
    } catch (e) {}

    listaProdutos = listaProdutos.filter((p) => String(p.id) !== String(id));
    renderizarAtalhosNumeros(listaProdutos);
    renderizarCatalogo();
  }

  function renderizarCatalogo() {
    const filtrados = filtrarProdutos(listaProdutos);

    countEl.textContent =
      filtrados.length === 1
        ? "1 oferta encontrada"
        : `${filtrados.length} ofertas encontradas`;

    if (filtrados.length === 0) {
      gridEl.style.display = "none";
      emptyStateEl.style.display = "block";
      return;
    }

    emptyStateEl.style.display = "none";
    gridEl.style.display = "grid";

    gridEl.innerHTML = filtrados
      .map((p) => {
        const desconto = calcularDesconto(p.precoAntigo, p.precoAtual);
        const nomePlat = p.plataformaNome || obterNomePlataforma(p.plataforma);

        return `
          <article class="product-card">
            <div class="card-image-wrap" data-open-id="${p.id}" style="cursor: pointer;">
              <div class="badge-codigo"><span>#${p.codigo}</span></div>
              ${desconto > 0 ? `<div class="badge-desconto">-${desconto}% OFF</div>` : ""}
              <div class="badge-plataforma plat-${p.plataforma}">${nomePlat}</div>
              ${
                isModoAdmin
                  ? `<button type="button" class="btn-delete-card" data-del-id="${p.id}" data-del-title="${p.titulo.replace(/"/g, "&quot;")}" title="Remover este produto da vitrine">🗑️ Excluir</button>`
                  : ""
              }
              <img src="${p.imagem}" alt="${p.titulo}" loading="lazy" />
            </div>

            <div class="card-body">
              <div class="card-meta">
                <span>${p.categoriaNome || obterNomeCategoria(p.categoria)}</span>
                <span class="card-rating">★ ${p.avaliacao || "4.9"} (${p.vendidos || "Oferta"})</span>
              </div>

              <h2 class="card-title" title="${p.titulo}" data-open-id="${p.id}" style="cursor: pointer;">${p.titulo}</h2>

              <div class="price-block">
                ${
                  p.precoAntigo && p.precoAntigo > p.precoAtual
                    ? `<div class="old-price">De ${formatarMoeda(p.precoAntigo)}</div>`
                    : `<div class="old-price">&nbsp;</div>`
                }
                <div class="current-price-row">
                  <span class="current-price">${formatarMoeda(p.precoAtual)}</span>
                  ${p.freteGratis ? `<span class="frete-tag">Frete Grátis*</span>` : ""}
                </div>
                <div class="installments">${p.parcelamento || "Compra 100% segura no site oficial"}</div>

                <a
                  href="${p.linkAfiliado}"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-buy ${p.plataforma}"
                >
                  <span>🛒 Comprar no ${nomePlat}</span>
                  <span>➔</span>
                </a>

                <div class="card-actions-secondary">
                  <button type="button" class="btn-watch-card" data-open-id="${p.id}">
                    ${p.video ? "▶️ Ver Vídeo da Oferta" : "🔍 Ver Detalhes"}
                  </button>
                  <button type="button" class="btn-zap-card" data-zap-id="${p.id}">
                    📲 Mandar no Zap
                  </button>
                </div>

                ${
                  isModoAdmin
                    ? `<button type="button" class="btn-video-card" data-vid-id="${p.id}">🎬 Gerar Vídeo IA (TikTok / Reels)</button>`
                    : ""
                }
              </div>
            </div>
          </article>
        `;
      })
      .join("");

    // Clique na foto, título ou botão "Ver Vídeo da Oferta" abre o modal com vídeo + botão gigante de compra
    gridEl.querySelectorAll("[data-open-id]").forEach((el) => {
      el.addEventListener("click", (e) => {
        if (e.target.closest(".btn-delete-card")) return;
        const id = el.getAttribute("data-open-id");
        const prod = listaProdutos.find((item) => String(item.id) === String(id));
        if (prod) abrirModalOfertaCliente(prod);
      });
    });

    gridEl.querySelectorAll(".btn-zap-card").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-zap-id");
        const prod = listaProdutos.find((item) => String(item.id) === String(id));
        if (prod) compartilharNoWhatsApp(prod);
      });
    });

    if (isModoAdmin) {
      gridEl.querySelectorAll(".btn-delete-card").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          excluirProduto(btn.getAttribute("data-del-id"), btn.getAttribute("data-del-title"));
        });
      });

      gridEl.querySelectorAll(".btn-video-card").forEach((btn) => {
        btn.addEventListener("click", () => {
          abrirEstudioVideo(btn.getAttribute("data-vid-id"));
        });
      });
    }
  }

  function atualizarBotaoLimpar() {
    clearSearchBtn.style.display = termoBusca.trim() ? "block" : "none";
  }

  // Eventos de busca
  searchInput.addEventListener("input", (e) => {
    termoBusca = e.target.value;
    quickNumbersEl.querySelectorAll(".num-pill").forEach((b) => b.classList.remove("active"));
    atualizarBotaoLimpar();
    renderizarCatalogo();
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    termoBusca = "";
    quickNumbersEl.querySelectorAll(".num-pill").forEach((b) => b.classList.remove("active"));
    atualizarBotaoLimpar();
    renderizarCatalogo();
  });

  document.getElementById("btnResetFilters").addEventListener("click", () => {
    categoriaAtiva = "todos";
    plataformaAtiva = "todas";
    termoBusca = "";
    searchInput.value = "";
    document.querySelectorAll(".cat-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.cat === "todos");
    });
    document.querySelectorAll(".plat-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.plat === "todas");
    });
    atualizarBotaoLimpar();
    renderizarCatalogo();
  });

  document.querySelectorAll(".cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".cat-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      categoriaAtiva = btn.dataset.cat;
      renderizarCatalogo();
    });
  });

  document.querySelectorAll(".plat-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".plat-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      plataformaAtiva = btn.dataset.plat;
      renderizarCatalogo();
    });
  });

  // Modal e Importador Automático por Link
  const modal = document.getElementById("adminModal");
  const openModalBtn = document.getElementById("openAdminBtn");
  const closeModalBtn = document.getElementById("closeAdminBtn");
  const formNovoProduto = document.getElementById("formNovoProduto");
  const inputLink = document.getElementById("inputLink");
  const btnPuxarDados = document.getElementById("btnPuxarDados");
  const extractStatus = document.getElementById("extractStatus");
  const previewBox = document.getElementById("previewBox");
  const previewImg = document.getElementById("previewImg");

  function calcularProximoCodigo() {
    let maior = 0;
    listaProdutos.forEach((p) => {
      const n = parseInt(String(p.codigo).replace(/\D/g, ""), 10);
      if (!isNaN(n) && n > maior) maior = n;
    });
    return String(maior + 1).padStart(2, "0");
  }

  function mostrarStatusExtracao(tipo, texto) {
    extractStatus.className = "extract-status " + tipo;
    extractStatus.textContent = texto;
  }

  async function puxarDadosDoLink() {
    const raw = inputLink.value.trim();
    if (!raw) {
      mostrarStatusExtracao("warn", "⚠️ Cole primeiro o link do produto no campo acima.");
      return;
    }

    btnPuxarDados.disabled = true;
    btnPuxarDados.textContent = "⏳ Buscando...";
    mostrarStatusExtracao("info", "⏳ Conectando ao site oficial para puxar foto, nome e preço...");

    try {
      const resp = await fetch("/api/extrair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: raw })
      });

      const dados = await resp.json();
      if (!resp.ok || !dados.sucesso) {
        mostrarStatusExtracao("warn", "⚠️ Não foi possível ler automaticamente. Preencha os campos abaixo.");
        return;
      }

      if (dados.urlOriginal) inputLink.value = dados.urlOriginal;
      if (dados.plataforma) document.getElementById("inputPlataforma").value = dados.plataforma;
      if (dados.categoria) document.getElementById("inputCategoria").value = dados.categoria;
      if (dados.titulo) document.getElementById("inputTitulo").value = dados.titulo;
      if (dados.precoAtual && dados.precoAtual > 0) {
        document.getElementById("inputPrecoAtual").value = Number(dados.precoAtual).toFixed(2);
      }
      if (dados.precoAntigo && dados.precoAntigo > 0) {
        document.getElementById("inputPrecoAntigo").value = Number(dados.precoAntigo).toFixed(2);
      }
      if (dados.imagem) {
        document.getElementById("inputImagem").value = dados.imagem;
        previewImg.src = dados.imagem;
        previewBox.style.display = "flex";
      }

      if (dados.titulo && dados.precoAtual > 0) {
        mostrarStatusExtracao(
          "success",
          `✅ Tudo puxado automaticamente da ${dados.plataformaNome}! Confira e clique em Salvar.`
        );
      } else if (dados.titulo) {
        mostrarStatusExtracao(
          "warn",
          `✅ Nome e loja identificados (${dados.plataformaNome})! Só confirme o Preço em Oferta abaixo.`
        );
      } else {
        mostrarStatusExtracao(
          "warn",
          `⚠️ A ${dados.plataformaNome} protegeu este link contra leitura automática. Preencha o nome e preço abaixo.`
        );
      }
    } catch (e) {
      mostrarStatusExtracao("warn", "⚠️ Erro de conexão com o extrator local.");
    } finally {
      btnPuxarDados.disabled = false;
      btnPuxarDados.textContent = "🔍 Puxar Dados";
    }
  }

  btnPuxarDados.addEventListener("click", puxarDadosDoLink);

  inputLink.addEventListener("paste", () => {
    setTimeout(() => {
      if (inputLink.value.trim().includes("http")) {
        puxarDadosDoLink();
      }
    }, 150);
  });

  document.getElementById("inputImagem").addEventListener("input", (e) => {
    const url = e.target.value.trim();
    if (url.startsWith("http")) {
      previewImg.src = url;
      previewBox.style.display = "flex";
    } else {
      previewBox.style.display = "none";
    }
  });

  openModalBtn.addEventListener("click", () => {
    formNovoProduto.reset();
    inputLink.value = "";
    extractStatus.className = "extract-status";
    extractStatus.textContent = "";
    previewBox.style.display = "none";
    document.getElementById("inputCodigo").value = calcularProximoCodigo();
    modal.classList.add("open");
    setTimeout(() => inputLink.focus(), 100);
  });

  closeModalBtn.addEventListener("click", () => {
    modal.classList.remove("open");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open");
  });

  formNovoProduto.addEventListener("submit", async (e) => {
    e.preventDefault();

    const codigo = document.getElementById("inputCodigo").value.trim() || calcularProximoCodigo();
    const titulo = document.getElementById("inputTitulo").value.trim();
    const plataforma = document.getElementById("inputPlataforma").value;
    const categoria = document.getElementById("inputCategoria").value;
    const precoAntigo = parseFloat(document.getElementById("inputPrecoAntigo").value) || 0;
    const precoAtual = parseFloat(document.getElementById("inputPrecoAtual").value) || 0;
    const imagem =
      document.getElementById("inputImagem").value.trim() ||
      "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=700&q=80";
    const linkAfiliado = inputLink.value.trim() || "#";

    const novo = {
      id: Date.now(),
      codigo,
      titulo,
      categoria,
      categoriaNome: obterNomeCategoria(categoria),
      plataforma,
      plataformaNome: obterNomePlataforma(plataforma),
      precoAntigo,
      precoAtual,
      parcelamento: "Oferta selecionada na Vitrine Express",
      avaliacao: "4.9",
      vendidos: "Destaque da Vitrine",
      destaqueVideo: true,
      freteGratis: true,
      imagem,
      linkAfiliado
    };

    try {
      const resp = await fetch("/api/produtos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ produto: novo })
      });
      if (resp.ok) {
        const dados = await resp.json();
        listaProdutos = dados.produtos;
      } else {
        listaProdutos.unshift(novo);
      }
    } catch (err) {
      listaProdutos.unshift(novo);
    }

    formNovoProduto.reset();
    modal.classList.remove("open");
    renderizarAtalhosNumeros(listaProdutos);
    renderizarCatalogo();
  });

  // Estúdio de Vídeo IA (TikTok / Instagram Reels)
  const videoModal = document.getElementById("videoModal");
  const closeVideoBtn = document.getElementById("closeVideoBtn");
  const selectVozIA = document.getElementById("selectVozIA");
  const inputRoteiroIA = document.getElementById("inputRoteiroIA");
  const btnGerarVideoAgora = document.getElementById("btnGerarVideoAgora");
  const videoStatusMsg = document.getElementById("videoStatusMsg");
  const videoResultArea = document.getElementById("videoResultArea");
  const videoPreviewPlayer = document.getElementById("videoPreviewPlayer");
  const btnDownloadVideo = document.getElementById("btnDownloadVideo");
  const btnAbrirPastaVideos = document.getElementById("btnAbrirPastaVideos");
  const btnPostarTikTok = document.getElementById("btnPostarTikTok");
  const inputLegendaIA = document.getElementById("inputLegendaIA");
  const btnCopiarLegenda = document.getElementById("btnCopiarLegenda");
  let ultimoArquivoVideoGerado = "";

  async function abrirEstudioVideo(idProduto) {
    produtoVideoAtualId = idProduto;
    videoResultArea.style.display = "none";
    videoPreviewPlayer.pause();
    videoPreviewPlayer.removeAttribute("src");
    videoStatusMsg.className = "extract-status info";
    videoStatusMsg.textContent = "⏳ Preparando roteiro e legenda com IA...";
    videoModal.classList.add("open");

    try {
      const resp = await fetch("/api/preparar-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: idProduto })
      });
      const dados = await resp.json();
      if (resp.ok && dados.sucesso) {
        inputRoteiroIA.value = dados.roteiro || "";
        inputLegendaIA.value = dados.legenda || "";
        videoStatusMsg.className = "extract-status";
        videoStatusMsg.textContent = "";
      } else {
        videoStatusMsg.className = "extract-status warn";
        videoStatusMsg.textContent = "⚠️ Não foi possível preparar o roteiro.";
      }
    } catch (e) {
      videoStatusMsg.className = "extract-status warn";
      videoStatusMsg.textContent = "⚠️ Erro ao conectar ao servidor de vídeo.";
    }
  }

  closeVideoBtn.addEventListener("click", () => {
    videoPreviewPlayer.pause();
    videoModal.classList.remove("open");
  });

  videoModal.addEventListener("click", (e) => {
    if (e.target === videoModal) {
      videoPreviewPlayer.pause();
      videoModal.classList.remove("open");
    }
  });

  btnGerarVideoAgora.addEventListener("click", async () => {
    if (!produtoVideoAtualId) return;

    btnGerarVideoAgora.disabled = true;
    btnGerarVideoAgora.textContent = "⏳ Gravando Voz IA e Montando Vídeo (~8 seg)...";
    videoStatusMsg.className = "extract-status info";
    videoStatusMsg.textContent =
      "🎙️ Gerando narração em português e renderizando cenas em formato TikTok/Reels...";

    try {
      const resp = await fetch("/api/gerar-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: produtoVideoAtualId,
          roteiro: inputRoteiroIA.value.trim(),
          voz: selectVozIA.value
        })
      });
      const dados = await resp.json();
      if (resp.ok && dados.sucesso) {
        videoStatusMsg.className = "extract-status success";
        videoStatusMsg.textContent = `✅ Vídeo pronto (${dados.duracao}s) e salvo na Vitrine! Clique em "🚀 Postar no TikTok" abaixo.`;
        inputLegendaIA.value = dados.legenda || inputLegendaIA.value;
        ultimoArquivoVideoGerado = dados.arquivo || "";
        const urlVideo = "/" + dados.arquivo + "?t=" + Date.now();
        videoPreviewPlayer.src = urlVideo;
        btnDownloadVideo.href = "/" + dados.arquivo;
        videoResultArea.style.display = "grid";
        videoPreviewPlayer.play().catch(() => {});
        sincronizarProdutosDoServidor();
      } else {
        videoStatusMsg.className = "extract-status warn";
        videoStatusMsg.textContent = "⚠️ Erro ao gerar vídeo: " + (dados.erro || "Tente novamente.");
      }
    } catch (e) {
      videoStatusMsg.className = "extract-status warn";
      videoStatusMsg.textContent = "⚠️ Falha ao comunicar com o gerador de vídeo.";
    } finally {
      btnGerarVideoAgora.disabled = false;
      btnGerarVideoAgora.textContent = "🎬 Gerar Vídeo Vertical (.MP4) com Voz IA";
    }
  });

  btnAbrirPastaVideos.addEventListener("click", async () => {
    try {
      await fetch("/api/abrir-pasta-videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arquivo: ultimoArquivoVideoGerado })
      });
    } catch (e) {}
  });

  btnPostarTikTok.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(inputLegendaIA.value);
    } catch (e) {}

    try {
      await fetch("/api/abrir-pasta-videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arquivo: ultimoArquivoVideoGerado })
      });
    } catch (e) {}

    window.open("https://www.tiktok.com/tiktokstudio/upload", "_blank", "noopener,noreferrer");
    videoStatusMsg.className = "extract-status success";
    videoStatusMsg.textContent =
      "🚀 Legenda copiada + Pasta aberta com o vídeo marcado! Arraste o vídeo para a aba do TikTok e aperte Ctrl+V na legenda.";
  });

  btnCopiarLegenda.addEventListener("click", () => {
    inputLegendaIA.select();
    navigator.clipboard.writeText(inputLegendaIA.value).then(() => {
      const txtOriginal = btnCopiarLegenda.textContent;
      btnCopiarLegenda.textContent = "✅ Legenda Copiada!";
      setTimeout(() => {
        btnCopiarLegenda.textContent = txtOriginal;
      }, 2000);
    });
  });

  // Se o cliente abrir um link direto como https://vitrine-express-ten.vercel.app/?p=10, já abre o Vídeo + Botão Gigante de Compra!
  let modalUrlJaAberto = false;
  function verificarParametroProdutoNaUrl() {
    if (modalUrlJaAberto) return;
    const params = new URLSearchParams(location.search);
    const codParam = (params.get("p") || params.get("codigo") || "").trim().replace(/^#/, "");
    if (!codParam) return;
    const prod = listaProdutos.find(
      (item) =>
        String(item.codigo).toLowerCase() === codParam.toLowerCase() ||
        String(item.codigo).replace(/^0+/, "") === codParam.replace(/^0+/, "")
    );
    if (prod) {
      modalUrlJaAberto = true;
      abrirModalOfertaCliente(prod);
    }
  }

  // Inicialização
  renderizarAtalhosNumeros(listaProdutos);
  renderizarCatalogo();
  verificarParametroProdutoNaUrl();
  sincronizarProdutosDoServidor();

  if (location.search.includes("painel=1")) {
    setTimeout(() => openModalBtn.click(), 300);
  }
})();
