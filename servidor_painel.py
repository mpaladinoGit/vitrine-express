import html
import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import gerador_video

PORTA = 8080
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_PRODUTOS = os.path.join(DIRETORIO_BASE, "produtos.js")

TITULOS_INVALIDOS = {
    "mercado livre",
    "mercado libre",
    "mercadolivre",
    "mercadolibre",
    "shopee brasil",
    "shopee",
    "amazon.com.br",
    "amazon",
    "acesso negado",
    "robot check",
}


def ler_produtos():
    if not os.path.exists(ARQUIVO_PRODUTOS):
        return []
    with open(ARQUIVO_PRODUTOS, "r", encoding="utf-8") as f:
        conteudo = f.read()
    match = re.search(r"window\.PRODUTOS_INICIAIS\s*=\s*(\[.*\])\s*;?", conteudo, re.DOTALL)
    if not match:
        return []
    bloco = match.group(1)
    try:
        return json.loads(bloco)
    except Exception:
        bloco_json = re.sub(r"(?m)^\s*([a-zA-Z0-9_]+)\s*:", r'"\1":', bloco)
        bloco_json = re.sub(r",(\s*[\]}])", r"\1", bloco_json)
        try:
            return json.loads(bloco_json)
        except Exception:
            return []


import subprocess
import threading


def _sincronizar_github_bg():
    try:
        subprocess.run(["git", "add", "produtos.js"], cwd=DIRETORIO_BASE, timeout=10)
        subprocess.run(
            ["git", "commit", "-m", "Atualiza catalogo de produtos da Vitrine Express"],
            cwd=DIRETORIO_BASE,
            timeout=10,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=DIRETORIO_BASE, timeout=25)
    except Exception:
        pass


def salvar_produtos(lista, sincronizar_git=True):
    cabecalho = (
        "// Catálogo oficial da Vitrine Express\n"
        "// Gerenciado pelo Painel Automático da Vitrine Express\n\n"
        "window.PRODUTOS_INICIAIS = "
    )
    corpo = json.dumps(lista, ensure_ascii=False, indent=2)
    with open(ARQUIVO_PRODUTOS, "w", encoding="utf-8") as f:
        f.write(cabecalho + corpo + ";\n")
    if sincronizar_git:
        threading.Thread(target=_sincronizar_github_bg, daemon=True).start()


def adivinhar_categoria(titulo):
    t = (titulo or "").lower()
    if any(
        p in t
        for p in [
            "fone",
            "bluetooth",
            "smartwatch",
            "relógio",
            "relogio",
            "celular",
            "smartphone",
            "carregador",
            "caixa de som",
            "tv",
            "televisão",
            "notebook",
            "tablet",
            "mouse",
            "teclado",
            "câmera",
            "camera",
            "gamer",
            "headset",
        ]
    ):
        return "eletronicos"
    if any(
        p in t
        for p in [
            "escova",
            "secador",
            "barbeador",
            "cabelo",
            "pele",
            "skincare",
            "maquiagem",
            "chapinha",
            "depilador",
            "perfume",
            "creme",
            "shampoo",
            "hidratante",
            "massageador",
        ]
    ):
        return "beleza"
    if any(
        p in t
        for p in [
            "parafusadeira",
            "furadeira",
            "ferramenta",
            "aspirador",
            "automotivo",
            "carro",
            "moto",
            "pneu",
            "chave",
            "lanterna",
            "lavadora",
            "serra",
            "trena",
            "compressor",
        ]
    ):
        return "ferramentas"
    return "casa"


def detectar_plataforma(url):
    u = (url or "").lower()
    if "shopee" in u or "shp.ee" in u:
        return "shopee", "Shopee"
    if "amazon" in u or "amzn.to" in u or "a.co" in u:
        return "amazon", "Amazon"
    if "mercadolivre" in u or "mercadolibre" in u or "meli.la" in u:
        return "mercadolivre", "Mercado Livre"
    return "mercadolivre", "Mercado Livre"


def desempacotar_url_verificacao(url):
    """Se o Mercado Livre redirecionar para /gz/account-verification?go=..., recupera a URL real do produto."""
    try:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "go" in qs and qs["go"]:
            return urllib.parse.unquote(qs["go"][0])
    except Exception:
        pass
    return url


def extrair_titulo_slug_url(url_alvo):
    url_limpa = desempacotar_url_verificacao(url_alvo)
    try:
        parsed = urllib.parse.urlparse(url_limpa)
        caminho = urllib.parse.unquote(parsed.path)

        # Shopee padrão: /Nome-Do-Produto-i.12345.67890
        m_shopee = re.search(r"/([^/]+)-i\.\d+\.\d+", caminho)
        if m_shopee:
            return m_shopee.group(1).replace("-", " ").strip()

        # Mercado Livre padrão 1: /MLB-123456-nome-do-produto-_JM
        m_ml = re.search(r"MLB-?\d+-([^/]+)-_JM", caminho, re.IGNORECASE)
        if m_ml:
            return m_ml.group(1).replace("-", " ").strip().title()

        # Mercado Livre padrão 2: /nome-do-produto/p/MLB123456
        m_ml2 = re.search(r"/([^/]+)/p/MLB", caminho, re.IGNORECASE)
        if m_ml2:
            return m_ml2.group(1).replace("-", " ").strip().title()

        # Mercado Livre padrão 3: qualquer segmento longo antes ou depois de MLB
        segmentos = [s for s in caminho.split("/") if len(s) > 12 and "-" in s]
        if segmentos:
            seg = segmentos[0]
            seg = re.sub(r"^MLB-?\d+-", "", seg, flags=re.IGNORECASE)
            seg = re.sub(r"-_JM$", "", seg, flags=re.IGNORECASE)
            return seg.replace("-", " ").strip().title()

        # Amazon padrão: /Nome-Do-Produto/dp/B0...
        m_amz = re.search(r"/([^/]+)/dp/[A-Z0-9]{10}", caminho)
        if m_amz:
            return m_amz.group(1).replace("-", " ").strip()
    except Exception:
        pass
    return ""


def buscar_complemento_web(titulo, mlb_id, plataforma):
    """Busca imagem oficial de catálogo e preço médio no Buscapé quando o link original exige login."""
    imagem = ""
    preco = 0.0
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    palavras_chave = " ".join((titulo or "").split()[:7]).strip()
    if not palavras_chave:
        return imagem, preco

    try:
        q_busca = urllib.parse.urlencode({"q": palavras_chave})
        req_b = urllib.request.Request(f"https://www.buscape.com.br/search?{q_busca}", headers=headers)
        with urllib.request.urlopen(req_b, timeout=8) as resp_b:
            html_b = resp_b.read(700_000).decode("utf-8", errors="replace")

            # 1. Foto oficial do produto no catálogo do Buscapé
            m_img = re.search(r'(https://i\.zst\.com\.br/thumbs/[^"\'<>]+)', html_b)
            if m_img:
                imagem = m_img.group(1)

            # 2. Preço do primeiro card de produto (evita valores pequenos de parcela)
            precos_achados = []
            for m_p in re.finditer(r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+,\d{2})", html_b):
                try:
                    val = float(m_p.group(1).replace(".", "").replace(",", "."))
                    if 15.0 <= val <= 20000.0:
                        precos_achados.append(val)
                except Exception:
                    pass
            if precos_achados:
                preco = precos_achados[0]
    except Exception:
        pass

    return imagem, preco


def titulo_eh_valido(t):
    if not t:
        return False
    limpo = t.strip().lower()
    if len(limpo) < 5:
        return False
    if limpo in TITULOS_INVALIDOS:
        return False
    if any(limpo.startswith(p) for p in ["mercado libre", "mercado livre", "robot check", "atenção"]):
        return False
    return True


def extrair_dados_url(texto_ou_url):
    texto_ou_url = (texto_ou_url or "").strip()
    m_url = re.search(r"https?://[^\s\"'<>]+", texto_ou_url)
    url_original = m_url.group(0) if m_url else texto_ou_url

    preco_texto = 0.0
    m_preco_txt = re.search(r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:,\d{2})?)", texto_ou_url)
    if m_preco_txt:
        try:
            preco_texto = float(m_preco_txt.group(1).replace(".", "").replace(",", "."))
        except Exception:
            preco_texto = 0.0

    plataforma, plataforma_nome = detectar_plataforma(url_original)
    url_final = url_original
    html_pagina = ""

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        req = urllib.request.Request(url_original, headers=headers)
        with opener.open(req, timeout=8) as resp:
            url_final = desempacotar_url_verificacao(resp.geturl() or url_original)
            raw = resp.read(500_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            html_pagina = raw.decode(charset, errors="replace")
    except Exception:
        url_final = desempacotar_url_verificacao(url_original)

    plataforma, plataforma_nome = detectar_plataforma(url_final)

    titulo = ""
    imagem = ""
    preco_atual = 0.0
    preco_antigo = 0.0

    if html_pagina:
        # 1. JSON-LD
        for m_ld in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_pagina,
            re.DOTALL | re.IGNORECASE,
        ):
            try:
                dados_ld = json.loads(m_ld.group(1).strip())
                itens = dados_ld if isinstance(dados_ld, list) else [dados_ld]
                for item in itens:
                    if isinstance(item, dict) and item.get("@type") in ("Product", "ItemPage"):
                        if not titulo_eh_valido(titulo) and item.get("name"):
                            titulo = str(item["name"])
                        if not imagem and item.get("image"):
                            img_val = item["image"]
                            if isinstance(img_val, list) and img_val:
                                imagem = str(img_val[0])
                            elif isinstance(img_val, dict):
                                imagem = str(img_val.get("url", ""))
                            elif isinstance(img_val, str):
                                imagem = img_val
                        offers = item.get("offers")
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            p = offers.get("price") or offers.get("lowPrice")
                            if p and not preco_atual:
                                preco_atual = float(str(p).replace(",", "."))
            except Exception:
                continue

        # 2. OpenGraph title & image
        if not titulo_eh_valido(titulo):
            m_og_t = re.search(
                r'<meta[^>]+(?:property|name)=["\'](?:og:title|twitter:title)["\'][^>]+content=["\']([^"\']+)["\']',
                html_pagina,
                re.IGNORECASE,
            ) or re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:title|twitter:title)["\']',
                html_pagina,
                re.IGNORECASE,
            )
            if m_og_t:
                candidato_t = html.unescape(m_og_t.group(1)).strip()
                if titulo_eh_valido(candidato_t):
                    titulo = candidato_t

        if not imagem:
            m_og_img = re.search(
                r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']',
                html_pagina,
                re.IGNORECASE,
            ) or re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
                html_pagina,
                re.IGNORECASE,
            )
            if m_og_img:
                cand_img = html.unescape(m_og_img.group(1)).strip()
                if "logo_large_plus" not in cand_img and "mercadolibre/pt_logo" not in cand_img:
                    imagem = cand_img

        if not imagem and plataforma == "amazon":
            m_amz_img = re.search(r'data-old-hires=["\'](https://[^"\']+)["\']', html_pagina) or re.search(
                r'"hiRes"\s*:\s*"(https://[^"]+)"', html_pagina
            )
            if m_amz_img:
                imagem = m_amz_img.group(1)

        if not preco_atual and plataforma == "amazon":
            m_amz_p = re.search(r'class=["\']a-offscreen["\']>R\$\s*([\d.,]+)<', html_pagina)
            if m_amz_p:
                try:
                    preco_atual = float(m_amz_p.group(1).replace(".", "").replace(",", "."))
                except Exception:
                    pass

    if titulo:
        titulo = re.sub(
            r"\s*[\|\-]\s*(Mercado Livre|Mercado Libre|Shopee Brasil|Shopee|Amazon\.com\.br).*$",
            "",
            titulo,
            flags=re.IGNORECASE,
        ).strip()

    # 3. Se o título veio bloqueado ("Mercado Libre"), extrai direto da URL do produto!
    if not titulo_eh_valido(titulo):
        titulo = extrair_titulo_slug_url(url_final) or extrair_titulo_slug_url(url_original)

    m_mlb = re.search(r"(MLB-?\d{7,14})", url_final, re.IGNORECASE) or re.search(
        r"(MLB-?\d{7,14})", url_original, re.IGNORECASE
    )
    mlb_id = m_mlb.group(1).replace("-", "").upper() if m_mlb else ""

    # 4. Se faltou imagem ou preço, busca complemento automático na web pelo nome + código do produto
    if titulo_eh_valido(titulo) and (not imagem or not preco_atual):
        img_web, preco_web = buscar_complemento_web(titulo, mlb_id, plataforma_nome)
        if not imagem and img_web:
            imagem = img_web
        if not preco_atual and preco_web > 0:
            preco_atual = preco_web

    if not preco_atual and preco_texto > 0:
        preco_atual = preco_texto

    if preco_atual > 0 and not preco_antigo:
        preco_antigo = round(preco_atual * 1.28, 2)

    categoria = adivinhar_categoria(titulo)

    return {
        "sucesso": True,
        "urlOriginal": url_original,
        "urlFinal": url_final,
        "plataforma": plataforma,
        "plataformaNome": plataforma_nome,
        "categoria": categoria,
        "titulo": titulo,
        "imagem": imagem,
        "precoAtual": preco_atual,
        "precoAntigo": preco_antigo,
    }


class PainelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRETORIO_BASE, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _enviar_json(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/produtos":
            produtos = ler_produtos()
            return self._enviar_json(200, {"produtos": produtos})
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo_raw = self.rfile.read(tamanho).decode("utf-8", errors="replace") if tamanho > 0 else "{}"
        try:
            payload = json.loads(corpo_raw)
        except Exception:
            payload = {}

        if parsed.path == "/api/extrair":
            url = payload.get("url", "")
            if not url:
                return self._enviar_json(400, {"sucesso": False, "erro": "Informe o link do produto."})
            resultado = extrair_dados_url(url)
            return self._enviar_json(200, resultado)

        if parsed.path == "/api/produtos":
            produtos = ler_produtos()
            novo = payload.get("produto")
            if not novo or not isinstance(novo, dict):
                return self._enviar_json(400, {"sucesso": False, "erro": "Dados do produto inválidos."})

            produtos.insert(0, novo)
            salvar_produtos(produtos)
            return self._enviar_json(200, {"sucesso": True, "produtos": produtos})

        if parsed.path == "/api/preparar-video":
            id_alvo = str(payload.get("id") or "")
            produtos = ler_produtos()
            prod = next((p for p in produtos if str(p.get("id")) == id_alvo), None)
            if not prod:
                return self._enviar_json(404, {"sucesso": False, "erro": "Produto não encontrado."})
            return self._enviar_json(
                200,
                {
                    "sucesso": True,
                    "roteiro": gerador_video.montar_roteiro_padrao(prod),
                    "legenda": gerador_video.montar_legenda_padrao(prod),
                },
            )

        if parsed.path == "/api/gerar-video":
            id_alvo = str(payload.get("id") or "")
            roteiro = payload.get("roteiro") or ""
            voz = payload.get("voz") or "pt-BR-FranciscaNeural"
            produtos = ler_produtos()
            prod = next((p for p in produtos if str(p.get("id")) == id_alvo), None)
            if not prod:
                return self._enviar_json(404, {"sucesso": False, "erro": "Produto não encontrado."})
            try:
                res = gerador_video.gerar_video_produto(prod, roteiro_custom=roteiro, voz=voz)
                return self._enviar_json(200, res)
            except Exception as e:
                return self._enviar_json(500, {"sucesso": False, "erro": str(e)})

        if parsed.path == "/api/abrir-pasta-videos":
            try:
                os.startfile(gerador_video.PASTA_VIDEOS)
                return self._enviar_json(200, {"sucesso": True})
            except Exception as e:
                return self._enviar_json(500, {"sucesso": False, "erro": str(e)})

        return self._enviar_json(404, {"sucesso": False, "erro": "Rota não encontrada."})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/produtos":
            qs = urllib.parse.parse_qs(parsed.query)
            id_alvo = (qs.get("id") or [""])[0]
            produtos = ler_produtos()
            filtrados = [p for p in produtos if str(p.get("id")) != str(id_alvo)]
            salvar_produtos(filtrados)
            return self._enviar_json(200, {"sucesso": True, "produtos": filtrados})

        return self._enviar_json(404, {"sucesso": False, "erro": "Rota não encontrada."})


if __name__ == "__main__":
    atuais = ler_produtos()
    if atuais:
        salvar_produtos(atuais, sincronizar_git=False)
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), PainelHandler)
    print(f"Servidor Vitrine Express rodando em http://localhost:{PORTA}")
    servidor.serve_forever()
